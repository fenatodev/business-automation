import subprocess


def test_reply_template_whitespace_fields_show_validation_feedback():
    subprocess.run(
        ["node", "tests/js/reply_template_whitespace_validation.cjs"],
        check=True,
    )
