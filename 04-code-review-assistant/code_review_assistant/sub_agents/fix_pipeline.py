"""Fix pipeline: LoopAgent(CodeFixer -> FixTestRunner -> FixValidator) -> FixSynthesizer."""

from google.adk.agents import Agent, LoopAgent, SequentialAgent
from google.adk.code_executors import BuiltInCodeExecutor

from ..config import CRITIC_MODEL, MAX_FIX_ATTEMPTS, WORKER_MODEL, StateKeys
from ..tools import compile_fix_report, exit_fix_loop, save_fix_report, validate_fixed_style

code_fixer_agent = Agent(
    name="CodeFixer",
    model=WORKER_MODEL,
    description="Rewrites the code to fix the issues found in review.",
    instruction="""You fix Python code.

Original code:
```python
{code_to_review?}
```
Style score: {style_score?}/100
Style issues: {style_issues?}
Test results: {test_execution_summary?}
Previous fix attempt (if any): {code_fixes?}
Previous attempt status (if any): {fix_status?}

Fix ALL critical issues from the tests, the style issues, and add missing docstrings.
Keep the same function/class names and behavior that the tests expect.
Output ONLY the complete fixed Python code. No explanations, no markdown fences.""",
    output_key=StateKeys.CODE_FIXES,
)

fix_test_runner_agent = Agent(
    name="FixTestRunner",
    model=WORKER_MODEL,
    description="Re-runs tests on the fixed code.",
    instruction="""You validate fixed code by executing tests.

Fixed code:
```python
{code_fixes?}
```
Original test results: {test_execution_summary?}

Write the same kind of tests that found the original issues (10-15 tests) and EXECUTE them
on the fixed code. Output ONLY a JSON object with keys: passed, failed, total, pass_rate
(0-100), still_failing (list of short descriptions). Do not output the test code.""",
    code_executor=BuiltInCodeExecutor(),
    output_key=StateKeys.FIX_TEST_SUMMARY,
)

fix_validator_agent = Agent(
    name="FixValidator",
    model=WORKER_MODEL,
    description="Scores the fix and decides whether to stop the loop.",
    instruction="""You validate a code fix.
1. Call validate_fixed_style (no arguments).
2. Call compile_fix_report (no arguments). It returns status SUCCESSFUL, PARTIAL or FAILED.
3. If and only if status is SUCCESSFUL, call exit_fix_loop.
4. Give a short summary with the before/after numbers from compile_fix_report.""",
    tools=[validate_fixed_style, compile_fix_report, exit_fix_loop],
    output_key=StateKeys.FIX_REPORT,
)

fix_attempt_loop = LoopAgent(
    name="FixAttemptLoop",
    sub_agents=[code_fixer_agent, fix_test_runner_agent, fix_validator_agent],
    max_iterations=MAX_FIX_ATTEMPTS,
)

fix_synthesizer_agent = Agent(
    name="FixSynthesizer",
    model=CRITIC_MODEL,
    description="Presents the fix results.",
    instruction="""Present the fix results to the user.

Validation report: {final_fix_report?}
Fix status: {fix_status?}
Fixed code:
{code_fixes?}

1. Call save_fix_report (no arguments).
2. Respond in markdown:
   ## Fix Summary (status and key improvements)
   ## Metrics (test pass rate before -> after, style score before -> after)
   ## What Was Fixed
   ## Fixed Code (the complete code in a python code block)
   ## Remaining Issues (only if status is not SUCCESSFUL)
Use only the numbers from the validation report.""",
    tools=[save_fix_report],
    output_key="fix_summary",
)

code_fix_pipeline = SequentialAgent(
    name="CodeFixPipeline",
    description="Fixes the reviewed code with up to N fix/test/validate iterations.",
    sub_agents=[fix_attempt_loop, fix_synthesizer_agent],
)
