"""Review pipeline: CodeAnalyzer -> StyleChecker -> TestRunner -> FeedbackSynthesizer."""

from google.adk.agents import Agent, SequentialAgent
from google.adk.code_executors import BuiltInCodeExecutor

from ..config import CRITIC_MODEL, WORKER_MODEL, StateKeys
from ..tools import (
    analyze_code_structure,
    check_code_style,
    save_review_report,
    search_past_feedback,
)

code_analyzer_agent = Agent(
    name="CodeAnalyzer",
    model=WORKER_MODEL,
    description="Parses the code structure with ast.",
    instruction="""You analyze Python code structure.
1. Call analyze_code_structure with the user's code EXACTLY as given (do not fix anything,
   not even syntax errors).
2. Summarize: number of functions/classes, imports, missing docstrings, and any syntax error
   (with line number).""",
    tools=[analyze_code_structure],
    output_key=StateKeys.STRUCTURE,
)

style_checker_agent = Agent(
    name="StyleChecker",
    model=WORKER_MODEL,
    description="Checks PEP 8 compliance with pycodestyle.",
    instruction="""You check PEP 8 style.
1. Call check_code_style (no arguments, it reads the code from state).
2. Report exactly what the tool returned:
## Style Analysis
- Style Score: <score>/100
- Total Issues: <count>
## Top Issues
<line, code, message for each top issue>""",
    tools=[check_code_style],
    output_key=StateKeys.STYLE_SUMMARY,
)

test_runner_agent = Agent(
    name="TestRunner",
    model=WORKER_MODEL,
    description="Writes and executes tests for the code using the built-in code executor.",
    instruction="""You are a testing specialist. The code to test is:
```python
{code_to_review?}
```
1. Work out what the code is supposed to do from names, docstrings and structure.
2. Write 10-15 tests (normal cases, edge cases, error handling) and EXECUTE them with your
   code executor. Report only what actually happened when you ran them.
3. Output ONLY a JSON object with these keys:
   - test_summary: total_tests_run, tests_passed, tests_failed, tests_with_errors
   - critical_issues: list of objects with type (logic_error | interface_bug | crash),
     description, example_input, expected_behavior, actual_behavior, severity
   - verdict: status (WORKING | BUGGY | BROKEN) and recommendation
Do not output the test code.""",
    code_executor=BuiltInCodeExecutor(),
    output_key=StateKeys.TEST_SUMMARY,
)

feedback_synthesizer_agent = Agent(
    name="FeedbackSynthesizer",
    model=CRITIC_MODEL,
    description="Combines all results into the final review.",
    instruction="""You are an experienced code reviewer and mentor.

Structure analysis: {structure_analysis_summary?}
Style check: {style_check_summary?}
Test results (JSON): {test_execution_summary?}

Steps, in order:
1. Call search_past_feedback to see this user's previous reviews (mention progress if any).
2. Write the feedback in markdown with these sections:
   ## Summary (honest overall assessment)
   ## Strengths (2-3 specific things)
   ## Code Quality (structure, style score, test results: X of Y passed, list each critical issue)
   ## Recommendations (specific fixes, critical bugs first)
   ## Next Steps (prioritized list)
3. Call save_review_report with feedback_text = the full feedback.
4. Return the feedback as your final answer.
Only use facts from the results above. Do not hide failing tests.""",
    tools=[search_past_feedback, save_review_report],
    output_key=StateKeys.FINAL_FEEDBACK,
)

code_review_pipeline = SequentialAgent(
    name="CodeReviewPipeline",
    description="Full review: structure analysis, PEP 8 check, executed tests, final feedback.",
    sub_agents=[code_analyzer_agent, style_checker_agent, test_runner_agent,
                feedback_synthesizer_agent],
)
