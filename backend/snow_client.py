# snow_client.py

import json
import os
import time
import requests
from dotenv import load_dotenv

load_dotenv()

SNOW_INSTANCE = os.getenv("SERVICENOW_INSTANCE", "").strip().strip('"').rstrip('/')
SNOW_USERNAME = os.getenv("SERVICENOW_USERNAME")
SNOW_PASSWORD = os.getenv("SERVICENOW_PASSWORD")
SNOW_BASE_URL = f"{SNOW_INSTANCE}/api/now/table"
SNOW_AUTH = (SNOW_USERNAME, SNOW_PASSWORD)

# ─────────────────────────────────────────
# FIX 1: USE REQUESTS.SESSION TO MAINTAIN COOKIES
# ─────────────────────────────────────────
session = requests.Session()
session.auth = SNOW_AUTH
session.headers.update({"Accept": "application/json", "Content-Type": "application/json"})

def safe_post(url, payload, retries=3, delay=1.5):
    for attempt in range(1, retries + 1):
        try:
            # Using session instead of requests
            response = session.post(url, json=payload, timeout=30)
            return response
        except requests.exceptions.ConnectionError as e:
            print(f"    ⚠️  Connection error (attempt {attempt}/{retries}): {e}")
            if attempt < retries: time.sleep(delay * attempt)
            else: raise
        except requests.exceptions.Timeout:
            if attempt < retries: time.sleep(delay * attempt)
            else: raise

def safe_get(url, retries=3, delay=1.5):
    for attempt in range(1, retries + 1):
        try:
            # Using session instead of requests
            response = session.get(url, timeout=30)
            return response
        except requests.exceptions.ConnectionError as e:
            print(f"    ⚠️  Connection error (attempt {attempt}/{retries}): {e}")
            if attempt < retries: time.sleep(delay * attempt)
            else: raise

# ─────────────────────────────────────────
# FIX 2: CORRECTLY QUERY AND DELETE PREFERENCES
# ─────────────────────────────────────────
def force_user_scope(app_sys_id: str, retries: int = 5):
    """
    Robust scope locking for Studio visibility
    """
    print(f"\n    🔄 Forcing API User session to Scope: {app_sys_id}...")

    # Get user sys_id
    user_url = f"{SNOW_BASE_URL}/sys_user?sysparm_query=user_name={SNOW_USERNAME}&sysparm_fields=sys_id"
    res = safe_get(user_url)
    users = res.json().get("result", [])
    if not users:
        print(f"    ⚠️  User {SNOW_USERNAME} not found.")
        return False

    user_id = users[0]["sys_id"]

    critical_prefs = [
        "sn_devstudio.current_app",
        "sn_devstudio.last_app",
        "system_app_selector.current_app",
        "glide.data_explorer.application",
        "com.glide.app.creator.current_app"
    ]

    for pref_name in critical_prefs:
        # STEP 1: GET the sys_id of the existing preference
        get_url = f"{SNOW_BASE_URL}/sys_user_preference?sysparm_query=name={pref_name}^user={user_id}&sysparm_fields=sys_id"
        get_res = safe_get(get_url)
        existing_prefs = get_res.json().get("result", [])

        # STEP 2: DELETE it using its explicit sys_id
        for pref in existing_prefs:
            pref_sys_id = pref["sys_id"]
            del_url = f"{SNOW_BASE_URL}/sys_user_preference/{pref_sys_id}"
            session.delete(del_url) # Correct Table API syntax

        # STEP 3: POST the new preference
        payload = {
            "name": pref_name,
            "user": user_id,
            "value": app_sys_id
        }
        session.post(f"{SNOW_BASE_URL}/sys_user_preference", json=payload)

    # Wait and verify
    time.sleep(3)

    verify_url = f"{SNOW_BASE_URL}/sys_user_preference?sysparm_query=user={user_id}^name=sn_devstudio.current_app&sysparm_fields=value"
    verify_res = safe_get(verify_url)
    verify_data = verify_res.json().get("result", [])
    
    current_scope = verify_data[0].get("value") if verify_data else None

    if current_scope == app_sys_id:
        print(f"    ✅ API Session successfully locked to Scope: {app_sys_id}")
        time.sleep(2.5)
        return True
    else:
        print(f"    ⚠️  Scope verification failed. Expected: {app_sys_id}, Got: {current_scope}")
        return False

