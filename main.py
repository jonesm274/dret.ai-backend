from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv
from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient
from azure.ai.agents.models import ListSortOrder
import os

load_dotenv()

app = Flask(__name__, static_folder="static", static_url_path="")

# Explicit CORS setup for your Azure Static Web App frontend
CORS(
    app,
    origins=["https://jolly-pebble-092f82b03.2.azurestaticapps.net"],
    supports_credentials=True,
    allow_headers=["Content-Type", "Authorization"]
)

# Azure setup
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

        if not agent_id or not message:
            return jsonify({"error": "Missing agentId or message."}), 400

        thread = project.agents.threads.create()
        thread_id = thread.id

        project.agents.messages.create(
            thread_id=thread_id,
            role="user",
            content=message
        )

        run = project.agents.runs.create_and_process(
            thread_id=thread_id,
            agent_id=agent_id
        )

        if run.status == "failed":
            return jsonify({"error": run.last_error}), 400

        messages = project.agents.messages.list(
            thread_id=thread_id,
            order=ListSortOrder.ASCENDING
        )

        response = ""
        for message in messages:
            if message.role == "assistant" and message.text_messages:
                response = message.text_messages[-1].text.value

        return jsonify({"response": response})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Catch-all route for React app
@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve_react_app(path):
    file_path = os.path.join(app.static_folder, path)
    if path != "" and os.path.exists(file_path):
        return send_from_directory(app.static_folder, path)
    return send_from_directory(app.static_folder, "index.html")

if __name__ == "__main__":
    app.run(debug=True)