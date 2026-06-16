# debt_snow_scanner.py

import re
from datetime import datetime, timedelta
from snow_client import safe_get, SNOW_BASE_URL
 
# ─────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────
 
# Records older than this are flagged as stale
STALE_THRESHOLD_DAYS = 730  # 2 years
 
# Fields to pull for every script-type record
SCRIPT_FIELDS = "sys_id,name,active,script,sys_updated_on,sys_updated_by,description"
 
# Fields for non-script records (flows, catalog items, UI policies)
META_FIELDS = "sys_id,name,active,sys_updated_on,sys_updated_by,description"
 
 
# ─────────────────────────────────────────
# HELPER: STALE DATE CHECK
# ─────────────────────────────────────────
 
def _is_stale(updated_on_str: str) -> bool:
    """Returns True if the record hasn't been updated in 2+ years."""
    if not updated_on_str:
        return True
    try:
        # ServiceNow format: "2021-04-15 10:32:00"
        updated_on = datetime.strptime(updated_on_str[:19], "%Y-%m-%d %H:%M:%S")
        return datetime.utcnow() - updated_on > timedelta(days=STALE_THRESHOLD_DAYS)
    except Exception:
        return False
 
 
# ─────────────────────────────────────────
# HELPER: APPLY BASIC RULE CHECKS
# Runs BEFORE AI — fast, no API cost
# ─────────────────────────────────────────
 
def apply_basic_rules(record: dict, table_source: str) -> list:
    """
    Applies pattern-based rules to a ServiceNow record.
    Returns a list of flag strings describing detected issues.
    These are pre-AI checks — quick and free.
    """
    flags = []
    script = record.get("script", "") or ""
    active = record.get("active", "true")
    updated_on = record.get("sys_updated_on", "")
 
    # FLAG 1: Inactive record
    if str(active).lower() in ("false", "0", ""):
        flags.append("inactive")
 
    # FLAG 2: Stale record (2+ years old)
    if _is_stale(updated_on):
        flags.append("stale_2yr")
 
    # FLAG 3: gs.sleep() — performance risk
    if "gs.sleep" in script:
        flags.append("gs_sleep_detected")
 
    # FLAG 4: Hardcoded sys_id pattern (32-char hex strings)
    hardcoded_sysid = re.findall(r'["\']([0-9a-f]{32})["\']', script)
    if hardcoded_sysid:
        flags.append(f"hardcoded_sysid({len(hardcoded_sysid)})")
 
    # FLAG 5: Deprecated APIs
    deprecated_patterns = [
        ("gs.getUser().getID()", "deprecated_gs_getUser"),
        ("getParameter(",        "deprecated_getParameter"),
        ("GlideAjax",            "glide_ajax_usage"),
        ("eval(",                "eval_usage_security_risk"),
        ("new GlideRecord",      "gliderecord_in_script"),
    ]
    for pattern, flag_name in deprecated_patterns:
        if pattern in script:
            flags.append(flag_name)
 
    # FLAG 6: No description (maintainability)
    desc = record.get("description", "") or ""
    if not desc.strip():
        flags.append("no_description")
 
    return flags
 
 
# ─────────────────────────────────────────
# SCANNER: BUSINESS RULES (sys_script)
# ─────────────────────────────────────────
 
def scan_business_rules(limit: int = 100) -> list:
    print(f"\n  🔍 Scanning Business Rules (sys_script) — limit: {limit}")
    url = (
        f"{SNOW_BASE_URL}/sys_script"
        f"?sysparm_fields={SCRIPT_FIELDS},table_name,when,action_insert,action_update"
        f"&sysparm_limit={limit}"
        f"&sysparm_exclude_reference_link=true"
    )
    response = safe_get(url)
    if response.status_code != 200:
        print(f"  ❌ Failed to scan sys_script: {response.status_code}")
        return []
 
    records = response.json().get("result", [])
    print(f"  ✅ Fetched {len(records)} business rules")
 
    results = []
    for r in records:
        results.append({
            "sys_id":       r.get("sys_id"),
            "name":         r.get("name"),
            "table_source": "sys_script",
            "label":        "Business Rule",
            "active":       r.get("active"),
            "last_updated": r.get("sys_updated_on"),
            "updated_by":   r.get("sys_updated_by"),
            "description":  r.get("description"),
            "script":       r.get("script"),
            "extra": {
                "target_table": r.get("table_name"),
                "when":         r.get("when"),
                "on_insert":    r.get("action_insert"),
                "on_update":    r.get("action_update"),
            },
            "basic_flags": apply_basic_rules(r, "sys_script")
        })
    return results
 
 
