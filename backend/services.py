# services.py

import json
import re
import time
from llm_config import get_openai_client, OPENAI_DEPLOYMENT
from prompts import RELEASE_IMPACT_INSTRUCTION, SYSTEM_PROMPT, SCOPED_APP_PROMPT
from discovery import discover_module
from snow_client import (
    create_snow_table,
    create_snow_field,
    create_snow_role,
    create_snow_form,
    create_snow_notification,
    create_snow_approval,
    create_snow_navigation,
    create_snow_workflow,
    create_snow_application,
    create_snow_app_menu,
    create_list_layout,
    create_list_control,
    create_client_script,
    create_script_include,
    create_system_property,
    create_relationship,
    create_related_list,
    create_scoped_app,
    create_scoped_table,
    create_scoped_field,
    create_scoped_role,
    create_scoped_navigation,
    create_acl,
    safe_get,
    SNOW_BASE_URL,
)
from rag_release_notes import query_release_notes, format_context_for_prompt, list_indexed_sources
from discovery import discover_scoped_app

# ─────────────────────────────────────────────────────────────────────────────
# checks release notes relevant to the requirement
# ─────────────────────────────────────────────────────────────────────────────

# def _check_release_notes_for_scoped_app(prompt: str) -> dict:
#     """
#     Queries the indexed release notes for anything relevant to scoped app
#     development before generating the blueprint. Returns context to inject
#     into the LLM prompt, plus a flag for whether anything relevant was found.
 
#     Returns:
#         {
#             "has_relevant_changes": bool,
#             "context_block":        str,   # formatted text for prompt injection
#             "raw_results":          list,
#             "sources_checked":      list
#         }
#     """
#     print("\n📚 CHECKING RELEASE NOTES FOR SCOPED APP IMPACT...")
 
#     # Check if anything is indexed at all
#     index_status = list_indexed_sources()
#     if index_status["total_vectors"] == 0:
#         print("  ℹ️  No release notes indexed. Proceeding with standard generation.")
#         return {
#             "has_relevant_changes": False,
#             "context_block":        "",
#             "raw_results":          [],
#             "sources_checked":      [],
#         }
 
#     # Build a query that combines the user's requirement with general
#     # scoped-app-relevant change categories
#     search_query = (
#         f"scoped application development changes deprecations security updates "
#         f"recommendations related to: {prompt}"
#     )
 
#     results = query_release_notes(search_query, top_k=6)
 
#     # Filter to reasonably relevant results only (cosine similarity threshold)
#     RELEVANCE_THRESHOLD = 0.35
#     relevant_results = [r for r in results if r["score"] >= RELEVANCE_THRESHOLD]
 
#     sources_checked = list(set(r["source"] for r in results))
 
#     if not relevant_results:
#         print(f"  ✅ No highly relevant release note changes found (checked {len(sources_checked)} doc(s))")
#         return {
#             "has_relevant_changes": False,
#             "context_block":        "",
#             "raw_results":          results,
#             "sources_checked":      sources_checked,
#         }
 
#     print(f"  ⚠️  Found {len(relevant_results)} relevant release note section(s):")
#     for r in relevant_results:
#         print(f"     - {r['source']} (page {r['page']}, score {r['score']:.2f})")
 
#     context_block = format_context_for_prompt(relevant_results)
 
#     return {
#         "has_relevant_changes": True,
#         "context_block":        context_block,
#         "raw_results":          relevant_results,
#         "sources_checked":      sources_checked,
#     }



def _check_release_notes_for_scoped_app(prompt: str, selected_features: list = None) -> dict:
    """
    Queries the indexed release notes once PER component type being built,
    instead of one blended generic search. This gives the LLM targeted,
    feature-specific context rather than a vague mixed bag of chunks.
 
    Args:
        prompt:             the user's app requirement text
        selected_features:  list of component types being generated
                            e.g. ["tables", "acls", "workflows", "forms"]
                            If None, defaults to a standard scoped app set.
 
    Returns:
        {
            "has_relevant_changes": bool,
            "context_block":        str,   # formatted, grouped by component
            "raw_results":          list,  # all chunks retrieved, tagged by component
            "sources_checked":      list,
            "components_searched":  list
        }
    """
    print("\n📚 CHECKING RELEASE NOTES (PER-FEATURE TARGETED SEARCH)...")
 
    index_status = list_indexed_sources()
    if index_status["total_vectors"] == 0:
        print("  ℹ️  No release notes indexed. Proceeding with standard generation.")
        return {
            "has_relevant_changes": False,
            "context_block":        "",
            "raw_results":          [],
            "sources_checked":      [],
            "components_searched":  [],
        }
 
    if not selected_features:
        selected_features = ["tables", "fields", "roles", "acls", "workflows", "forms", "navigation"]
 
    RELEVANCE_THRESHOLD = 0.40   # raised from 0.35 — fewer, more targeted matches
    TOP_K_PER_FEATURE    = 3      # max chunks per component type
 
    all_relevant   = []
    sources_seen   = set()
 
    for feature in selected_features:
        query = (
            f"ServiceNow {feature} deprecations security updates "
            f"recommendations changes — context: {prompt}"
        )
        results = query_release_notes(query, top_k=TOP_K_PER_FEATURE)
 
        for r in results:
            if r["score"] >= RELEVANCE_THRESHOLD:
                r["searched_for_component"] = feature   # tag which feature this was retrieved for
                all_relevant.append(r)
                sources_seen.add(r["source"])
 
        if results:
            top_score = max(r["score"] for r in results)
            print(f"  🔍 {feature}: top match score {top_score:.2f}"
                  f" ({'kept' if top_score >= RELEVANCE_THRESHOLD else 'below threshold, discarded'})")
 
    if not all_relevant:
        print(f"  ✅ No release note chunk cleared the {RELEVANCE_THRESHOLD} threshold for any component.")
        return {
            "has_relevant_changes": False,
            "context_block":        "",
            "raw_results":          [],
            "sources_checked":      list(sources_seen),
            "components_searched":  selected_features,
        }
 
    print(f"  ⚠️  {len(all_relevant)} chunk(s) cleared threshold across {len(set(r['searched_for_component'] for r in all_relevant))} component(s)")
 
    # Group context by component type for clearer prompt structure
    by_component = {}
    for r in all_relevant:
        by_component.setdefault(r["searched_for_component"], []).append(r)
 
    context_blocks = []
    for component, chunks in by_component.items():
        block_lines = [f"--- Context for component: {component} ---"]
        for c in chunks:
            block_lines.append(
                f"[Source: {c['source']}, Page {c['page']}, Relevance: {c['score']:.2f}]\n{c['text']}"
            )
        context_blocks.append("\n\n".join(block_lines))
 
    context_block = "\n\n".join(context_blocks)
 
    return {
        "has_relevant_changes": True,
        "context_block":        context_block,
        "raw_results":          all_relevant,
        "sources_checked":      list(sources_seen),
        "components_searched":  selected_features,
    }


