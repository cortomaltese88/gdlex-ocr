"""PySide6 interface for GD LEX OCR."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QSettings, QThread, QTimer, Qt, QUrl, Signal
from PySide6.QtGui import (
    QAction,
    QActionGroup,
    QCloseEvent,
    QDesktopServices,
    QFontDatabase,
    QIcon,
    QIntValidator,
)
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFileIconProvider,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenu,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QSystemTrayIcon,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from gdlex_ocr.casefile import analyze_case_folder
from gdlex_ocr.casefile_export import (
    casefile_analysis_to_dict,
    default_casefile_csv_path,
    default_casefile_json_path,
    default_casefile_markdown_path,
    write_casefile_analysis_csv,
    write_casefile_analysis_json,
    write_casefile_analysis_markdown,
)
from gdlex_ocr.icons import tray_icon
from gdlex_ocr.manifest import (
    format_manifest_verification,
    load_manifest,
    verify_manifest_outputs,
)
from gdlex_ocr.ocr_backends import detect_ocr_backend
from gdlex_ocr.output_layout import LOG_FILENAME, MANIFEST_FILENAME
from gdlex_ocr.pdf_splitter import PdfSplitError, count_pdf_pages
from gdlex_ocr.profiles import DEFAULT_PROFILE, PROFILE_NAMES, PROFILES
from gdlex_ocr.searchable_pdf import (
    DEFAULT_OCRMYPDF_TIMEOUT_SECONDS,
    validate_ocrmypdf_jobs,
    validate_ocrmypdf_timeout_seconds,
)
from gdlex_ocr.theme import (
    AVAILABLE_THEMES,
    apply_theme,
    load_theme_name,
    save_theme_name,
)
from gdlex_ocr.tray import GdlexOcrTray
from gdlex_ocr.version import (
    APP_NAME,
    APP_SUBTITLE,
    APP_VERSION_LABEL,
)
from gdlex_ocr.worker import OcrWorker

_OCR_LANGUAGES = [
    ("Italiano", "ita"),
    ("Italiano + Inglese", "ita+eng"),
    ("Inglese", "eng"),
    ("Spagnolo", "spa"),
    ("Francese", "fra"),
    ("Tedesco", "deu"),
]
_OCR_BACKENDS = [
    ("Automatico (OCRmyPDF)", "auto"),
    ("OCRmyPDF", "ocrmypdf"),
    ("Comando esterno", "external"),
]
_SETTINGS_ORGANIZATION = "GD LEX"
_ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"
_FOLDER_ICON_PATH = _ASSETS_DIR / "folder-matrix.svg"
_SETTINGS_KEYS = {
    "output_dir": "paths/outputDirectory",
    "profile": "processing/profile",
    "block_size": "processing/blockSize",
    "create_searchable": "pdf/createSearchable",
    "use_searchable_as_source": "pdf/useSearchableAsSource",
    "structured_output": "output/structuredJobDirectory",
    "analyze_judgment_after_conversion": "judgment/analyzeAfterConversion",
    "ocr_language": "ocr/language",
    "ocr_backend": "ocr/backend",
    "ocr_timeout": "ocr/timeoutSeconds",
    "ocr_jobs": "ocr/jobs",
    "external_ocr_command": "ocr/externalCommand",
}


class _ThemedFileIconProvider(QFileIconProvider):
    """Use the GD LEX folder icon while keeping system icons for other files."""

    def __init__(self) -> None:
        super().__init__()
        self._folder_icon = QIcon(str(_FOLDER_ICON_PATH))

    def icon(self, file_info_or_type):  # type: ignore[override]
        if not self._folder_icon.isNull():
            if file_info_or_type == QFileIconProvider.IconType.Folder:
                return self._folder_icon
            if hasattr(file_info_or_type, "isDir") and file_info_or_type.isDir():
                return self._folder_icon
        return super().icon(file_info_or_type)


def _tray_enabled() -> bool:
    if os.environ.get("GDLEX_OCR_DISABLE_TRAY") == "1":
        return False
    app = QApplication.instance()
    if app is not None and app.platformName().lower() == "offscreen":
        return False
    return True


def _themed_file_dialog(
    parent: QWidget,
    title: str,
    start_dir: str,
    file_mode: QFileDialog.FileMode,
    name_filter: str = "",
    options: QFileDialog.Option = QFileDialog.Option(0),
) -> QFileDialog:
    dialog = QFileDialog(parent, title, start_dir, name_filter)
    dialog.setOption(QFileDialog.Option.DontUseNativeDialog, True)
    dialog.setOptions(dialog.options() | options)
    dialog.setFileMode(file_mode)
    provider = _ThemedFileIconProvider()
    dialog.setIconProvider(provider)
    dialog._gdlex_icon_provider = provider  # type: ignore[attr-defined]
    return dialog


def resolve_output_path(value: str) -> Path:
    """Expand and validate an output path entered by the user."""
    raw_path = value.strip()
    if not raw_path:
        raise ValueError("La cartella di output non può essere vuota.")
    return Path(os.path.expanduser(os.path.expandvars(raw_path)))


def resolve_pdf_path(value: str) -> Path:
    """Expand a PDF path entered by the user."""
    raw_path = value.strip()
    if not raw_path:
        raise ValueError("Il percorso del file PDF non può essere vuoto.")
    return Path(os.path.expanduser(os.path.expandvars(raw_path)))


@dataclass(frozen=True, slots=True)
class CasefileGuiResult:
    """Summary returned by a casefile analysis run."""

    json_path: Path
    markdown_path: Path
    csv_path: Path
    total_files: int
    total_pdf_files: int
    total_indexes: int
    total_index_matches: int
    total_units: int
    total_warnings: int


def run_casefile_analysis(input_dir: Path, output_dir: Path) -> CasefileGuiResult:
    """Run a full casefile analysis and write JSON, Markdown, and CSV output."""
    analysis = analyze_case_folder(input_dir)
    json_path = default_casefile_json_path(output_dir)
    md_path = default_casefile_markdown_path(output_dir)
    csv_path = default_casefile_csv_path(output_dir)
    write_casefile_analysis_json(analysis, json_path)
    write_casefile_analysis_markdown(analysis, md_path)
    write_casefile_analysis_csv(analysis, csv_path)
    payload = casefile_analysis_to_dict(analysis)
    summary = payload["summary"]
    return CasefileGuiResult(
        json_path=json_path,
        markdown_path=md_path,
        csv_path=csv_path,
        total_files=summary["total_files"],
        total_pdf_files=summary["total_pdf_files"],
        total_indexes=summary["total_indexes"],
        total_index_matches=summary["total_index_matches"],
        total_units=summary["total_units"],
        total_warnings=summary["total_warnings"],
    )


class CasefileWorker(QThread):
    """Background thread for casefile folder analysis."""

    completed = Signal(object)
    failed = Signal(str)

    def __init__(self, input_dir: Path, output_dir: Path, parent=None) -> None:
        super().__init__(parent)
        self.input_dir = input_dir
        self.output_dir = output_dir

    def run(self) -> None:
        try:
            result = run_casefile_analysis(self.input_dir, self.output_dir)
            self.completed.emit(result)
        except Exception as exc:
            self.failed.emit(str(exc))


class AboutDialog(QDialog):
    """Application credits and local-processing information."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"Informazioni su {APP_NAME}")
        self.setModal(True)
        self.setMinimumWidth(520)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 26, 30, 22)
        layout.setSpacing(10)

        title = QLabel(APP_NAME)
        title.setObjectName("aboutTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        version = QLabel(f"Versione {APP_VERSION_LABEL}")
        version.setObjectName("aboutVersion")
        version.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(version)

        subtitle = QLabel(APP_SUBTITLE)
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitle)
        layout.addSpacing(6)

        details = QLabel(
            "<b>© 2026 Studio GD LEX - Avv. Marco Gianese</b><br><br>"
            "<b>Licenza progetto:</b> MIT<br>"
            "<b>Componenti terzi:</b> vedere THIRD_PARTY_NOTICES.md<br>"
            "<b>Motore documentale:</b> Docling<br>"
            "<b>GUI:</b> PySide6<br>"
            "<b>OCR/PDF:</b> Docling / RapidOCR<br>"
            "<b>PDF ricercabile (opzionale):</b> OCRmyPDF / backend locale "
            "configurato<br><br>"
            "<b>Privacy:</b> elaborazione locale; nessun upload cloud "
            "effettuato dall'applicazione."
        )
        details.setObjectName("aboutDetails")
        details.setAlignment(Qt.AlignmentFlag.AlignLeft)
        details.setWordWrap(True)
        layout.addWidget(details)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)


