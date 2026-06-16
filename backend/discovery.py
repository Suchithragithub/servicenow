# discovery.py
# Read-only scan of ServiceNow to detect existing module/app components.
# Zero writes — only GET calls.
# Now includes: Applications, App Menus, Scoped Apps with sys_id returns.

from snow_client import safe_get, SNOW_BASE_URL


# ─────────────────────────────────────────
# COMPONENT CHECKERS
# ─────────────────────────────────────────

def _find_tables(keyword: str) -> list:
    url = f"{SNOW_BASE_URL}/sys_db_object?sysparm_query=nameLIKE{keyword}^ORlabelLIKE{keyword}&sysparm_fields=name,label,sys_id&sysparm_limit=20"
    try:
        res = safe_get(url)
        return [{"name": r.get("name"), "label": r.get("label"), "sys_id": r.get("sys_id")} for r in res.json().get("result", [])]
    except Exception:
        return []

def _find_fields(table_name: str) -> list:
    url = f"{SNOW_BASE_URL}/sys_dictionary?sysparm_query=name={table_name}^elementSTARTSWITHu_&sysparm_fields=element,column_label,internal_type&sysparm_limit=50"
    try:
        res = safe_get(url)
        return [{"field_name": r.get("element"), "field_label": r.get("column_label"), "type": r.get("internal_type")} for r in res.json().get("result", [])]
    except Exception:
        return []

def _find_roles(keyword: str) -> list:
    url = f"{SNOW_BASE_URL}/sys_user_role?sysparm_query=nameLIKE{keyword}&sysparm_fields=name,sys_id&sysparm_limit=20"
    try:
        res = safe_get(url)
        return [{"name": r.get("name"), "sys_id": r.get("sys_id")} for r in res.json().get("result", [])]
    except Exception:
        return []

def _find_forms(keyword: str) -> list:
    url = f"{SNOW_BASE_URL}/sys_ui_section?sysparm_query=nameLIKE{keyword}^ORtitleLIKE{keyword}&sysparm_fields=name,title,sys_id&sysparm_limit=20"
    try:
        res = safe_get(url)
        return [{"name": r.get("name"), "title": r.get("title"), "sys_id": r.get("sys_id")} for r in res.json().get("result", [])]
    except Exception:
        return []

def _find_list_layouts(keyword: str) -> list:
    url = f"{SNOW_BASE_URL}/sys_ui_list?sysparm_query=nameLIKE{keyword}&sysparm_fields=name,sys_id&sysparm_limit=20"
    try:
        res = safe_get(url)
        return [{"name": r.get("name"), "sys_id": r.get("sys_id")} for r in res.json().get("result", [])]
    except Exception:
        return []

def _find_client_scripts(keyword: str) -> list:
    url = f"{SNOW_BASE_URL}/sys_script_client?sysparm_query=tableLIKE{keyword}^ORnameLIKE{keyword}&sysparm_fields=name,table,type,sys_id&sysparm_limit=20"
    try:
        res = safe_get(url)
        return [{"name": r.get("name"), "table": r.get("table"), "type": r.get("type")} for r in res.json().get("result", [])]
    except Exception:
        return []

def _find_script_includes(keyword: str) -> list:
    url = f"{SNOW_BASE_URL}/sys_script_include?sysparm_query=nameLIKE{keyword}&sysparm_fields=name,sys_id&sysparm_limit=20"
    try:
        res = safe_get(url)
        return [{"name": r.get("name"), "sys_id": r.get("sys_id")} for r in res.json().get("result", [])]
    except Exception:
        return []

def _find_access_controls(keyword: str) -> list:
    url = f"{SNOW_BASE_URL}/sys_security_acl?sysparm_query=nameLIKE{keyword}&sysparm_fields=name,operation,type,sys_id&sysparm_limit=20"
    try:
        res = safe_get(url)
        return [{"name": r.get("name"), "operation": r.get("operation")} for r in res.json().get("result", [])]
    except Exception:
        return []

def _find_system_properties(keyword: str) -> list:
    url = f"{SNOW_BASE_URL}/sys_properties?sysparm_query=nameLIKE{keyword}&sysparm_fields=name,value,sys_id&sysparm_limit=20"
    try:
        res = safe_get(url)
        return [{"name": r.get("name"), "value": r.get("value")} for r in res.json().get("result", [])]
    except Exception:
        return []

