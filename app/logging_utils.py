import logging
from contextlib import contextmanager
from time import perf_counter
from typing import Iterator


def _details(context: dict[str, object]) -> str:
    return " ".join(f"{key}={value}" for key, value in context.items() if value is not None)


@contextmanager
def log_operation(logger: logging.Logger, operation: str, **context: object) -> Iterator[None]:
    """Log an operation's start, completion, failure, and elapsed wall-clock time."""
    details = _details(context)
    suffix = f" {details}" if details else ""
    logger.info("process_started operation=%s%s", operation, suffix)
    started = perf_counter()
    try:
        yield
    except Exception:
        logger.exception(
            "process_failed operation=%s elapsed_seconds=%.3f%s",
            operation, perf_counter() - started, suffix,
        )
        raise
    else:
        logger.info(
            "process_completed operation=%s elapsed_seconds=%.3f%s",
            operation, perf_counter() - started, suffix,
        )
