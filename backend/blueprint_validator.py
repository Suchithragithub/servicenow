# import json
# import re
# from snow_client import safe_get, SNOW_BASE_URL

# # ── ServiceNow reserved table names (partial list) ───────────────────────────
# RESERVED_TABLE_NAMES = {
#     "sys_user", "sys_script", "incident", "problem", "change_request",
#     "cmdb_ci", "task", "sys_db_object", "sys_dictionary", "sys_properties",
#     "sc_cat_item", "wf_workflow", "sys_hub_flow", "sys_user_role",
# }

# SUPPORTED_FIELD_TYPES = {"string", "integer", "boolean", "glide_date"}
# VALID_ACL_OPERATIONS  = {"read", "write", "create", "delete"}
# MAX_TABLE_NAME_LEN    = 40
# MAX_SCOPE_LEN         = 18
# MAX_ROLE_NAME_LEN     = 40


# # ─────────────────────────────────────────
# # RESULT BUILDER
# # ─────────────────────────────────────────

# def _pass(check, message, detail=None):
#     return {"check": check, "status": "pass", "message": message, "detail": detail}

# def _warn(check, message, detail=None):
#     return {"check": check, "status": "warn", "message": message, "detail": detail}

# def _fail(check, message, detail=None):
#     return {"check": check, "status": "fail", "message": message, "detail": detail}


# # ─────────────────────────────────────────
# # SHARED LIVE CHECKS (read-only GET)
# # ─────────────────────────────────────────

# def _check_table_exists_in_snow(table_name: str) -> bool:
#     url = f"{SNOW_BASE_URL}/sys_db_object?sysparm_query=name={table_name}&sysparm_fields=sys_id"
#     try:
#         res = safe_get(url)
#         return len(res.json().get("result", [])) > 0
#     except Exception:
#         return False

# def _check_role_exists_in_snow(role_name: str) -> bool:
#     url = f"{SNOW_BASE_URL}/sys_user_role?sysparm_query=name={role_name}&sysparm_fields=sys_id"
#     try:
#         res = safe_get(url)
#         return len(res.json().get("result", [])) > 0
#     except Exception:
#         return False

# def _check_app_scope_exists(scope: str) -> bool:
#     url = f"{SNOW_BASE_URL}/sys_app?sysparm_query=scope={scope}&sysparm_fields=sys_id"
#     try:
#         res = safe_get(url)
#         return len(res.json().get("result", [])) > 0
#     except Exception:
#         return False

# def _check_app_name_exists(app_name: str) -> bool:
#     url = f"{SNOW_BASE_URL}/sys_app?sysparm_query=name={app_name}&sysparm_fields=sys_id"
#     try:
#         res = safe_get(url)
#         return len(res.json().get("result", [])) > 0
#     except Exception:
#         return False


# # ─────────────────────────────────────────
# # NEW MODULE VALIDATOR
# # ─────────────────────────────────────────

# def validate_module_blueprint(blueprint: dict, selected_features: list = None) -> dict:
#     """
#     Validates a new module blueprint before any ServiceNow writes.
#     Scenario-aware: only validates components that were selected.
#     If tables was not selected (already exists in SN), tables checks are skipped.
#     """
#     checks = []

#     validate_all    = selected_features is None
#     should_validate = lambda key: validate_all or key in (selected_features or [])

#     # Determine if tables was intentionally excluded (Scenario 3 — already exists)
#     tables_was_selected = validate_all or "tables" in (selected_features or [])

#     scenario_note = (
#         f"Validating selected features: {selected_features}"
#         if selected_features
#         else "Validating all blueprint components"
#     )
#     print(f"\n📋 VALIDATOR: {scenario_note}")

#     # ── 1. Blueprint structure ─────────────────────────────────────
#     # FIX: Only require "tables" in blueprint if tables was actually selected.
#     # In Scenario 3, tables already exist so they won't be in the blueprint.
#     required_always = ["module_name"]
#     required_if_selected = {
#         "tables": "tables",
#         "roles":  "roles",
#     }

#     missing = [k for k in required_always if not blueprint.get(k)]

#     # Only check tables/roles as required if they were selected
#     for feature_key, blueprint_key in required_if_selected.items():
#         if should_validate(feature_key) and not blueprint.get(blueprint_key):
#             missing.append(blueprint_key)

#     if missing:
#         checks.append(_fail(
#             "Blueprint Structure",
#             f"Missing required keys: {missing}",
#             "AI did not generate a complete blueprint. Try again."
#         ))
#     else:
#         checks.append(_pass("Blueprint Structure", "All required keys present"))

#     module_name = blueprint.get("module_name", "")

#     # ── 2. Module name ─────────────────────────────────────────────
#     if not module_name:
#         checks.append(_fail("Module Name", "Module name is empty"))
#     elif len(module_name) > 80:
#         checks.append(_warn("Module Name",
#                             f"Module name is long ({len(module_name)} chars) — consider shortening",
#                             module_name))
#     else:
#         checks.append(_pass("Module Name", f"'{module_name}' looks good"))

#     # ── 3. Tables ──────────────────────────────────────────────────
#     if should_validate("tables"):
#         tables = blueprint.get("tables", [])
#         if not tables:
#             # FIX: Only FAIL if tables was selected but missing.
#             # If tables wasn't selected it means they already exist in SN — skip.
#             if tables_was_selected:
#                 checks.append(_fail("Tables", "No tables defined in blueprint",
#                                     "Tables were selected but AI returned none. Try again."))
#             # If tables not selected → silently skip, no fail
#         else:
#             checks.append(_pass("Tables", f"{len(tables)} table(s) defined"))

#             table_names_in_blueprint = set()
#             for table in tables:
#                 t_name  = table.get("table_name", "")
#                 t_label = table.get("table_label", "")

