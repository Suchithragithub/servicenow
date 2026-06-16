# integration_scanner.py

import re
from datetime import datetime, timedelta
from snow_client import safe_get, SNOW_BASE_URL
 
# ─────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────
 
STALE_THRESHOLD_DAYS = 730  # 2 years = stale
 
# Base fields for every record
BASE_FIELDS = "sys_id,name,active,sys_updated_on,sys_updated_by,description"
 
 
# ─────────────────────────────────────────
# HELPER: STALE CHECK
# ─────────────────────────────────────────
 
def _is_stale(updated_on_str: str) -> bool:
    if not updated_on_str:
        return True
    try:
        updated_on = datetime.strptime(updated_on_str[:19], "%Y-%m-%d %H:%M:%S")
        return datetime.utcnow() - updated_on > timedelta(days=STALE_THRESHOLD_DAYS)
    except Exception:
        return False
 
 
# ─────────────────────────────────────────
# HELPER: BASIC RULE CHECKS
# Applied before AI — free, instant flags
# ─────────────────────────────────────────
 
def apply_integration_rules(record: dict, table_source: str) -> list:
    """
    Applies pattern-based rules to detect outdated integration patterns.
    Returns list of flag strings — runs before AI to save cost.
    """
    flags = []
    script  = record.get("script", "")  or ""
    name    = record.get("name", "")    or ""
    desc    = record.get("description","") or ""
    active  = record.get("active", "true")
    updated = record.get("sys_updated_on", "")
 
    # FLAG: Inactive record
    if str(active).lower() in ("false", "0", ""):
        flags.append("inactive")
 
    # FLAG: Stale record
    if _is_stale(updated):
        flags.append("stale_2yr")
 
    # FLAG: Hardcoded credentials in script
    cred_patterns = ["password", "passwd", "secret", "apikey", "api_key",
                     "Authorization", "token =", "Bearer "]
    for p in cred_patterns:
        if p.lower() in script.lower():
            flags.append("hardcoded_credential_risk")
            break
 
    # FLAG: Hardcoded URLs
    if re.search(r'https?://[a-zA-Z0-9._/-]{10,}', script):
        flags.append("hardcoded_url")
 
    # FLAG: Basic Auth usage
    if "basic" in script.lower() or "btoa(" in script or "base64" in script.lower():
        flags.append("basic_auth_detected")
 
    # FLAG: SOAP/XML legacy patterns
    if any(p in script for p in ["<soap:", "SOAP", "wsdl", "xmlns", "<?xml"]):
        flags.append("soap_xml_legacy")
 
    # FLAG: Email-based integration patterns
    if any(p in script.lower() for p in ["gs.sendmail", "email", "smtp", "mailbox"]):
        flags.append("email_based_integration")
 
    # FLAG: No error handling
    if script and "try" not in script and "catch" not in script:
        flags.append("no_error_handling")
 
    # FLAG: No retry logic
    if script and "retry" not in script.lower() and "attempt" not in script.lower():
        flags.append("no_retry_logic")
 
    # FLAG: No logging
    if script and "gs.log" not in script and "gs.info" not in script \
               and "gs.warn" not in script and "gs.error" not in script:
        flags.append("no_logging")
 
    # FLAG: Hardcoded sys_id (32-char hex)
    if re.findall(r'["\']([0-9a-f]{32})["\']', script):
        flags.append("hardcoded_sysid")
 
    # FLAG: No description
    if not desc.strip():
        flags.append("no_description")
 
    # FLAG: gs.sleep performance
    if "gs.sleep" in script:
        flags.append("gs_sleep_detected")
 
    return flags
 
 
# ─────────────────────────────────────────
# MODERNIZATION SCORE (pre-AI)
# ─────────────────────────────────────────
 
def calculate_pre_score(flags: list, table_source: str) -> int:
    """
    Calculates a quick modernization score (0-100) before AI runs.
    Higher = more modern.
    This gets refined by the AI score later.
    """
    score = 100
 
    deductions = {
        "soap_xml_legacy":          30,
        "email_based_integration":  25,
        "hardcoded_credential_risk":25,
        "basic_auth_detected":      15,
        "hardcoded_url":            15,
        "no_error_handling":        15,
        "no_retry_logic":           10,
        "no_logging":               10,
        "stale_2yr":                10,
        "hardcoded_sysid":          10,
        "inactive":                  5,
        "gs_sleep_detected":        10,
        "no_description":            5,
    }
 
    for flag in flags:
        clean = flag.split("(")[0]
        score -= deductions.get(clean, 0)
 
    # Scheduled jobs calling APIs are inherently less modern
    if table_source == "sys_trigger":
        score -= 15
 
    # SOAP messages are always legacy
    if table_source == "sys_soap_message":
        score -= 20
 
    return max(0, min(100, score))
 
 
