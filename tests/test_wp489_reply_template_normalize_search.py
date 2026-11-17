import subprocess


def test_reply_template_normalize_search():
    subprocess.run(
        ["node", "tests/js/reply_template_normalize_search.cjs"], check=True
    )