def _find_navigation(keyword: str) -> list:
    url = f"{SNOW_BASE_URL}/sys_app_module?sysparm_query=titleLIKE{keyword}^ORnameLIKE{keyword}&sysparm_fields=title,name,sys_id&sysparm_limit=20"
    try:
        res = safe_get(url)
        return [{"title": r.get("title"), "table": r.get("name"), "sys_id": r.get("sys_id")} for r in res.json().get("result", [])]
    except Exception:
        return []

def _find_workflows(keyword: str) -> list:
    url = f"{SNOW_BASE_URL}/wf_workflow?sysparm_query=nameLIKE{keyword}&sysparm_fields=name,table,active,sys_id&sysparm_limit=20"
    try:
        res = safe_get(url)
        return [{"name": r.get("name"), "table": r.get("table"), "active": r.get("active")} for r in res.json().get("result", [])]
    except Exception:
        return []

def _find_notifications(keyword: str) -> list:
    url = f"{SNOW_BASE_URL}/sysevent_email_action?sysparm_query=nameLIKE{keyword}&sysparm_fields=name,collection,active,sys_id&sysparm_limit=20"
    try:
        res = safe_get(url)
        return [{"name": r.get("name"), "table": r.get("collection"), "active": r.get("active")} for r in res.json().get("result", [])]
    except Exception:
        return []

def _find_approvals(keyword: str) -> list:
    url = f"{SNOW_BASE_URL}/sys_script?sysparm_query=nameLIKE{keyword}&sysparm_fields=name,collection,active,sys_id&sysparm_limit=20"
    try:
        res = safe_get(url)
        return [{"name": r.get("name"), "table": r.get("collection"), "active": r.get("active")} for r in res.json().get("result", [])]
    except Exception:
        return []

def _find_relationships(keyword: str) -> list:
    url = f"{SNOW_BASE_URL}/sys_relationship?sysparm_query=nameLIKE{keyword}&sysparm_fields=name,parent_table,child_table,sys_id&sysparm_limit=20"
    try:
        res = safe_get(url)
        return [{"name": r.get("name"), "parent": r.get("parent_table"), "child": r.get("child_table")} for r in res.json().get("result", [])]
    except Exception:
        return []

# ─────────────────────────────────────────
# FIX 1 & 2 & 6 & 11: Application + Menu + Scoped App discovery
# Now returns sys_ids so build process can reuse existing records
# ─────────────────────────────────────────

def _find_application(keyword: str) -> dict:
    """
    Searches sys_scope (global app) and sys_app (scoped app) for matching application.
    Returns: { "found": bool, "sys_id": str|None, "name": str|None, "scope": str|None, "type": "global"|"scoped"|None }
    """
    keyword_search = keyword.replace("_", " ")

    # Check sys_scope (global custom applications)
    url_scope = f"{SNOW_BASE_URL}/sys_scope?sysparm_query=nameLIKE{keyword_search}&sysparm_fields=name,scope,sys_id&sysparm_limit=5"
    try:
        res = safe_get(url_scope)
        results = res.json().get("result", [])
        if results:
            r = results[0]
            return {"found": True, "sys_id": r.get("sys_id"), "name": r.get("name"), "scope": r.get("scope"), "type": "global"}
    except Exception:
        pass

    # Check sys_app (scoped applications)
    url_app = f"{SNOW_BASE_URL}/sys_app?sysparm_query=nameLIKE{keyword_search}&sysparm_fields=name,scope,sys_id&sysparm_limit=5"
    try:
        res = safe_get(url_app)
        results = res.json().get("result", [])
        if results:
            r = results[0]
            return {"found": True, "sys_id": r.get("sys_id"), "name": r.get("name"), "scope": r.get("scope"), "type": "scoped"}
    except Exception:
        pass

    return {"found": False, "sys_id": None, "name": None, "scope": None, "type": None}


def _find_app_menu(keyword: str, app_sys_id: str = None) -> dict:
    """
    Searches sys_app_application for matching application menu.
    Returns: { "found": bool, "sys_id": str|None, "title": str|None }
    """
    keyword_search = keyword.replace("_", " ")

    query = f"titleLIKE{keyword_search}"
    if app_sys_id:
        query += f"^sys_scope={app_sys_id}"

    url = f"{SNOW_BASE_URL}/sys_app_application?sysparm_query={query}&sysparm_fields=title,sys_id&sysparm_limit=5"
    try:
        res = safe_get(url)
        results = res.json().get("result", [])
        if results:
            r = results[0]
            return {"found": True, "sys_id": r.get("sys_id"), "title": r.get("title")}
    except Exception:
        pass

    return {"found": False, "sys_id": None, "title": None}