# ─────────────────────────────────────────
# TABLES
# ─────────────────────────────────────────
def table_exists(table_name: str) -> bool:
    url = f"{SNOW_BASE_URL}/sys_db_object?sysparm_query=name={table_name}&sysparm_fields=sys_id"
    response = safe_get(url)
    results = response.json().get("result", [])
    return len(results) > 0

def create_snow_table(table_label: str, table_name: str, app_sys_id: str = None):
    url = f"{SNOW_BASE_URL}/sys_db_object"
    if not table_name.startswith("u_"): table_name = f"u_{table_name}"
    payload = {
        "label": table_label,
        "name": table_name,
        "create_access_controls": "true"
    }
    if app_sys_id:  # <-- Add this
        payload["sys_scope"] = app_sys_id
        payload["sys_package"] = app_sys_id
    response = safe_post(url, payload)
    if response.status_code == 201: return True, response.json().get("result", {}).get("sys_id")
    print(f"    ❌ Table failed ({response.status_code}): {response.text[:150]}")
    return False, response.text

def create_snow_field(table_name: str, field_label: str, field_name: str, internal_type: str, app_sys_id: str = None):
    SUPPORTED_TYPES = ["string", "integer", "boolean", "glide_date"]
    if internal_type not in SUPPORTED_TYPES: return False
    url = f"{SNOW_BASE_URL}/sys_dictionary"
    if not table_name.startswith("u_"): table_name = f"u_{table_name}"
    if not field_name.startswith("u_"): field_name = f"u_{field_name}"
    payload = {
        "name": table_name,
        "column_label": field_label,
        "element": field_name,
        "internal_type": internal_type
    }
    if app_sys_id:  # <-- Add this
        payload["sys_scope"] = app_sys_id
        payload["sys_package"] = app_sys_id
    response = safe_post(url, payload)
    return response.status_code == 201

# def create_snow_role(role_name: str, app_sys_id: str = None):
#     url = f"{SNOW_BASE_URL}/sys_user_role"
#     if not role_name.startswith("u_"): role_name = f"u_{role_name}"
#     payload = {
#         "name": role_name,
#         "description": f"Auto-generated role: {role_name}"
#     }
#     if app_sys_id:  # <-- Add this
#         payload["sys_scope"] = app_sys_id
#         payload["sys_package"] = app_sys_id
#     response = safe_post(url, payload)
#     if response.status_code == 201: return True, response.json().get("result", {}).get("sys_id")
#     return False, None

def create_snow_role(role_name: str, app_sys_id: str = None):
    url = f"{SNOW_BASE_URL}/sys_user_role"
    if not role_name.startswith("u_"):
        role_name = f"u_{role_name}"
 
    payload = {
        "name": role_name,
        "description": f"Auto-generated role: {role_name}"
    }
    if app_sys_id:
        payload["sys_scope"]   = app_sys_id
        payload["sys_package"] = app_sys_id
 
    response = safe_post(url, payload)
 
    if response.status_code == 201:
        return True, response.json().get("result", {}).get("sys_id")
 
    # ── DEBUG: print exactly why it failed ──────────────────────────────────
    print(f"    ❌ Role creation failed ({response.status_code}): {response.text[:300]}")
    # ── END DEBUG ────────────────────────────────────────────────────────────
 
    return False, None

def create_snow_form(form_name: str, target_table: str, visible_fields: list, app_sys_id: str = None):
    url = f"{SNOW_BASE_URL}/sys_ui_section"
    payload = {"name": target_table, "title": form_name, "view": "Default view"}
    if app_sys_id: 
        payload["sys_scope"] = app_sys_id
        payload["sys_package"] = app_sys_id
    response = safe_post(url, payload)
    if response.status_code != 201: return False, None
    section_id = response.json().get("result", {}).get("sys_id")
    time.sleep(0.5)
    for i, field_name in enumerate(visible_fields):
        field_url = f"{SNOW_BASE_URL}/sys_ui_element"
        field_payload = {"sys_ui_section": section_id, "element": field_name, "position": str(i), "type": "field"}
        if app_sys_id:
            field_payload["sys_scope"] = app_sys_id
            field_payload["sys_package"] = app_sys_id
        safe_post(field_url, field_payload)
        time.sleep(0.3)
    return True, section_id

