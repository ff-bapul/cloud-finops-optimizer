from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.database.database import get_db
from app.models.models import Rule, Finding, Resource
from app.schemas.schemas import RuleCreate, RuleUpdate, RuleResponse, FindingResponse, RemediationResponse
from app.services.ingestion import ingest_billing_data
from app.services.rule_engine import evaluate_rules

router = APIRouter()

@router.post("/upload")
async def upload_billing(
    file: UploadFile = File(...), 
    provider: str = Form(...), 
    db: Session = Depends(get_db)
):
    try:
        content = await file.read()
        resources_added = ingest_billing_data(db, content, file.filename, provider)
        return {"message": f"Successfully ingested {resources_added} resources for {provider}."}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/analyze")
def trigger_analysis(db: Session = Depends(get_db)):
    try:
        findings_created = evaluate_rules(db)
        return {"message": f"Analysis complete. Generated {findings_created} new findings."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/findings", response_model=List[FindingResponse])
def get_findings(severity: str = None, status: str = None, db: Session = Depends(get_db)):
    query = db.query(Finding).join(Rule)
    if status:
        query = query.filter(Finding.status == status)
    if severity:
        query = query.filter(Rule.severity == severity)
        
    results = []
    for f in query.all():
        resource = db.query(Resource).filter(Resource.id == f.resource_id).first()
        results.append(FindingResponse(
            id=f.id,
            resource_id=resource.resource_id if resource else f.resource_id, 
            rule_id=f.rule_id,
            status=f.status,
            remediation_command=f.remediation_command,
            potential_savings=f.potential_savings,
            created_at=f.created_at,
            provider=resource.provider if resource else "Unknown"
        ))
    return results

@router.get("/remediation", response_model=List[RemediationResponse])
def get_remediations(db: Session = Depends(get_db)):
    findings = db.query(Finding).filter(Finding.status == "Open").all()
    results = []
    for f in findings:
        # Load associated resource to get the cloud provider resource ID
        resource = db.query(Resource).filter(Resource.id == f.resource_id).first()
        results.append(RemediationResponse(
            finding_id=f.id,
            resource_id=resource.resource_id if resource else "Unknown",
            command=f.remediation_command,
            status=f.status,
            provider=resource.provider if resource else "Unknown"
        ))
    return results

@router.get("/rules", response_model=List[RuleResponse])
def get_rules(db: Session = Depends(get_db)):
    return db.query(Rule).all()

@router.post("/rules", response_model=RuleResponse)
def create_rule(rule: RuleCreate, db: Session = Depends(get_db)):
    db_rule = Rule(**rule.model_dump())
    db.add(db_rule)
    db.commit()
    db.refresh(db_rule)
    return db_rule

@router.put("/rules/{rule_id}", response_model=RuleResponse)
def update_rule(rule_id: int, rule_update: RuleUpdate, db: Session = Depends(get_db)):
    db_rule = db.query(Rule).filter(Rule.id == rule_id).first()
    if not db_rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    
    update_data = rule_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_rule, key, value)
        
    db.commit()
    db.refresh(db_rule)
    return db_rule

@router.delete("/rules/{rule_id}")
def delete_rule(rule_id: int, db: Session = Depends(get_db)):
    db_rule = db.query(Rule).filter(Rule.id == rule_id).first()
    if not db_rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    db.delete(db_rule)
    db.commit()
    return {"message": "Rule deleted"}
