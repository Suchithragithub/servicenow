# integration_services.py

import json
import re
import time
from llm_config import get_openai_client, OPENAI_DEPLOYMENT
from prompts import INTEGRATION_ANALYSIS_PROMPT
from integration_scanner import run_integration_scan, AVAILABLE_INTEGRATION_TABLES
 
# ─────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────
 
# Skip AI if no flags found — saves Azure OpenAI cost
AI_SKIP_IF_NO_FLAGS = True
 
# Max script chars sent to AI per record
MAX_SCRIPT_CHARS = 1500
 
# Delay between AI calls (rate limit protection)
AI_CALL_DELAY = 0.5
 
# Urgency thresholds based on modernization score
# Lower score = more urgent
URGENCY_THRESHOLDS = {
    "Critical": (0,  30),   # score 0-30
    "High":     (31, 50),   # score 31-50
    "Medium":   (51, 70),   # score 51-70
    "Low":      (71, 85),   # score 71-85
    "None":     (86, 100),  # score 86-100 → already modern
}
 
 
# ─────────────────────────────────────────
# URGENCY FROM SCORE
# ─────────────────────────────────────────
 
def _score_to_urgency(score: int) -> str:
    for urgency, (low, high) in URGENCY_THRESHOLDS.items():
        if low <= score <= high:
            return urgency
    return "None"
 
 
# ─────────────────────────────────────────
# AI ANALYZER
# ─────────────────────────────────────────
 
def analyze_with_ai(record: dict) -> dict:
    """
    Sends one integration record to Azure OpenAI for modernization analysis.
    Returns parsed AI response dict.
    """
    client = get_openai_client()
 
    script_content = (record.get("script") or "")[:MAX_SCRIPT_CHARS]
    basic_flags    = record.get("basic_flags", [])
    pre_score      = record.get("pre_score", 100)
 
    user_content = f"""
Component Name:   {record.get("name", "Unknown")}
Table:            {record.get("table_source", "Unknown")}
Component Type:   {record.get("label", "Unknown")}
Active:           {record.get("active", "Unknown")}
Last Updated:     {record.get("last_updated", "Unknown")}
Updated By:       {record.get("updated_by", "Unknown")}
Description:      {record.get("description") or "None provided"}
Pre-Score:        {pre_score}/100 (lower = more outdated)
 
Extra Metadata:
{json.dumps(record.get("extra", {}), indent=2)}
 
Pre-detected Flags (rule-based checks):
{json.dumps(basic_flags, indent=2) if basic_flags else "None"}
 
Script / Content:
{script_content if script_content else "No script content available (metadata-only record)"}
"""
 
    try:
        response = get_openai_client().chat.completions.create(
            model=OPENAI_DEPLOYMENT,
            temperature=0.1,
            max_tokens=1000,
            messages=[
                {"role": "system", "content": INTEGRATION_ANALYSIS_PROMPT},
                {"role": "user",   "content": user_content}
            ]
        )
        raw = response.choices[0].message.content
        raw = re.sub(r'```json\n?|```\n?', '', raw).strip()
        return json.loads(raw)
 
    except json.JSONDecodeError as e:
        print(f"    ⚠️  AI invalid JSON for '{record.get('name')}': {e}")
        return _fallback_ai_result(pre_score)
    except Exception as e:
        print(f"    ⚠️  AI call failed for '{record.get('name')}': {e}")
        return _fallback_ai_result(pre_score)
 
 
def _fallback_ai_result(pre_score: int) -> dict:
    """Returns a safe fallback when AI call fails."""
    return {
        "modernization_score":          pre_score,
        "urgency":                       _score_to_urgency(pre_score),
        "current_type":                  "Unknown",
        "issues":                        [],
        "summary":                       "AI analysis could not be completed. Review manually.",
        "recommended_approach":          "Manual review required.",
        "modernization_steps":           ["Review this integration manually."],
        "flow_designer_opportunity":     "Not analyzed.",
        "integrationhub_opportunity":    "Not analyzed.",
        "security_recommendation":       "Not analyzed."
    }
 
 
# ─────────────────────────────────────────
# FINAL SCORE: combine pre-score + AI score
# ─────────────────────────────────────────
 
def _final_score(pre_score: int, ai_score: int) -> int:
    """
    Weighted average — AI score carries more weight (70%) than rule score (30%).
    AI has more context. Rule checks are a fast pre-filter.
    """
    return int((ai_score * 0.7) + (pre_score * 0.3))
 
 
# ─────────────────────────────────────────
# SUMMARY BUILDER
# ─────────────────────────────────────────
 