#                 if not t_name.startswith("u_"):
#                     t_name = f"u_{t_name}"

#                 if not re.match(r'^u_[a-z0-9_]+$', t_name):
#                     checks.append(_fail(f"Table Name: {t_name}",
#                                         "Invalid format — must be lowercase letters, numbers, underscores only",
#                                         f"Got: {t_name}"))
#                 elif len(t_name) > MAX_TABLE_NAME_LEN:
#                     checks.append(_fail(f"Table Name: {t_name}",
#                                         f"Name too long ({len(t_name)} chars, max {MAX_TABLE_NAME_LEN})",
#                                         t_name))
#                 elif t_name.replace("u_", "") in RESERVED_TABLE_NAMES:
#                     checks.append(_fail(f"Table Name: {t_name}",
#                                         "Conflicts with a reserved ServiceNow table name",
#                                         t_name))
#                 else:
#                     checks.append(_pass(f"Table Name: {t_name}", "Format valid"))

#                 if t_name in table_names_in_blueprint:
#                     checks.append(_fail(f"Duplicate Table: {t_name}",
#                                         "Same table name appears twice in blueprint"))
#                 table_names_in_blueprint.add(t_name)

#                 if _check_table_exists_in_snow(t_name):
#                     checks.append(_warn(f"Table Exists: {t_name}",
#                                         f"Table '{t_name}' already exists in ServiceNow — will be skipped",
#                                         "Safe — existing table won't be overwritten"))
#                 else:
#                     checks.append(_pass(f"Table Availability: {t_name}",
#                                         f"'{t_name}' does not exist yet — safe to create"))

#                 if should_validate("fields"):
#                     fields = table.get("fields", [])
#                     if not fields:
#                         checks.append(_warn(f"Fields: {t_label}",
#                                             "No fields defined for this table",
#                                             "Table will be created with no custom fields"))
#                     for field in fields:
#                         f_type = field.get("internal_type", "")
#                         f_name = field.get("field_name", "")
#                         if f_type not in SUPPORTED_FIELD_TYPES:
#                             checks.append(_fail(f"Field Type: {f_name}",
#                                                 f"Unsupported type '{f_type}'",
#                                                 f"Supported: {sorted(SUPPORTED_FIELD_TYPES)}"))
#                         else:
#                             checks.append(_pass(f"Field Type: {f_name}",
#                                                 f"Type '{f_type}' is supported"))

#     # ── 4. Roles ───────────────────────────────────────────────────
#     if should_validate("roles"):
#         roles = blueprint.get("roles", [])
#         if not roles:
#             checks.append(_warn("Roles", "No roles defined — module will have no access control"))
#         else:
#             for role in roles:
#                 r_name = role if isinstance(role, str) else role.get("name", "")
#                 if not r_name.startswith("u_"):
#                     r_name = f"u_{r_name}"
#                 if not re.match(r'^u_[a-z0-9_]+$', r_name):
#                     checks.append(_warn(f"Role Name: {r_name}",
#                                         "Role name has unusual characters", r_name))
#                 else:
#                     checks.append(_pass(f"Role Name: {r_name}", "Format valid"))

#                 if _check_role_exists_in_snow(r_name):
#                     checks.append(_warn(f"Role Exists: {r_name}",
#                                         f"Role '{r_name}' already exists — will be skipped",
#                                         "Safe — existing role reused"))

#     # ── 5. Workflows ───────────────────────────────────────────────
#     if should_validate("workflows"):
#         workflows = blueprint.get("workflows", [])
#         for wf in workflows:
#             print(f"\n🔍 WORKFLOW DEBUG: {json.dumps(wf, indent=2)}")
#             step_data  = wf.get("steps") or wf.get("activities") or wf.get("actions") or []
#             wrong_keys = {"template_to_use", "variables_to_map", "trigger_table"}
#             has_wrong_keys = any(k in wf for k in wrong_keys)

#             if has_wrong_keys and not step_data:
#                 checks.append(_fail(
#                     f"Workflow: {wf.get('name')}",
#                     "Workflow uses unsupported format instead of steps array",
#                     "Blueprint must use: {\"steps\": [\"step1\", \"step2\", ...]}"
#                 ))
#             elif not step_data:
#                 checks.append(_warn(f"Workflow: {wf.get('name')}",
#                                     "Workflow has no steps defined",
#                                     "Will create an empty workflow shell"))
#             else:
#                 checks.append(_pass(f"Workflow: {wf.get('name')}",
#                                     f"{len(step_data)} steps defined"))

#     # ── 6. Forms ───────────────────────────────────────────────────
#     if should_validate("forms"):
#         forms = blueprint.get("forms", [])
#         if not forms:
#             checks.append(_warn("Forms", "No forms defined — users will see raw default view"))
#         else:
#             for form in forms:
#                 if not form.get("visible_fields"):
#                     checks.append(_warn(f"Form: {form.get('form_name')}",
#                                         "No visible fields defined for this form"))
#                 else:
#                     checks.append(_pass(f"Form: {form.get('form_name')}",
#                                         f"{len(form.get('visible_fields', []))} fields defined"))

#     # ── 7. Notifications ───────────────────────────────────────────
#     if should_validate("notifications"):
#         for notif in blueprint.get("notifications", []):
#             if not notif.get("recipient") and not notif.get("recipient_role"):
#                 checks.append(_warn(f"Notification: {notif.get('name')}",
#                                     "No recipient defined",
#                                     "Notification will be created but may not fire correctly"))
#             else:
#                 checks.append(_pass(f"Notification: {notif.get('name')}",
#                                     "Recipient defined"))

#     # ── 8. Approvals ───────────────────────────────────────────────
#     if should_validate("approvals"):
#         for approval in blueprint.get("approvals", []):
#             if not approval.get("approver_role"):
#                 checks.append(_warn(f"Approval: {approval.get('name')}",
#                                     "No approver role defined",
#                                     "Approval rule will be created but may not route correctly"))
#             else:
#                 checks.append(_pass(f"Approval: {approval.get('name')}",
#                                     f"Approver role: {approval.get('approver_role')}"))

