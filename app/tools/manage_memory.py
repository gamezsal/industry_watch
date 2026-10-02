# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Tools for interacting with Agent Platform Memory Bank."""

import logging
from typing import Any, Optional

from google.adk.memory.memory_entry import MemoryEntry
from google.adk.tools.function_tool import FunctionTool
from google.adk.tools.tool_context import ToolContext
from google.genai import types

logger = logging.getLogger(__name__)

# Fallback store for offline test execution when no remote Memory Bank service is wired to ToolContext
_LOCAL_PREFERENCE_CACHE: dict[str, str] = {
    "watch_list": "NVDA, AMD, INTC, MU, AVGO",
    "sector": "Semiconductors & AI Accelerator Hardware",
    "briefing_format": "Executive Bullets followed by Form 8-K Materiality Reconciliation (Matched, Filing-Only, Claim-Only)",
}


async def save_user_preferences(
    watch_list: Optional[str] = None,
    sector: Optional[str] = None,
    briefing_format: Optional[str] = None,
    notes: Optional[str] = None,
    tool_context: Optional[ToolContext] = None,
) -> dict[str, Any]:
    """Saves user watch-list, sector, briefing format, and operational preferences to Memory Bank.

    Args:
        watch_list: Comma-separated list of stock tickers to monitor (e.g. 'NVDA, AMD, INTC, MU, AVGO').
        sector: Target industry sector (e.g. 'Semiconductors & AI Hardware').
        briefing_format: Preferred report formatting structure (e.g. 'Bulleted Executive Summary + 8-K Materiality Table').
        notes: Optional user-specific operational preferences or custom directives.

    Returns:
        A dictionary confirming the saved preference profile in Memory Bank.
    """
    updated: dict[str, str] = {}
    if watch_list:
        _LOCAL_PREFERENCE_CACHE["watch_list"] = watch_list.strip()
        updated["watch_list"] = watch_list.strip()
    if sector:
        _LOCAL_PREFERENCE_CACHE["sector"] = sector.strip()
        updated["sector"] = sector.strip()
    if briefing_format:
        _LOCAL_PREFERENCE_CACHE["briefing_format"] = briefing_format.strip()
        updated["briefing_format"] = briefing_format.strip()
    if notes:
        _LOCAL_PREFERENCE_CACHE["notes"] = notes.strip()
        updated["notes"] = notes.strip()

    profile_text = (
        f"[USER SECTOR INTELLIGENCE PROFILE]\n"
        f"Watch-list: {_LOCAL_PREFERENCE_CACHE.get('watch_list', 'NVDA, AMD, INTC, MU, AVGO')}\n"
        f"Sector: {_LOCAL_PREFERENCE_CACHE.get('sector', 'Semiconductors')}\n"
        f"Briefing Format: {_LOCAL_PREFERENCE_CACHE.get('briefing_format', 'Executive bullets + 8-K reconciliation')}\n"
        f"Notes: {_LOCAL_PREFERENCE_CACHE.get('notes', 'None')}"
    )

    persisted_to_memory_bank = False
    if tool_context and hasattr(tool_context, "add_memory"):
        try:
            entry = MemoryEntry(
                content=types.Content(
                    role="user",
                    parts=[types.Part.from_text(text=profile_text)],
                ),
                author="user",
            )
            await tool_context.add_memory(memories=[entry])
            persisted_to_memory_bank = True
        except Exception as exc:
            logger.warning("Could not persist to Memory Bank directly: %s", exc)

    return {
        "status": "success",
        "persisted_to_memory_bank": persisted_to_memory_bank,
        "current_preferences": dict(_LOCAL_PREFERENCE_CACHE),
        "updated_fields": updated,
        "message": "User preferences updated and stored in Memory Bank.",
    }


async def recall_user_preferences(
    query: str = "watch_list sector briefing format",
    tool_context: Optional[ToolContext] = None,
) -> dict[str, Any]:
    """Recalls saved watch-list, sector, and briefing format from Memory Bank across sessions.

    Args:
        query: Specific search terms for memory retrieval (defaults to 'watch_list sector briefing format').

    Returns:
        The remembered preferences and relevant memories retrieved from Memory Bank.
    """
    retrieved_memories: list[str] = []

    if tool_context and hasattr(tool_context, "search_memory"):
        try:
            res = await tool_context.search_memory(query)
            if hasattr(res, "memories") and res.memories:
                for m in res.memories:
                    if hasattr(m, "content") and m.content and m.content.parts:
                        for p in m.content.parts:
                            if p.text:
                                retrieved_memories.append(p.text)
        except Exception as exc:
            logger.warning("Could not search Memory Bank: %s", exc)

    return {
        "status": "success",
        "watch_list": _LOCAL_PREFERENCE_CACHE.get("watch_list", "NVDA, AMD, INTC, MU, AVGO"),
        "sector": _LOCAL_PREFERENCE_CACHE.get("sector", "Semiconductors & AI Hardware"),
        "briefing_format": _LOCAL_PREFERENCE_CACHE.get("briefing_format", "Executive Bullets + 8-K Materiality Reconciliation"),
        "notes": _LOCAL_PREFERENCE_CACHE.get("notes", "None"),
        "retrieved_memory_bank_records": retrieved_memories,
        "source": "Memory Bank (Agent Platform) with local session cache fallback",
    }


save_user_preferences_tool = FunctionTool(save_user_preferences)
recall_user_preferences_tool = FunctionTool(recall_user_preferences)
