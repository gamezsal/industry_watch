"""SEC Form 8-K Item Taxonomy and covered semiconductor ticker metadata."""

from typing import Any

COVERED_TICKERS: dict[str, dict[str, Any]] = {
    "NVDA": {
        "cik": "0001045810",
        "company_name": "NVIDIA Corporation",
        "sector": "Semiconductors",
        "industry": "Semiconductors & Semiconductor Equipment",
        "keywords": ["gpu", "blackwell", "hopper", "cuda", "infiniband", "datacenter", "ai", "spectrum-x"],
    },
    "AMD": {
        "cik": "0000002488",
        "company_name": "Advanced Micro Devices, Inc.",
        "sector": "Semiconductors",
        "industry": "Semiconductors & Semiconductor Equipment",
        "keywords": ["epyc", "instinct", "mi300", "mi325", "rocm", "ryzen", "datacenter", "xilinx"],
    },
    "INTC": {
        "cik": "0000050863",
        "company_name": "Intel Corporation",
        "sector": "Semiconductors",
        "industry": "Semiconductors & Semiconductor Equipment",
        "keywords": ["xeon", "foundry", "ifs", "18a", "core ultra", "gaudi", "packaging", "foveros"],
    },
    "MU": {
        "cik": "0000723125",
        "company_name": "Micron Technology, Inc.",
        "sector": "Semiconductors",
        "industry": "Semiconductors & Semiconductor Equipment",
        "keywords": ["hbm", "hbm3e", "hbm4", "dram", "nand", "memory", "bandwidth", "storage"],
    },
    "AVGO": {
        "cik": "0001730168",
        "company_name": "Broadcom Inc.",
        "sector": "Semiconductors",
        "industry": "Semiconductors & Semiconductor Equipment",
        "keywords": ["xpu", "asic", "tomahawk", "jericho", "ethernet", "optical", "vmware", "serdes"],
    },
}

