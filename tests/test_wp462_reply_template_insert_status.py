import subprocess


def test_reply_template_insert_status():
    subprocess.run(["node", "tests/js/reply_template_insert_status.cjs"], check=True)
