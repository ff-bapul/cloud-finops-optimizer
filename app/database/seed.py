from sqlalchemy.orm import Session
from app.models.models import Rule

def seed_rules(db: Session):
    existing_rules = db.query(Rule).count()
    if existing_rules > 0:
        return # Database already seeded

    default_rules = [
        Rule(
            name="Unattached EBS Volume",
            provider="AWS",
            resource_type="EBS",
            expression="state == 'available'",
            severity="High",
            remediation_template="aws ec2 delete-volume --volume-id {resource_id}"
        ),
        Rule(
            name="Underutilized EC2",
            provider="AWS",
            resource_type="EC2",
            expression="cpu_utilization < 5 and state == 'running'",
            severity="Medium",
            remediation_template="aws ec2 terminate-instances --instance-ids {resource_id}"
        ),
        Rule(
            name="Detached Azure Managed Disk",
            provider="Azure",
            resource_type="ManagedDisk",
            expression="state == 'Unattached'",
            severity="High",
            remediation_template="az disk delete --name {resource_id} --yes"
        ),
        Rule(
            name="Idle Azure Virtual Machine",
            provider="Azure",
            resource_type="VirtualMachine",
            expression="cpu_utilization < 5 and state == 'Running'",
            severity="Medium",
            remediation_template="az vm deallocate --name {resource_id}"
        )
    ]
    
    db.bulk_save_objects(default_rules)
    db.commit()
