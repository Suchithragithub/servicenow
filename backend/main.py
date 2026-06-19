import os
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import requests
from llm_config import OPENAI_DEPLOYMENT, get_openai_client
from debt_services import scan_technical_debt, AVAILABLE_TABLES
from debt_snow_scanner import deactivate_record, DEACTIVATE_BLOCKED_TABLES
from release_services import fetch_servicenow_change, analyze_change_readiness
from integration_services import scan_integrations, AVAILABLE_INTEGRATION_TABLES
from integration_builder import generate_modernization_preview, apply_modernization
from atf_builder import build_atf_suite

from fastapi.responses import StreamingResponse
from orchestrator import Orchestrator

# from blueprint_validator import validate_module_blueprint, validate_scoped_app_blueprint


# Import the brain from services.py
from services import build_servicenow_module, build_scoped_app  

from fastapi import UploadFile, File
import shutil
from rag_release_notes import (
    ingest_pdf,
    query_release_notes,
    format_context_for_prompt,
    list_indexed_sources,
    delete_source,
    RELEASE_NOTES_DIR,
)

app = FastAPI()

orchestrator = Orchestrator()

# In-memory session store (swap for Redis in Phase 3)
_sessions: dict[str, dict] = {}

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class UserRequest(BaseModel):
    prompt: str

class DebtScanRequest(BaseModel):
    tables: list[str]   # e.g. ["sys_script", "sys_script_include"]
    limit: int = 100    # max records per table (sysparm_limit)

class DeactivateRequest(BaseModel):
    table: str
    sys_id: str

class DeactivateRequest(BaseModel):
    table:  str   # e.g. "sys_script"
    sys_id: str   # 32-char hex sys_id of the record
    name:   str   # just for logging — human readable name

class ReleaseCheckRequest(BaseModel):
    change_number: str  # e.g. "CHG0040007"
    instance_url: str   # e.g. "https://abhrademo5.service-now.com/"
    table_name: str     # e.g. "change_request"

class IntegrationScanRequest(BaseModel):
    tables: list[str]   # e.g. ["sys_rest_message", "sys_soap_message"]
    limit: int = 50     # max records per table

class PreviewRequest(BaseModel):
    finding: dict          # full finding object from scan result
 
 
class ApplyModernizationRequest(BaseModel):
    finding: dict          # original finding from scan
    blueprint: dict        # AI blueprint from preview step
    user_inputs: dict = {} # admin overrides: new_endpoint, new_rest_name,
                           #                  new_flow_name, new_auth_name


# ─────────────────────────────────────────
# NEW MODULE DEVELOPMENT
# ─────────────────────────────────────────

