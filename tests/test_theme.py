"""Static checks for shared application theme rules."""

from __future__ import annotations

import unittest

from gdlex_ocr.theme import LIGHT_STYLE_SHEET, MATRIX_STYLE_SHEET


class CheckboxThemeTest(unittest.TestCase):
    def test_checkbox_indicator_states_are_styled_in_all_themes(self) -> None:
        for style_sheet in (MATRIX_STYLE_SHEET, LIGHT_STYLE_SHEET):
            with self.subTest(style_sheet=style_sheet[:20]):
                self.assertIn("QCheckBox::indicator", style_sheet)
                self.assertIn("QCheckBox::indicator:unchecked", style_sheet)
                self.assertIn("QCheckBox::indicator:checked", style_sheet)
                self.assertIn("QCheckBox::indicator:disabled", style_sheet)


if __name__ == "__main__":
    unittest.main()
