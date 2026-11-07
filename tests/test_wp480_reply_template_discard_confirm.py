import subprocess


def test_reply_template_discard_requires_confirmation_only_for_changes():
    subprocess.run(
        ["node", "tests/js/reply_template_discard_confirm.cjs"], check=True
    )
