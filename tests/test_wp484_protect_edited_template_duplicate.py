import subprocess


def test_duplicate_is_disabled_while_its_template_is_edited():
    subprocess.run(
        ["node", "tests/js/reply_template_edit_duplicate_guard.cjs"],
        check=True,
    )
