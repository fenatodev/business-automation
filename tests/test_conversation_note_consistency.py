"""Exercise actual note selection/save handlers with controlled synthetic responses."""
import subprocess


def test_conversation_note_consistency():
    subprocess.run(["node", "tests/js/conversation_note_consistency.cjs"], check=True)
