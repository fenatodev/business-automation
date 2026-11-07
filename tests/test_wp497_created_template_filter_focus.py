import subprocess


def test_created_reply_template_is_revealed_and_focused_through_active_filter():
    subprocess.run(["node", "tests/js/reply_template_created_filter_focus.cjs"], check=True)
