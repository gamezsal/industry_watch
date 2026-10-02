"""Deterministic industry-watch tools for disclosures, claims, and reconciliation."""

from google.adk.tools import FunctionTool

from app.tools.manage_memory import (
    recall_user_preferences,
    recall_user_preferences_tool,
    save_user_preferences,
    save_user_preferences_tool,
)
from app.tools.public_claims import fetch_public_claims
from app.tools.reconcile import reconcile_claims_vs_disclosures
from app.tools.sec_edgar import fetch_company_disclosures
from app.tools.taxonomy import COVERED_TICKERS, ITEM_TAXONOMY_8K, score_8k_items

from app.tools.security_tools import (
    screen_with_model_armor,
    screen_with_model_armor_tool,
)

# Wrap deterministic functions in ADK FunctionTool instances
fetch_company_disclosures_tool = FunctionTool(fetch_company_disclosures)
fetch_public_claims_tool = FunctionTool(fetch_public_claims)
reconcile_claims_vs_disclosures_tool = FunctionTool(reconcile_claims_vs_disclosures)

__all__ = [
    "fetch_company_disclosures",
    "fetch_public_claims",
    "reconcile_claims_vs_disclosures",
    "save_user_preferences",
    "recall_user_preferences",
    "screen_with_model_armor",
    "fetch_company_disclosures_tool",
    "fetch_public_claims_tool",
    "reconcile_claims_vs_disclosures_tool",
    "save_user_preferences_tool",
    "recall_user_preferences_tool",
    "screen_with_model_armor_tool",
    "COVERED_TICKERS",
    "ITEM_TAXONOMY_8K",
    "score_8k_items",
]

