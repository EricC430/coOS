"""
M6.3 -- Role Context Tables

SPEC: docs/modules/M6_3_role_context_tables_SPEC.md
Risk mitigation: RISK-06 (role_implicit_states dual-key isolation)
Research: [R03 §6] role switch must fully reset Persona state
"""
from .models import RoleImplicitState, RoleProject, RoleSetting

__all__ = ["RoleProject", "RoleSetting", "RoleImplicitState"]