# ─────────────────────────────────────────
# STANDARD FEATURE CATALOG
# FIX 7: Now includes application + app_menu in standard features
# so they count toward completion percentage
# ─────────────────────────────────────────

STANDARD_FEATURES = {
    "default": [
        "application",        # FIX 7: added
        # "app_menu",           # FIX 7: added
        "tables",
        "fields",
        "roles",
        "forms",
        "list_layouts",
        "access_controls",
        "navigation",
        "workflows",
        "notifications",
        "approvals",
        "client_scripts",
        "script_includes",
        "system_properties",
        "relationships",
    ]
}

def get_standard_features(module_name: str) -> list:
    key = module_name.lower().replace(" ", "_")
    return STANDARD_FEATURES.get(key, STANDARD_FEATURES["default"])


# ─────────────────────────────────────────
# MAIN DISCOVERY FUNCTION
# FIX 1, 2, 6, 7, 11: Now discovers apps + menus, returns sys_ids
# ─────────────────────────────────────────

def discover_module(module_name: str) -> dict:
    """
    Scans ServiceNow for all components related to a module name.
    Now includes application and app_menu discovery with sys_id returns.
    """
    keyword        = module_name.lower().replace(" ", "_")
    keyword_search = module_name.lower().replace("_", " ")

    print(f"\n🔍 DISCOVERING: '{module_name}' (keyword: {keyword})")

    # ── Discover application and menu first (needed for sys_ids) ──
    app_info  = _find_application(keyword_search)
    menu_info = _find_app_menu(keyword_search, app_info.get("sys_id"))

    print(f"   🏢 Application : {'✅ ' + app_info['name'] if app_info['found'] else '❌ Not found'}")
    print(f"   📂 App Menu    : {'✅ ' + menu_info['title'] if menu_info['found'] else '❌ Not found'}")

    # ── Discover all other components ──
    tables          = _find_tables(keyword_search)
    roles           = _find_roles(keyword)
    forms           = _find_forms(keyword_search)
    list_layouts    = _find_list_layouts(keyword)
    client_scripts  = _find_client_scripts(keyword)
    script_includes = _find_script_includes(keyword)
    access_controls = _find_access_controls(keyword)
    system_props    = _find_system_properties(keyword)
    navigation      = _find_navigation(keyword_search)
    workflows       = _find_workflows(keyword_search)
    notifications   = _find_notifications(keyword_search)
    approvals       = _find_approvals(keyword_search)
    relationships   = _find_relationships(keyword_search)

    all_fields = []
    for table in tables:
        all_fields.extend(_find_fields(table["name"]))

    implemented = {
        "application":       [app_info]  if app_info["found"]  else [],  # FIX 1 & 6
        "app_menu":          [menu_info] if menu_info["found"] else [],  # FIX 2 & 6
        "tables":            tables,
        "fields":            all_fields,
        "roles":             roles,
        "forms":             forms,
        "list_layouts":      list_layouts,
        "client_scripts":    client_scripts,
        "script_includes":   script_includes,
        "access_controls":   access_controls,
        "system_properties": system_props,
        "navigation":        navigation,
        "workflows":         workflows,
        "notifications":     notifications,
        "approvals":         approvals,
        "relationships":     relationships,
    }

    standard_features  = get_standard_features(module_name)
    implemented_keys   = [k for k in standard_features if implemented.get(k)]
    missing_keys       = [k for k in standard_features if not implemented.get(k)]

    total             = len(standard_features)
    implemented_count = len(implemented_keys)
    missing_count     = len(missing_keys)
    completion_pct    = int((implemented_count / total) * 100) if total else 0

    if implemented_count == 0:
        scenario       = 1
        scenario_label = "not_found"
    elif missing_count == 0:
        scenario       = 2
        scenario_label = "fully_implemented"
    else:
        scenario       = 3
        scenario_label = "partial"

    result = {
        "scenario":          scenario,
        "scenario_label":    scenario_label,
        "module_name":       module_name,
        "keyword":           keyword,
        "implemented":       implemented,
        "implemented_keys":  implemented_keys,
        "missing_keys":      missing_keys,
        # FIX 6: expose app + menu sys_ids for reuse in build process
        "app_sys_id":        app_info.get("sys_id"),
        "app_name":          app_info.get("name"),
        "app_scope":         app_info.get("scope"),
        "app_type":          app_info.get("type"),
        "menu_sys_id":       menu_info.get("sys_id"),
        "summary": {
            "total_components":   total,
            "implemented_count":  implemented_count,
            "missing_count":      missing_count,
            "completion_percent": completion_pct,
        }
    }

    print(f"\n📊 DISCOVERY RESULT: Scenario {scenario} — {scenario_label.upper()}")
    print(f"   ✅ Implemented ({implemented_count}): {implemented_keys}")
    print(f"   ❌ Missing     ({missing_count}): {missing_keys}")
    print(f"   📈 Completion  : {completion_pct}%")
    if app_info["found"]:
        print(f"   🏢 App sys_id  : {app_info['sys_id']}")
    if menu_info["found"]:
        print(f"   📂 Menu sys_id : {menu_info['sys_id']}")

    return result



