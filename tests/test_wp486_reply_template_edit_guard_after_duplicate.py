import subprocess


def test_reply_template_edit_guards_survive_duplicate_list_refresh():
    subprocess.run(
        ["node", "tests/js/reply_template_edit_guard_after_duplicate.cjs"],
        check=True,
    )