# ─────────────────────────────────────────
# SCANNER: REST MESSAGES (sys_rest_message)
# ─────────────────────────────────────────
 
def scan_rest_messages(limit: int = 50) -> list:
    """
    Scans sys_rest_message — existing REST integrations.
    Also fetches child endpoints from sys_rest_message_fn.
    """
    print(f"\n  🔍 Scanning REST Messages (sys_rest_message) — limit: {limit}")
    url = (
        f"{SNOW_BASE_URL}/sys_rest_message"
        f"?sysparm_fields={BASE_FIELDS},rest_endpoint,authentication_type"
        f"&sysparm_limit={limit}"
        f"&sysparm_exclude_reference_link=true"
    )
    response = safe_get(url)
    if response.status_code != 200:
        print(f"  ❌ Failed: {response.status_code}")
        return []
 
    records = response.json().get("result", [])
    print(f"  ✅ Fetched {len(records)} REST messages")
 
    results = []
    for r in records:
        # Build a pseudo script from endpoint + auth info for rule checks
        pseudo_script = f"{r.get('rest_endpoint','')} {r.get('authentication_type','')}"
        pseudo_record = {**r, "script": pseudo_script}
        flags = apply_integration_rules(pseudo_record, "sys_rest_message")
 
        # Flag Basic Auth specifically from auth_type field
        auth_type = str(r.get("authentication_type", "")).lower()
        if auth_type in ("basic", "basic_auth") and "basic_auth_detected" not in flags:
            flags.append("basic_auth_detected")
        if auth_type == "no_authentication":
            flags.append("no_authentication")
 
        results.append({
            "sys_id":       r.get("sys_id"),
            "name":         r.get("name"),
            "table_source": "sys_rest_message",
            "label":        "REST Message",
            "active":       r.get("active"),
            "last_updated": r.get("sys_updated_on"),
            "updated_by":   r.get("sys_updated_by"),
            "description":  r.get("description"),
            "script":       None,
            "extra": {
                "endpoint":    r.get("rest_endpoint"),
                "auth_type":   r.get("authentication_type"),
            },
            "basic_flags":        flags,
            "pre_score":          calculate_pre_score(flags, "sys_rest_message"),
        })
    return results
 
 
# ─────────────────────────────────────────
# SCANNER: SOAP MESSAGES (sys_soap_message)
# ─────────────────────────────────────────
 
def scan_soap_messages(limit: int = 50) -> list:
    """
    Scans sys_soap_message — legacy SOAP/XML integrations.
    All SOAP is considered legacy — always flagged for modernization.
    """
    print(f"\n  🔍 Scanning SOAP Messages (sys_soap_message) — limit: {limit}")
    url = (
        f"{SNOW_BASE_URL}/sys_soap_message"
        f"?sysparm_fields={BASE_FIELDS},wsdl_url,authentication_type"
        f"&sysparm_limit={limit}"
        f"&sysparm_exclude_reference_link=true"
    )
    response = safe_get(url)
    if response.status_code != 200:
        print(f"  ❌ Failed: {response.status_code}")
        return []
 
    records = response.json().get("result", [])
    print(f"  ✅ Fetched {len(records)} SOAP messages")
 
    results = []
    for r in records:
        pseudo_record = {**r, "script": f"SOAP {r.get('wsdl_url','')}"}
        flags = apply_integration_rules(pseudo_record, "sys_soap_message")
        # All SOAP is legacy
        if "soap_xml_legacy" not in flags:
            flags.append("soap_xml_legacy")
 
        results.append({
            "sys_id":       r.get("sys_id"),
            "name":         r.get("name"),
            "table_source": "sys_soap_message",
            "label":        "SOAP Message",
            "active":       r.get("active"),
            "last_updated": r.get("sys_updated_on"),
            "updated_by":   r.get("sys_updated_by"),
            "description":  r.get("description"),
            "script":       None,
            "extra": {
                "wsdl_url":  r.get("wsdl_url"),
                "auth_type": r.get("authentication_type"),
            },
            "basic_flags":        flags,
            "pre_score":          calculate_pre_score(flags, "sys_soap_message"),
        })
    return results
 
 
