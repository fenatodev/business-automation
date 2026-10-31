"""WP-092 — Opportunity actionLabels fix UI contract tests."""
import pytest


@pytest.fixture
def operator_ui():
    """Read the operator UI files."""
    import pathlib
    base = pathlib.Path("app/operator_ui")
    return {
        "html": (base / "index.html").read_text(),
        "js": (base / "app.js").read_text(),
        "css": (base / "styles.css").read_text(),
    }


class TestActionLabelsComplete:
    """Verify actionLabels includes all triage status values."""

    def test_in_progress_label(self, operator_ui):
        js = operator_ui["js"]
        assert 'in_progress: "Em andamento"' in js

    def test_done_label(self, operator_ui):
        js = operator_ui["js"]
        assert 'done: "Concluída"' in js

    def test_lost_label(self, operator_ui):
        js = operator_ui["js"]
        assert 'lost: "Perdida"' in js

    def test_pending_label(self, operator_ui):
        js = operator_ui["js"]
        assert 'pending: "Pendente"' in js

    def test_ignore_label(self, operator_ui):
        js = operator_ui["js"]
        assert 'ignore: "Ignorar"' in js

    def test_follow_label(self, operator_ui):
        js = operator_ui["js"]
        assert 'follow: "Acompanhar"' in js

    def test_prepare_proposal_label(self, operator_ui):
        js = operator_ui["js"]
        assert 'prepare_proposal: "Preparar proposta"' in js

    def test_action_labels_object_exists(self, operator_ui):
        js = operator_ui["js"]
        assert "const actionLabels = {" in js

    def test_no_unknown_state_for_valid_actions(self, operator_ui):
        """Ensure all triage actions have labels so 'Estado desconhecido' is not shown."""
        js = operator_ui["js"]
        # All triage actions from schema must have labels
        assert 'in_progress:' in js
        assert 'done:' in js
        assert 'lost:' in js

    def test_wp092_comment(self, operator_ui):
        assert "WP-092" in operator_ui["js"]
