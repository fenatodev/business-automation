import subprocess


def test_reply_template_edit_ui_flow():
    subprocess.run(["node", "tests/js/reply_template_edit.cjs"], check=True)
