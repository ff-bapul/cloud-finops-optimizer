import pytest
from unittest.mock import patch
from app.models.models import Rule, Finding, Resource

def test_upload_billing_success(client, mocker):
    mocker.patch("app.api.endpoints.ingest_billing_data", return_value=5)
    response = client.post(
        "/api/upload",
        data={"provider": "AWS"},
        files={"file": ("test.csv", b"dummy content", "text/csv")}
    )
    assert response.status_code == 200
    assert "Successfully ingested 5 resources" in response.json()["message"]

def test_upload_billing_error(client, mocker):
    mocker.patch("app.api.endpoints.ingest_billing_data", side_effect=ValueError("Bad format"))
    response = client.post(
        "/api/upload",
        data={"provider": "AWS"},
        files={"file": ("test.txt", b"dummy content", "text/plain")}
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Bad format"

def test_trigger_analysis_success(client, mocker):
    mocker.patch("app.api.endpoints.evaluate_rules", return_value=3)
    response = client.post("/api/analyze")
    assert response.status_code == 200
    assert "Generated 3 new findings" in response.json()["message"]

def test_trigger_analysis_error(client, mocker):
    mocker.patch("app.api.endpoints.evaluate_rules", side_effect=Exception("DB Error"))
    response = client.post("/api/analyze")
    assert response.status_code == 500
    assert response.json()["detail"] == "DB Error"

def test_get_findings(client, db):
    db.add(Rule(id=1, name="R1", provider="AWS", resource_type="EBS", expression="True", severity="High"))
    db.add(Resource(id="r1", provider="AWS", resource_id="v1", resource_type="EBS"))
    db.add(Finding(id=1, resource_id="r1", rule_id=1, status="Open", remediation_command="cmd", potential_savings=10.0))
    # Finding with missing resource to test fallback
    db.add(Rule(id=2, name="R2", provider="AWS", resource_type="EC2", expression="True", severity="Low"))
    db.add(Finding(id=2, resource_id="r2_missing", rule_id=2, status="Closed", remediation_command="cmd2", potential_savings=0.0))
    db.commit()

    response = client.get("/api/findings")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    
    # Test filters
    resp2 = client.get("/api/findings?status=Open&severity=High")
    assert len(resp2.json()) == 1
    assert resp2.json()[0]["provider"] == "AWS"
    
    resp3 = client.get("/api/findings?severity=Low")
    assert len(resp3.json()) == 1
    assert resp3.json()[0]["provider"] == "Unknown"

def test_get_remediations(client, db):
    db.add(Resource(id="r1", provider="AWS", resource_id="v1", resource_type="EBS"))
    db.add(Finding(id=1, resource_id="r1", rule_id=1, status="Open", remediation_command="cmd", potential_savings=10.0))
    db.add(Finding(id=2, resource_id="r2_missing", rule_id=2, status="Open", remediation_command="cmd2", potential_savings=0.0))
    db.add(Finding(id=3, resource_id="r1", rule_id=1, status="Closed", remediation_command="cmd", potential_savings=10.0))
    db.commit()

    response = client.get("/api/remediation")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2 # Only Open findings
    
    assert data[0]["provider"] == "AWS"
    assert data[0]["resource_id"] == "v1"
    
    assert data[1]["provider"] == "Unknown"
    assert data[1]["resource_id"] == "Unknown"

def test_crud_rules(client, db):
    # Create
    rule_data = {
        "name": "Test Rule",
        "provider": "AWS",
        "resource_type": "EC2",
        "expression": "cost > 100",
        "severity": "High",
        "remediation_template": "echo fix",
        "enabled": True
    }
    resp = client.post("/api/rules", json=rule_data)
    assert resp.status_code == 200
    rule_id = resp.json()["id"]

    # Get
    resp2 = client.get("/api/rules")
    assert len(resp2.json()) == 1
    assert resp2.json()[0]["name"] == "Test Rule"

    # Update
    resp3 = client.put(f"/api/rules/{rule_id}", json={"name": "Updated Rule"})
    assert resp3.status_code == 200
    assert resp3.json()["name"] == "Updated Rule"

    # Update not found
    resp4 = client.put("/api/rules/999", json={"name": "Updated Rule"})
    assert resp4.status_code == 404

    # Delete
    resp5 = client.delete(f"/api/rules/{rule_id}")
    assert resp5.status_code == 200

    # Delete not found
    resp6 = client.delete("/api/rules/999")
    assert resp6.status_code == 404

def test_unauthorized_access():
    from fastapi.testclient import TestClient
    from app.main import app
    client = TestClient(app)
    response = client.get("/api/findings")
    assert response.status_code == 403
    assert response.json() == {"detail": "Could not validate API KEY"}