def create_snow_notification(name: str, table_name: str, trigger: str, recipient: str, app_sys_id: str = None):
    url = f"{SNOW_BASE_URL}/sysevent_email_action"
    payload = {
        "name": name,
        "collection": table_name,
        "action_insert": "true" if "insert" in trigger.lower() else "false",
        "action_update": "true" if "update" in trigger.lower() else "false",
        "subject": f"[ServiceNow] {name}",
        "message_html": f"<p>Automated notification for: {name}</p>",
        "recipients": recipient
    }
    if app_sys_id:  # <-- Add this
        payload["sys_scope"] = app_sys_id
        payload["sys_package"] = app_sys_id
    response = safe_post(url, payload)
    return response.status_code == 201

def get_role_sys_id(role_name: str):
    url = f"{SNOW_BASE_URL}/sys_user_role?sysparm_query=name={role_name}&sysparm_fields=sys_id"
    response = safe_get(url)
    results = response.json().get("result", [])
    if results: return results[0].get("sys_id")
    return None

def create_snow_approval(name: str, table_name: str, condition: str, approver_role: str, app_sys_id: str = None):
    url = f"{SNOW_BASE_URL}/sys_script"
    if not table_name.startswith(("u_", "x_snc_")): table_name = f"u_{table_name}"
    script = f"""(function executeRule(current, previous) {{ gs.log('Approval rule triggered: {name}'); current.state = 'pending_approval'; current.update(); }})(current, previous);"""
    payload = {
        "name": name,
        "collection": table_name,
        "when": "before",
        "action_insert": "true",
        "action_update": "false",
        "condition": condition,
        "script": script,
        "active": "true"
    }
    if app_sys_id:  # <-- Add this
        payload["sys_scope"] = app_sys_id
        payload["sys_package"] = app_sys_id
    response = safe_post(url, payload)
    return response.status_code == 201

