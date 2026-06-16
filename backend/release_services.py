# release_services.py

import os
import json
import requests
import urllib3

from fastapi import HTTPException
from openai import AzureOpenAI
from requests.exceptions import RequestException

# Disable SSL warnings for local development
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


# ─────────────────────────────────────────────────────────────
# AZURE CLIENT
# ─────────────────────────────────────────────────────────────
def get_azure_client():
    api_key = os.getenv("AZURE_OPENAI_API_KEY")
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")

    if not api_key or not endpoint:
        raise HTTPException(
            status_code=500,
            detail="Missing Azure OpenAI configuration in .env"
        )

    return AzureOpenAI(
        api_key=api_key,
        api_version=os.getenv(
            "AZURE_OPENAI_API_VERSION",
            "2024-02-15-preview"
        ),
        azure_endpoint=endpoint
    )


# ─────────────────────────────────────────────────────────────
# COMMON SERVICENOW GET HELPER
# ─────────────────────────────────────────────────────────────
def snow_get(
    url: str,
    username: str,
    password: str,
    headers: dict,
    params: dict = None
):
    try:
        print(f"\n[SNOW] Calling URL: {url}")
        print(f"[SNOW] Params: {params}")

        response = requests.get(
            url,
            auth=(username, password),
            headers=headers,
            params=params,
            verify=False,
            timeout=30
        )

        print(f"[SNOW] Status Code: {response.status_code}")

        response.raise_for_status()

        return response.json()

    except RequestException as e:
        print(f"[SNOW ERROR] {str(e)}")

        raise HTTPException(
            status_code=502,
            detail=f"ServiceNow API request failed: {str(e)}"
        )


# ─────────────────────────────────────────────────────────────
# FETCH SERVICENOW RECORDS
# ─────────────────────────────────────────────────────────────
def fetch_servicenow_change(
    instance_url: str,
    change_number: str,
    table_name: str
) -> dict:

    username = os.getenv("SERVICENOW_USERNAME")
    password = os.getenv("SERVICENOW_PASSWORD")

    if not username or not password:
        raise HTTPException(
            status_code=500,
            detail="Missing ServiceNow credentials in .env"
        )

    base_url = instance_url.rstrip("/")

    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json"
    }

    print(f"\n[Release] change_number={change_number}")
    print(f"[Release] instance={instance_url}")
    print(f"[Release] table={table_name}")

    # ─────────────────────────────────────────────────────────
    # UPDATE SET HANDLING
    # ─────────────────────────────────────────────────────────
    if table_name == "sys_update_set":

        set_url = f"{base_url}/api/now/table/sys_update_set"

        set_params = {
            "sysparm_query": f"nameLIKE{change_number}^ORsys_id={change_number}",
            "sysparm_limit": 1
        }

        result = snow_get(
            set_url,
            username,
            password,
            headers,
            set_params
        )

        results = result.get("result", [])

        if not results:
            raise HTTPException(
                status_code=404,
                detail=f"Update Set '{change_number}' not found."
            )

        record = results[0]

        return {
            "short_description": f"Update Set: {record.get('name')}",
            "description": record.get("description") or "Custom update set package.",
            "implementation_plan": "Commit update set to target environment.",
            "backout_plan": "Rollback update set changes.",
            "test_plan": "Execute ATF validation suite.",
            "related_approvals": [],
            "related_tasks": [],
            "affected_cis": []
        }

    # ─────────────────────────────────────────────────────────
    # MAIN TABLE LOOKUP
    # ─────────────────────────────────────────────────────────
    search_field = "number"

    if table_name in ["sysapproval_approver", "cmdb_ci"]:
        search_field = "sys_id"

    main_url = f"{base_url}/api/now/table/{table_name}"

    main_params = {
        "sysparm_query": f"{search_field}={change_number}",
        "sysparm_limit": 1
    }

    response_json = snow_get(
        main_url,
        username,
        password,
        headers,
        main_params
    )

    main_results = response_json.get("result", [])

    if not main_results:
        raise HTTPException(
            status_code=404,
            detail=f"Record '{change_number}' not found inside '{table_name}'."
        )

    record = main_results[0]

    sys_id = record.get("sys_id")

    approvals = []
    tasks = []
    cis = []

    # ─────────────────────────────────────────────────────────
    # CHANGE REQUEST DEPENDENCIES
    # ─────────────────────────────────────────────────────────
    if table_name == "change_request":

        approvals_url = f"{base_url}/api/now/table/sysapproval_approver"

        tasks_url = f"{base_url}/api/now/table/change_task"

        ci_url = f"{base_url}/api/now/table/task_ci"

        approvals_json = snow_get(
            approvals_url,
            username,
            password,
            headers,
            {
                "sysparm_query": f"sysapproval={sys_id}"
            }
        )

        tasks_json = snow_get(
            tasks_url,
            username,
            password,
            headers,
            {
                "sysparm_query": f"change_request={sys_id}"
            }
        )

        ci_json = snow_get(
            ci_url,
            username,
            password,
            headers,
            {
                "sysparm_query": f"task={sys_id}",
                "sysparm_fields": "ci_item.name"
            }
        )

        approvals = approvals_json.get("result", [])
        tasks = tasks_json.get("result", [])
        cis = ci_json.get("result", [])

    # ─────────────────────────────────────────────────────────
    # CHANGE TASK
    # ─────────────────────────────────────────────────────────
    elif table_name == "change_task":

        tasks = [record]

        parent_id = (
            record.get("change_request", {})
            .get("value")
        )

        if parent_id:

            approvals_url = f"{base_url}/api/now/table/sysapproval_approver"

            approvals_json = snow_get(
                approvals_url,
                username,
                password,
                headers,
                {
                    "sysparm_query": f"sysapproval={parent_id}"
                }
            )

            approvals = approvals_json.get("result", [])

    # ─────────────────────────────────────────────────────────
    # APPROVAL RECORD
    # ─────────────────────────────────────────────────────────
    elif table_name == "sysapproval_approver":
        approvals = [record]

    standardized_payload = {
        "short_description":
            record.get("short_description")
            or record.get("name")
            or f"Inspection Target: {change_number}",

        "description":
            record.get("description")
            or f"Operational record pulled from table '{table_name}'",

        "implementation_plan":
            record.get("implementation_plan")
            or "No implementation plan supplied.",

        "backout_plan":
            record.get("backout_plan")
            or "No rollback plan supplied.",

        "test_plan":
            record.get("test_plan")
            or "No validation strategy supplied.",

        "related_approvals": approvals,
        "related_tasks": tasks,
        "affected_cis": cis
    }

    print(f"[Release] change_data keys: {list(standardized_payload.keys())}")

    return standardized_payload