# ─────────────────────────────────────────
# SCANNER: SCRIPT INCLUDES (sys_script_include)
# Filters only those with REST/API patterns
# ─────────────────────────────────────────
 
def scan_integration_scripts(limit: int = 50) -> list:
    """
    Scans sys_script_include for scripts that contain
    REST/HTTP/API patterns — these are custom integration scripts.
    """
    print(f"\n  🔍 Scanning Integration Script Includes (sys_script_include) — limit: {limit}")
    url = (
        f"{SNOW_BASE_URL}/sys_script_include"
        f"?sysparm_fields={BASE_FIELDS},script,client_callable,api_name"
        f"&sysparm_limit={limit}"
        f"&sysparm_exclude_reference_link=true"
    )
    response = safe_get(url)
    if response.status_code != 200:
        print(f"  ❌ Failed: {response.status_code}")
        return []
 
    all_records = response.json().get("result", [])
 
    # Filter: only keep scripts that look like integration code
    integration_keywords = [
        "RESTMessage", "SOAPMessage", "GlideHTTPRequest",
        "http", "https", "endpoint", "api", "webhook",
        "request", "response", "payload", "json.parse",
        "XMLDocument", "wsdl"
    ]
    integration_records = [
        r for r in all_records
        if any(kw.lower() in (r.get("script") or "").lower()
               for kw in integration_keywords)
    ]
 
    print(f"  ✅ {len(all_records)} total → {len(integration_records)} integration scripts")
 
    results = []
    for r in integration_records:
        flags = apply_integration_rules(r, "sys_script_include")
 
        results.append({
            "sys_id":       r.get("sys_id"),
            "name":         r.get("name"),
            "table_source": "sys_script_include",
            "label":        "Integration Script",
            "active":       r.get("active"),
            "last_updated": r.get("sys_updated_on"),
            "updated_by":   r.get("sys_updated_by"),
            "description":  r.get("description"),
            "script":       r.get("script"),
            "extra": {
                "client_callable": r.get("client_callable"),
                "api_name":        r.get("api_name"),
            },
            "basic_flags":        flags,
            "pre_score":          calculate_pre_score(flags, "sys_script_include"),
        })
    return results
 
 
# ─────────────────────────────────────────
# SCANNER: SCHEDULED JOBS (sys_trigger)
# Filters only those with API/integration patterns
# ─────────────────────────────────────────
 
def scan_scheduled_jobs(limit: int = 50) -> list:
    """
    Scans sys_trigger (Scheduled Jobs).
    Scheduled jobs that call external APIs are prime
    modernization candidates — should be event-driven flows.
    """
    print(f"\n  🔍 Scanning Scheduled Jobs (sys_trigger) — limit: {limit}")
    url = (
        f"{SNOW_BASE_URL}/sys_trigger"
        f"?sysparm_fields={BASE_FIELDS},script,run_type,run_period"
        f"&sysparm_limit={limit}"
        f"&sysparm_exclude_reference_link=true"
    )
    response = safe_get(url)
    if response.status_code != 200:
        print(f"  ❌ Failed: {response.status_code}")
        return []
 
    all_records = response.json().get("result", [])
 
    # Filter: only jobs that have integration-related code
    integration_keywords = [
        "RESTMessage", "http", "https", "endpoint",
        "api", "webhook", "SOAPMessage", "GlideHTTPRequest",
        "email", "sendmail", "smtp"
    ]
    integration_records = [
        r for r in all_records
        if any(kw.lower() in (r.get("script") or "").lower()
               for kw in integration_keywords)
    ]
 
    print(f"  ✅ {len(all_records)} total → {len(integration_records)} integration jobs")
 
    results = []
    for r in integration_records:
        flags = apply_integration_rules(r, "sys_trigger")
        # All scheduled API callers should be event-driven
        flags.append("should_be_event_driven")
 
        results.append({
            "sys_id":       r.get("sys_id"),
            "name":         r.get("name"),
            "table_source": "sys_trigger",
            "label":        "Scheduled Job",
            "active":       r.get("active"),
            "last_updated": r.get("sys_updated_on"),
            "updated_by":   r.get("sys_updated_by"),
            "description":  r.get("description"),
            "script":       r.get("script"),
            "extra": {
                "run_type":   r.get("run_type"),
                "run_period": r.get("run_period"),
            },
            "basic_flags":        flags,
            "pre_score":          calculate_pre_score(flags, "sys_trigger"),
        })
    return results
 
 
