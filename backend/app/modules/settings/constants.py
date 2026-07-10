"""Settings Management — module constants.

Defines the fixed feature-key catalog used by the Features Configuration surface
(§6 of the API contract). These keys map directly to boolean columns across the
two owned tables (org_settings and org_salary_slip_settings).
No dynamic feature-flag store exists — only these known toggles are supported.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Feature key catalog (fixed boolean columns only — §6 of the API contract)
# ---------------------------------------------------------------------------

#: Feature keys from org_settings
ORG_SETTINGS_FEATURE_KEYS: frozenset[str] = frozenset(
    {
        "advance_shift_enabled",
        "enable_regularization",
        "enable_photo_punch",
    }
)

#: Feature keys from org_salary_slip_settings
SALARY_SLIP_FEATURE_KEYS: frozenset[str] = frozenset(
    {
        "auto_release_payslip",
        "branch_wise_payslip",
    }
)

#: Full fixed feature-key catalog
ALL_FEATURE_KEYS: frozenset[str] = ORG_SETTINGS_FEATURE_KEYS | SALARY_SLIP_FEATURE_KEYS

# ---------------------------------------------------------------------------
# Cross-module pointer labels surfaced in ConfigurationView
# ---------------------------------------------------------------------------

CROSS_MODULE_POINTERS: dict[str, dict[str, str]] = {
    "leave": {
        "module": "leave",
        "description": "Leave cycle and carry-forward configuration (managed by the Leave module).",
    },
    "payroll": {
        "module": "payroll",
        "description": (
            "Payroll calculation rules, overtime, and wage formula (managed by the Payroll module)."
        ),
    },
    "attendance": {
        "module": "attendance",
        "description": (
            "Full attendance device and mobile settings (managed by the Employee module "
            "via org_attendance_settings)."
        ),
    },
}