# # discovery.py
# # Read-only scan of ServiceNow to detect existing module/app components.
# # Zero writes — only GET calls.
# # Returns a structured result used by services.py to determine which scenario applies.

# from snow_client import safe_get, SNOW_BASE_URL


# # ─────────────────────────────────────────
# # COMPONENT CHECKERS — each returns list of found items
# # ─────────────────────────────────────────

# def _find_tables(keyword: str) -> list:
#     """Find tables whose name or label contains the keyword."""
#     url = f"{SNOW_BASE_URL}/sys_db_object?sysparm_query=nameLIKE{keyword}^ORlabelLIKE{keyword}&sysparm_fields=name,label,sys_id&sysparm_limit=20"
#     try:
#         res = safe_get(url)
#         results = res.json().get("result", [])
#         return [{"name": r.get("name"), "label": r.get("label"), "sys_id": r.get("sys_id")} for r in results]
#     except Exception:
#         return []


# def _find_fields(table_name: str) -> list:
#     """Find custom fields on a given table."""
#     url = f"{SNOW_BASE_URL}/sys_dictionary?sysparm_query=name={table_name}^elementSTARTSWITHu_&sysparm_fields=element,column_label,internal_type&sysparm_limit=50"
#     try:
#         res = safe_get(url)
#         results = res.json().get("result", [])
#         return [{"field_name": r.get("element"), "field_label": r.get("column_label"), "type": r.get("internal_type")} for r in results]
#     except Exception:
#         return []


# def _find_roles(keyword: str) -> list:
#     """Find roles whose name contains the keyword."""
#     url = f"{SNOW_BASE_URL}/sys_user_role?sysparm_query=nameLIKE{keyword}&sysparm_fields=name,sys_id&sysparm_limit=20"
#     try:
#         res = safe_get(url)
#         results = res.json().get("result", [])
#         return [{"name": r.get("name"), "sys_id": r.get("sys_id")} for r in results]
#     except Exception:
#         return []


# def _find_forms(keyword: str) -> list:
#     """Find form sections whose table name or title contains the keyword."""
#     url = f"{SNOW_BASE_URL}/sys_ui_section?sysparm_query=nameLIKE{keyword}^ORtitleLIKE{keyword}&sysparm_fields=name,title,sys_id&sysparm_limit=20"
#     try:
#         res = safe_get(url)
#         results = res.json().get("result", [])
#         return [{"name": r.get("name"), "title": r.get("title"), "sys_id": r.get("sys_id")} for r in results]
#     except Exception:
#         return []


# def _find_list_layouts(keyword: str) -> list:
#     """Find list layouts (sys_ui_list) for tables matching keyword."""
#     url = f"{SNOW_BASE_URL}/sys_ui_list?sysparm_query=nameLIKE{keyword}&sysparm_fields=name,sys_id&sysparm_limit=20"
#     try:
#         res = safe_get(url)
#         results = res.json().get("result", [])
#         return [{"name": r.get("name"), "sys_id": r.get("sys_id")} for r in results]
#     except Exception:
#         return []


# def _find_client_scripts(keyword: str) -> list:
#     """Find client scripts for tables matching keyword."""
#     url = f"{SNOW_BASE_URL}/sys_script_client?sysparm_query=tableLIKE{keyword}^ORnameLIKE{keyword}&sysparm_fields=name,table,type,sys_id&sysparm_limit=20"
#     try:
#         res = safe_get(url)
#         results = res.json().get("result", [])
#         return [{"name": r.get("name"), "table": r.get("table"), "type": r.get("type")} for r in results]
#     except Exception:
#         return []


