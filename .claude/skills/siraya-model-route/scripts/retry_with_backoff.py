"""Exponential-backoff retry helper for Siraya Model Router.

Retries only on truly retryable status codes (408, 429, 500, 502, 503) and
surfaces everything else immediately so callers can fix the request. The
backoff respects `Retry-After` if the server returns one; otherwise it falls
back to `base * 2 ** attempt` plus jitter.

Usage:
    from retry_with_backoff import retry_with_backoff
    from openai import OpenAI

    client = OpenAI(base_url="https://llm.siraya.ai/v1", api_key=API_KEY)

    response = retry_with_backoff(
        lambda: client.chat.completions.create(
            model="claude-sonnet-4.5",
            messages=[{"role": "user", "content": "hi"}],
        )
    )
"""

from __future__ import annotations

import random
import time
from typing import Callable, TypeVar

RETRYABLE = {408, 429, 500, 502, 503}
T = TypeVar("T")


def _status_code(err: BaseException) -> int | None:
    # Works for openai/anthropic SDK exceptions and bare requests.HTTPError.
    return (
        getattr(err, "status_code", None)
        or getattr(getattr(err, "response", None), "status_code", None)
    )


def _retry_after(err: BaseException) -> float | None:
    resp = getattr(err, "response", None)
    if resp is None:
        return None
    raw = getattr(resp, "headers", {}).get("Retry-After")
    try:
        return float(raw) if raw is not None else None
    except (TypeError, ValueError):
        return None


def retry_with_backoff(
    fn: Callable[[], T],
    *,
    max_retries: int = 5,
    base: float = 1.0,
    factor: float = 2.0,
    max_sleep: float = 30.0,
) -> T:
    """Run `fn`, retrying with exponential backoff on retryable statuses."""
    for attempt in range(max_retries):
        try:
            return fn()
        except BaseException as err:
            code = _status_code(err)
            if code not in RETRYABLE or attempt == max_retries - 1:
                raise
            sleep = _retry_after(err) or min(base * (factor ** attempt), max_sleep)
            sleep += random.random()
            time.sleep(sleep)
    raise RuntimeError("unreachable")  # pragma: no cover
