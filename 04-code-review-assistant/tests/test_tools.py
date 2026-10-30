"""Unit tests for the deterministic tools (no LLM calls)."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from code_review_assistant.tools import (  # noqa: E402
    code_structure,
    extract_json,
    pass_rate,
    score_issues,
    strip_code_fences,
    style_check,
)

BUGGY = '''def dfs_search_v1(graph, start, target):
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
'''

CLEAN = '''"""Module docstring."""


def add(a, b):
    """Add two numbers."""
    return a + b
'''


def test_structure_finds_function():
    s = code_structure(BUGGY)
    assert [f["name"] for f in s["functions"]] == ["dfs_search_v1"]
    assert s["functions"][0]["args"] == ["graph", "start", "target"]
    assert s["functions"][0]["has_docstring"] is False


def test_clean_code_scores_100():
    r = style_check(CLEAN)
    assert r["score"] == 100 and r["issue_count"] == 0


def test_style_issues_detected():
    r = style_check("import os,sys\ndef BadName( x ):\n  return x\n")
    codes = {i["code"] for i in r["issues"]}
    assert "E401" in codes      # multiple imports on one line
    assert "N802" in codes      # function name not lowercase
    assert r["score"] < 100


def test_score_floor_is_zero():
    assert score_issues([{"code": "E999"}] * 50) == 0


def test_strip_fences():
    assert strip_code_fences("```python\nx = 1\n```") == "x = 1\n"
    assert strip_code_fences("x = 1") == "x = 1\n"


def test_extract_json_with_extra_text():
    assert extract_json('Here:\n```json\n{"passed": 3, "total": 4}\n```') == {"passed": 3, "total": 4}
    assert extract_json("no json") == {}


def test_pass_rate_formats():
    assert pass_rate({"pass_rate": 80}) == 80
    assert pass_rate({"passed": 1, "total": 4}) == 25
    assert pass_rate('{"test_summary": {"total_tests_run": 10, "tests_passed": 7}}') == 70
