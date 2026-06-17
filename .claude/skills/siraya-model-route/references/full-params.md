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

## Responses API Parameters

`POST /v1/responses` — uses different field names from `/v1/chat/completions`.

| Parameter | Type | Description |
|-----------|------|-------------|
| `model` | string | Model ID (required) |
| `input` | string \| array | Prompt text or messages array (required) |
| `instructions` | string | System-level prompt (replaces system message) |
| `max_output_tokens` | int | Max output tokens |
| `tools` | array | Same format as chat completions |
| `tool_choice` | string | `"auto"` / `"none"` / `"required"` |
| `reasoning` | object | `{"effort": "low"\|"medium"\|"high"}` — 3 levels only (no `none`/`xhigh`) |
| `metadata` | object | Arbitrary key-value metadata |
| `temperature` | float | Sampling temperature |
| `stream` | bool | SSE streaming |

Response: `response.output` is an array of blocks — `type: "reasoning"` (content has `reasoning_text`) and `type: "message"` (content has `output_text`).

## Usage Response Object

All responses include a `usage` object. Full breakdown:

```json
{
  "usage": {
    "prompt_tokens": 100,
    "completion_tokens": 50,
    "total_tokens": 150,
    "prompt_tokens_details": {
      "cached_tokens": 80,
      "cache_write_tokens": 20,
      "text_tokens": 90,
      "audio_tokens": 0,
      "image_tokens": 10,
      "web_search_requests": 1
    },
    "completion_tokens_details": {
      "reasoning_tokens": 200,
      "text_tokens": 50,
      "audio_tokens": 0,
      "image_tokens": 0,
      "accepted_prediction_tokens": 30,
      "rejected_prediction_tokens": 5
    }
  }
}
```

- `web_search_requests` — number of native web search calls issued during this request
- `accepted_prediction_tokens` / `rejected_prediction_tokens` — speculative decoding metrics
- No `cost` field in the response; actual charges appear in the console Dashboard / Request Logs

## Endpoints

| Endpoint | Purpose |
|----------|---------|
| `POST /v1/chat/completions` | OpenAI-compat chat |
| `GET /v1/models` | List models |
| `POST /v1/embeddings` | Embeddings |
| `POST /v1/messages` | Anthropic-compat (no `/v1` prefix on base URL) |
| `POST /v1/responses` | OpenAI Responses API (stateful, `input`/`output` format) |
| `POST /v1/images/generations` | Text-to-image (response: `data[].b64_json`) |
| `POST /v1/videos/generations` | Text-to-video (response: `data[].url`); params: `model`, `prompt`, `seconds` |