def _generate_partial_scoped_blueprint(prompt: str, selected_features: list,
                                        existing_app_scope: str = None) -> dict:
    """
    Calls LLM to generate a SCOPED APP blueprint scoped to only the
    selected features, using SCOPED_APP_PROMPT (which produces roles as
    dicts {"name":..., "description":...}, plus app_name/app_scope —
    unlike SYSTEM_PROMPT which produces roles as plain strings and has
    no scope concept at all).
 
    If existing_app_scope is provided (app already exists — Scenario 2/3
    from discovery), the LLM is instructed to reuse that EXACT scope
    instead of inventing a new one, preventing duplicate-scope conflicts.
    """
    feature_instruction = (
        f"Generate ONLY these components: {', '.join(selected_features)}. "
        f"Do not generate any other components. "
        f"Only include JSON keys for the requested components. "
        f"HOWEVER, you MUST ALWAYS include \"app_name\" and \"app_scope\" "
        f"at the top level regardless of which components were selected — "
        f"these are required identity fields, not optional components."
    )
 
    scope_instruction = ""
    if existing_app_scope:
        scope_instruction = (
            f"\n\nIMPORTANT: This app ALREADY EXISTS with scope '{existing_app_scope}'. "
            f"You MUST use app_scope: \"{existing_app_scope}\" exactly — "
            f"do not invent a new scope. All table_name and role name values "
            f"must be prefixed with this exact scope."
        )
 
    scoped_prompt = f"{prompt}\n\nIMPORTANT: {feature_instruction}{scope_instruction}"
 
    release_check = _check_release_notes_for_scoped_app(prompt, selected_features)
 
    system_prompt = SCOPED_APP_PROMPT
    if release_check["has_relevant_changes"]:
        system_prompt = (
            f"{SCOPED_APP_PROMPT}\n\n"
            f"RECENT SERVICENOW RELEASE NOTES RELEVANT TO THIS REQUEST "
            f"(organized by component):\n"
            f"{release_check['context_block']}\n\n"
            f"{RELEASE_IMPACT_INSTRUCTION}"
        )
 
    client = get_openai_client()
    response = client.chat.completions.create(
        model=OPENAI_DEPLOYMENT,
        temperature=0.2,
        max_tokens=3500,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": scoped_prompt}
        ]
    )
 
    llm_response = response.choices[0].message.content
    llm_response = re.sub(r'```json\n?|```\n?', '', llm_response).strip()
    blueprint    = json.loads(llm_response)
 
    # ── DEFENSIVE FALLBACK ───────────────────────────────────────────────────
    # If the LLM still omitted app_name/app_scope despite the instruction
    # above (LLMs aren't 100% reliable at following "always include" rules
    # when also told "only include selected components"), derive them
    # ourselves instead of crashing downstream in _push_scoped_blueprint().
    if not blueprint.get("app_name"):
        # Reuse existing scope's implied name if available, else fall back to prompt
        blueprint["app_name"] = prompt.strip()[:80]
        print(f"  ⚠️  LLM omitted app_name — defaulted to: '{blueprint['app_name']}'")
 
    if not blueprint.get("app_scope"):
        if existing_app_scope:
            # Scenario 2/3: app already exists, MUST reuse its real scope
            blueprint["app_scope"] = existing_app_scope
            print(f"  ⚠️  LLM omitted app_scope — reused existing scope: '{existing_app_scope}'")
        else:
            # Scenario 1: derive a new scope from app_name
            clean_scope = re.sub(r'[^a-z0-9]+', '_', blueprint["app_name"].lower()).strip('_')[:15]
            blueprint["app_scope"] = f"x_{clean_scope}"
            print(f"  ⚠️  LLM omitted app_scope — derived: '{blueprint['app_scope']}'")
    # ── END DEFENSIVE FALLBACK ───────────────────────────────────────────────
 
    blueprint["_release_notes_check"] = {
        "checked":              True,
        "components_searched":  release_check["components_searched"],
        "sources_checked":      release_check["sources_checked"],
        "chunks_retrieved":     len(release_check["raw_results"]),
        "llm_reported_changes": len(blueprint.get("release_notes_impact", [])),
    }
 
    print("\n📋 PARTIAL SCOPED APP BLUEPRINT JSON:")
    print(json.dumps(blueprint, indent=2))
    print(f"\n📦 Blueprint keys: {list(blueprint.keys())}")
 
    return blueprint
 

# ─────────────────────────────────────────────────────────────────────────────
# FIX 3 & 4: Check-before-create helpers for Application and Menu
# ─────────────────────────────────────────────────────────────────────────────

def _get_or_create_application(module_name: str, scope: str) -> tuple:
    """
    Returns (app_sys_id, created: bool).
    Checks if application already exists before creating.
    FIX 3: prevents duplicate application creation on every build.
    """
    # Search sys_scope for existing application
    url = f"{SNOW_BASE_URL}/sys_scope?sysparm_query=nameLIKE{module_name}&sysparm_fields=name,sys_id&sysparm_limit=1"
    try:
        res     = safe_get(url)
        results = res.json().get("result", [])
        if results:
            sys_id = results[0].get("sys_id")
            print(f"  ℹ️  Application '{module_name}' already exists. Reusing sys_id: {sys_id}")
            return sys_id, False
    except Exception:
        pass

    # Not found — create it
    ok, sys_id = create_snow_application(module_name, scope)
    if ok:
        print(f"  ✅ Application '{module_name}' created. sys_id: {sys_id}")
        return sys_id, True
    print(f"  ❌ Failed to create application '{module_name}'")
    return None, False


def _get_or_create_app_menu(module_name: str, app_sys_id: str) -> tuple:
    """
    Returns (menu_sys_id, created: bool).
    Checks if menu already exists before creating.
    FIX 4: prevents duplicate menu creation on every build.
    """
    url = f"{SNOW_BASE_URL}/sys_app_application?sysparm_query=titleLIKE{module_name}&sysparm_fields=title,sys_id&sysparm_limit=1"
    try:
        res     = safe_get(url)
        results = res.json().get("result", [])
        if results:
            sys_id = results[0].get("sys_id")
            print(f"  ℹ️  App Menu '{module_name}' already exists. Reusing sys_id: {sys_id}")
            return sys_id, False
    except Exception:
        pass

    ok, sys_id = create_snow_app_menu(module_name, app_sys_id)
    if ok:
        print(f"  ✅ App Menu '{module_name}' created. sys_id: {sys_id}")
        return sys_id, True
    print(f"  ❌ Failed to create app menu '{module_name}'")
    return None, False