# SEC Form 8-K Item Taxonomy and Materiality Weights (scale 1 - 10)
ITEM_TAXONOMY_8K: dict[str, dict[str, Any]] = {
    "1.01": {
        "title": "Entry into a Material Definitive Agreement",
        "section": "Section 1 - Registrant's Business and Operations",
        "weight": 8,
        "tier": "HIGH",
        "description": "Contracts, partnerships, large customer commitments, or IP agreements not made in ordinary course.",
        "keywords": ["agreement", "contract", "partnership", "definitive", "supply", "license"],
    },
    "1.02": {
        "title": "Termination of a Material Definitive Agreement",
        "section": "Section 1 - Registrant's Business and Operations",
        "weight": 8,
        "tier": "HIGH",
        "description": "Termination of material contracts or alliances.",
        "keywords": ["terminated", "termination", "cancelled", "contract end"],
    },
    "1.03": {
        "title": "Bankruptcy or Receivership",
        "section": "Section 1 - Registrant's Business and Operations",
        "weight": 10,
        "tier": "CRITICAL",
        "description": "Bankruptcy or receivership proceedings.",
        "keywords": ["bankruptcy", "receivership", "insolvency", "chapter 11"],
    },
    "1.04": {
        "title": "Mine Safety - Reporting of Shutdowns and Patterns of Violations",
        "section": "Section 1 - Registrant's Business and Operations",
        "weight": 2,
        "tier": "LOW",
        "description": "Mine safety orders or citations.",
        "keywords": ["mine safety", "msha"],
    },
    "1.05": {
        "title": "Material Cybersecurity Incidents",
        "section": "Section 1 - Registrant's Business and Operations",
        "weight": 9,
        "tier": "CRITICAL",
        "description": "Material cybersecurity breaches or system compromises.",
        "keywords": ["cybersecurity", "breach", "hack", "ransomware", "incident", "compromise"],
    },
    "2.01": {
        "title": "Completion of Acquisition or Disposition of Assets",
        "section": "Section 2 - Financial Information",
        "weight": 8,
        "tier": "HIGH",
        "description": "Significant M&A, business unit purchases or divestitures.",
        "keywords": ["acquisition", "acquired", "merger", "disposition", "sold", "divestiture"],
    },
    "2.02": {
        "title": "Results of Operations and Financial Condition",
        "section": "Section 2 - Financial Information",
        "weight": 9,
        "tier": "CRITICAL",
        "description": "Quarterly earnings, revenue numbers, financial results, or earnings release announcements.",
        "keywords": ["earnings", "revenue", "financial results", "quarterly", "margin", "guidance", "q1", "q2", "q3", "q4"],
    },
    "2.03": {
        "title": "Creation of a Direct Financial Obligation or Off-Balance Sheet Arrangement",
        "section": "Section 2 - Financial Information",
        "weight": 6,
        "tier": "MEDIUM",
        "description": "Major debt issuance, credit facilities, or note offerings.",
        "keywords": ["notes", "debt", "credit facility", "senior notes", "indenture", "offering"],
    },
    "2.04": {
        "title": "Triggering Events That Accelerate or Increase a Direct Financial Obligation",
        "section": "Section 2 - Financial Information",
        "weight": 7,
        "tier": "HIGH",
        "description": "Defaults, acceleration of debt repayment, or financial covenants breached.",
        "keywords": ["default", "acceleration", "covenant", "obligation increase"],
    },
    "2.05": {
        "title": "Costs Associated with Exit or Disposal Activities (Restructuring)",
        "section": "Section 2 - Financial Information",
        "weight": 8,
        "tier": "HIGH",
        "description": "Workforce reductions, fab closures, operational exits, or restructuring charges.",
        "keywords": ["restructuring", "layoffs", "workforce reduction", "closure", "exit costs"],
    },
    "2.06": {
        "title": "Material Impairments",
        "section": "Section 2 - Financial Information",
        "weight": 8,
        "tier": "HIGH",
        "description": "Asset writedowns, goodwill write-offs, or equipment impairment.",
        "keywords": ["impairment", "write-down", "goodwill impairment", "asset impairment"],
    },
    "3.01": {
        "title": "Notice of Delisting or Failure to Satisfy a Continued Listing Rule",
        "section": "Section 3 - Securities and Trading Markets",
        "weight": 8,
        "tier": "HIGH",
        "description": "Exchange notifications regarding non-compliance or delisting threats.",
        "keywords": ["delisting", "listing standard", "nasdaq notice", "nyse notice"],
    },
    "3.02": {
        "title": "Unregistered Sales of Equity Securities",
        "section": "Section 3 - Securities and Trading Markets",
        "weight": 5,
        "tier": "MEDIUM",
        "description": "Private placements or non-public stock transactions.",
        "keywords": ["unregistered sales", "private placement", "warrants"],
    },
    "3.03": {
        "title": "Material Modification to Rights of Security Holders",
        "section": "Section 3 - Securities and Trading Markets",
        "weight": 6,
        "tier": "MEDIUM",
        "description": "Dilution or alterations to shareholder rights.",
        "keywords": ["shareholder rights", "modification", "poison pill"],
    },
    "4.01": {
        "title": "Changes in Registrant's Certifying Accountant",
        "section": "Section 4 - Matters Related to Accountants and Financial Statements",
        "weight": 9,
        "tier": "CRITICAL",
        "description": "Auditor dismissal, resignation, or replacement.",
        "keywords": ["auditor", "accountant", "resignation of auditor", "dismissed auditor", "kpmg", "pwc", "ey", "deloitte"],
    },
    "4.02": {
        "title": "Non-Reliance on Previously Issued Financial Statements (Restatement)",
        "section": "Section 4 - Matters Related to Accountants and Financial Statements",
        "weight": 10,
        "tier": "CRITICAL",
        "description": "Financial restatements or withdrawal of previously published audit opinions.",
        "keywords": ["restatement", "non-reliance", "accounting error", "misstatement"],
    },
    "5.01": {
        "title": "Changes in Control of Registrant",
        "section": "Section 5 - Corporate Governance and Management",
        "weight": 10,
        "tier": "CRITICAL",
        "description": "Takeover, activist takeover, or voting control alteration.",
        "keywords": ["change in control", "takeover", "controlling shareholder"],
    },
    "5.02": {
        "title": "Departure/Election of Directors or Certain Officers; Compensatory Arrangements",
        "section": "Section 5 - Corporate Governance and Management",
        "weight": 8,
        "tier": "HIGH",
        "description": "CEO, CFO, CTO, or Board leadership appointments, resignations, or compensation packages.",
        "keywords": ["ceo", "cfo", "cto", "director", "officer", "departure", "appointment", "resignation", "elected"],
    },
    "5.03": {
        "title": "Amendments to Articles of Incorporation or Bylaws",
        "section": "Section 5 - Corporate Governance and Management",
        "weight": 3,
        "tier": "LOW",
        "description": "Charter amendments, fiscal year adjustments.",
        "keywords": ["bylaws", "charter", "articles of incorporation", "fiscal year"],
    },
    "5.07": {
        "title": "Submission of Matters to a Vote of Security Holders",
        "section": "Section 5 - Corporate Governance and Management",
        "weight": 3,
        "tier": "LOW",
        "description": "Annual shareholder meeting election and voting outcomes.",
        "keywords": ["voting results", "annual meeting", "proxy results", "stockholder vote"],
    },
    "7.01": {
        "title": "Regulation FD Disclosure",
        "section": "Section 7 - Regulation FD",
        "weight": 5,
        "tier": "MEDIUM",
        "description": "Investor presentations, conference slides, or press release disclosures furnished under Reg FD.",
        "keywords": ["regulation fd", "investor presentation", "conference", "slides", "fireside chat"],
    },
    "8.01": {
        "title": "Other Events",
        "section": "Section 8 - Other Events",
        "weight": 5,
        "tier": "MEDIUM",
        "description": "Discretionary disclosures of events deemed of importance by management.",
        "keywords": ["other events", "press release", "litigation update", "product update", "announcement"],
    },
    "9.01": {
        "title": "Financial Statements and Exhibits",
        "section": "Section 9 - Financial Statements and Exhibits",
        "weight": 2,
        "tier": "LOW",
        "description": "Filed exhibits, press releases, or XBRL data attached to 8-K.",
        "keywords": ["exhibit", "press release exhibit", "99.1", "financial statements"],
    },
}


