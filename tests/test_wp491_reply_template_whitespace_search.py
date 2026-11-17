import subprocess


def test_reply_template_whitespace_search():
    subprocess.run(
        ["node", "tests/js/reply_template_whitespace_search.cjs"], check=True
    )
