import subprocess


def test_reply_template_unicode_search():
    subprocess.run(
        ["node", "tests/js/reply_template_unicode_search.cjs"], check=True
    )
