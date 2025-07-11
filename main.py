from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv
from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient
from azure.ai.agents.models import ListSortOrder
from config.report_id import POWERBI_REPORTS
from config.access import GROUP_ACCESS
# DISABLED METRICS IMPORT!
# from config.user_metrics import (
#     create_or_update_user,
#     log_interaction,
#     log_score,
#     get_user,
#     get_user_interactions,
#     get_user_scores
# )
import os
import requests
import jwt

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

def get_jwk():
    TENANT_ID = os.getenv("PBI_TENANT_ID")
    OPENID_CONFIG_URL = f"https://login.microsoftonline.com/{TENANT_ID}/v2.0/.well-known/openid-configuration"
    resp = requests.get(OPENID_CONFIG_URL)
    jwks_uri = resp.json()["jwks_uri"]
    keys = requests.get(jwks_uri).json()["keys"]
    return keys

def get_user_groups_from_token(token):
    keys = get_jwk()
    unverified_header = jwt.get_unverified_header(token)
    public_key = jwt.algorithms.RSAAlgorithm.from_jwk(
        next(k for k in keys if k["kid"] == unverified_header["kid"])
    )
    payload = jwt.decode(
        token,
        public_key,
        algorithms=["RS256"],
        audience=os.getenv("PBI_CLIENT_ID"),
        options={"verify_exp": True}
    )
    return payload.get("groups", [])

@app.route("/ask", methods=["POST"])
def ask_one_shot():
    try:
        data = request.json
        agent_id = data.get("agentId")
        message = data.get("message")

        if not agent_id or not message:
            return jsonify({"error": "Missing required fields."}), 400

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

        return jsonify({"response": response})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/tutor-ask", methods=["POST"])
def tutor_ask():
    try:
        data = request.json
        agent_id = data.get("agentId")
        message = data.get("message")
        thread_id = data.get("threadId")
        user_id = data.get("userId")
        user_name = data.get("userName")
        year_group = data.get("yearGroup")

        if not agent_id or not message or not user_id:
            return jsonify({"error": "Missing required fields."}), 400

        # DISABLED METRIC LOGGING
        # create_or_update_user(user_id=user_id, name=user_name, year_group=year_group)
        # log_interaction(user_id=user_id, role="user", message=message)

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

        # DISABLED METRIC LOGGING
        # log_interaction(user_id=user_id, role="assistant", message=response)

        return jsonify({"response": response, "threadId": thread_id})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/create-thread", methods=["POST"])
def create_thread():
    try:
        thread = project.agents.threads.create()
        return jsonify({"thread_id": thread.id})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/powerbi/embed-token", methods=["POST"])
def get_powerbi_embed_token():
    try:
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return jsonify({"error": "Missing auth token"}), 401
        token = auth_header.replace("Bearer ", "")
        try:
            user_groups = get_user_groups_from_token(token)
        except Exception as e:
            return jsonify({"error": f"Invalid token: {e}"}), 401

        report_key = request.json.get("reportKey")

        allowed = any(
            report_key in reports
            for group_id, reports in GROUP_ACCESS.items()
            if group_id in user_groups
        )
        if not allowed:
            return jsonify({"error": "Access denied"}), 403

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

        embed_url = (
            f"https://api.powerbi.com/v1.0/myorg/groups/"
            f"{report_config['group_id']}/reports/"
            f"{report_config['report_id']}/GenerateToken"
        )

        embed_payload = {
            "accessLevel": "View"
        }

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }

        embed_response = requests.post(embed_url, json=embed_payload, headers=headers)
        if not embed_response.ok:
            print("Power BI API error:", embed_response.text)
            embed_response.raise_for_status()

        embed_token = embed_response.json()["token"]

        return jsonify({
            "embedToken": embed_token,
            "embedUrl": (
                f"https://app.powerbi.com/reportEmbed"
                f"?reportId={report_config['report_id']}"
                f"&groupId={report_config['group_id']}"
            ),
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
