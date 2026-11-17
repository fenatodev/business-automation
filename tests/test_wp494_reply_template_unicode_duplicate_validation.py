import subprocess


def test_reply_template_unicode_duplicate_validation():
    subprocess.run(
        ["node", "tests/js/reply_template_unicode_duplicate.cjs"], check=True
    )
