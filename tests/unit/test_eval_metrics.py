"""Unit tests for deterministic verbatim citation evaluation metrics."""

import pytest
from tests.eval.metrics.deterministic_citations import (
    evaluate_verbatim_citations,
    extract_accession_numbers,
    extract_8k_item_codes,
)


def test_extract_accession_numbers():
    """Verify regex extraction of SEC Form 8-K accession numbers."""
    text = (
        "NVIDIA filed Form 8-K under accession 0001045810-26-000073 and 0001045810-26-000078. "
        "A random number 1234567890 should not match."
    )
    accs = extract_accession_numbers(text)
    assert accs == {"0001045810-26-000073", "0001045810-26-000078"}


def test_extract_8k_item_codes():
    """Verify regex extraction of SEC Form 8-K taxonomy item codes."""
    text = "The filing reported Item 2.02, Item 5.02, and exhibits under 9.01. Ignore 99.99."
    items = extract_8k_item_codes(text)
    assert items == {"2.02", "5.02", "9.01"}


def test_evaluate_verbatim_citations_pass():
    """When all cited accessions and item codes appear in tool outputs, score must be 1.0."""
    response = (
        "Under Form 8-K 0001045810-26-000073, NVIDIA reported Item 2.02 (Results of Operations) "
        "and Item 9.01 (Financial Statements and Exhibits)."
    )
    tool_output = {
        "disclosures": [
            {
                "accession_number": "0001045810-26-000073",
                "items": ["2.02", "9.01"],
            }
        ]
    }
    result = evaluate_verbatim_citations(response, tool_output)
    assert result["score"] == 1.0
    assert result["is_grounded"] is True
    assert result["ungrounded_accessions"] == []
    assert result["ungrounded_item_codes"] == []
    assert "PASSED VERBATIM GROUNDEDNESS" in result["explanation"]


def test_evaluate_verbatim_citations_hallucinated_accession():
    """When an accession number is fabricated or missing from tool output, score must be 0.0."""
    response = (
        "NVIDIA filed 8-K 0001045810-26-999999 (FABRICATED) reporting Item 2.02."
    )
    tool_output = {
        "disclosures": [
            {
                "accession_number": "0001045810-26-000073",
                "items": ["2.02"],
            }
        ]
    }
    result = evaluate_verbatim_citations(response, tool_output)
    assert result["score"] == 0.0
    assert result["is_grounded"] is False
    assert result["ungrounded_accessions"] == ["0001045810-26-999999"]
    assert "FAILED VERBATIM GROUNDEDNESS" in result["explanation"]


def test_evaluate_verbatim_citations_hallucinated_item_code():
    """When an 8-K item code is cited that never appeared in tool output, score must be 0.0."""
    response = (
        "Under 8-K 0001045810-26-000073, the company disclosed Item 1.03 (Bankruptcy) and Item 2.02."
    )
    tool_output = {
        "disclosures": [
            {
                "accession_number": "0001045810-26-000073",
                "items": ["2.02", "9.01"],
            }
        ]
    }
    result = evaluate_verbatim_citations(response, tool_output)
    assert result["score"] == 0.0
    assert result["is_grounded"] is False
    assert result["ungrounded_item_codes"] == ["1.03"]
    assert "FAILED VERBATIM GROUNDEDNESS" in result["explanation"]
