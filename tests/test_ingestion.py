import pytest
from app.services.ingestion import ingest_billing_data
from app.models.models import Resource
import json

def test_ingest_billing_data_csv(db):
    csv_content = b"resource_id,resource_type,state,cost,cpu_utilization,region\nvol-123,EBS,available,20.0,10.0,us-east-1"
    res = ingest_billing_data(db, csv_content, "data.csv", "AWS")
    assert res == 1
    resource = db.query(Resource).first()
    assert resource.resource_id == "vol-123"
    assert resource.resource_type == "EBS"
    assert resource.cost == 20.0

def test_ingest_billing_data_json(db):
    json_content = json.dumps([{"resource_id": "vm-123", "resource_type": "VM", "state": "Stopped", "cost": 100.5}]).encode('utf-8')
    res = ingest_billing_data(db, json_content, "data.json", "Azure")
    assert res == 1
    resource = db.query(Resource).first()
    assert resource.resource_id == "vm-123"
    assert resource.cost == 100.5

def test_ingest_billing_data_unsupported_format(db):
    with pytest.raises(ValueError, match="Unsupported file format"):
        ingest_billing_data(db, b"data", "data.txt", "AWS")

def test_ingest_billing_data_update_existing(db):
    csv_content1 = b"resource_id,resource_type,state,cost,cpu_utilization,region\nvol-123,EBS,available,20.0,10.0,us-east-1"
    ingest_billing_data(db, csv_content1, "data.csv", "AWS")
    
    # Update cost and state
    csv_content2 = b"resource_id,resource_type,state,cost,cpu_utilization,region\nvol-123,EBS,in-use,30.0,15.0,us-east-1"
    ingest_billing_data(db, csv_content2, "data.csv", "AWS")
    
    resource = db.query(Resource).filter_by(resource_id="vol-123").first()
    assert resource.state == "in-use"
    assert resource.cost == 30.0
    assert resource.cpu_utilization == 15.0

def test_ingest_billing_data_missing_fields(db):
    csv_content = b"random_field\n123"
    res = ingest_billing_data(db, csv_content, "data.csv", "AWS")
    assert res == 1
    resource = db.query(Resource).first()
    assert resource.resource_type == "Unknown"
    assert resource.state == "Unknown"
    assert resource.cost is None
    assert resource.cpu_utilization is None
