from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class RuleBase(BaseModel):
    name: str
    provider: str
    resource_type: str
    expression: str
    severity: str
    remediation_template: str
    enabled: Optional[bool] = True

class RuleCreate(RuleBase):
    pass

class RuleUpdate(BaseModel):
    name: Optional[str] = None
    provider: Optional[str] = None
    resource_type: Optional[str] = None
    expression: Optional[str] = None
    severity: Optional[str] = None
    remediation_template: Optional[str] = None
    enabled: Optional[bool] = None

class RuleResponse(RuleBase):
    id: int
    class Config:
        from_attributes = True

class FindingResponse(BaseModel):
    id: int
    resource_id: str
    rule_id: int
    status: str
    remediation_command: str
    potential_savings: float
    created_at: datetime
    provider: str
    class Config:
        from_attributes = True

class RemediationResponse(BaseModel):
    finding_id: int
    resource_id: str
    command: str
    status: str
    provider: str