# ─────────────────────────────────────────────────────────────
# AI ANALYSIS ENGINE
# ─────────────────────────────────────────────────────────────
def analyze_change_readiness(change_data: dict) -> dict:

    client = get_azure_client()

    deployment_name = (
        os.getenv("AZURE_DEPLOYMENT_NAME")
        or os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT")
    )

    if not deployment_name:
        raise HTTPException(
            status_code=500,
            detail="Missing Azure deployment name in .env"
        )

    try:
        from prompts import RELEASE_CHECKER_PROMPT

    except ImportError:
        raise HTTPException(
            status_code=500,
            detail="Could not import RELEASE_CHECKER_PROMPT"
        )

    formatted_prompt = RELEASE_CHECKER_PROMPT.format(
        short_description=change_data.get("short_description") or "None",
        description=change_data.get("description") or "None",
        implementation_plan=change_data.get("implementation_plan") or "None",
        backout_plan=change_data.get("backout_plan") or "None",
        test_plan=change_data.get("test_plan") or "None",
        approvals=json.dumps(change_data.get("related_approvals"), indent=2),
        tasks=json.dumps(change_data.get("related_tasks"), indent=2),
        affected_cis=json.dumps(change_data.get("affected_cis"), indent=2)
    )

    try:

        response = client.chat.completions.create(
            model=deployment_name,
            messages=[
                {
                    "role": "system",
                    "content":
                        "You are a senior release governance AI assistant. "
                        "Return ONLY valid JSON."
                },
                {
                    "role": "user",
                    "content": formatted_prompt
                }
            ],
            response_format={"type": "json_object"},
            temperature=0.2
        )

        parsed = json.loads(
            response.choices[0].message.content
        )

        print(f"[Release] readiness keys: {list(parsed.keys())}")

        return parsed

    except Exception as e:

        print(f"[AI ERROR] {str(e)}")

        raise HTTPException(
            status_code=500,
            detail=f"Azure OpenAI analysis failed: {str(e)}"
        )


