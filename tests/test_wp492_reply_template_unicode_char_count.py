import subprocess


def test_reply_template_unicode_char_count():
    subprocess.run(
        ["node", "tests/js/reply_template_unicode_char_count.cjs"], check=True
    )
