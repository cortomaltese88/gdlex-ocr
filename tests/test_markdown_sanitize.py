"""Smoke tests for Markdown payload sanitization."""

from __future__ import annotations

import unittest

from gdlex_ocr.markdown_sanitize import (
    IMAGE_PLACEHOLDER,
    sanitize_markdown,
)


class MarkdownSanitizeTest(unittest.TestCase):
    def test_embedded_data_image_is_replaced(self) -> None:
        result = sanitize_markdown(
            "Prima\n![scan](data:image/png;base64,QUJDREVGRw==)\nDopo\n"
        )

        self.assertIn(IMAGE_PLACEHOLDER, result.markdown)
        self.assertNotIn("data:image", result.markdown)
        self.assertEqual(1, result.embedded_images_removed)
        self.assertEqual(0, result.long_base64_lines_removed)
        self.assertEqual(1, result.total_removed)

    def test_long_base64_like_line_is_replaced(self) -> None:
        payload = "QUJDREVGR0hJSktMTU5PUFFSU1RVVldYWVo=" * 4
        result = sanitize_markdown(
            f"Testo\n{payload}\nFine\n",
            max_line_length=80,
        )

        self.assertEqual(
            f"Testo\n{IMAGE_PLACEHOLDER}\nFine\n",
            result.markdown,
        )
        self.assertEqual(0, result.embedded_images_removed)
        self.assertEqual(1, result.long_base64_lines_removed)
        self.assertEqual(1, result.total_removed)

    def test_normal_text_is_unchanged(self) -> None:
        markdown = "# Titolo\n\nTesto normale con punteggiatura.\n"

        result = sanitize_markdown(markdown)

        self.assertEqual(markdown, result.markdown)
        self.assertEqual(0, result.total_removed)


if __name__ == "__main__":
    unittest.main()
