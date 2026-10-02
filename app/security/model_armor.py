"""Google Cloud Model Armor service integration.

Screens incoming user prompts, model responses, and untrusted external tool
outputs (e.g. news text and public claims) for prompt injection, jailbreak attempts,
and safety violations using a dedicated Model Armor template.
"""

import json
import logging
import os
import re
import threading
import time
from typing import Any
import urllib.request
import urllib.error

from dotenv import load_dotenv

import google.auth
from google.auth.transport.requests import Request

load_dotenv()

logger = logging.getLogger(__name__)

_PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT", "your-gcp-project-id")
_LOCATION = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")
_TEMPLATE_ID = os.environ.get("MODEL_ARMOR_TEMPLATE_ID", "industry-watch-armor-template")

DEFAULT_MODEL_ARMOR_TEMPLATE = os.environ.get(
    "MODEL_ARMOR_TEMPLATE",
    f"projects/{_PROJECT_ID}/locations/{_LOCATION}/templates/{_TEMPLATE_ID}",
)
DEFAULT_MODEL_ARMOR_ENDPOINT = os.environ.get(
    "MODEL_ARMOR_ENDPOINT",
    f"https://modelarmor.{_LOCATION}.rep.googleapis.com",
)

# Deterministic fallback patterns for defense-in-depth offline screening
_FALLBACK_JAILBREAK_PATTERNS = [
    re.compile(r"ignore\s+(all\s+)?(previous|prior)\s+(instructions|directives|prompts)", re.IGNORECASE),
    re.compile(r"disregard\s+(all\s+)?safety\s+(guidelines|protocols|rules)", re.IGNORECASE),
    re.compile(r"you\s+are\s+now\s+(dan|unrestricted|jailbroken|godmode)", re.IGNORECASE),
    re.compile(r"reveal\s+(your\s+)?(system\s+prompt|developer\s+instructions|api\s+keys?)", re.IGNORECASE),
    re.compile(r"\[system\s+instruction:.*\]", re.IGNORECASE),
    re.compile(r"bypass\s+(all\s+)?content\s+filters", re.IGNORECASE),
]


