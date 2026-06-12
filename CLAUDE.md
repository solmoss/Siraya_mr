# Siraya Model Router — Testing Workspace

This directory is where Claude Code runs **functional tests** against Siraya Model Router and writes reports.

- **Docs:** https://docs.siraya.ai/docs/
- **Base URL:** `https://llm.siraya.ai`
  - OpenAI-compatible: `https://llm.siraya.ai/v1`
  - Anthropic-compatible: `https://llm.siraya.ai` (SDK adds `/v1/messages` itself)

## Step 0 — Always invoke `siraya-model-route` first

Before writing any test script, invoke the **`/siraya-model-route`** skill. It is the canonical reference for endpoints, request shapes, parameters, supported models, and known gotchas. Use it instead of guessing from memory or fetching docs again.

`references/full-params.md` and `references/troubleshooting.md` inside that skill cover error codes, retry strategy, and routing edge cases. Read them when you hit something unexpected.

### Maintain the skill as tests reveal gaps

The skill is a living document. When a test surfaces information that contradicts, is missing from, or is under-specified in the skill's description of **how Siraya is supposed to work**, you **must** update the skill before finishing the session. Treat the skill as part of the deliverable, not a read-only reference.

#### Skill updates vs. bug reports — pick the right channel

The skill describes **intended, correct behavior**. Updates to it are *functional additions or corrections to documentation* — never a place to record defects.

- **Update the skill** when the finding is documentation drift: the spec/contract is correct in production but the skill describes it wrong, omits it, or is out of date. Examples: a parameter exists but isn't listed; the documented default value doesn't match the actual default; a new model ID is supported but not mentioned; a routing header behaves as designed but the skill never explained it.
- **Do NOT update the skill** when the finding is a defect: Siraya's actual behavior diverges from what the docs/skill correctly describe, a request returns the wrong shape, a provider silently drops a parameter that should be honored, latency/error rates breach expectations, etc. Defects belong **only in the test report** — writing them into the skill would poison future runs by treating broken behavior as the spec.

Quick rule: if fixing the underlying system would make your finding obsolete, it's a **bug → report only**. If fixing the docs would make your finding obsolete, it's a **skill gap → update the skill**.

Trigger a skill update when a test reveals any of (all are documentation-shaped, not defect-shaped):

- **Incorrect facts in the skill** — a parameter shape, endpoint path, model ID, default value, or error code in the skill doesn't match the documented/intended behavior.
- **Missing coverage** — a feature, parameter, header, or supported failure mode that the skill doesn't mention but a tester would need to know.
- **Outdated guidance** — a recommended workaround, retry policy, or routing tip that no longer applies because the platform legitimately changed.
- **Newly discovered (but intended) gotchas** — provider-specific quirks, documented fallbacks, or non-obvious-but-by-design interactions worth warning future runs about.

How to update:

1. Edit the relevant file under `.claude/skills/siraya-model-route/` — usually `SKILL.md`, `references/full-params.md`, or `references/troubleshooting.md`. Pick the file whose scope matches the change.
2. Keep edits surgical: fix the wrong line, add the missing row/section, cite the model/endpoint the finding applies to.
3. In the test report, add a **Skill updates** section listing each file touched and a one-line summary of what changed. This makes the maintenance auditable.
4. If the same test also surfaced a defect, keep the defect in the report's results/findings sections — do **not** mirror it into the skill.

If unsure whether something belongs in the skill, ask: "Is this how Siraya is *supposed* to behave?" If yes and the skill is silent or wrong, update it. If no, it's a bug — write the report and stop.

## What we test here

Each test targets one Siraya feature and verifies behavior matches the docs **through Siraya's routing layer** (not just direct provider). Current scope:

| Feature | OpenAI-compat | Anthropic-compat | Notes |
|---------|---------------|------------------|-------|
| Basic chat completion | ✅ | ✅ | Sanity check |
| Streaming | ✅ | ✅ | SSE parsing, cancel behavior, keepalive comments |
| Prompt caching | implicit | `cache_control: ephemeral` | TTL, hit rate, provider-fallback impact |
| Tool calling | ✅ | ✅ | `tool_choice` modes, streaming aggregation |
| Structured outputs | `json_schema` / `json_object` | — | DeepSeek loose-mode fallback |
| Reasoning / thinking | `reasoning` object, `reasoning_effort` | `thinking` | `reasoning_content` field |
| Multimodal | image_url, file/pdf | image, document | URL vs base64 |
| Provider routing | `provider.sort` / `order` / `only` / `ignore` / `allow_fallbacks` | same via `extra_body` | Lock to single provider when debugging |
| ZDR | `zdr: true` | same | Reduces available providers |
| Error handling | 408/429/5xx retry | same | Exponential backoff |
| Web search | `web_search_options` | — | |