# ─────────────────────────────────────────
# SCANNER: SCRIPT INCLUDES (sys_script_include)
# ─────────────────────────────────────────
 
def scan_script_includes(limit: int = 100) -> list:
    print(f"\n  🔍 Scanning Script Includes (sys_script_include) — limit: {limit}")
    url = (
        f"{SNOW_BASE_URL}/sys_script_include"
        f"?sysparm_fields={SCRIPT_FIELDS},client_callable,api_name"
        f"&sysparm_limit={limit}"
        f"&sysparm_exclude_reference_link=true"
    )
    response = safe_get(url)
    if response.status_code != 200:
        print(f"  ❌ Failed to scan sys_script_include: {response.status_code}")
        return []
 
    records = response.json().get("result", [])
    print(f"  ✅ Fetched {len(records)} script includes")
 
    results = []
    for r in records:
        results.append({
            "sys_id":       r.get("sys_id"),
            "name":         r.get("name"),
            "table_source": "sys_script_include",
            "label":        "Script Include",
            "active":       r.get("active"),
            "last_updated": r.get("sys_updated_on"),
            "updated_by":   r.get("sys_updated_by"),
            "description":  r.get("description"),
            "script":       r.get("script"),
            "extra": {
                "client_callable": r.get("client_callable"),
                "api_name":        r.get("api_name"),
            },
            "basic_flags": apply_basic_rules(r, "sys_script_include")
        })
    return results
 
 
# ─────────────────────────────────────────
# SCANNER: CLIENT SCRIPTS (sys_script_client)
# ─────────────────────────────────────────
 
def scan_client_scripts(limit: int = 100) -> list:
    print(f"\n  🔍 Scanning Client Scripts (sys_script_client) — limit: {limit}")
    url = (
        f"{SNOW_BASE_URL}/sys_script_client"
        f"?sysparm_fields={SCRIPT_FIELDS},table_name,type"
        f"&sysparm_limit={limit}"
        f"&sysparm_exclude_reference_link=true"
    )
    response = safe_get(url)
    if response.status_code != 200:
        print(f"  ❌ Failed to scan sys_script_client: {response.status_code}")
        return []
 
    records = response.json().get("result", [])
    print(f"  ✅ Fetched {len(records)} client scripts")
 
    results = []
    for r in records:
        results.append({
            "sys_id":       r.get("sys_id"),
            "name":         r.get("name"),
            "table_source": "sys_script_client",
            "label":        "Client Script",
            "active":       r.get("active"),
            "last_updated": r.get("sys_updated_on"),
            "updated_by":   r.get("sys_updated_by"),
            "description":  r.get("description"),
            "script":       r.get("script"),
            "extra": {
                "target_table": r.get("table_name"),
                "script_type":  r.get("type"),
            },
            "basic_flags": apply_basic_rules(r, "sys_script_client")
        })
    return results
 
 
# ─────────────────────────────────────────
# SCANNER: FLOWS (sys_hub_flow)
# ─────────────────────────────────────────
 
def scan_flows(limit: int = 100) -> list:
    print(f"\n  🔍 Scanning Flows (sys_hub_flow) — limit: {limit}")
    url = (
        f"{SNOW_BASE_URL}/sys_hub_flow"
        f"?sysparm_fields={META_FIELDS},internal_name,run_as"
        f"&sysparm_limit={limit}"
        f"&sysparm_exclude_reference_link=true"
    )
    response = safe_get(url)
    if response.status_code != 200:
        print(f"  ❌ Failed to scan sys_hub_flow: {response.status_code}")
        return []
 
    records = response.json().get("result", [])
    print(f"  ✅ Fetched {len(records)} flows")
 
    results = []
    for r in records:
        pseudo_record = {**r, "script": r.get("description", "")}
        results.append({
            "sys_id":       r.get("sys_id"),
            "name":         r.get("name"),
            "table_source": "sys_hub_flow",
            "label":        "Flow Designer Flow",
            "active":       r.get("active"),
            "last_updated": r.get("sys_updated_on"),
            "updated_by":   r.get("sys_updated_by"),
            "description":  r.get("description"),
            "script":       None,
            "extra": {
                "internal_name": r.get("internal_name"),
                "run_as":        r.get("run_as"),
            },
            "basic_flags": apply_basic_rules(pseudo_record, "sys_hub_flow")
        })
    return results
 
 
