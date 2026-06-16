# rag_release_notes.py
#
# Stores ServiceNow release notes PDFs as FAISS vector embeddings (local, persistent).
# Used to check for platform changes/deprecations before generating scoped apps.
#
# Storage layout (all local, no external DB):
#   release_notes/
#     ├── <uploaded>.pdf              ← raw PDF kept for reference
#     ├── faiss_index/
#     │     ├── index.faiss           ← FAISS vector index (binary)
#     │     └── metadata.json         ← chunk text + source + page number
#
# Embedding model: Azure OpenAI text-embedding-3-small (1536 dims)
# Chunking: ~1000 chars per chunk, 150 char overlap, page-aware

import os
import json
import uuid
import numpy as np
import faiss
from pypdf import PdfReader
from llm_config import get_embedding_client

# ─────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────
RELEASE_NOTES_DIR = os.path.join(os.path.dirname(__file__), "release_notes")
INDEX_DIR         = os.path.join(RELEASE_NOTES_DIR, "faiss_index")
INDEX_PATH        = os.path.join(INDEX_DIR, "index.faiss")
METADATA_PATH     = os.path.join(INDEX_DIR, "metadata.json")

EMBEDDING_MODEL    = "text-embedding-3-large"   # Azure OpenAI embedding deployment name
EMBEDDING_DIM      = 3072
CHUNK_SIZE         = 1000     # characters per chunk
CHUNK_OVERLAP      = 150      # overlap between chunks
TOP_K_DEFAULT      = 5         # how many chunks to retrieve per query
EMBED_BATCH_SIZE   = 50        # how many chunks to embed per API call

os.makedirs(RELEASE_NOTES_DIR, exist_ok=True)
os.makedirs(INDEX_DIR, exist_ok=True)


# ─────────────────────────────────────────
# PDF TEXT EXTRACTION
# ─────────────────────────────────────────

def extract_pdf_text(pdf_path: str) -> list:
    """
    Extracts text from a PDF, page by page.
    Returns: [ {"page": 1, "text": "..."}, {"page": 2, "text": "..."}, ... ]
    """
    print(f"\n📄 Extracting text from: {pdf_path}")
    reader = PdfReader(pdf_path)
    pages  = []

    for i, page in enumerate(reader.pages):
        try:
            text = page.extract_text() or ""
        except Exception as e:
            print(f"  ⚠️  Failed to extract page {i+1}: {e}")
            text = ""
        if text.strip():
            pages.append({"page": i + 1, "text": text})

    print(f"  ✅ Extracted {len(pages)} pages with text")
    return pages


# ─────────────────────────────────────────
# CHUNKING
# ─────────────────────────────────────────

def chunk_text(pages: list, source_name: str) -> list:
    """
    Splits page text into overlapping chunks.
    Keeps page number reference for each chunk.

    Returns: [
        {"chunk_id": "...", "text": "...", "source": "australia.pdf", "page": 12},
        ...
    ]
    """
    chunks = []

    for page_data in pages:
        page_num = page_data["page"]
        text     = page_data["text"]

        start = 0
        while start < len(text):
            end       = min(start + CHUNK_SIZE, len(text))
            chunk_str = text[start:end].strip()

            if chunk_str:
                chunks.append({
                    "chunk_id": str(uuid.uuid4())[:8],
                    "text":     chunk_str,
                    "source":   source_name,
                    "page":     page_num,
                })

            if end >= len(text):
                break
            start = end - CHUNK_OVERLAP  # move forward with overlap

    print(f"  ✅ Created {len(chunks)} chunks from {source_name}")
    return chunks


# ─────────────────────────────────────────
# EMBEDDING (Azure OpenAI)
# ─────────────────────────────────────────

