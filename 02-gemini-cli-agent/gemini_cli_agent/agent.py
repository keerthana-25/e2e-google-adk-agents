"""ADK agent that uses the Gemini CLI (headless mode) as a tool.

Flow: user gives a GitHub URL + a task -> agent calls `gemini_cli` tool ->
tool clones the repo and runs `gemini -p "<task>"` inside it -> agent summarizes.
"""

import os
import re
import shutil
import subprocess

from dotenv import load_dotenv
from google.adk.agents import Agent

load_dotenv()

MODEL = os.getenv("AGENT_MODEL", "gemini-2.5-pro")
WORK_DIR = os.getenv("CLI_WORK_DIR", "/tmp/repos")
GEMINI_BIN = os.getenv("GEMINI_BIN", "gemini")
CLONE_TIMEOUT = 300
CLI_TIMEOUT = 600

_GITHUB_RE = re.compile(r"^https://github\.com/[\w.-]+/[\w.-]+?(\.git)?/?$")


def _clone_if_needed(github_url: str) -> str:
    """Clones the repo into WORK_DIR (once) and returns the local path."""
    if not _GITHUB_RE.match(github_url):
        raise ValueError(f"Not a valid public GitHub repo URL: {github_url}")
    repo_name = github_url.rstrip("/").split("/")[-1].removesuffix(".git")
    owner = github_url.rstrip("/").split("/")[-2]
    path = os.path.join(WORK_DIR, f"{owner}__{repo_name}")
    if not os.path.exists(path):
        os.makedirs(WORK_DIR, exist_ok=True)
        subprocess.run(
            ["git", "clone", "--depth", "1", github_url, path],
            check=True, capture_output=True, text=True, timeout=CLONE_TIMEOUT,
        )
    return path


def gemini_cli(task: str, github_url: str) -> str:
    """Runs the Gemini CLI in non-interactive mode on a GitHub repository.

    Args:
        task: What to ask Gemini CLI, e.g. "explain this codebase",
            "generate a test plan", "write unit tests for module X".
        github_url: Public GitHub repo URL, e.g. https://github.com/owner/repo

    Returns:
        The Gemini CLI output (stdout), or an error message.
    """
    if shutil.which(GEMINI_BIN) is None:
        return "Error: gemini CLI not found. Install it with `npm install -g @google/gemini-cli`."
    try:
        repo_dir = _clone_if_needed(github_url)
    except subprocess.CalledProcessError as e:
        return f"Error cloning repository: {e.stderr}"
    except Exception as e:  # bad url / timeout
        return f"Error cloning repository: {e}"

    # list args (no shell=True) so the task text can't inject shell commands
    cmd = [GEMINI_BIN, "-p", task]
    if os.getenv("GEMINI_CLI_MODEL"):
        cmd += ["-m", os.environ["GEMINI_CLI_MODEL"]]
    try:
        result = subprocess.run(
            cmd, cwd=repo_dir, capture_output=True, text=True,
            timeout=CLI_TIMEOUT, env=os.environ.copy(),
        )
    except subprocess.TimeoutExpired:
        return f"Gemini CLI timed out after {CLI_TIMEOUT} seconds."
    if result.returncode != 0:
        return f"Error executing Gemini CLI: {result.stderr.strip()}"
    return result.stdout


root_agent = Agent(
    name="gemini_cli_agent",
    model=MODEL,
    description="Software developer agent that uses Gemini CLI to analyze GitHub codebases.",
    instruction="""
You are a senior software developer. You have a powerful tool, `gemini_cli`, which runs
the Gemini CLI inside a cloned GitHub repository and can read the whole codebase.

- If the user didn't give a GitHub URL, ask for it.
- Always use `gemini_cli` to answer questions about the codebase (explain code, test plans,
  unit tests, code quality review, etc.). Pass a clear, specific task.
- Return the tool's answer to the user in clean markdown. Do not invent details that are
  not in the tool output. If the tool returns an error, show the error.
""",
    tools=[gemini_cli],
)
