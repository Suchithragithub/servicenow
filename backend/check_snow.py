# check_snow.py
import os
import requests
from dotenv import load_dotenv

load_dotenv()

SNOW_INSTANCE = os.getenv("SERVICENOW_INSTANCE", "").strip().strip('"').rstrip('/')
SNOW_USERNAME = os.getenv("SERVICENOW_USERNAME")
SNOW_PASSWORD = os.getenv("SERVICENOW_PASSWORD")
SNOW_BASE_URL = f"{SNOW_INSTANCE}/api/now/table"
SNOW_AUTH = (SNOW_USERNAME, SNOW_PASSWORD)

def search(label, url):
    print(f"\n🔍 {label}")
    response = requests.get(url, auth=SNOW_AUTH, timeout=30)
    data = response.json().get("result", [])
    if data:
        for item in data:
            name = (item.get("name") or item.get("label") or
                    item.get("title") or item.get("element") or str(item))
            print(f"   ✅ {name}")
    else:
        print("   ❌ Nothing found")

search("APPLICATION",
    f"{SNOW_BASE_URL}/sys_scope?sysparm_query=nameLIKEVendor&sysparm_fields=name,scope")

search("APP MENU",
    f"{SNOW_BASE_URL}/sys_app_application?sysparm_query=titleLIKEVendor&sysparm_fields=title")

search("ROLES",
    f"{SNOW_BASE_URL}/sys_user_role?sysparm_query=nameLIKEu_vendor&sysparm_fields=name")

search("TABLES",
    f"{SNOW_BASE_URL}/sys_db_object?sysparm_query=nameLIKEu_vendor&sysparm_fields=name,label")

search("FIELDS on u_vendor",
    f"{SNOW_BASE_URL}/sys_dictionary?sysparm_query=name=u_vendor^elementSTARTSWITHu_&sysparm_fields=element,internal_type,column_label")

search("FIELDS on u_vendor_documents",
    f"{SNOW_BASE_URL}/sys_dictionary?sysparm_query=name=u_vendor_documents^elementSTARTSWITHu_&sysparm_fields=element,internal_type,column_label")

search("FORMS",
    f"{SNOW_BASE_URL}/sys_ui_section?sysparm_query=nameLIKEu_vendor&sysparm_fields=name,title")

search("NOTIFICATIONS",
    f"{SNOW_BASE_URL}/sysevent_email_action?sysparm_query=nameLIKEVendor&sysparm_fields=name,collection")

search("APPROVALS (Business Rules)",
    f"{SNOW_BASE_URL}/sys_script?sysparm_query=nameLIKEVendor Approval&sysparm_fields=name,collection,when")

search("WORKFLOWS (Business Rules)",
    f"{SNOW_BASE_URL}/sys_script?sysparm_query=nameLIKEVendor Onboarding Workflow&sysparm_fields=name,collection,active")

search("NAVIGATION MODULES",
    f"{SNOW_BASE_URL}/sys_app_module?sysparm_query=titleLIKEVendor&sysparm_fields=title,name")