# orchestrator.py
# ONE new file. Routes natural language prompts to existing workers.
# Zero changes to any existing service file.

import json
import re
import os
import asyncio
from typing import AsyncGenerator

from llm_config import get_openai_client, OPENAI_DEPLOYMENT
from snow_client import safe_get, SNOW_BASE_URL


# ── Intent classifier system prompt ────────────────────────────────────────

INTENT_PROMPT = """
You are an intent classifier for a ServiceNow automation platform.
Given the user's message, return a JSON object with exactly these keys:

{
  "intent": one of ["new_module", "scoped_app", "integration", "tech_debt", "release"],
  "confidence": float 0-1,
  "extracted_params": {
    "tables": [],
    "limit": 5,
    "change_number": null,
    "table_name": null,
    "app_name": null,
    "app_scope": null,
    "description": null
  },
  "clarification_needed": null
}

Intent definitions:
- new_module  → build / create a new module, table, form, field, UI policy, business rule
- scoped_app  → create or scaffold a scoped application
  For scoped_app: extract app_name from the prompt (e.g. "IT Asset Management").
  app_scope is optional — leave null if not mentioned, the system will auto-derive it.
- integration → REST/SOAP integrations, modernise old integrations, MID server, API connections
- tech_debt   → unused scripts, duplicate BRs, dead code, legacy APIs, stale records, cleanup, scan
- release     → change requests, deployment, CAB, release notes, rollback plan, change readiness

For tech_debt extracted_params.tables, choose from:
  ["sys_script", "sys_script_include", "sys_script_client",
   "sys_hub_flow", "wf_workflow", "sc_cat_item", "sys_ui_policy"]
  If user says "all" or doesn't specify, include all of them.

For integration extracted_params.tables, choose from:
  ["sys_rest_message", "sys_soap_message", "sys_script_include",
   "sys_trigger", "sys_auth_profile"]
  If user says "all" or doesn't specify, include all of them.

For release, extract change_number (e.g. CHG0012345) and table_name
  (default: "change_request" if not specified).

Return ONLY valid JSON. No markdown. No explanation.
"""

# ── Intent → worker label ───────────────────────────────────────────────────

WORKER_LABELS = {
    "new_module":  "New Module Development",
    "scoped_app":  "Scoped App Development",
    "integration": "Integration Development & Modernization",
    "tech_debt":   "Technical Debt Clearance",
    "release":     "Release & Change Management",
}

# ── Default tables per intent (fallback if LLM doesn't extract) ─────────────

DEFAULT_TABLES = {
    "tech_debt":   ["sys_script", "sys_script_include", "sys_script_client"],
    "integration": ["sys_rest_message", "sys_soap_message",
                    "sys_script_include", "sys_trigger", "sys_auth_profile"],
}

BATCH_SIZE = 10


# ── Orchestrator ─────────────────────────────────────────────────────────────