def _build_summary(findings: list) -> dict:
    summary = {
        "total_scanned":    len(findings),
        "critical":         0,
        "high":             0,
        "medium":           0,
        "low":              0,
        "already_modern":   0,
        "avg_score":        0,
        "by_table":         {}
    }
 
    total_score = 0
 
    for f in findings:
        urgency = f.get("urgency", "None")
        if   urgency == "Critical": summary["critical"]       += 1
        elif urgency == "High":     summary["high"]           += 1
        elif urgency == "Medium":   summary["medium"]         += 1
        elif urgency == "Low":      summary["low"]            += 1
        else:                       summary["already_modern"] += 1
 
        total_score += f.get("modernization_score", 100)
 
        table = f.get("table_source", "unknown")
        summary["by_table"][table] = summary["by_table"].get(table, 0) + 1
 
    if findings:
        summary["avg_score"] = round(total_score / len(findings), 1)
 
    return summary
 
 
# ─────────────────────────────────────────
# MASTER ORCHESTRATOR
# ─────────────────────────────────────────
 
def scan_integrations(tables: list, limit: int = 50) -> dict:
    """
    Main entry point for Integration Modernization scan.
 
    Steps:
      1. Scan selected ServiceNow tables (read-only)
      2. Apply basic rule checks + pre-score
      3. Send flagged records to Azure OpenAI for deep analysis
      4. Combine pre-score + AI score into final score
      5. Return full report with summary + findings
 
    Args:
        tables: list of ServiceNow table names to scan
        limit:  max records per table (default 50)
 
    Returns:
        dict with 'summary' and 'findings' keys
    """
    print("\n" + "="*60)
    print("🚀 INTEGRATION MODERNIZATION SCAN INITIATED")
    print("="*60)
 
    # STEP 1: SCAN
    all_records = run_integration_scan(tables=tables, limit=limit)
 
    if not all_records:
        return {
            "status":   "completed",
            "summary":  {
                "total_scanned": 0, "critical": 0, "high": 0,
                "medium": 0, "low": 0, "already_modern": 0,
                "avg_score": 0, "by_table": {}
            },
            "findings": []
        }
 
    # STEP 2 + 3: ANALYZE
    findings = []
    total    = len(all_records)
 
    print(f"\n🤖 STARTING AI ANALYSIS ({total} records)...")
 
    for i, record in enumerate(all_records, 1):
        name        = record.get("name", "Unknown")
        basic_flags = record.get("basic_flags", [])
        pre_score   = record.get("pre_score", 100)
 
        print(f"\n  [{i}/{total}] {record.get('label')} → '{name}' (pre-score: {pre_score})")
        print(f"    Flags: {basic_flags if basic_flags else 'none'}")
 
        # Skip AI if no flags and config allows
        if AI_SKIP_IF_NO_FLAGS and not basic_flags:
            print(f"    ⏭️  Skipping AI (no flags)")
            ai_result = {
                "modernization_score":       100,
                "urgency":                   "None",
                "current_type":              record.get("label"),
                "issues":                    [],
                "summary":                   "No outdated patterns detected.",
                "recommended_approach":      "No modernization needed.",
                "modernization_steps":       [],
                "flow_designer_opportunity": "Not applicable",
                "integrationhub_opportunity":"Not applicable",
                "security_recommendation":   "No changes needed"
            }
        else:
            print(f"    🤖 Sending to Azure OpenAI...")
            ai_result = analyze_with_ai(record)
            time.sleep(AI_CALL_DELAY)
 
        # Combine scores
        ai_score    = ai_result.get("modernization_score", pre_score)
        final_score = _final_score(pre_score, ai_score)
        urgency     = ai_result.get("urgency") or _score_to_urgency(final_score)
 
        print(f"    ✅ Final Score: {final_score}/100 | Urgency: {urgency}")
 
        finding = {
            "sys_id":                    record.get("sys_id"),
            "name":                      name,
            "table_source":              record.get("table_source"),
            "label":                     record.get("label"),
            "active":                    record.get("active"),
            "last_updated":              record.get("last_updated"),
            "updated_by":                record.get("updated_by"),
            "description":               record.get("description"),
            "extra":                     record.get("extra", {}),
            "basic_flags":               basic_flags,
            "modernization_score":       final_score,
            "urgency":                   urgency,
            "current_type":              ai_result.get("current_type", record.get("label")),
            "ai_issues":                 ai_result.get("issues", []),
            "ai_summary":                ai_result.get("summary", ""),
            "recommended_approach":      ai_result.get("recommended_approach", ""),
            "modernization_steps":       ai_result.get("modernization_steps", []),
            "flow_designer_opportunity": ai_result.get("flow_designer_opportunity", ""),
            "integrationhub_opportunity":ai_result.get("integrationhub_opportunity", ""),
            "security_recommendation":   ai_result.get("security_recommendation", ""),
        }
        findings.append(finding)
 
    # Sort: Critical → High → Medium → Low → None (by score ascending)
    findings.sort(key=lambda x: x.get("modernization_score", 100))
 
    summary = _build_summary(findings)
 
    print("\n" + "="*60)
    print("🎉 INTEGRATION SCAN COMPLETE")
    print(f"   Total: {summary['total_scanned']} | "
          f"Critical: {summary['critical']} | "
          f"High: {summary['high']} | "
          f"Avg Score: {summary['avg_score']}/100")
    print("="*60)
 
    return {
        "status":   "completed",
        "summary":  summary,
        "findings": findings
    }