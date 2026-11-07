import subprocess


def test_reply_template_inserts_at_cursor_without_losing_draft():
    subprocess.run(["node", "tests/js/reply_template_preserve_draft.cjs"], check=True)