def create_snow_workflow(name: str, table_name: str, trigger: str, steps: list, app_sys_id: str = None):
    """Creates a Legacy Workflow with Begin → Approval → Create Task → End"""

    if not table_name.startswith(("u_", "x_")):
        table_name = f"u_{table_name}"

    # ── STEP 1: Get activity definition sys_ids from YOUR instance ──
    def get_activity_def_id(activity_name: str):
        url = f"{SNOW_BASE_URL}/wf_activity_definition?sysparm_query=name={activity_name}&sysparm_fields=sys_id&sysparm_limit=1"
        res = safe_get(url)
        results = res.json().get("result", [])
        return results[0].get("sys_id") if results else None

    begin_def_id    = get_activity_def_id("Begin")
    end_def_id      = get_activity_def_id("End")
    approval_def_id = get_activity_def_id("Approval - User")
    task_def_id     = get_activity_def_id("Create Task")

    print(f"    📋 Activity Defs — Begin:{begin_def_id} End:{end_def_id} Approval:{approval_def_id} Task:{task_def_id}")

    if not begin_def_id or not end_def_id:
        print("    ❌ Could not find Begin/End activity definitions. Falling back to Business Rule.")
        return _create_workflow_as_business_rule(name, table_name, trigger, steps, app_sys_id)

    # ── STEP 2: Create workflow header ──
    wf_url = f"{SNOW_BASE_URL}/wf_workflow"
    wf_payload = {
        "name": name,
        "table": table_name,
        "description": f"Auto-generated: {name}",
        "active": "true",
    }
    if app_sys_id:
        wf_payload["sys_scope"] = app_sys_id
        wf_payload["sys_package"] = app_sys_id

    wf_res = safe_post(wf_url, wf_payload)
    if wf_res.status_code != 201:
        print(f"    ❌ Workflow header failed: {wf_res.text[:150]}")
        return False

    wf_sys_id = wf_res.json().get("result", {}).get("sys_id")
    time.sleep(1)

    # ── STEP 3: Create workflow version ──
    ver_url = f"{SNOW_BASE_URL}/wf_workflow_version"
    ver_payload = {
        "workflow": wf_sys_id,
        "name": name,
        "table": table_name,
        "active": "true",
        "published": "true",
    }
    if app_sys_id:
        ver_payload["sys_scope"] = app_sys_id

    ver_res = safe_post(ver_url, ver_payload)
    if ver_res.status_code != 201:
        print(f"    ❌ Workflow version failed: {ver_res.text[:150]}")
        return False

    ver_sys_id = ver_res.json().get("result", {}).get("sys_id")
    time.sleep(1)

    # ── STEP 4: Create activities ──
    act_url = f"{SNOW_BASE_URL}/wf_activity"

    def create_activity(act_name, def_id, x, y):
        payload = {
            "workflow_version": ver_sys_id,
            "name": act_name,
            "activity_definition": def_id,
            "x": str(x),
            "y": str(y),
        }
        if app_sys_id:
            payload["sys_scope"] = app_sys_id
        res = safe_post(act_url, payload)
        if res.status_code == 201:
            return res.json().get("result", {}).get("sys_id")
        print(f"    ⚠️  Activity '{act_name}' failed: {res.text[:100]}")
        return None

    begin_id = create_activity("Begin", begin_def_id, 50, 100)
    time.sleep(0.3)

    # Create approval or task activities based on steps
    activity_ids = [begin_id]
    x_pos = 250

    for step in steps:
        step_lower = str(step).lower()
        if "approval" in step_lower and approval_def_id:
            act_id = create_activity(step, approval_def_id, x_pos, 100)
        elif "task" in step_lower and task_def_id:
            act_id = create_activity(step, task_def_id, x_pos, 100)
        elif task_def_id:
            act_id = create_activity(step, task_def_id, x_pos, 100)
        else:
            act_id = None

        if act_id:
            activity_ids.append(act_id)
            x_pos += 200
        time.sleep(0.3)

    end_id = create_activity("End", end_def_id, x_pos, 100)
    activity_ids.append(end_id)
    time.sleep(0.3)

    # ── STEP 5: Create transitions ──
    trans_url = f"{SNOW_BASE_URL}/wf_transition"

    def create_transition(from_id, to_id, condition_name="Always"):
        if not from_id or not to_id:
            return
        payload = {
            "from": from_id,
            "to": to_id,
            "workflow_version": ver_sys_id,
            "name": condition_name,
            "condition_type": "0",
        }
        if app_sys_id:
            payload["sys_scope"] = app_sys_id
        safe_post(trans_url, payload)
        time.sleep(0.2)

    # Chain all activities: Begin → step1 → step2 → ... → End
    for i in range(len(activity_ids) - 1):
        create_transition(activity_ids[i], activity_ids[i + 1])

    print(f"    ✅ Workflow '{name}' created with {len(steps)} activities.")
    return True


def _create_workflow_as_business_rule(name, table_name, trigger, steps, app_sys_id=None):
    """Fallback — creates a Business Rule if workflow canvas fails"""
    url = f"{SNOW_BASE_URL}/sys_script"
    steps_log = "\n".join([f"    gs.log('Step: {s}');" for s in steps])
    script = f"""(function executeRule(current, previous) {{
    gs.log('Workflow started: {name}');
{steps_log}
    gs.log('Workflow completed: {name}');
}})(current, previous);"""
    payload = {
        "name": name,
        "collection": table_name,
        "when": "after",
        "action_insert": "true" if "insert" in str(trigger).lower() else "false",
        "action_update": "true" if "update" in str(trigger).lower() else "false",
        "script": script,
        "active": "true"
    }
    if app_sys_id:
        payload["sys_scope"] = app_sys_id
        payload["sys_package"] = app_sys_id
    res = safe_post(url, payload)
    return res.status_code == 201

def create_snow_application(app_name: str, app_scope: str, app_sys_id: str = None):
    url = f"{SNOW_BASE_URL}/sys_scope"
    payload = {
        "name": app_name,
        "scope": app_scope,
        "version": "1.0.0",
        "active": "true"
    }
    if app_sys_id:  # <-- Add this (though sys_scope is usually set by the scope itself)
        payload["sys_scope"] = app_sys_id
        payload["sys_package"] = app_sys_id
    response = safe_post(url, payload)
    if response.status_code == 201: return True, response.json().get("result", {}).get("sys_id")
    return False, None

