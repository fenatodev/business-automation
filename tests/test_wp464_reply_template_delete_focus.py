import subprocess


def test_reply_template_delete_restores_keyboard_focus():
    subprocess.run(["node", "tests/js/reply_template_delete_focus.cjs"], check=True)