class ModelArmorService:
    """Client for screening text against Google Cloud Model Armor templates."""

    def __init__(
        self,
        template_name: str | None = None,
        endpoint: str | None = None,
        project_id: str | None = None,
        timeout: float = 6.0,
    ):
        self.template_name = template_name or os.environ.get(
            "MODEL_ARMOR_TEMPLATE", DEFAULT_MODEL_ARMOR_TEMPLATE
        )
        self.endpoint = (endpoint or DEFAULT_MODEL_ARMOR_ENDPOINT).rstrip("/")
        self.project_id = project_id or os.environ.get("GOOGLE_CLOUD_PROJECT", _PROJECT_ID)
        self.timeout = timeout

        self._creds = None
        self._token_lock = threading.Lock()
        self._cached_token: str | None = None
        self._token_expiry: float = 0.0

    def _get_auth_token(self) -> str | None:
        """Fetch or refresh Application Default Credentials OAuth2 access token."""
        with self._token_lock:
            now = time.time()
            if self._cached_token and now < (self._token_expiry - 120):
                return self._cached_token

            try:
                if self._creds is None:
                    creds, _ = google.auth.default(
                        scopes=["https://www.googleapis.com/auth/cloud-platform"]
                    )
                    self._creds = creds

                self._creds.refresh(Request())
                self._cached_token = self._creds.token
                # Google access tokens typically valid for 3600 seconds
                self._token_expiry = now + 3500
                return self._cached_token
            except Exception as exc:
                logger.warning("Failed to refresh ADC token for Model Armor: %s", exc)
                return None

    def _call_api(self, action: str, payload: dict[str, Any]) -> dict[str, Any] | None:
        """Call the regional Model Armor REST API endpoint."""
        token = self._get_auth_token()
        if not token:
            return None

        url = f"{self.endpoint}/v1/{self.template_name}:{action}"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "X-Goog-User-Project": self.project_id,
        }
        body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=body, headers=headers, method="POST")

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as http_err:
            try:
                err_body = http_err.read().decode("utf-8")
                logger.warning("Model Armor HTTP Error %s: %s", http_err.code, err_body)
            except Exception:
                pass
            return None
        except Exception as exc:
            logger.warning("Model Armor API call failed (%s): %s", action, exc)
            return None

    def screen_user_prompt(self, text: str) -> dict[str, Any]:
        """Screen a user prompt for prompt injection and jailbreak attempts."""
        if not text or not text.strip():
            return {
                "is_safe": True,
                "match_found": False,
                "threat_type": None,
                "confidence_level": None,
                "error_message": None,
                "sanitized_text": text,
                "source": "empty_input",
            }

        api_res = self._call_api(
            "sanitizeUserPrompt",
            {"userPromptData": {"text": text}},
        )

        if api_res and "sanitizationResult" in api_res:
            s_res = api_res["sanitizationResult"]
            filter_match = s_res.get("filterMatchState") == "MATCH_FOUND"
            filter_results = s_res.get("filterResults", {})
            pi_result = filter_results.get("pi_and_jailbreak", {}).get("piAndJailbreakFilterResult", {})
            pi_match = pi_result.get("matchState") == "MATCH_FOUND"
            confidence = pi_result.get("confidenceLevel")
            meta = s_res.get("sanitizationMetadata", {})
            err_msg = meta.get(
                "errorMessage",
                "Request blocked by Model Armor: Prompt injection or jailbreak detected."
            )

            is_safe = not (filter_match or pi_match)
            return {
                "is_safe": is_safe,
                "match_found": bool(filter_match or pi_match),
                "threat_type": "pi_and_jailbreak" if (filter_match or pi_match) else None,
                "confidence_level": confidence,
                "error_message": err_msg if not is_safe else None,
                "sanitized_text": "" if not is_safe else text,
                "source": "MODEL_ARMOR_CLOUD_API",
                "template": self.template_name,
            }

        # Deterministic fallback screening
        return self._deterministic_fallback_screen(text, context="user_prompt")

    def screen_model_response(self, text: str, user_prompt: str = "") -> dict[str, Any]:
        """Screen an outgoing model response for safety violations and leakage."""
        if not text or not text.strip():
            return {
                "is_safe": True,
                "match_found": False,
                "error_message": None,
                "sanitized_text": text,
                "source": "empty_input",
            }

        payload: dict[str, Any] = {"modelResponseData": {"text": text}}
        if user_prompt:
            payload["userPrompt"] = user_prompt

        api_res = self._call_api("sanitizeModelResponse", payload)

        if api_res and "sanitizationResult" in api_res:
            s_res = api_res["sanitizationResult"]
            filter_match = s_res.get("filterMatchState") == "MATCH_FOUND"
            meta = s_res.get("sanitizationMetadata", {})
            err_msg = meta.get(
                "errorMessage",
                "Response blocked by Model Armor: Safety violation detected."
            )
            is_safe = not filter_match
            return {
                "is_safe": is_safe,
                "match_found": filter_match,
                "error_message": err_msg if not is_safe else None,
                "sanitized_text": "" if not is_safe else text,
                "source": "MODEL_ARMOR_CLOUD_API",
                "template": self.template_name,
            }

        return self._deterministic_fallback_screen(text, context="model_response")

    def screen_untrusted_tool_output(
        self,
        claims: list[dict[str, Any]],
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """Screens untrusted tool output (e.g. public claims, news snippets) for prompt injection.

        Returns:
            A tuple of (sanitized_claims, detected_threats).
            Claims with detected prompt injection attacks have their snippets neutralized
            and are tagged with SECURITY_ALERT: PROMPT_INJECTION_DETECTED.
        """
        sanitized_claims: list[dict[str, Any]] = []
        detected_threats: list[dict[str, Any]] = []

        for claim in claims:
            c_copy = dict(claim)
            title = c_copy.get("title", "")
            snippet = c_copy.get("snippet", "")
            combined_text = f"{title}. {snippet}".strip()

            eval_res = self.screen_user_prompt(combined_text)

            if not eval_res["is_safe"]:
                # Injection or jailbreak detected in untrusted tool data
                c_copy["model_armor_status"] = "BLOCKED_HOSTILE_INJECTION"
                c_copy["is_hostile_prompt_injection"] = True
                c_copy["security_warning"] = (
                    "CRITICAL SECURITY ALERT: Model Armor detected a prompt injection or "
                    "jailbreak payload inside this untrusted public media claim."
                )
                c_copy["original_snippet"] = snippet
                # Neutralize snippet so it cannot hijack subsequent LLM reasoning turns
                c_copy["snippet"] = (
                    "[NEUTRALIZED BY MODEL ARMOR: Hostile prompt injection payload detected "
                    "in external news feed and masked.]"
                )
                detected_threats.append({
                    "claim_id": c_copy.get("claim_id", "UNKNOWN"),
                    "title": title,
                    "threat_type": eval_res.get("threat_type", "pi_and_jailbreak"),
                    "confidence_level": eval_res.get("confidence_level"),
                    "error_message": eval_res.get("error_message"),
                })
            else:
                c_copy["model_armor_status"] = "SCREENED_SAFE"
                c_copy["is_hostile_prompt_injection"] = False

            sanitized_claims.append(c_copy)

        return sanitized_claims, detected_threats

    def _deterministic_fallback_screen(self, text: str, context: str) -> dict[str, Any]:
        """Deterministic heuristic screening for prompt injection/jailbreak patterns."""
        for pattern in _FALLBACK_JAILBREAK_PATTERNS:
            if pattern.search(text):
                err_msg = (
                    f"Request blocked by Model Armor ({context}): "
                    "Prompt injection or jailbreak attempt detected."
                )
                return {
                    "is_safe": False,
                    "match_found": True,
                    "threat_type": "pi_and_jailbreak",
                    "confidence_level": "HIGH",
                    "error_message": err_msg,
                    "sanitized_text": "",
                    "source": "DETERMINISTIC_HEURISTIC_FALLBACK",
                    "template": self.template_name,
                }

        return {
            "is_safe": True,
            "match_found": False,
            "threat_type": None,
            "confidence_level": None,
            "error_message": None,
            "sanitized_text": text,
            "source": "DETERMINISTIC_HEURISTIC_FALLBACK",
            "template": self.template_name,
        }


# Global singleton instance
model_armor_service = ModelArmorService()


def screen_user_prompt(text: str) -> dict[str, Any]:
    """Convenience helper to screen incoming user prompts."""
    return model_armor_service.screen_user_prompt(text)


def screen_model_response(text: str, user_prompt: str = "") -> dict[str, Any]:
    """Convenience helper to screen model responses."""
    return model_armor_service.screen_model_response(text, user_prompt)


def screen_untrusted_tool_output(
    claims: list[dict[str, Any]]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Convenience helper to screen untrusted claims/tool output."""
    return model_armor_service.screen_untrusted_tool_output(claims)