def create_snow_app_menu(title: str, app_sys_id: str = None):
    url = f"{SNOW_BASE_URL}/sys_app_application"
    payload = {
        "title": title,
        "active": "true",
        "order": "100"
    }
    if app_sys_id:  # <-- Add this
        payload["sys_scope"] = app_sys_id
        payload["sys_package"] = app_sys_id
    response = safe_post(url, payload)
    if response.status_code == 201: return True, response.json().get("result", {}).get("sys_id")
    return False, None

# def create_snow_navigation(title: str, table_name: str, menu_sys_id: str = None, app_sys_id: str = None):
#     url = f"{SNOW_BASE_URL}/sys_app_module"
#     if not table_name.startswith("u_"): table_name = f"u_{table_name}"
#     payload = {
#         "title": title,
#         "name": table_name,
#         "active": "true",
#         "order": "100",
#         "link_type": "LIST",
#         "roles": ""
#     }
#     if menu_sys_id:
#         payload["application"] = menu_sys_id
#     if app_sys_id:  # <-- Add this
#         payload["sys_scope"] = app_sys_id
#         payload["sys_package"] = app_sys_id
#     response = safe_post(url, payload)
#     return response.status_code == 201

def create_snow_navigation(title: str, table_name: str, menu_sys_id: str = None, app_sys_id: str = None):
    """
    Creates a Navigation Module (sys_app_module) linked to an Application Menu.
    FIX 5: menu_sys_id is now properly passed as "application" field,
    which links the nav module to the correct app menu in the left panel.
    """
    url = f"{SNOW_BASE_URL}/sys_app_module"
    if not table_name.startswith(("u_", "x_")):
        table_name = f"u_{table_name}"
 
    payload = {
        "title":     title,
        "name":      table_name,
        "active":    "true",
        "order":     "100",
        "link_type": "LIST",
        "roles":     ""
    }
    # FIX 5: link to application menu
    if menu_sys_id:
        payload["application"] = menu_sys_id
    if app_sys_id:
        payload["sys_scope"]   = app_sys_id
        payload["sys_package"] = app_sys_id
 
    response = safe_post(url, payload)
    return response.status_code == 201

# ─────────────────────────────────────────
# SCOPED APP FUNCTIONS
# ─────────────────────────────────────────
def create_scoped_app(app_name: str, app_scope: str, description: str = ""):
    app_url = f"{SNOW_BASE_URL}/sys_app"
    clean_scope = app_scope.lower().replace(" ", "_")[:18]

    app_payload = {
        "name": app_name,
        "scope": clean_scope,
        "short_description": description,
        "version": "1.0.0",
        "active": "true"
    }

    app_response = safe_post(app_url, app_payload)

    if app_response.status_code == 201:
        app_sys_id = app_response.json().get("result", {}).get("sys_id")
        print(f"  ✅ Scoped App '{app_name}' created! Sys_ID: {app_sys_id}")

        # Force scope lock
        force_user_scope(app_sys_id)

        time.sleep(3)  # Important buffer
        return True, app_sys_id
    else:
        print(f"❌ Failed to create scoped app: {app_response.text[:200]}")
        return False, None


def create_scoped_table(table_label: str, table_name: str, app_scope: str, app_sys_id: str):
    url = f"{SNOW_BASE_URL}/sys_db_object"
    if not table_name.startswith(app_scope):
        table_name = f"{app_scope}_{table_name}"

    if table_exists(table_name):
        print(f"    ℹ️  Table {table_name} already exists.")
        return True, None

    payload = {
        "label": table_label,
        "name": table_name,
        "create_access_controls": "false",
        "sys_scope": app_sys_id,
        "sys_package": app_sys_id
    }

    response = safe_post(url, payload)
    if response.status_code == 201:
        print(f"    ✅ Table '{table_name}' created.")
        return True, response.json().get("result", {}).get("sys_id")
    else:
        print(f"    ❌ Table creation failed: {response.text[:150]}")
        return False, None


