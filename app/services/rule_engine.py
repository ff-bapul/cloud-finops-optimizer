from sqlalchemy.orm import Session
from app.models.models import Resource, Rule, Finding
from simpleeval import simple_eval

def evaluate_rules(db: Session) -> int:
    """
    Evaluates active rules against resources dynamically and generates remediation findings.
    """
    rules = db.query(Rule).filter(Rule.enabled == True).all()
    resources = db.query(Resource).all()
    
    findings_created = 0

    for rule in rules:
        # Filter resources by provider and type
        candidate_resources = [
            r for r in resources 
            if r.provider == rule.provider and r.resource_type == rule.resource_type
        ]
        
        for resource in candidate_resources:
            # Prepare evaluation context
            context = {
                "id": resource.id,
                "provider": resource.provider,
                "resource_type": resource.resource_type,
                "resource_id": resource.resource_id,
                "state": resource.state,
                "cpu_utilization": resource.cpu_utilization,
                "cost": resource.cost,
                "region": resource.region
            }
            
            # Inject raw metadata into context without overwriting core fields
            if resource.raw_metadata:
                for k, v in resource.raw_metadata.items():
                    if k not in context:
                        context[k] = v

            try:
                # Safely evaluate string expression
                is_violation = simple_eval(rule.expression, names=context)
                
                if is_violation:
                    # Check if finding already exists
                    existing_finding = db.query(Finding).filter(
                        Finding.resource_id == resource.id,
                        Finding.rule_id == rule.id,
                        Finding.status == "Open"
                    ).first()
                    
                    if not existing_finding:
                        # Dynamically generate CLI command using format injection
                        try:
                            command = rule.remediation_template.format(**context)
                        except KeyError:
                            command = f"Error formatting template: {rule.remediation_template}"

                        finding = Finding(
                            resource_id=resource.id,
                            rule_id=rule.id,
                            remediation_command=command,
                            potential_savings=resource.cost if resource.cost else 0.0
                        )
                        db.add(finding)
                        findings_created += 1
            except Exception as e:
                print(f"Failed to evaluate rule '{rule.name}' for resource '{resource.resource_id}': {e}")

    db.commit()
    return findings_created
