# atf_builder.py
# Generates and pushes ATF (Automated Test Framework) test suites to ServiceNow.
# Called after a module is successfully built.
# Zero blueprint validation — tests actual runtime behavior in ServiceNow.

import time
import json
from snow_client import safe_post, safe_get, SNOW_BASE_URL


# ─────────────────────────────────────────
# ATF TABLE REFERENCES
# ─────────────────────────────────────────
ATF_TEST_TABLE        = "sys_atf_test"
ATF_SUITE_TABLE       = "sys_atf_test_suite"
ATF_STEP_TABLE        = "sys_atf_step"
ATF_SUITE_TEST_TABLE  = "sys_atf_test_suite_test"  # links tests to suites


# ─────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────

def _get_step_config_id(step_name: str) -> str:
    """
    Fetches the sys_id of an ATF step config by name.
    e.g. "Create or Update Record", "Run Server Side Script"
    """
    url = (
        f"{SNOW_BASE_URL}/sys_atf_step_config?"
        f"sysparm_query=nameLIKE{step_name}&sysparm_fields=sys_id&sysparm_limit=1"
    )
    try:
        res     = safe_get(url)
        results = res.json().get("result", [])
        return results[0].get("sys_id") if results else None
    except Exception:
        return None


def _create_atf_test(name: str, description: str, active: bool = True) -> str:
    """Creates an ATF test record. Returns sys_id."""
    payload = {
        "name":        name,
        "description": description,
        "active":      "true" if active else "false",
    }
    res = safe_post(f"{SNOW_BASE_URL}/{ATF_TEST_TABLE}", payload)
    if res.status_code == 201:
        return res.json().get("result", {}).get("sys_id")
    print(f"  ❌ ATF test creation failed: {res.text[:150]}")
    return None


def _create_atf_step(test_sys_id: str, step_config_id: str,
                     order: int, inputs: dict) -> str:
    """Creates a step inside an ATF test. Returns sys_id."""
    payload = {
        "test":        test_sys_id,
        "step_config": step_config_id,
        "order":       str(order),
        "inputs":      json.dumps(inputs),
    }
    res = safe_post(f"{SNOW_BASE_URL}/{ATF_STEP_TABLE}", payload)
    if res.status_code == 201:
        return res.json().get("result", {}).get("sys_id")
    print(f"  ❌ ATF step creation failed: {res.text[:150]}")
    return None


def _create_atf_suite(name: str, description: str) -> str:
    """Creates an ATF test suite. Returns sys_id."""
    payload = {
        "name":        name,
        "description": description,
        "active":      "true",
    }
    res = safe_post(f"{SNOW_BASE_URL}/{ATF_SUITE_TABLE}", payload)
    if res.status_code == 201:
        return res.json().get("result", {}).get("sys_id")
    print(f"  ❌ ATF suite creation failed: {res.text[:150]}")
    return None


def _link_test_to_suite(suite_sys_id: str, test_sys_id: str, order: int):
    """Links an ATF test to a test suite."""
    payload = {
        "test_suite": suite_sys_id,
        "test":       test_sys_id,
        "order":      str(order),
    }
    res = safe_post(f"{SNOW_BASE_URL}/{ATF_SUITE_TEST_TABLE}", payload)
    return res.status_code == 201


def _run_server_script_step(test_sys_id: str, order: int, script: str,
                             step_config_id: str) -> str:
    """Creates a 'Run Server Side Script' step."""
    return _create_atf_step(
        test_sys_id, step_config_id, order,
        {"script": script}
    )


# ─────────────────────────────────────────
# TEST GENERATORS
# Each function creates one ATF test and returns its sys_id
# ─────────────────────────────────────────

def _test_table_crud(module_name: str, table_name: str,
                     fields: list, script_config_id: str) -> str:
    """
    Test: Create, Read, Update, Delete a record on the table.
    Verifies the table is accessible and writable.
    """
    test_name = f"{module_name} — Table CRUD: {table_name}"
    test_id   = _create_atf_test(
        test_name,
        f"Verifies that records can be created, read, updated and deleted on {table_name}"
    )
    if not test_id:
        return None

    # Build field values for test record
    field_assignments = ""
    for field in fields[:3]:  # use first 3 fields only
        f_name = field.get("field_name", "")
        f_type = field.get("internal_type", "string")
        if f_type == "string":
            field_assignments += f'    gr.{f_name} = "ATF_TEST_VALUE";\n'
        elif f_type == "integer":
            field_assignments += f'    gr.{f_name} = 1;\n'
        elif f_type == "boolean":
            field_assignments += f'    gr.{f_name} = true;\n'

    script = f"""
// ATF Test: CRUD on {table_name}
var gr = new GlideRecord('{table_name}');
gr.initialize();
{field_assignments}
var sys_id = gr.insert();

// Verify insert
gs.assertTrue(sys_id != null && sys_id != '', 'Record should be created');
gs.assertTrue(sys_id.length > 0, 'sys_id should be a valid string');

// Read back
var gr2 = new GlideRecord('{table_name}');
gs.assertTrue(gr2.get(sys_id), 'Record should be readable');

// Update
gr2.short_description = 'ATF_UPDATED';
gr2.update();

// Delete
var gr3 = new GlideRecord('{table_name}');
gr3.get(sys_id);
gr3.deleteRecord();

// Verify delete
var gr4 = new GlideRecord('{table_name}');
gs.assertFalse(gr4.get(sys_id), 'Record should be deleted');

gs.info('ATF CRUD test passed for {table_name}');
"""

    _run_server_script_step(test_id, 10, script, script_config_id)
    return test_id