# ─────────────────────────────────────────────────────────────────────────────
# HELPER — Generate blueprint from LLM for only the selected features
# ─────────────────────────────────────────────────────────────────────────────

# def _generate_partial_blueprint(prompt: str, selected_features: list) -> dict:
#     feature_instruction = (
#         f"Generate ONLY these components: {', '.join(selected_features)}. "
#         f"Do not generate any other components. "
#         f"Only include JSON keys for the requested components."
#     )
#     scoped_prompt = f"{prompt}\n\nIMPORTANT: {feature_instruction}"

#     client = get_openai_client()
#     response = client.chat.completions.create(
#         model=OPENAI_DEPLOYMENT,
#         temperature=0.2,
#         max_tokens=3000,
#         messages=[
#             {"role": "system", "content": SYSTEM_PROMPT},
#             {"role": "user",   "content": scoped_prompt}
#         ]
#     )

#     llm_response = response.choices[0].message.content
#     llm_response = re.sub(r'```json\n?|```\n?', '', llm_response).strip()
#     blueprint    = json.loads(llm_response)

#     # ── KEY REMAPPING — normalize LLM key variations ──────────────────────
#     if blueprint.get("access_controls") and not blueprint.get("acls"):
#         blueprint["acls"] = blueprint["access_controls"]
#         print("  🔄 Remapped 'access_controls' → 'acls'")
#     if not blueprint.get("navigation"):
#         for alt in ["nav_modules", "nav", "navigation_modules"]:
#             if blueprint.get(alt):
#                 blueprint["navigation"] = blueprint[alt]
#                 print(f"  🔄 Remapped '{alt}' → 'navigation'")
#                 break
#     if blueprint.get("properties") and not blueprint.get("system_properties"):
#         blueprint["system_properties"] = blueprint["properties"]
#         print("  🔄 Remapped 'properties' → 'system_properties'")
#     if blueprint.get("scripts") and not blueprint.get("client_scripts"):
#         blueprint["client_scripts"] = blueprint["scripts"]
#         print("  🔄 Remapped 'scripts' → 'client_scripts'")
#     if blueprint.get("includes") and not blueprint.get("script_includes"):
#         blueprint["script_includes"] = blueprint["includes"]
#         print("  🔄 Remapped 'includes' → 'script_includes'")
        

#     print("\n📋 PARTIAL BLUEPRINT JSON:")
#     print(json.dumps(blueprint, indent=2))
#     print(f"\n📦 Blueprint keys: {list(blueprint.keys())}")

#     return blueprint

def _generate_partial_blueprint(prompt: str, selected_features: list, mode: str = "module") -> dict:
    feature_instruction = (
        f"Generate ONLY these components: {', '.join(selected_features)}. "
        f"Do not generate any other components. "
        f"Only include JSON keys for the requested components."
    )
    scoped_prompt = f"{prompt}\n\nIMPORTANT: {feature_instruction}"

    client = get_openai_client()
    response = client.chat.completions.create(
        model=OPENAI_DEPLOYMENT,
        temperature=0.2,
        max_tokens=3000,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": scoped_prompt}
        ]
    )

    llm_response = response.choices[0].message.content
    llm_response = re.sub(r'```json\n?|```\n?', '', llm_response).strip()
    blueprint    = json.loads(llm_response)

    # ── KEY REMAPPING — normalize LLM key variations ──────────────────────
    if blueprint.get("access_controls") and not blueprint.get("acls"):
        blueprint["acls"] = blueprint["access_controls"]
        print("  🔄 Remapped 'access_controls' → 'acls'")
    if not blueprint.get("navigation"):
        for alt in ["nav_modules", "nav", "navigation_modules"]:
            if blueprint.get(alt):
                blueprint["navigation"] = blueprint[alt]
                print(f"  🔄 Remapped '{alt}' → 'navigation'")
                break
    if blueprint.get("properties") and not blueprint.get("system_properties"):
        blueprint["system_properties"] = blueprint["properties"]
        print("  🔄 Remapped 'properties' → 'system_properties'")
    if blueprint.get("scripts") and not blueprint.get("client_scripts"):
        blueprint["client_scripts"] = blueprint["scripts"]
        print("  🔄 Remapped 'scripts' → 'client_scripts'")
    if blueprint.get("includes") and not blueprint.get("script_includes"):
        blueprint["script_includes"] = blueprint["includes"]
        print("  🔄 Remapped 'includes' → 'script_includes'")

    # ── SCOPED APP NORMALIZATION ─────────────────────────────────────────────
    # Regular modules use "module_name". Scoped apps need "app_name" AND
    # "app_scope" (e.g. "x_vendor_mgmt"). The LLM only ever produces
    # "module_name" / "description" regardless of mode, so when this
    # blueprint is destined for a scoped app, we derive the missing keys
    # here instead of leaving them None and crashing later in
    # create_scoped_app() (app_scope.lower() on NoneType).
    if mode == "scoped":
        app_name = (
            blueprint.get("app_name")
            or blueprint.get("module_name")
            or prompt.strip()
        )
        blueprint["app_name"] = app_name

        if not blueprint.get("app_scope"):
            clean_scope = re.sub(r'[^a-z0-9]+', '_', app_name.lower()).strip('_')[:18]
            blueprint["app_scope"] = f"x_{clean_scope}"
            print(f"  🔄 Derived app_scope '{blueprint['app_scope']}' from app_name '{app_name}'")

    print("\n📋 PARTIAL BLUEPRINT JSON:")
    print(json.dumps(blueprint, indent=2))
    print(f"\n📦 Blueprint keys: {list(blueprint.keys())}")

    return blueprint
# ─────────────────────────────────────────────────────────────────────────────
# HELPER — Push blueprint to ServiceNow
# FIX 3, 4, 5, 8, 10: reuses existing app/menu, links nav to menu,
# supports building into existing app, skips apis/dashboards gracefully
# ─────────────────────────────────────────────────────────────────────────────

