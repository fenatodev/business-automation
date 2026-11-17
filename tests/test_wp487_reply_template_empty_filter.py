import subprocess


def test_reply_template_empty_filter():
    subprocess.run(
        ["node", "tests/js/reply_template_empty_filter.cjs"], check=True
    )
