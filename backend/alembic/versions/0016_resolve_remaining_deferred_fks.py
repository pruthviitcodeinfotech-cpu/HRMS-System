"""resolve remaining deferred user/rbac foreign keys

Adds the four previously-deferred cross-module FOREIGN KEY constraints from the
User Management & RBAC module (0007). They were deferred while the project-wide
primary-key convention was undecided; migration 0009 standardized every key
column on BIGINT, so the source and destination columns are now type-compatible
and these constraints can be enforced.

This migration ONLY adds constraints. It does not create/alter/drop tables,
columns, indexes, or any other constraint.

Resolved FKs (source.column -> destination.pk, ON DELETE per approved architecture):
    * users.org_id                     -> organizations.org_id  (NO ACTION,
      matching every other org_id FK in the project)
    * users.employee_id                -> employees.employee_id (SET NULL;
      column is nullable)
    * user_branch_access.branch_id     -> branches.branch_id    (RESTRICT)
    * user_department_access.department_id -> departments.dept_id (RESTRICT;
      the destination primary key is `dept_id`, not `department_id`)

No source table references users/user_branch_access/user_department_access, so
no circular FK dependency is introduced. All four constraint names are new (no
existing constraint is recreated).

Revision ID: 0016_resolve_remaining_deferred_fks
Revises: 0015_attendance_core
Create Date: 2026-07-08
"""

from collections.abc import Sequence
from typing import Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0016_resolve_remaining_deferred_fks"
down_revision: Union[str, None] = "0015_attendance_core"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_foreign_key(
        "fk_users_org_id_organizations",
        "users",
        "organizations",
        ["org_id"],
        ["org_id"],
    )
    op.create_foreign_key(
        "fk_users_employee_id_employees",
        "users",
        "employees",
        ["employee_id"],
        ["employee_id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_user_branch_access_branch_id_branches",
        "user_branch_access",
        "branches",
        ["branch_id"],
        ["branch_id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_user_department_access_department_id_departments",
        "user_department_access",
        "departments",
        ["department_id"],
        ["dept_id"],
        ondelete="RESTRICT",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_user_department_access_department_id_departments",
        "user_department_access",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_user_branch_access_branch_id_branches",
        "user_branch_access",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_users_employee_id_employees",
        "users",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_users_org_id_organizations",
        "users",
        type_="foreignkey",
    )
