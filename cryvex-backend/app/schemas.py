"""
Strict Pydantic Schemas for Zero-Trust Input Validation.
Prevents NoSQL injection by enforcing strict typing on all user-controlled inputs
before they reach MongoDB query methods.
"""

from pydantic import BaseModel, Field


class VisitorID(BaseModel):
    """
    Strict validator for visitor_id fields.
    Only allows alphanumeric characters, underscores, and hyphens.
    This blocks MongoDB operator injection (e.g., {"$ne": null}, {"$gt": ""}).
    """
    visitor_id: str = Field(
        ...,
        min_length=1,
        max_length=128,
        pattern=r"^[a-zA-Z0-9_-]+$"
    )
