---
name: siraya-model-route
description: Build, debug, or test apps against Siraya Model Router (siraya.ai / llm.siraya.ai) — a unified gateway that routes requests across 12+ AI providers (Anthropic, OpenAI, Google Vertex, Azure, DeepSeek, etc.) via OpenAI- and Anthropic-compatible APIs. Trigger when the user mentions Siraya, llm.siraya.ai, provider routing/fallbacks, multi-provider inference, switches an OpenAI/Anthropic SDK base URL to Siraya, points Claude Code at Siraya as backend, or asks about cross-provider cost/latency optimization — even if they don't explicitly say "routing".
---

# Siraya Model Route

Siraya Model Router is a unified inference gateway that routes requests across 12+ AI providers with automatic cost/latency/throughput optimization. The API is OpenAI-compatible and Anthropic-compatible — a drop-in replacement for either SDK.

## Setup

1. Sign up at [console.siraya.ai](https://console.siraya.ai)
2. Create an API key at [console.siraya.ai/api-keys](https://console.siraya.ai/api-keys)
3. Add credits at [console.siraya.ai/credit](https://console.siraya.ai/credit)

**Base URLs:**

| Env  | OpenAI-compatible                            | Anthropic-compatible                     |
|------|----------------------------------------------|------------------------------------------|
| prod | `https://llm.siraya.ai/v1`                   | `https://llm.siraya.ai`                  |
| uat  | `http://llm-uat.sirayatech.com/v1`           | `http://llm-uat.sirayatech.com`          |

(Anthropic SDK appends `/v1/messages` itself, so pass the host without `/v1`.) UAT is HTTP-only and lives on a different apex (`sirayatech.com`), with its own model catalog that may include preview model IDs not yet on prod.

**Auth:** `Authorization: Bearer <key>`

**`.env` convention used in this workspace** (both endpoints declared here, no hardcoding in scripts):

```
# Production
SIRAYA_API_KEY=sk-...
SIRAYA_BASE_URL=https://llm.siraya.ai/v1

# UAT
SIRAYA_UAT_API_KEY=sk-...
SIRAYA_UAT_BASE_URL=http://llm-uat.sirayatech.com/v1
```

Scripts read the pair matching the chosen environment (e.g. `--env prod|uat`). Never commit keys — Siraya is a GitHub secret-scanning partner and will auto-disable exposed keys.

## Quick Start

**Python (OpenAI SDK):**
```python
from openai import OpenAI

client = OpenAI(base_url="https://llm.siraya.ai/v1", api_key="<SIRAYA_API_KEY>")

completion = client.chat.completions.create(
    model="deepseek-v4-flash",
    messages=[{"role": "user", "content": "Hello"}]
)
print(completion.choices[0].message.content)
```

**TypeScript (OpenAI SDK):**
```typescript
import OpenAI from 'openai';

const client = new OpenAI({
    baseURL: 'https://llm.siraya.ai/v1',
    apiKey: '<SIRAYA_API_KEY>',
});

const completion = await client.chat.completions.create({
    model: 'deepseek-v4-flash',
    messages: [{ role: 'user', content: 'Hello' }],
});
```

**Anthropic SDK (drop-in):**
```python
import anthropic
client = anthropic.Anthropic(base_url="https://llm.siraya.ai", api_key="<SIRAYA_API_KEY>")
message = client.messages.create(
    model="claude-sonnet-4.5",
    max_tokens=1024,
    messages=[{"role": "user", "content": "Hello"}]
)
```

**curl:**
```bash
curl https://llm.siraya.ai/v1/chat/completions \
  -H "Authorization: Bearer $SIRAYA_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"deepseek-v4-flash","messages":[{"role":"user","content":"Hello"}]}'
```

> Before a longer session, run `scripts/sanity_probe.sh [model_id]` to confirm auth, reachability, and that the model is registered against your key.

## Provider Routing (the main feature)

Without a `provider` block in `extra_body`, Siraya picks providers via cost-effective load balancing. To control routing, pass a `provider` object:

```python
completion = client.chat.completions.create(
    model="gemini-2.5-pro",
    messages=[{"role": "user", "content": "Hello"}],
    extra_body={
        "provider": {
            "sort": "price",          # "price" | "throughput" | "latency"
            "allow_fallbacks": True,
        }
    }
)
```

| Parameter | Type | Default | Meaning |
|-----------|------|---------|---------|
| `sort` | string | — | `"price"` (cheapest) / `"throughput"` (highest tok/s) / `"latency"` (lowest TTFT) |
| `allow_fallbacks` | bool | `true` | Auto-fallback to other providers on failure |
| `order` | array | — | Preferred order, e.g. `["anthropic", "azure"]` |
| `only` | array | — | Whitelist providers |
| `ignore` | array | — | Blacklist providers |
| `require_parameters` | bool | `false` | Only route to providers that actually support every requested param |

**Provider IDs:** `anthropic`, `openai`, `google-vertex`, `azure`, `amazon-bedrock`, `deepseek`, `x-ai`, `alibaba`, `byteplus`, `minimax`, `moonshot`, `z-ai`. Per-provider model availability lives in `references/full-params.md`, or list live via:

```bash
curl -s https://llm.siraya.ai/v1/models -H "Authorization: Bearer $SIRAYA_API_KEY"
```

### Routing Recipes

```python
# Cheapest
extra_body={"provider": {"sort": "price"}}
# Lowest TTFT, no fallback (strict)
extra_body={"provider": {"sort": "latency", "allow_fallbacks": False}}
# Prefer Anthropic, then Google Vertex
extra_body={"provider": {"order": ["anthropic", "google-vertex"]}}
# Whitelist
extra_body={"provider": {"only": ["openai", "azure"]}}
# Blacklist
extra_body={"provider": {"ignore": ["deepseek"]}}
# Zero data retention only (may reduce available providers significantly)
extra_body={"zdr": True}
```

### Why `require_parameters: true` matters

If you request non-standard params (tools, `reasoning`, `response_format`) without it, Siraya may route to a provider that silently ignores those fields and returns a plain completion. Set it whenever the param must actually take effect.

## Using Claude Code with Siraya as backend

```bash
export ANTHROPIC_BASE_URL="https://llm.siraya.ai"
export ANTHROPIC_AUTH_TOKEN="<SIRAYA_API_KEY>"
export ANTHROPIC_MODEL="claude-sonnet-4.5"
claude .
```

Claude Code keeps its native Anthropic API protocol; Siraya handles routing underneath.

## Streaming

Set `stream=True`. Siraya emits occasional `: Siraya Model Router PROCESSING` SSE comments as keepalives — filter them. Aborting the client connection (`AbortController` in TS, closing the response in Python) cancels billing immediately.

```python
stream = client.chat.completions.create(
    model="claude-sonnet-4.5",
    messages=[{"role": "user", "content": "Tell me a story"}],
    stream=True,
    stream_options={"include_usage": True}   # final chunk carries token totals
)
for chunk in stream:
    if chunk.choices and chunk.choices[0].delta.content:
        print(chunk.choices[0].delta.content, end="")
```

## Prompt Caching

Cuts repeated-input cost by ~90%. Two modes:

**Implicit (automatic)** — OpenAI, Gemini, Grok, DeepSeek, Moonshot, Alibaba. No code change; ≥1024-token prefix matches automatically.

**Explicit (`cache_control`)** — Anthropic Claude requires markers. Up to 4 breakpoints per request. TTL: 300s (default) or 3600s.

```python
response = client.chat.completions.create(
    model="claude-sonnet-4.5",
    messages=[{
        "role": "system",
        "content": [
            {"type": "text", "text": "You are an expert."},
            {
                "type": "text",
                "text": LARGE_STATIC_CONTEXT,
                "cache_control": {"type": "ephemeral", "ttl": 3600}
            }
        ]
    }, {"role": "user", "content": "Question about the context"}]
)
```

**Layout rule:** static content first, variable content last. Modifying tool definitions, system prompts, or `tool_choice` invalidates the cache. Full miss checklist in `references/troubleshooting.md`.

## Tool Calling

```python
tools = [{
    "type": "function",
    "function": {
        "name": "get_weather",
        "description": "Get current weather for a location",
        "parameters": {
            "type": "object",
            "properties": {"location": {"type": "string"}},
            "required": ["location"],
            "additionalProperties": False
        },
        "strict": True
    }
}]

response = client.chat.completions.create(
    model="claude-sonnet-4.5",
    messages=[{"role": "user", "content": "Weather in Tokyo?"}],
    tools=tools,
    tool_choice="auto"   # "auto" | "required" | "none" | {"type":"function","function":{"name":"..."}}
)

if response.choices[0].finish_reason == "tool_calls":
    for call in response.choices[0].message.tool_calls:
        # call.id, call.function.name, call.function.arguments (JSON string)
        ...
```

When pinning the provider via `only`/`order`, also set `require_parameters: True` — otherwise Siraya may fall back to a provider that doesn't honor tools and you'll get plain text back.

## Structured Outputs

`json_schema` for strict validation; `json_object` for loose JSON. DeepSeek currently only supports `json_object`.

```python
response = client.chat.completions.create(
    model="claude-sonnet-4.5",
    messages=[{"role": "user", "content": "Extract person info from: ..."}],
    response_format={
        "type": "json_schema",
        "json_schema": {
            "name": "person",
            "strict": True,
            "schema": {
                "type": "object",
                "properties": {"name": {"type": "string"}, "age": {"type": "integer"}},
                "required": ["name", "age"],
                "additionalProperties": False
            }
        }
    }
)
```

Set an adequate `max_completion_tokens` — reasoning models burn tokens before producing output, and a tight budget will silently truncate the JSON.

## Reasoning / Thinking

Unified across providers (OpenAI o-series, Gemini 2.5, Claude 3.7+).

```python
response = client.chat.completions.create(
    model="claude-sonnet-4.5",
    messages=[{"role": "user", "content": "Solve this puzzle..."}],
    extra_body={
        "reasoning": {
            "effort": "high",       # "none" | "low" | "medium" | "high" | "xhigh"
            "max_tokens": 4000,
            "exclude": False        # True to hide reasoning from response
        }
    }
)

print(response.choices[0].message.reasoning_content)
print(response.usage.completion_tokens_details.reasoning_tokens)
```

On the Anthropic-compat endpoint, the native `thinking: {...}` block works as well.

## Multimodal Input

**Image (URL or base64):**
```python
messages=[{
    "role": "user",
    "content": [
        {"type": "text", "text": "What's in this image?"},
        {"type": "image_url", "image_url": {"url": "https://example.com/cat.jpg"}}
        # or: {"url": "data:image/jpeg;base64,..."}
    ]
}]
```

**PDF:**
```python
{"type": "file", "file": {"file_data": "data:application/pdf;base64,..."}}
```

## Web Search

```python
response = client.chat.completions.create(
    model="gpt-5",
    messages=[{"role": "user", "content": "Latest on the Mars sample return mission?"}],
    extra_body={
        "web_search_options": {
            "context_size": "medium",                              # "low" | "medium" | "high"
            "user_location": {"type": "approximate", "country": "US"}
        }
    }
)
```

## Error Handling

Brief rules (full table + retry helper in `references/troubleshooting.md`):

- **Retryable** with exponential backoff (base 1s, factor 2, jitter): `408`, `429`, `500`, `502`, `503`
- **Not retryable** — fix the request: `400`, `401`, `403`, `404`, `422`

A ready-to-use helper lives at `scripts/retry_with_backoff.py`.

## Other Useful Params

| Param | Description |
|-------|-------------|
| `transforms` | e.g. `["middle-out"]` — auto-compress long contexts |
| `zdr` | `true` — only route to zero-data-retention endpoints (reduces available providers) |
| `seed` | Deterministic sampling |
| `user` | End-user ID for abuse monitoring |

Full parameter reference: `references/full-params.md`.

## Zero Completion Insurance

Always on, no config. Empty/failed completions are never billed — logs show "zero credit deduction" for protected requests.

## Framework Integrations

**LiteLLM:**
```python
import litellm
response = litellm.completion(
    model="openai/deepseek-v4-flash",
    messages=[{"role": "user", "content": "Hi"}],
    api_base="https://llm.siraya.ai/v1",
    api_key="<SIRAYA_API_KEY>"
)
```

**LangChain:**
```python
from langchain_openai import ChatOpenAI
llm = ChatOpenAI(
    base_url="https://llm.siraya.ai/v1",
    api_key="<SIRAYA_API_KEY>",
    model="deepseek-v4-flash"
)
```

Also supports: PydanticAI, OpenAI Agents SDK, OpenAI Codex CLI, n8n, Langfuse, OpenClaw, OpenCode.

## Inspecting routing decisions

Standard responses don't expose the chosen upstream directly. Useful signals:

- `response.model` — sometimes carries a provider hint as prefix/suffix
- Sudden latency jumps across otherwise-identical requests usually mean a different upstream got picked
- The [Siraya console](https://console.siraya.ai) shows the actual provider per request

When attribution matters (debugging caching, reasoning, structured output), pin the provider so the result is reproducible:

```python
extra_body={"provider": {"order": ["anthropic"], "allow_fallbacks": False}}
```

## Bundled resources

- `references/full-params.md` — complete parameter reference + endpoint list
- `references/troubleshooting.md` — error codes, retry strategy, cache-miss / routing-surprise checklists
- `scripts/sanity_probe.sh` — verify key + model registration before a session
- `scripts/retry_with_backoff.py` — exponential-backoff helper for 408/429/5xx