#     # ── 9. Navigation ──────────────────────────────────────────────
#     if should_validate("navigation"):
#         nav_items = blueprint.get("navigation", [])
#         tables    = blueprint.get("tables", [])
#         if nav_items:
#             # Navigation explicitly defined in blueprint
#             checks.append(_pass("Navigation",
#                                  f"{len(nav_items)} navigation module(s) defined"))
#         elif tables:
#             # Navigation will be auto-created from tables — OK
#             checks.append(_pass("Navigation",
#                                  f"Navigation will be auto-created from {len(tables)} table(s)"))
#         else:
#             # FIX: tables not in blueprint because they already exist in SN
#             # Navigation can still be created using existing tables — warn not fail
#             checks.append(_warn("Navigation",
#                                  "No tables in blueprint — navigation will use existing ServiceNow tables",
#                                  "Safe — existing tables will be used for navigation links"))

#     # ── 10. Access Controls ────────────────────────────────────────
#     if should_validate("access_controls"):
#         acls = blueprint.get("acls") or blueprint.get("access_controls") or []
#         if not acls:
#             checks.append(_warn("Access Controls",
#                                  "No ACLs defined — default ServiceNow access will apply"))
#         else:
#             for acl in acls:
#                 op = acl.get("operation", "").lower()
#                 if op not in VALID_ACL_OPERATIONS:
#                     checks.append(_fail(f"ACL Operation: {acl.get('table')}",
#                                         f"Invalid operation '{op}'",
#                                         f"Valid: {VALID_ACL_OPERATIONS}"))
#                 else:
#                     checks.append(_pass(f"ACL: {op} on {acl.get('table')}",
#                                         f"Operation '{op}' is valid"))

#     # ── 11. List Layouts ───────────────────────────────────────────
#     if should_validate("list_layouts"):
#         layouts = blueprint.get("list_layouts", [])
#         if not layouts:
#             checks.append(_warn("List Layouts", "No list layouts defined"))
#         else:
#             for layout in layouts:
#                 if not layout.get("columns"):
#                     checks.append(_warn(f"List Layout: {layout.get('table_name')}",
#                                         "No columns defined for this layout"))
#                 else:
#                     checks.append(_pass(f"List Layout: {layout.get('table_name')}",
#                                         f"{len(layout.get('columns', []))} columns defined"))

#     # ── 12. Client Scripts ─────────────────────────────────────────
#     if should_validate("client_scripts"):
#         for cs in blueprint.get("client_scripts", []):
#             valid_types = {"onChange", "onLoad", "onSubmit", "onCellEdit"}
#             if cs.get("type") not in valid_types:
#                 checks.append(_fail(f"Client Script: {cs.get('name')}",
#                                     f"Invalid type '{cs.get('type')}'",
#                                     f"Valid types: {valid_types}"))
#             elif not cs.get("script"):
#                 checks.append(_warn(f"Client Script: {cs.get('name')}",
#                                     "No script body defined"))
#             else:
#                 checks.append(_pass(f"Client Script: {cs.get('name')}",
#                                     f"Type '{cs.get('type')}' is valid"))

#     # ── 13. Script Includes ────────────────────────────────────────
#     if should_validate("script_includes"):
#         for si in blueprint.get("script_includes", []):
#             if not si.get("script"):
#                 checks.append(_warn(f"Script Include: {si.get('name')}",
#                                     "No script body defined — empty include will be created"))
#             else:
#                 checks.append(_pass(f"Script Include: {si.get('name')}",
#                                     "Script body defined"))

#     # ── 14. System Properties ──────────────────────────────────────
#     if should_validate("system_properties"):
#         valid_prop_types = {"string", "integer", "boolean", "choice"}
#         for prop in blueprint.get("system_properties", []):
#             if not prop.get("name"):
#                 checks.append(_fail("System Property", "Property name is empty"))
#             elif prop.get("type") and prop.get("type") not in valid_prop_types:
#                 checks.append(_warn(f"Property: {prop.get('name')}",
#                                     f"Type '{prop.get('type')}' may not be supported",
#                                     f"Recommended: {valid_prop_types}"))
#             else:
#                 checks.append(_pass(f"Property: {prop.get('name')}",
#                                     f"Value: {prop.get('value')}"))

#     # ── 15. Relationships ──────────────────────────────────────────
#     if should_validate("relationships"):
#         for rel in blueprint.get("relationships", []):
#             if not rel.get("parent_table") or not rel.get("child_table"):
#                 checks.append(_fail(f"Relationship: {rel.get('name')}",
#                                     "Missing parent_table or child_table"))
#             else:
#                 checks.append(_pass(f"Relationship: {rel.get('name')}",
#                                     f"{rel.get('parent_table')} → {rel.get('child_table')}"))

#     result = _build_result(checks)
#     result["scenario_note"] = scenario_note
#     return result


# # ─────────────────────────────────────────
# # SCOPED APP VALIDATOR
# # ─────────────────────────────────────────

# def validate_scoped_app_blueprint(blueprint: dict, selected_features: list = None) -> dict:
#     checks = []

#     validate_all    = selected_features is None
#     should_validate = lambda key: validate_all or key in (selected_features or [])

#     scenario_note = (
#         f"Validating selected features: {selected_features}"
#         if selected_features
#         else "Validating all scoped app blueprint components"
#     )

#     # ── 1. Structure ───────────────────────────────────────────────
#     required_keys = ["app_name", "app_scope"]
#     missing = [k for k in required_keys if not blueprint.get(k)]
#     if missing:
#         checks.append(_fail("Blueprint Structure", f"Missing required keys: {missing}"))
#     else:
#         checks.append(_pass("Blueprint Structure", "All required keys present"))

