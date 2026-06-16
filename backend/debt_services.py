#debt_services.py

import json
import re
import time
from llm_config import get_openai_client, OPENAI_DEPLOYMENT
from prompts import DEBT_ANALYSIS_PROMPT
from debt_snow_scanner import run_scan, SCANNER_MAP
 
 
# ─────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────
 
# Only send to AI if the record has at least 1 basic_flag
# Records with zero flags get risk_level = "None" without an AI call
# This saves Azure OpenAI cost significantly
AI_SKIP_IF_NO_FLAGS = True
 
# Max script length sent to AI (characters)
MAX_SCRIPT_CHARS = 1500

# Delay between AI calls (seconds) to avoid rate limiting
AI_CALL_DELAY = 0.5
 
 
# ─────────────────────────────────────────
# AVAILABLE TABLES (for React scan selector)
# ─────────────────────────────────────────
 
AVAILABLE_TABLES = [
    {"table": "sys_script",         "label": "Business Rules",      "phase": 1},
    {"table": "sys_script_include", "label": "Script Includes",     "phase": 1},
    {"table": "sys_script_client",  "label": "Client Scripts",      "phase": 1},
    {"table": "sys_hub_flow",       "label": "Flow Designer Flows", "phase": 2},
    {"table": "wf_workflow",        "label": "Legacy Workflows",    "phase": 2},
    {"table": "sc_cat_item",        "label": "Catalog Items",       "phase": 2},
    {"table": "sys_ui_policy",      "label": "UI Policies",         "phase": 2},
]
 
 
# ─────────────────────────────────────────
# AI ANALYZER
# ─────────────────────────────────────────
 
def analyze_with_ai(record: dict) -> dict:
    """
    Sends one ServiceNow record to Azure OpenAI for debt analysis.
    Returns the parsed AI response dict.
    """
    client = get_openai_client()
 
    script_content = (record.get("script") or "")[:MAX_SCRIPT_CHARS]
    basic_flags = record.get("basic_flags", [])
 
    user_content = f"""
Component Name: {record.get('name', 'Unknown')}
Table: {record.get('table_source', 'Unknown')}
Component Type: {record.get('label', 'Unknown')}
Active: {record.get('active', 'Unknown')}
Last Updated: {record.get('last_updated', 'Unknown')}
Updated By: {record.get('updated_by', 'Unknown')}
Description: {record.get('description') or 'None provided'}
 
Pre-detected Flags (from basic rule checks):
{json.dumps(basic_flags, indent=2) if basic_flags else 'None'}
 
Script / Content:
{script_content if script_content else 'No script content available (metadata-only record)'}
"""
 
    try:
        response = client.chat.completions.create(
            model=OPENAI_DEPLOYMENT,
            temperature=0.1,
            max_tokens=800,
            messages=[
                {"role": "system", "content": DEBT_ANALYSIS_PROMPT},
                {"role": "user",   "content": user_content}
            ]
        )
 
        raw = response.choices[0].message.content
        raw = re.sub(r'```json\n?|```\n?', '', raw).strip()
        return json.loads(raw)
 
    except json.JSONDecodeError as e:
        print(f"    ⚠️  AI returned invalid JSON for '{record.get('name')}': {e}")
        return {
            "risk_level":     "Low",
            "issues":         [],
            "summary":        "AI analysis could not be parsed.",
            "recommendation": "Review manually."
        }
    except Exception as e:
        print(f"    ⚠️  AI call failed for '{record.get('name')}': {e}")
        return {
            "risk_level":     "Low",
            "issues":         [],
            "summary":        "AI analysis failed.",
            "recommendation": "Review manually."
        }
 
 
# ─────────────────────────────────────────
# RISK LEVEL NORMALIZER
# ─────────────────────────────────────────
 
def _normalize_risk(ai_risk: str, basic_flags: list) -> str:
    """
    Final risk level decision.
    Combines AI verdict with basic rule flags.
    Basic flags can only elevate risk, never lower it.
    """
    RISK_ORDER = {"None": 0, "Low": 1, "Medium": 2, "High": 3}
 
    ai_level   = ai_risk if ai_risk in RISK_ORDER else "Low"
    flag_level = "None"
 
    high_risk_flags   = {"gs_sleep_detected", "eval_usage_security_risk", "legacy_workflow_migrate_to_flow"}
    medium_risk_flags = {"gliderecord_in_script", "deprecated_getParameter", "glide_ajax_usage"}
 
    for flag in basic_flags:
        clean_flag = flag.split("(")[0]
        if clean_flag in high_risk_flags or clean_flag.startswith("hardcoded_sysid"):
            flag_level = "High"
            break
        elif clean_flag in medium_risk_flags:
            flag_level = max(flag_level, "Medium", key=lambda x: RISK_ORDER.get(x, 0))
 
    if not flag_level or flag_level == "None":
        if "inactive" in basic_flags or "stale_2yr" in basic_flags:
            flag_level = "Low"
 
    final = max(ai_level, flag_level, key=lambda x: RISK_ORDER.get(x, 0))
    return final
 
 
