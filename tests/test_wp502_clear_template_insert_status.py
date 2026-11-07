import subprocess


def test_reply_template_insert_status_clears_on_manual_edit():
    subprocess.run(["node", "tests/js/reply_template_insert_status_clear.cjs"], check=True)