#     app_name  = blueprint.get("app_name", "")
#     app_scope = blueprint.get("app_scope", "")

#     # ── 2. App name ────────────────────────────────────────────────
#     if not app_name:
#         checks.append(_fail("App Name", "App name is empty"))
#     else:
#         checks.append(_pass("App Name", f"'{app_name}' looks good"))
#         if _check_app_name_exists(app_name):
#             checks.append(_warn("App Name Exists",
#                                 f"App '{app_name}' already exists — will be reused",
#                                 "Safe — existing app will not be overwritten"))

#     # ── 3. Scope format ────────────────────────────────────────────
#     if not app_scope:
#         checks.append(_fail("App Scope", "Scope is empty"))
#     elif not app_scope.startswith("x_"):
#         checks.append(_fail("App Scope Format",
#                             f"Scope must start with 'x_' — got '{app_scope}'"))
#     elif len(app_scope) > MAX_SCOPE_LEN:
#         checks.append(_fail("App Scope Length",
#                             f"Scope too long ({len(app_scope)} chars, max {MAX_SCOPE_LEN})",
#                             app_scope))
#     elif not re.match(r'^x_[a-z0-9_]+$', app_scope):
#         checks.append(_fail("App Scope Characters",
#                             "Scope must be lowercase letters, numbers, underscores only",
#                             app_scope))
#     else:
#         checks.append(_pass("App Scope Format", f"'{app_scope}' is valid"))
#         if _check_app_scope_exists(app_scope):
#             checks.append(_warn("App Scope Exists",
#                                 f"Scope '{app_scope}' already exists — will be reused",
#                                 "Safe — existing scoped app will not be overwritten"))
#         else:
#             checks.append(_pass("App Scope Availability", f"'{app_scope}' is available"))

#     # ── 4. Tables ──────────────────────────────────────────────────
#     if should_validate("tables"):
#         tables = blueprint.get("tables", [])
#         if not tables:
#             checks.append(_warn("Tables", "No tables defined"))
#         else:
#             checks.append(_pass("Tables", f"{len(tables)} table(s) defined"))

#         for table in tables:
#             t_name          = table.get("table_name", "")
#             expected_prefix = f"{app_scope}_"

#             if app_scope and not t_name.startswith(expected_prefix) \
#                          and not t_name.startswith(app_scope):
#                 checks.append(_warn(f"Table Prefix: {t_name}",
#                                     f"Table should start with scope prefix '{expected_prefix}'",
#                                     f"Got: {t_name} — services.py will auto-prefix if needed"))
#             else:
#                 checks.append(_pass(f"Table Prefix: {t_name}", "Scope prefix matches"))

#             if len(t_name) > MAX_TABLE_NAME_LEN:
#                 checks.append(_fail(f"Table Name Length: {t_name}",
#                                     f"Too long ({len(t_name)} chars, max {MAX_TABLE_NAME_LEN})"))

#             if should_validate("fields"):
#                 for field in table.get("fields", []):
#                     f_type = field.get("internal_type", "")
#                     f_name = field.get("field_name", "")
#                     if f_type not in SUPPORTED_FIELD_TYPES:
#                         checks.append(_fail(f"Field Type: {f_name}",
#                                             f"Unsupported type '{f_type}'",
#                                             f"Supported: {sorted(SUPPORTED_FIELD_TYPES)}"))

#     # ── 5. Roles ───────────────────────────────────────────────────
#     if should_validate("roles"):
#         for role in blueprint.get("roles", []):
#             r_name = role.get("name", "") if isinstance(role, dict) else role
#             if app_scope and not r_name.startswith(app_scope):
#                 checks.append(_warn(f"Role Prefix: {r_name}",
#                                     f"Role should start with scope '{app_scope}'",
#                                     "create_scoped_role() will auto-prefix"))
#             else:
#                 checks.append(_pass(f"Role Prefix: {r_name}", "Scope prefix matches"))

#     # ── 6. ACLs ────────────────────────────────────────────────────
#     if should_validate("access_controls"):
#         for acl in blueprint.get("acls", []):
#             op = acl.get("operation", "").lower()
#             if op not in VALID_ACL_OPERATIONS:
#                 checks.append(_fail(f"ACL Operation: {acl.get('table')}",
#                                     f"Invalid operation '{op}'",
#                                     f"Valid: {VALID_ACL_OPERATIONS}"))
#             else:
#                 checks.append(_pass(f"ACL: {op} on {acl.get('table')}",
#                                     f"'{op}' is valid"))

#     # ── 7. Navigation ──────────────────────────────────────────────
#     if should_validate("navigation"):
#         app_structure = blueprint.get("app_structure", {})
#         menus         = app_structure.get("menus",   [])
#         modules       = app_structure.get("modules", [])

#         if not menus:
#             checks.append(_warn("App Menu",
#                                 "No menu defined — fallback menu will be created"))
#         else:
#             checks.append(_pass("App Menu", f"{len(menus)} menu(s) defined"))

#         if not modules:
#             checks.append(_warn("Navigation",
#                                 "No navigation modules — will fall back to table list"))
#         else:
#             checks.append(_pass("Navigation",
#                                 f"{len(modules)} navigation module(s) defined"))

#     # ── 8. Workflows ───────────────────────────────────────────────
#     if should_validate("workflows"):
#         for wf in blueprint.get("workflows", []):
#             step_data  = wf.get("steps") or wf.get("activities") or wf.get("actions") or []
#             wrong_keys = {"template_to_use", "variables_to_map", "trigger_table"}
#             has_wrong_keys = any(k in wf for k in wrong_keys)

