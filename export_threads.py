import os
import re
from datetime import datetime, timezone
from dotenv import load_dotenv
from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient
from azure.ai.agents.models import ListSortOrder
import markdown
from xhtml2pdf import pisa

# Load .env values
load_dotenv()

# Set up Azure AI Foundry project
credential = DefaultAzureCredential()
project = AIProjectClient(
    credential=credential,
    endpoint="https://dret-ai.services.ai.azure.com/api/projects/az-matthewj-3507"
)

EXPORT_DIR = "exported_threads"
os.makedirs(EXPORT_DIR, exist_ok=True)

# Filter for 11 July 2025 (UTC)
start_date = datetime(2025, 7, 11, 0, 0, 0, tzinfo=timezone.utc)
end_date = datetime(2025, 7, 12, 0, 0, 0, tzinfo=timezone.utc)

def clean_message_text(text):
    """Clean up unicode issues and remove internal source reference tags."""
    text = (
        text.replace("“", '"')
            .replace("”", '"')
            .replace("’", "'")
            .replace("‘", "'")
            .replace("—", "-")
            .replace("–", "-")
            .replace("…", "...")
            .replace("\u2020", "")  # dagger
            .strip()
    )
    text = strip_citations(text)
    return text

def strip_citations(text):
    """Remove all source reference formats (square, double-width, and unicode blocks)."""
    text = re.sub(r"\[\d+:\d+\u2020[^\]]*]", "", text)
    text = re.sub(r"\u3010\d+:\d+\u2020[^\u3011]*\u3011", "", text)
    text = re.sub(r"■.*?■", "", text)
    return re.sub(r"[ ]{2,}", " ", text).strip()

def format_datetime(dt_string):
    try:
        dt = datetime.fromisoformat(dt_string)
        return dt.strftime("%d %B %Y, %H:%M:%S")
    except Exception:
        return dt_string

def generate_pdf(thread_data, output_path):
    html = f"""
    <html>
    <head>
    <meta charset="UTF-8">
    <style>
        body {{ font-family: Helvetica, sans-serif; font-size: 11pt; }}
        h1 {{ font-size: 16pt; }}
        hr {{ margin: 12px 0; }}
        p {{ margin-bottom: 8px; }}
        code {{ background-color: #eee; padding: 2px 4px; font-family: monospace; }}
    </style>
    </head>
    <body>
    <h1>Thread ID: {thread_data['thread_id']}</h1>
    <p><strong>Created at:</strong> {format_datetime(thread_data['created_at'])}</p>
    <hr>
    """

    for msg in thread_data["messages"]:
        role = msg["role"].capitalize()
        raw_timestamp = msg["timestamp"]
        try:
            timestamp_dt = datetime.fromisoformat(raw_timestamp)
            timestamp = timestamp_dt.strftime("%H:%M:%S")
        except Exception:
            timestamp = raw_timestamp

        raw_content = msg["content"]
        cleaned_content = clean_message_text(raw_content.strip())

        if not cleaned_content:
            continue

        html += f"<p><strong>{role} ({timestamp}):</strong></p>"
        html += markdown.markdown(cleaned_content)
        html += "<hr>"

    html += "</body></html>"

    with open(output_path, "wb") as f:
        pisa_status = pisa.CreatePDF(html, dest=f)

    if pisa_status.err:
        print(f"❌ Failed to write PDF for thread {thread_data['thread_id']}")

def export_all_threads():
    threads = list(project.agents.threads.list())
    print(f"Found {len(threads)} total threads.")

    exported_count = 0
    skipped_empty = 0
    skipped_out_of_range = 0

    for thread in threads:
        if not (start_date <= thread.created_at < end_date):
            skipped_out_of_range += 1
            continue

        messages = list(project.agents.messages.list(
            thread_id=thread.id,
            order=ListSortOrder.ASCENDING
        ))

        if not messages:
            print(f"⏭️ Skipping thread {thread.id} (no messages)")
            skipped_empty += 1
            continue

        thread_data = {
            "thread_id": thread.id,
            "created_at": thread.created_at.isoformat(),
            "messages": []
        }

        for m in messages:
            message_text = m.text_messages[-1].text.value if m.text_messages else ""
            thread_data["messages"].append({
                "role": m.role,
                "timestamp": m.created_at.isoformat(),
                "content": message_text
            })

        # Generate filename: e.g., "09-32-01 (6 messages).pdf"
        start_time = thread.created_at.strftime("%H-%M-%S")
        message_count = len(thread_data["messages"])
        filename = f"{start_time} ({message_count} messages).pdf"
        output_path = os.path.join(EXPORT_DIR, filename)

        generate_pdf(thread_data, output_path)
        print(f"✅ Exported {filename}")
        exported_count += 1

    print(f"\n🎉 Done!")
    print(f"Exported {exported_count} PDFs to `{EXPORT_DIR}`")
    print(f"Skipped empty threads: {skipped_empty}")
    print(f"Skipped (not from 11 July 2025): {skipped_out_of_range}")

if __name__ == "__main__":
    export_all_threads()
