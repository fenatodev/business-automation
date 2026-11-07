import subprocess


def test_auto_suggestion_preserves_existing_reply_draft():
    subprocess.run(
        ["node", "tests/js/reply_auto_suggestion_clears_template_status.cjs"],
        check=True,
    )
