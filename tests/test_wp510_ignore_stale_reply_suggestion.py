import subprocess


def test_reply_suggestion_from_previous_conversation_is_ignored():
    subprocess.run(
        ["node", "tests/js/reply_suggestion_stale_conversation.cjs"],
        check=True,
        capture_output=True,
        text=True,
    )
