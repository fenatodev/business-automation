"""WP-168 — More keyboard shortcuts in operator UI.

Tests that the new keyboard shortcuts are registered and the footer reflects them:
- Ctrl+N: show create lead form
- Ctrl+L: focus lead search
- Ctrl+Shift+C: focus customer search
- /: focus opportunity search (when not in input)
"""
import re


class TestKeyboardShortcutsJavaScript:
    """Test JavaScript keyboard shortcut handlers."""

    @classmethod
    def setup_class(cls):
        with open("app/operator_ui/app.js") as f:
            cls.js = f.read()

    def test_ctrl_n_handler_exists(self):
        """Ctrl+N handler exists."""
        assert 'Ctrl+N' in self.js or ("e.key === \"n\"" in self.js and "show-create-lead" in self.js)

    def test_ctrl_n_shows_create_lead(self):
        """Ctrl+N triggers show create lead button."""
        section = re.search(
            r'e\.key === "n".*?show-create-lead',
            self.js,
            re.DOTALL,
        )
        assert section is not None

    def test_ctrl_l_handler_exists(self):
        """Ctrl+L handler exists."""
        section = re.search(
            r'e\.key === "l".*?lead-search',
            self.js,
            re.DOTALL,
        )
        assert section is not None

    def test_ctrl_l_focusses_lead_search(self):
        """Ctrl+L focuses lead search input."""
        section = re.search(
            r'e\.key === "l".*?\.focus\(\)',
            self.js,
            re.DOTALL,
        )
        assert section is not None

    def test_ctrl_shift_c_handler_exists(self):
        """Ctrl+Shift+C handler exists."""
        section = re.search(
            r'e\.shiftKey.*?e\.key === "C".*?customer-search',
            self.js,
            re.DOTALL,
        )
        assert section is not None

    def test_slash_handler_exists(self):
        """Slash / handler exists."""
        section = re.search(
            r'e\.key === "/"',
            self.js,
        )
        assert section is not None

    def test_slash_focusses_opp_search(self):
        """Slash / focuses opportunity search."""
        section = re.search(
            r'e\.key === "/"[^}]*opp-search',
            self.js,
            re.DOTALL,
        )
        assert section is not None

    def test_shortcuts_respect_input_state(self):
        """Shortcuts check isInput before triggering."""
        # Ctrl+N, Ctrl+L, Ctrl+Shift+C, / should all check !isInput
        section = re.search(
            r'e\.key === "/"[^}]*!isInput',
            self.js,
            re.DOTALL,
        )
        assert section is not None


class TestKeyboardShortcutsFooter:
    """Test that the footer reflects the new shortcuts."""

    @classmethod
    def setup_class(cls):
        with open("app/operator_ui/index.html") as f:
            cls.html = f.read()

    def test_footer_mentions_ctrl_n(self):
        """Footer mentions Ctrl+N shortcut."""
        footer = re.search(r'<footer>.*?</footer>', self.html, re.DOTALL)
        assert footer is not None
        assert 'Ctrl+N' in footer.group(0)

    def test_footer_mentions_ctrl_l(self):
        """Footer mentions Ctrl+L shortcut."""
        footer = re.search(r'<footer>.*?</footer>', self.html, re.DOTALL)
        assert footer is not None
        assert 'Ctrl+L' in footer.group(0)

    def test_footer_mentions_ctrl_shift_c(self):
        """Footer mentions Ctrl+Shift+C shortcut."""
        footer = re.search(r'<footer>.*?</footer>', self.html, re.DOTALL)
        assert footer is not None
        assert 'Ctrl+Shift+C' in footer.group(0)

    def test_footer_mentions_slash(self):
        """Footer mentions / shortcut."""
        footer = re.search(r'<footer>.*?</footer>', self.html, re.DOTALL)
        assert footer is not None
        # The / character in the footer
        assert '/ (buscar)' in footer.group(0)

    def test_footer_still_mentions_ctrl_k(self):
        """Footer still mentions original Ctrl+K shortcut."""
        footer = re.search(r'<footer>.*?</footer>', self.html, re.DOTALL)
        assert footer is not None
        assert 'Ctrl+K' in footer.group(0)

    def test_footer_still_mentions_escape(self):
        """Footer still mentions Escape shortcut."""
        footer = re.search(r'<footer>.*?</footer>', self.html, re.DOTALL)
        assert footer is not None
        assert 'Esc' in footer.group(0)
