"""Reusable FastAPI dependencies (DB session, auth/authz, pagination)."""

from app.core.dependencies.auth import (
    CurrentUser,
    get_current_active_user,
    get_current_user,
    require_permission,
    require_role,
)
from app.core.dependencies.db import get_db
from app.core.dependencies.pagination import (
    PaginationParams,
    SortParams,
    pagination_params,
    sort_params,
)

__all__ = [
    "get_db",
    "CurrentUser",
    "get_current_user",
    "get_current_active_user",
    "require_permission",
    "require_role",
    "PaginationParams",
    "SortParams",
    "pagination_params",
    "sort_params",
]