# ─────────────────────────────────────────
# SUMMARY BUILDER
# ─────────────────────────────────────────
 
def _build_summary(findings: list) -> dict:
    """Builds the aggregate summary counts from all findings."""
    summary = {
        "total_scanned": len(findings),
        "high_risk":     0,
        "medium_risk":   0,
        "low_risk":      0,
        "no_risk":       0,
        "inactive":      0,
        "stale":         0,
        "by_table":      {}
    }
 
    for f in findings:
        risk = f.get("risk_level", "None")
        if   risk == "High":   summary["high_risk"]   += 1
        elif risk == "Medium": summary["medium_risk"]  += 1
        elif risk == "Low":    summary["low_risk"]     += 1
        else:                  summary["no_risk"]      += 1
 
        if "inactive"  in f.get("basic_flags", []): summary["inactive"] += 1
        if "stale_2yr" in f.get("basic_flags", []): summary["stale"]    += 1
 
        table = f.get("table_source", "unknown")
        summary["by_table"][table] = summary["by_table"].get(table, 0) + 1
 
    return summary
 
 
# ─────────────────────────────────────────
# MASTER ORCHESTRATOR
# ─────────────────────────────────────────
 
def scan_technical_debt(tables: list, limit: int = 100) -> dict:
    """
    Main entry point for Technical Debt scan.
 
    Steps:
      1. Scan selected ServiceNow tables (read-only GET calls)
      2. Apply basic rule checks to every record
      3. Send flagged records to Azure OpenAI for deep analysis
      4. Combine results into a structured debt report
      5. Return full report with summary + findings
 
    Args:
        tables: list of ServiceNow table names to scan
        limit:  max records per table (default 100)
 
    Returns:
        dict with 'summary' and 'findings' keys
    """
    print("\n" + "="*60)
    print("🚀 TECHNICAL DEBT CLEARANCE — SCAN INITIATED")
    print("="*60)
 
    # STEP 1: SCAN
    all_records = run_scan(tables=tables, limit=limit)
 
    if not all_records:
        return {
            "status":   "completed",
            "summary":  {"total_scanned": 0, "high_risk": 0, "medium_risk": 0,
                         "low_risk": 0, "no_risk": 0, "inactive": 0, "stale": 0, "by_table": {}},
            "findings": []
        }
 
    # STEP 2 + 3: ANALYZE
    findings = []
    total = len(all_records)
 
    print(f"\n🤖 STARTING AI ANALYSIS ({total} records)...")
    print(f"   AI skip if no flags: {AI_SKIP_IF_NO_FLAGS}")
 
    for i, record in enumerate(all_records, 1):
        name        = record.get("name", "Unknown")
        basic_flags = record.get("basic_flags", [])
 
        print(f"\n  [{i}/{total}] {record.get('label')} → '{name}'")
        print(f"    Flags: {basic_flags if basic_flags else 'none'}")
 
        if AI_SKIP_IF_NO_FLAGS and not basic_flags:
            print(f"    ⏭️  Skipping AI (no flags detected)")
            ai_result = {
                "risk_level":     "None",
                "issues":         [],
                "summary":        "No issues detected by rule checks.",
                "recommendation": "No action required."
            }
        else:
            print(f"    🤖 Sending to Azure OpenAI...")
            ai_result = analyze_with_ai(record)
            time.sleep(AI_CALL_DELAY)
 
        final_risk = _normalize_risk(
            ai_result.get("risk_level", "None"),
            basic_flags
        )
 
        print(f"    ✅ Final Risk: {final_risk}")
 
        finding = {
            "sys_id":         record.get("sys_id"),
            "name":           name,
            "table_source":   record.get("table_source"),
            "label":          record.get("label"),
            "active":         record.get("active"),
            "last_updated":   record.get("last_updated"),
            "updated_by":     record.get("updated_by"),
            "description":    record.get("description"),
            "extra":          record.get("extra", {}),
            "basic_flags":    basic_flags,
            "risk_level":     final_risk,
            "ai_issues":      ai_result.get("issues", []),
            "ai_summary":     ai_result.get("summary", ""),
            "recommendation": ai_result.get("recommendation", "")
        }
        findings.append(finding)
 
    # STEP 4: BUILD REPORT
    summary = _build_summary(findings)
 
    # Sort: High → Medium → Low → None
    RISK_ORDER = {"High": 0, "Medium": 1, "Low": 2, "None": 3}
    findings.sort(key=lambda x: RISK_ORDER.get(x.get("risk_level", "None"), 3))
 
    print("\n" + "="*60)
    print("🎉 TECHNICAL DEBT SCAN COMPLETE")
    print(f"   Total: {summary['total_scanned']} | "
          f"High: {summary['high_risk']} | "
          f"Medium: {summary['medium_risk']} | "
          f"Low: {summary['low_risk']}")
    print("="*60)
 
    return {
        "status":   "completed",
        "summary":  summary,
        "findings": findings
    }