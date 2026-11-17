import subprocess


def test_reply_suggestion_clear_on_edit():
    subprocess.run(
        ["node", "tests/js/reply_suggestion_clear_on_edit.cjs"], check=True
    )
