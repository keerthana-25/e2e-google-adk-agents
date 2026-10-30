FROM python:3.11-slim

# git for cloning, node for the Gemini CLI
RUN apt-get update && apt-get install -y curl git \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

RUN npm install -g @google/gemini-cli

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY gemini_cli_agent ./gemini_cli_agent

EXPOSE 8080
# adk web serves the agent UI + API
CMD ["adk", "web", "--host", "0.0.0.0", "--port", "8080", "."]
