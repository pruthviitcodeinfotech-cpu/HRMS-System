"""Branch-specific data isolation: add branch_id to 19 master and operational tables

Revision ID: 0023_branch_isolation
Revises: 0022_salary_slip_toggles
Create Date: 2026-07-27
"""

from collections.abc import Sequence
from typing import Union

from alembic import op
import sqlalchemy as sa


# -----------------------------------------------------------------------
revision: str = "0023_branch_isolation"
down_revision: Union[str, None] = "0022_salary_slip_toggles"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None
# -----------------------------------------------------------------------


def upgrade() -> None:
    # Ensure default branches exist for any org that has records
    op.execute("""
        INSERT INTO branches (org_id, branch_name, is_active, is_deleted, created_at, updated_at)
        SELECT DISTINCT o.org_id, 'Head Office', true, false, NOW(), NOW()
        FROM organizations o
        WHERE NOT EXISTS (
            SELECT 1 FROM branches b WHERE b.org_id = o.org_id AND b.is_deleted = false
        );
    """)

    # -------------------------------------------------------------------
    # 1. departments
    # -------------------------------------------------------------------
    op.add_column("departments", sa.Column("branch_id", sa.BigInteger(), nullable=True))
    op.execute("""
        UPDATE departments d
        SET branch_id = (
            SELECT e.master_branch_id
            FROM employees e
            WHERE e.dept_id = d.dept_id AND e.is_deleted = false
            GROUP BY e.master_branch_id
            ORDER BY COUNT(*) DESC
            LIMIT 1
        )
        WHERE d.branch_id IS NULL;

        UPDATE departments d
        SET branch_id = (
            SELECT b.branch_id FROM branches b WHERE b.org_id = d.org_id ORDER BY b.branch_id ASC LIMIT 1
        )
        WHERE d.branch_id IS NULL;
    """)
    op.alter_column("departments", "branch_id", nullable=False)
    op.create_foreign_key(
        "fk_departments_branch_id_branches",
        "departments",
        "branches",
        ["branch_id"],
        ["branch_id"],
        ondelete="RESTRICT",
        onupdate="CASCADE",
    )
    op.drop_index("uq_departments_org_id_dept_name", table_name="departments", if_exists=True)
    op.create_index(
        "uq_departments_branch_id_dept_name",
        "departments",
        ["branch_id", "dept_name"],
        unique=True,
        postgresql_where=sa.text("is_deleted = false"),
    )
    op.create_index("ix_departments_branch_id", "departments", ["branch_id"])

    # -------------------------------------------------------------------
    # 2. designations
    # -------------------------------------------------------------------
    op.add_column("designations", sa.Column("branch_id", sa.BigInteger(), nullable=True))
    op.execute("""
        UPDATE designations dg
        SET branch_id = (
            SELECT e.master_branch_id
            FROM employees e
            WHERE e.designation_id = dg.designation_id AND e.is_deleted = false
            GROUP BY e.master_branch_id
            ORDER BY COUNT(*) DESC
            LIMIT 1
        )
        WHERE dg.branch_id IS NULL;

        UPDATE designations dg
        SET branch_id = (
            SELECT b.branch_id FROM branches b WHERE b.org_id = dg.org_id ORDER BY b.branch_id ASC LIMIT 1
        )
        WHERE dg.branch_id IS NULL;
    """)
    op.alter_column("designations", "branch_id", nullable=False)
    op.create_foreign_key(
        "fk_designations_branch_id_branches",
        "designations",
        "branches",
        ["branch_id"],
        ["branch_id"],
        ondelete="RESTRICT",
        onupdate="CASCADE",
    )
    op.drop_index("uq_designations_org_id_designation_name", table_name="designations", if_exists=True)
    op.create_index(
        "uq_designations_branch_id_designation_name",
        "designations",
        ["branch_id", "designation_name"],
        unique=True,
        postgresql_where=sa.text("is_deleted = false"),
    )
    op.create_index("ix_designations_branch_id", "designations", ["branch_id"])

    # -------------------------------------------------------------------
    # 3. shifts
    # -------------------------------------------------------------------
    op.add_column("shifts", sa.Column("branch_id", sa.BigInteger(), nullable=True))
    op.execute("""
        UPDATE shifts s
        SET branch_id = (
            SELECT e.master_branch_id
            FROM shift_assignments sa
            JOIN employees e ON e.employee_id = sa.employee_id
            WHERE sa.shift_id = s.shift_id
            GROUP BY e.master_branch_id
            ORDER BY COUNT(*) DESC
            LIMIT 1
        )
        WHERE s.branch_id IS NULL;

        UPDATE shifts s
        SET branch_id = (
            SELECT b.branch_id FROM branches b WHERE b.org_id = s.org_id ORDER BY b.branch_id ASC LIMIT 1
        )
        WHERE s.branch_id IS NULL;
    """)
    op.alter_column("shifts", "branch_id", nullable=False)
    op.create_foreign_key(
        "fk_shifts_branch_id_branches",
        "shifts",
        "branches",
        ["branch_id"],
        ["branch_id"],
        ondelete="RESTRICT",
        onupdate="CASCADE",
    )
    op.drop_index("uq_shifts_org_id_shift_name", table_name="shifts", if_exists=True)
    op.create_index(
        "uq_shifts_branch_id_shift_name",
        "shifts",
        ["branch_id", "shift_name"],
        unique=True,
        postgresql_where=sa.text("is_deleted = false"),
    )
    op.create_index("ix_shifts_branch_id", "shifts", ["branch_id"])

    # -------------------------------------------------------------------
    # 4. shift_assignments
    # -------------------------------------------------------------------
    op.add_column("shift_assignments", sa.Column("branch_id", sa.BigInteger(), nullable=True))
    op.execute("""
        UPDATE shift_assignments sa
        SET branch_id = e.master_branch_id
        FROM employees e
        WHERE sa.employee_id = e.employee_id AND sa.branch_id IS NULL;

        UPDATE shift_assignments sa
        SET branch_id = (
            SELECT b.branch_id FROM branches b WHERE b.org_id = sa.org_id ORDER BY b.branch_id ASC LIMIT 1
        )
        WHERE sa.branch_id IS NULL;
    """)
    op.alter_column("shift_assignments", "branch_id", nullable=False)
    op.create_foreign_key(
        "fk_shift_assignments_branch_id_branches",
        "shift_assignments",
        "branches",
        ["branch_id"],
        ["branch_id"],
        ondelete="RESTRICT",
        onupdate="CASCADE",
    )
    op.create_index("ix_shift_assignments_branch_id_employee_id", "shift_assignments", ["branch_id", "employee_id"])

    # -------------------------------------------------------------------
    # 5. roster
    # -------------------------------------------------------------------
    op.add_column("roster", sa.Column("branch_id", sa.BigInteger(), nullable=True))
    op.execute("""
        UPDATE roster r
        SET branch_id = e.master_branch_id
        FROM employees e
        WHERE r.employee_id = e.employee_id AND r.branch_id IS NULL;

        UPDATE roster r
        SET branch_id = (
            SELECT b.branch_id FROM branches b WHERE b.org_id = r.org_id ORDER BY b.branch_id ASC LIMIT 1
        )
        WHERE r.branch_id IS NULL;
    """)
    op.alter_column("roster", "branch_id", nullable=False)
    op.create_foreign_key(
        "fk_roster_branch_id_branches",
        "roster",
        "branches",
        ["branch_id"],
        ["branch_id"],
        ondelete="RESTRICT",
        onupdate="CASCADE",
    )
    op.create_index("ix_roster_branch_id_roster_date", "roster", ["branch_id", "roster_date"])

    # -------------------------------------------------------------------
    # 6. payroll_groups
    # -------------------------------------------------------------------
    op.add_column("payroll_groups", sa.Column("branch_id", sa.BigInteger(), nullable=True))
    op.execute("""
        UPDATE payroll_groups pg
        SET branch_id = (
            SELECT e.master_branch_id
            FROM employee_payroll_group_assignments epga
            JOIN employees e ON e.employee_id = epga.employee_id
            WHERE epga.payroll_group_id = pg.id
            GROUP BY e.master_branch_id
            ORDER BY COUNT(*) DESC
            LIMIT 1
        )
        WHERE pg.branch_id IS NULL;

        UPDATE payroll_groups pg
        SET branch_id = (
            SELECT b.branch_id FROM branches b WHERE b.org_id = pg.org_id ORDER BY b.branch_id ASC LIMIT 1
        )
        WHERE pg.branch_id IS NULL;
    """)
    op.alter_column("payroll_groups", "branch_id", nullable=False)
    op.create_foreign_key(
        "fk_payroll_groups_branch_id_branches",
        "payroll_groups",
        "branches",
        ["branch_id"],
        ["branch_id"],
        ondelete="RESTRICT",
        onupdate="CASCADE",
    )
    op.drop_index("uq_payroll_groups_org_id_name", table_name="payroll_groups", if_exists=True)
    op.create_index(
        "uq_payroll_groups_branch_id_name",
        "payroll_groups",
        ["branch_id", "name"],
        unique=True,
        postgresql_where=sa.text("is_deleted = false"),
    )
    op.create_index("ix_payroll_groups_branch_id", "payroll_groups", ["branch_id"])

    # -------------------------------------------------------------------
    # 7. payroll_computed_rows
    # -------------------------------------------------------------------
    op.add_column("payroll_computed_rows", sa.Column("branch_id", sa.BigInteger(), nullable=True))
    op.execute("""
        UPDATE payroll_computed_rows pcr
        SET branch_id = e.master_branch_id
        FROM employees e
        WHERE pcr.employee_id = e.employee_id AND pcr.branch_id IS NULL;

        UPDATE payroll_computed_rows pcr
        SET branch_id = pg.branch_id
        FROM payroll_groups pg
        WHERE pcr.payroll_group_id = pg.id AND pcr.branch_id IS NULL;
    """)
    op.alter_column("payroll_computed_rows", "branch_id", nullable=False)
    op.create_foreign_key(
        "fk_payroll_computed_rows_branch_id_branches",
        "payroll_computed_rows",
        "branches",
        ["branch_id"],
        ["branch_id"],
        ondelete="RESTRICT",
        onupdate="CASCADE",
    )
    op.create_index("ix_payroll_computed_rows_branch_id_cycle_from", "payroll_computed_rows", ["branch_id", "cycle_from"])

    # -------------------------------------------------------------------
    # 8. finalized_payroll_runs
    # -------------------------------------------------------------------
    op.add_column("finalized_payroll_runs", sa.Column("branch_id", sa.BigInteger(), nullable=True))
    op.execute("""
        UPDATE finalized_payroll_runs fpr
        SET branch_id = pg.branch_id
        FROM payroll_groups pg
        WHERE fpr.payroll_group_id = pg.id AND fpr.branch_id IS NULL;

        UPDATE finalized_payroll_runs fpr
        SET branch_id = (
            SELECT b.branch_id FROM branches b WHERE b.org_id = fpr.org_id ORDER BY b.branch_id ASC LIMIT 1
        )
        WHERE fpr.branch_id IS NULL;
    """)
    op.alter_column("finalized_payroll_runs", "branch_id", nullable=False)
    op.create_foreign_key(
        "fk_finalized_payroll_runs_branch_id_branches",
        "finalized_payroll_runs",
        "branches",
        ["branch_id"],
        ["branch_id"],
        ondelete="RESTRICT",
        onupdate="CASCADE",
    )
    op.create_index("ix_finalized_payroll_runs_branch_id_cycle_from", "finalized_payroll_runs", ["branch_id", "cycle_from"])

    # -------------------------------------------------------------------
    # 9. leave_types
    # -------------------------------------------------------------------
    op.add_column("leave_types", sa.Column("branch_id", sa.BigInteger(), nullable=True))
    op.execute("""
        UPDATE leave_types lt
        SET branch_id = (
            SELECT e.master_branch_id
            FROM leave_requests lr
            JOIN employees e ON e.employee_id = lr.employee_id
            WHERE lr.leave_type_id = lt.id
            GROUP BY e.master_branch_id
            ORDER BY COUNT(*) DESC
            LIMIT 1
        )
        WHERE lt.branch_id IS NULL;

        UPDATE leave_types lt
        SET branch_id = (
            SELECT b.branch_id FROM branches b WHERE b.org_id = lt.org_id ORDER BY b.branch_id ASC LIMIT 1
        )
        WHERE lt.branch_id IS NULL;
    """)
    op.alter_column("leave_types", "branch_id", nullable=False)
    op.create_foreign_key(
        "fk_leave_types_branch_id_branches",
        "leave_types",
        "branches",
        ["branch_id"],
        ["branch_id"],
        ondelete="RESTRICT",
        onupdate="CASCADE",
    )
    op.drop_constraint("uq_leave_types_org_id_alias", table_name="leave_types", type_="unique")
    op.create_unique_constraint("uq_leave_types_branch_id_alias", "leave_types", ["branch_id", "alias"])
    op.create_index("ix_leave_types_branch_id", "leave_types", ["branch_id"])

    # -------------------------------------------------------------------
    # 10. leave_requests
    # -------------------------------------------------------------------
    op.add_column("leave_requests", sa.Column("branch_id", sa.BigInteger(), nullable=True))
    op.execute("""
        UPDATE leave_requests lr
        SET branch_id = e.master_branch_id
        FROM employees e
        WHERE lr.employee_id = e.employee_id AND lr.branch_id IS NULL;
    """)
    op.alter_column("leave_requests", "branch_id", nullable=False)
    op.create_foreign_key(
        "fk_leave_requests_branch_id_branches",
        "leave_requests",
        "branches",
        ["branch_id"],
        ["branch_id"],
        ondelete="RESTRICT",
        onupdate="CASCADE",
    )
    op.create_index("ix_leave_requests_branch_id_status", "leave_requests", ["branch_id", "status"])

    # -------------------------------------------------------------------
    # 11. employee_leave_balances
    # -------------------------------------------------------------------
    op.add_column("employee_leave_balances", sa.Column("branch_id", sa.BigInteger(), nullable=True))
    op.execute("""
        UPDATE employee_leave_balances elb
        SET branch_id = e.master_branch_id
        FROM employees e
        WHERE elb.employee_id = e.employee_id AND elb.branch_id IS NULL;
    """)
    op.alter_column("employee_leave_balances", "branch_id", nullable=False)
    op.create_foreign_key(
        "fk_employee_leave_balances_branch_id_branches",
        "employee_leave_balances",
        "branches",
        ["branch_id"],
        ["branch_id"],
        ondelete="RESTRICT",
        onupdate="CASCADE",
    )
    op.create_index("ix_employee_leave_balances_branch_id_employee_id", "employee_leave_balances", ["branch_id", "employee_id"])

    # -------------------------------------------------------------------
    # 12. holiday_templates
    # -------------------------------------------------------------------
    op.add_column("holiday_templates", sa.Column("branch_id", sa.BigInteger(), nullable=True))
    op.execute("""
        UPDATE holiday_templates ht
        SET branch_id = (
            SELECT e.master_branch_id
            FROM employee_holiday_assignments eha
            JOIN employees e ON e.employee_id = eha.employee_id
            WHERE eha.template_id = ht.id
            GROUP BY e.master_branch_id
            ORDER BY COUNT(*) DESC
            LIMIT 1
        )
        WHERE ht.branch_id IS NULL;

        UPDATE holiday_templates ht
        SET branch_id = (
            SELECT b.branch_id FROM branches b WHERE b.org_id = ht.org_id ORDER BY b.branch_id ASC LIMIT 1
        )
        WHERE ht.branch_id IS NULL;
    """)
    op.alter_column("holiday_templates", "branch_id", nullable=False)
    op.create_foreign_key(
        "fk_holiday_templates_branch_id_branches",
        "holiday_templates",
        "branches",
        ["branch_id"],
        ["branch_id"],
        ondelete="RESTRICT",
        onupdate="CASCADE",
    )
    op.drop_index("uq_holiday_templates_org_id_name_ci", table_name="holiday_templates", if_exists=True)
    op.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS uq_holiday_templates_branch_id_name_ci
        ON holiday_templates (branch_id, lower(name))
        WHERE is_deleted = false
    """)
    op.create_index("ix_holiday_templates_branch_id", "holiday_templates", ["branch_id"])

    # -------------------------------------------------------------------
    # 13. employee_holiday_assignments
    # -------------------------------------------------------------------
    op.add_column("employee_holiday_assignments", sa.Column("branch_id", sa.BigInteger(), nullable=True))
    op.execute("""
        UPDATE employee_holiday_assignments eha
        SET branch_id = e.master_branch_id
        FROM employees e
        WHERE eha.employee_id = e.employee_id AND eha.branch_id IS NULL;
    """)
    op.alter_column("employee_holiday_assignments", "branch_id", nullable=False)
    op.create_foreign_key(
        "fk_employee_holiday_assignments_branch_id_branches",
        "employee_holiday_assignments",
        "branches",
        ["branch_id"],
        ["branch_id"],
        ondelete="RESTRICT",
        onupdate="CASCADE",
    )
    op.create_index("ix_employee_holiday_assignments_branch_id", "employee_holiday_assignments", ["branch_id"])

    # -------------------------------------------------------------------
    # 14. approval_requests
    # -------------------------------------------------------------------
    op.add_column("approval_requests", sa.Column("branch_id", sa.BigInteger(), nullable=True))
    op.execute("""
        UPDATE approval_requests ar
        SET branch_id = e.master_branch_id
        FROM employees e
        WHERE ar.employee_id = e.employee_id AND ar.branch_id IS NULL;

        UPDATE approval_requests ar
        SET branch_id = (
            SELECT b.branch_id FROM branches b WHERE b.org_id = ar.org_id ORDER BY b.branch_id ASC LIMIT 1
        )
        WHERE ar.branch_id IS NULL;
    """)
    op.alter_column("approval_requests", "branch_id", nullable=False)
    op.create_foreign_key(
        "fk_approval_requests_branch_id_branches",
        "approval_requests",
        "branches",
        ["branch_id"],
        ["branch_id"],
        ondelete="RESTRICT",
        onupdate="CASCADE",
    )
    op.create_index("ix_approval_requests_branch_id_status", "approval_requests", ["branch_id", "status"])

    # -------------------------------------------------------------------
    # 15. attendance_regularization_requests
    # -------------------------------------------------------------------
    op.add_column("attendance_regularization_requests", sa.Column("branch_id", sa.BigInteger(), nullable=True))
    op.execute("""
        UPDATE attendance_regularization_requests arr
        SET branch_id = e.master_branch_id
        FROM employees e
        WHERE arr.employee_id = e.employee_id AND arr.branch_id IS NULL;
    """)
    op.alter_column("attendance_regularization_requests", "branch_id", nullable=False)
    op.create_foreign_key(
        "fk_attendance_regularization_requests_branch_id_branches",
        "attendance_regularization_requests",
        "branches",
        ["branch_id"],
        ["branch_id"],
        ondelete="RESTRICT",
        onupdate="CASCADE",
    )
    op.create_index("ix_att_regularization_reqs_branch_id_status", "attendance_regularization_requests", ["branch_id", "status"])

    # -------------------------------------------------------------------
    # 16. login_reset_requests
    # -------------------------------------------------------------------
    op.add_column("login_reset_requests", sa.Column("branch_id", sa.BigInteger(), nullable=True))
    op.execute("""
        UPDATE login_reset_requests lrr
        SET branch_id = e.master_branch_id
        FROM employees e
        WHERE lrr.employee_id = e.employee_id AND lrr.branch_id IS NULL;
    """)
    op.alter_column("login_reset_requests", "branch_id", nullable=False)
    op.create_foreign_key(
        "fk_login_reset_requests_branch_id_branches",
        "login_reset_requests",
        "branches",
        ["branch_id"],
        ["branch_id"],
        ondelete="RESTRICT",
        onupdate="CASCADE",
    )
    op.create_index("ix_login_reset_requests_branch_id_status", "login_reset_requests", ["branch_id", "status"])

    # -------------------------------------------------------------------
    # 17. notifications
    # -------------------------------------------------------------------
    op.add_column("notifications", sa.Column("branch_id", sa.BigInteger(), nullable=True))
    op.execute("""
        UPDATE notifications n
        SET branch_id = (
            SELECT b.branch_id FROM branches b WHERE b.org_id = n.org_id ORDER BY b.branch_id ASC LIMIT 1
        )
        WHERE n.branch_id IS NULL;
    """)
    op.alter_column("notifications", "branch_id", nullable=False)
    op.create_foreign_key(
        "fk_notifications_branch_id_branches",
        "notifications",
        "branches",
        ["branch_id"],
        ["branch_id"],
        ondelete="RESTRICT",
        onupdate="CASCADE",
    )
    op.create_index("ix_notifications_branch_id_created_at", "notifications", ["branch_id", "created_at"])

    # -------------------------------------------------------------------
    # 18. notification_recipients
    # -------------------------------------------------------------------
    op.add_column("notification_recipients", sa.Column("branch_id", sa.BigInteger(), nullable=True))
    op.execute("""
        UPDATE notification_recipients nr
        SET branch_id = n.branch_id
        FROM notifications n
        WHERE nr.notification_id = n.id AND nr.branch_id IS NULL;

        UPDATE notification_recipients nr
        SET branch_id = (
            SELECT b.branch_id FROM branches b WHERE b.org_id = nr.org_id ORDER BY b.branch_id ASC LIMIT 1
        )
        WHERE nr.branch_id IS NULL;
    """)
    op.alter_column("notification_recipients", "branch_id", nullable=False)
    op.create_foreign_key(
        "fk_notification_recipients_branch_id_branches",
        "notification_recipients",
        "branches",
        ["branch_id"],
        ["branch_id"],
        ondelete="RESTRICT",
        onupdate="CASCADE",
    )
    op.create_index("ix_notification_recipients_branch_id_user_id", "notification_recipients", ["branch_id", "user_id"])

    # -------------------------------------------------------------------
    # 19. activity_logs
    # -------------------------------------------------------------------
    op.add_column("activity_logs", sa.Column("branch_id", sa.BigInteger(), nullable=True))
    op.execute("""
        UPDATE activity_logs al
        SET branch_id = e.master_branch_id
        FROM employees e
        WHERE al.employee_id = e.employee_id AND al.branch_id IS NULL;

        UPDATE activity_logs al
        SET branch_id = (
            SELECT b.branch_id FROM branches b WHERE b.org_id = al.org_id ORDER BY b.branch_id ASC LIMIT 1
        )
        WHERE al.branch_id IS NULL;
    """)
    op.alter_column("activity_logs", "branch_id", nullable=False)
    op.create_foreign_key(
        "fk_activity_logs_branch_id_branches",
        "activity_logs",
        "branches",
        ["branch_id"],
        ["branch_id"],
        ondelete="RESTRICT",
        onupdate="CASCADE",
    )
    op.create_index("ix_activity_logs_branch_id_logged_at", "activity_logs", ["branch_id", sa.text("logged_at DESC")])


def downgrade() -> None:
    # 19. activity_logs
    op.drop_index("ix_activity_logs_branch_id_logged_at", table_name="activity_logs")
    op.drop_constraint("fk_activity_logs_branch_id_branches", "activity_logs", type_="foreignkey")
    op.drop_column("activity_logs", "branch_id")

    # 18. notification_recipients
    op.drop_index("ix_notification_recipients_branch_id_user_id", table_name="notification_recipients")
    op.drop_constraint("fk_notification_recipients_branch_id_branches", "notification_recipients", type_="foreignkey")
    op.drop_column("notification_recipients", "branch_id")

    # 17. notifications
    op.drop_index("ix_notifications_branch_id_created_at", table_name="notifications")
    op.drop_constraint("fk_notifications_branch_id_branches", "notifications", type_="foreignkey")
    op.drop_column("notifications", "branch_id")

    # 16. login_reset_requests
    op.drop_index("ix_login_reset_requests_branch_id_status", table_name="login_reset_requests")
    op.drop_constraint("fk_login_reset_requests_branch_id_branches", "login_reset_requests", type_="foreignkey")
    op.drop_column("login_reset_requests", "branch_id")

    # 15. attendance_regularization_requests
    op.drop_index("ix_att_regularization_reqs_branch_id_status", table_name="attendance_regularization_requests")
    op.drop_constraint("fk_attendance_regularization_requests_branch_id_branches", "attendance_regularization_requests", type_="foreignkey")
    op.drop_column("attendance_regularization_requests", "branch_id")

    # 14. approval_requests
    op.drop_index("ix_approval_requests_branch_id_status", table_name="approval_requests")
    op.drop_constraint("fk_approval_requests_branch_id_branches", "approval_requests", type_="foreignkey")
    op.drop_column("approval_requests", "branch_id")

    # 13. employee_holiday_assignments
    op.drop_index("ix_employee_holiday_assignments_branch_id", table_name="employee_holiday_assignments")
    op.drop_constraint("fk_employee_holiday_assignments_branch_id_branches", "employee_holiday_assignments", type_="foreignkey")
    op.drop_column("employee_holiday_assignments", "branch_id")

    # 12. holiday_templates
    op.drop_index("ix_holiday_templates_branch_id", table_name="holiday_templates")
    op.drop_index("uq_holiday_templates_branch_id_name_ci", table_name="holiday_templates", if_exists=True)
    op.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS uq_holiday_templates_org_id_name_ci
        ON holiday_templates (org_id, lower(name))
        WHERE is_deleted = false
    """)
    op.drop_constraint("fk_holiday_templates_branch_id_branches", "holiday_templates", type_="foreignkey")
    op.drop_column("holiday_templates", "branch_id")

    # 11. employee_leave_balances
    op.drop_index("ix_employee_leave_balances_branch_id_employee_id", table_name="employee_leave_balances")
    op.drop_constraint("fk_employee_leave_balances_branch_id_branches", "employee_leave_balances", type_="foreignkey")
    op.drop_column("employee_leave_balances", "branch_id")

    # 10. leave_requests
    op.drop_index("ix_leave_requests_branch_id_status", table_name="leave_requests")
    op.drop_constraint("fk_leave_requests_branch_id_branches", "leave_requests", type_="foreignkey")
    op.drop_column("leave_requests", "branch_id")

    # 9. leave_types
    op.drop_index("ix_leave_types_branch_id", table_name="leave_types")
    op.drop_constraint("uq_leave_types_branch_id_alias", table_name="leave_types", type_="unique")
    op.create_unique_constraint("uq_leave_types_org_id_alias", "leave_types", ["org_id", "alias"])
    op.drop_constraint("fk_leave_types_branch_id_branches", "leave_types", type_="foreignkey")
    op.drop_column("leave_types", "branch_id")

    # 8. finalized_payroll_runs
    op.drop_index("ix_finalized_payroll_runs_branch_id_cycle_from", table_name="finalized_payroll_runs")
    op.drop_constraint("fk_finalized_payroll_runs_branch_id_branches", "finalized_payroll_runs", type_="foreignkey")
    op.drop_column("finalized_payroll_runs", "branch_id")

    # 7. payroll_computed_rows
    op.drop_index("ix_payroll_computed_rows_branch_id_cycle_from", table_name="payroll_computed_rows")
    op.drop_constraint("fk_payroll_computed_rows_branch_id_branches", "payroll_computed_rows", type_="foreignkey")
    op.drop_column("payroll_computed_rows", "branch_id")

    # 6. payroll_groups
    op.drop_index("ix_payroll_groups_branch_id", table_name="payroll_groups")
    op.drop_index("uq_payroll_groups_branch_id_name", table_name="payroll_groups", if_exists=True)
    op.create_index(
        "uq_payroll_groups_org_id_name",
        "payroll_groups",
        ["org_id", "name"],
        unique=True,
        postgresql_where=sa.text("is_deleted = false"),
    )
    op.drop_constraint("fk_payroll_groups_branch_id_branches", "payroll_groups", type_="foreignkey")
    op.drop_column("payroll_groups", "branch_id")

    # 5. roster
    op.drop_index("ix_roster_branch_id_roster_date", table_name="roster")
    op.drop_constraint("fk_roster_branch_id_branches", "roster", type_="foreignkey")
    op.drop_column("roster", "branch_id")

    # 4. shift_assignments
    op.drop_index("ix_shift_assignments_branch_id_employee_id", table_name="shift_assignments")
    op.drop_constraint("fk_shift_assignments_branch_id_branches", "shift_assignments", type_="foreignkey")
    op.drop_column("shift_assignments", "branch_id")

    # 3. shifts
    op.drop_index("ix_shifts_branch_id", table_name="shifts")
    op.drop_index("uq_shifts_branch_id_shift_name", table_name="shifts", if_exists=True)
    op.create_index(
        "uq_shifts_org_id_shift_name",
        "shifts",
        ["org_id", "shift_name"],
        unique=True,
        postgresql_where=sa.text("is_deleted = false"),
    )
    op.drop_constraint("fk_shifts_branch_id_branches", "shifts", type_="foreignkey")
    op.drop_column("shifts", "branch_id")

    # 2. designations
    op.drop_index("ix_designations_branch_id", table_name="designations")
    op.drop_index("uq_designations_branch_id_designation_name", table_name="designations", if_exists=True)
    op.create_index(
        "uq_designations_org_id_designation_name",
        "designations",
        ["org_id", "designation_name"],
        unique=True,
        postgresql_where=sa.text("is_deleted = false"),
    )
    op.drop_constraint("fk_designations_branch_id_branches", "designations", type_="foreignkey")
    op.drop_column("designations", "branch_id")

    # 1. departments
    op.drop_index("ix_departments_branch_id", table_name="departments")
    op.drop_index("uq_departments_branch_id_dept_name", table_name="departments", if_exists=True)
    op.create_index(
        "uq_departments_org_id_dept_name",
        "departments",
        ["org_id", "dept_name"],
        unique=True,
        postgresql_where=sa.text("is_deleted = false"),
    )
    op.drop_constraint("fk_departments_branch_id_branches", "departments", type_="foreignkey")
    op.drop_column("departments", "branch_id")