# def _find_script_includes(keyword: str) -> list:
#     """Find script includes whose name contains the keyword."""
#     url = f"{SNOW_BASE_URL}/sys_script_include?sysparm_query=nameLIKE{keyword}&sysparm_fields=name,sys_id&sysparm_limit=20"
#     try:
#         res = safe_get(url)
#         results = res.json().get("result", [])
#         return [{"name": r.get("name"), "sys_id": r.get("sys_id")} for r in results]
#     except Exception:
#         return []


# def _find_access_controls(keyword: str) -> list:
#     """Find ACLs for tables matching keyword."""
#     url = f"{SNOW_BASE_URL}/sys_security_acl?sysparm_query=nameLIKE{keyword}&sysparm_fields=name,operation,type,sys_id&sysparm_limit=20"
#     try:
#         res = safe_get(url)
#         results = res.json().get("result", [])
#         return [{"name": r.get("name"), "operation": r.get("operation")} for r in results]
#     except Exception:
#         return []


# def _find_system_properties(keyword: str) -> list:
#     """Find system properties whose name contains the keyword."""
#     url = f"{SNOW_BASE_URL}/sys_properties?sysparm_query=nameLIKE{keyword}&sysparm_fields=name,value,sys_id&sysparm_limit=20"
#     try:
#         res = safe_get(url)
#         results = res.json().get("result", [])
#         return [{"name": r.get("name"), "value": r.get("value")} for r in results]
#     except Exception:
#         return []


# def _find_navigation(keyword: str) -> list:
#     """Find navigation modules whose title or table contains the keyword."""
#     url = f"{SNOW_BASE_URL}/sys_app_module?sysparm_query=titleLIKE{keyword}^ORnameLIKE{keyword}&sysparm_fields=title,name,sys_id&sysparm_limit=20"
#     try:
#         res = safe_get(url)
#         results = res.json().get("result", [])
#         return [{"title": r.get("title"), "table": r.get("name"), "sys_id": r.get("sys_id")} for r in results]
#     except Exception:
#         return []


# def _find_workflows(keyword: str) -> list:
#     """Find workflows whose name contains the keyword."""
#     url = f"{SNOW_BASE_URL}/wf_workflow?sysparm_query=nameLIKE{keyword}&sysparm_fields=name,table,active,sys_id&sysparm_limit=20"
#     try:
#         res = safe_get(url)
#         results = res.json().get("result", [])
#         return [{"name": r.get("name"), "table": r.get("table"), "active": r.get("active")} for r in results]
#     except Exception:
#         return []


# def _find_notifications(keyword: str) -> list:
#     """Find email notifications whose name contains the keyword."""
#     url = f"{SNOW_BASE_URL}/sysevent_email_action?sysparm_query=nameLIKE{keyword}&sysparm_fields=name,collection,active,sys_id&sysparm_limit=20"
#     try:
#         res = safe_get(url)
#         results = res.json().get("result", [])
#         return [{"name": r.get("name"), "table": r.get("collection"), "active": r.get("active")} for r in results]
#     except Exception:
#         return []


# def _find_approvals(keyword: str) -> list:
#     """Find approval business rules whose name contains the keyword."""
#     url = f"{SNOW_BASE_URL}/sys_script?sysparm_query=nameLIKE{keyword}&sysparm_fields=name,collection,active,sys_id&sysparm_limit=20"
#     try:
#         res = safe_get(url)
#         results = res.json().get("result", [])
#         return [{"name": r.get("name"), "table": r.get("collection"), "active": r.get("active")} for r in results]
#     except Exception:
#         return []


# def _find_relationships(keyword: str) -> list:
#     """Find table relationships for tables matching keyword."""
#     url = f"{SNOW_BASE_URL}/sys_relationship?sysparm_query=nameLIKE{keyword}&sysparm_fields=name,parent_table,child_table,sys_id&sysparm_limit=20"
#     try:
#         res = safe_get(url)
#         results = res.json().get("result", [])
#         return [{"name": r.get("name"), "parent": r.get("parent_table"), "child": r.get("child_table")} for r in results]
#     except Exception:
#         return []


# # ─────────────────────────────────────────
# # STANDARD FEATURE CATALOG
# # What a complete module of each type should have.
# # Used to compute what is "missing" in Scenario 3.
# # ─────────────────────────────────────────

# STANDARD_FEATURES = {
#     "default": [
#         "tables",
#         "fields",
#         "roles",
#         "forms",
#         "list_layouts",
#         "access_controls",
#         "navigation",
#         "workflows",
#         "notifications",
#         "approvals",
#         "client_scripts",
#         "script_includes",
#         "system_properties",
#         "relationships",
#     ]
# }