class Orchestrator:

    def __init__(self):
        self.llm = get_openai_client()   # AzureOpenAI instance

    # ── Public entry point ───────────────────────────────────────────────────

    async def handle(self, user_prompt: str, session: dict) -> AsyncGenerator[str, None]:
        """
        Yields newline-terminated JSON strings (SSE data lines).

        Chunk shapes:
          { "type": "routing",  "intent": "...", "label": "...", "confidence": 0.95 }
          { "type": "prescan",  "summary": { "hint": "...", ...counts } }
          { "type": "progress", "done": N, "total": N, "batch_result": [...] }
          { "type": "result",   "data": { ... } }
          { "type": "clarify",  "question": "..." }
          { "type": "error",    "message": "..." }
        """
        try:
            # 1. Classify intent
            intent_data = await self._classify(user_prompt)

            if intent_data.get("clarification_needed"):
                yield _chunk("clarify", question=intent_data["clarification_needed"])
                return

            intent = intent_data["intent"]
            params = intent_data.get("extracted_params", {})

            # Ensure tables always have a fallback
            if not params.get("tables"):
                params["tables"] = DEFAULT_TABLES.get(intent, [])

            # Store in session for Phase 3 multi-turn memory
            session["last_intent"] = intent
            session["last_params"]  = params
            session["history"].append({"role": "user", "content": user_prompt})

            yield _chunk("routing",
                         intent=intent,
                         label=WORKER_LABELS[intent],
                         confidence=intent_data.get("confidence", 0.9))

            # 2. Pre-scan: fast SN count summary shown before heavy AI work
            prescan = await self._prescan(intent, params)
            yield _chunk("prescan", summary=prescan)

            # 3. Dispatch to the right worker
            worker_map = {
                "tech_debt":   self._run_tech_debt,
                "integration": self._run_integration,
                "release":     self._run_release,
                "new_module":  self._run_new_module,
                "scoped_app":  self._run_scoped_app,
            }
            async for chunk in worker_map[intent](user_prompt, params, prescan):
                yield chunk

        except Exception as exc:
            yield _chunk("error", message=str(exc))

    # ── Intent classification (sync LLM wrapped in executor) ─────────────────

    async def _classify(self, prompt: str) -> dict:
        loop = asyncio.get_event_loop()

        def _sync():
            resp = self.llm.chat.completions.create(
                model=OPENAI_DEPLOYMENT,
                temperature=0,
                max_tokens=400,
                messages=[
                    {"role": "system", "content": INTENT_PROMPT},
                    {"role": "user",   "content": prompt},
                ]
            )
            text = resp.choices[0].message.content.strip()
            text = re.sub(r"^```[a-z]*\n?", "", text)
            text = re.sub(r"\n?```$",        "", text)
            return json.loads(text)

        return await loop.run_in_executor(None, _sync)

    # ── Pre-scan: SN record counts shown immediately ─────────────────────────

    async def _prescan(self, intent: str, params: dict) -> dict:
        loop = asyncio.get_event_loop()

        def _count(table: str, query: str = "") -> int:
            """Returns record count for a SN table using aggregate API."""
            try:
                q = f"?sysparm_count=true&sysparm_limit=1"
                if query:
                    q += f"&sysparm_query={query}"
                url = f"{SNOW_BASE_URL}/{table}{q}"
                res = safe_get(url)
                if res and res.status_code == 200:
                    result = res.json().get("result", [])
                    if result:
                        return int(result[0].get("Stats.count", 0))
            except Exception:
                pass
            return 0

        def _prescan_sync() -> dict:
            summary = {}

            if intent == "tech_debt":
                tables = params.get("tables", DEFAULT_TABLES["tech_debt"])
                # Map table → friendly label for display
                label_map = {
                    "sys_script":         "business_rules",
                    "sys_script_include": "script_includes",
                    "sys_script_client":  "client_scripts",
                    "sys_hub_flow":       "flows",
                    "wf_workflow":        "legacy_workflows",
                    "sc_cat_item":        "catalog_items",
                    "sys_ui_policy":      "ui_policies",
                }
                total = 0
                for t in tables:
                    key = label_map.get(t, t)
                    cnt = _count(t)
                    summary[key] = cnt
                    total += cnt
                summary["hint"] = (
                    f"Found ~{total} records across {len(tables)} table(s). "
                    "Scanning for unused/duplicate/risky logic…"
                )

            elif intent == "integration":
                tables = params.get("tables", DEFAULT_TABLES["integration"])
                label_map = {
                    "sys_rest_message":   "rest_messages",
                    "sys_soap_message":   "soap_messages",
                    "sys_script_include": "integration_scripts",
                    "sys_trigger":        "scheduled_jobs",
                    "sys_auth_profile":   "auth_profiles",
                }
                total = 0
                for t in tables:
                    key = label_map.get(t, t)
                    cnt = _count(t)
                    summary[key] = cnt
                    total += cnt
                summary["hint"] = (
                    f"Found ~{total} integration records across {len(tables)} table(s). "
                    "Analysing for modernization opportunities…"
                )

            elif intent == "release":
                change_number = params.get("change_number")
                open_changes  = _count("change_request", "state=assess^ORstate=-1")
                summary["open_changes"] = open_changes
                summary["hint"] = (
                    f"{open_changes} open change requests in your instance. "
                    + (f"Fetching {change_number}…" if change_number else
                       "Please provide a change number (e.g. CHG0012345).")
                )

            elif intent in ("new_module", "scoped_app"):
                summary["hint"] = "Ready to scaffold. Analysing your requirements…"

            return summary

        return await loop.run_in_executor(None, _prescan_sync)

    # ── Worker: Technical Debt ────────────────────────────────────────────────

    async def _run_tech_debt(self,
                              prompt: str,
                              params: dict,
                              prescan: dict) -> AsyncGenerator[str, None]:
        from debt_snow_scanner import run_scan
        from debt_services     import analyze_with_ai, _normalize_risk, _build_summary, AI_SKIP_IF_NO_FLAGS
        import concurrent.futures

        tables = params.get("tables") or DEFAULT_TABLES["tech_debt"]
        limit  = int(params.get("limit") or 100)
        loop   = asyncio.get_event_loop()

        # ── Step 1: fetch all records ──────────────────────────────
        print(f"[Orchestrator] Fetching records from: {tables}")
        try:
            all_records = await asyncio.wait_for(
                loop.run_in_executor(None, lambda: run_scan(tables=tables, limit=limit)),
                timeout=60.0
            )
        except asyncio.TimeoutError:
            yield _chunk("error", message="ServiceNow scan timed out after 60s. Check connectivity.")
            return
        except Exception as e:
            yield _chunk("error", message=f"Scan fetch failed: {str(e)}")
            return

        total = len(all_records)
        print(f"[Orchestrator] Fetched {total} records. Starting AI analysis...")

        if total == 0:
            yield _chunk("result", data={
                "status": "completed",
                "summary": {"total_scanned": 0, "high_risk": 0, "medium_risk": 0,
                            "low_risk": 0, "no_risk": 0, "inactive": 0, "stale": 0, "by_table": {}},
                "findings": []
            })
            return

        # ── Step 2: AI analysis in batches ────────────────────────
        findings = []
        done     = 0

        # Use a dedicated thread pool — avoids exhausting the default executor
        executor = concurrent.futures.ThreadPoolExecutor(max_workers=2)

        try:
            for batch in _batches(all_records, BATCH_SIZE):
                batch_findings = []

                for record in batch:
                    basic_flags = record.get("basic_flags", [])
                    name        = record.get("name", "Unknown")
                    print(f"[Orchestrator] Analysing: {name} | flags: {basic_flags}")

                    if AI_SKIP_IF_NO_FLAGS and not basic_flags:
                        ai_result = {
                            "risk_level":     "None",
                            "issues":         [],
                            "summary":        "No issues detected by rule checks.",
                            "recommendation": "No action required."
                        }
                    else:
                        try:
                            # Run sync AI call in thread with per-record timeout
                            rec = record  # explicit capture
                            ai_result = await asyncio.wait_for(
                                loop.run_in_executor(executor, lambda r=rec: analyze_with_ai(r)),
                                timeout=30.0   # 30s per record max
                            )
                        except asyncio.TimeoutError:
                            print(f"[Orchestrator] AI timeout for: {name}")
                            ai_result = {
                                "risk_level":     "Low",
                                "issues":         [],
                                "summary":        "AI analysis timed out.",
                                "recommendation": "Review manually."
                            }
                        except Exception as e:
                            print(f"[Orchestrator] AI error for {name}: {e}")
                            ai_result = {
                                "risk_level":     "Low",
                                "issues":         [],
                                "summary":        f"AI analysis failed: {str(e)}",
                                "recommendation": "Review manually."
                            }

                    final_risk = _normalize_risk(
                        ai_result.get("risk_level", "None"), basic_flags
                    )

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
                        "recommendation": ai_result.get("recommendation", ""),
                    }
                    batch_findings.append(finding)

                findings.extend(batch_findings)
                done += len(batch)
                print(f"[Orchestrator] Progress: {done}/{total}")

                # Yield progress after every batch
                yield _chunk("progress",
                             done=done,
                             total=total,
                             batch_result=batch_findings)

        finally:
            executor.shutdown(wait=False)

        # ── Step 3: final summary ──────────────────────────────────
        summary = _build_summary(findings)
        RISK_ORDER = {"High": 0, "Medium": 1, "Low": 2, "None": 3}
        findings.sort(key=lambda x: RISK_ORDER.get(x.get("risk_level", "None"), 3))

        yield _chunk("result", data={
            "status":   "completed",
            "summary":  summary,
            "findings": findings
        })
        
    # ── Worker: Integration Modernization ────────────────────────────────────

    async def _run_integration(self,
                                prompt: str,
                                params: dict,
                                prescan: dict) -> AsyncGenerator[str, None]:
        from integration_scanner  import run_integration_scan
        from integration_services import (
            analyze_with_ai     as intg_analyze_with_ai,
            _final_score,
            _score_to_urgency,
            _build_summary      as intg_build_summary,
            AI_SKIP_IF_NO_FLAGS as INTG_SKIP,
        )
        import concurrent.futures

        tables = params.get("tables") or DEFAULT_TABLES["integration"]
        limit  = int(params.get("limit") or 50)
        loop   = asyncio.get_event_loop()

        # ── Step 1: fetch ──────────────────────────────────────────
        print(f"[Orchestrator] Integration fetch: {tables}")
        try:
            all_records = await asyncio.wait_for(
                loop.run_in_executor(
                    None, lambda: run_integration_scan(tables=tables, limit=limit)
                ),
                timeout=60.0
            )
        except asyncio.TimeoutError:
            yield _chunk("error", message="Integration scan timed out after 60s.")
            return
        except Exception as e:
            yield _chunk("error", message=f"Integration fetch failed: {str(e)}")
            return

        total = len(all_records)
        print(f"[Orchestrator] Fetched {total} integration records.")

        if total == 0:
            yield _chunk("result", data={
                "status":  "completed",
                "summary": {
                    "total_scanned": 0, "critical": 0, "high": 0,
                    "medium": 0, "low": 0, "already_modern": 0,
                    "avg_score": 0, "by_table": {}
                },
                "findings": []
            })
            return

        # ── Step 2: batch AI analysis ──────────────────────────────
        findings = []
        done     = 0
        executor = concurrent.futures.ThreadPoolExecutor(max_workers=2)

        try:
            for batch in _batches(all_records, BATCH_SIZE):
                batch_findings = []

                for record in batch:
                    basic_flags = record.get("basic_flags", [])
                    pre_score   = record.get("pre_score", 100)
                    name        = record.get("name", "Unknown")
                    print(f"[Orchestrator] Integration analysing: {name} | flags: {basic_flags}")

                    if INTG_SKIP and not basic_flags:
                        ai_result = {
                            "modernization_score":        100,
                            "urgency":                    "None",
                            "current_type":               record.get("label"),
                            "issues":                     [],
                            "summary":                    "No outdated patterns detected.",
                            "recommended_approach":       "No modernization needed.",
                            "modernization_steps":        [],
                            "flow_designer_opportunity":  "Not applicable",
                            "integrationhub_opportunity": "Not applicable",
                            "security_recommendation":    "No changes needed",
                        }
                    else:
                        try:
                            rec = record  # explicit capture
                            ai_result = await asyncio.wait_for(
                                loop.run_in_executor(
                                    executor,
                                    lambda r=rec: intg_analyze_with_ai(r)
                                ),
                                timeout=30.0
                            )
                            print(f"[Orchestrator] Integration AI done: {name}")
                        except asyncio.TimeoutError:
                            print(f"[Orchestrator] Integration AI timeout: {name}")
                            ai_result = {
                                "modernization_score":        pre_score,
                                "urgency":                    _score_to_urgency(pre_score),
                                "current_type":               record.get("label"),
                                "issues":                     [],
                                "summary":                    "AI analysis timed out — review manually.",
                                "recommended_approach":       "Manual review required.",
                                "modernization_steps":        [],
                                "flow_designer_opportunity":  "Not analyzed.",
                                "integrationhub_opportunity": "Not analyzed.",
                                "security_recommendation":    "Not analyzed.",
                            }
                        except Exception as e:
                            print(f"[Orchestrator] Integration AI error for {name}: {e}")
                            ai_result = {
                                "modernization_score":        pre_score,
                                "urgency":                    _score_to_urgency(pre_score),
                                "current_type":               record.get("label"),
                                "issues":                     [],
                                "summary":                    f"AI error: {str(e)}",
                                "recommended_approach":       "Review manually.",
                                "modernization_steps":        [],
                                "flow_designer_opportunity":  "Not analyzed.",
                                "integrationhub_opportunity": "Not analyzed.",
                                "security_recommendation":    "Not analyzed.",
                            }

                    ai_score    = ai_result.get("modernization_score", pre_score)
                    final_score = _final_score(pre_score, ai_score)
                    urgency     = ai_result.get("urgency") or _score_to_urgency(final_score)

                    finding = {
                        "sys_id":                     record.get("sys_id"),
                        "name":                       name,
                        "table_source":               record.get("table_source"),
                        "label":                      record.get("label"),
                        "active":                     record.get("active"),
                        "last_updated":               record.get("last_updated"),
                        "updated_by":                 record.get("updated_by"),
                        "description":                record.get("description"),
                        "extra":                      record.get("extra", {}),
                        "basic_flags":                basic_flags,
                        "modernization_score":        final_score,
                        "urgency":                    urgency,
                        "current_type":               ai_result.get("current_type", record.get("label")),
                        "ai_issues":                  ai_result.get("issues", []),
                        "ai_summary":                 ai_result.get("summary", ""),
                        "recommended_approach":       ai_result.get("recommended_approach", ""),
                        "modernization_steps":        ai_result.get("modernization_steps", []),
                        "flow_designer_opportunity":  ai_result.get("flow_designer_opportunity", ""),
                        "integrationhub_opportunity": ai_result.get("integrationhub_opportunity", ""),
                        "security_recommendation":    ai_result.get("security_recommendation", ""),
                    }
                    batch_findings.append(finding)

                findings.extend(batch_findings)
                done += len(batch)
                print(f"[Orchestrator] Integration progress: {done}/{total}")
                yield _chunk("progress", done=done, total=total, batch_result=batch_findings)

        finally:
            executor.shutdown(wait=False)

        # ── Step 3: final result ───────────────────────────────────
        findings.sort(key=lambda x: x.get("modernization_score", 100))
        summary = intg_build_summary(findings)

        yield _chunk("result", data={
            "status":   "completed",
            "summary":  summary,
            "findings": findings
        })

    # ── Worker: Release & Change Management ──────────────────────────────────

    async def _run_release(self, prompt, params, prescan):
        from release_services import fetch_servicenow_change, analyze_change_readiness

        change_number = params.get("change_number")
        table_name    = params.get("table_name") or "change_request"
        instance_url  = os.getenv("SERVICENOW_INSTANCE", "").strip().strip('"').rstrip("/")
        loop          = asyncio.get_event_loop()

        print(f"[Release] change_number={change_number}, instance={instance_url}")  # ← add this

        if not change_number:
            yield _chunk("clarify",
                        question="Please provide a change number (e.g. CHG0040007).")
            return

        try:
            change_data = await loop.run_in_executor(
                None,
                lambda: fetch_servicenow_change(instance_url, change_number, table_name)
            )
            print(f"[Release] change_data keys: {list(change_data.keys())}")

            result = await loop.run_in_executor(
                None,
                lambda: analyze_change_readiness(change_data)
            )
            print(f"[Release] readiness keys: {list(result.keys())}")

            # ── FLATTEN THE PAYLOAD HERE ──────────────────────────────────────
            yield _chunk("result", data={
                "status": "completed",
                "change_number": change_number,
                "table": table_name,
                "source_record": change_data,
                "message": f"Release readiness for {change_number}: {result.get('production_readiness', '—')}",
                
                # Bring these keys to the top-level so the Chat UI can see them!
                "production_readiness": result.get("production_readiness"),
                "risk_score": result.get("risk_score"),
                "cab_summary": result.get("cab_summary"),
                "issues_found": result.get("issues_found", []),
                "recommended_actions": result.get("recommended_actions", []),
                "rollback_suggestions": result.get("rollback_suggestions"),
            })

        except Exception as e:
            print(f"[Release] ERROR: {e}")
            yield _chunk("error", message=str(e))

    # ── Worker: New Module Development ───────────────────────────────────────

    # REPLACE the entire _run_new_module method

    async def _run_new_module(self,
                           prompt: str,
                           params: dict,
                           prescan: dict) -> AsyncGenerator[str, None]:
        """
        Generates blueprint only — no ServiceNow writes.
        Frontend handles validate → push flow via BlueprintValidator.
        """
        import re, json
        from prompts import SYSTEM_PROMPT
        loop = asyncio.get_event_loop()

        try:
            def _generate():
                resp = self.llm.chat.completions.create(
                    model=OPENAI_DEPLOYMENT,
                    temperature=0.2,
                    max_tokens=2500,
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user",   "content": prompt},
                    ]
                )
                raw = resp.choices[0].message.content
                raw = re.sub(r'```json\n?|```\n?', '', raw).strip()
                return json.loads(raw)

            blueprint = await loop.run_in_executor(None, _generate)

            # Stream the blueprint back — frontend will show
            # BlueprintValidator + "Add into ServiceNow" button
            yield _chunk("result", data=blueprint)

        except Exception as e:
            yield _chunk("error", message=str(e))

    # ── Worker: Scoped App Development ───────────────────────────────────────

    

    async def _run_scoped_app(self,
                           prompt: str,
                           params: dict,
                           prescan: dict) -> AsyncGenerator[str, None]:
        """
        Generates scoped app blueprint only — no ServiceNow writes.
        Frontend handles validate → push flow via BlueprintValidator.
        """
        import re, json
        from prompts import SCOPED_APP_PROMPT
        loop = asyncio.get_event_loop()

        try:
            def _generate():
                resp = self.llm.chat.completions.create(
                    model=OPENAI_DEPLOYMENT,
                    temperature=0.2,
                    max_tokens=3000,
                    messages=[
                        {"role": "system", "content": SCOPED_APP_PROMPT},
                        {"role": "user",   "content": prompt},
                    ]
                )
                raw = resp.choices[0].message.content
                raw = re.sub(r'```json\n?|```\n?', '', raw).strip()
                return json.loads(raw)

            blueprint = await loop.run_in_executor(None, _generate)

            yield _chunk("result", data=blueprint)

        except Exception as e:
            yield _chunk("error", message=str(e))

# ── Helpers ──────────────────────────────────────────────────────────────────

def _chunk(type_: str, **kwargs) -> str:
    """Returns a newline-terminated JSON string — one SSE data line."""
    return json.dumps({"type": type_, **kwargs}) + "\n"


def _batches(lst: list, size: int):
    for i in range(0, len(lst), size):
        yield lst[i: i + size]