# ─────────────────────────────────────────
# SCANNER: AUTH PROFILES (sys_auth_profile)
# ─────────────────────────────────────────
 
def scan_auth_profiles(limit: int = 50) -> list:
    """
    Scans sys_auth_profile — credential/auth configurations.
    Basic Auth profiles are upgrade candidates to OAuth2.
    """
    print(f"\n  🔍 Scanning Auth Profiles (sys_auth_profile) — limit: {limit}")
    url = (
        f"{SNOW_BASE_URL}/sys_auth_profile"
        f"?sysparm_fields={BASE_FIELDS},type"
        f"&sysparm_limit={limit}"
        f"&sysparm_exclude_reference_link=true"
    )
    response = safe_get(url)
    if response.status_code != 200:
        print(f"  ❌ Failed: {response.status_code}")
        return []
 
    records = response.json().get("result", [])
    print(f"  ✅ Fetched {len(records)} auth profiles")
 
    results = []
    for r in records:
        pseudo_record = {**r, "script": str(r.get("type", ""))}
        flags = apply_integration_rules(pseudo_record, "sys_auth_profile")
 
        auth_type = str(r.get("type", "")).lower()
        if "basic" in auth_type:
            if "basic_auth_detected" not in flags:
                flags.append("basic_auth_detected")
            flags.append("upgrade_to_oauth2")
        elif "oauth" in auth_type or "oauth2" in auth_type:
            flags.append("already_oauth2")   # good — modern
 
        results.append({
            "sys_id":       r.get("sys_id"),
            "name":         r.get("name"),
            "table_source": "sys_auth_profile",
            "label":        "Auth Profile",
            "active":       r.get("active"),
            "last_updated": r.get("sys_updated_on"),
            "updated_by":   r.get("sys_updated_by"),
            "description":  r.get("description"),
            "script":       None,
            "extra": {
                "auth_type": r.get("type"),
            },
            "basic_flags":        flags,
            "pre_score":          calculate_pre_score(flags, "sys_auth_profile"),
        })
    return results
 
 
# ─────────────────────────────────────────
# AVAILABLE TABLES (for React selector)
# ─────────────────────────────────────────
 
INTEGRATION_SCANNER_MAP = {
    "sys_rest_message":    scan_rest_messages,
    "sys_soap_message":    scan_soap_messages,
    "sys_script_include":  scan_integration_scripts,
    "sys_trigger":         scan_scheduled_jobs,
    "sys_auth_profile":    scan_auth_profiles,
}
 
AVAILABLE_INTEGRATION_TABLES = [
    {"table": "sys_rest_message",   "label": "REST Messages",         "description": "Existing REST integrations"},
    {"table": "sys_soap_message",   "label": "SOAP Messages",         "description": "Legacy SOAP/XML integrations"},
    {"table": "sys_script_include", "label": "Integration Scripts",   "description": "Script includes with API logic"},
    {"table": "sys_trigger",        "label": "Scheduled Jobs",        "description": "Jobs calling external APIs"},
    {"table": "sys_auth_profile",   "label": "Auth Profiles",         "description": "Credential configurations"},
]
 
 
def run_integration_scan(tables: list, limit: int = 50) -> list:
    """
    Entry point: runs scanners for the requested integration tables.
 
    Args:
        tables: list of table names to scan
        limit:  max records per table
 
    Returns:
        flat list of all scanned records with basic_flags and pre_score
    """
    print("\n" + "="*60)
    print("🔍 INTEGRATION MODERNIZATION SCAN STARTED")
    print(f"   Tables: {tables} | Limit: {limit}")
    print("="*60)
 
    all_records = []
    for table in tables:
        fn = INTEGRATION_SCANNER_MAP.get(table)
        if not fn:
            print(f"  ⚠️  No scanner for: {table} — skipping")
            continue
        records = fn(limit=limit)
        all_records.extend(records)
 
    print(f"\n✅ Total integration records fetched: {len(all_records)}")
    return all_records