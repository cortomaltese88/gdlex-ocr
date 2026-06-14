"""Smoke tests for processing profile configuration."""

from __future__ import annotations

import unittest

from gdlex_ocr.profiles import DEFAULT_PROFILE, PROFILES


class ProcessingProfilesTest(unittest.TestCase):
    def test_expected_profiles_and_default_exist(self) -> None:
        self.assertEqual(
            {"Veloce", "Bilanciato", "Accurato"},
            set(PROFILES),
        )
        self.assertEqual("Bilanciato", DEFAULT_PROFILE)
        self.assertIn(DEFAULT_PROFILE, PROFILES)

    def test_balanced_profile_values(self) -> None:
        profile = PROFILES["Bilanciato"]

        self.assertEqual(15, profile.block_size)
        self.assertEqual(10, profile.num_threads)
        self.assertEqual(6, profile.page_batch_size)
        self.assertEqual("fast", profile.table_mode)

    def test_accurate_profile_uses_accurate_tables(self) -> None:
        self.assertEqual("accurate", PROFILES["Accurato"].table_mode)

    def test_summaries_are_non_empty_and_informative(self) -> None:
        for name, profile in PROFILES.items():
            with self.subTest(profile=name):
                summary = profile.summary()
                self.assertTrue(summary.strip())
                self.assertIn(str(profile.block_size), summary)
                self.assertIn(str(profile.num_threads), summary)
                self.assertIn(profile.table_mode, summary)


if __name__ == "__main__":
    unittest.main()
