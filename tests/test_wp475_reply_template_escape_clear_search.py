import subprocess


def test_reply_template_escape_clear_search():
    subprocess.run(
        ["node", "tests/js/reply_template_escape_clear_search.cjs"], check=True
    )
