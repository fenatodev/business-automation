import subprocess


def test_reply_template_protect_draft_switch():
    subprocess.run(
        ["node", "tests/js/reply_template_protect_draft_switch.cjs"], check=True
    )