#             if has_wrong_keys and not step_data:
#                 checks.append(_fail(f"Workflow: {wf.get('name')}",
#                                     "Workflow uses unsupported format instead of steps array",
#                                     "Blueprint must use: {\"steps\": [...]}"))
#             elif not step_data:
#                 checks.append(_warn(f"Workflow: {wf.get('name')}",
#                                     "Workflow has no steps defined"))
#             else:
#                 checks.append(_pass(f"Workflow: {wf.get('name')}",
#                                     f"{len(step_data)} steps defined"))

#     # ── 9. Notifications ───────────────────────────────────────────
#     if should_validate("notifications"):
#         for notif in blueprint.get("notifications", []):
#             if not notif.get("recipient") and not notif.get("recipient_role"):
#                 checks.append(_warn(f"Notification: {notif.get('name')}",
#                                     "No recipient defined"))
#             else:
#                 checks.append(_pass(f"Notification: {notif.get('name')}",
#                                     "Recipient defined"))

#     result = _build_result(checks)
#     result["scenario_note"] = scenario_note
#     return result


# # ─────────────────────────────────────────
# # RESULT AGGREGATOR
# # ─────────────────────────────────────────

# def _build_result(checks: list) -> dict:
#     passes = sum(1 for c in checks if c["status"] == "pass")
#     warns  = sum(1 for c in checks if c["status"] == "warn")
#     fails  = sum(1 for c in checks if c["status"] == "fail")

#     return {
#         "passed":      fails == 0,
#         "can_proceed": fails == 0,
#         "summary":     {"pass": passes, "warn": warns, "fail": fails},
#         "checks":      checks,
#     }


# # # blueprint_validator.py
# # # Pure validation — zero writes to ServiceNow.
# # # All checks are either local (rule-based) or read-only GET calls.
# # # Scenario-aware: validates only the components that were selected by the user.

# # import json
# # import re
# # from snow_client import safe_get, SNOW_BASE_URL

# # # ── ServiceNow reserved table names (partial list) ───────────────────────────
# # RESERVED_TABLE_NAMES = {
# #     "sys_user", "sys_script", "incident", "problem", "change_request",
# #     "cmdb_ci", "task", "sys_db_object", "sys_dictionary", "sys_properties",
# #     "sc_cat_item", "wf_workflow", "sys_hub_flow", "sys_user_role",
# # }

# # SUPPORTED_FIELD_TYPES = {"string", "integer", "boolean", "glide_date"}
# # VALID_ACL_OPERATIONS  = {"read", "write", "create", "delete"}
# # MAX_TABLE_NAME_LEN    = 40
# # MAX_SCOPE_LEN         = 18
# # MAX_ROLE_NAME_LEN     = 40


# # # ─────────────────────────────────────────
# # # RESULT BUILDER
# # # ─────────────────────────────────────────

# # def _pass(check, message, detail=None):
# #     return {"check": check, "status": "pass", "message": message, "detail": detail}

# # def _warn(check, message, detail=None):
# #     return {"check": check, "status": "warn", "message": message, "detail": detail}

# # def _fail(check, message, detail=None):
# #     return {"check": check, "status": "fail", "message": message, "detail": detail}


# # # ─────────────────────────────────────────
# # # SHARED LIVE CHECKS (read-only GET)
# # # ─────────────────────────────────────────

# # def _check_table_exists_in_snow(table_name: str) -> bool:
# #     url = f"{SNOW_BASE_URL}/sys_db_object?sysparm_query=name={table_name}&sysparm_fields=sys_id"
# #     try:
# #         res = safe_get(url)
# #         return len(res.json().get("result", [])) > 0
# #     except Exception:
# #         return False

# # def _check_role_exists_in_snow(role_name: str) -> bool:
# #     url = f"{SNOW_BASE_URL}/sys_user_role?sysparm_query=name={role_name}&sysparm_fields=sys_id"
# #     try:
# #         res = safe_get(url)
# #         return len(res.json().get("result", [])) > 0
# #     except Exception:
# #         return False

# # def _check_app_scope_exists(scope: str) -> bool:
# #     url = f"{SNOW_BASE_URL}/sys_app?sysparm_query=scope={scope}&sysparm_fields=sys_id"
# #     try:
# #         res = safe_get(url)
# #         return len(res.json().get("result", [])) > 0
# #     except Exception:
# #         return False

# # def _check_app_name_exists(app_name: str) -> bool:
# #     url = f"{SNOW_BASE_URL}/sys_app?sysparm_query=name={app_name}&sysparm_fields=sys_id"
# #     try:
# #         res = safe_get(url)
# #         return len(res.json().get("result", [])) > 0
# #     except Exception:
# #         return False


# # # ─────────────────────────────────────────
# # # NEW MODULE VALIDATOR
# # # Scenario-aware: only validates what was selected
# # # ─────────────────────────────────────────

# # def validate_module_blueprint(blueprint: dict, selected_features: list = None) -> dict:
# #     """
# #     Validates a new module blueprint before any ServiceNow writes.

# #     Args:
# #         blueprint:         The raw_blueprint dict from smart_build_module
# #         selected_features: List of features user selected e.g. ["tables", "roles", "workflows"]
# #                            If None, validates everything in the blueprint.

# #     Returns:
# #         {
# #           "passed":      bool,   # True only if zero fails
# #           "can_proceed": bool,   # True if zero fails (warns are OK)
# #           "summary":     { pass: N, warn: N, fail: N },
# #           "checks":      [ { check, status, message, detail } ],
# #           "scenario_note": str   # explains which scenario this validation is for
# #         }
# #     """
# #     checks = []

# #     # ── Determine what to validate ────────────────────────────────
# #     # If selected_features passed, only validate those components.
# #     # Otherwise validate everything present in the blueprint.
# #     validate_all = selected_features is None
# #     should_validate = lambda key: validate_all or key in (selected_features or [])

