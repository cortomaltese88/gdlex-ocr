"""Tests for Help menu update check action."""

from __future__ import annotations

import os
import unittest
from unittest.mock import MagicMock, patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QMessageBox

from gdlex_ocr.gui import (
    MainWindow,
    _build_deb_download_url,
    _fetch_latest_release_info,
    _find_deb_asset,
    _is_remote_version_newer,
    _parse_version_tuple,
)
from gdlex_ocr.version import APP_VERSION


def _fake_release(
    version: str = "0.7.0",
    *,
    deb: bool = True,
) -> dict:
    assets = []
    if deb:
        assets.append(
            {
                "name": f"gdlex-ocr_{version}_all.deb",
                "browser_download_url": _build_deb_download_url(version),
            }
        )
    return {
        "tag_name": f"v{version}",
        "html_url": f"https://github.com/cortomaltese88/gdlex-ocr/releases/tag/v{version}",
        "assets": assets,
    }


class VersionHelpersTest(unittest.TestCase):
    def test_parse_version_tuple(self) -> None:
        self.assertEqual(_parse_version_tuple("0.6.0"), (0, 6, 0))
        self.assertEqual(_parse_version_tuple("1.2.3"), (1, 2, 3))

    def test_remote_newer(self) -> None:
        self.assertTrue(_is_remote_version_newer("0.6.0", "0.6.1"))
        self.assertTrue(_is_remote_version_newer("0.6.1", "0.10.0"))
        self.assertTrue(_is_remote_version_newer("0.6.1", "1.0.0"))

    def test_remote_not_newer(self) -> None:
        self.assertFalse(_is_remote_version_newer("0.6.0", "0.6.0"))
        self.assertFalse(_is_remote_version_newer("0.7.0", "0.6.1"))

    def test_0_10_0_greater_than_0_6_1(self) -> None:
        self.assertTrue(_is_remote_version_newer("0.6.1", "0.10.0"))

    def test_build_deb_download_url(self) -> None:
        url = _build_deb_download_url("0.6.0")
        self.assertEqual(
            url,
            "https://github.com/cortomaltese88/gdlex-ocr/releases/download/"
            "v0.6.0/gdlex-ocr_0.6.0_all.deb",
        )

    def test_find_deb_asset_present(self) -> None:
        release = _fake_release("0.7.0", deb=True)
        url = _find_deb_asset(release)
        self.assertIsNotNone(url)
        self.assertIn("gdlex-ocr_0.7.0_all.deb", url)

    def test_find_deb_asset_missing(self) -> None:
        release = _fake_release("0.7.0", deb=False)
        self.assertIsNone(_find_deb_asset(release))

    def test_find_deb_asset_empty_assets(self) -> None:
        self.assertIsNone(_find_deb_asset({"assets": []}))
        self.assertIsNone(_find_deb_asset({}))


class UpdateCheckMenuTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        self.window = MainWindow()

    def tearDown(self) -> None:
        self.window.close()
        self.window.deleteLater()
        self.app.processEvents()

    def _find_update_action(self):
        for action in self.window.menuBar().actions():
            menu = action.menu()
            if menu is None:
                continue
            for child in menu.actions():
                if child.text() == "Controlla aggiornamenti…":
                    return child
        return None

    def test_update_action_exists_in_help_menu(self) -> None:
        action = self._find_update_action()
        self.assertIsNotNone(
            action, "Menu action 'Controlla aggiornamenti…' not found"
        )

    @patch("gdlex_ocr.gui._fetch_latest_release_info")
    @patch("gdlex_ocr.gui.QMessageBox.information")
    def test_up_to_date(
        self, mock_info: MagicMock, mock_fetch: MagicMock
    ) -> None:
        mock_fetch.return_value = _fake_release(APP_VERSION)
        action = self._find_update_action()
        assert action is not None
        action.trigger()
        mock_info.assert_called_once()
        msg = mock_info.call_args[0][2]
        self.assertIn("aggiornato", msg)
        self.assertIn(APP_VERSION, msg)

    @patch("gdlex_ocr.gui.QDesktopServices.openUrl", return_value=True)
    @patch("gdlex_ocr.gui._fetch_latest_release_info")
    @patch(
        "gdlex_ocr.gui.QMessageBox.question",
        return_value=QMessageBox.StandardButton.Yes,
    )
    def test_update_available_opens_deb(
        self,
        mock_question: MagicMock,
        mock_fetch: MagicMock,
        mock_open: MagicMock,
    ) -> None:
        mock_fetch.return_value = _fake_release("99.0.0")
        action = self._find_update_action()
        assert action is not None
        action.trigger()
        mock_question.assert_called_once()
        msg = mock_question.call_args[0][2]
        self.assertIn("99.0.0", msg)
        self.assertIn(APP_VERSION, msg)
        self.assertIn("gdlex-ocr_99.0.0_all.deb", msg)
        mock_open.assert_called_once()
        opened_url = mock_open.call_args[0][0].toString()
        self.assertIn("gdlex-ocr_99.0.0_all.deb", opened_url)

    @patch("gdlex_ocr.gui.QDesktopServices.openUrl", return_value=True)
    @patch("gdlex_ocr.gui._fetch_latest_release_info")
    @patch(
        "gdlex_ocr.gui.QMessageBox.question",
        return_value=QMessageBox.StandardButton.Yes,
    )
    def test_update_available_no_deb_opens_release_page(
        self,
        mock_question: MagicMock,
        mock_fetch: MagicMock,
        mock_open: MagicMock,
    ) -> None:
        mock_fetch.return_value = _fake_release("99.0.0", deb=False)
        action = self._find_update_action()
        assert action is not None
        action.trigger()
        mock_question.assert_called_once()
        msg = mock_question.call_args[0][2]
        self.assertIn("non ho trovato il pacchetto .deb", msg)
        mock_open.assert_called_once()
        opened_url = mock_open.call_args[0][0].toString()
        self.assertIn("releases/tag/v99.0.0", opened_url)

    @patch("gdlex_ocr.gui._fetch_latest_release_info", side_effect=OSError("no net"))
    @patch("gdlex_ocr.gui.QMessageBox.information")
    def test_network_error_shows_fallback(
        self, mock_info: MagicMock, mock_fetch: MagicMock
    ) -> None:
        action = self._find_update_action()
        assert action is not None
        action.trigger()
        mock_info.assert_called_once()
        msg = mock_info.call_args[0][2]
        self.assertIn("Impossibile controllare", msg)
        self.assertIn("releases/latest", msg)

    @patch("gdlex_ocr.gui._fetch_latest_release_info")
    @patch("gdlex_ocr.gui.QMessageBox.information")
    def test_empty_tag_name_shows_fallback(
        self, mock_info: MagicMock, mock_fetch: MagicMock
    ) -> None:
        mock_fetch.return_value = {"tag_name": "", "assets": []}
        action = self._find_update_action()
        assert action is not None
        action.trigger()
        mock_info.assert_called_once()
        msg = mock_info.call_args[0][2]
        self.assertIn("Impossibile controllare", msg)

    @patch("gdlex_ocr.gui.QDesktopServices.openUrl", return_value=True)
    @patch("gdlex_ocr.gui._fetch_latest_release_info")
    @patch(
        "gdlex_ocr.gui.QMessageBox.question",
        return_value=QMessageBox.StandardButton.No,
    )
    def test_user_declines_does_not_open_browser(
        self,
        mock_question: MagicMock,
        mock_fetch: MagicMock,
        mock_open: MagicMock,
    ) -> None:
        mock_fetch.return_value = _fake_release("99.0.0")
        action = self._find_update_action()
        assert action is not None
        action.trigger()
        mock_question.assert_called_once()
        mock_open.assert_not_called()


if __name__ == "__main__":
    unittest.main()
