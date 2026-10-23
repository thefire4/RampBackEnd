"""Compatibility module — implementation lives in project_log_services.py."""

from src.api.services.project_log_services import (  # noqa: F401
    get_project_history,
    log_project_change,
    log_project_created,
)
