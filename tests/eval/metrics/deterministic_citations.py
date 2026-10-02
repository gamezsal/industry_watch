"""Deterministic evaluation metric: Verbatim 8-K Accession Number & Item Code Groundedness.

Enforces that every SEC accession number (e.g. 0001045810-26-000073) and Form 8-K
item code (e.g. 2.02, 5.02, 8.01) cited in the agent's response must appear verbatim
in the actual tool output from that turn or conversation session.
"""

import json
import re
from typing import Any
from app.tools.taxonomy import ITEM_TAXONOMY_8K

# Regex for SEC Form 8-K accession numbers: 10 digits - 2 digits - 6 digits
ACCESSION_REGEX = re.compile(r"\b\d{10}-\d{2}-\d{6}\b")

# Regex for Form 8-K item codes: e.g. "Item 2.02", "Items 1.01 and 9.01", or bare item numbers "2.02"
ITEM_CODE_REGEX = re.compile(r"\b(?:Item|Items|item|items)?\s*([1-9]\.[0-9]{2})\b")

VALID_8K_ITEMS = set(ITEM_TAXONOMY_8K.keys())


def extract_accession_numbers(text: str) -> set[str]:
    """Extract all SEC accession numbers from text."""
    if not text:
        return set()
    return set(ACCESSION_REGEX.findall(text))


def extract_8k_item_codes(text: str) -> set[str]:
    """Extract all valid SEC Form 8-K item codes from text."""
    if not text:
        return set()
    raw_matches = ITEM_CODE_REGEX.findall(text)
    # Filter to only valid 8-K taxonomy item codes
    return {code for code in raw_matches if code in VALID_8K_ITEMS}


def _extract_all_tool_outputs_text(obj: Any) -> list[str]:
    """Recursively traverse a dictionary/list/turn structure to collect all tool output text."""
    collected = []
    if isinstance(obj, str):
        collected.append(obj)
    elif isinstance(obj, dict):
        for k, v in obj.items():
            # Check common keys for tool outputs or responses
            collected.extend(_extract_all_tool_outputs_text(v))
    elif isinstance(obj, (list, tuple)):
        for item in obj:
            collected.extend(_extract_all_tool_outputs_text(item))
    return collected


def extract_tool_ground_truth(agent_data: dict[str, Any] | list[Any]) -> tuple[set[str], set[str]]:
    """Extract the complete ground-truth set of accession numbers and 8-K item codes from tool outputs."""
    tool_accessions: set[str] = set()
    tool_items: set[str] = set()

    # If agent_data contains turns
    turns = agent_data.get("turns", []) if isinstance(agent_data, dict) else agent_data

    for turn in turns:
        events = turn.get("events", []) if isinstance(turn, dict) else []
        for event in events:
            author = event.get("author", "")
            # Look for tool outputs / responses
            if author in ("tool", "tool_response", "function_response", "tool_call"):
                content = event.get("content", {})
                all_text = " ".join(_extract_all_tool_outputs_text(content))
                tool_accessions.update(extract_accession_numbers(all_text))
                tool_items.update(extract_8k_item_codes(all_text))

            # Also check if intermediate_data / tool_uses is embedded
            if "tool_uses" in event or "tool_outputs" in event:
                all_text = " ".join(_extract_all_tool_outputs_text(event))
                tool_accessions.update(extract_accession_numbers(all_text))
                tool_items.update(extract_8k_item_codes(all_text))

    return tool_accessions, tool_items


def evaluate_verbatim_citations(
    response_text: str,
    tool_outputs: list[dict[str, Any]] | dict[str, Any] | str,
) -> dict[str, Any]:
    """Grade whether every cited accession number and 8-K item code appears verbatim in tool output.

    Args:
        response_text: The agent's generated response to evaluate.
        tool_outputs: Tool outputs (either structured turn events, list of tool response dicts, or raw string).

    Returns:
        Structured evaluation with binary score (1.0 = pass, 0.0 = fail), cited vs tool sets,
        and ungrounded citations list.
    """
    cited_accessions = extract_accession_numbers(response_text)
    cited_items = extract_8k_item_codes(response_text)

    # Extract tool ground truth
    if isinstance(tool_outputs, str):
        tool_accessions = extract_accession_numbers(tool_outputs)
        tool_items = extract_8k_item_codes(tool_outputs)
    elif isinstance(tool_outputs, dict) and "turns" in tool_outputs:
        tool_accessions, tool_items = extract_tool_ground_truth(tool_outputs)
    else:
        # Generic dict or list of tool responses
        all_text = " ".join(_extract_all_tool_outputs_text(tool_outputs))
        tool_accessions = extract_accession_numbers(all_text)
        tool_items = extract_8k_item_codes(all_text)

    # Deterministic verification
    ungrounded_accessions = cited_accessions - tool_accessions
    ungrounded_items = cited_items - tool_items

    has_ungrounded = bool(ungrounded_accessions or ungrounded_items)
    is_grounded = not has_ungrounded

    score = 1.0 if is_grounded else 0.0

    # Build human-readable explanation
    if not cited_accessions and not cited_items:
        explanation = (
            "No SEC accession numbers or 8-K item codes were cited in the response. "
            "Metric evaluates as grounded (no ungrounded citations fabricated)."
        )
    elif is_grounded:
        explanation = (
            f"PASSED VERBATIM GROUNDEDNESS: All {len(cited_accessions)} cited accession number(s) "
            f"({', '.join(sorted(cited_accessions)) if cited_accessions else 'None'}) and all "
            f"{len(cited_items)} cited Form 8-K item code(s) "
            f"({', '.join(sorted(cited_items)) if cited_items else 'None'}) appeared verbatim in tool outputs."
        )
    else:
        reasons = []
        if ungrounded_accessions:
            reasons.append(
                f"Fabricated/ungrounded accession number(s): {', '.join(sorted(ungrounded_accessions))}"
            )
        if ungrounded_items:
            reasons.append(
                f"Fabricated/ungrounded 8-K item code(s): {', '.join(sorted(ungrounded_items))}"
            )
        explanation = (
            f"FAILED VERBATIM GROUNDEDNESS: Response hallucinated regulatory identifiers not present in tool output! "
            + "; ".join(reasons)
        )

    return {
        "score": score,
        "is_grounded": is_grounded,
        "cited_accessions": sorted(list(cited_accessions)),
        "cited_item_codes": sorted(list(cited_items)),
        "tool_accessions": sorted(list(tool_accessions)),
        "tool_item_codes": sorted(list(tool_items)),
        "ungrounded_accessions": sorted(list(ungrounded_accessions)),
        "ungrounded_item_codes": sorted(list(ungrounded_items)),
        "explanation": explanation,
    }


def evaluate(instance: dict[str, Any]) -> dict[str, Any]:
    """Entry point for agents-cli eval custom metric integration."""
    response = instance.get("response", "")
    agent_data = instance.get("agent_data", {})
    return evaluate_verbatim_citations(response, agent_data)