def score_8k_items(items: list[str]) -> dict[str, Any]:
    """Score the materiality of a list of 8-K item codes against the SEC taxonomy."""
    if not items:
        return {
            "composite_score": 10,
            "max_weight": 1,
            "tier": "LOW",
            "evaluated_items": [],
            "summary": "No specific 8-K items declared or general filing.",
        }

    evaluated = []
    max_weight = 1
    total_weights = 0

    for raw_item in items:
        cleaned = raw_item.strip()
        # Normalise e.g. "Item 2.02" -> "2.02"
        if cleaned.lower().startswith("item "):
            cleaned = cleaned[5:].strip()

        taxonomy_entry = ITEM_TAXONOMY_8K.get(cleaned)
        if taxonomy_entry:
            evaluated.append({
                "item_code": cleaned,
                "title": taxonomy_entry["title"],
                "section": taxonomy_entry["section"],
                "weight": taxonomy_entry["weight"],
                "tier": taxonomy_entry["tier"],
                "description": taxonomy_entry["description"],
            })
            if taxonomy_entry["weight"] > max_weight:
                max_weight = taxonomy_entry["weight"]
            total_weights += taxonomy_entry["weight"]
        else:
            evaluated.append({
                "item_code": cleaned,
                "title": "Custom / Uncategorized 8-K Item",
                "section": "Unclassified",
                "weight": 4,
                "tier": "MEDIUM",
                "description": "Item not in standard numbered taxonomy.",
            })
            if 4 > max_weight:
                max_weight = 4
            total_weights += 4

    # Composite score on 0-100 scale: combination of max severity + additive breadth
    composite_score = min(100, (max_weight * 8) + (len(evaluated) * 4))

    if max_weight >= 9:
        overall_tier = "CRITICAL"
    elif max_weight >= 7:
        overall_tier = "HIGH"
    elif max_weight >= 5:
        overall_tier = "MEDIUM"
    else:
        overall_tier = "LOW"

    return {
        "composite_score": composite_score,
        "max_weight": max_weight,
        "tier": overall_tier,
        "evaluated_items": evaluated,
        "summary": f"{overall_tier} materiality: max weight {max_weight}/10 across {len(evaluated)} item(s).",
    }
