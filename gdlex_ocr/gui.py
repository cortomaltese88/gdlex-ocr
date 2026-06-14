"""PySide6 interface for GD LEX OCR."""

from __future__ import annotations

import subprocess
from pathlib import Path

from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QCloseEvent, QFontDatabase
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFrame,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from gdlex_ocr.pdf_splitter import PdfSplitError, count_pdf_pages
from gdlex_ocr.profiles import DEFAULT_PROFILE, PROFILE_NAMES, PROFILES
from gdlex_ocr.version import (
    APP_NAME,
    APP_SUBTITLE,
    APP_VERSION_LABEL,
)
from gdlex_ocr.worker import OcrWorker


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self._worker: OcrWorker | None = None
        self._close_after_cancel = False
        self._final_markdown_path: str | None = None

        self.setWindowTitle(f"{APP_NAME} {APP_VERSION_LABEL}")
        self.setMinimumSize(820, 660)
        self.resize(980, 760)

        central = QWidget(self)
        self.setCentralWidget(central)
        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(24, 22, 24, 22)
        root_layout.setSpacing(12)

        header = QFrame()
        header.setObjectName("headerFrame")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(22, 14, 18, 14)
        header_layout.setSpacing(16)

        identity_layout = QVBoxLayout()
        identity_layout.setSpacing(2)
        title = QLabel(APP_NAME)
        title.setObjectName("appTitle")
        identity_layout.addWidget(title)
        subtitle = QLabel(APP_SUBTITLE)
        subtitle.setObjectName("appSubtitle")
        identity_layout.addWidget(subtitle)
        header_layout.addLayout(identity_layout, 1)

        version = QLabel(APP_VERSION_LABEL)
        version.setObjectName("versionBadge")
        version.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(version)
        root_layout.addWidget(header)

        source_group = QGroupBox("Documento e destinazione")
        source_layout = QFormLayout(source_group)
        source_layout.setContentsMargins(18, 18, 18, 16)
        source_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        source_layout.setFieldGrowthPolicy(
            QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow
        )
        source_layout.setHorizontalSpacing(14)
        source_layout.setVerticalSpacing(10)

        self.pdf_edit = QLineEdit()
        self.pdf_edit.setReadOnly(True)
        self.pdf_edit.setPlaceholderText("Seleziona un fascicolo PDF")
        self.pdf_button = QPushButton("Sfoglia PDF")
        self.pdf_button.clicked.connect(self._select_pdf)
        pdf_row = QHBoxLayout()
        pdf_row.setSpacing(10)
        pdf_row.addWidget(self.pdf_edit, 1)
        pdf_row.addWidget(self.pdf_button)
        source_layout.addRow("File PDF", pdf_row)

        self.output_edit = QLineEdit()
        self.output_edit.setReadOnly(True)
        self.output_edit.setPlaceholderText("Seleziona la cartella di destinazione")
        self.output_button = QPushButton("Sfoglia cartella")
        self.output_button.clicked.connect(self._select_output)
        output_row = QHBoxLayout()
        output_row.setSpacing(10)
        output_row.addWidget(self.output_edit, 1)
        output_row.addWidget(self.output_button)
        source_layout.addRow("Cartella output", output_row)
        root_layout.addWidget(source_group)

        options_group = QGroupBox("Opzioni OCR")
        options_outer = QVBoxLayout(options_group)
        options_outer.setContentsMargins(18, 18, 18, 16)
        options_outer.setSpacing(10)

        profile_row = QHBoxLayout()
        profile_row.setSpacing(12)
        profile_label = QLabel("Profilo elaborazione")
        profile_row.addWidget(profile_label)
        self.profile_combo = QComboBox()
        self.profile_combo.addItems(PROFILE_NAMES)
        self.profile_combo.setCurrentText(DEFAULT_PROFILE)
        self.profile_combo.setMinimumWidth(140)
        self.profile_combo.currentTextChanged.connect(self._on_profile_changed)
        profile_row.addWidget(self.profile_combo)
        self.profile_summary_label = QLabel()
        self.profile_summary_label.setObjectName("sectionHint")
        profile_row.addWidget(self.profile_summary_label, 1)
        options_outer.addLayout(profile_row)

        block_row = QHBoxLayout()
        block_row.setSpacing(12)
        block_label = QLabel("Dimensione blocco")
        block_row.addWidget(block_label)
        self.block_size_spin = QSpinBox()
        self.block_size_spin.setRange(1, 500)
        self.block_size_spin.setSuffix(" pagine")
        self.block_size_spin.setMinimumWidth(130)
        block_row.addWidget(self.block_size_spin)

        block_row.addSpacing(16)
        pages_caption = QLabel("Documento")
        pages_caption.setObjectName("sectionHint")
        block_row.addWidget(pages_caption)
        self.page_count_label = QLabel("Nessun PDF selezionato")
        block_row.addWidget(self.page_count_label)
        block_row.addStretch(1)
        local_note = QLabel("Elaborazione locale · nessun upload cloud")
        local_note.setObjectName("sectionHint")
        block_row.addWidget(local_note)
        options_outer.addLayout(block_row)
        root_layout.addWidget(options_group)

        # Initialise spin and summary from default profile
        self._on_profile_changed(DEFAULT_PROFILE)

        progress_group = QGroupBox("Avanzamento")
        progress_layout = QVBoxLayout(progress_group)
        progress_layout.setContentsMargins(18, 18, 18, 16)
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
        root_layout.addWidget(progress_group)

        log_group = QGroupBox("Log elaborazione")
        log_layout = QVBoxLayout(log_group)
        log_layout.setContentsMargins(12, 18, 12, 12)
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
        root_layout.addWidget(log_group, 1)

        button_row = QHBoxLayout()
        button_row.setSpacing(10)

        self.open_folder_button = QPushButton("Apri cartella output")
        self.open_folder_button.setEnabled(False)
        self.open_folder_button.clicked.connect(self._open_output_folder)
        button_row.addWidget(self.open_folder_button)

        self.open_markdown_button = QPushButton("Apri Markdown")
        self.open_markdown_button.setEnabled(False)
        self.open_markdown_button.clicked.connect(self._open_markdown)
        button_row.addWidget(self.open_markdown_button)

        button_row.addStretch(1)

        self.start_button = QPushButton("Avvia")
        self.start_button.setObjectName("primaryButton")
        self.start_button.setDefault(True)
        self.start_button.clicked.connect(self._start)
        button_row.addWidget(self.start_button)

        self.cancel_button = QPushButton("Annulla")
        self.cancel_button.setObjectName("cancelButton")
        self.cancel_button.setEnabled(False)
        self.cancel_button.clicked.connect(self._cancel)
        button_row.addWidget(self.cancel_button)

        root_layout.addLayout(button_row)

    def _on_profile_changed(self, name: str) -> None:
        profile = PROFILES.get(name)
        if profile is None:
            return
        self.block_size_spin.setValue(profile.block_size)
        self.profile_summary_label.setText(profile.summary())

    def _select_pdf(self) -> None:
        start_dir = str(Path(self.pdf_edit.text()).parent) if self.pdf_edit.text() else ""
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Seleziona il fascicolo PDF",
            start_dir,
            "Documenti PDF (*.pdf)",
        )
        if not filename:
            return

        self.pdf_edit.setText(filename)
        try:
            page_count = count_pdf_pages(filename)
        except PdfSplitError as exc:
            self.page_count_label.setText("PDF non leggibile")
            QMessageBox.warning(self, "PDF non valido", str(exc))
            return

        self.page_count_label.setText(f"{page_count} pagine")
        if not self.output_edit.text():
            self.output_edit.setText(str(Path(filename).parent))

    def _select_output(self) -> None:
        start_dir = self.output_edit.text() or str(Path.home())
        directory = QFileDialog.getExistingDirectory(
            self,
            "Seleziona la cartella di output",
            start_dir,
            QFileDialog.Option.ShowDirsOnly,
        )
        if directory:
            self.output_edit.setText(directory)

    def _start(self) -> None:
        pdf_path = Path(self.pdf_edit.text())
        output_dir = Path(self.output_edit.text())

        if not self.pdf_edit.text() or not pdf_path.is_file():
            QMessageBox.warning(
                self, "Dati mancanti", "Selezionare un file PDF valido."
            )
            return
        if pdf_path.suffix.lower() != ".pdf":
            QMessageBox.warning(
                self, "Formato non valido", "Il file selezionato non è un PDF."
            )
            return
        if not self.output_edit.text():
            QMessageBox.warning(
                self, "Dati mancanti", "Selezionare la cartella di output."
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

        self._final_markdown_path = None
        self.open_folder_button.setEnabled(False)
        self.open_markdown_button.setEnabled(False)
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
            self,
        )
        self._worker.log_message.connect(self._append_log)
        self._worker.progress_changed.connect(self._update_progress)
        self._worker.completed.connect(self._completed)
        self._worker.cancelled.connect(self._cancelled)
        self._worker.failed.connect(self._failed)
        self._worker.finished.connect(self._worker_finished)
        self._worker.start()

    def _cancel(self) -> None:
        if self._worker is None or not self._worker.isRunning():
            return
        self.cancel_button.setEnabled(False)
        self.status_label.setText("Annullamento in corso...")
        self._append_log("Richiesto annullamento dell'elaborazione.")
        self._worker.request_cancel()

    def _append_log(self, message: str) -> None:
        self.log_view.append(message)
        scrollbar = self.log_view.verticalScrollBar()
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
        self.open_folder_button.setEnabled(True)
        self.open_markdown_button.setEnabled(True)
        self.status_label.setText(f"Completato: {final_path}")
        self.eta_label.setText("ETA: completato")
        QMessageBox.information(
            self,
            "Elaborazione completata",
            f"Markdown creato:\n{final_path}\n\n"
            f"Durata totale: {duration_text}\n"
            f"Velocità: {speed_text}\n\n"
            f"Output intermedi:\n{work_dir}",
        )

    def _cancelled(self, work_dir: str) -> None:
        self.status_label.setText("Elaborazione annullata")
        self.eta_label.setText("ETA: --")
        QMessageBox.information(
            self,
            "Elaborazione annullata",
            f"Gli output parziali disponibili sono in:\n{work_dir}",
        )

    def _failed(self, message: str) -> None:
        self.status_label.setText("Elaborazione terminata con errore")
        self.eta_label.setText("ETA: --")
        QMessageBox.critical(
            self,
            "Errore di elaborazione",
            f"{message}\n\nConsultare run.log nella cartella di output.",
        )

    def _worker_finished(self) -> None:
        worker = self._worker
        self._worker = None
        self._set_running(False)
        if worker is not None:
            worker.deleteLater()
        if self._close_after_cancel:
            self._close_after_cancel = False
            QTimer.singleShot(0, self.close)

    def _set_running(self, running: bool) -> None:
        self.pdf_button.setEnabled(not running)
        self.output_button.setEnabled(not running)
        self.profile_combo.setEnabled(not running)
        self.block_size_spin.setEnabled(not running)
        self.start_button.setEnabled(not running)
        self.cancel_button.setEnabled(running)
        if running:
            self.open_folder_button.setEnabled(False)
            self.open_markdown_button.setEnabled(False)

    def _open_output_folder(self) -> None:
        folder = self.output_edit.text()
        if not folder or not Path(folder).is_dir():
            QMessageBox.warning(
                self,
                "Cartella non trovata",
                "La cartella di output non esiste o non è accessibile.",
            )
            return
        try:
            subprocess.Popen(["xdg-open", folder])
        except OSError as exc:
            QMessageBox.critical(
                self,
                "Impossibile aprire la cartella",
                f"Errore durante l'apertura della cartella:\n{exc}",
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
        try:
            subprocess.Popen(["xdg-open", path])
        except OSError as exc:
            QMessageBox.critical(
                self,
                "Impossibile aprire il file",
                f"Errore durante l'apertura del file Markdown:\n{exc}",
            )

    def closeEvent(self, event: QCloseEvent) -> None:
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