def create_scoped_field(table_name: str, field_label: str, field_name: str, internal_type: str, app_sys_id: str):
    SUPPORTED_TYPES = ["string", "integer", "boolean", "glide_date"]
    if internal_type not in SUPPORTED_TYPES:
        return False

    url = f"{SNOW_BASE_URL}/sys_dictionary"
    if not field_name.startswith("u_"):
        field_name = f"u_{field_name}"

    payload = {
        "name": table_name,
        "column_label": field_label,
        "element": field_name,
        "internal_type": internal_type,
        "sys_scope": app_sys_id,
        "sys_package": app_sys_id
    }

    response = safe_post(url, payload)
    return response.status_code == 201


def create_scoped_role(role_name: str, description: str, app_scope: str, app_sys_id: str):
    url = f"{SNOW_BASE_URL}/sys_user_role"
    if app_scope and not role_name.startswith(app_scope):
        role_name = f"{app_scope}_{role_name}"

    payload = {
        "name": role_name,
        "description": description or f"Auto-generated scoped role: {role_name}",
        "sys_scope": app_sys_id,
        "sys_package": app_sys_id
    }

    response = safe_post(url, payload)
    if response.status_code == 201:
        return True, response.json().get("result", {}).get("sys_id")
    else:
        if response.status_code == 403:
            print(f"    ⚠️  Role creation blocked (403). Check API user permissions.")
        return False, None


def create_acl(table_name: str, operation: str, role_name: str, description: str, app_sys_id: str):
    url = f"{SNOW_BASE_URL}/sys_security_acl"
    VALID_OPERATIONS = ["read", "write", "create", "delete"]
    if operation.lower() not in VALID_OPERATIONS:
        return False

    payload = {
        "name": table_name,
        "operation": operation.lower(),
        "type": "record",
        "active": "true",
        "description": description or f"ACL for {operation} on {table_name}",
        "sys_scope": app_sys_id,
        "sys_package": app_sys_id
    }

    if role_name:
        role_id = get_role_sys_id(role_name)
        if role_id:
            payload["role"] = role_id

    response = safe_post(url, payload)
    if response.status_code == 201:
        return True
    elif response.status_code == 403:
        print(f"    ⚠️  ACL creation blocked (403). Requires security_admin role.")
        return False
    return False


def create_scoped_navigation(title: str, table_name: str, menu_sys_id: str, order: str, app_sys_id: str):
    url = f"{SNOW_BASE_URL}/sys_app_module"
    if not table_name.startswith("x_"):
        table_name = f"{table_name}"

    payload = {
        "title": title,
        "name": table_name,
        "active": "true",
        "order": str(order),
        "link_type": "LIST",
        "roles": "",
        "sys_scope": app_sys_id,
        "sys_package": app_sys_id
    }

    if menu_sys_id:
        payload["application"] = menu_sys_id

    response = safe_post(url, payload)
    if response.status_code == 201:
        print(f"    ✅ Navigation '{title}' created.")
        return True
    else:
        print(f"    ❌ Navigation failed: {response.text[:150]}")
        return False


# Keep other helper functions (non-scoped) as backup
def get_role_sys_id(role_name: str):
    url = f"{SNOW_BASE_URL}/sys_user_role?sysparm_query=name={role_name}&sysparm_fields=sys_id"
    response = safe_get(url)
    results = response.json().get("result", [])
    return results[0].get("sys_id") if results else None


# ─────────────────────────────────────────
# 7 NEW FUNCTIONS — ADD TO BOTTOM OF snow_client.py
# ─────────────────────────────────────────


