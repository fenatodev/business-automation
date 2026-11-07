import subprocess


def test_successful_reply_submission_clears_template_insert_status():
    subprocess.run(
        ["node", "tests/js/reply_template_status_on_reply_submit.cjs"],
        check=True,
    )