def embed_texts(texts: list) -> np.ndarray:
    """
    Embeds a list of strings using Azure OpenAI embeddings.
    Batches requests to avoid token limits.
    Returns: np.ndarray of shape (len(texts), EMBEDDING_DIM)
    """
    client     = get_embedding_client()
    all_embeds = []

    for i in range(0, len(texts), EMBED_BATCH_SIZE):
        batch = texts[i:i + EMBED_BATCH_SIZE]
        print(f"  🔢 Embedding batch {i // EMBED_BATCH_SIZE + 1} ({len(batch)} chunks)...")

        response = client.embeddings.create(
            model=EMBEDDING_MODEL,
            input=batch
        )
        batch_embeds = [item.embedding for item in response.data]
        all_embeds.extend(batch_embeds)

    return np.array(all_embeds, dtype="float32")


# ─────────────────────────────────────────
# FAISS INDEX MANAGEMENT
# ─────────────────────────────────────────

def _load_index_and_metadata():
    """
    Loads existing FAISS index + metadata if present.
    Returns (index, metadata_list). Creates empty ones if not found.
    """
    if os.path.exists(INDEX_PATH) and os.path.exists(METADATA_PATH):
        index = faiss.read_index(INDEX_PATH)
        with open(METADATA_PATH, "r", encoding="utf-8") as f:
            metadata = json.load(f)
        print(f"  📂 Loaded existing index: {index.ntotal} vectors, {len(metadata)} metadata entries")
        return index, metadata

    # Create new empty index (cosine similarity via normalized inner product)
    index    = faiss.IndexFlatIP(EMBEDDING_DIM)
    metadata = []
    print("  🆕 Created new empty FAISS index")
    return index, metadata


def _save_index_and_metadata(index, metadata):
    faiss.write_index(index, INDEX_PATH)
    with open(METADATA_PATH, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)
    print(f"  💾 Saved index: {index.ntotal} vectors, {len(metadata)} metadata entries")


def _normalize(vectors: np.ndarray) -> np.ndarray:
    """L2-normalize vectors so inner product = cosine similarity."""
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    norms[norms == 0] = 1e-10
    return vectors / norms


# ─────────────────────────────────────────
# MAIN: INGEST A PDF
# ─────────────────────────────────────────

def ingest_pdf(pdf_path: str, source_name: str = None) -> dict:
    """
    Full pipeline: extract → chunk → embed → store in FAISS.
    Call this after a PDF is uploaded.

    Args:
        pdf_path:    local path to the PDF file
        source_name: label for this document e.g. "australia_release_notes.pdf"
                     (defaults to filename if not given)

    Returns:
        { "source": str, "pages": int, "chunks": int, "total_vectors_in_index": int }
    """
    if source_name is None:
        source_name = os.path.basename(pdf_path)

    print(f"\n🚀 INGESTING: {source_name}")
    print("=" * 60)

    # 1. Extract
    pages = extract_pdf_text(pdf_path)
    if not pages:
        raise ValueError(f"No extractable text found in {pdf_path}")

    # 2. Chunk
    chunks = chunk_text(pages, source_name)
    if not chunks:
        raise ValueError(f"No chunks created from {pdf_path}")

    # 3. Embed
    texts      = [c["text"] for c in chunks]
    embeddings = embed_texts(texts)
    embeddings = _normalize(embeddings)

    # 4. Load existing index, append, save
    index, metadata = _load_index_and_metadata()

    # Remove old chunks from same source first (re-ingest = replace)
    if any(m["source"] == source_name for m in metadata):
        print(f"  🔄 Source '{source_name}' already indexed — rebuilding without old chunks")
        keep_indices = [i for i, m in enumerate(metadata) if m["source"] != source_name]
        if keep_indices:
            # Rebuild index with only kept vectors
            old_vectors = faiss.vector_to_array(index.reconstruct_n(0, index.ntotal)).reshape(index.ntotal, EMBEDDING_DIM)
            kept_vectors = old_vectors[keep_indices]
            new_index = faiss.IndexFlatIP(EMBEDDING_DIM)
            if len(kept_vectors) > 0:
                new_index.add(kept_vectors)
            index    = new_index
            metadata = [metadata[i] for i in keep_indices]
        else:
            index    = faiss.IndexFlatIP(EMBEDDING_DIM)
            metadata = []

    index.add(embeddings)
    metadata.extend(chunks)

    _save_index_and_metadata(index, metadata)

    print(f"\n✅ INGESTION COMPLETE: {source_name}")
    print(f"   Pages: {len(pages)} | Chunks: {len(chunks)} | Total vectors in index: {index.ntotal}")
    print("=" * 60)

    return {
        "source":                 source_name,
        "pages":                  len(pages),
        "chunks":                 len(chunks),
        "total_vectors_in_index": index.ntotal,
    }


