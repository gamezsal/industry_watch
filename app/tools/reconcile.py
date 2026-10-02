"""Deterministic reconciliation engine joining public claims and SEC 8-K disclosures."""

import json
import logging
import os
from datetime import datetime, timedelta
from typing import Any

from dotenv import load_dotenv

from app.tools.public_claims import fetch_public_claims
from app.tools.sec_edgar import fetch_company_disclosures
from app.tools.taxonomy import COVERED_TICKERS, ITEM_TAXONOMY_8K, score_8k_items

load_dotenv()

logger = logging.getLogger(__name__)

_PROJECT_NUMBER = os.environ.get("GOOGLE_CLOUD_PROJECT_NUMBER", "your-project-number")
_LOCATION = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")
_ENGINE_ID = os.environ.get("GOOGLE_CLOUD_AGENT_ENGINE_ID", "your-agent-engine-id")
_SANDBOX_ID = os.environ.get("VERTEX_AI_SANDBOX_ID", "your-sandbox-id")

DEFAULT_SANDBOX_NAME = os.environ.get(
    "VERTEX_AI_SANDBOX_NAME",
    f"projects/{_PROJECT_NUMBER}/locations/{_LOCATION}/reasoningEngines/{_ENGINE_ID}/sandboxEnvironments/{_SANDBOX_ID}",
)


def _parse_date(date_str: str) -> datetime | None:
    """Parse YYYY-MM-DD string into datetime object."""
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str[:10], "%Y-%m-%d")
    except ValueError:
        return None


def _calculate_keyword_overlap(text: str, item_codes: list[str]) -> list[str]:
    """Identify which 8-K item keywords appear in the given text."""
    text_lower = text.lower()
    matched_items = []
    for code in item_codes:
        meta = ITEM_TAXONOMY_8K.get(code)
        if not meta:
            continue
        keywords = meta.get("keywords", [])
        if any(kw in text_lower for kw in keywords):
            matched_items.append(code)
    return matched_items


def _detect_claim_materiality_profile(claim_title: str, claim_snippet: str) -> dict[str, Any]:
    """Scan untrusted public claim text against 8-K taxonomy to assess claimed materiality."""
    combined_text = f"{claim_title} {claim_snippet}".lower()
    detected_codes = []

    for code, meta in ITEM_TAXONOMY_8K.items():
        if code in ("9.01", "1.04"):
            continue
        for kw in meta.get("keywords", []):
            # Require word boundary or distinctive phrase to avoid false positives
            if f" {kw} " in f" {combined_text} " or kw in combined_text:
                if code not in detected_codes:
                    detected_codes.append(code)
                break

    if detected_codes:
        tax_eval = score_8k_items(detected_codes)
        return {
            "implied_8k_items": detected_codes,
            "implied_materiality_tier": tax_eval["tier"],
            "implied_composite_score": tax_eval["composite_score"],
            "risk_assessment": (
                f"POTENTIAL_DISCREPANCY: Claim asserts {tax_eval['tier']} materiality events "
                f"({', '.join(detected_codes)}) without verified Form 8-K on record."
            ),
        }

    return {
        "implied_8k_items": [],
        "implied_materiality_tier": "LOW",
        "implied_composite_score": 15,
        "risk_assessment": "General industry commentary, product marketing, or unclassified rumors.",
    }


