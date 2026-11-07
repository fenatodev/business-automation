import subprocess


def test_cancel_reply_template_edit_restores_focus_through_active_filter():
    subprocess.run(
        ["node", "tests/js/reply_template_cancel_edit_filter_focus.cjs"], check=True
    )
