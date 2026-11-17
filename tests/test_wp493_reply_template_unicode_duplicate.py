import subprocess


def test_reply_template_unicode_duplicate():
    subprocess.run(
        ["node", "tests/js/reply_template_unicode_duplicate.cjs"], check=True
    )
