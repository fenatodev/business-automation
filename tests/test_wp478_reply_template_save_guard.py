import subprocess


def test_reply_template_edit_cannot_be_cancelled_while_saving():
    subprocess.run(
        ["node", "tests/js/reply_template_save_guard.cjs"], check=True
    )
