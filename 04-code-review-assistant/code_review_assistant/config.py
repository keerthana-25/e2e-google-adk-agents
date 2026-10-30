import os

from dotenv import load_dotenv

load_dotenv()

WORKER_MODEL = os.getenv("WORKER_MODEL", "gemini-2.5-flash")   # analysis, tests, fixes
CRITIC_MODEL = os.getenv("CRITIC_MODEL", "gemini-2.5-pro")      # final feedback
MAX_FIX_ATTEMPTS = int(os.getenv("MAX_FIX_ATTEMPTS", "3"))


class StateKeys:
    """Session state keys shared between agents (avoids typos)."""
    CODE_TO_REVIEW = "code_to_review"
    STRUCTURE = "structure_analysis_summary"
    STYLE_SCORE = "style_score"
    STYLE_ISSUES = "style_issues"
    STYLE_SUMMARY = "style_check_summary"
    TEST_SUMMARY = "test_execution_summary"
    FINAL_FEEDBACK = "final_feedback"
    CODE_FIXES = "code_fixes"
    FIXED_STYLE_SCORE = "fixed_style_score"
    FIX_TEST_SUMMARY = "fix_test_execution_summary"
    FIX_REPORT = "final_fix_report"
    FIX_STATUS = "fix_status"
    # "user:" prefix = scoped to the user, survives across sessions with a persistent session service
    PAST_FEEDBACK = "user:past_feedback"