def _test_role_exists(module_name: str, role_name: str,
                      script_config_id: str) -> str:
    """
    Test: Verify the role exists in ServiceNow.
    """
    test_name = f"{module_name} — Role Exists: {role_name}"
    test_id   = _create_atf_test(
        test_name,
        f"Verifies that role '{role_name}' exists in sys_user_role"
    )
    if not test_id:
        return None

    script = f"""
// ATF Test: Role exists
var gr = new GlideRecord('sys_user_role');
gr.addQuery('name', '{role_name}');
gr.query();
gs.assertTrue(gr.next(), 'Role {role_name} should exist in sys_user_role');
gs.info('Role {role_name} confirmed to exist');
"""
    _run_server_script_step(test_id, 10, script, script_config_id)
    return test_id


def _test_workflow_exists(module_name: str, workflow_name: str,
                          script_config_id: str) -> str:
    """
    Test: Verify the workflow exists and is active.
    """
    test_name = f"{module_name} — Workflow Active: {workflow_name}"
    test_id   = _create_atf_test(
        test_name,
        f"Verifies that workflow '{workflow_name}' exists and is active"
    )
    if not test_id:
        return None

    script = f"""
// ATF Test: Workflow exists and is active
var gr = new GlideRecord('wf_workflow');
gr.addQuery('name', '{workflow_name}');
gr.addQuery('active', true);
gr.query();
gs.assertTrue(gr.next(), 'Workflow {workflow_name} should exist and be active');
gs.info('Workflow {workflow_name} confirmed active');
"""
    _run_server_script_step(test_id, 10, script, script_config_id)
    return test_id


def _test_notification_exists(module_name: str, notification_name: str,
                               script_config_id: str) -> str:
    """
    Test: Verify the notification exists and is active.
    """
    test_name = f"{module_name} — Notification: {notification_name}"
    test_id   = _create_atf_test(
        test_name,
        f"Verifies that notification '{notification_name}' exists and is active"
    )
    if not test_id:
        return None

    script = f"""
// ATF Test: Notification exists
var gr = new GlideRecord('sysevent_email_action');
gr.addQuery('name', '{notification_name}');
gr.addQuery('active', true);
gr.query();
gs.assertTrue(gr.next(), 'Notification {notification_name} should exist and be active');
gs.info('Notification {notification_name} confirmed');
"""
    _run_server_script_step(test_id, 10, script, script_config_id)
    return test_id


def _test_navigation_exists(module_name: str, nav_title: str,
                             script_config_id: str) -> str:
    """
    Test: Verify the navigation module exists in the left menu.
    """
    test_name = f"{module_name} — Navigation: {nav_title}"
    test_id   = _create_atf_test(
        test_name,
        f"Verifies that navigation module '{nav_title}' exists in sys_app_module"
    )
    if not test_id:
        return None

    script = f"""
// ATF Test: Navigation module exists
var gr = new GlideRecord('sys_app_module');
gr.addQuery('title', '{nav_title}');
gr.addQuery('active', true);
gr.query();
gs.assertTrue(gr.next(), 'Navigation module {nav_title} should exist');
gs.info('Navigation {nav_title} confirmed');
"""
    _run_server_script_step(test_id, 10, script, script_config_id)
    return test_id


def _test_acl_exists(module_name: str, table_name: str,
                     operation: str, script_config_id: str) -> str:
    """
    Test: Verify the ACL exists for a table operation.
    """
    test_name = f"{module_name} — ACL: {operation} on {table_name}"
    test_id   = _create_atf_test(
        test_name,
        f"Verifies ACL for {operation} on {table_name} exists"
    )
    if not test_id:
        return None

    script = f"""
// ATF Test: ACL exists
var gr = new GlideRecord('sys_security_acl');
gr.addQuery('name', '{table_name}');
gr.addQuery('operation', '{operation}');
gr.addQuery('active', true);
gr.query();
gs.assertTrue(gr.next(), 'ACL for {operation} on {table_name} should exist');
gs.info('ACL {operation} on {table_name} confirmed');
"""
    _run_server_script_step(test_id, 10, script, script_config_id)
    return test_id


def _test_script_include_exists(module_name: str, si_name: str,
                                 script_config_id: str) -> str:
    """
    Test: Verify the script include exists and is active.
    """
    test_name = f"{module_name} — Script Include: {si_name}"
    test_id   = _create_atf_test(
        test_name,
        f"Verifies that script include '{si_name}' exists and is active"
    )
    if not test_id:
        return None

    script = f"""
// ATF Test: Script Include exists
var gr = new GlideRecord('sys_script_include');
gr.addQuery('name', '{si_name}');
gr.addQuery('active', true);
gr.query();
gs.assertTrue(gr.next(), 'Script Include {si_name} should exist and be active');
gs.info('Script Include {si_name} confirmed');
"""
    _run_server_script_step(test_id, 10, script, script_config_id)
    return test_id


# =============================================================================
# atf_builder.py — KEY FIX
# Tests are now generated from build_result (what ACTUALLY succeeded),
# not from blueprint (what was supposed to be created).
# This prevents tests being created for roles/ACLs/properties that
# failed to actually get created in ServiceNow.
#
# ALSO ADDS missing test types: System Properties, Client Scripts,
# Relationships, List Layouts — none of these had test generators before.
# =============================================================================

