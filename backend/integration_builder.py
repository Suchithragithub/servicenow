import json
import re
import time
from llm_config import get_openai_client, OPENAI_DEPLOYMENT
from prompts import INTEGRATION_PREVIEW_PROMPT
from snow_client import safe_post, safe_get, session, SNOW_BASE_URL
 
 
# ─────────────────────────────────────────
# STEP 1: GENERATE PREVIEW  (NO SNOW WRITES)
# ─────────────────────────────────────────
 
def generate_modernization_preview(finding: dict) -> dict:
    """
    Sends a scan finding to Azure OpenAI and gets a Before/After
    modernization preview blueprint.
 
    ZERO writes to ServiceNow — pure AI generation.
    Safe to call multiple times.
 
    Args:
        finding: one finding dict from the scan result
 
    Returns:
        dict with before_state, after_state, new components, summary
    """
    print(f"\n🔮 GENERATING PREVIEW FOR: '{finding.get('name')}'")
 
    user_content = f"""
Integration Name:   {finding.get('name', 'Unknown')}
Table:              {finding.get('table_source', 'Unknown')}
Component Type:     {finding.get('label', 'Unknown')}
Active:             {finding.get('active', 'Unknown')}
Last Updated:       {finding.get('last_updated', 'Unknown')}
Modernization Score:{finding.get('modernization_score', 0)}/100
Urgency:            {finding.get('urgency', 'Unknown')}
 
Current Issues:
{json.dumps(finding.get('ai_issues', []), indent=2)}
 
Detected Flags:
{json.dumps(finding.get('basic_flags', []), indent=2)}
 
Extra Metadata:
{json.dumps(finding.get('extra', {}), indent=2)}
 
AI Summary:
{finding.get('ai_summary', 'None')}
 
Recommended Approach:
{finding.get('recommended_approach', 'None')}
 
Security Recommendation:
{finding.get('security_recommendation', 'None')}
"""
 
    try:
        client = get_openai_client()
        response = client.chat.completions.create(
            model=OPENAI_DEPLOYMENT,
            temperature=0.1,
            max_tokens=1200,
            messages=[
                {"role": "system", "content": INTEGRATION_PREVIEW_PROMPT},
                {"role": "user",   "content": user_content}
            ]
        )
        raw = response.choices[0].message.content
        raw = re.sub(r'```json\n?|```\n?', '', raw).strip()
        blueprint = json.loads(raw)
 
        print(f"  ✅ Preview generated for '{finding.get('name')}'")
        return {
            "status":    "success",
            "finding":   finding,
            "blueprint": blueprint
        }
 
    except json.JSONDecodeError as e:
        print(f"  ❌ AI returned invalid JSON: {e}")
        return {
            "status":  "error",
            "message": "AI could not generate a valid preview. Try again.",
            "finding": finding
        }
    except Exception as e:
        print(f"  ❌ Preview generation failed: {e}")
        return {
            "status":  "error",
            "message": str(e),
            "finding": finding
        }
 
 
# ─────────────────────────────────────────
# STEP 2A: CREATE REST MESSAGE
# ─────────────────────────────────────────
 
def _create_rest_message(data: dict) -> tuple:
    """
    Creates a new sys_rest_message record in ServiceNow.
 
    Args:
        data: dict with name, endpoint, auth_type, http_method, description
 
    Returns:
        (success: bool, sys_id: str, message: str)
    """
    url     = f"{SNOW_BASE_URL}/sys_rest_message"
    payload = {
        "name":                data.get("name"),
        "rest_endpoint":       data.get("endpoint", ""),
        "authentication_type": _map_auth_type(data.get("auth_type", "no_auth")),
        "description":         data.get("description", ""),
        "active":              "true"
    }
 
    print(f"  📡 Creating REST Message: '{data.get('name')}'")
    response = safe_post(url, payload)
 
    if response.status_code == 201:
        sys_id = response.json().get("result", {}).get("sys_id")
        print(f"  ✅ REST Message created. sys_id: {sys_id}")
        return True, sys_id, "REST Message created successfully."
    else:
        msg = f"Failed ({response.status_code}): {response.text[:200]}"
        print(f"  ❌ {msg}")
        return False, None, msg
 
 
# ─────────────────────────────────────────
# STEP 2B: CREATE FLOW
# ─────────────────────────────────────────
 
def _create_flow(data: dict) -> tuple:
    """
    Creates a new sys_hub_flow record in ServiceNow.
    Note: Flow Designer flows created via Table API are basic shells.
    Full flow logic is configured inside ServiceNow Studio after creation.
 
    Args:
        data: dict with name, trigger_type, description
 
    Returns:
        (success: bool, sys_id: str, message: str)
    """
    url     = f"{SNOW_BASE_URL}/sys_hub_flow"
    payload = {
        "name":        data.get("name"),
        "description": data.get("description", ""),
        "active":      "false",   # start inactive — admin activates after review
        "run_as":      "user"
    }
 
    print(f"  ⚙️  Creating Flow: '{data.get('name')}'")
    response = safe_post(url, payload)
 
    if response.status_code == 201:
        sys_id = response.json().get("result", {}).get("sys_id")
        print(f"  ✅ Flow shell created. sys_id: {sys_id}")
        return True, sys_id, "Flow shell created successfully. Open in Flow Designer to add steps."
    else:
        msg = f"Failed ({response.status_code}): {response.text[:200]}"
        print(f"  ❌ {msg}")
        return False, None, msg
 
 
