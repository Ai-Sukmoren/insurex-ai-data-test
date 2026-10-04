import pytest
from pydantic import ValidationError

from sales_agent.leads import Lead, LeadDraft, LeadRepository, normalise_phone


@pytest.mark.parametrize("raw,expected", [
    ("081-234-5678", "0812345678"),
    ("+66 81 234 5678", "0812345678"),
    ("66812345678", "0812345678"),
    ("02-123-4567", "021234567"),
])
def test_phone_normalisation(raw, expected):
    assert normalise_phone(raw) == expected


@pytest.mark.parametrize("raw", ["12345", "0012345678", "", "081-234-567"])
def test_invalid_phone_rejected(raw):
    with pytest.raises(ValueError):
        normalise_phone(raw)


def test_lead_validation():
    lead = Lead(name="  Alice   Wong ", occupation="nurse", monthly_income=32000, phone="089-765-4321", session_id="s1")
    assert (lead.name, lead.phone) == ("Alice Wong", "0897654321")
    with pytest.raises(ValidationError):
        Lead(name="A", occupation="nurse", monthly_income=-5, phone="123", session_id="s1")


def test_draft_merge_keeps_earlier_values_and_reports_missing():
    draft = LeadDraft(name="Alice").merge(LeadDraft(occupation="nurse", name=None))
    assert draft.name == "Alice" and draft.occupation == "nurse"
    assert draft.missing() == ["monthly_income", "phone"]


def test_repository_round_trip(tmp_path):
    repo = LeadRepository(tmp_path / "leads.db")
    lead_id = repo.save(Lead(name="Bob Lee", occupation="driver", monthly_income=18000, phone="0912345678", session_id="b"))
    rows = repo.all()
    assert rows[0]["lead_id"] == lead_id and rows[0]["phone"] == "0912345678"
