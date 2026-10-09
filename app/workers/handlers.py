import time
from typing import Any

from app.models.job import Job


def add(a: int, b: int) -> int:
    return a + b


def fibonacci(n: int) -> int:
    if n < 0:
        raise ValueError("n must be non-negative")

    previous, current = 0, 1
    for _ in range(n):
        previous, current = current, previous + current
    return previous


def sleep(seconds: float) -> None:
    time.sleep(seconds)


HANDLERS = {
    "add": add,
    "fibonacci": fibonacci,
    "sleep": sleep,
}


def execute(job: Job) -> Any:
    try:
        handler = HANDLERS[job.type]
        return handler(**job.payload)
    except Exception as e:
        raise(e)
