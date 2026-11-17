import subprocess


def test_reply_template_announce_search_clear():
    subprocess.run(
        ["node", "tests/js/reply_template_announce_search_clear.cjs"], check=True
    )