@app.post("/api/build-app")
async def build_servicenow_app(req: UserRequest):
    try:
        # All logic is safely handled in the service
        result = build_servicenow_module(req.prompt)

        return {
            "status": "success",
            "message": "App blueprint generated and tables built in ServiceNow!",
            "data": result
        }

    except Exception as e:
        print(f"❌ Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    

    
# ─────────────────────────────────────────
# SCOPED APP DEVELOPMENT
# ─────────────────────────────────────────
@app.post("/api/build-scoped-app")
async def build_scoped_app_route(req: UserRequest):
    try:
        result = build_scoped_app(req.prompt)
        return {
            "status": "success",
            "message": f"Scoped App '{result['app_name']}' built successfully!",
            **result
        }
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    
# ─────────────────────────────────────────
# DEBT CLEARANCE SCAN
# ─────────────────────────────────────────
    
@app.get("/api/debt-tables")
async def get_debt_tables():
    """
    Returns the list of scannable ServiceNow tables with labels.
    React uses this to build the scan selection checkboxes.
    """
    return {"tables": AVAILABLE_TABLES}
 
 
@app.post("/api/scan-debt")
async def run_debt_scan(req: DebtScanRequest):
    """
    Main scan endpoint. Scans selected ServiceNow tables,
    applies basic rule checks, runs AI analysis, returns full debt report.
 
    Request body:
    {
        "tables": ["sys_script", "sys_script_include", "sys_script_client"],
        "limit": 100
    }
    """
    try:
        if not req.tables:
            raise HTTPException(status_code=400, detail="At least one table must be selected.")
 
        result = scan_technical_debt(tables=req.tables, limit=req.limit)
 
        return {
            "status":   result["status"],
            "message":  f"Debt scan complete. {result['summary']['total_scanned']} records scanned.",
            "summary":  result["summary"],
            "findings": result["findings"]
        }
 
    except Exception as e:
        print(f"❌ Debt scan error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    
@app.post("/api/deactivate-record")
async def deactivate_snow_record(req: DeactivateRequest):
    """
    Safely deactivates (sets active=false) a single ServiceNow record.
    Does NOT delete anything. Fully reversible from ServiceNow UI.
 
    Request:
    {
        "table":  "sys_script",
        "sys_id": "abc123def456...",
        "name":   "Update User Email"
    }
 
    Response (success):
    {
        "status": "success",
        "message": "Record successfully deactivated in sys_script.",
        "updated_record": { "sys_id": "...", "name": "...", "active": "false" }
    }
 
    Response (blocked):
    {
        "status": "blocked",
        "message": "Deactivation blocked for table sys_security_acl — protected table."
    }
    """
    try:
        print(f"\\n🔧 DEACTIVATE REQUEST: {req.table}/{req.sys_id} ('{req.name}')")
 
        result = deactivate_record(table=req.table, sys_id=req.sys_id)
 
        if result["success"]:
            return {
                "status":         "success",
                "message":        result["message"],
                "updated_record": result["updated_record"]
            }
        else:
            return {
                "status":  "failed",
                "message": result["message"]
            }
 
    except Exception as e:
        print(f"❌ Deactivate error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    
# ─────────────────────────────────────────
# PRIVATE AGGREGATE CORE HELPER
# ─────────────────────────────────────────
def get_servicenow_count(base_url: str, query: str) -> int:
    """
    Hits the ServiceNow Aggregate (Stats) API to compute an integer row tally.
    """
    username = os.getenv("SERVICENOW_USERNAME")
    password = os.getenv("SERVICENOW_PASSWORD")
    
    stats_url = f"{base_url.rstrip('/')}/api/now/stats/change_request"
    params = {
        "sysparm_query": query,
        "sysparm_count": "true"
    }
    headers = {"Accept": "application/json"}
    
    try:
        # verify=False handles dev instances without robust SSL setups natively
        response = requests.get(stats_url, auth=(username, password), headers=headers, params=params, verify=False)
        response.raise_for_status()
        
        data = response.json()
        count_string = data.get("result", {}).get("stats", {}).get("count", "0")
        return int(count_string)
        
    except Exception as e:
        print(f"Error fetching aggregate count for query [{query}]: {e}")
        return 0
    
@app.get("/api/config/instance")
async def get_configured_instance():
    """
    Exposes the targeted ServiceNow instance URL from the backend environment
    so the React UI never requires manual typing or hardcoding.
    """
    # Fallback to your demo instance if the environment variable isn't set yet
    instance_url = os.getenv("SERVICENOW_INSTANCE_URL", "https://abhrademo5.service-now.com/")
    return {"instance_url": instance_url}
    
# ─────────────────────────────────────────
# LIVE RELEASE ANALYTICS & DASHBOARDS
# ─────────────────────────────────────────
@app.post("/api/release/analyze")
async def analyze_release_safety(req: ReleaseCheckRequest):
    try:
        change_payload = fetch_servicenow_change(
            instance_url=req.instance_url, 
            change_number=req.change_number,
            table_name=req.table_name
        )
        analysis_report = analyze_change_readiness(change_payload)
        return analysis_report
    except HTTPException as http_ex:
        raise http_ex
    except Exception as e:
        print(f"❌ Release Analysis error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal Release Analytics Engine error: {str(e)}")

#  FIXED: Mounted route onto @app engine to resolve the 404 error
@app.get("/api/release/dashboard-stats")
async def get_dashboard_stats(instance_url: str):
    """
    Fetches real-time release metric aggregations safely mapped to standard SNOW states.
    """
    if not instance_url:
        raise HTTPException(status_code=400, detail="Missing instance_url parameter")
    return {
    # Match State = Scheduled (-2) OR State = Implement (-1)
    "upcoming": get_servicenow_count(instance_url, "state=-2^ORstate=-1"), 
    
    # Match Approval = Requested
    "pending_cab": get_servicenow_count(instance_url, "approval=requested"), 
    
    # Match Approval = Approved AND State = Scheduled (-2)
    "ready": get_servicenow_count(instance_url, "approval=approved^state=-2"), 
    
    # Match Risk = High (2) OR Risk = Very High (1)
    "high_risk": get_servicenow_count(instance_url, "risk=1^ORrisk=2") 
}


# ─────────────────────────────────────────
# INTEGRATION & MODERNIZATION
# ─────────────────────────────────────────

@app.get("/api/integration-tables")
async def get_integration_tables():
    """
    Returns the list of scannable integration tables with labels.
    React uses this to build the scan selection checkboxes.
 
    Response:
    {
        "tables": [
            {"table": "sys_rest_message", "label": "REST Messages", "description": "..."},
            ...
        ]
    }
    """
    return {"tables": AVAILABLE_INTEGRATION_TABLES}
 
 
@app.post("/api/scan-integrations")
async def run_integration_scan_route(req: IntegrationScanRequest):
    """
    Main integration scan endpoint.
    Scans selected ServiceNow tables, applies rule checks,
    runs AI analysis, returns full modernization report.
 
    Request:
    {
        "tables": ["sys_rest_message", "sys_soap_message", "sys_trigger"],
        "limit": 50
    }
 
    Response:
    {
        "status": "completed",
        "message": "Integration scan complete. 12 records scanned.",
        "summary": {
            "total_scanned": 12,
            "critical": 2,
            "high": 4,
            "medium": 3,
            "low": 2,
            "already_modern": 1,
            "avg_score": 48.5,
            "by_table": {"sys_rest_message": 5, "sys_soap_message": 3, ...}
        },
        "findings": [
            {
                "sys_id": "abc123...",
                "name": "SAP Procurement REST",
                "table_source": "sys_rest_message",
                "label": "REST Message",
                "active": "true",
                "last_updated": "2020-06-15 10:00:00",
                "updated_by": "admin",
                "extra": {"endpoint": "http://sap.company.com/api", "auth_type": "basic"},
                "basic_flags": ["basic_auth_detected", "hardcoded_url", "no_error_handling"],
                "modernization_score": 28,
                "urgency": "Critical",
                "current_type": "Basic Auth REST Integration",
                "ai_issues": [
                    {"type": "Basic Auth", "detail": "Using Basic Auth — should migrate to OAuth2", "risk": "High"}
                ],
                "ai_summary": "Legacy REST integration using Basic Auth with no error handling.",
                "recommended_approach": "Replace with IntegrationHub REST spoke + OAuth2",
                "modernization_steps": [
                    "Create OAuth2 credential profile in ServiceNow",
                    "Replace sys_rest_message with IntegrationHub REST Action",
                    "Build Flow Designer flow to trigger on procurement events"
                ],
                "flow_designer_opportunity": "Replace scheduled polling with Flow Designer event trigger",
                "integrationhub_opportunity": "Use REST Step in Flow Designer with IntegrationHub spoke",
                "security_recommendation": "Migrate from Basic Auth to OAuth2 client credentials flow"
            }
        ]
    }
    """
    try:
        if not req.tables:
            raise HTTPException(status_code=400, detail="At least one table must be selected.")
 
        result = scan_integrations(tables=req.tables, limit=req.limit)
 
        return {
            "status":   result["status"],
            "message":  f"Integration scan complete. {result['summary']['total_scanned']} records scanned.",
            "summary":  result["summary"],
            "findings": result["findings"]
        }
 
    except Exception as e:
        print(f"❌ Integration scan error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    
@app.post("/api/preview-modernization")
async def preview_modernization(req: PreviewRequest):
    """
    Generates a Before/After modernization preview for a finding.
    ZERO writes to ServiceNow — pure AI generation.
    Safe to call multiple times.
 
    Request:
    {
        "finding": { ...finding object from scan result... }
    }
 
    Response:
    {
        "status": "success",
        "finding": { ...original finding... },
        "blueprint": {
            "before_state": [...],
            "after_state": [...],
            "create_rest_message": true,
            "create_flow": true,
            "create_auth_profile": true,
            "new_rest_message": { "suggested_name": "...", ... },
            "new_flow": { "suggested_name": "...", ... },
            "new_auth_profile": { "suggested_name": "...", ... },
            "old_record_action": "deactivate",
            "summary": "..."
        }
    }
    """
    try:
        result = generate_modernization_preview(finding=req.finding)
        return result
    except Exception as e:
        print(f"❌ Preview error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
 
 
@app.post("/api/apply-modernization")
async def apply_modernization_route(req: ApplyModernizationRequest):
    """
    Applies the approved modernization blueprint to ServiceNow.
    Called ONLY after admin reviews and approves the preview.
 
    Safety rule:
      - Creates all new components first
      - Deactivates old record ONLY if ALL succeed
      - If anything fails: stops and deactivates nothing
 
    Request:
    {
        "finding":     { ...original finding... },
        "blueprint":   { ...blueprint from preview... },
        "user_inputs": {
            "new_endpoint":   "https://api.company.com/v2",
            "new_rest_name":  "SAP API v2",
            "new_flow_name":  "SAP Procurement Flow",
            "new_auth_name":  "SAP OAuth2 Profile"
        }
    }
 
    Response:
    {
        "status": "completed | partial | failed",
        "finding_name": "SAP Procurement API",
        "steps": [
            { "step": "Create REST Message", "success": true,  "message": "...", "sys_id": "..." },
            { "step": "Create Auth Profile", "success": true,  "message": "...", "sys_id": "..." },
            { "step": "Create Flow",         "success": true,  "message": "...", "sys_id": "..." },
            { "step": "Deactivate Old Record","success": true, "message": "..." }
        ],
        "created_records": [
            { "label": "REST Message", "name": "...", "table": "...", "sys_id": "...", "snow_url": "..." }
        ],
        "old_deactivated": true,
        "errors": []
    }
    """
    try:
        result = apply_modernization(
            finding=req.finding,
            blueprint=req.blueprint,
            user_inputs=req.user_inputs
        )
        return result
    except Exception as e:
        print(f"❌ Apply modernization error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    
@app.post("/api/agent")
async def agent_endpoint(request: Request):
    
    """
    Body: { "prompt": "...", "session_id": "..." }
    Returns: text/event-stream of newline-delimited JSON chunks
    """
    body       = await request.json()
    prompt     = body.get("prompt", "").strip()
    session_id = body.get("session_id", "default")

    if not prompt:
        return {"error": "prompt is required"}

    # fetch or create session (Phase 3 multi-turn memory hook)
    session = _sessions.setdefault(session_id, {
        "history": [],
        "last_intent": None,
        "last_params": {},
    })
    session["history"].append({"role": "user", "content": prompt})

    async def stream():
        async for chunk in orchestrator.handle(prompt, session):
            yield f"data: {chunk}\n"   # SSE format

    return StreamingResponse(stream(), media_type="text/event-stream")

# ---------------------------------
# TESTING 
#----------------------------------

@app.post("/api/build-and-test")
async def build_and_test(request: Request):
    """
    Combined endpoint:
    1. Builds the module from blueprint
    2. Immediately generates ATF test suite
    3. Returns both build result and ATF suite info
 
    Request body:
    {
        "blueprint":         { ...blueprint dict... },
        "module_name":       "Vendor Management",
        "selected_features": ["roles", "workflows", ...]
    }
 
    Response:
    {
        "status":       "completed",
        "build_result": { ...what was created... },
        "atf": {
            "suite_name":    "Vendor Management — Automated Test Suite",
            "suite_sys_id":  "abc123...",
            "suite_url":     "https://instance.service-now.com/...",
            "tests_created": 12,
            "tests":         [ { name, sys_id, type } ],
            "errors":        []
        }
    }
    """
    body      = await request.json()
    blueprint = body.get("blueprint")
    module_name = body.get("module_name") or blueprint.get("module_name", "")
 
    if not blueprint:
        raise HTTPException(status_code=400, detail="blueprint is required")
 
    import asyncio
    loop = asyncio.get_event_loop()
 
    # Step 1: Build the module
    from services import build_servicenow_module_from_blueprint
    build_result = await loop.run_in_executor(
        None, lambda: build_servicenow_module_from_blueprint(blueprint)
    )
 
    # Step 2: Generate ATF tests
    atf_result = await loop.run_in_executor(
        None, lambda: build_atf_suite(module_name, build_result, blueprint)
    )
 
    return {
        "status":       "completed",
        "build_result": build_result,
        "atf":          atf_result,
    }
 
 
@app.post("/api/generate-atf")
async def generate_atf_only(request: Request):
    """
    Generates ATF tests for an already-built module.
    Use this if you want to add tests to an existing module
    without rebuilding it.
 
    Request body:
    {
        "blueprint":    { ...blueprint dict... },
        "module_name":  "Vendor Management",
        "build_result": { ...existing build result... }
    }
    """
    body         = await request.json()
    blueprint    = body.get("blueprint")
    module_name  = body.get("module_name") or (blueprint or {}).get("module_name", "")
    build_result = body.get("build_result", {})
 
    if not blueprint:
        raise HTTPException(status_code=400, detail="blueprint is required")
 
    import asyncio
    loop = asyncio.get_event_loop()
 
    atf_result = await loop.run_in_executor(
        None, lambda: build_atf_suite(module_name, build_result, blueprint)
    )
 
    return {"status": "completed", "atf": atf_result}

# @app.post("/api/validate-module")
# async def validate_module(body: Request):
#     data      = await body.json()
#     blueprint = data.get("blueprint")
#     selected_features = data.get("selected_features") 

#      # ── DEBUG ──
#     print("\n" + "="*50)
#     print("🔍 VALIDATE-MODULE CALLED")
#     print(f"   blueprint keys     : {list(blueprint.keys()) if blueprint else 'NONE'}")
#     print(f"   selected_features  : {selected_features}")
#     print(f"   'tables' in bp     : {'tables' in blueprint if blueprint else False}")
#     print("="*50)
#     # ── END DEBUG ──

#     if not blueprint:
#         return {"error": "blueprint is required"}
    
#     return validate_module_blueprint(blueprint, selected_features)

# @app.post("/api/validate-scoped-app")
# async def validate_scoped_app(body: Request):
#     data      = await body.json()
#     blueprint = data.get("blueprint")
#     selected_features = data.get("selected_features")

#     # ── DEBUG ──
#     print("\n" + "="*50)
#     print("🔍 VALIDATE-SCOPED-APP CALLED")
#     print(f"   blueprint keys     : {list(blueprint.keys()) if blueprint else 'NONE'}")
#     print(f"   selected_features  : {selected_features}")
#     print("="*50)
#     # ── END DEBUG ──

#     if not blueprint:
#         return {"error": "blueprint is required"}
#     return validate_scoped_app_blueprint(blueprint, selected_features)



@app.post("/api/generate-blueprint")
async def generate_blueprint_only(request: Request):
    try:
        body              = await request.json()
        prompt            = body.get("prompt", "")
        selected_features = body.get("selected_features", [])  # ← NEW
 
        if not prompt:
            raise HTTPException(status_code=400, detail="prompt is required")
 
        print(f"[generate-blueprint] prompt: {prompt}")
        print(f"[generate-blueprint] selected_features: {selected_features}")  # ← NEW
 
        from services import _generate_partial_blueprint  # ← use the shared helper
 
        # If selected_features provided, use partial blueprint generator
        # Otherwise fall back to generating everything (backward compat)
        if selected_features:
            blueprint = _generate_partial_blueprint(prompt, selected_features)
        else:
            # fallback: generate full blueprint (old behaviour)
            from prompts import SYSTEM_PROMPT
            import re, json
            client   = get_openai_client()
            response = client.chat.completions.create(
                model=OPENAI_DEPLOYMENT,
                temperature=0.2,
                max_tokens=3000,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user",   "content": prompt}
                ]
            )
            raw       = response.choices[0].message.content
            raw       = re.sub(r'```json\n?|```\n?', '', raw).strip()
            blueprint = json.loads(raw)
 
        print(f"[generate-blueprint] parsed keys: {list(blueprint.keys())}")  # ← will now show all 11 keys
        return {"blueprint": blueprint}
 
    except json.JSONDecodeError as e:
        print(f"[generate-blueprint] JSON parse failed: {e}")
        raise HTTPException(status_code=500, detail=f"LLM returned invalid JSON: {str(e)}")
    except Exception as e:
        print(f"[generate-blueprint] error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/build-from-blueprint")
async def build_from_blueprint(request: Request):
    from services import build_servicenow_module_from_blueprint   # ← changed
    body      = await request.json()
    blueprint = body.get("blueprint")

    import asyncio
    loop   = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        None, lambda: build_servicenow_module_from_blueprint(blueprint)  # ← pass blueprint directly
    )
    return {"status": "completed", "data": result}


# @app.post("/api/generate-scoped-blueprint")
# async def generate_scoped_blueprint(request: Request):
#     body   = await request.json()
#     prompt = body.get("prompt", "")
#     client = get_openai_client()
#     from prompts import SCOPED_APP_PROMPT
#     import re, json

#     response = client.chat.completions.create(
#         model=OPENAI_DEPLOYMENT,
#         temperature=0.2,
#         max_tokens=3000,
#         messages=[
#             {"role": "system", "content": SCOPED_APP_PROMPT},
#             {"role": "user",   "content": prompt}
#         ]
#     )
#     raw = response.choices[0].message.content
#     raw = re.sub(r'```json\n?|```\n?', '', raw).strip()
#     import json
#     blueprint = json.loads(raw)
#     return {"blueprint": blueprint}

@app.post("/api/generate-scoped-blueprint")
async def generate_scoped_blueprint(request: Request):
    body   = await request.json()
    prompt = body.get("prompt", "")
 
    if not prompt:
        raise HTTPException(status_code=400, detail="prompt is required")
 
    from prompts import SCOPED_APP_PROMPT
    from services import _check_release_notes_for_scoped_app
    import re, json
 
    print(f"[generate-scoped-blueprint] prompt: {prompt}")
 
    # ── Check release notes before generating ──────────────────────────────
    release_check = _check_release_notes_for_scoped_app(prompt)
 
    system_prompt = SCOPED_APP_PROMPT
    if release_check["has_relevant_changes"]:
        system_prompt = (
            f"{SCOPED_APP_PROMPT}\n\n"
            f"IMPORTANT — RECENT SERVICENOW RELEASE NOTES RELEVANT TO THIS REQUEST:\n"
            f"{release_check['context_block']}\n\n"
            f"Incorporate any deprecations, security updates, or new recommendations "
            f"from the above into your generated blueprint."
        )
        print(f"[generate-scoped-blueprint] release notes relevant — injecting context from {release_check['sources_checked']}")
    else:
        print("[generate-scoped-blueprint] no relevant release note changes found")
 
    client   = get_openai_client()
    response = client.chat.completions.create(
        model=OPENAI_DEPLOYMENT,
        temperature=0.2,
        max_tokens=3000,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": prompt}
        ]
    )
 
    raw       = response.choices[0].message.content
    raw       = re.sub(r'```json\n?|```\n?', '', raw).strip()
    blueprint = json.loads(raw)
 
    # Attach metadata about the check for frontend visibility
    blueprint["_release_notes_check"] = {
        "checked":              True,
        "has_relevant_changes": release_check["has_relevant_changes"],
        "sources_checked":      release_check["sources_checked"],
    }
 
    return {
        "blueprint":      blueprint,
        "release_check":  {
            "has_relevant_changes": release_check["has_relevant_changes"],
            "sources_checked":      release_check["sources_checked"],
            "relevant_sections":    release_check["raw_results"],
        }
    }


@app.post("/api/build-scoped-from-blueprint")
async def build_scoped_from_blueprint(request: Request):
    from services import build_scoped_app_from_blueprint          # ← changed
    body      = await request.json()
    blueprint = body.get("blueprint")

    import asyncio
    loop   = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        None, lambda: build_scoped_app_from_blueprint(blueprint)  # ← pass blueprint directly
    )
    return {"status": "completed", "data": result}

@app.post("/api/module-status")
async def module_status(body: dict):
    from services import get_module_status
    return get_module_status(body.get("module_name", ""))

#----------------------------------------------------------------------
#   RAG PIPELINE 
#----------------------------------------------------------------------

@app.post("/api/release-notes/upload")
async def upload_release_notes(file: UploadFile = File(...)):
    """
    Uploads a ServiceNow release notes PDF, extracts text, chunks it,
    embeds via Azure OpenAI, and stores in the local FAISS index.
 
    Accepts PDFs up to 40MB+ (large files handled in streaming chunks).
 
    Request: multipart/form-data with "file" field (the PDF)
 
    Response:
    {
        "status": "success",
        "source": "australia_release_notes.pdf",
        "pages": 245,
        "chunks": 612,
        "total_vectors_in_index": 1840
    }
    """
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
 
    # Save uploaded file to release_notes directory
    save_path = os.path.join(RELEASE_NOTES_DIR, file.filename)
 
    try:
        print(f"\n📥 UPLOADING: {file.filename}")
        with open(save_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
 
        file_size_mb = os.path.getsize(save_path) / (1024 * 1024)
        print(f"  ✅ Saved to disk: {save_path} ({file_size_mb:.1f} MB)")
 
        # Run ingestion pipeline (extract → chunk → embed → store)
        result = ingest_pdf(save_path, source_name=file.filename)
 
        return {"status": "success", **result}
 
    except Exception as e:
        print(f"❌ Upload/ingestion error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
 
 
@app.get("/api/release-notes/list")
async def list_release_notes():
    """
    Returns what release notes are currently indexed.
 
    Response:
    {
        "total_vectors": 1840,
        "sources": [
            {"source": "australia_release_notes.pdf", "chunk_count": 920},
            {"source": "zurich_release_notes.pdf",     "chunk_count": 920}
        ]
    }
    """
    return list_indexed_sources()
 
 
@app.delete("/api/release-notes/{source_name}")
async def delete_release_notes(source_name: str):
    """
    Removes a specific release notes document from the index.
    """
    result = delete_source(source_name)
 
    # Also delete the physical PDF file
    pdf_path = os.path.join(RELEASE_NOTES_DIR, source_name)
    if os.path.exists(pdf_path):
        os.remove(pdf_path)
 
    return result
 
 
@app.post("/api/release-notes/query")
async def query_release_notes_endpoint(request: Request):
    """
    Manually query the release notes index.
    Useful for testing or for the frontend to show "what changed" info.
 
    Request:
    {
        "query": "scoped app deprecations and security changes",
        "top_k": 5,
        "source_filter": "zurich_release_notes.pdf"   // optional
    }
 
    Response:
    {
        "results": [
            {"text": "...", "source": "...", "page": 12, "score": 0.83}
        ],
        "context": "formatted text block ready for prompt injection"
    }
    """
    body          = await request.json()
    query         = body.get("query", "")
    top_k         = body.get("top_k", 5)
    source_filter = body.get("source_filter")
 
    if not query:
        raise HTTPException(status_code=400, detail="query is required")
 
    results = query_release_notes(query, top_k=top_k, source_filter=source_filter)
    context = format_context_for_prompt(results)
 
    return {"results": results, "context": context}

#-----------------------------------------------------------------------------

# =============================================================================
# main.py — ADD this new endpoint (alongside your existing /api/build-and-test)
# =============================================================================

@app.post("/api/build-scoped-and-test")
async def build_scoped_and_test(request: Request):
    """
    Combined endpoint for SCOPED APPS:
    1. Builds the scoped app from blueprint
    2. Immediately generates ATF test suite (scoped-app-aware)
    3. Returns both build result and ATF suite info

    Request body:
    {
        "blueprint": { ...scoped app blueprint dict... }
    }

    Response:
    {
        "status":       "completed",
        "build_result": { ...what was created... },
        "atf": {
            "suite_name":    "...",
            "suite_sys_id":  "...",
            "suite_url":     "...",
            "tests_created": N,
            "tests":         [...],
            "errors":        []
        }
    }
    """
    body      = await request.json()
    blueprint = body.get("blueprint")

    if not blueprint:
        raise HTTPException(status_code=400, detail="blueprint is required")

    app_name  = blueprint.get("app_name", "")
    app_scope = blueprint.get("app_scope", "")

    import asyncio
    loop = asyncio.get_event_loop()

    # Step 1: Build the scoped app
    from services import build_scoped_app_from_blueprint
    build_result = await loop.run_in_executor(
        None, lambda: build_scoped_app_from_blueprint(blueprint)
    )

    # Step 2: Generate ATF tests (scoped-app-aware version)
    from atf_builder import build_scoped_atf_suite
    atf_result = await loop.run_in_executor(
        None, lambda: build_scoped_atf_suite(app_name, app_scope, build_result, blueprint)
    )

    return {
        "status":       "completed",
        "build_result": build_result,
        "atf":          atf_result,
    }
    
# ─────────────────────────────────────────
# HEALTH CHECK
# ─────────────────────────────────────────
@app.get("/health")
async def health_check():
    return {
        "status": "running",
        "routes": {
            "new_module":         "/api/build-app",
            "scoped_app":         "/api/build-scoped-app",
            "debt_tables":        "/api/debt-tables",
            "debt_scan":          "/api/scan-debt",
            "deactivate_record":  "/api/deactivate-record",
            "integration_tables": "/api/integration-tables",
            "integration_scan":   "/api/scan-integrations",
            "integration_preview":     "/api/preview-modernization",
            "integration_apply":       "/api/apply-modernization"
        }
    }