def execute_reconciliation_in_sandbox(
    ticker: str,
    disclosures: list[dict[str, Any]],
    claims: list[dict[str, Any]],
    date_window_days: int = 5,
    sandbox_name: str | None = None,
) -> dict[str, Any] | None:
    """Dispatches the reconciliation join and Form 8-K materiality scoring to the Vertex AI Code Execution Sandbox."""
    try:
        import vertexai

        target_sandbox = sandbox_name or os.environ.get("VERTEX_AI_SANDBOX_NAME", DEFAULT_SANDBOX_NAME)
        project = os.environ.get("GOOGLE_CLOUD_PROJECT", "your-gcp-project-id")
        location = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")

        client = vertexai.Client(project=project, location=location)

        payload = {
            "ticker": ticker,
            "disclosures": disclosures,
            "claims": claims,
            "date_window_days": date_window_days,
            "taxonomy": ITEM_TAXONOMY_8K,
        }
        raw_json_str = json.dumps(payload)

        sandbox_py = f"""
import json
from datetime import datetime

payload = json.loads({json.dumps(raw_json_str)})
ticker = payload["ticker"]
disclosures = payload["disclosures"]
claims = payload["claims"]
date_window_days = payload["date_window_days"]
taxonomy = payload["taxonomy"]

def parse_date(d_str):
    if not d_str: return None
    try: return datetime.strptime(d_str[:10], "%Y-%m-%d")
    except Exception: return None

def score_items(items):
    weights = []
    for item in items:
        meta = taxonomy.get(item, {{"weight": 2, "tier": "LOW"}})
        weights.append(meta.get("weight", 2))
    max_w = max(weights) if weights else 0
    if max_w >= 9: tier = "CRITICAL"
    elif max_w >= 7: tier = "HIGH"
    elif max_w >= 4: tier = "MEDIUM"
    else: tier = "LOW"
    comp = round(min(100.0, max_w * 10.0 + (len(items) - 1) * 3.0), 1)
    return {{"tier": tier, "max_weight": max_w, "composite_score": comp}}

parsed_filings = []
for d in disclosures:
    dt = parse_date(d.get("filing_date") or d.get("report_date"))
    items = d.get("items", [])
    parsed_filings.append({{
        "accession": d.get("accession_number"),
        "filing_date": d.get("filing_date"),
        "report_date": d.get("report_date"),
        "items": items,
        "dt": dt,
        "materiality": score_items(items),
        "description": d.get("description", "8-K"),
        "doc_url": d.get("doc_url", ""),
        "raw": d
    }})

parsed_claims = []
for c in claims:
    dt = parse_date(c.get("published_date"))
    parsed_claims.append({{
        "claim_id": c.get("claim_id"),
        "title": c.get("title"),
        "published_date": c.get("published_date"),
        "source_type": c.get("source_type"),
        "url": c.get("url"),
        "snippet": c.get("snippet", ""),
        "dt": dt,
        "raw": c
    }})

matched = []
matched_accessions = set()
matched_claims = set()

for c in parsed_claims:
    if not c["dt"]: continue
    best_f = None
    min_dist = 999999
    for f in parsed_filings:
        if not f["dt"]: continue
        dist = abs((c["dt"] - f["dt"]).days)
        if dist <= date_window_days and dist < min_dist:
            min_dist = dist
            best_f = (f, dist)
    if best_f:
        f, dist = best_f
        matched.append({{
            "match_id": f"MATCH-{{ticker}}-{{len(matched)+1:02d}}",
            "claim_id": c["claim_id"],
            "claim_title": c["title"],
            "claim_published_date": c["published_date"],
            "claim_source_type": c["source_type"],
            "claim_url": c["url"],
            "accession_number": f["accession"],
            "filing_date": f["filing_date"],
            "report_date": f["report_date"],
            "filing_items": f["items"],
            "filing_description": f["description"],
            "filing_doc_url": f["doc_url"],
            "days_offset": dist,
            "corroborated_items": f["items"],
            "materiality_score": f["materiality"]["composite_score"],
            "materiality_tier": f["materiality"]["tier"],
            "taxonomy_summary": f"Items {{f['items']}} scored in sandbox",
            "verification_status": "OFFICIALLY_CORROBORATED",
            "notes": f"Corroborated by Form 8-K {{f['accession']}} ({{dist}}d offset)."
        }})
        matched_accessions.add(f["accession"])
        matched_claims.add(c["claim_id"])

filing_only = []
for f in parsed_filings:
    if f["accession"] not in matched_accessions:
        filing_only.append({{
            "accession_number": f["accession"],
            "form": "8-K",
            "filing_date": f["filing_date"],
            "report_date": f["report_date"],
            "items": f["items"],
            "description": f["description"],
            "doc_url": f["doc_url"],
            "materiality_score": f["materiality"]["composite_score"],
            "materiality_tier": f["materiality"]["tier"],
            "taxonomy_evaluation": f"Taxonomy items: {{f['items']}}",
            "status": "UNCOVERED_REGULATORY_DISCLOSURE",
            "analyst_implication": "Material SEC disclosure unnoted in public media flow." if f["materiality"]["tier"] in ("CRITICAL", "HIGH") else "Routine regulatory filing."
        }})

claim_only = []
for c in parsed_claims:
    if c["claim_id"] not in matched_claims:
        claim_only.append({{
            "claim_id": c["claim_id"],
            "title": c["title"],
            "published_date": c["published_date"],
            "source_type": c["source_type"],
            "url": c["url"],
            "snippet": c["snippet"],
            "is_untrusted": True,
            "status": "UNSUBSTANTIATED_BY_SEC_8K",
            "implied_materiality_tier": "MEDIUM",
            "implied_materiality_score": 50.0,
            "risk_flag": "Claim lacks SEC Form 8-K corroboration.",
            "verification_warning": "UNVERIFIED MEDIA CLAIM: No corresponding Form 8-K found."
        }})

res = {{
    "status": "success",
    "ticker": ticker,
    "date_window_days": date_window_days,
    "execution_mode": "VERTEX_AI_SANDBOX_ENVIRONMENT",
    "reconciliation_metrics": {{
        "total_public_claims": len(claims),
        "total_sec_disclosures": len(disclosures),
        "matched_count": len(matched),
        "filing_only_count": len(filing_only),
        "claim_only_count": len(claim_only),
        "corroboration_rate_pct": round(len(matched) / len(claims) * 100, 1) if claims else 0.0,
        "highest_materiality_tier": max([m["materiality_tier"] for m in matched + filing_only], default="LOW"),
        "highest_materiality_score": max([m["materiality_score"] for m in matched + filing_only], default=0.0),
    }},
    "buckets": {{
        "matched": matched,
        "filing_only": filing_only,
        "claim_only": claim_only,
    }}
}}

print("###RESULT_START###")
print(json.dumps(res))
print("###RESULT_END###")
"""
        exec_res = client.agent_engines.sandboxes.execute_code(
            name=target_sandbox,
            input_data={"code": sandbox_py},
        )
        for output in exec_res.outputs:
            raw_text = output.data.decode("utf-8")
            if "###RESULT_START###" in raw_text:
                part = raw_text.split("###RESULT_START###")[1].split("###RESULT_END###")[0].strip()
                parsed_res = json.loads(part)
                parsed_res["sandbox_resource_name"] = target_sandbox
                return parsed_res
            try:
                msg_out = json.loads(raw_text).get("msg_out", "")
                if "###RESULT_START###" in msg_out:
                    part = msg_out.split("###RESULT_START###")[1].split("###RESULT_END###")[0].strip()
                    parsed_res = json.loads(part)
                    parsed_res["sandbox_resource_name"] = target_sandbox
                    return parsed_res
            except Exception:
                pass
        return None
    except Exception as exc:
        logger.info("Sandbox execution bypassed or unavailable (%s); executing locally.", exc)
        return None


