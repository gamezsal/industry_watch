import os
import vertexai
import json
from dotenv import load_dotenv

load_dotenv()

PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT", "your-gcp-project-id")
LOCATION = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")
PROJECT_NUMBER = os.environ.get("GOOGLE_CLOUD_PROJECT_NUMBER", "your-project-number")
ENGINE_ID = os.environ.get("GOOGLE_CLOUD_AGENT_ENGINE_ID", "your-agent-engine-id")

client = vertexai.Client(project=PROJECT_ID, location=LOCATION)
engine_name = os.environ.get(
    "GOOGLE_CLOUD_AGENT_ENGINE_RESOURCE_NAME",
    f"projects/{PROJECT_NUMBER}/locations/{LOCATION}/reasoningEngines/{ENGINE_ID}",
)

print("Creating sandbox on Agent Engine...")
op = client.agent_engines.sandboxes.create(
    name=engine_name,
    spec={'code_execution_environment': {}},
)
sandbox_name = op.response.name
print("Sandbox created:", sandbox_name)

code_snippet = """
a = 10
b = 20
print(f"Computed sum in sandbox: {a + b}")
"""

print("Executing test code in sandbox...")
res = client.agent_engines.sandboxes.execute_code(
    name=sandbox_name,
    input_data={'code': code_snippet}
)

for o in res.outputs:
    try:
        parsed = json.loads(o.data.decode('utf-8'))
        print("Sandbox Output:", parsed)
    except Exception:
        print("Raw Output:", o.data.decode('utf-8'))
