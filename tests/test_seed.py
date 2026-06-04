import pytest
from app.database.seed import seed_rules
from app.models.models import Rule

def test_seed_rules(db):
    # Should create rules
    seed_rules(db)
    rules = db.query(Rule).all()
    assert len(rules) == 4
    
    # Second time should do nothing
    seed_rules(db)
    rules2 = db.query(Rule).all()
    assert len(rules2) == 4
