import subprocess


def test_reply_template_edit_delete_guard():
    subprocess.run(
        ["node", "tests/js/reply_template_edit_delete_guard.cjs"], check=True
    )
