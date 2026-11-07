import subprocess


def test_reply_template_navigation_guard():
    subprocess.run(
        ["node", "tests/js/reply_template_navigation_guard.cjs"], check=True
    )
