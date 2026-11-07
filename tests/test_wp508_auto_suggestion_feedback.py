import subprocess


def test_auto_reply_suggestion_failure_is_announced_without_overwriting_draft():
    subprocess.run(
        ["node", "tests/js/reply_auto_suggestion_feedback.cjs"],
        check=True,
        capture_output=True,
        text=True,
    )


def test_typing_reply_clears_auto_suggestion_feedback():
    subprocess.run(
        ["node", "tests/js/reply_auto_suggestion_feedback.cjs"],
        check=True,
        capture_output=True,
        text=True,
    )
