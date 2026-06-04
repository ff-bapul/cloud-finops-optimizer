import pytest
from app.models.models import Resource, Rule, Finding
from app.services.rule_engine import evaluate_rules

def test_rule_evaluation_generates_finding(db):
    # Match: Creates finding
    db.add(Rule(id=1, name="R1", provider="AWS", resource_type="EBS", expression="state == 'available'", severity="High", remediation_template="cmd {resource_id}", enabled=True))
    db.add(Resource(id="r1", provider="AWS", resource_id="v1", resource_type="EBS", state="available", cost=20.0))
    db.commit()
    assert evaluate_rules(db) == 1

def test_rule_evaluation_disabled_rule(db):
    db.add(Rule(id=1, name="R1", provider="AWS", resource_type="EBS", expression="state == 'available'", enabled=False))
    db.add(Resource(id="r1", provider="AWS", resource_id="v1", resource_type="EBS", state="available"))
    db.commit()
    assert evaluate_rules(db) == 0

def test_rule_evaluation_no_violation(db):
    db.add(Rule(id=1, name="R1", provider="AWS", resource_type="EBS", expression="state == 'available'", enabled=True))
    db.add(Resource(id="r1", provider="AWS", resource_id="v1", resource_type="EBS", state="in-use"))
    db.commit()
    assert evaluate_rules(db) == 0

def test_rule_evaluation_duplicate_finding(db):
    db.add(Rule(id=1, name="R1", provider="AWS", resource_type="EBS", expression="state == 'available'", enabled=True, remediation_template="x"))
    db.add(Resource(id="r1", provider="AWS", resource_id="v1", resource_type="EBS", state="available"))
    db.add(Finding(resource_id="r1", rule_id=1, status="Open", remediation_command="x"))
    db.commit()
    # finding already exists
    assert evaluate_rules(db) == 0

def test_rule_evaluation_format_error(db):
    db.add(Rule(id=1, name="R1", provider="AWS", resource_type="EBS", expression="state == 'available'", enabled=True, remediation_template="cmd {unknown_key}"))
    db.add(Resource(id="r1", provider="AWS", resource_id="v1", resource_type="EBS", state="available"))
    db.commit()
    assert evaluate_rules(db) == 1
    finding = db.query(Finding).first()
    assert "Error formatting template" in finding.remediation_command

def test_rule_evaluation_simple_eval_exception(db):
    # Invalid python expression
    db.add(Rule(id=1, name="R1", provider="AWS", resource_type="EBS", expression="1 / 0", enabled=True, remediation_template="cmd"))
    db.add(Resource(id="r1", provider="AWS", resource_id="v1", resource_type="EBS", state="available"))
    db.commit()
    assert evaluate_rules(db) == 0

def test_rule_evaluation_raw_metadata_injection(db):
    db.add(Rule(id=1, name="R1", provider="AWS", resource_type="EBS", expression="my_custom_key == 'yes'", enabled=True, remediation_template="cmd {my_custom_key}"))
    db.add(Resource(id="r1", provider="AWS", resource_id="v1", resource_type="EBS", raw_metadata={"my_custom_key": "yes", "state": "override_me_not"}))
    db.commit()
    assert evaluate_rules(db) == 1
    finding = db.query(Finding).first()
    assert finding.remediation_command == "cmd yes"

def test_rule_evaluation_missing_cost(db):
    db.add(Rule(id=1, name="R1", provider="AWS", resource_type="EBS", expression="True", enabled=True, remediation_template="cmd"))
    db.add(Resource(id="r1", provider="AWS", resource_id="v1", resource_type="EBS", cost=None))
    db.commit()
    assert evaluate_rules(db) == 1
    finding = db.query(Finding).first()
    assert finding.potential_savings == 0.0