# #     scenario_note = (
# #         f"Validating selected features: {selected_features}"
# #         if selected_features
# #         else "Validating all blueprint components"
# #     )
# #     print(f"\n📋 VALIDATOR: {scenario_note}")

# #     # ── 1. Blueprint structure ─────────────────────────────────────
# #     required_keys = ["module_name", "tables", "roles"]
# #     missing = [k for k in required_keys if not blueprint.get(k)]
# #     if missing:
# #         checks.append(_fail("Blueprint Structure",
# #                             f"Missing required keys: {missing}",
# #                             "AI did not generate a complete blueprint. Try again."))
# #     else:
# #         checks.append(_pass("Blueprint Structure", "All required keys present"))

# #     module_name = blueprint.get("module_name", "")

# #     # ── 2. Module name ─────────────────────────────────────────────
# #     if not module_name:
# #         checks.append(_fail("Module Name", "Module name is empty"))
# #     elif len(module_name) > 80:
# #         checks.append(_warn("Module Name",
# #                             f"Module name is long ({len(module_name)} chars) — consider shortening",
# #                             module_name))
# #     else:
# #         checks.append(_pass("Module Name", f"'{module_name}' looks good"))

# #     # ── 3. Tables ──────────────────────────────────────────────────
# #     if should_validate("tables"):
# #         tables = blueprint.get("tables", [])
# #         if not tables:
# #             checks.append(_fail("Tables", "No tables defined in blueprint"))
# #         else:
# #             checks.append(_pass("Tables", f"{len(tables)} table(s) defined"))

# #         table_names_in_blueprint = set()
# #         for table in tables:
# #             t_name  = table.get("table_name", "")
# #             t_label = table.get("table_label", "")

# #             if not t_name.startswith("u_"):
# #                 t_name = f"u_{t_name}"

# #             if not re.match(r'^u_[a-z0-9_]+$', t_name):
# #                 checks.append(_fail(f"Table Name: {t_name}",
# #                                     "Invalid format — must be lowercase letters, numbers, underscores only",
# #                                     f"Got: {t_name}"))
# #             elif len(t_name) > MAX_TABLE_NAME_LEN:
# #                 checks.append(_fail(f"Table Name: {t_name}",
# #                                     f"Name too long ({len(t_name)} chars, max {MAX_TABLE_NAME_LEN})",
# #                                     t_name))
# #             elif t_name.replace("u_", "") in RESERVED_TABLE_NAMES:
# #                 checks.append(_fail(f"Table Name: {t_name}",
# #                                     "Conflicts with a reserved ServiceNow table name",
# #                                     t_name))
# #             else:
# #                 checks.append(_pass(f"Table Name: {t_name}", "Format valid"))

# #             if t_name in table_names_in_blueprint:
# #                 checks.append(_fail(f"Duplicate Table: {t_name}",
# #                                     "Same table name appears twice in blueprint"))
# #             table_names_in_blueprint.add(t_name)

# #             # Scenario 1/3: table should NOT exist yet (we are creating it)
# #             if _check_table_exists_in_snow(t_name):
# #                 checks.append(_warn(f"Table Exists: {t_name}",
# #                                     f"Table '{t_name}' already exists in ServiceNow — will be skipped",
# #                                     "Safe — existing table won't be overwritten"))
# #             else:
# #                 checks.append(_pass(f"Table Availability: {t_name}",
# #                                     f"'{t_name}' does not exist yet — safe to create"))

# #             # ── Fields ──────────────────────────────────────────────
# #             if should_validate("fields"):
# #                 fields = table.get("fields", [])
# #                 if not fields:
# #                     checks.append(_warn(f"Fields: {t_label}",
# #                                         "No fields defined for this table",
# #                                         "Table will be created with no custom fields"))
# #                 for field in fields:
# #                     f_type = field.get("internal_type", "")
# #                     f_name = field.get("field_name", "")
# #                     if f_type not in SUPPORTED_FIELD_TYPES:
# #                         checks.append(_fail(f"Field Type: {f_name}",
# #                                             f"Unsupported type '{f_type}'",
# #                                             f"Supported: {sorted(SUPPORTED_FIELD_TYPES)}"))
# #                     else:
# #                         checks.append(_pass(f"Field Type: {f_name}",
# #                                             f"Type '{f_type}' is supported"))

# #     # ── 4. Roles ───────────────────────────────────────────────────
# #     if should_validate("roles"):
# #         roles = blueprint.get("roles", [])
# #         if not roles:
# #             checks.append(_warn("Roles", "No roles defined — module will have no access control"))
# #         else:
# #             for role in roles:
# #                 r_name = role if isinstance(role, str) else role.get("name", "")
# #                 if not r_name.startswith("u_"):
# #                     r_name = f"u_{r_name}"
# #                 if not re.match(r'^u_[a-z0-9_]+$', r_name):
# #                     checks.append(_warn(f"Role Name: {r_name}",
# #                                         "Role name has unusual characters", r_name))
# #                 else:
# #                     checks.append(_pass(f"Role Name: {r_name}", "Format valid"))

# #                 if _check_role_exists_in_snow(r_name):
# #                     checks.append(_warn(f"Role Exists: {r_name}",
# #                                         f"Role '{r_name}' already exists — will be skipped",
# #                                         "Safe — existing role reused"))

# #     # ── 5. Workflows ───────────────────────────────────────────────
# #     if should_validate("workflows"):
# #         workflows = blueprint.get("workflows", [])
# #         for wf in workflows:
# #             print(f"\n🔍 WORKFLOW DEBUG: {json.dumps(wf, indent=2)}")

# #             step_data = (
# #                 wf.get("steps") or
# #                 wf.get("activities") or
# #                 wf.get("actions") or
# #                 []
# #             )

# #             wrong_keys = {"template_to_use", "variables_to_map", "trigger_table"}
# #             has_wrong_keys = any(k in wf for k in wrong_keys)