def _push_blueprint(blueprint: dict, module_name: str,
                    existing_app_sys_id: str = None,
                    existing_menu_sys_id: str = None) -> dict:
    """
    Pushes a blueprint to ServiceNow.

    FIX 3 & 4: Accepts existing app/menu sys_ids from discovery.
                If provided, skips creation and reuses them.
    FIX 8:      Supports building into an existing application.
    """
    result = {
        "module_name":               module_name,
        "description":               blueprint.get("description"),
        "raw_blueprint":             blueprint,
        "app_sys_id":                existing_app_sys_id,
        "menu_sys_id":               existing_menu_sys_id,
        "tables_created":            [],
        "fields_created":            [],
        "roles_created":             [],
        "forms_created":             [],
        "list_layouts_created":      [],
        "list_controls_created":     [],
        "access_controls_created":   [],
        "navigation_created":        [],
        "workflows_created":         [],
        "notifications_created":     [],
        "approvals_created":         [],
        "client_scripts_created":    [],
        "script_includes_created":   [],
        "system_properties_created": [],
        "relationships_created":     [],
        "related_lists_created":     [],
        # FIX 10: track skipped components
        "skipped_components":        [],
    }

    # ── FIX 3 & 4 & 8: APPLICATION + MENU — reuse if exists ────────────────
    print("\n🏢 RESOLVING APPLICATION & MENU...")
    scope = "x_" + module_name.lower().replace(" ", "_")[:15]

    if existing_app_sys_id:
        app_sys_id = existing_app_sys_id
        print(f"  ♻️  Reusing existing application sys_id: {app_sys_id}")
    else:
        app_sys_id, _ = _get_or_create_application(module_name, scope)
    result["app_sys_id"] = app_sys_id
    time.sleep(1)

    if existing_menu_sys_id:
        menu_sys_id = existing_menu_sys_id
        print(f"  ♻️  Reusing existing menu sys_id: {menu_sys_id}")
    else:
        menu_sys_id, _ = _get_or_create_app_menu(module_name, app_sys_id)
    result["menu_sys_id"] = menu_sys_id
    time.sleep(1)

    # ── 1. ROLES ────────────────────────────────────────────────────────────
    # if blueprint.get("roles"):
    #     print("\n🔐 PUSHING ROLES...")
    #     for role_name in blueprint.get("roles", []):
    #         ok, _ = create_snow_role(role_name)
    #         print(f"  {'✅' if ok else '❌'} Role: {role_name}")
    #         if ok:
    #             result["roles_created"].append(role_name)

    print("\n🔐 PUSHING ROLES...")
    for role in blueprint.get("roles", []):
        if isinstance(role, str):
            role_name = role
            role_desc = ""
        else:
            role_name = role.get("name", "")
            role_desc = role.get("description", "")

        if not role_name:
            continue

        ok, _ = create_scoped_role(role_name, role_desc, app_scope, app_sys_id)
        print(f"  {'✅' if ok else '❌'} Role: {role_name}")
        if ok:
            result["roles_created"].append(role_name)
        time.sleep(0.5)

    # ── 2. TABLES + FIELDS ──────────────────────────────────────────────────
    if blueprint.get("tables"):
        print("\n🏗️  PUSHING TABLES & FIELDS...")
        for table_def in blueprint.get("tables", []):
            t_label = table_def.get("table_label")
            t_name  = table_def.get("table_name")
            print(f"\n  📋 Table: {t_label} ({t_name})")
            success, _ = create_snow_table(t_label, t_name)
            if not success:
                print(f"  ❌ Skipping table: {t_name}")
                continue
            result["tables_created"].append(t_label)
            for field in table_def.get("fields", []):
                ok = create_snow_field(t_name, field.get("field_label"), field.get("field_name"), field.get("internal_type"))
                print(f"    {'✅' if ok else '❌'} Field: {field.get('field_label')} ({field.get('internal_type')})")
                if ok:
                    result["fields_created"].append(field.get("field_name"))

    tables        = blueprint.get("tables", [])
    default_table = tables[0].get("table_name") if tables else ""

    # ── 3. FORMS ────────────────────────────────────────────────────────────
    if blueprint.get("forms"):
        print("\n📄 PUSHING FORMS...")
        for form in blueprint.get("forms", []):
            ok, _ = create_snow_form(form.get("form_name"), form.get("target_table"), form.get("visible_fields", []))
            print(f"  {'✅' if ok else '❌'} Form: {form.get('form_name')}")
            if ok:
                result["forms_created"].append(form.get("form_name"))

    # ── 4. LIST LAYOUTS ─────────────────────────────────────────────────────
    if blueprint.get("list_layouts"):
        print("\n📋 PUSHING LIST LAYOUTS...")
        for layout in blueprint.get("list_layouts", []):
            t_name  = layout.get("table_name", default_table)
            columns = layout.get("columns", [])
            ok, _   = create_list_layout(t_name, columns)
            print(f"  {'✅' if ok else '❌'} List Layout: {t_name}")
            if ok:
                result["list_layouts_created"].append(t_name)
                ctrl_ok, _ = create_list_control(t_name)
                if ctrl_ok:
                    result["list_controls_created"].append(t_name)
            time.sleep(0.5)

    # ── 5. ACCESS CONTROLS ──────────────────────────────────────────────────
    acls = blueprint.get("acls") or blueprint.get("access_controls") or []
    if acls:
        print("\n🔒 PUSHING ACCESS CONTROLS...")
        for acl in acls:
            ok = create_acl(acl.get("table"), acl.get("operation"), acl.get("role"), acl.get("description", ""), None)
            print(f"  {'✅' if ok else '❌'} ACL: {acl.get('operation')} on {acl.get('table')}")
            if ok:
                result["access_controls_created"].append(f"{acl.get('operation')} on {acl.get('table')}")
            time.sleep(0.3)

    # ── 6. NAVIGATION ── FIX 5: pass menu_sys_id so nav links to app menu ──
    nav_items = blueprint.get("navigation") or []
    if nav_items:
        print("\n🧭 PUSHING NAVIGATION MODULES...")
        for nav in nav_items:
            # FIX 5: menu_sys_id passed so navigation is linked to this application
            ok = create_snow_navigation(nav.get("title"), nav.get("table"), menu_sys_id)
            print(f"  {'✅' if ok else '❌'} Nav: {nav.get('title')}")
            if ok:
                result["navigation_created"].append(nav.get("title"))
            time.sleep(0.3)
    elif blueprint.get("tables"):
        # Fallback: nav from tables
        print("\n🧭 PUSHING NAVIGATION (from tables)...")
        for table_def in blueprint.get("tables", []):
            # FIX 5: menu_sys_id passed here too
            ok = create_snow_navigation(table_def.get("table_label"), table_def.get("table_name"), menu_sys_id)
            print(f"  {'✅' if ok else '❌'} Nav: {table_def.get('table_label')}")
            if ok:
                result["navigation_created"].append(table_def.get("table_label"))

    # ── 7. WORKFLOWS ────────────────────────────────────────────────────────
    if blueprint.get("workflows"):
        print("\n⚙️  PUSHING WORKFLOWS...")
        for workflow in blueprint.get("workflows", []):
            ok = create_snow_workflow(name=workflow.get("name"), table_name=default_table,
                                      trigger=workflow.get("trigger", "On Insert"), steps=workflow.get("steps", []))
            print(f"  {'✅' if ok else '❌'} Workflow: {workflow.get('name')}")
            if ok:
                result["workflows_created"].append(workflow.get("name"))
            time.sleep(1)

    # ── 8. NOTIFICATIONS ────────────────────────────────────────────────────
    if blueprint.get("notifications"):
        print("\n📧 PUSHING NOTIFICATIONS...")
        for notif in blueprint.get("notifications", []):
            ok = create_snow_notification(notif.get("name"), default_table, notif.get("trigger", ""), notif.get("recipient", ""))
            print(f"  {'✅' if ok else '❌'} Notification: {notif.get('name')}")
            if ok:
                result["notifications_created"].append(notif.get("name"))

    # ── 9. APPROVALS ────────────────────────────────────────────────────────
    if blueprint.get("approvals"):
        print("\n✅ PUSHING APPROVALS...")
        for approval in blueprint.get("approvals", []):
            ok = create_snow_approval(approval.get("name"), default_table, approval.get("condition", ""), approval.get("approver_role", ""))
            print(f"  {'✅' if ok else '❌'} Approval: {approval.get('name')}")
            if ok:
                result["approvals_created"].append(approval.get("name"))

    # ── 10. CLIENT SCRIPTS ──────────────────────────────────────────────────
    if blueprint.get("client_scripts"):
        print("\n💻 PUSHING CLIENT SCRIPTS...")
        for cs in blueprint.get("client_scripts", []):
            ok, _ = create_client_script(
                table_name=cs.get("table", default_table), script_name=cs.get("name"),
                script_type=cs.get("type", "onLoad"), field_name=cs.get("field_name", ""),
                script_body=cs.get("script", "function onLoad() {}"),
            )
            print(f"  {'✅' if ok else '❌'} Client Script: {cs.get('name')} ({cs.get('type')})")
            if ok:
                result["client_scripts_created"].append(cs.get("name"))
            time.sleep(0.3)

    # ── 11. SCRIPT INCLUDES ─────────────────────────────────────────────────
    if blueprint.get("script_includes"):
        print("\n📚 PUSHING SCRIPT INCLUDES...")
        for si in blueprint.get("script_includes", []):
            ok, _ = create_script_include(
                name=si.get("name"), description=si.get("description", ""),
                script_body=si.get("script", f"var {si.get('name')} = Class.create(); {si.get('name')}.prototype = {{ initialize: function() {{}}, type: '{si.get('name')}' }};")
            )
            print(f"  {'✅' if ok else '❌'} Script Include: {si.get('name')}")
            if ok:
                result["script_includes_created"].append(si.get("name"))
            time.sleep(0.3)

    # ── 12. SYSTEM PROPERTIES ───────────────────────────────────────────────
    if blueprint.get("system_properties"):
        print("\n⚙️  PUSHING SYSTEM PROPERTIES...")
        for prop in blueprint.get("system_properties", []):
            ok, _ = create_system_property(
                name=prop.get("name"), value=prop.get("value", ""),
                description=prop.get("description", ""), prop_type=prop.get("type", "string")
            )
            print(f"  {'✅' if ok else '❌'} Property: {prop.get('name')} = {prop.get('value')}")
            if ok:
                result["system_properties_created"].append(prop.get("name"))
            time.sleep(0.3)

    # ── 13. RELATIONSHIPS ───────────────────────────────────────────────────
    if blueprint.get("relationships"):
        print("\n🔗 PUSHING RELATIONSHIPS...")
        for rel in blueprint.get("relationships", []):
            ok, _ = create_relationship(
                name=rel.get("name"), parent_table=rel.get("parent_table"),
                child_table=rel.get("child_table"), query_with=rel.get("query_with", "")
            )
            print(f"  {'✅' if ok else '❌'} Relationship: {rel.get('name')}")
            if ok:
                result["relationships_created"].append(rel.get("name"))
                rl_ok, _ = create_related_list(
                    parent_table=rel.get("parent_table"), child_table=rel.get("child_table"),
                    ref_field=rel.get("query_with", ""), title=f"{rel.get('child_table')} List"
                )
                if rl_ok:
                    result["related_lists_created"].append(rel.get("name"))
            time.sleep(0.3)

    # ── FIX 10: Log skipped components (apis, dashboards) ───────────────────
    for skipped_key in ["apis", "dashboards"]:
        if blueprint.get(skipped_key):
            count = len(blueprint[skipped_key])
            print(f"\n⏭️  SKIPPING '{skipped_key}' ({count} item(s)) — not supported by ServiceNow Table API.")
            result["skipped_components"].append(skipped_key)

    print("\n🎉 BUILD COMPLETE!")
    print("=" * 50)
    return result


