import subprocess


def test_updated_reply_template_remains_accessible_through_search_filter():
    subprocess.run(
        ["node", "tests/js/reply_template_updated_filter_focus.cjs"], check=True
    )
