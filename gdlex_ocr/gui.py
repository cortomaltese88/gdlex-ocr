"""Minimal PySide6 interface for GD LEX OCR."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QCloseEvent, QFont
from PySide6.QtWidgets import (
    QFileDialog,
    QFormLayout,
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
from gdlex_ocr.worker import OcrWorker


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self._worker: OcrWorker | None = None
        self._close_after_cancel = False

        self.setWindowTitle("GD LEX OCR")
        self.setMinimumSize(760, 600)
        self.resize(880, 680)

        central = QWidget(self)
        self.setCentralWidget(central)
        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(24, 20, 24, 20)
        root_layout.setSpacing(14)

        title = QLabel("GD LEX OCR")
        title_font = QFont()
        title_font.setPointSize(20)
        title_font.setBold(True)
        title.setFont(title_font)
        root_layout.addWidget(title)

        subtitle = QLabel("OCR locale per fascicoli e documenti")
        subtitle.setStyleSheet("color: #555;")
        root_layout.addWidget(subtitle)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(10)

        self.pdf_edit = QLineEdit()
        self.pdf_edit.setReadOnly(True)
        self.pdf_edit.setPlaceholderText("Seleziona un fascicolo PDF")
        self.pdf_button = QPushButton("Sfoglia...")
        self.pdf_button.clicked.connect(self._select_pdf)
        pdf_row = QHBoxLayout()
        pdf_row.addWidget(self.pdf_edit, 1)
        pdf_row.addWidget(self.pdf_button)
        form.addRow("File PDF:", pdf_row)

        self.output_edit = QLineEdit()
        self.output_edit.setReadOnly(True)
        self.output_edit.setPlaceholderText("Seleziona la cartella di destinazione")
        self.output_button = QPushButton("Sfoglia...")
        self.output_button.clicked.connect(self._select_output)
        output_row = QHBoxLayout()
        output_row.addWidget(self.output_edit, 1)
        output_row.addWidget(self.output_button)
        form.addRow("Cartella output:", output_row)

        self.block_size_spin = QSpinBox()
        self.block_size_spin.setRange(1, 500)
        self.block_size_spin.setValue(5)
        self.block_size_spin.setSuffix(" pagine")
        form.addRow("Dimensione blocco:", self.block_size_spin)

        self.page_count_label = QLabel("Nessun PDF selezionato")
        form.addRow("Pagine:", self.page_count_label)
        root_layout.addLayout(form)

        progress_row = QHBoxLayout()
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("%p%")
        progress_row.addWidget(self.progress_bar, 1)
        self.eta_label = QLabel("ETA: --")
        self.eta_label.setMinimumWidth(135)
        progress_row.addWidget(self.eta_label)
        root_layout.addLayout(progress_row)

        self.status_label = QLabel("Pronto")
        root_layout.addWidget(self.status_label)

        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setPlaceholderText("Il log dell'elaborazione apparirà qui.")
        self.log_view.document().setMaximumBlockCount(5000)
        root_layout.addWidget(self.log_view, 1)

        button_row = QHBoxLayout()
        button_row.addStretch(1)
        self.start_button = QPushButton("Avvia")
        self.start_button.setDefault(True)
        self.start_button.clicked.connect(self._start)
        button_row.addWidget(self.start_button)
        self.cancel_button = QPushButton("Annulla")
        self.cancel_button.setEnabled(False)
        self.cancel_button.clicked.connect(self._cancel)
        button_row.addWidget(self.cancel_button)
        root_layout.addLayout(button_row)

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

        self.log_view.clear()
        self.progress_bar.setValue(0)
        self.eta_label.setText("ETA: calcolo dopo il primo blocco")
        self.status_label.setText("Preparazione dei blocchi PDF...")
        self._set_running(True)

        self._worker = OcrWorker(
            str(pdf_path),
            str(output_dir),
            self.block_size_spin.value(),
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

    def _completed(self, final_path: str, work_dir: str) -> None:
        self.status_label.setText(f"Completato: {final_path}")
        self.eta_label.setText("ETA: completato")
        QMessageBox.information(
            self,
            "Elaborazione completata",
            f"Markdown creato:\n{final_path}\n\n"
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
        self.block_size_spin.setEnabled(not running)
        self.start_button.setEnabled(not running)
        self.cancel_button.setEnabled(running)

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
