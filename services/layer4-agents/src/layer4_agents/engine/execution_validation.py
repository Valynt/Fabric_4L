from __future__ import annotations


def ensure_controller_accepts_execution(*, is_shutdown: bool, error_cls: type[Exception]) -> None:
    if is_shutdown:
        raise error_cls("OrchestrationController is shutting down")
