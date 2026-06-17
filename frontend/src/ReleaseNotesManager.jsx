// ReleaseNotesManager.jsx
// Standalone admin page — sidebar tab "Release Notes"
// Upload PDFs, view what's indexed, delete documents, test queries.

import React, { useState, useEffect, useRef } from 'react';
import {
  Box, Typography, Button, Card, CardContent, Chip,
  CircularProgress, Alert, Paper, LinearProgress, Divider,
  TextField, IconButton, Tooltip, Grid
} from '@mui/material';

import CloudUploadIcon   from '@mui/icons-material/CloudUpload';
import PictureAsPdfIcon  from '@mui/icons-material/PictureAsPdf';
import DeleteIcon        from '@mui/icons-material/Delete';
import SearchIcon        from '@mui/icons-material/Search';
import StorageIcon       from '@mui/icons-material/Storage';
import CheckCircleIcon   from '@mui/icons-material/CheckCircle';
import ArticleIcon       from '@mui/icons-material/Article';
import RefreshIcon       from '@mui/icons-material/Refresh';

const API_BASE = 'http://127.0.0.1:8000';

export default function ReleaseNotesManager() {
  const [sources,        setSources]        = useState([]);
  const [totalVectors,   setTotalVectors]   = useState(0);
  const [loading,        setLoading]        = useState(true);
  const [uploading,      setUploading]      = useState(false);
  const [uploadProgress, setUploadProgress] = useState(null); // {filename, status}
  const [error,          setError]          = useState(null);
  const [deletingSource, setDeletingSource] = useState(null);

  // Query test panel
  const [testQuery,   setTestQuery]   = useState('');
  const [testResults, setTestResults] = useState(null);
  const [testLoading, setTestLoading] = useState(false);

  const fileInputRef = useRef(null);

  // ── Load indexed sources on mount ──────────────────────────────────────
  const loadSources = async () => {
    setLoading(true);
    setError(null);
    try {
      const res  = await fetch(`${API_BASE}/api/release-notes/list`);
      const data = await res.json();
      setSources(data.sources || []);
      setTotalVectors(data.total_vectors || 0);
    } catch (err) {
      setError('Could not load indexed release notes.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadSources(); }, []);

  // ── Upload handler ───────────────────────────────────────────────────────
  const handleFileSelect = (e) => {
    const file = e.target.files?.[0];
    if (file) handleUpload(file);
  };

  const handleUpload = async (file) => {
    if (!file.name.toLowerCase().endsWith('.pdf')) {
      setError('Only PDF files are supported.');
      return;
    }

    setUploading(true);
    setError(null);
    setUploadProgress({ filename: file.name, status: 'uploading' });

    const formData = new FormData();
    formData.append('file', file);

    try {
      setUploadProgress({ filename: file.name, status: 'embedding' });

      const res = await fetch(`${API_BASE}/api/release-notes/upload`, {
        method: 'POST',
        body:   formData,
      });

      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail || 'Upload failed');
      }

      const data = await res.json();
      setUploadProgress({ filename: file.name, status: 'done', result: data });

      await loadSources();

      setTimeout(() => setUploadProgress(null), 3000);
    } catch (err) {
      setError(err.message);
      setUploadProgress(null);
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    const file = e.dataTransfer.files?.[0];
    if (file) handleUpload(file);
  };

  // ── Delete handler ───────────────────────────────────────────────────────
  const handleDelete = async (sourceName) => {
    setDeletingSource(sourceName);
    try {
      await fetch(`${API_BASE}/api/release-notes/${encodeURIComponent(sourceName)}`, {
        method: 'DELETE',
      });
      await loadSources();
    } catch (err) {
      setError(`Failed to delete ${sourceName}`);
    } finally {
      setDeletingSource(null);
    }
  };

  // ── Test query handler ───────────────────────────────────────────────────
  const handleTestQuery = async () => {
    if (!testQuery.trim()) return;
    setTestLoading(true);
    setTestResults(null);
    try {
      const res = await fetch(`${API_BASE}/api/release-notes/query`, {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({ query: testQuery, top_k: 5 }),
      });
      const data = await res.json();
      setTestResults(data.results || []);
    } catch (err) {
      setError('Query failed');
    } finally {
      setTestLoading(false);
    }
  };

  return (
    <Box sx={{ animation: 'fadeIn 0.5s ease-in' }}>

      {/* ── Header ── */}
      <Card elevation={0} sx={{ mb: 3, border: '1px solid #e0e0e0', borderRadius: 2 }}>
        <CardContent sx={{ p: 4 }}>
          <Typography variant="h5" fontWeight="bold" color="primary" sx={{ mb: 1 }}>
            ServiceNow Release Notes
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Upload ServiceNow release notes (e.g. Australia, Zurich) to keep scoped app
            generation aware of platform deprecations, security updates, and new
            recommendations. These are automatically checked before every scoped app build.
          </Typography>
        </CardContent>
      </Card>

      {/* ── Stats bar ── */}
      <Box sx={{ display: 'flex', gap: 2, mb: 3, flexWrap: 'wrap' }}>
        <Paper elevation={0} sx={{
          flex: 1, minWidth: 180, p: 2.5,
          border: '1px solid #e2e8f0', borderTop: '3px solid #6366f1', borderRadius: 2,
        }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
            <StorageIcon sx={{ color: '#6366f1' }} />
            <Box>
              <Typography variant="h5" fontWeight="bold" sx={{ color: '#6366f1', lineHeight: 1 }}>
                {totalVectors}
              </Typography>
              <Typography variant="caption" color="text.secondary">Total Chunks Indexed</Typography>
            </Box>
          </Box>
        </Paper>
        <Paper elevation={0} sx={{
          flex: 1, minWidth: 180, p: 2.5,
          border: '1px solid #e2e8f0', borderTop: '3px solid #10b981', borderRadius: 2,
        }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
            <ArticleIcon sx={{ color: '#10b981' }} />
            <Box>
              <Typography variant="h5" fontWeight="bold" sx={{ color: '#10b981', lineHeight: 1 }}>
                {sources.length}
              </Typography>
              <Typography variant="caption" color="text.secondary">Documents Indexed</Typography>
            </Box>
          </Box>
        </Paper>
      </Box>

      {error && <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>{error}</Alert>}

      {/* ── Upload zone ── */}
      <Card elevation={0} sx={{ mb: 3, border: '1px solid #e2e8f0', borderRadius: 2 }}>
        <CardContent sx={{ p: 3 }}>
          <Typography variant="subtitle2" fontWeight="bold" color="text.secondary" sx={{ mb: 1.5 }}>
            UPLOAD RELEASE NOTES PDF
          </Typography>

          <Box
            onDrop={handleDrop}
            onDragOver={(e) => e.preventDefault()}
            onClick={() => fileInputRef.current?.click()}
            sx={{
              border: '2px dashed #c7d2fe', borderRadius: 2, p: 4,
              textAlign: 'center', cursor: 'pointer',
              bgcolor: '#f5f5ff', transition: 'all 0.15s',
              '&:hover': { borderColor: '#6366f1', bgcolor: '#eef2ff' },
            }}
          >
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf"
              onChange={handleFileSelect}
              style={{ display: 'none' }}
            />
            <CloudUploadIcon sx={{ fontSize: 40, color: '#6366f1', mb: 1 }} />
            <Typography variant="body1" fontWeight="medium" sx={{ mb: 0.5 }}>
              Drop PDF here or click to browse
            </Typography>
            <Typography variant="caption" color="text.secondary">
              Supports large files (40MB+). Embedding may take a few minutes per document.
            </Typography>
          </Box>

          {/* Upload progress */}
          {uploadProgress && (
            <Paper elevation={0} sx={{
              mt: 2, p: 2, border: '1px solid #c7d2fe', borderRadius: 2, bgcolor: '#f5f5ff',
            }}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, mb: 1 }}>
                {uploadProgress.status === 'done'
                  ? <CheckCircleIcon sx={{ color: '#16a34a' }} />
                  : <CircularProgress size={18} />
                }
                <Typography variant="body2" fontWeight="medium">
                  {uploadProgress.filename}
                </Typography>
                <Chip
                  label={
                    uploadProgress.status === 'uploading' ? 'Uploading...' :
                    uploadProgress.status === 'embedding' ? 'Extracting & Embedding...' :
                    'Indexed Successfully'
                  }
                  size="small"
                  color={uploadProgress.status === 'done' ? 'success' : 'primary'}
                  sx={{ ml: 'auto' }}
                />
              </Box>
              {uploadProgress.status !== 'done' && (
                <LinearProgress sx={{ borderRadius: 4, height: 4 }} />
              )}
              {uploadProgress.result && (
                <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 1 }}>
                  {uploadProgress.result.pages} pages → {uploadProgress.result.chunks} chunks created
                </Typography>
              )}
            </Paper>
          )}
        </CardContent>
      </Card>

      {/* ── Indexed documents list ── */}
      <Card elevation={0} sx={{ mb: 3, border: '1px solid #e2e8f0', borderRadius: 2 }}>
        <CardContent sx={{ p: 3 }}>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1.5 }}>
            <Typography variant="subtitle2" fontWeight="bold" color="text.secondary">
              INDEXED DOCUMENTS
            </Typography>
            <IconButton size="small" onClick={loadSources}>
              <RefreshIcon sx={{ fontSize: 18 }} />
            </IconButton>
          </Box>

          {loading ? (
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, py: 2 }}>
              <CircularProgress size={18} />
              <Typography variant="body2" color="text.secondary">Loading...</Typography>
            </Box>
          ) : sources.length === 0 ? (
            <Alert severity="info">
              No release notes indexed yet. Upload a PDF above to get started.
            </Alert>
          ) : (
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
              {sources.map((src) => (
                <Paper key={src.source} elevation={0} sx={{
                  p: 1.5, border: '1px solid #e2e8f0', borderRadius: 1.5,
                  display: 'flex', alignItems: 'center', gap: 1.5,
                }}>
                  <PictureAsPdfIcon sx={{ color: '#dc2626', flexShrink: 0 }} />
                  <Box sx={{ flex: 1, minWidth: 0 }}>
                    <Typography variant="body2" fontWeight="medium" noWrap>
                      {src.source}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      {src.chunk_count} chunks indexed
                    </Typography>
                  </Box>
                  <Chip
                    label="Active"
                    size="small"
                    icon={<CheckCircleIcon sx={{ fontSize: '14px !important' }} />}
                    sx={{ bgcolor: '#f0fdf4', color: '#16a34a', border: '1px solid #86efac' }}
                  />
                  <Tooltip title="Remove from index">
                    <IconButton
                      size="small"
                      onClick={() => handleDelete(src.source)}
                      disabled={deletingSource === src.source}
                    >
                      {deletingSource === src.source
                        ? <CircularProgress size={16} />
                        : <DeleteIcon sx={{ fontSize: 18, color: '#ef4444' }} />
                      }
                    </IconButton>
                  </Tooltip>
                </Paper>
              ))}
            </Box>
          )}
        </CardContent>
      </Card>

      {/* ── Test query panel ── */}
      <Card elevation={0} sx={{ border: '1px solid #e2e8f0', borderRadius: 2 }}>
        <CardContent sx={{ p: 3 }}>
          <Typography variant="subtitle2" fontWeight="bold" color="text.secondary" sx={{ mb: 1.5 }}>
            TEST SEARCH
          </Typography>
          <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 2 }}>
            Try a search to see what the system would find before generating a scoped app.
          </Typography>

          <Box sx={{ display: 'flex', gap: 1.5, mb: 2 }}>
            <TextField
              fullWidth
              size="small"
              placeholder="e.g. scoped app ACL deprecations, security hardening changes"
              value={testQuery}
              onChange={(e) => setTestQuery(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter') handleTestQuery(); }}
            />
            <Button
              variant="contained"
              onClick={handleTestQuery}
              disabled={testLoading || !testQuery.trim()}
              startIcon={testLoading ? <CircularProgress size={16} color="inherit" /> : <SearchIcon />}
              sx={{ bgcolor: '#6366f1', '&:hover': { bgcolor: '#4f46e5' }, whiteSpace: 'nowrap' }}
            >
              Search
            </Button>
          </Box>

          {testResults && (
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
              {testResults.length === 0 ? (
                <Alert severity="info">No relevant results found in indexed release notes.</Alert>
              ) : (
                testResults.map((r, i) => (
                  <Paper key={i} elevation={0} sx={{
                    p: 1.5, border: '1px solid #e2e8f0', borderLeft: '3px solid #6366f1', borderRadius: 1.5,
                  }}>
                    <Box sx={{ display: 'flex', gap: 1, mb: 0.5, alignItems: 'center' }}>
                      <Chip label={r.source} size="small" variant="outlined" sx={{ fontSize: '0.65rem' }} />
                      <Typography variant="caption" color="text.secondary">Page {r.page}</Typography>
                      <Chip
                        label={`${(r.score * 100).toFixed(0)}% match`}
                        size="small"
                        sx={{
                          ml: 'auto', fontSize: '0.65rem',
                          bgcolor: r.score > 0.5 ? '#f0fdf4' : '#f8fafc',
                          color:   r.score > 0.5 ? '#16a34a' : '#64748b',
                        }}
                      />
                    </Box>
                    <Typography variant="body2" color="text.secondary" sx={{ fontSize: '0.8rem' }}>
                      {r.text.length > 280 ? r.text.slice(0, 280) + '...' : r.text}
                    </Typography>
                  </Paper>
                ))
              )}
            </Box>
          )}
        </CardContent>
      </Card>
    </Box>
  );
}