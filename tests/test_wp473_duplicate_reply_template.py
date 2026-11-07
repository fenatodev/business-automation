import subprocess


def test_reply_template_can_be_duplicated_from_operator_ui():
    subprocess.run(
        ["node", "tests/js/reply_template_duplicate.cjs"],
        check=True,
    )
