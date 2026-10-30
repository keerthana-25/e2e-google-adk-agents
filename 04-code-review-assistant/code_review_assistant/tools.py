"""Deterministic tools used by the review / fix agents.

The LLM agents decide WHAT to do; these tools do the parts that should not be left to
an LLM (parsing with ast, PEP 8 checks with pycodestyle, scoring, saving reports).
"""

import ast
import json
import re
from datetime import datetime
from typing import Any, Dict, List

import pycodestyle
from google.adk.tools import ToolContext
from google.genai import types

from .config import StateKeys

IGNORED_CODES = ["E501", "W503"]   # long lines / line break before operator
SCORE_WEIGHTS = {"E1": 10, "E2": 3, "E3": 5, "E4": 8, "E5": 5, "E7": 7, "E9": 10,
                 "W1": 2, "W2": 2, "W3": 2, "W5": 3, "W6": 3, "N8": 7}


# ---------------- pure helpers (unit tested) ----------------

def strip_code_fences(text: str) -> str:
    """Removes ```python ... ``` fences if the model added them."""
    m = re.search(r"```(?:python|py)?\s*\n(.*?)```", text or "", re.DOTALL)
    return (m.group(1) if m else (text or "")).strip() + "\n"


def extract_json(text) -> Dict[str, Any]:
    """Pulls the first JSON object out of model output (which may have fences/extra text)."""
    if isinstance(text, dict):
        return text
    if not text:
        return {}
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end <= start:
        return {}
    try:
        return json.loads(text[start:end + 1])
    except json.JSONDecodeError:
        return {}


def code_structure(code: str) -> Dict[str, Any]:
    tree = ast.parse(code)
    functions, classes, imports = [], [], []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            functions.append({
                "name": node.name,
                "line": node.lineno,
                "args": [a.arg for a in node.args.args],
                "has_docstring": ast.get_docstring(node) is not None,
                "length": (node.end_lineno or node.lineno) - node.lineno + 1,
            })
        elif isinstance(node, ast.ClassDef):
            classes.append({
                "name": node.name,
                "line": node.lineno,
                "methods": [n.name for n in node.body if isinstance(n, ast.FunctionDef)],
                "has_docstring": ast.get_docstring(node) is not None,
            })
        elif isinstance(node, ast.Import):
            imports += [a.name for a in node.names]
        elif isinstance(node, ast.ImportFrom):
            imports.append(node.module or ".")
    return {
        "functions": functions,
        "classes": classes,
        "imports": imports,
        "line_count": len(code.splitlines()),
        "has_module_docstring": ast.get_docstring(tree) is not None,
    }


class _CollectReport(pycodestyle.BaseReport):
    def __init__(self, options):
        super().__init__(options)
        self.issues: List[Dict[str, Any]] = []

    def error(self, line_number, offset, text, check):
        code = text[:4]
        if self._ignore_code(code):
            return None
        self.issues.append({"line": line_number, "column": offset + 1,
                            "code": code, "message": text[5:]})
        return code


def _naming_issues(code: str) -> List[Dict[str, Any]]:
    issues = []
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return issues
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name != node.name.lower():
            issues.append({"line": node.lineno, "column": node.col_offset + 1, "code": "N802",
                           "message": f"function name '{node.name}' should be lowercase"})
        elif isinstance(node, ast.ClassDef) and (not node.name[0].isupper() or "_" in node.name):
            issues.append({"line": node.lineno, "column": node.col_offset + 1, "code": "N801",
                           "message": f"class name '{node.name}' should use CapWords"})
    return issues


def score_issues(issues: List[Dict[str, Any]]) -> int:
    deduction = sum(SCORE_WEIGHTS.get(i["code"][:2], 3) for i in issues)
    return max(0, 100 - min(deduction, 100))


def style_check(code: str) -> Dict[str, Any]:
    style = pycodestyle.StyleGuide(quiet=True, max_line_length=100, ignore=IGNORED_CODES,
                                   reporter=_CollectReport)
    lines = code.splitlines(keepends=True)
    if lines and not lines[-1].endswith("\n"):
        lines[-1] += "\n"
    checker = pycodestyle.Checker(lines=lines, options=style.options)
    checker.check_all()
    issues = checker.report.issues + _naming_issues(code)
    issues.sort(key=lambda i: (i["line"], i["column"]))
    return {"score": score_issues(issues), "issue_count": len(issues), "issues": issues}


def pass_rate(test_summary) -> float:
    """Handles both the review test JSON and the fix test JSON."""
    data = extract_json(test_summary)
    if "pass_rate" in data:
        return float(data["pass_rate"])
    if "passed" in data and data.get("total"):
        return 100.0 * data["passed"] / data["total"]
    s = data.get("test_summary", {})
    if s.get("total_tests_run"):
        return 100.0 * s.get("tests_passed", 0) / s["total_tests_run"]
    return 0.0


# ---------------- ADK tools ----------------