# #             if has_wrong_keys and not step_data:
# #                 checks.append(_fail(
# #                     f"Workflow: {wf.get('name')}",
# #                     "Workflow uses unsupported format (template/variables) instead of steps array",
# #                     "Blueprint must use: {\"steps\": [\"step1\", \"step2\", ...]}"
# #                 ))
# #             elif not step_data:
# #                 checks.append(_warn(f"Workflow: {wf.get('name')}",
# #                                     "Workflow has no steps defined",
# #                                     "Will create an empty workflow shell"))
# #             else:
# #                 checks.append(_pass(f"Workflow: {wf.get('name')}",
# #                                     f"{len(step_data)} steps defined"))

# #     # ── 6. Forms ───────────────────────────────────────────────────
# #     if should_validate("forms"):
# #         forms = blueprint.get("forms", [])
# #         if not forms:
# #             checks.append(_warn("Forms", "No forms defined — users will see raw default view"))
# #         else:
# #             for form in forms:
# #                 if not form.get("visible_fields"):
# #                     checks.append(_warn(f"Form: {form.get('form_name')}",
# #                                         "No visible fields defined for this form"))
# #                 else:
# #                     checks.append(_pass(f"Form: {form.get('form_name')}",
# #                                         f"{len(form.get('visible_fields', []))} fields defined"))

# #     # ── 7. Notifications ───────────────────────────────────────────
# #     if should_validate("notifications"):
# #         for notif in blueprint.get("notifications", []):
# #             if not notif.get("recipient") and not notif.get("recipient_role"):
# #                 checks.append(_warn(f"Notification: {notif.get('name')}",
# #                                     "No recipient defined",
# #                                     "Notification will be created but may not fire correctly"))
# #             else:
# #                 checks.append(_pass(f"Notification: {notif.get('name')}",
# #                                     "Recipient defined"))

# #     # ── 8. Approvals ───────────────────────────────────────────────
# #     if should_validate("approvals"):
# #         for approval in blueprint.get("approvals", []):
# #             if not approval.get("approver_role"):
# #                 checks.append(_warn(f"Approval: {approval.get('name')}",
# #                                     "No approver role defined",
# #                                     "Approval rule will be created but may not route correctly"))
# #             else:
# #                 checks.append(_pass(f"Approval: {approval.get('name')}",
# #                                     f"Approver role: {approval.get('approver_role')}"))

# #     # ── 9. Navigation ──────────────────────────────────────────────
# #     if should_validate("navigation"):
# #         tables = blueprint.get("tables", [])
# #         if not tables:
# #             checks.append(_warn("Navigation",
# #                                 "No tables defined — navigation modules cannot be created"))
# #         else:
# #             checks.append(_pass("Navigation",
# #                                 f"Navigation will be created for {len(tables)} table(s)"))

# #     result = _build_result(checks)
# #     result["scenario_note"] = scenario_note
# #     return result


# # # ─────────────────────────────────────────
# # # SCOPED APP VALIDATOR
# # # ─────────────────────────────────────────

# # def validate_scoped_app_blueprint(blueprint: dict, selected_features: list = None) -> dict:
# #     """
# #     Validates a scoped app blueprint before any ServiceNow writes.

# #     Args:
# #         blueprint:         The raw scoped app blueprint dict
# #         selected_features: Optional list of features to validate.
# #                            If None, validates everything.
# #     """
# #     checks = []

# #     validate_all = selected_features is None
# #     should_validate = lambda key: validate_all or key in (selected_features or [])

# #     scenario_note = (
# #         f"Validating selected features: {selected_features}"
# #         if selected_features
# #         else "Validating all scoped app blueprint components"
# #     )

# #     # ── 1. Structure ───────────────────────────────────────────────
# #     required_keys = ["app_name", "app_scope", "tables", "roles"]
# #     missing = [k for k in required_keys if not blueprint.get(k)]
# #     if missing:
# #         checks.append(_fail("Blueprint Structure", f"Missing required keys: {missing}"))
# #     else:
# #         checks.append(_pass("Blueprint Structure", "All required keys present"))

# #     app_name  = blueprint.get("app_name", "")
# #     app_scope = blueprint.get("app_scope", "")

# #     # ── 2. App name ────────────────────────────────────────────────
# #     if not app_name:
# #         checks.append(_fail("App Name", "App name is empty"))
# #     else:
# #         checks.append(_pass("App Name", f"'{app_name}' looks good"))
# #         if _check_app_name_exists(app_name):
# #             checks.append(_fail("App Name Conflict",
# #                                 f"An app named '{app_name}' already exists in ServiceNow",
# #                                 "Choose a different name or the creation will fail"))

# #     # ── 3. Scope format ────────────────────────────────────────────
# #     if not app_scope:
# #         checks.append(_fail("App Scope", "Scope is empty"))
# #     elif not app_scope.startswith("x_"):
# #         checks.append(_fail("App Scope Format",
# #                             f"Scope must start with 'x_' — got '{app_scope}'"))
# #     elif len(app_scope) > MAX_SCOPE_LEN:
# #         checks.append(_fail("App Scope Length",
# #                             f"Scope too long ({len(app_scope)} chars, max {MAX_SCOPE_LEN})",
# #                             app_scope))
# #     elif not re.match(r'^x_[a-z0-9_]+$', app_scope):
# #         checks.append(_fail("App Scope Characters",
# #                             "Scope must be lowercase letters, numbers, underscores only",
# #                             app_scope))
# #     else:
# #         checks.append(_pass("App Scope Format", f"'{app_scope}' is valid"))
# #         if _check_app_scope_exists(app_scope):
# #             checks.append(_fail("App Scope Conflict",
# #                                 f"Scope '{app_scope}' already exists in ServiceNow",
# #                                 "Each scope must be globally unique"))
# #         else:
# #             checks.append(_pass("App Scope Availability", f"'{app_scope}' is available"))