class MainWindow(QMainWindow):
    def __init__(
        self,
        settings: QSettings | None = None,
        *,
        ocr_timeout_seconds: int = DEFAULT_OCRMYPDF_TIMEOUT_SECONDS,
        ocr_jobs: int | None = None,
    ) -> None:
        super().__init__()
        self._worker: OcrWorker | None = None
        self._casefile_worker: CasefileWorker | None = None
        self._settings = settings if settings is not None else self._default_settings()
        self._ocr_timeout_seconds = validate_ocrmypdf_timeout_seconds(
            ocr_timeout_seconds
        )
        self._ocr_jobs = validate_ocrmypdf_jobs(ocr_jobs)
        self._loading_settings = False
        self._close_after_cancel = False
        self._tray_real_quit_requested = False
        self.tray: GdlexOcrTray | None = None
        self._final_markdown_path: str | None = None
        self._searchable_pdf_path: str | None = None
        self._manifest_path: str | None = None
        self._log_path: str | None = None
        self._job_output_dir: str | None = None
        self._create_searchable_requested = False
        self._output_path_customized = False
        self._theme_actions: dict[str, QAction] = {}

        self.setWindowTitle(f"{APP_NAME} {APP_VERSION_LABEL}")
        app = QApplication.instance()
        if app is not None and not app.windowIcon().isNull():
            self.setWindowIcon(app.windowIcon())
        self.setMinimumSize(1020, 900)
        self.resize(1100, 920)
        self._build_menu_bar()

        central = QWidget(self)
        central.setObjectName("mainCanvas")
        self.setCentralWidget(central)
        canvas_layout = QVBoxLayout(central)
        canvas_layout.setContentsMargins(12, 12, 12, 12)
        canvas_layout.setSpacing(0)

        app_shell = QFrame()
        app_shell.setObjectName("appShell")
        canvas_layout.addWidget(app_shell)

        root_layout = QVBoxLayout(app_shell)
        root_layout.setContentsMargins(18, 14, 18, 12)
        root_layout.setSpacing(8)

        header = QFrame()
        header.setObjectName("headerFrame")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(22, 12, 18, 12)
        header_layout.setSpacing(18)

        identity_layout = QVBoxLayout()
        identity_layout.setSpacing(1)
        eyebrow = QLabel("GD LEX / LOCAL DOCUMENT INTELLIGENCE")
        eyebrow.setObjectName("headerEyebrow")
        identity_layout.addWidget(eyebrow)
        title = QLabel(APP_NAME)
        title.setObjectName("appTitle")
        identity_layout.addWidget(title)
        subtitle = QLabel(APP_SUBTITLE)
        subtitle.setObjectName("appSubtitle")
        identity_layout.addWidget(subtitle)
        header_layout.addLayout(identity_layout, 1)

        header_divider = QFrame()
        header_divider.setObjectName("headerDivider")
        header_divider.setFrameShape(QFrame.Shape.VLine)
        header_layout.addWidget(header_divider)

        release_layout = QVBoxLayout()
        release_layout.setSpacing(5)
        release_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        version = QLabel(APP_VERSION_LABEL)
        version.setObjectName("versionBadge")
        version.setAlignment(Qt.AlignmentFlag.AlignCenter)
        release_layout.addWidget(version)
        local_status = QLabel("LOCAL / OFFLINE")
        local_status.setObjectName("headerMeta")
        local_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        release_layout.addWidget(local_status)
        header_layout.addLayout(release_layout)
        root_layout.addWidget(header)

        # === Main tab widget ===
        self.main_tabs = QTabWidget()
        self.main_tabs.setObjectName("mainTabs")
        root_layout.addWidget(self.main_tabs, 1)

        # ----------------------------------------------------------
        # Tab: OCR documento
        # ----------------------------------------------------------
        self.ocr_tab = QWidget()
        self.ocr_tab.setObjectName("ocrTab")
        ocr_scroll = QScrollArea()
        ocr_scroll.setWidgetResizable(True)
        ocr_scroll.setFrameShape(QFrame.Shape.NoFrame)
        ocr_scroll.setWidget(self.ocr_tab)
        self.main_tabs.addTab(ocr_scroll, "OCR documento")

        ocr_layout = QVBoxLayout(self.ocr_tab)
        ocr_layout.setContentsMargins(0, 6, 0, 0)
        ocr_layout.setSpacing(8)

        source_group = QGroupBox("Documento e destinazione")
        source_group.setMinimumHeight(118)
        source_layout = QGridLayout(source_group)
        source_layout.setContentsMargins(18, 14, 18, 14)
        source_layout.setHorizontalSpacing(14)
        source_layout.setVerticalSpacing(12)
        source_layout.setColumnMinimumWidth(0, 150)
        source_layout.setColumnStretch(1, 1)
        source_layout.setRowMinimumHeight(0, 38)
        source_layout.setRowMinimumHeight(1, 38)

        self.pdf_edit = QLineEdit()
        self.pdf_edit.setMinimumHeight(36)
        self.pdf_edit.setPlaceholderText(
            "Inserisci o incolla un file PDF (anche con ~ o variabili ambiente)"
        )
        self.pdf_edit.textEdited.connect(self._on_pdf_text_edited)
        self.pdf_edit.editingFinished.connect(self._update_pdf_page_count)
        self.pdf_button = QPushButton("Sfoglia PDF")
        self.pdf_button.setMinimumWidth(150)
        self.pdf_button.setMinimumHeight(36)
        self.pdf_button.clicked.connect(self._select_pdf)
        pdf_label = QLabel("File PDF")
        pdf_label.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        source_layout.addWidget(pdf_label, 0, 0)
        source_layout.addWidget(self.pdf_edit, 0, 1)
        source_layout.addWidget(self.pdf_button, 0, 2)

        self.output_edit = QLineEdit()
        self.output_edit.setMinimumHeight(36)
        self.output_edit.setPlaceholderText(
            "Inserisci o incolla una cartella (anche con ~ o variabili ambiente)"
        )
        self.output_edit.textEdited.connect(self._on_output_text_edited)
        self.output_button = QPushButton("Sfoglia cartella")
        self.output_button.setMinimumWidth(150)
        self.output_button.setMinimumHeight(36)
        self.output_button.clicked.connect(self._select_output)
        output_label = QLabel("Cartella output")
        output_label.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        source_layout.addWidget(output_label, 1, 0)
        source_layout.addWidget(self.output_edit, 1, 1)
        source_layout.addWidget(self.output_button, 1, 2)
        ocr_layout.addWidget(source_group)

        # --- Opzioni OCR ---
        options_group = QGroupBox("Opzioni OCR")
        options_layout = QGridLayout(options_group)
        options_layout.setContentsMargins(18, 10, 18, 10)
        options_layout.setHorizontalSpacing(14)
        options_layout.setVerticalSpacing(8)
        options_layout.setColumnMinimumWidth(0, 150)
        options_layout.setColumnMinimumWidth(1, 220)
        options_layout.setColumnStretch(2, 1)

        profile_label = QLabel("Profilo elaborazione")
        profile_label.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        options_layout.addWidget(profile_label, 0, 0)
        self.profile_combo = QComboBox()
        self.profile_combo.addItems(PROFILE_NAMES)
        self.profile_combo.setCurrentText(DEFAULT_PROFILE)
        self.profile_combo.setMinimumWidth(220)
        self.profile_combo.currentTextChanged.connect(self._on_profile_changed)
        options_layout.addWidget(self.profile_combo, 0, 1)
        self.profile_summary_label = QLabel()
        self.profile_summary_label.setObjectName("sectionHint")
        options_layout.addWidget(self.profile_summary_label, 0, 2, 1, 2)

        block_label = QLabel("Dimensione blocco")
        block_label.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        options_layout.addWidget(block_label, 1, 0)
        self.block_size_spin = QSpinBox()
        self.block_size_spin.setRange(1, 500)
        self.block_size_spin.setSuffix(" pagine")
        self.block_size_spin.setMinimumWidth(180)
        options_layout.addWidget(self.block_size_spin, 1, 1)

        document_info = QHBoxLayout()
        document_info.setSpacing(8)
        pages_caption = QLabel("Documento")
        pages_caption.setObjectName("sectionHint")
        document_info.addWidget(pages_caption)
        self.page_count_label = QLabel("Nessun PDF selezionato")
        document_info.addWidget(self.page_count_label)
        document_info.addStretch(1)
        options_layout.addLayout(document_info, 1, 2)

        local_note = QLabel("Elaborazione locale · nessun upload cloud")
        local_note.setObjectName("sectionHint")
        local_note.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        options_layout.addWidget(local_note, 1, 3)
        ocr_layout.addWidget(options_group)

        self._on_profile_changed(DEFAULT_PROFILE)

        # --- PDF ricercabile e organizzazione output ---
        self.pdf_output_group = QGroupBox("PDF e output")
        self.pdf_output_group.setObjectName("pdfOutputGroup")
        self.pdf_output_group.setMinimumHeight(150)
        pdf_output_layout = QVBoxLayout(self.pdf_output_group)
        pdf_output_layout.setContentsMargins(10, 6, 10, 6)
        pdf_output_layout.setSpacing(0)

        self.pdf_output_tabs = QTabWidget()
        self.pdf_output_tabs.setObjectName("pdfOutputTabs")
        self.pdf_output_tabs.setMinimumHeight(140)
        pdf_output_layout.addWidget(self.pdf_output_tabs)

        self.pdf_output_base_tab = QWidget()
        base_layout = QGridLayout(self.pdf_output_base_tab)
        base_layout.setContentsMargins(10, 4, 10, 4)
        base_layout.setHorizontalSpacing(12)
        base_layout.setVerticalSpacing(1)
        base_layout.setColumnStretch(0, 1)
        base_layout.setColumnStretch(2, 1)

        self.searchable_checkbox = QCheckBox("Crea PDF ricercabile OCR")
        self.searchable_checkbox.setChecked(False)
        self.searchable_checkbox.toggled.connect(self._on_searchable_changed)
        base_layout.addWidget(self.searchable_checkbox, 0, 0)

        self.ocr_language_label = QLabel("Lingua OCR:")
        self.ocr_language_label.setObjectName("sectionHint")
        self.ocr_language_label.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        base_layout.addWidget(self.ocr_language_label, 0, 1)
        self.ocr_language_combo = QComboBox()
        for display, code in _OCR_LANGUAGES:
            self.ocr_language_combo.addItem(display, userData=code)
        self.ocr_language_combo.setCurrentIndex(0)
        self.ocr_language_combo.setEnabled(False)
        self.ocr_language_combo.setMinimumWidth(220)
        base_layout.addWidget(self.ocr_language_combo, 0, 2)

        self.use_searchable_as_source_checkbox = QCheckBox(
            "Usa il PDF ricercabile come sorgente Docling"
        )
        self.use_searchable_as_source_checkbox.setChecked(False)
        self.use_searchable_as_source_checkbox.setEnabled(False)
        self.use_searchable_as_source_checkbox.setToolTip(
            "Utile con Accurato testo o con un backend esterno configurato."
        )
        base_layout.addWidget(self.use_searchable_as_source_checkbox, 1, 0)

        self.structured_output_checkbox = QCheckBox(
            "Crea cartella fascicolo per ogni elaborazione"
        )
        self.structured_output_checkbox.setChecked(False)
        self.structured_output_checkbox.setToolTip(
            "Organizza Markdown, log, manifest e PDF ricercabile "
            "in una sottocartella dedicata."
        )
        base_layout.addWidget(self.structured_output_checkbox, 1, 1, 1, 2)

        self.judgment_analysis_checkbox = QCheckBox(
            "Analisi sentenza per impugnazione"
        )
        self.judgment_analysis_checkbox.setObjectName("judgmentAnalysisCheckbox")
        self.judgment_analysis_checkbox.setChecked(False)
        self.judgment_analysis_checkbox.setToolTip(
            "Genera una scheda sentenza locale (sentenza_analysis.md) e "
            "metadati nel manifest. Non calcola termini definitivi di "
            "impugnazione."
        )
        base_layout.addWidget(self.judgment_analysis_checkbox, 2, 0, 1, 3)
        self.pdf_output_tabs.addTab(self.pdf_output_base_tab, "Base")

        self.pdf_output_backend_tab = QWidget()
        backend_layout = QGridLayout(self.pdf_output_backend_tab)
        backend_layout.setContentsMargins(10, 8, 10, 10)
        backend_layout.setHorizontalSpacing(12)
        backend_layout.setVerticalSpacing(6)
        backend_layout.setColumnMinimumWidth(0, 150)
        backend_layout.setColumnMinimumWidth(2, 120)
        backend_layout.setColumnStretch(1, 0)
        backend_layout.setColumnStretch(3, 1)

        self.ocr_backend_label = QLabel("Backend OCR:")
        self.ocr_backend_label.setObjectName("sectionHint")
        backend_layout.addWidget(self.ocr_backend_label, 0, 0)
        self.ocr_backend_combo = QComboBox()
        for display, backend_name in _OCR_BACKENDS:
            self.ocr_backend_combo.addItem(display, userData=backend_name)
        self.ocr_backend_combo.currentIndexChanged.connect(
            self._on_ocr_backend_changed
        )
        self.ocr_backend_combo.setEnabled(False)
        self.ocr_backend_combo.setToolTip(
            "Utile con Accurato testo o con un backend esterno configurato."
        )
        backend_layout.addWidget(self.ocr_backend_combo, 0, 1, 1, 3)

        self.ocr_timeout_label = QLabel("Timeout OCRmyPDF:")
        self.ocr_timeout_label.setObjectName("sectionHint")
        backend_layout.addWidget(self.ocr_timeout_label, 1, 0)
        self.ocr_timeout_spin = QSpinBox()
        self.ocr_timeout_spin.setRange(1, 86400)
        self.ocr_timeout_spin.setSuffix(" s")
        self.ocr_timeout_spin.setValue(self._ocr_timeout_seconds)
        self.ocr_timeout_spin.setToolTip(
            "Tempo massimo concesso a OCRmyPDF. Default: 1800 secondi."
        )
        self.ocr_timeout_spin.setEnabled(False)
        backend_layout.addWidget(self.ocr_timeout_spin, 1, 1)

        self.ocr_jobs_label = QLabel("Jobs OCRmyPDF:")
        self.ocr_jobs_label.setObjectName("sectionHint")
        backend_layout.addWidget(self.ocr_jobs_label, 1, 2)
        self.ocr_jobs_edit = QLineEdit()
        self.ocr_jobs_edit.setValidator(QIntValidator(1, 9999, self.ocr_jobs_edit))
        self.ocr_jobs_edit.setPlaceholderText("Automatico")
        if self._ocr_jobs is not None:
            self.ocr_jobs_edit.setText(str(self._ocr_jobs))
        self.ocr_jobs_edit.setToolTip(
            "Lascia vuoto per usare il comportamento predefinito di OCRmyPDF."
        )
        self.ocr_jobs_edit.setEnabled(False)
        backend_layout.addWidget(self.ocr_jobs_edit, 1, 3)

        self.external_ocr_command_label = QLabel("Comando esterno:")
        self.external_ocr_command_label.setObjectName("sectionHint")
        backend_layout.addWidget(self.external_ocr_command_label, 2, 0)
        self.external_ocr_command_edit = QLineEdit()
        self.external_ocr_command_edit.setPlaceholderText(
            "tool --input {input} --output {output} --lang {language}"
        )
        self.external_ocr_command_edit.setToolTip(
            "Comando locale senza shell; richiede {input} e {output}."
        )
        self.external_ocr_command_edit.setEnabled(False)
        backend_layout.addWidget(self.external_ocr_command_edit, 2, 1, 1, 3)
        self.pdf_output_tabs.addTab(
            self.pdf_output_backend_tab,
            "Backend OCR",
        )
        ocr_layout.addWidget(self.pdf_output_group)

        # --- Avanzamento ---
        self.progress_group = QGroupBox("Avanzamento")
        progress_layout = QVBoxLayout(self.progress_group)
        progress_layout.setContentsMargins(18, 12, 18, 10)
        progress_layout.setSpacing(8)

        progress_info_row = QHBoxLayout()
        self.status_label = QLabel("Pronto")
        self.status_label.setObjectName("statusLabel")
        progress_info_row.addWidget(self.status_label, 1)
        self.eta_label = QLabel("ETA: --")
        self.eta_label.setObjectName("etaLabel")
        self.eta_label.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        self.eta_label.setMinimumWidth(210)
        progress_info_row.addWidget(self.eta_label)
        progress_layout.addLayout(progress_info_row)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("%p%")
        progress_layout.addWidget(self.progress_bar)
        ocr_layout.addWidget(self.progress_group)

        log_group = QGroupBox("Log elaborazione")
        log_layout = QVBoxLayout(log_group)
        log_layout.setContentsMargins(12, 12, 12, 10)
        self.log_view = QTextEdit()
        self.log_view.setObjectName("logView")
        self.log_view.setReadOnly(True)
        self.log_view.setPlaceholderText("Il log dell'elaborazione apparirà qui.")
        self.log_view.document().setMaximumBlockCount(5000)
        monospace_font = QFontDatabase.systemFont(
            QFontDatabase.SystemFont.FixedFont
        )
        monospace_font.setPointSize(9)
        self.log_view.setFont(monospace_font)
        log_layout.addWidget(self.log_view)
        ocr_layout.addWidget(log_group, 1)

        actions_layout = QVBoxLayout()
        actions_layout.setSpacing(8)

        output_buttons_row = QHBoxLayout()
        output_buttons_row.setSpacing(10)

        self.open_folder_button = QPushButton("Apri cartella output")
        self.open_folder_button.setEnabled(False)
        self.open_folder_button.clicked.connect(self._open_output_folder)
        output_buttons_row.addWidget(self.open_folder_button)

        self.open_markdown_button = QPushButton("Apri Markdown")
        self.open_markdown_button.setEnabled(False)
        self.open_markdown_button.clicked.connect(self._open_markdown)
        output_buttons_row.addWidget(self.open_markdown_button)

        self.open_pdf_button = QPushButton("Apri PDF OCR")
        self.open_pdf_button.setEnabled(False)
        self.open_pdf_button.clicked.connect(self._open_searchable_pdf)
        output_buttons_row.addWidget(self.open_pdf_button)

        self.open_manifest_button = QPushButton("Apri manifest")
        self.open_manifest_button.setEnabled(False)
        self.open_manifest_button.clicked.connect(self._open_manifest)
        output_buttons_row.addWidget(self.open_manifest_button)

        self.open_log_button = QPushButton("Apri log")
        self.open_log_button.setEnabled(False)
        self.open_log_button.clicked.connect(self._open_log)
        output_buttons_row.addWidget(self.open_log_button)

        self.verify_outputs_button = QPushButton("Verifica output")
        self.verify_outputs_button.setEnabled(False)
        self.verify_outputs_button.clicked.connect(self._verify_outputs)
        output_buttons_row.addWidget(self.verify_outputs_button)

        actions_layout.addLayout(output_buttons_row)

        run_buttons_row = QHBoxLayout()
        run_buttons_row.setSpacing(10)
        run_buttons_row.addStretch(1)

        self.start_button = QPushButton("Avvia")
        self.start_button.setObjectName("primaryButton")
        self.start_button.setDefault(True)
        self.start_button.clicked.connect(self._start)
        run_buttons_row.addWidget(self.start_button)

        self.cancel_button = QPushButton("Annulla")
        self.cancel_button.setObjectName("cancelButton")
        self.cancel_button.setEnabled(False)
        self.cancel_button.clicked.connect(self._cancel)
        run_buttons_row.addWidget(self.cancel_button)

        actions_layout.addLayout(run_buttons_row)
        ocr_layout.addLayout(actions_layout)

        # ----------------------------------------------------------
        # Tab: Fascicolo
        # ----------------------------------------------------------
        self.casefile_tab = QWidget()
        self.casefile_tab.setObjectName("casefileTab")
        casefile_scroll = QScrollArea()
        casefile_scroll.setWidgetResizable(True)
        casefile_scroll.setFrameShape(QFrame.Shape.NoFrame)
        casefile_scroll.setWidget(self.casefile_tab)
        self.main_tabs.addTab(casefile_scroll, "Fascicolo")

        casefile_tab_layout = QVBoxLayout(self.casefile_tab)
        casefile_tab_layout.setContentsMargins(0, 6, 0, 0)
        casefile_tab_layout.setSpacing(8)

        casefile_group = QGroupBox("Fascicolo PDP/TIAP")
        casefile_layout = QGridLayout(casefile_group)
        casefile_layout.setContentsMargins(18, 14, 18, 14)
        casefile_layout.setHorizontalSpacing(14)
        casefile_layout.setVerticalSpacing(12)
        casefile_layout.setColumnMinimumWidth(0, 150)
        casefile_layout.setColumnStretch(1, 1)
        casefile_layout.setRowMinimumHeight(0, 38)
        casefile_layout.setRowMinimumHeight(1, 38)

        self.casefile_input_edit = QLineEdit()
        self.casefile_input_edit.setObjectName("casefileInputEdit")
        self.casefile_input_edit.setMinimumHeight(36)
        self.casefile_input_edit.setPlaceholderText(
            "Cartella del fascicolo da analizzare"
        )
        self.casefile_input_button = QPushButton("Sfoglia…")
        self.casefile_input_button.setMinimumWidth(150)
        self.casefile_input_button.setMinimumHeight(36)
        self.casefile_input_button.clicked.connect(self._select_casefile_input)
        casefile_input_label = QLabel("Cartella fascicolo")
        casefile_input_label.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        casefile_layout.addWidget(casefile_input_label, 0, 0)
        casefile_layout.addWidget(self.casefile_input_edit, 0, 1)
        casefile_layout.addWidget(self.casefile_input_button, 0, 2)

        self.casefile_output_edit = QLineEdit()
        self.casefile_output_edit.setObjectName("casefileOutputEdit")
        self.casefile_output_edit.setMinimumHeight(36)
        self.casefile_output_edit.setPlaceholderText(
            "Cartella di destinazione per i file di indice"
        )
        self.casefile_output_button = QPushButton("Sfoglia…")
        self.casefile_output_button.setMinimumWidth(150)
        self.casefile_output_button.setMinimumHeight(36)
        self.casefile_output_button.clicked.connect(
            self._select_casefile_output
        )
        casefile_output_label = QLabel("Cartella output")
        casefile_output_label.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        casefile_layout.addWidget(casefile_output_label, 1, 0)
        casefile_layout.addWidget(self.casefile_output_edit, 1, 1)
        casefile_layout.addWidget(self.casefile_output_button, 1, 2)

        casefile_note = QLabel(
            "Analisi locale euristica: non esegue OCR e non legge il "
            "contenuto dei PDF. Genera fascicolo_index.json, "
            "fascicolo_index.md e fascicolo_index.csv."
        )
        casefile_note.setObjectName("sectionHint")
        casefile_note.setWordWrap(True)
        casefile_layout.addWidget(casefile_note, 2, 0, 1, 2)

        self.casefile_start_button = QPushButton("Analizza fascicolo")
        self.casefile_start_button.setObjectName("casefileAnalyzeButton")
        self.casefile_start_button.setMinimumHeight(36)
        self.casefile_start_button.clicked.connect(
            self._start_casefile_analysis
        )
        casefile_layout.addWidget(self.casefile_start_button, 2, 2)
        casefile_tab_layout.addWidget(casefile_group)

        # --- Casefile log ---
        casefile_log_group = QGroupBox("Log fascicolo")
        casefile_log_layout = QVBoxLayout(casefile_log_group)
        casefile_log_layout.setContentsMargins(12, 12, 12, 10)
        self.casefile_log_view = QTextEdit()
        self.casefile_log_view.setObjectName("casefileLogView")
        self.casefile_log_view.setReadOnly(True)
        self.casefile_log_view.setPlaceholderText(
            "Il log dell'analisi fascicolo apparirà qui."
        )
        self.casefile_log_view.document().setMaximumBlockCount(2000)
        self.casefile_log_view.setFont(monospace_font)
        casefile_log_layout.addWidget(self.casefile_log_view)
        casefile_tab_layout.addWidget(casefile_log_group, 1)

        # --- Casefile output buttons ---
        casefile_buttons_row = QHBoxLayout()
        casefile_buttons_row.setSpacing(10)
        self.casefile_open_folder_button = QPushButton("Apri cartella output")
        self.casefile_open_folder_button.setObjectName(
            "casefileOpenFolderButton"
        )
        self.casefile_open_folder_button.setEnabled(False)
        self.casefile_open_folder_button.clicked.connect(
            self._open_casefile_output_folder
        )
        casefile_buttons_row.addWidget(self.casefile_open_folder_button)

        self.casefile_open_report_button = QPushButton("Apri report Markdown")
        self.casefile_open_report_button.setObjectName(
            "casefileOpenReportButton"
        )
        self.casefile_open_report_button.setEnabled(False)
        self.casefile_open_report_button.clicked.connect(
            self._open_casefile_report
        )
        casefile_buttons_row.addWidget(self.casefile_open_report_button)
        casefile_buttons_row.addStretch(1)
        casefile_tab_layout.addLayout(casefile_buttons_row)

        self._casefile_output_dir: str | None = None
        self._casefile_report_path: str | None = None

        self._load_gui_settings()
        self._connect_settings_persistence()
        self._setup_tray()

    # ------------------------------------------------------------------
    # Menu bar
    # ------------------------------------------------------------------

    def _build_menu_bar(self) -> None:
        self.file_menu = self.menuBar().addMenu("File")
        self.quit_action = QAction("Esci", self)
        self.quit_action.setShortcut("Ctrl+Q")
        self.quit_action.triggered.connect(self.request_close)
        self.file_menu.addAction(self.quit_action)

        view_menu = self.menuBar().addMenu("Visualizza")
        theme_menu = QMenu("Tema", self)
        view_menu.addMenu(theme_menu)

        self._theme_action_group = QActionGroup(self)
        self._theme_action_group.setExclusive(True)
        current_theme = load_theme_name()
        for name in AVAILABLE_THEMES:
            action = QAction(name, self)
            action.setCheckable(True)
            action.setChecked(name == current_theme)
            action.triggered.connect(
                lambda checked, theme_name=name: self._apply_theme(theme_name)
            )
            self._theme_action_group.addAction(action)
            theme_menu.addAction(action)
            self._theme_actions[name] = action

        help_menu = self.menuBar().addMenu("Aiuto")
        about_action = QAction(f"Informazioni su {APP_NAME}...", self)
        about_action.setShortcut("F1")
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

    def _apply_theme(self, name: str) -> None:
        app = QApplication.instance()
        if app is None:
            return
        apply_theme(app, name)
        save_theme_name(name)
        for theme_name, action in self._theme_actions.items():
            action.setChecked(theme_name == name)
        self.status_label.setText(f"Tema applicato: {name}")

    def _show_about(self) -> None:
        AboutDialog(self).exec()

    # ------------------------------------------------------------------
    # GUI settings
    # ------------------------------------------------------------------

    def _default_settings(self) -> QSettings | None:
        app = QApplication.instance()
        if (
            app is None
            or app.organizationName() != _SETTINGS_ORGANIZATION
            or app.applicationName() != APP_NAME
        ):
            return None
        return QSettings()

    def _settings_text(self, key: str, default: str = "") -> str:
        if self._settings is None:
            return default
        value = self._settings.value(key, default)
        if value is None:
            return default
        return str(value)

    def _settings_bool(self, key: str, default: bool = False) -> bool:
        if self._settings is None:
            return default
        value = self._settings.value(key, default)
        if isinstance(value, bool):
            return value
        if value is None:
            return default
        normalized = str(value).strip().lower()
        if normalized in {"1", "true", "yes", "on"}:
            return True
        if normalized in {"0", "false", "no", "off"}:
            return False
        return default

    def _settings_int(self, key: str, default: int) -> int:
        if self._settings is None:
            return default
        value = self._settings.value(key, default)
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    def _settings_positive_int(self, key: str, default: int) -> int:
        value = self._settings_int(key, default)
        if value <= 0:
            return default
        return value

    def _settings_optional_positive_int(
        self,
        key: str,
        default: int | None = None,
    ) -> int | None:
        if self._settings is None or not self._settings.contains(key):
            return default
        value = self._settings.value(key)
        if value in (None, ""):
            return None
        try:
            parsed = int(value)
        except (TypeError, ValueError):
            return default
        if parsed <= 0:
            return default
        return parsed

    def _current_ocr_jobs(self) -> int | None:
        raw_value = self.ocr_jobs_edit.text().strip()
        if not raw_value:
            return None
        try:
            jobs = int(raw_value)
        except ValueError:
            return None
        try:
            return validate_ocrmypdf_jobs(jobs)
        except ValueError:
            return None

    def _update_ocr_runtime_options(self, *args: object) -> None:
        self._ocr_timeout_seconds = validate_ocrmypdf_timeout_seconds(
            self.ocr_timeout_spin.value()
        )
        self._ocr_jobs = self._current_ocr_jobs()
        self._save_gui_settings()

    def _set_combo_data(self, combo: QComboBox, value: str) -> None:
        if not value:
            return
        index = combo.findData(value)
        if index >= 0:
            combo.setCurrentIndex(index)

    def _load_gui_settings(self) -> None:
        if self._settings is None:
            return
        self._loading_settings = True
        try:
            output_dir = self._settings_text(_SETTINGS_KEYS["output_dir"]).strip()
            if output_dir:
                self.output_edit.setText(output_dir)
                self._output_path_customized = True

            profile = self._settings_text(_SETTINGS_KEYS["profile"])
            if profile in PROFILES:
                self.profile_combo.setCurrentText(profile)

            self.block_size_spin.setValue(
                self._settings_int(
                    _SETTINGS_KEYS["block_size"],
                    self.block_size_spin.value(),
                )
            )
            self.searchable_checkbox.setChecked(
                self._settings_bool(
                    _SETTINGS_KEYS["create_searchable"],
                    self.searchable_checkbox.isChecked(),
                )
            )
            self.use_searchable_as_source_checkbox.setChecked(
                self._settings_bool(
                    _SETTINGS_KEYS["use_searchable_as_source"],
                    self.use_searchable_as_source_checkbox.isChecked(),
                )
            )
            self.structured_output_checkbox.setChecked(
                self._settings_bool(
                    _SETTINGS_KEYS["structured_output"],
                    self.structured_output_checkbox.isChecked(),
                )
            )
            self.judgment_analysis_checkbox.setChecked(
                self._settings_bool(
                    _SETTINGS_KEYS["analyze_judgment_after_conversion"],
                    self.judgment_analysis_checkbox.isChecked(),
                )
            )
            self._set_combo_data(
                self.ocr_language_combo,
                self._settings_text(_SETTINGS_KEYS["ocr_language"]),
            )
            self._set_combo_data(
                self.ocr_backend_combo,
                self._settings_text(_SETTINGS_KEYS["ocr_backend"]),
            )
            self._ocr_timeout_seconds = self._settings_positive_int(
                _SETTINGS_KEYS["ocr_timeout"],
                self._ocr_timeout_seconds,
            )
            self.ocr_timeout_spin.setValue(self._ocr_timeout_seconds)
            self._ocr_jobs = self._settings_optional_positive_int(
                _SETTINGS_KEYS["ocr_jobs"],
                self._ocr_jobs,
            )
            if self._ocr_jobs is None:
                self.ocr_jobs_edit.clear()
            else:
                self.ocr_jobs_edit.setText(str(self._ocr_jobs))
            self.external_ocr_command_edit.setText(
                self._settings_text(_SETTINGS_KEYS["external_ocr_command"])
            )
            self._on_searchable_changed(self.searchable_checkbox.isChecked())
            self._on_ocr_backend_changed()
        finally:
            self._loading_settings = False

    def _connect_settings_persistence(self) -> None:
        self.block_size_spin.valueChanged.connect(self._save_gui_settings)
        self.ocr_language_combo.currentIndexChanged.connect(self._save_gui_settings)
        self.use_searchable_as_source_checkbox.toggled.connect(
            self._save_gui_settings
        )
        self.structured_output_checkbox.toggled.connect(self._save_gui_settings)
        self.judgment_analysis_checkbox.toggled.connect(self._save_gui_settings)
        self.external_ocr_command_edit.textEdited.connect(self._save_gui_settings)
        self.external_ocr_command_edit.editingFinished.connect(
            self._save_gui_settings
        )
        self.ocr_timeout_spin.valueChanged.connect(self._update_ocr_runtime_options)
        self.ocr_jobs_edit.textChanged.connect(self._update_ocr_runtime_options)

    def _save_gui_settings(self, *args: object) -> None:
        if self._settings is None or self._loading_settings:
            return

        output_dir = self.output_edit.text().strip()
        if output_dir and self._output_path_customized:
            self._settings.setValue(_SETTINGS_KEYS["output_dir"], output_dir)
        else:
            self._settings.remove(_SETTINGS_KEYS["output_dir"])

        self._settings.setValue(
            _SETTINGS_KEYS["profile"],
            self.profile_combo.currentText(),
        )
        self._settings.setValue(
            _SETTINGS_KEYS["block_size"],
            self.block_size_spin.value(),
        )
        self._settings.setValue(
            _SETTINGS_KEYS["create_searchable"],
            self.searchable_checkbox.isChecked(),
        )
        self._settings.setValue(
            _SETTINGS_KEYS["use_searchable_as_source"],
            self.use_searchable_as_source_checkbox.isChecked(),
        )
        self._settings.setValue(
            _SETTINGS_KEYS["structured_output"],
            self.structured_output_checkbox.isChecked(),
        )
        self._settings.setValue(
            _SETTINGS_KEYS["analyze_judgment_after_conversion"],
            self.judgment_analysis_checkbox.isChecked(),
        )
        self._settings.setValue(
            _SETTINGS_KEYS["ocr_language"],
            self.ocr_language_combo.currentData() or "ita",
        )
        self._settings.setValue(
            _SETTINGS_KEYS["ocr_backend"],
            self.ocr_backend_combo.currentData() or "auto",
        )
        self._settings.setValue(
            _SETTINGS_KEYS["ocr_timeout"],
            self._ocr_timeout_seconds,
        )
        if self._ocr_jobs is None:
            self._settings.remove(_SETTINGS_KEYS["ocr_jobs"])
        else:
            self._settings.setValue(_SETTINGS_KEYS["ocr_jobs"], self._ocr_jobs)

        external_command = self.external_ocr_command_edit.text().strip()
        if external_command:
            self._settings.setValue(
                _SETTINGS_KEYS["external_ocr_command"],
                external_command,
            )
        else:
            self._settings.remove(_SETTINGS_KEYS["external_ocr_command"])
        self._settings.sync()

    # ------------------------------------------------------------------
    # System tray
    # ------------------------------------------------------------------

    def _setup_tray(self) -> None:
        if not _tray_enabled():
            return
        icon = tray_icon()
        if icon is None:
            return
        self.tray = GdlexOcrTray(
            self,
            icon=icon,
            toggle_window=self._toggle_window_from_tray,
            show_window=self._show_window_from_tray,
            open_output_folder=self._open_output_folder,
            quit_app=self.request_close,
        )
        if self._tray_is_available():
            app = QApplication.instance()
            if app is not None:
                app.setQuitOnLastWindowClosed(False)

    def _tray_is_available(self) -> bool:
        return self.tray is not None and self.tray.is_available()

    def _show_window_from_tray(self) -> None:
        if self.isMinimized():
            self.showNormal()
        elif not self.isVisible():
            self.show()
        self.raise_()
        self.activateWindow()

    def _toggle_window_from_tray(self) -> None:
        if self.isVisible() and not self.isMinimized():
            self.hide()
            return
        self._show_window_from_tray()

    def _cleanup_tray(self) -> None:
        if self.tray is None:
            return
        self.tray.cleanup()
        self.tray = None

    def request_close(self) -> None:
        """Request a real application exit through the shared tray-aware flow."""
        self._quit_from_tray()

    def _quit_from_tray(self) -> None:
        if self._tray_real_quit_requested:
            return
        if self._worker is not None and self._worker.isRunning():
            self._show_window_from_tray()
            answer = QMessageBox.question(
                self,
                "Elaborazione in corso",
                "Annullare l'elaborazione e uscire dall'applicazione?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if answer != QMessageBox.StandardButton.Yes:
                return
            self._tray_real_quit_requested = True
            self._close_after_cancel = True
            self._cancel()
            return

        self._tray_real_quit_requested = True
        self._cleanup_tray()
        app = QApplication.instance()
        if app is not None:
            app.setQuitOnLastWindowClosed(True)
        QTimer.singleShot(0, self.close)
        if app is not None:
            QTimer.singleShot(0, app.quit)

    def _show_tray_message(
        self,
        title: str,
        message: str,
        icon: QSystemTrayIcon.MessageIcon = QSystemTrayIcon.MessageIcon.Information,
    ) -> None:
        if self.tray is not None:
            self.tray.show_message(title, message, icon)

    # ------------------------------------------------------------------
    # Profile / PDF options
    # ------------------------------------------------------------------

    def _on_profile_changed(self, name: str) -> None:
        profile = PROFILES.get(name)
        if profile is None:
            return
        self.block_size_spin.setValue(profile.block_size)
        self.profile_summary_label.setText(profile.summary())
        if not hasattr(self, "searchable_checkbox"):
            return
        self.searchable_checkbox.setChecked(profile.create_searchable_pdf)
        self.use_searchable_as_source_checkbox.setChecked(
            profile.use_searchable_as_source
        )
        self._save_gui_settings()

    def _on_searchable_changed(self, checked: bool) -> None:
        self.ocr_language_combo.setEnabled(checked)
        self.ocr_backend_combo.setEnabled(checked)
        self.ocr_timeout_spin.setEnabled(checked)
        self.ocr_jobs_edit.setEnabled(checked)
        self.use_searchable_as_source_checkbox.setEnabled(checked)
        self._on_ocr_backend_changed()
        self._save_gui_settings()

    def _on_ocr_backend_changed(self) -> None:
        backend = self.ocr_backend_combo.currentData() or "auto"
        self.external_ocr_command_edit.setEnabled(
            self.searchable_checkbox.isChecked() and backend == "external"
        )
        self._save_gui_settings()

    # ------------------------------------------------------------------
    # File / folder selectors
    # ------------------------------------------------------------------

    def _on_output_text_edited(self, text: str) -> None:
        self._output_path_customized = bool(text.strip())
        self._save_gui_settings()

    def _on_pdf_text_edited(self, text: str) -> None:
        if text.strip():
            self.page_count_label.setText("Conteggio pagine all'avvio")
        else:
            self.page_count_label.setText("Nessun PDF selezionato")

    def _update_pdf_page_count(self, show_warning: bool = False) -> bool:
        try:
            pdf_path = resolve_pdf_path(self.pdf_edit.text())
        except ValueError:
            self.page_count_label.setText("Nessun PDF selezionato")
            return False

        if not pdf_path.is_file():
            self.page_count_label.setText("PDF non trovato")
            return False
        if pdf_path.suffix.lower() != ".pdf":
            self.page_count_label.setText("Formato non PDF")
            return False

        try:
            page_count = count_pdf_pages(pdf_path)
        except PdfSplitError as exc:
            self.page_count_label.setText("PDF non leggibile")
            if show_warning:
                QMessageBox.warning(self, "PDF non valido", str(exc))
            return False

        self.page_count_label.setText(f"{page_count} pagine")
        return True

    def _select_pdf(self) -> None:
        try:
            start_dir = str(resolve_pdf_path(self.pdf_edit.text()).parent)
        except ValueError:
            start_dir = ""
        dialog = _themed_file_dialog(
            self,
            "Seleziona il fascicolo PDF",
            start_dir,
            QFileDialog.FileMode.ExistingFile,
            "Documenti PDF (*.pdf)",
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        filename = dialog.selectedFiles()[0] if dialog.selectedFiles() else ""
        if not filename:
            return

        self.pdf_edit.setText(filename)
        self._update_pdf_page_count(show_warning=True)
        if not self.output_edit.text().strip() or not self._output_path_customized:
            self.output_edit.setText(str(Path(filename).parent))
            self._output_path_customized = False

    def _select_output(self) -> None:
        try:
            start_dir = str(resolve_output_path(self.output_edit.text()))
        except ValueError:
            start_dir = str(Path.home())
        dialog = _themed_file_dialog(
            self,
            "Seleziona la cartella di output",
            start_dir,
            QFileDialog.FileMode.Directory,
            options=QFileDialog.Option.ShowDirsOnly,
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        directory = dialog.selectedFiles()[0] if dialog.selectedFiles() else ""
        if directory:
            self.output_edit.setText(directory)
            self._output_path_customized = True
            self._save_gui_settings()

    # ------------------------------------------------------------------
    # Casefile analysis
    # ------------------------------------------------------------------

    def _select_casefile_input(self) -> None:
        start_dir = self.casefile_input_edit.text().strip() or str(Path.home())
        dialog = _themed_file_dialog(
            self,
            "Seleziona la cartella del fascicolo",
            start_dir,
            QFileDialog.FileMode.Directory,
            options=QFileDialog.Option.ShowDirsOnly,
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        directory = dialog.selectedFiles()[0] if dialog.selectedFiles() else ""
        if directory:
            self.casefile_input_edit.setText(directory)

    def _select_casefile_output(self) -> None:
        start_dir = self.casefile_output_edit.text().strip() or str(Path.home())
        dialog = _themed_file_dialog(
            self,
            "Seleziona la cartella di output",
            start_dir,
            QFileDialog.FileMode.Directory,
            options=QFileDialog.Option.ShowDirsOnly,
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        directory = dialog.selectedFiles()[0] if dialog.selectedFiles() else ""
        if directory:
            self.casefile_output_edit.setText(directory)

    def _start_casefile_analysis(self) -> None:
        input_text = self.casefile_input_edit.text().strip()
        if not input_text:
            QMessageBox.warning(
                self,
                "Dati mancanti",
                "Selezionare la cartella del fascicolo.",
            )
            return
        input_dir = Path(os.path.expanduser(os.path.expandvars(input_text)))
        if not input_dir.is_dir():
            QMessageBox.warning(
                self,
                "Cartella non trovata",
                "La cartella del fascicolo non esiste o non è una cartella.",
            )
            return

        output_text = self.casefile_output_edit.text().strip()
        if not output_text:
            QMessageBox.warning(
                self,
                "Dati mancanti",
                "Selezionare la cartella di output.",
            )
            return
        output_dir = Path(os.path.expanduser(os.path.expandvars(output_text)))
        try:
            output_dir.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            QMessageBox.critical(
                self,
                "Cartella non accessibile",
                f"Impossibile usare la cartella di output:\n{exc}",
            )
            return

        self._set_casefile_running(True)
        self.casefile_log_view.clear()
        self.casefile_open_folder_button.setEnabled(False)
        self.casefile_open_report_button.setEnabled(False)
        self._append_casefile_log("Avvio analisi fascicolo…")
        self._append_casefile_log(f"  Input:  {input_dir}")
        self._append_casefile_log(f"  Output: {output_dir}")

        self._casefile_worker = CasefileWorker(
            input_dir, output_dir, parent=self
        )
        self._casefile_worker.completed.connect(self._casefile_completed)
        self._casefile_worker.failed.connect(self._casefile_failed)
        self._casefile_worker.finished.connect(self._casefile_worker_finished)
        self._casefile_worker.start()

    def _casefile_completed(self, result: CasefileGuiResult) -> None:
        self._append_casefile_log(
            f"Fascicolo: {result.total_files} file, "
            f"{result.total_pdf_files} PDF, "
            f"{result.total_indexes} indici, "
            f"{result.total_index_matches} match, "
            f"{result.total_units} unità, "
            f"{result.total_warnings} warning"
        )
        self._append_casefile_log(f"  JSON:     {result.json_path}")
        self._append_casefile_log(f"  Markdown: {result.markdown_path}")
        self._append_casefile_log(f"  CSV:      {result.csv_path}")

        self._casefile_output_dir = str(result.json_path.parent)
        self._casefile_report_path = str(result.markdown_path)
        self.casefile_open_folder_button.setEnabled(True)
        self.casefile_open_report_button.setEnabled(True)

        QMessageBox.information(
            self,
            "Analisi fascicolo completata",
            f"Analisi fascicolo completata.\n\n"
            f"File totali: {result.total_files}\n"
            f"PDF: {result.total_pdf_files}\n"
            f"Indici: {result.total_indexes}\n"
            f"Match: {result.total_index_matches}\n"
            f"Unità documentali: {result.total_units}\n"
            f"Warning: {result.total_warnings}\n\n"
            f"JSON: {result.json_path}\n"
            f"Markdown: {result.markdown_path}\n"
            f"CSV: {result.csv_path}",
        )

    def _casefile_failed(self, message: str) -> None:
        self._append_casefile_log(f"Errore analisi fascicolo: {message}")
        QMessageBox.critical(
            self,
            "Errore analisi fascicolo",
            f"Impossibile completare l'analisi:\n{message}",
        )

    def _casefile_worker_finished(self) -> None:
        worker = self._casefile_worker
        self._casefile_worker = None
        self._set_casefile_running(False)
        if worker is not None:
            worker.deleteLater()

    def _open_casefile_output_folder(self) -> None:
        folder = self._casefile_output_dir
        if not folder or not Path(folder).is_dir():
            QMessageBox.warning(
                self,
                "Cartella non trovata",
                "La cartella di output non esiste o non è accessibile.",
            )
            return
        self._open_local_path(
            Path(folder),
            "Impossibile aprire la cartella",
            "Errore durante l'apertura della cartella.",
        )

    def _open_casefile_report(self) -> None:
        path = self._casefile_report_path
        if not path or not Path(path).is_file():
            QMessageBox.warning(
                self,
                "File non trovato",
                "Il report Markdown non esiste o non è accessibile.",
            )
            return
        self._open_local_path(
            Path(path),
            "Impossibile aprire il file",
            "Errore durante l'apertura del report.",
        )

    def _set_casefile_running(self, running: bool) -> None:
        self.casefile_input_edit.setEnabled(not running)
        self.casefile_input_button.setEnabled(not running)
        self.casefile_output_edit.setEnabled(not running)
        self.casefile_output_button.setEnabled(not running)
        self.casefile_start_button.setEnabled(not running)

    # ------------------------------------------------------------------
    # Processing
    # ------------------------------------------------------------------

    def _start(self) -> None:
        try:
            pdf_path = resolve_pdf_path(self.pdf_edit.text())
        except ValueError as exc:
            QMessageBox.warning(
                self, "Dati mancanti", str(exc)
            )
            return
        if not pdf_path.is_file():
            QMessageBox.warning(
                self, "File non trovato", "Il file PDF indicato non esiste."
            )
            return
        if pdf_path.suffix.lower() != ".pdf":
            QMessageBox.warning(
                self, "Formato non valido", "Il file indicato non ha estensione .pdf."
            )
            return
        try:
            page_count = count_pdf_pages(pdf_path)
        except PdfSplitError as exc:
            self.page_count_label.setText("PDF non leggibile")
            QMessageBox.warning(self, "PDF non valido", str(exc))
            return
        self.page_count_label.setText(f"{page_count} pagine")
        try:
            output_dir = resolve_output_path(self.output_edit.text())
        except ValueError as exc:
            QMessageBox.warning(
                self, "Dati mancanti", str(exc)
            )
            return

        try:
            output_dir.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            QMessageBox.critical(
                self,
                "Cartella non accessibile",
                f"Impossibile usare la cartella di output:\n{exc}",
            )
            return

        self.output_edit.setText(str(output_dir))
        self._save_gui_settings()
        create_searchable = self.searchable_checkbox.isChecked()
        ocr_backend = self.ocr_backend_combo.currentData() or "auto"
        external_ocr_command = self.external_ocr_command_edit.text().strip() or None
        if create_searchable:
            backend = detect_ocr_backend(
                ocr_backend,
                external_command=external_ocr_command,
            )
            if not backend.runnable:
                detail = "\n".join(backend.warnings) or "Backend non disponibile."
                QMessageBox.warning(
                    self,
                    "Backend OCR non disponibile",
                    f"{detail}\n\n"
                    "La generazione del PDF ricercabile verrà saltata.",
                )
                create_searchable = False

        ocr_language = self.ocr_language_combo.currentData() or "ita"
        self._create_searchable_requested = create_searchable

        self._final_markdown_path = None
        self._searchable_pdf_path = None
        self._manifest_path = None
        self._log_path = None
        self._job_output_dir = None
        self.open_folder_button.setEnabled(False)
        self.open_markdown_button.setEnabled(False)
        self.open_pdf_button.setEnabled(False)
        self.open_manifest_button.setEnabled(False)
        self.open_log_button.setEnabled(False)
        self.verify_outputs_button.setEnabled(False)
        self.log_view.clear()
        self.progress_bar.setValue(0)
        self.eta_label.setText("ETA: calcolo dopo il primo blocco")
        self.status_label.setText("Preparazione dei blocchi PDF...")
        self._set_running(True)

        profile = PROFILES[self.profile_combo.currentText()]
        self._worker = OcrWorker(
            str(pdf_path),
            str(output_dir),
            self.block_size_spin.value(),
            profile,
            create_searchable=create_searchable,
            ocr_language=ocr_language,
            structured_output=self.structured_output_checkbox.isChecked(),
            ocr_backend=ocr_backend,
            external_ocr_command=external_ocr_command,
            use_searchable_as_source=(
                create_searchable
                and self.use_searchable_as_source_checkbox.isChecked()
            ),
            ocr_timeout_seconds=self._ocr_timeout_seconds,
            ocr_jobs=self._ocr_jobs,
            analyze_judgment_after_conversion=(
                self.judgment_analysis_checkbox.isChecked()
            ),
            parent=self,
        )
        self._worker.log_message.connect(self._append_log)
        self._worker.progress_changed.connect(self._update_progress)
        self._worker.completed.connect(self._completed)
        self._worker.cancelled.connect(self._cancelled)
        self._worker.failed.connect(self._failed)
        self._worker.searchable_pdf_done.connect(self._on_searchable_pdf_done)
        self._worker.searchable_pdf_error.connect(self._on_searchable_pdf_error)
        self._worker.finished.connect(self._worker_finished)
        self._worker.start()

    def _cancel(self) -> None:
        if self._worker is None or not self._worker.isRunning():
            return
        self.cancel_button.setEnabled(False)
        self.status_label.setText("Annullamento in corso...")
        self._append_log("Richiesto annullamento dell'elaborazione.")
        self._worker.request_cancel()

    # ------------------------------------------------------------------
    # Worker signal handlers
    # ------------------------------------------------------------------

    def _append_log(self, message: str) -> None:
        self.log_view.append(message)
        scrollbar = self.log_view.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def _append_casefile_log(self, message: str) -> None:
        self.casefile_log_view.append(message)
        scrollbar = self.casefile_log_view.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def _update_progress(self, percent: int, eta: str) -> None:
        self.progress_bar.setValue(percent)
        self.eta_label.setText(f"ETA: {eta}")
        self.status_label.setText(f"Elaborazione in corso: {percent}%")

    def _completed(
        self,
        final_path: str,
        work_dir: str,
        duration_text: str,
        speed_text: str,
    ) -> None:
        self._final_markdown_path = final_path
        self._job_output_dir = str(Path(final_path).parent)
        self.open_folder_button.setEnabled(True)
        self.open_markdown_button.setEnabled(True)
        self._enable_manifest_button()
        self._enable_log_button()
        self.status_label.setText(f"Completato: {final_path}")
        self.eta_label.setText("ETA: completato")
        pdf_note = (
            "\n\nCreazione PDF ricercabile OCR in corso..."
            if self._create_searchable_requested
            else ""
        )
        completion_message = (
            f"Markdown creato:\n{final_path}\n\n"
            f"Durata totale: {duration_text}\n"
            f"Velocità: {speed_text}"
            f"{pdf_note}\n\n"
            f"Output intermedi:\n{work_dir}"
        )
        self._show_tray_message(
            "Elaborazione completata",
            f"Markdown creato: {final_path}",
        )
        if self.isVisible():
            QMessageBox.information(
                self,
                "Elaborazione completata",
                completion_message,
            )

    def _cancelled(self, work_dir: str) -> None:
        self._remember_worker_output_dir()
        self.status_label.setText("Elaborazione annullata")
        self.eta_label.setText("ETA: --")
        self._enable_manifest_button()
        self._enable_log_button()
        if self.isVisible():
            QMessageBox.information(
                self,
                "Elaborazione annullata",
                f"Gli output parziali disponibili sono in:\n{work_dir}",
            )

    def _failed(self, message: str) -> None:
        self._remember_worker_output_dir()
        self.status_label.setText("Elaborazione terminata con errore")
        self.eta_label.setText("ETA: --")
        self._enable_manifest_button()
        self._enable_log_button()
        self._show_tray_message(
            "Errore OCR",
            message,
            QSystemTrayIcon.MessageIcon.Critical,
        )
        if self.isVisible():
            QMessageBox.critical(
                self,
                "Errore di elaborazione",
                f"{message}\n\nConsultare run.log nella cartella di output.",
            )

    def _on_searchable_pdf_done(self, path: str) -> None:
        self._searchable_pdf_path = path
        self.open_pdf_button.setEnabled(True)
        self._append_log(f"PDF ricercabile disponibile: {path}")

    def _on_searchable_pdf_error(self, message: str) -> None:
        self._show_tray_message(
            "Errore OCR",
            f"PDF ricercabile non creato: {message}",
            QSystemTrayIcon.MessageIcon.Critical,
        )
        if self.isVisible():
            QMessageBox.warning(
                self,
                "Errore PDF ricercabile",
                f"Impossibile creare il PDF ricercabile:\n\n{message}",
            )

    def _worker_finished(self) -> None:
        worker = self._worker
        self._worker = None
        self._set_running(False)
        if worker is not None:
            worker.deleteLater()
        if self._close_after_cancel:
            self._close_after_cancel = False
            app = QApplication.instance()
            if self._tray_real_quit_requested and app is not None:
                app.setQuitOnLastWindowClosed(True)
            QTimer.singleShot(0, self.close)
            if self._tray_real_quit_requested and app is not None:
                QTimer.singleShot(0, app.quit)

    # ------------------------------------------------------------------
    # UI state helpers
    # ------------------------------------------------------------------

    def _set_running(self, running: bool) -> None:
        self.pdf_edit.setEnabled(not running)
        self.pdf_button.setEnabled(not running)
        self.output_edit.setEnabled(not running)
        self.output_button.setEnabled(not running)
        self.profile_combo.setEnabled(not running)
        self.block_size_spin.setEnabled(not running)
        self.searchable_checkbox.setEnabled(not running)
        self.ocr_backend_combo.setEnabled(
            not running and self.searchable_checkbox.isChecked()
        )
        self.ocr_timeout_spin.setEnabled(
            not running and self.searchable_checkbox.isChecked()
        )
        self.ocr_jobs_edit.setEnabled(
            not running and self.searchable_checkbox.isChecked()
        )
        self.external_ocr_command_edit.setEnabled(
            not running
            and self.searchable_checkbox.isChecked()
            and (self.ocr_backend_combo.currentData() or "auto") == "external"
        )
        self.use_searchable_as_source_checkbox.setEnabled(
            not running and self.searchable_checkbox.isChecked()
        )
        self.structured_output_checkbox.setEnabled(not running)
        self.judgment_analysis_checkbox.setEnabled(not running)
        self.start_button.setEnabled(not running)
        self.cancel_button.setEnabled(running)
        if running:
            self.ocr_language_combo.setEnabled(False)
            self.open_folder_button.setEnabled(False)
            self.open_markdown_button.setEnabled(False)
            self.open_pdf_button.setEnabled(False)
            self.open_manifest_button.setEnabled(False)
            self.open_log_button.setEnabled(False)
            self.verify_outputs_button.setEnabled(False)
        else:
            self.ocr_language_combo.setEnabled(self.searchable_checkbox.isChecked())
            self._on_ocr_backend_changed()

    # ------------------------------------------------------------------
    # Open-file / open-folder handlers
    # ------------------------------------------------------------------

    def _resolve_existing_output_file(self, filename: str) -> Path | None:
        """Return output_dir / filename if it is a regular file, else None."""
        output_dir = self._current_output_dir()
        if output_dir is None:
            return None
        path = output_dir / filename
        return path if path.is_file() else None

    def _remember_worker_output_dir(self) -> None:
        if self._worker is not None:
            self._job_output_dir = str(self._worker.output_dir)

    def _current_output_dir(self) -> Path | None:
        if self._job_output_dir:
            return Path(self._job_output_dir)
        try:
            return resolve_output_path(self.output_edit.text())
        except ValueError:
            return None

    def _open_local_path(
        self,
        path: Path,
        error_title: str,
        error_message: str,
    ) -> None:
        try:
            opened = QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))
        except Exception as exc:
            QMessageBox.critical(
                self,
                error_title,
                f"{error_message}\n{exc}",
            )
            return
        if not opened:
            QMessageBox.critical(self, error_title, error_message)

    def _open_output_folder(self) -> None:
        folder = self._current_output_dir()
        if folder is None or not folder.is_dir():
            QMessageBox.warning(
                self,
                "Cartella non trovata",
                "La cartella di output non esiste o non è accessibile.",
            )
            return
        self._open_local_path(
            folder,
            "Impossibile aprire la cartella",
            "Errore durante l'apertura della cartella.",
        )

    def _open_markdown(self) -> None:
        path = self._final_markdown_path
        if not path or not Path(path).is_file():
            QMessageBox.warning(
                self,
                "File non trovato",
                "Il file Markdown non esiste o non è accessibile.",
            )
            return
        self._open_local_path(
            Path(path),
            "Impossibile aprire il file",
            "Errore durante l'apertura del file Markdown.",
        )

    def _open_searchable_pdf(self) -> None:
        path = self._searchable_pdf_path
        if not path or not Path(path).is_file():
            QMessageBox.warning(
                self,
                "File non trovato",
                "Il PDF ricercabile non esiste o non è accessibile.",
            )
            return
        self._open_local_path(
            Path(path),
            "Impossibile aprire il file",
            "Errore durante l'apertura del PDF.",
        )

    def _enable_manifest_button(self) -> None:
        path = self._resolve_existing_output_file(MANIFEST_FILENAME)
        if path is not None:
            self._manifest_path = str(path)
            self.open_manifest_button.setEnabled(True)
            self.verify_outputs_button.setEnabled(True)

    def _open_manifest(self) -> None:
        path = self._manifest_path
        if not path or not Path(path).is_file():
            QMessageBox.warning(
                self,
                "File non trovato",
                "Il file manifest.json non esiste o non è accessibile.",
            )
            return
        self._open_local_path(
            Path(path),
            "Impossibile aprire il file",
            "Errore durante l'apertura del manifest.",
        )

    def _enable_log_button(self) -> None:
        path = self._resolve_existing_output_file(LOG_FILENAME)
        if path is not None:
            self._log_path = str(path)
            self.open_log_button.setEnabled(True)

    def _open_log(self) -> None:
        path = self._log_path
        if not path or not Path(path).is_file():
            QMessageBox.warning(
                self,
                "File non trovato",
                "Il file run.log non esiste o non è accessibile.",
            )
            return
        self._open_local_path(
            Path(path),
            "Impossibile aprire il file",
            "Errore durante l'apertura del log.",
        )

    def _verify_outputs(self) -> None:
        path = self._manifest_path
        if not path or not Path(path).is_file():
            QMessageBox.warning(
                self,
                "File non trovato",
                "Il file manifest.json non esiste o non è accessibile.",
            )
            return
        try:
            manifest = load_manifest(Path(path))
            report = verify_manifest_outputs(manifest)
        except (OSError, ValueError) as exc:
            QMessageBox.warning(
                self,
                "Manifest non leggibile",
                f"Impossibile verificare gli output:\n{exc}",
            )
            return
        QMessageBox.information(
            self,
            "Verifica output",
            format_manifest_verification(report),
        )

    # ------------------------------------------------------------------
    # Close event
    # ------------------------------------------------------------------

    def closeEvent(self, event: QCloseEvent) -> None:
        self._save_gui_settings()
        if self._tray_real_quit_requested:
            self._cleanup_tray()
            event.accept()
            return

        if self._tray_is_available():
            event.ignore()
            self.hide()
            return

        if self._worker is None or not self._worker.isRunning():
            event.accept()
            return

        answer = QMessageBox.question(
            self,
            "Elaborazione in corso",
            "Annullare l'elaborazione e chiudere l'applicazione?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer == QMessageBox.StandardButton.Yes:
            self._close_after_cancel = True
            self._cancel()
        event.ignore()