async def analyze_code_structure(code: str, tool_context: ToolContext) -> Dict[str, Any]:
    """Parses Python code with ast and saves it in state for the other agents.

    Args:
        code: The Python source code exactly as the user submitted it.
    """
    if not code or not code.strip():
        return {"status": "error", "message": "No code provided."}
    code = strip_code_fences(code)
    tool_context.state[StateKeys.CODE_TO_REVIEW] = code
    try:
        return {"status": "success", **code_structure(code)}
    except SyntaxError as e:
        return {"status": "error", "error_type": "SyntaxError",
                "message": f"line {e.lineno}: {e.msg}"}


async def check_code_style(tool_context: ToolContext) -> Dict[str, Any]:
    """Runs PEP 8 (pycodestyle) + naming checks on the code saved in state."""
    code = tool_context.state.get(StateKeys.CODE_TO_REVIEW, "")
    if not code:
        return {"status": "error", "message": "No code in state. Run analyze_code_structure first."}
    result = style_check(code)
    tool_context.state[StateKeys.STYLE_SCORE] = result["score"]
    tool_context.state[StateKeys.STYLE_ISSUES] = result["issues"][:20]
    return {"status": "success", "score": result["score"],
            "issue_count": result["issue_count"], "top_issues": result["issues"][:10]}


async def search_past_feedback(tool_context: ToolContext) -> Dict[str, Any]:
    """Returns this user's previous review summaries (score history)."""
    past = tool_context.state.get(StateKeys.PAST_FEEDBACK, [])
    return {"review_count": len(past), "past_reviews": past[-5:]}


async def save_review_report(feedback_text: str, tool_context: ToolContext) -> Dict[str, Any]:
    """Saves the final review as an artifact and records the score in the user's history.

    Args:
        feedback_text: The full markdown feedback that will be shown to the user.
    """
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    report = {
        "timestamp": ts,
        "style_score": tool_context.state.get(StateKeys.STYLE_SCORE),
        "test_pass_rate": round(pass_rate(tool_context.state.get(StateKeys.TEST_SUMMARY)), 1),
        "feedback": feedback_text,
    }
    version = None
    try:
        version = await tool_context.save_artifact(
            f"review_report_{ts}.json",
            types.Part.from_bytes(data=json.dumps(report, indent=2).encode(),
                                  mime_type="application/json"),
        )
    except Exception as e:  # no artifact service configured
        report["artifact_error"] = str(e)
    past = list(tool_context.state.get(StateKeys.PAST_FEEDBACK, []))
    past.append({k: report[k] for k in ("timestamp", "style_score", "test_pass_rate")})
    tool_context.state[StateKeys.PAST_FEEDBACK] = past[-20:]
    return {"status": "saved", "artifact_version": version}


async def validate_fixed_style(tool_context: ToolContext) -> Dict[str, Any]:
    """Runs the same style check on the fixed code (state: code_fixes)."""
    fixed = strip_code_fences(tool_context.state.get(StateKeys.CODE_FIXES, ""))
    tool_context.state[StateKeys.CODE_FIXES] = fixed
    try:
        ast.parse(fixed)
    except SyntaxError as e:
        tool_context.state[StateKeys.FIXED_STYLE_SCORE] = 0
        return {"status": "error", "message": f"Fixed code has a syntax error: line {e.lineno}: {e.msg}"}
    result = style_check(fixed)
    tool_context.state[StateKeys.FIXED_STYLE_SCORE] = result["score"]
    return {"status": "success", "score": result["score"], "remaining_issues": result["issues"][:10]}


async def compile_fix_report(tool_context: ToolContext) -> Dict[str, Any]:
    """Compares original vs fixed code (style score + test pass rate) and sets fix_status."""
    s = tool_context.state
    before_tests = pass_rate(s.get(StateKeys.TEST_SUMMARY))
    after_tests = pass_rate(s.get(StateKeys.FIX_TEST_SUMMARY))
    before_style = s.get(StateKeys.STYLE_SCORE, 0) or 0
    after_style = s.get(StateKeys.FIXED_STYLE_SCORE, 0) or 0

    if after_tests >= 100 and after_style >= 90:
        status = "SUCCESSFUL"
    elif after_tests > before_tests or after_style > before_style:
        status = "PARTIAL"
    else:
        status = "FAILED"
    s[StateKeys.FIX_STATUS] = status
    return {
        "status": status,
        "tests_pass_rate": {"before": round(before_tests, 1), "after": round(after_tests, 1)},
        "style_score": {"before": before_style, "after": after_style},
    }


def exit_fix_loop(tool_context: ToolContext) -> Dict[str, Any]:
    """Call this ONLY when fix_status is SUCCESSFUL to stop further fix attempts."""
    tool_context.actions.escalate = True
    return {"message": "Fix successful, exiting loop."}


async def save_fix_report(tool_context: ToolContext) -> Dict[str, Any]:
    """Saves the fixed code as an artifact."""
    try:
        version = await tool_context.save_artifact(
            "fixed_code.py",
            types.Part.from_bytes(data=tool_context.state.get(StateKeys.CODE_FIXES, "").encode(),
                                  mime_type="text/x-python"),
        )
        return {"status": "saved", "artifact": "fixed_code.py", "version": version}
    except Exception as e:
        return {"status": "error", "message": str(e)}