# ─────────────────────────────────────────
# MAIN: QUERY THE INDEX
# ─────────────────────────────────────────

def query_release_notes(query: str, top_k: int = TOP_K_DEFAULT,
                        source_filter: str = None) -> list:
    """
    Searches the FAISS index for chunks relevant to the query.

    Args:
        query:         search text e.g. "scoped app deprecations"
        top_k:         number of results to return
        source_filter: optional — only search within this source file
                       e.g. "zurich_release_notes.pdf"

    Returns:
        [
            {"text": "...", "source": "...", "page": 12, "score": 0.83},
            ...
        ]
    """
    index, metadata = _load_index_and_metadata()

    if index.ntotal == 0:
        print("  ⚠️  No release notes indexed yet.")
        return []

    # Embed the query
    query_vec = embed_texts([query])
    query_vec = _normalize(query_vec)

    # Search — get more than top_k if filtering by source
    search_k = top_k * 5 if source_filter else top_k
    search_k = min(search_k, index.ntotal)

    scores, indices = index.search(query_vec, search_k)

    results = []
    for score, idx in zip(scores[0], indices[0]):
        if idx < 0 or idx >= len(metadata):
            continue
        chunk = metadata[idx]
        if source_filter and chunk["source"] != source_filter:
            continue
        results.append({
            "text":   chunk["text"],
            "source": chunk["source"],
            "page":   chunk["page"],
            "score":  float(score),
        })
        if len(results) >= top_k:
            break

    return results


# ─────────────────────────────────────────
# HELPER: Format results into a prompt-ready string
# ─────────────────────────────────────────

def format_context_for_prompt(results: list) -> str:
    """
    Formats query results into a readable block to inject into an LLM prompt.
    """
    if not results:
        return "No relevant release notes found."

    blocks = []
    for r in results:
        blocks.append(
            f"[Source: {r['source']}, Page {r['page']}, Relevance: {r['score']:.2f}]\n{r['text']}"
        )
    return "\n\n---\n\n".join(blocks)


# ─────────────────────────────────────────
# HELPER: List what's currently indexed
# ─────────────────────────────────────────

def list_indexed_sources() -> dict:
    """
    Returns summary of what's currently in the FAISS index.
    """
    index, metadata = _load_index_and_metadata()

    sources = {}
    for m in metadata:
        src = m["source"]
        sources[src] = sources.get(src, 0) + 1

    return {
        "total_vectors": index.ntotal,
        "sources": [{"source": s, "chunk_count": c} for s, c in sources.items()]
    }


def delete_source(source_name: str) -> dict:
    """
    Removes all chunks belonging to a specific source from the index.
    """
    index, metadata = _load_index_and_metadata()

    keep_indices = [i for i, m in enumerate(metadata) if m["source"] != source_name]
    removed_count = len(metadata) - len(keep_indices)

    if removed_count == 0:
        return {"removed": 0, "message": f"Source '{source_name}' not found in index"}

    if keep_indices:
        old_vectors  = index.reconstruct_n(0, index.ntotal)
        kept_vectors = old_vectors[keep_indices]
        new_index    = faiss.IndexFlatIP(EMBEDDING_DIM)
        new_index.add(kept_vectors)
        index    = new_index
        metadata = [metadata[i] for i in keep_indices]
    else:
        index    = faiss.IndexFlatIP(EMBEDDING_DIM)
        metadata = []

    _save_index_and_metadata(index, metadata)

    return {"removed": removed_count, "message": f"Removed {removed_count} chunks from '{source_name}'"}