import subprocess


def test_reply_template_load_empty_busy():
    """WP-443, 449, 450, 451: template load retry, empty state, aria-busy."""
    subprocess.run(
        ["node", "tests/js/reply_template_load_empty_busy.cjs"], check=True
    )