# ─────────────────────────────────────────
# SCANNER: LEGACY WORKFLOWS (wf_workflow)
# ─────────────────────────────────────────
 
def scan_workflows(limit: int = 100) -> list:
    print(f"\n  🔍 Scanning Legacy Workflows (wf_workflow) — limit: {limit}")
    url = (
        f"{SNOW_BASE_URL}/wf_workflow"
        f"?sysparm_fields={META_FIELDS},table,checked_out"
        f"&sysparm_limit={limit}"
        f"&sysparm_exclude_reference_link=true"
    )
    response = safe_get(url)
    if response.status_code != 200:
        print(f"  ❌ Failed to scan wf_workflow: {response.status_code}")
        return []
 
    records = response.json().get("result", [])
    print(f"  ✅ Fetched {len(records)} legacy workflows")
 
    results = []
    for r in records:
        pseudo_record = {**r, "script": ""}
        flags = apply_basic_rules(pseudo_record, "wf_workflow")
        flags.append("legacy_workflow_migrate_to_flow")
 
        results.append({
            "sys_id":       r.get("sys_id"),
            "name":         r.get("name"),
            "table_source": "wf_workflow",
            "label":        "Legacy Workflow",
            "active":       r.get("active"),
            "last_updated": r.get("sys_updated_on"),
            "updated_by":   r.get("sys_updated_by"),
            "description":  r.get("description"),
            "script":       None,
            "extra": {
                "target_table": r.get("table"),
                "checked_out":  r.get("checked_out"),
            },
            "basic_flags": flags
        })
    return results
 
 
# ─────────────────────────────────────────
# SCANNER: CATALOG ITEMS (sc_cat_item)
# ─────────────────────────────────────────
 
def scan_catalog_items(limit: int = 100) -> list:
    print(f"\n  🔍 Scanning Catalog Items (sc_cat_item) — limit: {limit}")
    url = (
        f"{SNOW_BASE_URL}/sc_cat_item"
        f"?sysparm_fields=sys_id,name,active,sys_updated_on,sys_updated_by,short_description,category,sc_catalogs"
        f"&sysparm_limit={limit}"
        f"&sysparm_exclude_reference_link=true"
    )
    response = safe_get(url)
    if response.status_code != 200:
        print(f"  ❌ Failed to scan sc_cat_item: {response.status_code}")
        return []
 
    records = response.json().get("result", [])
    print(f"  ✅ Fetched {len(records)} catalog items")
 
    results = []
    for r in records:
        pseudo_record = {
            **r,
            "script":      "",
            "description": r.get("short_description", "")
        }
        results.append({
            "sys_id":       r.get("sys_id"),
            "name":         r.get("name"),
            "table_source": "sc_cat_item",
            "label":        "Catalog Item",
            "active":       r.get("active"),
            "last_updated": r.get("sys_updated_on"),
            "updated_by":   r.get("sys_updated_by"),
            "description":  r.get("short_description"),
            "script":       None,
            "extra": {
                "category":    r.get("category"),
                "sc_catalogs": r.get("sc_catalogs"),
            },
            "basic_flags": apply_basic_rules(pseudo_record, "sc_cat_item")
        })
    return results
 
 
# ─────────────────────────────────────────
# SCANNER: UI POLICIES (sys_ui_policy)
# ─────────────────────────────────────────
 
def scan_ui_policies(limit: int = 100) -> list:
    print(f"\n  🔍 Scanning UI Policies (sys_ui_policy) — limit: {limit}")
    url = (
        f"{SNOW_BASE_URL}/sys_ui_policy"
        f"?sysparm_fields=sys_id,short_description,active,sys_updated_on,sys_updated_by,table_name,conditions"
        f"&sysparm_limit={limit}"
        f"&sysparm_exclude_reference_link=true"
    )
    response = safe_get(url)
    if response.status_code != 200:
        print(f"  ❌ Failed to scan sys_ui_policy: {response.status_code}")
        return []
 
    records = response.json().get("result", [])
    print(f"  ✅ Fetched {len(records)} UI policies")
 
    results = []
    for r in records:
        pseudo_record = {
            **r,
            "script":      "",
            "name":        r.get("short_description", ""),
            "description": r.get("conditions", "")
        }
        results.append({
            "sys_id":       r.get("sys_id"),
            "name":         r.get("short_description") or "(no description)",
            "table_source": "sys_ui_policy",
            "label":        "UI Policy",
            "active":       r.get("active"),
            "last_updated": r.get("sys_updated_on"),
            "updated_by":   r.get("sys_updated_by"),
            "description":  r.get("conditions"),
            "script":       None,
            "extra": {
                "target_table": r.get("table_name"),
                "conditions":   r.get("conditions"),
            },
            "basic_flags": apply_basic_rules(pseudo_record, "sys_ui_policy")
        })
    return results
 
 