def create_list_layout(table_name: str, columns: list, app_sys_id: str = None):
    """
    Creates a list layout (sys_ui_list) for a table.
    columns: list of field names to show as columns e.g. ["u_name", "u_status", "u_created_date"]
    """
    url = f"{SNOW_BASE_URL}/sys_ui_list"

    if not table_name.startswith(("u_", "x_")):
        table_name = f"u_{table_name}"

    payload = {
        "name":  table_name,
        "view":  "Default view",
        "title": f"{table_name} List"
    }
    if app_sys_id:
        payload["sys_scope"]   = app_sys_id
        payload["sys_package"] = app_sys_id

    response = safe_post(url, payload)
    if response.status_code != 201:
        print(f"    ❌ List layout failed ({response.status_code}): {response.text[:150]}")
        return False, None

    list_sys_id = response.json().get("result", {}).get("sys_id")
    time.sleep(0.3)

    # Add each column as a sys_ui_list_element
    for i, col in enumerate(columns):
        col_url     = f"{SNOW_BASE_URL}/sys_ui_list_element"
        col_payload = {
            "list_layout": list_sys_id,
            "element":     col,
            "position":    str(i)
        }
        if app_sys_id:
            col_payload["sys_scope"]   = app_sys_id
            col_payload["sys_package"] = app_sys_id
        safe_post(col_url, col_payload)
        time.sleep(0.2)

    print(f"    ✅ List layout '{table_name}' created with {len(columns)} columns.")
    return True, list_sys_id


def create_list_control(table_name: str, app_sys_id: str = None):
    """
    Creates a list control (sys_ui_list_control) for a table.
    Controls checkboxes, insert/delete buttons visibility on the list view.
    """
    url = f"{SNOW_BASE_URL}/sys_ui_list_control"

    if not table_name.startswith(("u_", "x_")):
        table_name = f"u_{table_name}"

    payload = {
        "name":              table_name,
        "view":              "Default view",
        "insert_btn":        "true",
        "delete_btn":        "true",
        "checkbox":          "true",
        "omit_search_arrow": "false"
    }
    if app_sys_id:
        payload["sys_scope"]   = app_sys_id
        payload["sys_package"] = app_sys_id

    response = safe_post(url, payload)
    if response.status_code == 201:
        print(f"    ✅ List control '{table_name}' created.")
        return True, response.json().get("result", {}).get("sys_id")

    print(f"    ❌ List control failed ({response.status_code}): {response.text[:150]}")
    return False, None


def create_client_script(
    table_name:   str,
    script_name:  str,
    script_type:  str,   # "onChange" | "onLoad" | "onSubmit" | "onCellEdit"
    field_name:   str,   # relevant for onChange
    script_body:  str,
    app_sys_id:   str = None
):
    """
    Creates a client script (sys_script_client) for a table.
    script_type: onChange | onLoad | onSubmit | onCellEdit
    """
    VALID_TYPES = {"onChange", "onLoad", "onSubmit", "onCellEdit"}
    if script_type not in VALID_TYPES:
        print(f"    ❌ Invalid client script type '{script_type}'. Must be one of {VALID_TYPES}")
        return False, None

    url = f"{SNOW_BASE_URL}/sys_script_client"

    if not table_name.startswith(("u_", "x_")):
        table_name = f"u_{table_name}"

    payload = {
        "name":       script_name,
        "table":      table_name,
        "type":       script_type,
        "field_name": field_name if script_type == "onChange" else "",
        "script":     script_body,
        "active":     "true",
        "global":     "false"
    }
    if app_sys_id:
        payload["sys_scope"]   = app_sys_id
        payload["sys_package"] = app_sys_id

    response = safe_post(url, payload)
    if response.status_code == 201:
        print(f"    ✅ Client script '{script_name}' ({script_type}) created.")
        return True, response.json().get("result", {}).get("sys_id")

    print(f"    ❌ Client script failed ({response.status_code}): {response.text[:150]}")
    return False, None


def create_script_include(
    name:        str,
    script_body: str,
    description: str = "",
    app_sys_id:  str = None
):
    """
    Creates a Script Include (sys_script_include) — reusable server-side logic.
    script_body should be a valid JS class definition e.g.:
        var VendorUtils = Class.create();
        VendorUtils.prototype = {
            initialize: function() {},
            getActiveVendors: function() { ... },
            type: 'VendorUtils'
        };
    """
    url = f"{SNOW_BASE_URL}/sys_script_include"

    payload = {
        "name":        name,
        "description": description or f"Auto-generated script include: {name}",
        "script":      script_body,
        "active":      "true",
        "access":      "public",
        "api_name":    name
    }
    if app_sys_id:
        payload["sys_scope"]   = app_sys_id
        payload["sys_package"] = app_sys_id

    response = safe_post(url, payload)
    if response.status_code == 201:
        print(f"    ✅ Script include '{name}' created.")
        return True, response.json().get("result", {}).get("sys_id")

    print(f"    ❌ Script include failed ({response.status_code}): {response.text[:150]}")
    return False, None


