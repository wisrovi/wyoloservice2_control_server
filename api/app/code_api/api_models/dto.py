from pydantic import BaseModel
from typing import Dict, Any, Optional




# Pydantic models for request bodies
class MetricRequest(BaseModel):
    query: Optional[str] = None
    status: Optional[str] = None
    limit: Optional[int] = None
    instance: Optional[str] = None
    bucket: Optional[str] = None
    job_ids: Optional[str] = None

class TrainingJobRequest(BaseModel):
    user_id: str
    project_id: str
    config: Dict[str, Any]
    yaml_content: Optional[str] = None

class DataUploadRequest(BaseModel):
    filename: str
    size: int
    type: str
    user_id: Optional[str] = None