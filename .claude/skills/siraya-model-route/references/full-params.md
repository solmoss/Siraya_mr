# Full Parameter Reference

## Core

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `model` | string | — | Model ID (required) |
| `messages` | array | — | Conversation history (required) |
| `temperature` | float 0.0–2.0 | 1.0 | Output randomness |
| `top_p` | float 0.0–1.0 | 1.0 | Nucleus sampling |
| `n` | int ≥1 | 1 | Number of completions |
| `max_completion_tokens` | int ≥1 | — | Max output tokens (prefer over `max_tokens`) |
| `max_tokens` | int ≥1 | — | Deprecated |
| `stream` | bool | false | SSE streaming |
| `stream_options` | object | — | `{"include_usage": true}` |
| `user` | string | — | End-user identifier |

## Penalties & Sampling

| Parameter | Range | Default | Description |
|-----------|-------|---------|-------------|
| `frequency_penalty` | -2.0–2.0 | 0.0 | Penalize frequent tokens |
| `presence_penalty` | -2.0–2.0 | 0.0 | Penalize already-used tokens |
| `logit_bias` | -100–100 | — | Per-token bias map |
| `seed` | int | — | Deterministic sampling |
| `stop` | array ≤4 | — | Stop sequences |
| `logprobs` | bool | false | Return log probs |
| `top_logprobs` | 0–20 | — | Top N log probs |

## Output Structure

```json
{
  "response_format": {
    "type": "json_schema",
    "json_schema": {
      "name": "...",
      "strict": true,
      "schema": { /* JSON Schema */ }
    }
  }
}
```
Or `{"type": "json_object"}` for loose JSON.

## Tools

| Parameter | Description |
|-----------|-------------|
| `tools` | Array of `{type:"function", function:{name, description, parameters, strict}}` |
| `tool_choice` | `"auto"` / `"none"` / `"required"` / `{type:"function", function:{name}}` |
| `parallel_tool_calls` | Allow multiple simultaneous tool calls |

## Reasoning

```json
{
  "reasoning": {
    "effort": "high",       // none | low | medium | high | xhigh
    "max_tokens": 4000,
    "exclude": false,        // hide reasoning from output
    "enabled": true
  }
}
```
Also: `reasoning_effort: "low"|"medium"|"high"` (legacy, o1/o3/Gemini 2.5).  
Claude 3.7+: `thinking: {...}` (extended thinking).

## Web Search

```json
{
  "web_search_options": {
    "context_size": "medium",              // "low" | "medium" | "high"
    "user_location": {
      "type": "approximate",
      "country": "US",
      "city": "San Francisco",
      "region": "CA"
    }
  }
}
```

## Routing

These fields go inside `extra_body` on OpenAI-compat calls (or directly at the top level on Anthropic-compat calls — the Anthropic SDK forwards unknown keys via its own `extra_body`/`metadata` mechanism).

```json
{
  "provider": {
    "sort": "price",                       // "price" | "throughput" | "latency"
    "allow_fallbacks": true,
    "order": ["anthropic", "azure"],
    "only": ["openai"],
    "ignore": ["deepseek"],
    "require_parameters": true
  },
  "transforms": ["middle-out"],
  "zdr": true
}
```

## Provider IDs

`anthropic`, `openai`, `google-vertex`, `azure`, `amazon-bedrock`, `deepseek`, `x-ai`, `alibaba`, `byteplus`, `minimax`, `moonshot`, `z-ai`

## Endpoints

| Endpoint | Purpose |
|----------|---------|
| `POST /v1/chat/completions` | OpenAI-compat chat |
| `GET /v1/models` | List models |
| `POST /v1/embeddings` | Embeddings |
| `POST /v1/messages` | Anthropic-compat (no `/v1` prefix on base URL) |
| `POST /v1/responses` | OpenAI Responses API |
| `POST /v1/images/generations` | Text-to-image |
| `POST /v1/videos/generations` | Text-to-video |