# ─────────────────────────────────────────
# STEP 2C: CREATE AUTH PROFILE
# ─────────────────────────────────────────
 
def _create_auth_profile(data: dict) -> tuple:
    """
    Creates a new sys_auth_profile record in ServiceNow.
 
    Args:
        data: dict with name, auth_type, description
 
    Returns:
        (success: bool, sys_id: str, message: str)
    """
    url     = f"{SNOW_BASE_URL}/sys_auth_profile"
    payload = {
        "name":        data.get("name"),
        "type":        _map_auth_type(data.get("auth_type", "oauth2")),
        "description": data.get("description", ""),
        "active":      "true"
    }
 
    print(f"  🔐 Creating Auth Profile: '{data.get('name')}'")
    response = safe_post(url, payload)
 
    if response.status_code == 201:
        sys_id = response.json().get("result", {}).get("sys_id")
        print(f"  ✅ Auth Profile created. sys_id: {sys_id}")
        return True, sys_id, "Auth Profile created. Add credentials inside ServiceNow."
    else:
        msg = f"Failed ({response.status_code}): {response.text[:200]}"
        print(f"  ❌ {msg}")
        return False, None, msg
 
 
# ─────────────────────────────────────────
# STEP 2D: DEACTIVATE OLD RECORD
# Only called AFTER all components created successfully
# ─────────────────────────────────────────
 
def _deactivate_old_record(table: str, sys_id: str, name: str) -> tuple:
    """
    Sets active = false on the old integration record.
    Called ONLY after all new components are successfully created.
 
    Args:
        table:  ServiceNow table name
        sys_id: old record sys_id
        name:   record name (for logging)
 
    Returns:
        (success: bool, message: str)
    """
    # Protect critical tables — never deactivate these
    PROTECTED = {"sys_dictionary", "sys_db_object", "sys_properties", "sys_security_acl"}
    if table in PROTECTED:
        return False, f"Table '{table}' is protected — cannot deactivate."
 
    url      = f"{SNOW_BASE_URL}/{table}/{sys_id}"
    payload  = {"active": "false"}
 
    print(f"  📴 Deactivating old record: '{name}' ({table}/{sys_id})")
    response = session.patch(url, json=payload, timeout=30)
 
    if response.status_code == 200:
        print(f"  ✅ Old record deactivated.")
        return True, f"'{name}' deactivated successfully. Re-activate anytime from ServiceNow."
    else:
        msg = f"Deactivation failed ({response.status_code}): {response.text[:150]}"
        print(f"  ❌ {msg}")
        return False, msg
 
 
# ─────────────────────────────────────────
# HELPER: MAP AUTH TYPE TO SNOW VALUE
# ─────────────────────────────────────────
 
def _map_auth_type(auth_type: str) -> str:
    mapping = {
        "oauth2":    "oauth2",
        "basic":     "basic",
        "api_key":   "api_key",
        "no_auth":   "no_authentication",
        "none":      "no_authentication",
    }
    return mapping.get(str(auth_type).lower(), "no_authentication")
 
 
# ─────────────────────────────────────────
# MASTER BUILDER — APPLY MODERNIZATION
# ─────────────────────────────────────────
 