# ─────────────────────────────────────────────────────────────────────────────
# SMART BUILD — Handles all 3 scenarios
# FIX 6: passes existing app/menu sys_ids from discovery to _push_blueprint
# ─────────────────────────────────────────────────────────────────────────────

def smart_build_module(prompt: str, module_name: str, selected_features: list) -> dict:
    print("\n" + "=" * 60)
    print(f"🚀 SMART BUILD: '{module_name}'")
    print("=" * 60)

    discovery      = discover_module(module_name)
    scenario       = discovery["scenario"]
    scenario_label = discovery["scenario_label"]

    print(f"\n📌 SCENARIO {scenario}: {scenario_label.upper()}")
    print(f"   Selected features to build: {selected_features}")

    if scenario == 3:
        missing_keys     = discovery["missing_keys"]
        invalid_selected = [f for f in selected_features if f not in missing_keys]
        if invalid_selected:
            print(f"\n⚠️  Already exist, skipping: {invalid_selected}")
            selected_features = [f for f in selected_features if f in missing_keys]

    if not selected_features:
        print("\n⚠️  No valid features selected. Nothing to build.")
        return {
            "scenario": scenario, "scenario_label": scenario_label,
            "discovery": discovery, "selected_features": selected_features, "build_result": None
        }

    print(f"\n🤖 GENERATING BLUEPRINT FOR: {selected_features}")
    blueprint = _generate_partial_blueprint(prompt, selected_features)

    # FIX 6: pass existing app/menu sys_ids so they are reused, not recreated
    build_result = _push_blueprint(
        blueprint,
        module_name,
        existing_app_sys_id=discovery.get("app_sys_id"),
        existing_menu_sys_id=discovery.get("menu_sys_id"),
    )

    return {
        "scenario": scenario, "scenario_label": scenario_label,
        "discovery": discovery, "selected_features": selected_features,
        "build_result": build_result
    }


