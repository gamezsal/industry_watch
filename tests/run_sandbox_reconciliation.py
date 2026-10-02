"""Execute reconciliation join and materiality scoring in the Vertex AI Code Execution Sandbox."""

import json
import os
import vertexai
from dotenv import load_dotenv

from app.tools.sec_edgar import fetch_company_disclosures
from app.tools.public_claims import fetch_public_claims
from app.tools.taxonomy import ITEM_TAXONOMY_8K

load_dotenv()

PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT", "your-gcp-project-id")
LOCATION = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")
PROJECT_NUMBER = os.environ.get("GOOGLE_CLOUD_PROJECT_NUMBER", "your-project-number")
ENGINE_ID = os.environ.get("GOOGLE_CLOUD_AGENT_ENGINE_ID", "your-agent-engine-id")
SANDBOX_ID = os.environ.get("VERTEX_AI_SANDBOX_ID", "your-sandbox-id")

ENGINE_NAME = os.environ.get(
    "GOOGLE_CLOUD_AGENT_ENGINE_RESOURCE_NAME",
    f"projects/{PROJECT_NUMBER}/locations/{LOCATION}/reasoningEngines/{ENGINE_ID}",
)
SANDBOX_NAME = os.environ.get(
    "VERTEX_AI_SANDBOX_NAME",
    f"projects/{PROJECT_NUMBER}/locations/{LOCATION}/reasoningEngines/{ENGINE_ID}/sandboxEnvironments/{SANDBOX_ID}",
)

def main():
    client = vertexai.Client(project=PROJECT_ID, location=LOCATION)

    # Fetch disclosures and claims for NVDA and AMD
    nvda_disc = fetch_company_disclosures("NVDA", limit=5).get("disclosures", [])
    nvda_claims = fetch_public_claims("NVDA", limit=5).get("claims", [])

    amd_disc = fetch_company_disclosures("AMD", limit=5).get("disclosures", [])
    amd_claims = fetch_public_claims("AMD", limit=5).get("claims", [])

    payload = {
        "NVDA": {"disclosures": nvda_disc, "claims": nvda_claims},
        "AMD": {"disclosures": amd_disc, "claims": amd_claims},
        "taxonomy": ITEM_TAXONOMY_8K,
    }

    raw_payload_json = json.dumps(payload)

    # Python script to run INSIDE the code-execution sandbox
    sandbox_code = f"""
import json
from datetime import datetime

payload = json.loads({json.dumps(raw_payload_json)})
taxonomy = payload["taxonomy"]

def parse_date(d_str):
    if not d_str: return None
    try: return datetime.strptime(d_str[:10], "%Y-%m-%d")
    except Exception: return None

def score_items(items):
    weights = []
    tiers = []
    for item in items:
        meta = taxonomy.get(item, {{"weight": 2, "tier": "LOW", "title": "Other"}})
        weights.append(meta["weight"])
        tiers.append(meta["tier"])
    max_w = max(weights) if weights else 0
    if max_w >= 9: tier = "CRITICAL"
    elif max_w >= 7: tier = "HIGH"
    elif max_w >= 4: tier = "MEDIUM"
    else: tier = "LOW"
    comp = round(min(100.0, max_w * 10.0 + (len(items) - 1) * 3.0), 1)
    return {{"tier": tier, "max_weight": max_w, "composite_score": comp}}

results = {{}}

for ticker in ["NVDA", "AMD"]:
    disclosures = payload[ticker]["disclosures"]
    claims = payload[ticker]["claims"]
    
    parsed_filings = []
    for d in disclosures:
        dt = parse_date(d.get("filing_date") or d.get("report_date"))
        items = d.get("items", [])
        parsed_filings.append({{
            "accession": d.get("accession_number"),
            "filing_date": d.get("filing_date"),
            "items": items,
            "dt": dt,
            "materiality": score_items(items),
            "description": d.get("description", ""),
            "raw": d
        }})

    parsed_claims = []
    for c in claims:
        dt = parse_date(c.get("published_date"))
        parsed_claims.append({{
            "claim_id": c.get("claim_id"),
            "title": c.get("title"),
            "published_date": c.get("published_date"),
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
            if dist <= 5 and dist < min_dist:
                min_dist = dist
                best_f = (f, dist)
        if best_f:
            f, dist = best_f
            matched.append({{
                "claim_id": c["claim_id"],
                "claim_title": c["title"],
                "claim_date": c["published_date"],
                "sec_accession": f["accession"],
                "sec_filing_date": f["filing_date"],
                "items": f["items"],
                "days_offset": dist,
                "materiality_tier": f["materiality"]["tier"],
                "materiality_score": f["materiality"]["composite_score"]
            }})
            matched_accessions.add(f["accession"])
            matched_claims.add(c["claim_id"])

    filing_only = []
    for f in parsed_filings:
        if f["accession"] not in matched_accessions:
            filing_only.append({{
                "sec_accession": f["accession"],
                "filing_date": f["filing_date"],
                "items": f["items"],
                "materiality_tier": f["materiality"]["tier"],
                "materiality_score": f["materiality"]["composite_score"],
                "description": f["description"]
            }})

    claim_only = []
    for c in parsed_claims:
        if c["claim_id"] not in matched_claims:
            claim_only.append({{
                "claim_id": c["claim_id"],
                "title": c["title"],
                "published_date": c["published_date"],
                "warning": "UNSUBSTANTIATED_BY_SEC_8K"
            }})

    results[ticker] = {{
        "matched_count": len(matched),
        "filing_only_count": len(filing_only),
        "claim_only_count": len(claim_only),
        "matched": matched,
        "filing_only": filing_only,
        "claim_only": claim_only
    }}

print("--- SANDBOX_RECONCILIATION_OUTPUT_START ---")
print(json.dumps(results, indent=2))
print("--- SANDBOX_RECONCILIATION_OUTPUT_END ---")
"""

    print("Sending reconciliation join and materiality scoring to sandbox:")
    print(f"Sandbox: {SANDBOX_NAME}")
    res = client.agent_engines.sandboxes.execute_code(
        name=SANDBOX_NAME,
        input_data={"code": sandbox_code}
    )

    for output in res.outputs:
        raw_text = output.data.decode("utf-8")
        try:
            parsed = json.loads(raw_text)
            msg_out = parsed.get("msg_out", "")
            msg_err = parsed.get("msg_err", "")
            print("Sandbox Execution msg_out:\n", msg_out)
            if msg_err:
                print("Sandbox Execution msg_err:\n", msg_err)
        except Exception:
            print("Raw output:\n", raw_text)

if __name__ == "__main__":
    main()
