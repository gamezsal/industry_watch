"""Model Armor screening tool for ADK agent."""

from typing import Any
from google.adk.tools import FunctionTool
from app.security.model_armor import (
    screen_user_prompt,
    screen_model_response,
    screen_untrusted_tool_output,
)


def screen_with_model_armor(
    text: str,
    target: str = "prompt",
    user_prompt: str = "",
) -> dict[str, Any]:
    """Screen text using Google Cloud Model Armor template for prompt injection, jailbreaks, and safety violations.

    Args:
        text: Text content to screen (user prompt, model output, or untrusted external snippet).
        target: Target type to evaluate ('prompt', 'model_response', or 'untrusted_tool_output').
        user_prompt: Optional context of the original prompt (used when target='model_response').

    Returns:
        Structured evaluation with safety verdict, filter matches, confidence level, and sanitized text.
    """
    clean_target = target.strip().lower()

    if clean_target in ("prompt", "user_prompt", "input"):
        return screen_user_prompt(text)
    elif clean_target in ("response", "model_response", "output"):
        return screen_model_response(text, user_prompt=user_prompt)
    elif clean_target in ("tool_output", "untrusted_tool_output", "claims"):
        # Wrap single text item into claim dictionary
        sample_claims = [{"title": "Tool Output Inspection", "snippet": text}]
        screened, threats = screen_untrusted_tool_output(sample_claims)
        is_safe = len(threats) == 0
        return {
            "is_safe": is_safe,
            "match_found": not is_safe,
            "threat_type": threats[0]["threat_type"] if threats else None,
            "confidence_level": threats[0]["confidence_level"] if threats else None,
            "error_message": threats[0]["error_message"] if threats else None,
            "sanitized_text": screened[0]["snippet"],
            "source": "MODEL_ARMOR_CLOUD_API",
        }
    else:
        # Default to prompt screening
        return screen_user_prompt(text)


screen_with_model_armor_tool = FunctionTool(screen_with_model_armor)
