import os
import requests
from azure.identity import DefaultAzureCredential

credential = DefaultAzureCredential()
token = credential.get_token("https://ai.azure.com/.default").token

PROJECT_ID = "az-matthewj-3507"
ENDPOINT = "https://dret-ai.services.ai.azure.com"

headers = {
    "Authorization": f"Bearer {token}"
}

url = f"{ENDPOINT}/api/projects/{PROJECT_ID}/agents"

response = requests.options(url, headers=headers)

print("Available API versions (if returned):")
print(response.text)
