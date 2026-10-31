"""WP-163 — Theme toggle (dark/light) in operator UI.

Tests the theme toggle contract: HTML button exists, CSS variables for light theme,
and JavaScript theme switching logic.
"""
import re


class TestThemeToggleUI:
    """Test theme toggle UI contract."""

    @classmethod
    def setup_class(cls):
        with open("app/operator_ui/index.html") as f:
            cls.html = f.read()
        with open("app/operator_ui/app.js") as f:
            cls.js = f.read()
        with open("app/operator_ui/styles.css") as f:
            cls.css = f.read()

    def test_theme_toggle_button_exists(self):
        """Theme toggle button is in the topbar."""
        assert 'id="theme-toggle"' in self.html
        assert 'class="theme-toggle"' in self.html

    def test_theme_toggle_in_topbar_right(self):
        """Theme toggle is inside topbar-right container."""
        topbar_right = re.search(r'class="topbar-right".*?</div>', self.html, re.DOTALL)
        assert topbar_right is not None
        assert 'id="theme-toggle"' in topbar_right.group(0)

    def test_css_dark_theme_variables(self):
        """Dark theme CSS variables are defined in :root."""
        assert ":root {" in self.css
        assert "--bg:" in self.css
        assert "--panel:" in self.css
        assert "--text:" in self.css

    def test_css_light_theme_override(self):
        """Light theme CSS variables override dark theme."""
        assert '[data-theme="light"]' in self.css

    def test_css_light_theme_has_different_bg(self):
        """Light theme background is different from dark theme."""
        # Light theme should have a light background
        light_section = re.search(
            r'\[data-theme="light"\]\s*\{([^}]+)\}', self.css, re.DOTALL
        )
        assert light_section is not None
        assert "--bg:" in light_section.group(1)

    def test_css_light_theme_has_different_text(self):
        """Light theme text color is different from dark theme."""
        light_section = re.search(
            r'\[data-theme="light"\]\s*\{([^}]+)\}', self.css, re.DOTALL
        )
        assert light_section is not None
        assert "--text:" in light_section.group(1)

    def test_css_theme_toggle_styles(self):
        """Theme toggle button has dedicated styles."""
        assert ".theme-toggle" in self.css

    def test_js_theme_toggle_logic_exists(self):
        """JavaScript contains theme toggle initialization."""
        assert "theme-toggle" in self.js

    def test_js_theme_toggle_uses_local_storage(self):
        """Theme preference is persisted in localStorage."""
        assert "localStorage" in self.js
        assert "operator-theme" in self.js

    def test_js_theme_toggle_switches_data_attribute(self):
        """Theme toggle sets data-theme attribute on document element."""
        assert 'data-theme' in self.js
        assert 'setAttribute' in self.js

    def test_js_theme_toggle_has_dark_default(self):
        """Default theme is dark."""
        # The JS should default to "dark"
        assert '"dark"' in self.js

    def test_js_theme_toggle_has_light_option(self):
        """Light theme is available as an option."""
        assert '"light"' in self.js

    def test_js_theme_toggle_changes_icon(self):
        """Theme toggle changes icon based on current theme."""
        # Should have sun and moon icons
        assert "☀️" in self.js or "sun" in self.js.lower()
        assert "🌙" in self.js or "moon" in self.js.lower()

    def test_css_input_uses_variables(self):
        """Input elements use CSS variables for theming."""
        assert "var(--input-bg)" in self.css
        assert "var(--input-border)" in self.css

    def test_light_theme_has_input_variables(self):
        """Light theme defines input variables."""
        light_section = re.search(
            r'\[data-theme="light"\]\s*\{([^}]+)\}', self.css, re.DOTALL
        )
        assert light_section is not None
        assert "--input-bg:" in light_section.group(1)
        assert "--input-border:" in light_section.group(1)

    def test_theme_toggle_before_notification_bell(self):
        """Theme toggle appears before notification bell in DOM order."""
        theme_pos = self.html.index('id="theme-toggle"')
        notif_pos = self.html.index('id="notification-bell"')
        assert theme_pos < notif_pos

    def test_theme_toggle_has_title_attribute(self):
        """Theme toggle has accessible title."""
        assert 'title="Alternar tema"' in self.html

    def test_color_scheme_dark(self):
        """Dark theme sets color-scheme to dark."""
        root_section = re.search(r':root\s*\{([^}]+)\}', self.css, re.DOTALL)
        assert root_section is not None
        assert "color-scheme: dark" in root_section.group(1)

    def test_color_scheme_light(self):
        """Light theme sets color-scheme to light."""
        light_section = re.search(
            r'\[data-theme="light"\]\s*\{([^}]+)\}', self.css, re.DOTALL
        )
        assert light_section is not None
        assert "color-scheme: light" in light_section.group(1)

    def test_js_init_theme_iife(self):
        """Theme initialization is wrapped in IIFE."""
        assert "initTheme" in self.js
