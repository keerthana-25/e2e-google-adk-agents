# (b) Advanced Tool Agent – Gemini CLI as a tool inside ADK

An ADK agent whose main tool is the **Gemini CLI** running in headless mode (`gemini -p`).
The user gives a GitHub repo URL and a task; the tool clones the repo and runs Gemini CLI
inside it, so Gemini CLI can read the whole codebase itself (no need to pick files and send
them to the agent).

Based on: [Combine ADK, Gemini CLI and Cloud Run (Derrick Chwong)](https://medium.com/@derrickchwong/combine-adk-gemini-cli-and-cloud-run-c5dea5118853)
and [derrickchwong/gemini-cli-on-adk](https://github.com/derrickchwong/gemini-cli-on-adk).

## Architecture

```
user ──> gemini_cli_agent (ADK LlmAgent, gemini-2.5-pro)
              │  tool call: gemini_cli(task, github_url)
              ▼
         git clone --depth 1 <repo>  ->  /tmp/repos/<owner>__<repo>
              │
              ▼
         subprocess: gemini -p "<task>"   (cwd = repo)
              │  stdout
              ▼
         agent formats the answer for the user
```

`gemini_cli_agent/agent.py`:
- validates the URL (only `https://github.com/<owner>/<repo>`),
- clones once and reuses the clone,
- runs the CLI with an argument list (no `shell=True`, so the task text can't inject shell commands),
- has timeouts (5 min clone, 10 min CLI) and returns errors as text so the agent can report them.

## Run locally

```bash
cd 02-gemini-cli-agent
npm install -g @google/gemini-cli          # needs Node 20+
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp gemini_cli_agent/.env.example gemini_cli_agent/.env   # GOOGLE_API_KEY + GEMINI_API_KEY
export GEMINI_API_KEY=...                  # the CLI reads it from the environment
adk web
```

Example prompts:
- `Explain this codebase: https://github.com/derrickchwong/gemini-cli-on-adk`
- `Generate a test plan for https://github.com/google/adk-samples`
- `Review the code quality of the agent module and suggest improvements`

## Deploy to Cloud Run

```bash
export PROJECT_ID=your-project
./deploy.sh
```
The Dockerfile installs Node + Gemini CLI + ADK and runs `adk web` on port 8080. On Cloud Run
both ADK and Gemini CLI use Vertex AI (`GOOGLE_GENAI_USE_VERTEXAI=TRUE`); the service account
needs `roles/aiplatform.user`. The service is deployed with `--no-allow-unauthenticated`
(use `gcloud run services proxy gemini-cli-adk --region us-central1` to open it).

## Notes
- Only public repos are supported (no git credentials in the container).
- Gemini CLI in headless mode without `--yolo` won't run tools that need approval (e.g. writing
  files), so generated tests are returned as text in the answer.
