import os
import requests
from dotenv import load_dotenv

load_dotenv()

SNOW_INSTANCE = os.getenv("SERVICENOW_INSTANCE", "").strip().strip('"').rstrip('/')
SNOW_USERNAME = os.getenv("SERVICENOW_USERNAME")
SNOW_PASSWORD = os.getenv("SERVICENOW_PASSWORD")
SNOW_BASE_URL = f"{SNOW_INSTANCE}/api/now/table"
SNOW_AUTH = (SNOW_USERNAME, SNOW_PASSWORD)

print(f"🔍 Instance : {SNOW_INSTANCE}")
print(f"🔍 Username : {SNOW_USERNAME}")
print(f"🔍 Password : {'set' if SNOW_PASSWORD else 'NOT SET'}")
print(f"🔍 Base URL : {SNOW_BASE_URL}")

# Test 1 - Basic connection
print("\n--- TEST 1: Basic Connection ---")
response = requests.get(
    f"{SNOW_BASE_URL}/sys_user_role?sysparm_limit=1",
    auth=SNOW_AUTH,
    timeout=30
)
print(f"Status : {response.status_code}")
print(f"Response: {response.text[:300]}")

# Test 2 - Create a role
print("\n--- TEST 2: Create Role ---")
response = requests.post(
    f"{SNOW_BASE_URL}/sys_user_role",
    auth=SNOW_AUTH,
    json={"name": "u_test_role_delete_me", "description": "test"},
    timeout=30
)
print(f"Status : {response.status_code}")
print(f"Response: {response.text[:300]}")

# Test 3 - Create a table
print("\n--- TEST 3: Create Table ---")
response = requests.post(
    f"{SNOW_BASE_URL}/sys_db_object",
    auth=SNOW_AUTH,
    json={"label": "Test Table", "name": "u_test_table_delete_me", "create_access_controls": "true"},
    timeout=30
)
print(f"Status : {response.status_code}")
print(f"Response: {response.text[:300]}")


# Test scoped app creation
print("\n--- TEST: Create Scoped App ---")
response = requests.post(
    f"{SNOW_BASE_URL}/sys_scope",
    auth=SNOW_AUTH,
    json={
        "name": "Test Vendor App",
        "scope": "x_snc_test_vendor",
        "short_description": "Test scoped app",
        "version": "1.0.0",
        "active": "true",
        "private": "false",
        "licensable": "false",
        "enforce_license": "false",
        "vendor": "Custom",
        "vendor_prefix": "x_snc_test_vendor"
    },
    timeout=30
)
print(f"Status : {response.status_code}")
print(f"Response: {response.text[:500]}")

# add to test_connection.py
print("\n--- TEST: Create sys_app ---")
response = requests.post(
    f"{SNOW_BASE_URL}/sys_app",
    auth=SNOW_AUTH,
    json={
        "name": "Test Vendor App2",
        "scope": "x_snc_test_vend2",
        "short_description": "Test",
        "version": "1.0.0",
        "active": "true"
    },
    timeout=30
)
print(f"Status : {response.status_code}")
print(f"Response: {response.text[:300]}")