When the user requests a test, identify which row above it falls under. If it doesn't fit, ask before improvising.

## Credentials

`.env` (gitignored, never commit):
```
SIRAYA_API_KEY=sk-...
```

Always `source .env` before any `docker exec`, and always inject via `-e SIRAYA_API_KEY="$SIRAYA_API_KEY"` — never bake the key into a script or image.

## Execution Rules

### All scripts run inside `siraya_mr` Docker container

The host has no Python deps. The container image (see `Dockerfile`) ships `requests`, `openai`, `anthropic`. Add `rich` or other deps via `docker exec siraya_mr pip install <pkg>` if a script needs them, then capture that in the report's Environment section.

**Start container if not running:**
```bash
docker start siraya_mr
```

**Run a script (preferred for anything >10 lines):**
```bash
source .env
docker cp my_test.py siraya_mr:/tmp/my_test.py
docker exec -e SIRAYA_API_KEY="$SIRAYA_API_KEY" siraya_mr python3 /tmp/my_test.py
```

**Run inline (one-off probes):**
```bash
source .env
docker exec -e SIRAYA_API_KEY="$SIRAYA_API_KEY" siraya_mr python3 -c '
import os
from openai import OpenAI
c = OpenAI(base_url="https://llm.siraya.ai/v1", api_key=os.environ["SIRAYA_API_KEY"])
r = c.chat.completions.create(model="deepseek-v4-flash", messages=[{"role":"user","content":"hi"}])
print(r.choices[0].message.content)
'
```

### Script template

When writing a new test script, use this skeleton (keep it minimal — only add what the test needs):

```python
#!/usr/bin/env python3
"""<one-line objective>"""
import argparse, os, sys, time
from openai import OpenAI       # or: from anthropic import Anthropic

def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--api_key", default=os.environ.get("SIRAYA_API_KEY", ""))
    p.add_argument("--base_url", default="https://llm.siraya.ai/v1")
    p.add_argument("--model", default="claude-sonnet-4.5")
    return p.parse_args()

def main():
    args = parse_args()
    if not args.api_key:
        sys.exit("SIRAYA_API_KEY not set")
    client = OpenAI(base_url=args.base_url, api_key=args.api_key)
    # ... test logic, print results in a format the report can quote verbatim
    
if __name__ == "__main__":
    main()
```

Rules of thumb:
- **Argparse over hardcoded values** — makes scripts reusable across models/endpoints.
- **Print structured output** — pipe-separated tables or JSON lines, so the report can copy them in.
- **Inter-request sleep** for any loop hitting the API — use `time.sleep(2)` to avoid 429.
- **Capture token counts** (`response.usage.*`) when the test concerns cost or caching.
- **Don't silently retry** — surface failures explicitly so they appear in the report.

## Test Reports

After each test session, write a Markdown report in this directory, the report use Chinese.

**Naming:** `YYYY-MM-DD_<short-description>.md` (e.g. `2026-06-05_openai-compat-streaming.md`). Use today's date, not the date Claude Code thinks it is.

**Template (sections that proved valuable in past reports):**

```markdown
# Test: <Title>

**Date:** YYYY-MM-DD
**Tester:** Claude Code
**Target:** Siraya Model Router

## Objective

What was tested and the specific hypothesis being verified (e.g. "verify cache_control: ephemeral works through Siraya's routing for Claude Opus 4.6 within the 5-min TTL").

## Environment

- Container: `siraya_mr`
- Model(s): (exact IDs)
- Endpoint: `https://llm.siraya.ai...` (note whether OpenAI- or Anthropic-compatible)
- Script: `<filename>` + relevant settings (request count, interval, etc.)

Include the exact `docker exec` command that ran the test so the run is reproducible.

## Test Cases

Per case: input, expected, actual, pass/fail. A table is usually clearest.

## Results Summary

Pass/fail counts, notable findings, anomalies.

## Conclusion

Does the feature work through Siraya? Strength + caveats in one paragraph. Open follow-ups if any.
```

The report is the deliverable. Write it last but keep notes during execution so nothing is lost.
