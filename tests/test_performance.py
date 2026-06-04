import pytest
import time
from app.models.models import Resource, Rule
from app.services.rule_engine import evaluate_rules
import uuid

def test_performance_rule_engine(db):
    # Setup 1000 resources and 10 rules
    for i in range(10):
        db.add(Rule(
            name=f"Rule {i}", 
            provider="AWS", 
            resource_type="EBS", 
            expression="cost > 50", 
            severity="High",
            remediation_template="cmd {resource_id}",
            enabled=True
        ))
        
    for i in range(1000):
        db.add(Resource(
            id=str(uuid.uuid4()), 
            provider="AWS", 
            resource_id=f"vol-{i}", 
            resource_type="EBS", 
            state="available", 
            cost=60.0 # Will trigger all rules
        ))
    db.commit()

    start_time = time.time()
    findings_created = evaluate_rules(db)
    end_time = time.time()
    
    assert findings_created == 10000 # 1000 resources * 10 rules
    # Engine should process 10k evaluations reasonably quickly
    assert (end_time - start_time) < 10.0
