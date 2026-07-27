"""User Profile — module constants.

The audit module label and the storage prefix used for profile-photo uploads.
No feature-permission keys: every route acts on the caller's own row, so
authentication alone (no RBAC feature gate) is the guard — mirroring ``/auth/me``.
"""

from __future__ import annotations

AUDIT_MODULE = "User Profile"
PROFILE_PHOTO_PREFIX = "profile-photos"

__all__ = ["AUDIT_MODULE", "PROFILE_PHOTO_PREFIX"]