def apply_modernization(finding: dict, blueprint: dict, user_inputs: dict) -> dict:
    """
    Applies the modernization blueprint to ServiceNow.
 
    SAFETY RULE:
      All components created first.
      Old record deactivated ONLY if ALL succeed.
      If any step fails → stop → deactivate nothing.
 
    Args:
        finding:     original finding from scan
        blueprint:   AI-generated preview blueprint
        user_inputs: overrides from admin (endpoint, names etc.)
                     Keys: new_endpoint, new_rest_name,
                           new_flow_name, new_auth_name
 
    Returns:
        dict with status, steps_completed, links to new records
    """
    print("\n" + "="*60)
    print(f"🚀 APPLYING MODERNIZATION: '{finding.get('name')}'")
    print("="*60)
 
    result = {
        "status":          "in_progress",
        "finding_name":    finding.get("name"),
        "table_source":    finding.get("table_source"),
        "steps":           [],
        "created_records": [],
        "old_deactivated": False,
        "errors":          []
    }
 
    # ── Merge user inputs into blueprint ─────────────────────────
    rest_data  = blueprint.get("new_rest_message", {})
    flow_data  = blueprint.get("new_flow", {})
    auth_data  = blueprint.get("new_auth_profile", {})
 
    # User can override AI suggestions
    rest_data["name"]     = user_inputs.get("new_rest_name")     or rest_data.get("suggested_name", f"{finding.get('name')} v2")
    rest_data["endpoint"] = user_inputs.get("new_endpoint")      or rest_data.get("suggested_endpoint", "")
    rest_data["auth_type"]= user_inputs.get("auth_type")         or rest_data.get("suggested_auth", "oauth2")
    flow_data["name"]     = user_inputs.get("new_flow_name")     or flow_data.get("suggested_name", f"{finding.get('name')} Flow")
    auth_data["name"]     = user_inputs.get("new_auth_name")     or auth_data.get("suggested_name", f"{finding.get('name')} Auth")
 
    all_success = True
 
    # ── STEP 1: Create REST Message ───────────────────────────────
    if blueprint.get("create_rest_message", True):
        ok, sys_id, msg = _create_rest_message(rest_data)
        result["steps"].append({
            "step":    "Create REST Message",
            "name":    rest_data["name"],
            "success": ok,
            "message": msg,
            "sys_id":  sys_id,
            "table":   "sys_rest_message",
            "snow_url": f"sys_rest_message.do?sys_id={sys_id}" if sys_id else None
        })
        if ok and sys_id:
            result["created_records"].append({
                "label":   "REST Message",
                "name":    rest_data["name"],
                "table":   "sys_rest_message",
                "sys_id":  sys_id,
                "snow_url":f"sys_rest_message.do?sys_id={sys_id}"
            })
        if not ok:
            all_success = False
            result["errors"].append(f"REST Message: {msg}")
        time.sleep(0.5)
 
    # ── STEP 2: Create Auth Profile ───────────────────────────────
    if blueprint.get("create_auth_profile", True) and all_success:
        ok, sys_id, msg = _create_auth_profile(auth_data)
        result["steps"].append({
            "step":    "Create Auth Profile",
            "name":    auth_data["name"],
            "success": ok,
            "message": msg,
            "sys_id":  sys_id,
            "table":   "sys_auth_profile",
            "snow_url": f"sys_auth_profile.do?sys_id={sys_id}" if sys_id else None
        })
        if ok and sys_id:
            result["created_records"].append({
                "label":   "Auth Profile",
                "name":    auth_data["name"],
                "table":   "sys_auth_profile",
                "sys_id":  sys_id,
                "snow_url":f"sys_auth_profile.do?sys_id={sys_id}"
            })
        if not ok:
            all_success = False
            result["errors"].append(f"Auth Profile: {msg}")
        time.sleep(0.5)
 
    # ── STEP 3: Create Flow ───────────────────────────────────────
    if blueprint.get("create_flow", True) and all_success:
        ok, sys_id, msg = _create_flow(flow_data)
        result["steps"].append({
            "step":    "Create Flow",
            "name":    flow_data["name"],
            "success": ok,
            "message": msg,
            "sys_id":  sys_id,
            "table":   "sys_hub_flow",
            "snow_url": f"sys_hub_flow.do?sys_id={sys_id}" if sys_id else None
        })
        if ok and sys_id:
            result["created_records"].append({
                "label":   "Flow Designer Flow",
                "name":    flow_data["name"],
                "table":   "sys_hub_flow",
                "sys_id":  sys_id,
                "snow_url":f"sys_hub_flow.do?sys_id={sys_id}"
            })
        if not ok:
            all_success = False
            result["errors"].append(f"Flow: {msg}")
        time.sleep(0.5)
 
    # ── STEP 4: DEACTIVATE OLD RECORD ────────────────────────────
    # ONLY if ALL previous steps succeeded
    if all_success:
        ok, msg = _deactivate_old_record(
            table  = finding.get("table_source"),
            sys_id = finding.get("sys_id"),
            name   = finding.get("name")
        )
        result["steps"].append({
            "step":    "Deactivate Old Record",
            "name":    finding.get("name"),
            "success": ok,
            "message": msg,
            "sys_id":  finding.get("sys_id"),
            "table":   finding.get("table_source")
        })
        result["old_deactivated"] = ok
        if not ok:
            result["errors"].append(f"Deactivation: {msg}")
    else:
        # Safety: skip deactivation
        result["steps"].append({
            "step":    "Deactivate Old Record",
            "name":    finding.get("name"),
            "success": False,
            "message": "Skipped — previous steps had errors. Old record kept active for safety.",
            "sys_id":  finding.get("sys_id"),
            "table":   finding.get("table_source")
        })
        result["errors"].append("Old record NOT deactivated because component creation failed.")
 
    # ── FINAL STATUS ─────────────────────────────────────────────
    if all_success and result["old_deactivated"]:
        result["status"] = "completed"
    elif all_success and not result["old_deactivated"]:
        result["status"] = "partial"   # components created but deactivation failed
    else:
        result["status"] = "failed"
 
    print(f"\n{'✅' if result['status'] == 'completed' else '⚠️'} MODERNIZATION STATUS: {result['status'].upper()}")
    print(f"   Created: {len(result['created_records'])} records")
    print(f"   Old deactivated: {result['old_deactivated']}")
    if result["errors"]:
        print(f"   Errors: {result['errors']}")
    print("="*60)
 
    return result