from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, DateTime, JSON
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.database.database import Base

class Resource(Base):
    __tablename__ = "resources"

    id = Column(String, primary_key=True, index=True) # UUID or similar generated locally
    provider = Column(String, index=True) # AWS, Azure
    resource_type = Column(String, index=True) # EC2, EBS, Disk
    resource_id = Column(String, index=True) # Original cloud ID
    state = Column(String) # Running, Stopped, Available
    cpu_utilization = Column(Float, nullable=True)
    cost = Column(Float, nullable=True)
    region = Column(String, nullable=True)
    raw_metadata = Column(JSON, nullable=True)

    findings = relationship("Finding", back_populates="resource")

class Rule(Base):
    __tablename__ = "rules"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    provider = Column(String, index=True)
    resource_type = Column(String, index=True)
    expression = Column(String)
    severity = Column(String) # High, Medium, Low
    remediation_template = Column(String)
    enabled = Column(Boolean, default=True)

    findings = relationship("Finding", back_populates="rule")

class Finding(Base):
    __tablename__ = "findings"

    id = Column(Integer, primary_key=True, index=True)
    resource_id = Column(String, ForeignKey("resources.id"))
    rule_id = Column(Integer, ForeignKey("rules.id"))
    status = Column(String, default="Open") # Open, Remediated, Ignored
    remediation_command = Column(String)
    potential_savings = Column(Float, default=0.0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    resource = relationship("Resource", back_populates="findings")
    rule = relationship("Rule", back_populates="findings")
