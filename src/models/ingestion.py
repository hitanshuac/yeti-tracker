"""
Data models for the Yeti-Tracker ingestion pipeline.
"""

from pydantic import BaseModel, Field


class ExtractedEvent(BaseModel):
    """Strict schema for the LLM to map unstructured SRE logs into structured Cloud FinOps data."""

    region: str = Field(..., description="Cloud region, e.g., us-east-1")
    instance_type: str = Field(..., description="Compute tier, e.g., p4d.24xlarge")
    idle_hours: int = Field(..., ge=0, description="Number of hours the instance was left idle")


class IngestionRequest(BaseModel):
    """Payload for the FastAPI POST /api/ingest/text endpoint."""

    text: str = Field(..., description="Unstructured operational text or log data.")