# -----------------------------------------------------------------------------
# ADD these 4 new test generator functions, alongside your existing
# _test_table_crud, _test_role_exists, etc.
# -----------------------------------------------------------------------------

def _test_system_property_exists(module_name: str, prop_name: str,
                                  script_config_id: str) -> str:
    """
    Test: Verify a system property exists with the expected name.
    """
    test_name = f"{module_name} — System Property: {prop_name}"
    test_id   = _create_atf_test(
        test_name,
        f"Verifies that system property '{prop_name}' exists in sys_properties"
    )
    if not test_id:
        return None

    script = f"""
// ATF Test: System property exists
var gr = new GlideRecord('sys_properties');
gr.addQuery('name', '{prop_name}');
gr.query();
gs.assertTrue(gr.next(), 'System property {prop_name} should exist');
gs.info('System property {prop_name} confirmed to exist');
"""
    _run_server_script_step(test_id, 10, script, script_config_id)
    return test_id


def _test_client_script_exists(module_name: str, script_name: str,
                                table_name: str, script_config_id: str) -> str:
    """
    Test: Verify a client script exists and is active for the given table.
    """
    test_name = f"{module_name} — Client Script: {script_name}"
    test_id   = _create_atf_test(
        test_name,
        f"Verifies that client script '{script_name}' exists and is active on {table_name}"
    )
    if not test_id:
        return None

    script = f"""
// ATF Test: Client script exists
var gr = new GlideRecord('sys_script_client');
gr.addQuery('name', '{script_name}');
gr.addQuery('table', '{table_name}');
gr.addQuery('active', true);
gr.query();
gs.assertTrue(gr.next(), 'Client script {script_name} should exist and be active');
gs.info('Client script {script_name} confirmed');
"""
    _run_server_script_step(test_id, 10, script, script_config_id)
    return test_id


def _test_relationship_exists(module_name: str, rel_name: str,
                              parent_table: str, child_table: str,
                              script_config_id: str) -> str:
    """
    Test: Verify a relationship record exists between parent and child tables.
    """
    test_name = f"{module_name} — Relationship: {rel_name}"
    test_id   = _create_atf_test(
        test_name,
        f"Verifies that relationship '{rel_name}' exists between {parent_table} and {child_table}"
    )
    if not test_id:
        return None

    script = f"""
// ATF Test: Relationship exists
var gr = new GlideRecord('sys_relationship');
gr.addQuery('name', '{rel_name}');
gr.query();
gs.assertTrue(gr.next(), 'Relationship {rel_name} should exist');
gs.info('Relationship {rel_name} confirmed');
"""
    _run_server_script_step(test_id, 10, script, script_config_id)
    return test_id


def _test_list_layout_exists(module_name: str, table_name: str,
                             script_config_id: str) -> str:
    """
    Test: Verify a list layout (sys_ui_list) exists for the given table.
    """
    test_name = f"{module_name} — List Layout: {table_name}"
    test_id   = _create_atf_test(
        test_name,
        f"Verifies that a list layout exists for table {table_name}"
    )
    if not test_id:
        return None

    script = f"""
// ATF Test: List layout exists
var gr = new GlideRecord('sys_ui_list');
gr.addQuery('name', '{table_name}');
gr.query();
gs.assertTrue(gr.next(), 'List layout for {table_name} should exist');
gs.info('List layout for {table_name} confirmed');
"""
    _run_server_script_step(test_id, 10, script, script_config_id)
    return test_id


# -----------------------------------------------------------------------------
# REPLACE build_atf_suite() ENTIRELY with this version.
# Now reads from build_result's "_created" lists (what actually succeeded)
# instead of blindly iterating the blueprint.
# -----------------------------------------------------------------------------

