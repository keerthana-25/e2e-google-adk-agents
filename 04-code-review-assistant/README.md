# (d) Production Quality Code Review Assistant

A Python code review assistant built with ADK. It reviews code with a 4-stage pipeline and,
if issues are found, can fix them with an iterative fix → test → validate loop.

Based on: [ADK code reviewer assistant codelab](https://codelabs.developers.google.com/adk-code-reviewer-assistant/instructions?hl=en#0)
and [ayoisio/adk-code-review-assistant](https://github.com/ayoisio/adk-code-review-assistant).

## Architecture

```
CodeReviewAssistant (root LlmAgent, routes with transfer_to_agent)
 ├─ CodeReviewPipeline (SequentialAgent)
 │    1. CodeAnalyzer       -> analyze_code_structure (ast)          -> structure_analysis_summary
 │    2. StyleChecker       -> check_code_style (pycodestyle + naming) -> style_score, style_issues
 │    3. TestRunner         -> BuiltInCodeExecutor (writes & RUNS tests) -> test_execution_summary
 │    4. FeedbackSynthesizer-> search_past_feedback, save_review_report  -> final_feedback
 └─ CodeFixPipeline (SequentialAgent)
      FixAttemptLoop (LoopAgent, max 3)
        1. CodeFixer        -> code_fixes
        2. FixTestRunner    -> BuiltInCodeExecutor                     -> fix_test_execution_summary
        3. FixValidator     -> validate_fixed_style, compile_fix_report, exit_fix_loop (escalate)
      FixSynthesizer        -> save_fix_report (artifact)              -> fix_summary
```

What makes it "production quality":
- **Deterministic tools for deterministic work** – parsing (`ast`), PEP 8 (`pycodestyle`), scoring
  and pass/fail decisions are Python code, not LLM guesses. The LLM only writes tests/fixes/feedback.
- **Real test execution** – tests are executed in Gemini's sandboxed code executor, not imagined.
- **Self-correcting loop** – `LoopAgent` retries the fix up to `MAX_FIX_ATTEMPTS` and stops early
  when `compile_fix_report` says `SUCCESSFUL` (tool sets `escalate=True`).
- **State contract** – all state keys are in `config.StateKeys`.
- **Artifacts + history** – review/fix reports are saved as artifacts, and the score history is
  kept in `user:` scoped state (survives across sessions with a persistent session service).
- **Config by env vars**, unit tests for the tools, Dockerfile for Cloud Run.

## Run

```bash
cd 04-code-review-assistant
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp code_review_assistant/.env.example code_review_assistant/.env   # GOOGLE_API_KEY
pytest -q tests          # unit tests for the tools (no API key needed)
adk web
```

Demo input (buggy DFS from the codelab – `stack = start` should be `stack = [start]`, and
`graph[current]` crashes for nodes with no entry):

```python
def dfs_search_v1(graph, start, target):
    visited = set()
    stack = start
    while stack:
        current = stack.pop()
        if current == target:
            return True
        if current not in visited:
            visited.add(current)
            for neighbor in graph[current]:
                if neighbor not in visited:
                    stack.append(neighbor)
    return False
```

1. `Please review this code: <paste>` → review with style score, executed test results, critical issues
2. `Yes, please fix it` → fix loop → before/after metrics + fixed code
3. Artifacts tab in `adk web` shows `review_report_*.json` and `fixed_code.py`

## Deploy (Cloud Run)

```bash
gcloud run deploy code-review-assistant --source . --region us-central1 \
  --set-env-vars GOOGLE_GENAI_USE_VERTEXAI=TRUE,GOOGLE_CLOUD_PROJECT=$PROJECT_ID,GOOGLE_CLOUD_LOCATION=us-central1 \
  --no-allow-unauthenticated
```
Optional `SESSION_DB_URL` (e.g. Cloud SQL Postgres) makes sessions and the user history persistent.

## Notes / differences from the reference
- `tools.py` is a smaller rewrite of the reference tools (~250 lines instead of ~980); it uses
  pycodestyle's API directly instead of capturing stdout.
- The CodeFixer does not use a code executor (it only writes code); testing is done by FixTestRunner.
- The pass criteria for SUCCESSFUL are 100% tests passing and style score ≥ 90.