def create_system_property(
    name:        str,
    value:       str,
    description: str = "",
    prop_type:   str = "string",   # string | integer | boolean | choice
    app_sys_id:  str = None
):
    """
    Creates a System Property (sys_properties).
    name    : dot-notation e.g. "vendor.management.approval_required"
    value   : default value e.g. "true"
    prop_type: string | integer | boolean | choice
    """
    url = f"{SNOW_BASE_URL}/sys_properties"

    payload = {
        "name":        name,
        "value":       value,
        "description": description or f"Auto-generated property: {name}",
        "type":        prop_type,
        "private":     "false",
        "read_roles":  "",
        "write_roles": "admin"
    }
    if app_sys_id:
        payload["sys_scope"]   = app_sys_id
        payload["sys_package"] = app_sys_id

    response = safe_post(url, payload)
    if response.status_code == 201:
        print(f"    ✅ System property '{name}' = '{value}' created.")
        return True, response.json().get("result", {}).get("sys_id")

    print(f"    ❌ System property failed ({response.status_code}): {response.text[:150]}")
    return False, None


def create_relationship(
    name:         str,
    parent_table: str,
    child_table:  str,
    query_with:   str = "",   # field on child that points to parent e.g. "u_vendor"
    app_sys_id:   str = None
):
    """
    Creates a table relationship (sys_relationship).
    parent_table : e.g. "u_vendor"
    child_table  : e.g. "u_vendor_contract"
    query_with   : field on child that references parent e.g. "u_vendor_id"
    """
    url = f"{SNOW_BASE_URL}/sys_relationship"

    if not parent_table.startswith(("u_", "x_")):
        parent_table = f"u_{parent_table}"
    if not child_table.startswith(("u_", "x_")):
        child_table = f"u_{child_table}"

    payload = {
        "name":         name,
        "parent_table": parent_table,
        "child_table":  child_table,
        "query_with":   query_with,
        "active":       "true"
    }
    if app_sys_id:
        payload["sys_scope"]   = app_sys_id
        payload["sys_package"] = app_sys_id

    response = safe_post(url, payload)
    if response.status_code == 201:
        print(f"    ✅ Relationship '{name}' ({parent_table} → {child_table}) created.")
        return True, response.json().get("result", {}).get("sys_id")

    print(f"    ❌ Relationship failed ({response.status_code}): {response.text[:150]}")
    return False, None


def create_related_list(
    parent_table: str,
    child_table:  str,
    ref_field:    str,   # field on child_table that references parent e.g. "u_vendor"
    title:        str = "",
    app_sys_id:   str = None
):
    """
    Creates a Related List (sys_ui_related_list) so child records appear
    on the parent record's form automatically.
    parent_table : table whose form shows the related list e.g. "u_vendor"
    child_table  : table whose records appear in the list e.g. "u_vendor_contract"
    ref_field    : field on child_table that points back to parent e.g. "u_vendor_id"
    """
    url = f"{SNOW_BASE_URL}/sys_ui_related_list"

    if not parent_table.startswith(("u_", "x_")):
        parent_table = f"u_{parent_table}"
    if not child_table.startswith(("u_", "x_")):
        child_table = f"u_{child_table}"

    payload = {
        "name":      parent_table,
        "related":   f"{child_table}.{ref_field}",
        "title":     title or f"{child_table} List",
        "view":      "Default view",
        "read_only": "false"
    }
    if app_sys_id:
        payload["sys_scope"]   = app_sys_id
        payload["sys_package"] = app_sys_id

    response = safe_post(url, payload)
    if response.status_code == 201:
        print(f"    ✅ Related list '{child_table}' on '{parent_table}' created.")
        return True, response.json().get("result", {}).get("sys_id")

    print(f"    ❌ Related list failed ({response.status_code}): {response.text[:150]}")
    return False, None