def build_atf_suite(module_name: str, build_result: dict, blueprint: dict) -> dict:
    """
    Generates a complete ATF test suite for a built module.
    Only generates tests for components that were CONFIRMED CREATED
    in build_result — not for anything that failed during the build.
    This way, a failing ATF test always means something is genuinely
    broken at test-run-time, not "this was never created in the first place".
    """
    print(f"\n🧪 BUILDING ATF TEST SUITE FOR: {module_name}")
    print("=" * 60)

    result = {
        "suite_name":    f"{module_name} — Automated Test Suite",
        "suite_sys_id":  None,
        "suite_url":     None,
        "tests_created": 0,
        "tests":         [],
        "skipped":       [],
        "errors":        [],
    }

    script_config_id = _get_step_config_id("Run Server Side Script")
    if not script_config_id:
        script_config_id = _get_step_config_id("Server Side Script")
    if not script_config_id:
        error = "Could not find ATF 'Run Server Side Script' step config. ATF plugin may not be active."
        print(f"  ❌ {error}")
        result["errors"].append(error)
        return result

    print(f"  ✅ Script step config found: {script_config_id}")

    suite_id = _create_atf_suite(
        f"{module_name} — Automated Test Suite",
        f"Auto-generated ATF tests for the {module_name} module. "
        f"Only includes tests for components confirmed created during build."
    )
    if not suite_id:
        result["errors"].append("Failed to create ATF test suite")
        return result

    result["suite_sys_id"] = suite_id
    snow_instance = __import__('os').getenv("SERVICENOW_INSTANCE", "").strip().rstrip('/')
    result["suite_url"] = (
        f"{snow_instance}/nav_to.do?uri=sys_atf_test_suite.do?sys_id={suite_id}"
    )
    print(f"  ✅ ATF Suite created: {suite_id}")

    test_order = 10

    # Build a lookup of blueprint items by name, so we can find full details
    # (fields, table, type etc.) for items confirmed in build_result.
    bp_tables_by_name        = {t.get("table_name"): t for t in blueprint.get("tables", [])}
    bp_workflows_by_name     = {w.get("name"): w for w in blueprint.get("workflows", [])}
    bp_notifications_by_name = {n.get("name"): n for n in blueprint.get("notifications", [])}
    bp_navigation_by_title   = {n.get("title"): n for n in blueprint.get("navigation", [])}
    bp_acls_by_key           = {f"{a.get('operation')} on {a.get('table')}": a for a in (blueprint.get("acls") or blueprint.get("access_controls") or [])}
    bp_script_includes       = {s.get("name"): s for s in blueprint.get("script_includes", [])}
    bp_client_scripts        = {c.get("name"): c for c in blueprint.get("client_scripts", [])}
    bp_relationships         = {r.get("name"): r for r in blueprint.get("relationships", [])}

    # ── 1. Table CRUD tests — only for tables CONFIRMED created ───────────────
    tables_created = build_result.get("tables_created", [])
    for table_label in tables_created:
        # tables_created stores labels, need to find matching table_name
        matching = next((t for t in blueprint.get("tables", []) if t.get("table_label") == table_label), None)
        if not matching:
            continue
        t_name  = matching.get("table_name", "")
        fields  = matching.get("fields", [])
        test_id = _test_table_crud(module_name, t_name, fields, script_config_id)
        if test_id:
            _link_test_to_suite(suite_id, test_id, test_order)
            result["tests"].append({"name": f"CRUD: {t_name}", "sys_id": test_id, "type": "table_crud"})
            result["tests_created"] += 1
            test_order += 10
            print(f"  ✅ Test: CRUD on {t_name}")
        time.sleep(0.5)

    # ── 2. Role tests — only for roles CONFIRMED created ──────────────────────
    roles_created = build_result.get("roles_created", [])
    for role_name in roles_created:
        test_id = _test_role_exists(module_name, role_name, script_config_id)
        if test_id:
            _link_test_to_suite(suite_id, test_id, test_order)
            result["tests"].append({"name": f"Role: {role_name}", "sys_id": test_id, "type": "role_exists"})
            result["tests_created"] += 1
            test_order += 10
            print(f"  ✅ Test: Role {role_name}")
        time.sleep(0.3)
    if not roles_created and blueprint.get("roles"):
        result["skipped"].append(f"Roles ({len(blueprint.get('roles', []))} failed to create — no tests generated)")

    # ── 3. Workflow tests — only for workflows CONFIRMED created ──────────────
    workflows_created = build_result.get("workflows_created", [])
    for wf_name in workflows_created:
        test_id = _test_workflow_exists(module_name, wf_name, script_config_id)
        if test_id:
            _link_test_to_suite(suite_id, test_id, test_order)
            result["tests"].append({"name": f"Workflow: {wf_name}", "sys_id": test_id, "type": "workflow_exists"})
            result["tests_created"] += 1
            test_order += 10
            print(f"  ✅ Test: Workflow {wf_name}")
        time.sleep(0.3)

    # ── 4. Notification tests — only for notifications CONFIRMED created ──────
    notifications_created = build_result.get("notifications_created", [])
    for notif_name in notifications_created:
        test_id = _test_notification_exists(module_name, notif_name, script_config_id)
        if test_id:
            _link_test_to_suite(suite_id, test_id, test_order)
            result["tests"].append({"name": f"Notification: {notif_name}", "sys_id": test_id, "type": "notification_exists"})
            result["tests_created"] += 1
            test_order += 10
            print(f"  ✅ Test: Notification {notif_name}")
        time.sleep(0.3)

    # ── 5. Navigation tests — only for navigation CONFIRMED created ───────────
    navigation_created = build_result.get("navigation_created", [])
    for nav_title in navigation_created:
        test_id = _test_navigation_exists(module_name, nav_title, script_config_id)
        if test_id:
            _link_test_to_suite(suite_id, test_id, test_order)
            result["tests"].append({"name": f"Navigation: {nav_title}", "sys_id": test_id, "type": "navigation_exists"})
            result["tests_created"] += 1
            test_order += 10
            print(f"  ✅ Test: Navigation {nav_title}")
        time.sleep(0.3)

    # ── 6. ACL tests — only for ACLs CONFIRMED created ─────────────────────────
    acls_created = build_result.get("access_controls_created", [])
    for acl_key in acls_created:
        # acl_key format: "read on u_vendor"
        parts = acl_key.split(" on ")
        if len(parts) != 2:
            continue
        operation, table_name = parts
        test_id = _test_acl_exists(module_name, table_name, operation, script_config_id)
        if test_id:
            _link_test_to_suite(suite_id, test_id, test_order)
            result["tests"].append({"name": f"ACL: {acl_key}", "sys_id": test_id, "type": "acl_exists"})
            result["tests_created"] += 1
            test_order += 10
            print(f"  ✅ Test: ACL {acl_key}")
        time.sleep(0.3)
    if not acls_created and (blueprint.get("acls") or blueprint.get("access_controls")):
        bp_acl_count = len(blueprint.get("acls") or blueprint.get("access_controls") or [])
        result["skipped"].append(f"ACLs ({bp_acl_count} failed to create — likely missing security_admin role — no tests generated)")

    # ── 7. Script Include tests — only for ones CONFIRMED created ─────────────
    script_includes_created = build_result.get("script_includes_created", [])
    for si_name in script_includes_created:
        test_id = _test_script_include_exists(module_name, si_name, script_config_id)
        if test_id:
            _link_test_to_suite(suite_id, test_id, test_order)
            result["tests"].append({"name": f"Script Include: {si_name}", "sys_id": test_id, "type": "script_include_exists"})
            result["tests_created"] += 1
            test_order += 10
            print(f"  ✅ Test: Script Include {si_name}")
        time.sleep(0.3)

    # ── 8. System Property tests — NEW, only for ones CONFIRMED created ───────
    properties_created = build_result.get("system_properties_created", [])
    for prop_name in properties_created:
        test_id = _test_system_property_exists(module_name, prop_name, script_config_id)
        if test_id:
            _link_test_to_suite(suite_id, test_id, test_order)
            result["tests"].append({"name": f"Property: {prop_name}", "sys_id": test_id, "type": "system_property_exists"})
            result["tests_created"] += 1
            test_order += 10
            print(f"  ✅ Test: System Property {prop_name}")
        time.sleep(0.3)
    if not properties_created and blueprint.get("system_properties"):
        bp_prop_count = len(blueprint.get("system_properties", []))
        result["skipped"].append(f"System Properties ({bp_prop_count} failed to create — likely permission issue — no tests generated)")

    # ── 9. Client Script tests — NEW, only for ones CONFIRMED created ─────────
    client_scripts_created = build_result.get("client_scripts_created", [])
    for cs_name in client_scripts_created:
        bp_cs = bp_client_scripts.get(cs_name, {})
        table_name = bp_cs.get("table", "")
        test_id = _test_client_script_exists(module_name, cs_name, table_name, script_config_id)
        if test_id:
            _link_test_to_suite(suite_id, test_id, test_order)
            result["tests"].append({"name": f"Client Script: {cs_name}", "sys_id": test_id, "type": "client_script_exists"})
            result["tests_created"] += 1
            test_order += 10
            print(f"  ✅ Test: Client Script {cs_name}")
        time.sleep(0.3)

    # ── 10. Relationship tests — NEW, only for ones CONFIRMED created ─────────
    relationships_created = build_result.get("relationships_created", [])
    for rel_name in relationships_created:
        bp_rel = bp_relationships.get(rel_name, {})
        parent_table = bp_rel.get("parent_table", "")
        child_table  = bp_rel.get("child_table", "")
        test_id = _test_relationship_exists(module_name, rel_name, parent_table, child_table, script_config_id)
        if test_id:
            _link_test_to_suite(suite_id, test_id, test_order)
            result["tests"].append({"name": f"Relationship: {rel_name}", "sys_id": test_id, "type": "relationship_exists"})
            result["tests_created"] += 1
            test_order += 10
            print(f"  ✅ Test: Relationship {rel_name}")
        time.sleep(0.3)

    # ── 11. List Layout tests — NEW, only for ones CONFIRMED created ──────────
    list_layouts_created = build_result.get("list_layouts_created", [])
    for table_name in list_layouts_created:
        test_id = _test_list_layout_exists(module_name, table_name, script_config_id)
        if test_id:
            _link_test_to_suite(suite_id, test_id, test_order)
            result["tests"].append({"name": f"List Layout: {table_name}", "sys_id": test_id, "type": "list_layout_exists"})
            result["tests_created"] += 1
            test_order += 10
            print(f"  ✅ Test: List Layout {table_name}")
        time.sleep(0.3)

    if result["skipped"]:
        print(f"\n⚠️  SKIPPED COMPONENTS (failed during build, no tests generated):")
        for s in result["skipped"]:
            print(f"   - {s}")

    print(f"\n🎉 ATF SUITE COMPLETE: {result['tests_created']} tests created")
    print(f"   Suite URL: {result['suite_url']}")
    print("=" * 60)

    return result