# ─────────────────────────────────────────
# SCANNER MAP + MASTER ENTRY POINT
# ─────────────────────────────────────────
 
SCANNER_MAP = {
    "sys_script":         scan_business_rules,
    "sys_script_include": scan_script_includes,
    "sys_script_client":  scan_client_scripts,
    "sys_hub_flow":       scan_flows,
    "wf_workflow":        scan_workflows,
    "sc_cat_item":        scan_catalog_items,
    "sys_ui_policy":      scan_ui_policies,
}
 
def run_scan(tables: list, limit: int = 100) -> list:
    """
    Entry point: runs scanners for the requested tables.
    Returns a flat list of all scanned records with basic_flags attached.
 
    Args:
        tables: list of ServiceNow table names to scan
                e.g. ["sys_script", "sys_script_include"]
        limit:  max records per table (sysparm_limit)
 
    Returns:
        list of dicts — each dict is one scanned record
    """
    print("\n" + "="*60)
    print(f"🔍 TECHNICAL DEBT SCAN STARTED")
    print(f"   Tables: {tables}")
    print(f"   Limit per table: {limit}")
    print("="*60)
 
    all_records = []
 
    for table in tables:
        scanner_fn = SCANNER_MAP.get(table)
        if not scanner_fn:
            print(f"  ⚠️  No scanner registered for table: {table} — skipping")
            continue
        records = scanner_fn(limit=limit)
        all_records.extend(records)
 
    print(f"\n✅ Total records fetched: {len(all_records)}")
    return all_records

# ─────────────────────────────────────────────────────────────────────────────
# STEP 1: ADD THIS FUNCTION TO debt_snow_scanner.py  (at the bottom)
# ─────────────────────────────────────────────────────────────────────────────
 
# Tables where deactivation is NEVER allowed — safety guard
DEACTIVATE_BLOCKED_TABLES = {
    "sys_security_acl",   # ACLs — security risk
    "sys_dictionary",     # Fields — breaks forms
    "sys_db_object",      # Tables — breaks entire app
    "sys_properties",     # System properties — instance-wide impact
}
 
def deactivate_record(table: str, sys_id: str) -> dict:
    """
    Safely sets active = false on a single ServiceNow record.
    Uses PATCH — only updates the active field, nothing else.
    Never touches blocked tables.
 
    Args:
        table:  ServiceNow table name  e.g. "sys_script"
        sys_id: Record sys_id          e.g. "abc123..."
 
    Returns:
        dict with keys: success (bool), message (str), updated_record (dict)
    """
    # ── Safety guard ──────────────────────────────
    if table in DEACTIVATE_BLOCKED_TABLES:
        return {
            "success": False,
            "message": f"Deactivation blocked for table '{table}' — protected table.",
            "updated_record": {}
        }
 
    if not sys_id or len(sys_id) != 32:
        return {
            "success": False,
            "message": "Invalid sys_id provided.",
            "updated_record": {}
        }
 
    url = f"{SNOW_BASE_URL}/{table}/{sys_id}"
    payload = {"active": "false"}
 
    try:
        from snow_client import session
        response = session.patch(url, json=payload, timeout=30)
 
        if response.status_code == 200:
            record = response.json().get("result", {})
            print(f"  ✅ Deactivated: {table}/{sys_id}")
            return {
                "success": True,
                "message": f"Record successfully deactivated in {table}.",
                "updated_record": {
                    "sys_id":     record.get("sys_id"),
                    "name":       record.get("name") or record.get("short_description", ""),
                    "active":     record.get("active"),
                    "updated_on": record.get("sys_updated_on"),
                }
            }
        elif response.status_code == 403:
            return {
                "success": False,
                "message": "Permission denied. API user lacks write access to this table.",
                "updated_record": {}
            }
        elif response.status_code == 404:
            return {
                "success": False,
                "message": f"Record not found: {sys_id} in {table}.",
                "updated_record": {}
            }
        else:
            return {
                "success": False,
                "message": f"ServiceNow returned {response.status_code}: {response.text[:200]}",
                "updated_record": {}
            }
 
    except Exception as e:
        print(f"  ❌ Deactivate error: {e}")
        return {
            "success": False,
            "message": f"Request failed: {str(e)}",
            "updated_record": {}
        }