"""Compatibility exports for crew code; canonical mapping lives in models."""

from dbie.models.task_roles import TASK_MODEL_ROLES, TaskClass, role_for_task

__all__ = ["TASK_MODEL_ROLES", "TaskClass", "role_for_task"]