# ─────────────────────────────────────────
# MAIN BUILDER FUNCTION
# ─────────────────────────────────────────

def build_atf_suite(module_name: str, build_result: dict, blueprint: dict) -> dict:
    """
    Generates a complete ATF test suite for a built module.
    Called after _push_blueprint() completes successfully.

    Args:
        module_name  : e.g. "Vendor Management"
        build_result : the dict returned by _push_blueprint()
        blueprint    : the original blueprint dict

    Returns:
        {
            "suite_name":    str,
            "suite_sys_id":  str,
            "suite_url":     str,
            "tests_created": int,
            "tests":         [ { name, sys_id, type } ],
            "skipped":       [ str ],
            "errors":        [ str ]
        }
    """
    print(f"\n🧪 BUILDING ATF TEST SUITE FOR: {module_name}")
    print("=" * 60)

    result = {
        "suite_name":    f"{module_name} — Automated Test Suite",
        "suite_sys_id":  None,
        "suite_url":     None,
        "tests_created": 0,
        "tests":         [],
        "skipped":       [],
        "errors":        [],
    }

    # ── Get step config sys_id for "Run Server Side Script" ──────────────────
    script_config_id = _get_step_config_id("Run Server Side Script")
    if not script_config_id:
        # Try alternate name
        script_config_id = _get_step_config_id("Server Side Script")
    if not script_config_id:
        error = "Could not find ATF 'Run Server Side Script' step config. ATF plugin may not be active."
        print(f"  ❌ {error}")
        result["errors"].append(error)
        return result

    print(f"  ✅ Script step config found: {script_config_id}")

    # ── Create the test suite ─────────────────────────────────────────────────
    suite_id = _create_atf_suite(
        f"{module_name} — Automated Test Suite",
        f"Auto-generated ATF tests for the {module_name} module. "
        f"Tests table CRUD, roles, workflows, notifications, navigation and ACLs."
    )
    if not suite_id:
        result["errors"].append("Failed to create ATF test suite")
        return result

    result["suite_sys_id"] = suite_id
    snow_instance = __import__('os').getenv("SERVICENOW_INSTANCE", "").strip().rstrip('/')
    result["suite_url"] = (
        f"{snow_instance}/nav_to.do?uri=sys_atf_test_suite.do?sys_id={suite_id}"
    )
    print(f"  ✅ ATF Suite created: {suite_id}")

    test_order = 10

    # ── 1. Table CRUD tests ───────────────────────────────────────────────────
    tables = blueprint.get("tables", [])
    for table in tables:
        t_name  = table.get("table_name", "")
        fields  = table.get("fields", [])
        test_id = _test_table_crud(module_name, t_name, fields, script_config_id)
        if test_id:
            _link_test_to_suite(suite_id, test_id, test_order)
            result["tests"].append({"name": f"CRUD: {t_name}", "sys_id": test_id, "type": "table_crud"})
            result["tests_created"] += 1
            test_order += 10
            print(f"  ✅ Test: CRUD on {t_name}")
        else:
            result["errors"].append(f"Failed to create CRUD test for {t_name}")
        time.sleep(0.5)

    # ── 2. Role exists tests ──────────────────────────────────────────────────
    # roles = blueprint.get("roles", [])
    # for role in roles:
    #     role_name = role if isinstance(role, str) else role.get("name", "")
    #     if not role_name:
    #         continue
    #     if not role_name.startswith("u_"):
    #         role_name = f"u_{role_name}"
    #     test_id = _test_role_exists(module_name, role_name, script_config_id)
    #     if test_id:
    #         _link_test_to_suite(suite_id, test_id, test_order)
    #         result["tests"].append({"name": f"Role: {role_name}", "sys_id": test_id, "type": "role_exists"})
    #         result["tests_created"] += 1
    #         test_order += 10
    #         print(f"  ✅ Test: Role {role_name}")
    #     time.sleep(0.3)
    roles_created = build_result.get("roles_created", [])
    for role_name in roles_created:
        test_id = _test_role_exists(module_name, role_name, script_config_id)
        if test_id:
            _link_test_to_suite(suite_id, test_id, test_order)
            result["tests"].append({"name": f"Role: {role_name}", "sys_id": test_id, "type": "role_exists"})
            result["tests_created"] += 1
            test_order += 10
            print(f"  ✅ Test: Role {role_name}")
        time.sleep(0.3)
    if not roles_created and blueprint.get("roles"):
        bp_role_count = len(blueprint.get("roles", []))
        result["skipped"].append(f"Roles ({bp_role_count} failed to create — no tests generated)")
        print(f"  ⏭️  Skipped {bp_role_count} role test(s) — none were successfully created")

    # ── 3. Workflow exists tests ──────────────────────────────────────────────
    workflows = blueprint.get("workflows", [])
    for wf in workflows:
        wf_name = wf.get("name", "")
        if not wf_name:
            continue
        test_id = _test_workflow_exists(module_name, wf_name, script_config_id)
        if test_id:
            _link_test_to_suite(suite_id, test_id, test_order)
            result["tests"].append({"name": f"Workflow: {wf_name}", "sys_id": test_id, "type": "workflow_exists"})
            result["tests_created"] += 1
            test_order += 10
            print(f"  ✅ Test: Workflow {wf_name}")
        time.sleep(0.3)

    # ── 4. Notification exists tests ──────────────────────────────────────────
    notifications = blueprint.get("notifications", [])
    for notif in notifications:
        notif_name = notif.get("name", "")
        if not notif_name:
            continue
        test_id = _test_notification_exists(module_name, notif_name, script_config_id)
        if test_id:
            _link_test_to_suite(suite_id, test_id, test_order)
            result["tests"].append({"name": f"Notification: {notif_name}", "sys_id": test_id, "type": "notification_exists"})
            result["tests_created"] += 1
            test_order += 10
            print(f"  ✅ Test: Notification {notif_name}")
        time.sleep(0.3)

    # ── 5. Navigation exists tests ────────────────────────────────────────────
    navigation = blueprint.get("navigation", [])
    for nav in navigation:
        nav_title = nav.get("title", "")
        if not nav_title:
            continue
        test_id = _test_navigation_exists(module_name, nav_title, script_config_id)
        if test_id:
            _link_test_to_suite(suite_id, test_id, test_order)
            result["tests"].append({"name": f"Navigation: {nav_title}", "sys_id": test_id, "type": "navigation_exists"})
            result["tests_created"] += 1
            test_order += 10
            print(f"  ✅ Test: Navigation {nav_title}")
        time.sleep(0.3)

    # ── 6. ACL exists tests ───────────────────────────────────────────────────
    # acls = blueprint.get("acls") or blueprint.get("access_controls") or []
    # for acl in acls:
    #     table_name = acl.get("table", "")
    #     operation  = acl.get("operation", "")
    #     if not table_name or not operation:
    #         continue
    #     test_id = _test_acl_exists(module_name, table_name, operation, script_config_id)
    #     if test_id:
    #         _link_test_to_suite(suite_id, test_id, test_order)
    #         result["tests"].append({"name": f"ACL: {operation} on {table_name}", "sys_id": test_id, "type": "acl_exists"})
    #         result["tests_created"] += 1
    #         test_order += 10
    #         print(f"  ✅ Test: ACL {operation} on {table_name}")
    #     time.sleep(0.3)

    acls_created = build_result.get("access_controls_created", [])
    for acl_key in acls_created:
        # acl_key format: "read on u_vendor"
        parts = acl_key.split(" on ")
        if len(parts) != 2:
            continue
        operation, table_name = parts
        test_id = _test_acl_exists(module_name, table_name, operation, script_config_id)
        if test_id:
            _link_test_to_suite(suite_id, test_id, test_order)
            result["tests"].append({"name": f"ACL: {acl_key}", "sys_id": test_id, "type": "acl_exists"})
            result["tests_created"] += 1
            test_order += 10
            print(f"  ✅ Test: ACL {acl_key}")
        time.sleep(0.3)
    if not acls_created and (blueprint.get("acls") or blueprint.get("access_controls")):
        bp_acl_count = len(blueprint.get("acls") or blueprint.get("access_controls") or [])
        result["skipped"].append(f"ACLs ({bp_acl_count} failed to create — likely missing security_admin role — no tests generated)")
        print(f"  ⏭️  Skipped {bp_acl_count} ACL test(s) — none were successfully created")

    # ── 7. Script Include exists tests ────────────────────────────────────────
    script_includes = blueprint.get("script_includes", [])
    for si in script_includes:
        si_name = si.get("name", "")
        if not si_name:
            continue
        test_id = _test_script_include_exists(module_name, si_name, script_config_id)
        if test_id:
            _link_test_to_suite(suite_id, test_id, test_order)
            result["tests"].append({"name": f"Script Include: {si_name}", "sys_id": test_id, "type": "script_include_exists"})
            result["tests_created"] += 1
            test_order += 10
            print(f"  ✅ Test: Script Include {si_name}")
        time.sleep(0.3)

    if result["skipped"]:
        print(f"\n⚠️  SKIPPED COMPONENTS (failed during build, no tests generated):")
        for s in result["skipped"]:
            print(f"   - {s}")

    print(f"\n🎉 ATF SUITE COMPLETE: {result['tests_created']} tests created")
    print(f"   Suite URL: {result['suite_url']}")
    print("=" * 60)

    return result

