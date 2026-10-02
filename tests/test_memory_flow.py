"""End-to-end verification of Agent Platform AI Sessions and Memory Bank integration."""

import asyncio
import os
from dotenv import load_dotenv

from google.adk.sessions.vertex_ai_session_service import VertexAiSessionService
from google.adk.memory.vertex_ai_memory_bank_service import VertexAiMemoryBankService
from app.tools.manage_memory import save_user_preferences, recall_user_preferences

load_dotenv()

PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT", "your-gcp-project-id")
LOCATION = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")
ENGINE_ID = os.environ.get("GOOGLE_CLOUD_AGENT_ENGINE_ID", "your-agent-engine-id")

async def test_flow():
    print("Connecting to Agent Platform AI Sessions and Memory Bank...")
    session_svc = VertexAiSessionService(project=PROJECT_ID, location=LOCATION, agent_engine_id=ENGINE_ID)
    memory_svc = VertexAiMemoryBankService(project=PROJECT_ID, location=LOCATION, agent_engine_id=ENGINE_ID)

    # 1. Multi-turn session creation
    session = await session_svc.create_session(app_name="industry-watch", user_id="analyst-lead")
    print(f"[OK] Created Agent Platform AI Session: {session.id}")

    # 2. Persist preferences to Memory Bank
    save_result = await save_user_preferences(
        watch_list="NVDA, AMD, INTC, MU, AVGO",
        sector="Semiconductors & AI Hardware Accelerators",
        briefing_format="Executive Highlights + SEC Form 8-K Materiality Score Table (Matched / Filing-Only / Claim-Only)",
        notes="Flag any critical Form 8-K Item 1.05 or Item 2.02 filings immediately",
    )
    print(f"[OK] Saved preferences: {save_result['status']}")

    # 3. Recall preferences across sessions
    recall_result = await recall_user_preferences()
    print("[OK] Recalled preferences across sessions:")
    print(f"   Watch-list:      {recall_result['watch_list']}")
    print(f"   Sector:          {recall_result['sector']}")
    print(f"   Briefing Format: {recall_result['briefing_format']}")
    print(f"   Notes:           {recall_result['notes']}")

    # Clean up test session
    await session_svc.delete_session(app_name="industry-watch", user_id="analyst-lead", session_id=session.id)
    print(f"[OK] Cleaned up session {session.id}")

if __name__ == "__main__":
    asyncio.run(test_flow())
