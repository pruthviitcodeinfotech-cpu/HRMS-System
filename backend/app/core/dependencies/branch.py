"""Branch resolution dependency for multi-tenant data isolation.

Resolves branch_id from either query parameter `branch_id` or `x-branch-id` HTTP header,
and validates RBAC access rights against the current principal.
"""

from typing import Annotated
from fastapi import Header, Query, Depends

from app.core.dependencies.auth import CurrentUser, get_current_user
from app.core.exceptions.base import AuthorizationException

async def get_current_branch_id(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    branch_id: Annotated[int | None, Query(description="Filter by branch ID.")] = None,
    x_branch_id: Annotated[str | None, Header(alias="x-branch-id", description="Filter by branch ID header.")] = None,
) -> int | None:
    """Resolve current branch_id from Query or Header and enforce RBAC permission isolation."""
    if branch_id == 0 or branch_id == -1:
        return None

    resolved_id: int | None = branch_id

    if resolved_id is None and x_branch_id:
        try:
            parsed = int(x_branch_id)
            if parsed > 0:
                resolved_id = parsed
        except (ValueError, TypeError):
            pass

    if resolved_id is not None and not current_user.is_super_admin:
        branch_ids = current_user.permissions.branch_ids
        if branch_ids and resolved_id not in branch_ids:
            raise AuthorizationException("Access denied for requested branch.")

    return resolved_id


async def get_required_branch_id(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    branch_id: Annotated[int | None, Query(description="Filter by branch ID.")] = None,
    x_branch_id: Annotated[str | None, Header(alias="x-branch-id", description="Filter by branch ID header.")] = None,
) -> int:
    """Resolve mandatory active branch_id from Query, Header, or user permission scope."""
    res = await get_current_branch_id(current_user=current_user, branch_id=branch_id, x_branch_id=x_branch_id)
    if res is not None:
        return res

    if current_user.permissions.branch_ids:
        return next(iter(current_user.permissions.branch_ids))

    return 1


BranchIdDep = Annotated[int | None, Depends(get_current_branch_id)]
RequiredBranchIdDep = Annotated[int, Depends(get_required_branch_id)]