# ─────────────────────────────────────────────────────────────────────────────
# DISCOVERY ONLY
# ─────────────────────────────────────────────────────────────────────────────

def get_module_status(module_name: str) -> dict:
    discovery = discover_module(module_name)
    scenario  = discovery["scenario"]

    if scenario == 1:
        ui_message = f"No existing '{module_name}' module found in ServiceNow. Select the features you want to create."
    elif scenario == 2:
        ui_message = f"'{module_name}' is fully implemented in ServiceNow. You can still add enhancements."
    else:
        pct = discovery["summary"]["completion_percent"]
        ui_message = (
            f"'{module_name}' is {pct}% complete. "
            f"{len(discovery['implemented_keys'])} components exist, "
            f"{len(discovery['missing_keys'])} are missing."
        )

    discovery["ui_message"] = ui_message
    return discovery


# ─────────────────────────────────────────────────────────────────────────────
# NEW: SCOPED APP 3-SCENARIO MANAGEMENT
# ─────────────────────────────────────────────────────────────────────────────

def get_scoped_app_status(app_name: str) -> dict:
    """
    Retrieves status summary and tracks completion matrix for Scoped App entities.
    """
    discovery = discover_scoped_app(app_name)
    scenario = discovery["scenario"]

    if scenario == 1:
        ui_message = f"No existing scoped app '{app_name}' discovered in ServiceNow. Configure your missing features to initiate setup."
    elif scenario == 2:
        ui_message = f"Scoped app '{app_name}' is completely implemented in ServiceNow."
    else:
        pct = discovery["summary"]["completion_percent"]
        ui_message = (
            f"Scoped app '{app_name}' is {pct}% complete. "
            f"{len(discovery['implemented_keys'])} features exist, "
            f"{len(discovery['missing_keys'])} are currently missing."
        )

    discovery["ui_message"] = ui_message
    return discovery


def smart_build_scoped_app(prompt: str, app_name: str, selected_features: list) -> dict:
    """
    Builds or patches a Scoped App selectively by scanning the current environment first.
    Reuses existing sys_ids if found to prevent collisions or split-scope duplication.
    """
    print("\n" + "=" * 60)
    print(f"🚀 SMART SCOPED APP BUILD: '{app_name}'")
    print("=" * 60)

    discovery = discover_scoped_app(app_name)
    scenario = discovery["scenario"]
    scenario_label = discovery["scenario_label"]

    print(f"\n📌 SCENARIO {scenario}: {scenario_label.upper()}")
    print(f"   Selected features to build: {selected_features}")

    if scenario == 3:
        missing_keys = discovery["missing_keys"]
        invalid_selected = [f for f in selected_features if f not in missing_keys]
        if invalid_selected:
            print(f"\n⚠️   Already exist, skipping from build matrix: {invalid_selected}")
            selected_features = [f for f in selected_features if f in missing_keys]

    if not selected_features:
        print("\n⚠️   No valid missing features chosen. Execution skipped.")
        return {
            "scenario": scenario, "scenario_label": scenario_label,
            "discovery": discovery, "selected_features": selected_features, "build_result": None
        }

    # Pass selected_features to filter the RAG lookup cleanly
    print(f"\n🤖 RUNNING RELEASE NOTE MATCHES & PROMPT GENERATION...")
    blueprint = build_scoped_app(prompt, selected_features=selected_features)

    return {
        "scenario": scenario, "scenario_label": scenario_label,
        "discovery": discovery, "selected_features": selected_features,
        "build_result": blueprint
    }


# ─────────────────────────────────────────────────────────────────────────────
# ORIGINAL FUNCTIONS — Backward compatibility
# ─────────────────────────────────────────────────────────────────────────────

