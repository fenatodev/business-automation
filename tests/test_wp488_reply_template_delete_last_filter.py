import subprocess


def test_reply_template_delete_last_filter():
    subprocess.run(
        ["node", "tests/js/reply_template_delete_last_filter.cjs"], check=True
    )
