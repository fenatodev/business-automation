import subprocess


def test_inflight_auto_suggestion_preserves_operator_state():
    subprocess.run(
        ["node", "tests/js/reply_auto_suggestion_inflight_guard.cjs"],
        check=True,
    )
