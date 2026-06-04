import pandas as pd
from sqlalchemy.orm import Session
import uuid
import io

from app.models.models import Resource

def ingest_billing_data(db: Session, file_content: bytes, filename: str, provider: str) -> int:
    """
    Parses CSV or JSON billing files using Pandas and normalizes them into Resource entities.
    """
    if filename.endswith(".csv"):
        df = pd.read_csv(io.BytesIO(file_content))
    elif filename.endswith(".json"):
        df = pd.read_json(io.BytesIO(file_content))
    else:
        raise ValueError("Unsupported file format. Use CSV or JSON.")
    
    resources_added_or_updated = 0
    
    for _, row in df.iterrows():
        row_dict = row.to_dict()
        
        # Mapping standard fields (falling back to generated or default values if missing)
        resource_id_val = str(row_dict.get('resource_id', uuid.uuid4()))
        resource_type_val = str(row_dict.get('resource_type', 'Unknown'))
        state_val = str(row_dict.get('state', 'Unknown'))
        
        cpu_val = row_dict.get('cpu_utilization')
        cost_val = row_dict.get('cost')
        region_val = str(row_dict.get('region', 'Unknown'))
        
        # Check if resource already exists
        resource = db.query(Resource).filter(
            Resource.resource_id == resource_id_val, 
            Resource.provider == provider
        ).first()

        if not resource:
            resource = Resource(
                id=str(uuid.uuid4()),
                provider=provider,
                resource_id=resource_id_val,
                resource_type=resource_type_val,
                state=state_val,
                cpu_utilization=float(cpu_val) if pd.notnull(cpu_val) else None,
                cost=float(cost_val) if pd.notnull(cost_val) else None,
                region=region_val,
                raw_metadata=row_dict
            )
            db.add(resource)
        else:
            resource.state = state_val
            resource.cpu_utilization = float(cpu_val) if pd.notnull(cpu_val) else None
            resource.cost = float(cost_val) if pd.notnull(cost_val) else None
            resource.raw_metadata = row_dict
            
        resources_added_or_updated += 1

    db.commit()
    return resources_added_or_updated
