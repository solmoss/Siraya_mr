# Troubleshooting

## Retry Strategy

Implement exponential backoff for retryable errors. Recommended: base 1s, factor 2, max 5 retries, jitter.

```python
import time, random

def retry_with_backoff(fn, max_retries=5):
    for attempt in range(max_retries):
        try:
            return fn()
        except Exception as e:
            code = getattr(e, "status_code", None)
            if code not in (408, 429, 500, 502, 503) or attempt == max_retries - 1:
                raise
            sleep = (2 ** attempt) + random.random()
            time.sleep(sleep)
```

## Error Code Reference

| Code | Type | Cause | Action |
|------|------|-------|--------|
| 400 | `invalid_request_error` | Malformed JSON, bad params | Fix request |
| 400 | `context_length_exceeded` | Prompt too long | Truncate or use `transforms: ["middle-out"]` |
| 400 | `content_policy_violation` | Blocked content | Modify prompt |
| 401 | `authentication_error` | Missing/invalid key | Check `Authorization: Bearer ...` |
| 403 | `permission_denied_error` | Insufficient permissions | Check key scope |
| 404 | `not_found_error` | Unknown model/route | Check model ID via `/v1/models` |
| 408 | timeout | Upstream timeout | Retry with backoff |
| 422 | `unprocessable_entity_error` | Semantically invalid | Fix request shape |
| 429 | `rate_limit_error` | Rate limited | Retry with backoff |
| 500 | server error | Internal issue | Retry with backoff |
| 502 | bad gateway | Upstream connection failure | Retry with backoff |
| 503 | service unavailable | No providers / fallback exhausted | Loosen `only`/`ignore` filters |

## Cache Misses

If prompt caching isn't reducing cost:

- Static content must be **identical** including whitespace
- For Anthropic: ensure `cache_control` markers are present
- For Anthropic: max 4 breakpoints per request
- TTL is 300s by default — long gaps drop the cache
- Modifying tools, system prompt, or `tool_choice` invalidates cache
- Adding/removing images may partially invalidate

## Routing Surprises

- **Wrong provider selected:** explicitly set `provider.order` or `provider.only`
- **Unexpected fallback:** set `allow_fallbacks: false`
- **Higher latency than expected:** sort by `latency` instead of `price`
- **`require_parameters: true`** is useful when using non-standard params (tools, reasoning) — without it Siraya may route to a provider that silently ignores them

## ZDR Surprises

`zdr: true` may reduce available providers significantly. If you get 503, the request couldn't find a ZDR endpoint for the requested model.

## Streaming Issues

- `: Siraya Model Router PROCESSING` comments are keepalives — filter them
- Aborting the client connection halts billing — use `AbortController` (TS) or close response (Python)
- Set `stream_options: {"include_usage": true}` to get final token counts in the last chunk
