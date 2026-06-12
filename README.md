# Siraya_MR

Functional testing workspace for **Siraya Model Router** (https://llm.siraya.ai) — a unified gateway that routes requests across 12+ AI providers via OpenAI- and Anthropic-compatible APIs.

This repository tracks the **base configuration** used by Claude Code when running tests against Siraya in this directory. Test scripts and per-session reports are produced locally and intentionally kept out of git.

## What's in here

| Path | Purpose |
|------|---------|
| `CLAUDE.md` | Project instructions for Claude Code — execution rules, report template, what to test, when to update the skill. |
| `Dockerfile` | `siraya_mr` container image. Python 3.12 + `requests` / `openai` / `anthropic` SDKs, Node 20, and the OpenAI Codex CLI. |
| `.claude/skills/siraya-model-route/` | Canonical skill describing Siraya's endpoints, parameters, supported models, and known gotchas. Invoked before writing any test. |
| `.gitignore` | Excludes secrets, local Codex state, settings.local.json, dated test reports, and ad-hoc test scripts. |

## Setup

1. **Create `.env`** (gitignored):
   ```
   SIRAYA_API_KEY=sk-...
   ```
2. **Build & start the container:**
   ```bash
   docker build -t siraya_mr .
   docker run -dit --name siraya_mr siraya_mr
   ```
3. **Run a probe** (key is injected at runtime, never baked in):
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

## How tests are run

See `CLAUDE.md` for the full workflow. In short:

- Always invoke the `/siraya-model-route` skill before writing a test script.
- All scripts run inside the `siraya_mr` container — the host has no Python deps.
- Each session produces a Markdown report (Chinese), named `YYYY-MM-DD_<short-description>.md`. Reports live locally and are not committed.
- If a test reveals documentation drift in the skill, update the skill in the same session.

## Reference

- Siraya docs: https://docs.siraya.ai/docs/
- Base URL: `https://llm.siraya.ai` (Anthropic-compatible) / `https://llm.siraya.ai/v1` (OpenAI-compatible)
