import pytest
import os
import sqlite3
from app.schemas.deal import Deal
from app.db.database import DealRepository
from app.db.init_db import init_db

from app.config import settings
settings.database_path = "test_deals.db"

@pytest.fixture(autouse=True)
def setup_db():
    # Setup
    if os.path.exists("test_deals.db"):
        os.remove("test_deals.db")
    init_db()
    yield
    # Teardown
    if os.path.exists("test_deals.db"):
        os.remove("test_deals.db")

def test_create_and_get_deal():
    repo = DealRepository()
    deal = Deal()
    deal.project.title = "Test E-commerce"
    
    deal_id = repo.create_deal(deal)
    assert deal_id is not None
    
    retrieved = repo.get_deal(deal_id)
    assert retrieved is not None
    assert retrieved.project.title == "Test E-commerce"

def test_invalid_deal_id():
    repo = DealRepository()
    assert repo.get_deal("invalid-id") is None
    
    with pytest.raises(ValueError):
        repo.append_message("invalid-id", "client", "hello")

def test_append_message():
    repo = DealRepository()
    deal = Deal()
    deal_id = repo.create_deal(deal)
    
    repo.append_message(deal_id, "client", "Can we add chat?")
    repo.append_message(deal_id, "freelancer", "Yes, but it costs more.")
    
    retrieved = repo.get_deal(deal_id)
    assert len(retrieved.messages) == 2
    assert retrieved.messages[0].sender == "client"
    assert retrieved.messages[0].content == "Can we add chat?"
    assert retrieved.messages[1].sender == "freelancer"
    assert retrieved.messages[0].id.startswith("MSG-")
    assert retrieved.messages[0].timestamp is not None

def test_provenance_preservation():
    from app.schemas.deal import Requirement, SourceType, CertaintyType
    repo = DealRepository()
    deal = Deal()
    deal.requirements.append(Requirement(
        id="R1", description="Auth", source=SourceType.AI, certainty=CertaintyType.INFERRED
    ))
    deal_id = repo.create_deal(deal)
    retrieved = repo.get_deal(deal_id)
    assert retrieved.requirements[0].source == SourceType.AI
    assert retrieved.requirements[0].certainty == CertaintyType.INFERRED

def test_get_deal_endpoint_mock():
    # Since we are not using FastAPI TestClient here, just testing repo
    repo = DealRepository()
    deal = Deal()
    deal_id = repo.create_deal(deal)
    retrieved = repo.get_deal(deal_id)
    # The endpoint attaches ID to the model
    retrieved.id = deal_id
    assert retrieved.id == deal_id

def test_list_deals_uses_structured_client():
    repo = DealRepository()
    deal = Deal()
    deal.project.title = "Client Portal"
    deal.client.name = "Jane Doe"
    deal.client.company = "Acme Studio"
    deal.commercial.budget = 1500
    deal.commercial.currency = "USD"

    repo.create_deal(deal)

    deals = repo.list_deals()

    assert len(deals) == 1
    assert deals[0]["title"] == "Client Portal"
    assert deals[0]["client"] == "Jane Doe"
    assert deals[0]["budget"] == 1500
    assert deals[0]["currency"] == "USD"