def reconcile_claims_vs_disclosures(
    ticker: str,
    disclosures: list[dict[str, Any]] | None = None,
    claims: list[dict[str, Any]] | None = None,
    date_window_days: int = 5,
    run_in_sandbox: bool = True,
) -> dict[str, Any]:
    """Reconcile public news/IR claims against official SEC Form 8-K filings for a company.

    Joins on CIK/ticker and date proximity window, classifies events into three mutually
    exclusive buckets (matched, filing-only, and claim-only), and computes deterministic
    materiality scores based on the SEC Form 8-K item taxonomy in the code execution sandbox.

    Args:
        ticker: Covered semiconductor ticker (NVDA, AMD, INTC, MU, AVGO).
        disclosures: Optional list of official disclosures (auto-fetched if omitted or empty).
        claims: Optional list of public claims (auto-fetched if omitted or empty).
        date_window_days: Proximity window in days to consider a claim and filing related (default: 5).
        run_in_sandbox: Whether to execute the join and scoring in the code execution sandbox (default: True).

    Returns:
        Structured reconciliation report with matched, filing-only, and claim-only buckets,
        materiality scoring, and discrepancy risk assessments.
    """
    clean_ticker = ticker.strip().upper()
    meta = COVERED_TICKERS.get(clean_ticker)
    if not meta:
        return {
            "status": "error",
            "message": f"Ticker '{clean_ticker}' is not supported. Covered tickers: {list(COVERED_TICKERS.keys())}",
        }

    # Auto-fetch if not supplied
    if disclosures is None or not disclosures:
        disc_res = fetch_company_disclosures(clean_ticker, limit=10)
        disclosures = disc_res.get("disclosures", [])

    if claims is None or not claims:
        claim_res = fetch_public_claims(clean_ticker, limit=10)
        claims = claim_res.get("claims", [])

    if run_in_sandbox:
        sandbox_result = execute_reconciliation_in_sandbox(
            clean_ticker, disclosures, claims, date_window_days
        )
        if sandbox_result:
            return sandbox_result

    matched_pairs: list[dict[str, Any]] = []
    matched_claim_ids: set[str] = set()
    matched_accessions: set[str] = set()

    # Pre-parse dates
    parsed_filings = []
    for disc in disclosures:
        f_date = _parse_date(disc.get("filing_date", ""))
        r_date = _parse_date(disc.get("report_date", ""))
        parsed_filings.append({
            "raw": disc,
            "filing_date": f_date,
            "report_date": r_date or f_date,
            "items": disc.get("items", []),
            "accession": disc.get("accession_number", ""),
            "materiality": disc.get("materiality", score_8k_items(disc.get("items", []))),
        })

    parsed_claims = []
    for clm in claims:
        p_date = _parse_date(clm.get("published_date", ""))
        parsed_claims.append({
            "raw": clm,
            "published_date": p_date,
            "claim_id": clm.get("claim_id", ""),
            "title": clm.get("title", ""),
            "snippet": clm.get("snippet", ""),
        })

    # Join logic: match on CIK/ticker and date window (+/- date_window_days)
    for c in parsed_claims:
        if not c["published_date"]:
            continue

        best_match = None
        min_distance = 999999

        for f in parsed_filings:
            target_date = f["report_date"] or f["filing_date"]
            if not target_date:
                continue

            delta_days = abs((c["published_date"] - target_date).days)
            if delta_days <= date_window_days:
                # Semantic relevance check: verify if keywords overlap or shared company context
                claim_text = f"{c['title']} {c['snippet']}"
                item_overlaps = _calculate_keyword_overlap(claim_text, f["items"])

                # Proximity match valid if within window and either has item overlap or is within tight 2-day window
                if delta_days <= 2 or item_overlaps:
                    if delta_days < min_distance:
                        min_distance = delta_days
                        best_match = (f, delta_days, item_overlaps)

        if best_match:
            f_matched, distance, item_overlaps = best_match
            matched_pairs.append({
                "match_id": f"MATCH-{clean_ticker}-{len(matched_pairs)+1:02d}",
                "claim_id": c["claim_id"],
                "claim_title": c["title"],
                "claim_published_date": c["raw"].get("published_date"),
                "claim_source_type": c["raw"].get("source_type"),
                "claim_url": c["raw"].get("url"),
                "accession_number": f_matched["accession"],
                "filing_date": f_matched["raw"].get("filing_date"),
                "report_date": f_matched["raw"].get("report_date"),
                "filing_items": f_matched["items"],
                "filing_description": f_matched["raw"].get("description"),
                "filing_doc_url": f_matched["raw"].get("doc_url"),
                "days_offset": distance,
                "corroborated_items": item_overlaps if item_overlaps else f_matched["items"],
                "materiality_score": f_matched["materiality"]["composite_score"],
                "materiality_tier": f_matched["materiality"]["tier"],
                "taxonomy_summary": f_matched["materiality"]["summary"],
                "verification_status": "OFFICIALLY_CORROBORATED",
                "notes": (
                    f"Public report corroborated by SEC Form 8-K (Accession: {f_matched['accession']}) "
                    f"filed {distance} day(s) apart."
                ),
            })
            matched_claim_ids.add(c["claim_id"])
            matched_accessions.add(f_matched["accession"])

    # Bucket 2: Filing-only (Regulatory filings with no corresponding media claims found)
    filing_only: list[dict[str, Any]] = []
    for f in parsed_filings:
        if f["accession"] not in matched_accessions:
            mat = f["materiality"]
            filing_only.append({
                "accession_number": f["accession"],
                "form": f["raw"].get("form", "8-K"),
                "filing_date": f["raw"].get("filing_date"),
                "report_date": f["raw"].get("report_date"),
                "items": f["items"],
                "description": f["raw"].get("description"),
                "doc_url": f["raw"].get("doc_url"),
                "materiality_score": mat["composite_score"],
                "materiality_tier": mat["tier"],
                "taxonomy_evaluation": mat["summary"],
                "status": "UNCOVERED_REGULATORY_DISCLOSURE",
                "analyst_implication": (
                    "CRITICAL OMISSION: Material SEC disclosure unnoted in public media flow."
                    if mat["tier"] in ("CRITICAL", "HIGH")
                    else "Routine regulatory filing without major public coverage."
                ),
            })

    # Bucket 3: Claim-only (Public claims with no corresponding SEC 8-K filing)
    claim_only: list[dict[str, Any]] = []
    for c in parsed_claims:
        if c["claim_id"] not in matched_claim_ids:
            materiality_profile = _detect_claim_materiality_profile(c["title"], c["snippet"])
            claim_only.append({
                "claim_id": c["claim_id"],
                "title": c["title"],
                "published_date": c["raw"].get("published_date"),
                "source_type": c["raw"].get("source_type"),
                "source_channel": c["raw"].get("source_channel"),
                "url": c["raw"].get("url"),
                "snippet": c["snippet"],
                "is_untrusted": True,
                "status": "UNSUBSTANTIATED_BY_SEC_8K",
                "implied_materiality_tier": materiality_profile["implied_materiality_tier"],
                "implied_materiality_score": materiality_profile["implied_composite_score"],
                "risk_flag": materiality_profile["risk_assessment"],
                "verification_warning": (
                    "UNVERIFIED MEDIA CLAIM: No corresponding Form 8-K found within date window. "
                    "Treat as unverified rumor, corporate PR spin, or ordinary course marketing."
                ),
            })

    # Summary metrics
    total_claims_count = len(claims)
    total_filings_count = len(disclosures)
    matched_count = len(matched_pairs)

    match_rate = round((matched_count / total_claims_count * 100), 1) if total_claims_count > 0 else 0.0

    # Determine highest materiality detected across matched and filing-only
    highest_score = 0
    highest_tier = "LOW"
    for m in matched_pairs:
        if m["materiality_score"] > highest_score:
            highest_score = m["materiality_score"]
            highest_tier = m["materiality_tier"]
    for fo in filing_only:
        if fo["materiality_score"] > highest_score:
            highest_score = fo["materiality_score"]
            highest_tier = fo["materiality_tier"]

    return {
        "status": "success",
        "ticker": clean_ticker,
        "company_name": meta["company_name"],
        "cik": meta["cik"],
        "date_window_days": date_window_days,
        "reconciliation_metrics": {
            "total_public_claims": total_claims_count,
            "total_sec_disclosures": total_filings_count,
            "matched_count": matched_count,
            "filing_only_count": len(filing_only),
            "claim_only_count": len(claim_only),
            "corroboration_rate_pct": match_rate,
            "highest_materiality_tier": highest_tier,
            "highest_materiality_score": highest_score,
        },
        "buckets": {
            "matched": matched_pairs,
            "filing_only": filing_only,
            "claim_only": claim_only,
        },
        "analyst_guidance": (
            f"Reconciliation completed for {clean_ticker}. "
            f"{matched_count} claims verified against official Form 8-Ks; "
            f"{len(filing_only)} filings lack public media coverage; "
            f"{len(claim_only)} claims lack SEC corroboration. "
            "Every statement must be grounded strictly in SEC 8-K disclosures."
        ),
    }
