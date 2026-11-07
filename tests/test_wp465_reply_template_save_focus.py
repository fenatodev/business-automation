import subprocess


def test_reply_template_save_returns_focus_to_name_field():
    subprocess.run(["node", "tests/js/reply_template_save_focus.cjs"], check=True)
