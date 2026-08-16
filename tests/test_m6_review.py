import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.db.init_db import init_db
from app.db.database import DealRepository

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_db():
    init_db()
    yield

def test_approve_review():
    # Create deal
    deal_payload = {
        "client": {"name": "Test Client"},
        "project": {"title": "Test Project"},
        "commercial": {"budget": 1000, "currency": "USD"},
        "timeline": {},
        "scope": {"deliverables": ["A"]},
        "requirements": [],
        "dependencies": [],
        "unknowns": [],
        "risks": [],
        "questions": [],
        "decisions": [],
        "messages": [],
        "preflight": {"status": "ready"}
    }
    create_res = client.post("/api/deals", json=deal_payload)
    assert create_res.status_code == 200
    deal_id = create_res.json()["deal_id"]
    
    # Add Review Approve
    rev_payload = {
        "status": "approved",
        "draft": "This is an approved draft."
    }
    rev_res = client.post(f"/api/deals/{deal_id}/reviews", json=rev_payload)
    assert rev_res.status_code == 200
    review_id = rev_res.json()["review_id"]
    assert review_id.startswith("REV-")
    
    # Retrieve deal and check state
    get_res = client.get(f"/api/deals/{deal_id}")
    deal_data = get_res.json()
    assert len(deal_data["reviews"]) == 1
    assert deal_data["reviews"][0]["id"] == review_id
    assert deal_data["reviews"][0]["status"] == "approved"

def test_reject_review():
    # Create deal
    deal_payload = {
        "client": {"name": "Test Client"},
        "project": {"title": "Test Project"},
        "commercial": {"budget": 1000, "currency": "USD"},
        "timeline": {},
        "scope": {"deliverables": ["A"]},
        "requirements": [],
        "dependencies": [],
        "unknowns": [],
        "risks": [],
        "questions": [],
        "decisions": [],
        "messages": [],
        "preflight": {"status": "ready"}
    }
    create_res = client.post("/api/deals", json=deal_payload)
    deal_id = create_res.json()["deal_id"]
    
    # Add Review Reject
    rev_payload = {
        "status": "rejected",
        "draft": "This is a rejected draft."
    }
    rev_res = client.post(f"/api/deals/{deal_id}/reviews", json=rev_payload)
    assert rev_res.status_code == 200
    
    # Retrieve deal and check state
    get_res = client.get(f"/api/deals/{deal_id}")
    deal_data = get_res.json()
    assert deal_data["reviews"][0]["status"] == "rejected"

def test_error_deal_not_found():
    rev_payload = {
        "status": "approved",
        "draft": "Draft"
    }
    rev_res = client.post("/api/deals/nonexistent/reviews", json=rev_payload)
    assert rev_res.status_code == 404

def test_error_invalid_payload():
    create_res = client.post("/api/deals", json={"project": {"title": "A"}, "commercial": {}, "timeline": {}, "scope": {}})
    deal_id = create_res.json()["deal_id"]
    
    rev_res = client.post(f"/api/deals/{deal_id}/reviews", json={"status": "invalid_status", "draft": "A"})
    assert rev_res.status_code == 422 # Pydantic validation error because Enum doesn't match
    
def test_immutability():
    # Create deal
    deal_payload = {
        "client": {"name": "Test Client"},
        "project": {"title": "Test Project"},
        "commercial": {"budget": 1000, "currency": "USD"},
        "timeline": {},
        "scope": {"deliverables": ["A"]},
        "requirements": [],
        "dependencies": [],
        "unknowns": [],
        "risks": [],
        "questions": [],
        "decisions": [],
        "messages": [],
        "preflight": {"status": "ready"}
    }
    create_res = client.post("/api/deals", json=deal_payload)
    deal_id = create_res.json()["deal_id"]
    
    get_res_before = client.get(f"/api/deals/{deal_id}")
    deal_before = get_res_before.json()
    
    # Add Review
    rev_payload = {
        "status": "approved",
        "draft": "Draft"
    }
    client.post(f"/api/deals/{deal_id}/reviews", json=rev_payload)
    
    get_res_after = client.get(f"/api/deals/{deal_id}")
    deal_after = get_res_after.json()
    
    # Assert immutability of core fields
    assert deal_before["commercial"] == deal_after["commercial"]
    assert deal_before["scope"] == deal_after["scope"]
    assert deal_before["timeline"] == deal_after["timeline"]
    assert deal_before["preflight"] == deal_after["preflight"]
    assert deal_before["project"] == deal_after["project"]
    assert deal_before["client"] == deal_after["client"]