# #     # ── 4. Tables ──────────────────────────────────────────────────
# #     if should_validate("tables"):
# #         tables = blueprint.get("tables", [])
# #         if not tables:
# #             checks.append(_warn("Tables", "No tables defined"))
# #         else:
# #             checks.append(_pass("Tables", f"{len(tables)} table(s) defined"))

# #         for table in tables:
# #             t_name = table.get("table_name", "")
# #             expected_prefix = f"{app_scope}_"

# #             if app_scope and not t_name.startswith(expected_prefix) \
# #                          and not t_name.startswith(app_scope):
# #                 checks.append(_warn(f"Table Prefix: {t_name}",
# #                                     f"Table should start with scope prefix '{expected_prefix}'",
# #                                     f"Got: {t_name} — services.py will auto-prefix if needed"))
# #             else:
# #                 checks.append(_pass(f"Table Prefix: {t_name}", "Scope prefix matches"))

# #             if len(t_name) > MAX_TABLE_NAME_LEN:
# #                 checks.append(_fail(f"Table Name Length: {t_name}",
# #                                     f"Too long ({len(t_name)} chars, max {MAX_TABLE_NAME_LEN})"))

# #             if should_validate("fields"):
# #                 for field in table.get("fields", []):
# #                     f_type = field.get("internal_type", "")
# #                     f_name = field.get("field_name", "")
# #                     if f_type not in SUPPORTED_FIELD_TYPES:
# #                         checks.append(_fail(f"Field Type: {f_name}",
# #                                             f"Unsupported type '{f_type}'",
# #                                             f"Supported: {sorted(SUPPORTED_FIELD_TYPES)}"))

# #     # ── 5. Roles ───────────────────────────────────────────────────
# #     if should_validate("roles"):
# #         for role in blueprint.get("roles", []):
# #             r_name = role.get("name", "") if isinstance(role, dict) else role
# #             if app_scope and not r_name.startswith(app_scope):
# #                 checks.append(_warn(f"Role Prefix: {r_name}",
# #                                     f"Role should start with scope '{app_scope}'",
# #                                     "create_scoped_role() will auto-prefix"))
# #             else:
# #                 checks.append(_pass(f"Role Prefix: {r_name}", "Scope prefix matches"))

# #     # ── 6. ACLs ────────────────────────────────────────────────────
# #     if should_validate("access_controls"):
# #         for acl in blueprint.get("acls", []):
# #             op = acl.get("operation", "").lower()
# #             if op not in VALID_ACL_OPERATIONS:
# #                 checks.append(_fail(f"ACL Operation: {acl.get('table')}",
# #                                     f"Invalid operation '{op}'",
# #                                     f"Valid: {VALID_ACL_OPERATIONS}"))
# #             else:
# #                 checks.append(_pass(f"ACL Operation: {acl.get('table')}",
# #                                     f"'{op}' is valid"))

# #     # ── 7. App structure / navigation ─────────────────────────────
# #     if should_validate("navigation"):
# #         app_structure = blueprint.get("app_structure", {})
# #         menus   = app_structure.get("menus",   [])
# #         modules = app_structure.get("modules", [])

# #         if not menus:
# #             checks.append(_warn("App Menu",
# #                                 "No menu defined — fallback menu will be created"))
# #         else:
# #             checks.append(_pass("App Menu", f"{len(menus)} menu(s) defined"))

# #         if not modules:
# #             checks.append(_warn("Navigation",
# #                                 "No navigation modules — will fall back to table list"))
# #         else:
# #             checks.append(_pass("Navigation",
# #                                 f"{len(modules)} navigation module(s) defined"))

# #     # ── 8. Workflows ───────────────────────────────────────────────
# #     if should_validate("workflows"):
# #         for wf in blueprint.get("workflows", []):
# #             step_data = wf.get("steps") or wf.get("activities") or wf.get("actions") or []
# #             wrong_keys = {"template_to_use", "variables_to_map", "trigger_table"}
# #             has_wrong_keys = any(k in wf for k in wrong_keys)

# #             if has_wrong_keys and not step_data:
# #                 checks.append(_fail(f"Workflow: {wf.get('name')}",
# #                                     "Workflow uses unsupported format instead of steps array",
# #                                     "Blueprint must use: {\"steps\": [...]}"))
# #             elif not step_data:
# #                 checks.append(_warn(f"Workflow: {wf.get('name')}",
# #                                     "Workflow has no steps defined"))
# #             else:
# #                 checks.append(_pass(f"Workflow: {wf.get('name')}",
# #                                     f"{len(step_data)} steps defined"))

# #     # ── 9. Notifications ───────────────────────────────────────────
# #     if should_validate("notifications"):
# #         for notif in blueprint.get("notifications", []):
# #             if not notif.get("recipient") and not notif.get("recipient_role"):
# #                 checks.append(_warn(f"Notification: {notif.get('name')}",
# #                                     "No recipient defined"))
# #             else:
# #                 checks.append(_pass(f"Notification: {notif.get('name')}",
# #                                     "Recipient defined"))

# #     result = _build_result(checks)
# #     result["scenario_note"] = scenario_note
# #     return result


# # # ─────────────────────────────────────────
# # # RESULT AGGREGATOR
# # # ─────────────────────────────────────────

# # def _build_result(checks: list) -> dict:
# #     passes = sum(1 for c in checks if c["status"] == "pass")
# #     warns  = sum(1 for c in checks if c["status"] == "warn")
# #     fails  = sum(1 for c in checks if c["status"] == "fail")

# #     return {
# #         "passed":      fails == 0,
# #         "can_proceed": fails == 0,
# #         "summary":     {"pass": passes, "warn": warns, "fail": fails},
# #         "checks":      checks,
# #     }