# def get_standard_features(module_name: str) -> list:
#     """Returns the expected feature set for a given module type."""
#     key = module_name.lower().replace(" ", "_")
#     return STANDARD_FEATURES.get(key, STANDARD_FEATURES["default"])


# # ─────────────────────────────────────────
# # MAIN DISCOVERY FUNCTION
# # ─────────────────────────────────────────

# def discover_module(module_name: str) -> dict:
#     """
#     Scans ServiceNow for all components related to a module name.

#     Returns:
#     {
#         "scenario": 1 | 2 | 3,
#         "scenario_label": "not_found" | "fully_implemented" | "partial",
#         "module_name": str,
#         "keyword": str,
#         "implemented": {
#             "tables": [...],
#             "fields": [...],
#             "roles": [...],
#             "forms": [...],
#             "list_layouts": [...],
#             "client_scripts": [...],
#             "script_includes": [...],
#             "access_controls": [...],
#             "system_properties": [...],
#             "navigation": [...],
#             "workflows": [...],
#             "notifications": [...],
#             "approvals": [...],
#             "relationships": [...],
#         },
#         "implemented_keys": [...],   # which component types have at least 1 item
#         "missing_keys": [...],       # which component types have 0 items
#         "summary": {
#             "total_components": int,
#             "implemented_count": int,
#             "missing_count": int,
#             "completion_percent": int
#         }
#     }
#     """
#     keyword = module_name.lower().replace(" ", "_")
#     keyword_search = module_name.lower().replace("_", " ")

#     print(f"\n🔍 DISCOVERING: '{module_name}' (keyword: {keyword})")

#     # Run all discovery checks
#     tables         = _find_tables(keyword_search)
#     roles          = _find_roles(keyword)
#     forms          = _find_forms(keyword_search)
#     list_layouts   = _find_list_layouts(keyword)
#     client_scripts = _find_client_scripts(keyword)
#     script_includes= _find_script_includes(keyword)
#     access_controls= _find_access_controls(keyword)
#     system_props   = _find_system_properties(keyword)
#     navigation     = _find_navigation(keyword_search)
#     workflows      = _find_workflows(keyword_search)
#     notifications  = _find_notifications(keyword_search)
#     approvals      = _find_approvals(keyword_search)
#     relationships  = _find_relationships(keyword_search)

#     # Find fields for each discovered table
#     all_fields = []
#     for table in tables:
#         fields = _find_fields(table["name"])
#         all_fields.extend(fields)

#     implemented = {
#         "tables":          tables,
#         "fields":          all_fields,
#         "roles":           roles,
#         "forms":           forms,
#         "list_layouts":    list_layouts,
#         "client_scripts":  client_scripts,
#         "script_includes": script_includes,
#         "access_controls": access_controls,
#         "system_properties": system_props,
#         "navigation":      navigation,
#         "workflows":       workflows,
#         "notifications":   notifications,
#         "approvals":       approvals,
#         "relationships":   relationships,
#     }

#     # Determine which components exist and which are missing
#     standard_features = get_standard_features(module_name)
#     implemented_keys  = [k for k in standard_features if implemented.get(k)]
#     missing_keys      = [k for k in standard_features if not implemented.get(k)]

#     total             = len(standard_features)
#     implemented_count = len(implemented_keys)
#     missing_count     = len(missing_keys)
#     completion_pct    = int((implemented_count / total) * 100) if total else 0

#     # ── Determine Scenario ──────────────────
#     if implemented_count == 0:
#         scenario       = 1
#         scenario_label = "not_found"
#     elif missing_count == 0:
#         scenario       = 2
#         scenario_label = "fully_implemented"
#     else:
#         scenario       = 3
#         scenario_label = "partial"

#     result = {
#         "scenario":        scenario,
#         "scenario_label":  scenario_label,
#         "module_name":     module_name,
#         "keyword":         keyword,
#         "implemented":     implemented,
#         "implemented_keys":implemented_keys,
#         "missing_keys":    missing_keys,
#         "summary": {
#             "total_components":   total,
#             "implemented_count":  implemented_count,
#             "missing_count":      missing_count,
#             "completion_percent": completion_pct,
#         }
#     }

#     # Print discovery summary
#     print(f"\n📊 DISCOVERY RESULT: Scenario {scenario} — {scenario_label.upper()}")
#     print(f"   ✅ Implemented ({implemented_count}): {implemented_keys}")
#     print(f"   ❌ Missing     ({missing_count}): {missing_keys}")
#     print(f"   📈 Completion  : {completion_pct}%")

#     return result




