import os
import requests
from azure.identity import DefaultAzureCredential

# Agent IDs by decade (update these)
AGENT_IDS = {
    "twenties": "asst_p4jmmAr74OMhLbAoisN07nIN"
}

# Your project endpoint (no trailing slash)
PROJECT_ID = "az-matthewj-3507"
ENDPOINT = f"https://dret-ai.services.ai.azure.com"

# Get Azure access token using DefaultAzureCredential
credential = DefaultAzureCredential()
token = credential.get_token("https://ai.azure.com/.default").token

headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json"
}

for label, agent_id in AGENT_IDS.items():
    url = f"{ENDPOINT}/api/projects/{PROJECT_ID}/agents/{agent_id}?api-version=2024-04-01-preview"
    print(f"Updating agent {label} ({agent_id})...")

    patch_body = {
        "knowledge_retrieval_settings": {
            "trigger": "on_first_user_message"
        }
    }

    response = requests.patch(url, headers=headers, json=patch_body)

    if response.ok:
        print(f"✅ Success for {label}")
    else:
        print(f"❌ Failed for {label}: {response.status_code} - {response.text}")
