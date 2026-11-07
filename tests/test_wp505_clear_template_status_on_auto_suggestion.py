import subprocess


def test_auto_reply_suggestion_clears_template_insert_status():
    subprocess.run(
        ["node", "tests/js/reply_auto_suggestion_clears_template_status.cjs"],
        check=True,
    )
