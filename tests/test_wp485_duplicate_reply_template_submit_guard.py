import subprocess


def test_reply_template_duplicate_prevents_concurrent_submissions():
    subprocess.run(
        ["node", "tests/js/reply_template_duplicate_guard.cjs"],
        check=True,
    )
