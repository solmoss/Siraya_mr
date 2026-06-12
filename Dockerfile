FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    iputils-ping \
    ca-certificates \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

# Node.js 20 (NodeSource) — needed for the OpenAI Codex CLI
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/* \
    && node --version && npm --version

RUN pip install --no-cache-dir requests openai anthropic

# OpenAI Codex CLI (binary name: `codex`)
RUN npm install -g @openai/codex \
    && codex --version

CMD ["python3"]
