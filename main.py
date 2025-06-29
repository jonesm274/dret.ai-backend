from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv
from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient
from azure.ai.agents.models import ListSortOrder
from config.report_id import POWERBI_REPORTS
import os
import requests

load_dotenv()

app = Flask(__name__, static_folder="static", static_url_path="")

CORS(
    app,
    origins=[
        "https://jolly-pebble-092f82b03.2.azurestaticapps.net",
        "https://www.teachingtools.co.uk",
        "https://teachingtools.co.uk"
    ],
    supports_credentials=True,
    allow_headers=["Content-Type", "Authorization"]
)

credential = DefaultAzureCredential()
project = AIProjectClient(
    credential=credential,
    endpoint="https://dret-ai.services.ai.azure.com/api/projects/az-matthewj-3507"
)

@app.route("/ask", methods=["POST"])
def ask():
    try:
        data = request.json
        agent_id = data.get("agentId")
        message = data.get("message")
        thread_id = data.get("threadId")

        if not agent_id or not message:
            return jsonify({"error": "Missing agentId or message."}), 400

        if thread_id:
            try:
                thread = project.agents.threads.get(thread_id)
            except Exception:
                thread = project.agents.threads.create()
                thread_id = thread.id
        else:
            thread = project.agents.threads.create()
            thread_id = thread.id

        project.agents.messages.create(thread_id=thread_id, role="user", content=message)

        run = project.agents.runs.create_and_process(thread_id=thread_id, agent_id=agent_id)

        if run.status == "failed":
            return jsonify({"error": run.last_error}), 400

        messages = project.agents.messages.list(thread_id=thread_id, order=ListSortOrder.ASCENDING)

        response = ""
        for m in messages:
            if m.role == "assistant" and m.text_messages:
                response = m.text_messages[-1].text.value

        return jsonify({"response": response, "threadId": thread_id})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/powerbi/embed-token", methods=["POST"])
def get_powerbi_embed_token():
    try:
        report_key = request.json.get("reportKey")
        username = request.json.get("username", "anonymous@teachingtools.co.uk")
        roles = request.json.get("roles", ["AllUsers"])

        report_config = POWERBI_REPORTS.get(report_key)
        if not report_config:
            return jsonify({"error": "Invalid report key"}), 400

        tenant_id = os.getenv("PBI_TENANT_ID")
        client_id = os.getenv("PBI_CLIENT_ID")
        client_secret = os.getenv("PBI_CLIENT_SECRET")

        token_url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
        token_data = {
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret,
            "scope": "https://analysis.windows.net/powerbi/api/.default"
        }

        token_response = requests.post(token_url, data=token_data)
        token_response.raise_for_status()
        access_token = token_response.json()["access_token"]

        embed_url = f"https://api.powerbi.com/v1.0/myorg/groups/{report_config['group_id']}/reports/{report_config['report_id']}/GenerateToken"
        embed_payload = {
            "accessLevel": "View",
            "identities": [
                {
                    "username": username,
                    "roles": roles,
                    "datasets": [report_config["dataset_id"]]
                }
            ]
        }

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }

        embed_response = requests.post(embed_url, json=embed_payload, headers=headers)
        embed_response.raise_for_status()
        embed_token = embed_response.json()["token"]

        return jsonify({
            "embedToken": embed_token,
            "embedUrl": f"https://app.powerbi.com/reportEmbed?reportId={report_config['report_id']}&groupId={report_config['group_id']}",
            "reportId": report_config["report_id"]
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve_react_app(path):
    file_path = os.path.join(app.static_folder, path)
    if path != "" and os.path.exists(file_path):
        return send_from_directory(app.static_folder, path)
    return send_from_directory(app.static_folder, "index.html")

if __name__ == "__main__":
    app.run(debug=True)