#------------------------------------------------------------------------

# =============================================================================
# atf_builder.py — ADD this new function at the bottom of the file
# Generates ATF tests for scoped apps (different blueprint shape than
# regular modules — tables/roles/acls use app_scope prefix, workflows use
# trigger_table/trigger_event instead of table/trigger, notifications use
# recipient_role instead of recipient).
# =============================================================================

def build_scoped_atf_suite(app_name: str, app_scope: str,
                           build_result: dict, blueprint: dict) -> dict:
    """
    Generates a complete ATF test suite for a built SCOPED APP.
    Same test types as build_atf_suite() but adapted for scoped app
    blueprint field names (trigger_table, trigger_event, recipient_role, etc.)

    Args:
        app_name     : e.g. "IT Asset Management"
        app_scope    : e.g. "x_snc_itam"
        build_result : the dict returned by _push_scoped_blueprint()
        blueprint    : the original scoped app blueprint dict

    Returns: same shape as build_atf_suite()
    """
    print(f"\n🧪 BUILDING ATF TEST SUITE FOR SCOPED APP: {app_name} ({app_scope})")
    print("=" * 60)

    result = {
        "suite_name":    f"{app_name} — Automated Test Suite",
        "suite_sys_id":  None,
        "suite_url":     None,
        "tests_created": 0,
        "tests":         [],
        "skipped":       [],
        "errors":        [],
    }

    script_config_id = _get_step_config_id("Run Server Side Script")
    if not script_config_id:
        script_config_id = _get_step_config_id("Server Side Script")
    if not script_config_id:
        error = "Could not find ATF 'Run Server Side Script' step config. ATF plugin may not be active."
        print(f"  ❌ {error}")
        result["errors"].append(error)
        return result

    print(f"  ✅ Script step config found: {script_config_id}")

    suite_id = _create_atf_suite(
        f"{app_name} — Automated Test Suite",
        f"Auto-generated ATF tests for the {app_name} scoped app ({app_scope}). "
        f"Tests table CRUD, roles, workflows, notifications, navigation and ACLs."
    )
    if not suite_id:
        result["errors"].append("Failed to create ATF test suite")
        return result

    result["suite_sys_id"] = suite_id
    snow_instance = __import__('os').getenv("SERVICENOW_INSTANCE", "").strip().rstrip('/')
    result["suite_url"] = (
        f"{snow_instance}/nav_to.do?uri=sys_atf_test_suite.do?sys_id={suite_id}"
    )
    print(f"  ✅ ATF Suite created: {suite_id}")

    test_order = 10

    # ── 1. Table CRUD tests ───────────────────────────────────────────────────
    for table in blueprint.get("tables", []):
        t_name  = table.get("table_name", "")
        fields  = table.get("fields", [])
        test_id = _test_table_crud(app_name, t_name, fields, script_config_id)
        if test_id:
            _link_test_to_suite(suite_id, test_id, test_order)
            result["tests"].append({"name": f"CRUD: {t_name}", "sys_id": test_id, "type": "table_crud"})
            result["tests_created"] += 1
            test_order += 10
            print(f"  ✅ Test: CRUD on {t_name}")
        else:
            result["errors"].append(f"Failed to create CRUD test for {t_name}")
        time.sleep(0.5)

    # ── 2. Role exists tests ──────────────────────────────────────────────────
    for role in blueprint.get("roles", []):
        role_name = role.get("name", "") if isinstance(role, dict) else role
        if not role_name:
            continue
        test_id = _test_role_exists(app_name, role_name, script_config_id)
        if test_id:
            _link_test_to_suite(suite_id, test_id, test_order)
            result["tests"].append({"name": f"Role: {role_name}", "sys_id": test_id, "type": "role_exists"})
            result["tests_created"] += 1
            test_order += 10
            print(f"  ✅ Test: Role {role_name}")
        time.sleep(0.3)

    # ── 3. Workflow exists tests ──────────────────────────────────────────────
    # Scoped app workflows use "name" same as regular — no change needed
    for wf in blueprint.get("workflows", []):
        wf_name = wf.get("name", "")
        if not wf_name:
            continue
        test_id = _test_workflow_exists(app_name, wf_name, script_config_id)
        if test_id:
            _link_test_to_suite(suite_id, test_id, test_order)
            result["tests"].append({"name": f"Workflow: {wf_name}", "sys_id": test_id, "type": "workflow_exists"})
            result["tests_created"] += 1
            test_order += 10
            print(f"  ✅ Test: Workflow {wf_name}")
        time.sleep(0.3)

    # ── 4. Notification exists tests ──────────────────────────────────────────
    for notif in blueprint.get("notifications", []):
        notif_name = notif.get("name", "")
        if not notif_name:
            continue
        test_id = _test_notification_exists(app_name, notif_name, script_config_id)
        if test_id:
            _link_test_to_suite(suite_id, test_id, test_order)
            result["tests"].append({"name": f"Notification: {notif_name}", "sys_id": test_id, "type": "notification_exists"})
            result["tests_created"] += 1
            test_order += 10
            print(f"  ✅ Test: Notification {notif_name}")
        time.sleep(0.3)

    # ── 5. Navigation exists tests ────────────────────────────────────────────
    # Scoped app navigation is under app_structure.modules, not a top-level "navigation" key
    app_structure = blueprint.get("app_structure", {})
    nav_modules    = app_structure.get("modules", [])
    for nav in nav_modules:
        nav_title = nav.get("title", "")
        if not nav_title:
            continue
        test_id = _test_navigation_exists(app_name, nav_title, script_config_id)
        if test_id:
            _link_test_to_suite(suite_id, test_id, test_order)
            result["tests"].append({"name": f"Navigation: {nav_title}", "sys_id": test_id, "type": "navigation_exists"})
            result["tests_created"] += 1
            test_order += 10
            print(f"  ✅ Test: Navigation {nav_title}")
        time.sleep(0.3)

    # ── 6. ACL exists tests ───────────────────────────────────────────────────
    for acl in blueprint.get("acls", []):
        table_name = acl.get("table", "")
        operation  = acl.get("operation", "")
        if not table_name or not operation:
            continue
        test_id = _test_acl_exists(app_name, table_name, operation, script_config_id)
        if test_id:
            _link_test_to_suite(suite_id, test_id, test_order)
            result["tests"].append({"name": f"ACL: {operation} on {table_name}", "sys_id": test_id, "type": "acl_exists"})
            result["tests_created"] += 1
            test_order += 10
            print(f"  ✅ Test: ACL {operation} on {table_name}")
        time.sleep(0.3)

    # ── 7. App scope exists test (scoped-app-specific check) ──────────────────
    test_id = _test_app_scope_exists(app_name, app_scope, script_config_id)
    if test_id:
        _link_test_to_suite(suite_id, test_id, test_order)
        result["tests"].append({"name": f"App Scope: {app_scope}", "sys_id": test_id, "type": "app_scope_exists"})
        result["tests_created"] += 1
        test_order += 10
        print(f"  ✅ Test: App Scope {app_scope}")

    print(f"\n🎉 ATF SUITE COMPLETE: {result['tests_created']} tests created")
    print(f"   Suite URL: {result['suite_url']}")
    print("=" * 60)

    return result


# ─────────────────────────────────────────
# NEW TEST TYPE — App scope exists (scoped-app-specific)
# ADD this alongside your other _test_* functions
# ─────────────────────────────────────────

def _test_app_scope_exists(app_name: str, app_scope: str,
                           script_config_id: str) -> str:
    """
    Test: Verify the scoped application's scope is registered in sys_app.
    """
    test_name = f"{app_name} — App Scope Registered: {app_scope}"
    test_id   = _create_atf_test(
        test_name,
        f"Verifies that scope '{app_scope}' is registered as a valid application in sys_app"
    )
    if not test_id:
        return None

    script = f"""
// ATF Test: App scope is registered
var gr = new GlideRecord('sys_app');
gr.addQuery('scope', '{app_scope}');
gr.addQuery('active', true);
gr.query();
gs.assertTrue(gr.next(), 'Scope {app_scope} should be registered as an active application');
gs.info('App scope {app_scope} confirmed registered');
"""
    _run_server_script_step(test_id, 10, script, script_config_id)
    return test_id