def build_servicenow_module(prompt: str):
    print("\n" + "=" * 50)
    print(f"🚀 INITIATING MODULE CREATION: '{prompt}'")
    print("=" * 50)
    client = get_openai_client()
    response = client.chat.completions.create(
        model=OPENAI_DEPLOYMENT, temperature=0.2, max_tokens=2500,
        messages=[{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": prompt}]
    )
    llm_response = re.sub(r'```json\n?|```\n?', '', response.choices[0].message.content).strip()
    blueprint    = json.loads(llm_response)
    print(f"\n✅ Blueprint received for: {blueprint.get('module_name')}")
    return _push_blueprint(blueprint, blueprint.get("module_name"))


def build_servicenow_module_from_blueprint(blueprint: dict):
    print("\n" + "=" * 50)
    print(f"🚀 BUILDING FROM VALIDATED BLUEPRINT: '{blueprint.get('module_name')}'")
    print("=" * 50)
    return _push_blueprint(blueprint, blueprint.get("module_name"))


# def build_scoped_app(prompt: str):
#     print("\n" + "=" * 60)
#     print(f"🚀 INITIATING SCOPED APP CREATION: '{prompt}'")
#     print("=" * 60)
#     client = get_openai_client()
#     response = client.chat.completions.create(
#         model=OPENAI_DEPLOYMENT, temperature=0.2, max_tokens=3000,
#         messages=[{"role": "system", "content": SCOPED_APP_PROMPT}, {"role": "user", "content": prompt}]
#     )
#     llm_response = re.sub(r'```json\n?|```\n?', '', response.choices[0].message.content).strip()
#     blueprint    = json.loads(llm_response)
#     print(f"\n✅ Blueprint received for: {blueprint.get('app_name')} | Scope: {blueprint.get('app_scope')}")
#     return _push_scoped_blueprint(blueprint, blueprint.get("app_name"), blueprint.get("app_scope"), blueprint.get("description", ""))

# def build_scoped_app(prompt: str):
#     print("\n" + "=" * 60)
#     print(f"🚀 INITIATING SCOPED APP CREATION: '{prompt}'")
#     print("=" * 60)
 
#     # ── STEP 1: Check release notes for relevant platform changes ──────────
#     release_check = _check_release_notes_for_scoped_app(prompt)
 
#     # ── STEP 2: Build the system prompt — inject release note context if found
#     system_prompt = SCOPED_APP_PROMPT
#     if release_check["has_relevant_changes"]:
#         system_prompt = (
#             f"{SCOPED_APP_PROMPT}\n\n"
#             f"IMPORTANT — RECENT SERVICENOW RELEASE NOTES RELEVANT TO THIS REQUEST:\n"
#             f"{release_check['context_block']}\n\n"
#             f"Incorporate any deprecations, security updates, or new recommendations "
#             f"from the above into your generated blueprint. For example, if an older "
#             f"approach is deprecated, use the recommended replacement instead."
#         )
#         print("  🔄 Injecting release note context into generation prompt")
#     else:
#         print("  ➡️  Proceeding with standard generation workflow (no relevant changes found)")
 
#     # ── STEP 3: Generate blueprint with (possibly augmented) prompt ────────
#     client = get_openai_client()
#     response = client.chat.completions.create(
#         model=OPENAI_DEPLOYMENT,
#         temperature=0.2,
#         max_tokens=3000,
#         messages=[
#             {"role": "system", "content": system_prompt},
#             {"role": "user",   "content": prompt}
#         ]
#     )
 
#     llm_response = re.sub(r'```json\n?|```\n?', '', response.choices[0].message.content).strip()
#     blueprint     = json.loads(llm_response)
 
#     # Attach release note check info to blueprint for visibility/audit
#     blueprint["_release_notes_check"] = {
#         "checked":             True,
#         "has_relevant_changes": release_check["has_relevant_changes"],
#         "sources_checked":     release_check["sources_checked"],
#     }
 
#     print(f"\n✅ Blueprint received for: {blueprint.get('app_name')} | Scope: {blueprint.get('app_scope')}")
#     return _push_scoped_blueprint(
#         blueprint, blueprint.get("app_name"),
#         blueprint.get("app_scope"), blueprint.get("description", "")
#     )

def build_scoped_app(prompt: str, selected_features: list = None):
    print("\n" + "=" * 60)
    print(f"🚀 INITIATING SCOPED APP CREATION: '{prompt}'")
    print("=" * 60)
 
    release_check = _check_release_notes_for_scoped_app(prompt, selected_features)
 
    system_prompt = SCOPED_APP_PROMPT
    if release_check["has_relevant_changes"]:
        system_prompt = (
            f"{SCOPED_APP_PROMPT}\n\n"
            f"RECENT SERVICENOW RELEASE NOTES RELEVANT TO THIS REQUEST "
            f"(organized by component):\n"
            f"{release_check['context_block']}\n\n"
            f"{RELEASE_IMPACT_INSTRUCTION}"
        )
        print(f"  🔄 Injecting per-component release note context "
              f"({', '.join(release_check['sources_checked'])})")
    else:
        print("  ➡️  Proceeding with standard generation workflow (no relevant changes found)")
 
    client = get_openai_client()
    response = client.chat.completions.create(
        model=OPENAI_DEPLOYMENT,
        temperature=0.2,
        max_tokens=3500,   # increased slightly to fit release_notes_impact field
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": prompt}
        ]
    )
 
    llm_response = re.sub(r'```json\n?|```\n?', '', response.choices[0].message.content).strip()
    blueprint    = json.loads(llm_response)
 
    # Use the LLM's OWN reported impact — not our retrieval guess.
    # If LLM didn't include the key, default to empty (honest fallback).
    llm_reported_impact = blueprint.get("release_notes_impact", [])
 
    blueprint["_release_notes_check"] = {
        "checked":              True,
        "components_searched":  release_check["components_searched"],
        "sources_checked":      release_check["sources_checked"],
        "chunks_retrieved":     len(release_check["raw_results"]),
        "llm_reported_changes": len(llm_reported_impact),
    }
 
    print(f"\n✅ Blueprint received for: {blueprint.get('app_name')} | Scope: {blueprint.get('app_scope')}")
    print(f"   LLM self-reported {len(llm_reported_impact)} genuine release-note-driven change(s)")
 
    return _push_scoped_blueprint(
        blueprint, blueprint.get("app_name"),
        blueprint.get("app_scope"), blueprint.get("description", "")
    )
 

# def build_scoped_app_from_blueprint(blueprint: dict):
#     print("\n" + "=" * 60)
#     print(f"🚀 BUILDING SCOPED APP FROM VALIDATED BLUEPRINT: '{blueprint.get('app_name')}'")
#     print("=" * 60)
#     return _push_scoped_blueprint(blueprint, blueprint.get("app_name"), blueprint.get("app_scope"), blueprint.get("description", ""))

def build_scoped_app_from_blueprint(blueprint):
    app_name  = blueprint.get("app_name") or blueprint.get("module_name")
    app_scope = blueprint.get("app_scope")
    if not app_name or not app_scope:
        raise ValueError(
            f"Blueprint missing app_name/app_scope. "
            f"Keys present: {list(blueprint.keys())}"
        )
    return _push_scoped_blueprint(blueprint, app_name, app_scope, blueprint.get("description", ""))


# ─────────────────────────────────────────────────────────────────────────────
# SCOPED APP PUSH
# FIX 11: checks if scoped app already exists before creating
# FIX 10: skips apis/dashboards gracefully
# ─────────────────────────────────────────────────────────────────────────────

def _push_scoped_blueprint(blueprint: dict, app_name: str, app_scope: str, description: str) -> dict:
    result = {
        "app_name": app_name, "app_scope": app_scope, "description": description,
        "app_created": False, "menu_created": False, "roles_created": [],
        "tables_created": [], "fields_created": [], "forms_created": [],
        "acls_created": [], "workflows_created": [], "approvals_created": [],
        "notifications_created": [], "navigation_created": [],
        "skipped_components": [],  # FIX 10
    }

    # ── FIX 11: Check if scoped app already exists ───────────────────────────
    print("\n🏢 RESOLVING SCOPED APPLICATION...")
    existing_url = f"{SNOW_BASE_URL}/sys_app?sysparm_query=scope={app_scope}&sysparm_fields=name,sys_id&sysparm_limit=1"
    app_sys_id   = None
    try:
        res     = safe_get(existing_url)
        results = res.json().get("result", [])
        if results:
            app_sys_id = results[0].get("sys_id")
            print(f"  ℹ️  Scoped app scope '{app_scope}' already exists. Reusing sys_id: {app_sys_id}")
            result["app_created"] = False
    except Exception:
        pass

    if not app_sys_id:
        app_ok, app_sys_id = create_scoped_app(app_name, app_scope, description)
        result["app_created"] = app_ok
        time.sleep(5)
        if not app_ok:
            raise Exception(f"❌ Failed to create scoped app '{app_name}'.")

    # ── FIX 4: check menu before creating ───────────────────────────────────
    print("\n📂 RESOLVING APP MENU...")
    app_structure    = blueprint.get("app_structure", {})
    menus            = app_structure.get("menus", [])
    first_menu_title = menus[0].get("title", app_name) if menus else app_name
    menu_sys_id, _   = _get_or_create_app_menu(first_menu_title, app_sys_id)
    result["menu_created"] = menu_sys_id is not None
    time.sleep(2)

    print("\n🔐 PUSHING ROLES...")
    for role in blueprint.get("roles", []):
        ok, _ = create_scoped_role(role.get("name"), role.get("description", ""), app_scope, app_sys_id)
        print(f"  {'✅' if ok else '❌'} Role: {role.get('name')}")
        if ok: result["roles_created"].append(role.get("name"))
        time.sleep(0.5)

    print("\n🏗️  PUSHING TABLES & FIELDS...")
    for table_def in blueprint.get("tables", []):
        t_label = table_def.get("table_label")
        t_name  = table_def.get("table_name")
        success, _ = create_scoped_table(t_label, t_name, app_scope, app_sys_id)
        if not success: continue
        result["tables_created"].append(t_label)
        for field in table_def.get("fields", []):
            ok = create_scoped_field(t_name, field.get("field_label"), field.get("field_name"), field.get("internal_type"), app_sys_id)
            print(f"    {'✅' if ok else '❌'} Field: {field.get('field_label')}")
            if ok: result["fields_created"].append(field.get("field_name"))
        time.sleep(1)

    print("\n📄 PUSHING FORMS...")
    for form in blueprint.get("forms", []):
        ok, _ = create_snow_form(form.get("form_name"), form.get("target_table"), form.get("visible_fields", []), app_sys_id)
        print(f"  {'✅' if ok else '❌'} Form: {form.get('form_name')}")
        if ok: result["forms_created"].append(form.get("form_name"))
        time.sleep(0.5)

    print("\n🔒 PUSHING ACLs...")
    for acl in blueprint.get("acls", []):
        ok = create_acl(acl.get("table"), acl.get("operation"), acl.get("role"), acl.get("description", ""), app_sys_id)
        print(f"  {'✅' if ok else '❌'} ACL: {acl.get('operation')} on {acl.get('table')}")
        if ok: result["acls_created"].append(f"{acl.get('operation')} on {acl.get('table')}")
        time.sleep(0.5)

    print("\n📧 PUSHING NOTIFICATIONS...")
    for notif in blueprint.get("notifications", []):
        ok = create_snow_notification(notif.get("name"), notif.get("table", ""), notif.get("trigger", ""), notif.get("recipient_role", ""), app_sys_id)
        print(f"  {'✅' if ok else '❌'} Notification: {notif.get('name')}")
        if ok: result["notifications_created"].append(notif.get("name"))
        time.sleep(0.5)

    print("\n✅ PUSHING APPROVALS...")
    for approval in blueprint.get("approvals", []):
        ok = create_snow_approval(approval.get("name"), approval.get("table", ""), approval.get("condition", ""), approval.get("approver_role", ""), app_sys_id)
        print(f"  {'✅' if ok else '❌'} Approval: {approval.get('name')}")
        if ok: result["approvals_created"].append(approval.get("name"))
        time.sleep(0.5)

    print("\n⚙️  PUSHING WORKFLOWS...")
    for workflow in blueprint.get("workflows", []):
        ok = create_snow_workflow(workflow.get("name"), workflow.get("trigger_table", ""), workflow.get("trigger_event", "insert"), workflow.get("steps", []), app_sys_id)
        print(f"  {'✅' if ok else '❌'} Workflow: {workflow.get('name')}")
        if ok: result["workflows_created"].append(workflow.get("name"))
        time.sleep(0.5)

    # FIX 5: navigation linked to menu_sys_id
    print("\n🧭 PUSHING NAVIGATION MODULES...")
    modules = app_structure.get("modules", [])
    nav_items = modules or blueprint.get("tables", [])
    for item in nav_items:
        title = item.get("title") or item.get("table_label")
        table = item.get("table") or item.get("table_name")
        ok    = create_scoped_navigation(title, table, menu_sys_id, item.get("order", "100"), app_sys_id)
        print(f"  {'✅' if ok else '❌'} Nav: {title}")
        if ok: result["navigation_created"].append(title)
        time.sleep(0.5)

    # FIX 10: log skipped
    for skipped_key in ["apis", "dashboards"]:
        if blueprint.get(skipped_key):
            print(f"\n⏭️  SKIPPING '{skipped_key}' — not supported by ServiceNow Table API.")
            result["skipped_components"].append(skipped_key)

    print("\n🎉 SCOPED APP GENERATION COMPLETE!")
    print("=" * 50)
    return result


# -------------------------------------------- ATF validation -----------------------------------------------
#------------------------------------------------------------------------------------------------------------
def build_module_with_atf(prompt: str, module_name: str,
                           selected_features: list) -> dict:
    """
    Full pipeline:
    1. Runs discovery (3 scenarios)
    2. Generates partial blueprint
    3. Pushes blueprint to ServiceNow
    4. Generates ATF test suite
    5. Returns everything
 
    Returns:
    {
        "scenario":          int,
        "scenario_label":    str,
        "discovery":         dict,
        "selected_features": list,
        "build_result":      dict,
        "atf": {
            "suite_name":    str,
            "suite_sys_id":  str,
            "suite_url":     str,
            "tests_created": int,
            "tests":         list,
            "errors":        list
        }
    }
    """
    from atf_builder import build_atf_suite
 
    # Run the smart build (handles all 3 scenarios)
    smart_result = smart_build_module(prompt, module_name, selected_features)
 
    # If build succeeded, generate ATF suite
    blueprint    = _generate_partial_blueprint.__wrapped__ if hasattr(
        _generate_partial_blueprint, '__wrapped__') else None
    build_result = smart_result.get("build_result")
 
    atf_result = {"suite_sys_id": None, "tests_created": 0, "errors": ["Build did not complete"]}
 
    if build_result:
        raw_blueprint = build_result.get("raw_blueprint", {})
        atf_result    = build_atf_suite(module_name, build_result, raw_blueprint)
 
    return {
        **smart_result,
        "atf": atf_result,
    }
 
 
