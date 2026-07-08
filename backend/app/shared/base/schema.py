"""Base Pydantic (v2) schema conventions shared by all DTOs.

Response/DTO models inherit from :class:`BaseSchema`. ORM-backed responses use
``from_attributes`` so they can be built directly from SQLAlchemy instances via
``Model.model_validate(orm_obj)``. JSON keys are snake_case (matching the API
contracts).
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class BaseSchema(BaseModel):
    """Common base for all request/response schemas."""

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        str_strip_whitespace=True,
        extra="ignore",
    )


class TimestampSchema(BaseSchema):
    """Mixin schema exposing standard audit timestamps."""

    created_at: datetime
    updated_at: datetime
