"""Parts import dialog for OCR-based PDF parts list import.

This dialog provides:
- Progress display during import
- Results summary
- Detailed part-by-part status
- Export to CSV option
"""

import csv
from pathlib import Path
from typing import Optional, List
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QProgressBar, QTableWidget, QTableWidgetItem, QHeaderView,
    QGroupBox, QTextEdit, QFileDialog, QMessageBox, QCheckBox,
    QDialogButtonBox, QWidget, QSplitter, QFrame
)
from PySide6.QtCore import Qt, QThread, Signal, QUrl
from PySide6.QtGui import QColor, QDesktopServices

from electrical_schematics.api.parts_import_service import (
    PartsImportService, ImportResult, ImportStatus, PartImportDetail
)
from electrical_schematics.database.manager import DatabaseManager
from electrical_schematics.config.settings import DigiKeyConfig


class ImportWorker(QThread):
    """Worker thread for running import in background."""

    progress = Signal(str, int, int)  # message, current, total
    finished = Signal(object)  # ImportResult
    error = Signal(str)

    def __init__(
        self,
        service: PartsImportService,
        pdf_path: Path,
        update_existing: bool
    ):
        super().__init__()
        self.service = service
        self.pdf_path = pdf_path
        self.update_existing = update_existing

    def run(self) -> None:
        try:
            result = self.service.import_parts(
                self.pdf_path,
                update_existing=self.update_existing,
                progress_callback=self._on_progress
            )
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))

    def _on_progress(self, message: str, current: int, total: int) -> None:
        self.progress.emit(message, current, total)


class PartsImportDialog(QDialog):
    """Dialog for importing parts from PDF via OCR and DigiKey."""

    def __init__(
        self,
        parent: Optional[QWidget],
        db_manager: DatabaseManager,
        pdf_path: Optional[Path] = None,
        digikey_config: Optional[DigiKeyConfig] = None
    ):
        """Initialize parts import dialog.

        Args:
            parent: Parent widget
            db_manager: Database manager for library operations
            pdf_path: Path to PDF file (optional, can select later)
            digikey_config: DigiKey API configuration
        """
        super().__init__(parent)
        self.db_manager = db_manager
        self.pdf_path = pdf_path
        self.digikey_config = digikey_config
        self.import_result: Optional[ImportResult] = None
        self.worker: Optional[ImportWorker] = None

        self.setWindowTitle("Import Parts from PDF")
        self.setMinimumSize(800, 600)
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the dialog UI."""
        layout = QVBoxLayout(self)

        # File selection section
        file_group = QGroupBox("PDF File")
        file_layout = QHBoxLayout(file_group)

        self.file_label = QLabel(str(self.pdf_path) if self.pdf_path else "No file selected")
        self.file_label.setStyleSheet("color: #666;")
        file_layout.addWidget(self.file_label, 1)

        self.browse_btn = QPushButton("Browse...")
        self.browse_btn.clicked.connect(self._browse_file)
        file_layout.addWidget(self.browse_btn)

        layout.addWidget(file_group)

        # Options section
        options_group = QGroupBox("Import Options")
        options_layout = QVBoxLayout(options_group)

        self.update_existing_cb = QCheckBox("Update existing library entries with DigiKey data")
        self.update_existing_cb.setChecked(True)
        self.update_existing_cb.setToolTip(
            "If a part already exists in the library, update it with fresh DigiKey data"
        )
        options_layout.addWidget(self.update_existing_cb)

        # DigiKey status
        digikey_status = QLabel()
        if self.digikey_config and self.digikey_config.client_id:
            digikey_status.setText("DigiKey API: Configured")
            digikey_status.setStyleSheet("color: green;")
        else:
            digikey_status.setText("DigiKey API: Not configured (parts will be added with OCR data only)")
            digikey_status.setStyleSheet("color: orange;")
        options_layout.addWidget(digikey_status)

        layout.addWidget(options_group)

        # Progress section
        self.progress_group = QGroupBox("Progress")
        progress_layout = QVBoxLayout(self.progress_group)

        self.status_label = QLabel("Ready to import")
        progress_layout.addWidget(self.status_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        progress_layout.addWidget(self.progress_bar)

        layout.addWidget(self.progress_group)

        # Results section (hidden initially)
        self.results_group = QGroupBox("Results")
        self.results_group.setVisible(False)
        results_layout = QVBoxLayout(self.results_group)

        # Summary
        self.summary_label = QLabel()
        self.summary_label.setStyleSheet("font-size: 14px; padding: 10px;")
        results_layout.addWidget(self.summary_label)

        # Details table
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(5)
        self.results_table.setHorizontalHeaderLabels([
            "Device Tag", "Part Number", "Status", "Message", "DigiKey Link"
        ])
        self.results_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.results_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.results_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.results_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.results_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.results_table.setAlternatingRowColors(True)
        self.results_table.cellDoubleClicked.connect(self._on_cell_double_click)
        results_layout.addWidget(self.results_table)

        # Export button
        export_layout = QHBoxLayout()
        export_layout.addStretch()
        self.export_btn = QPushButton("Export to CSV...")
        self.export_btn.clicked.connect(self._export_csv)
        self.export_btn.setEnabled(False)
        export_layout.addWidget(self.export_btn)
        results_layout.addLayout(export_layout)

        layout.addWidget(self.results_group)

        # Errors section (hidden initially)
        self.errors_group = QGroupBox("Errors")
        self.errors_group.setVisible(False)
        errors_layout = QVBoxLayout(self.errors_group)

        self.errors_text = QTextEdit()
        self.errors_text.setReadOnly(True)
        self.errors_text.setMaximumHeight(100)
        self.errors_text.setStyleSheet("color: red;")
        errors_layout.addWidget(self.errors_text)

        layout.addWidget(self.errors_group)

        # Buttons
        button_layout = QHBoxLayout()

        self.import_btn = QPushButton("Start Import")
        self.import_btn.setDefault(True)
        self.import_btn.clicked.connect(self._start_import)
        self.import_btn.setEnabled(self.pdf_path is not None)
        button_layout.addWidget(self.import_btn)

        button_layout.addStretch()

        self.close_btn = QPushButton("Close")
        self.close_btn.clicked.connect(self.accept)
        button_layout.addWidget(self.close_btn)

        layout.addLayout(button_layout)

    def _browse_file(self) -> None:
        """Browse for PDF file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select PDF File",
            str(Path.home()),
            "PDF Files (*.pdf)"
        )

        if file_path:
            self.pdf_path = Path(file_path)
            self.file_label.setText(str(self.pdf_path))
            self.file_label.setStyleSheet("color: #333;")
            self.import_btn.setEnabled(True)

    def _start_import(self) -> None:
        """Start the import process."""
        if not self.pdf_path:
            QMessageBox.warning(self, "No File", "Please select a PDF file first.")
            return

        # Reset UI
        self.import_btn.setEnabled(False)
        self.browse_btn.setEnabled(False)
        self.results_group.setVisible(False)
        self.errors_group.setVisible(False)
        self.progress_bar.setValue(0)
        self.status_label.setText("Initializing...")

        # Create service
        service = PartsImportService(
            db_manager=self.db_manager,
            digikey_config=self.digikey_config
        )

        # Start worker thread
        self.worker = ImportWorker(
            service=service,
            pdf_path=self.pdf_path,
            update_existing=self.update_existing_cb.isChecked()
        )
        self.worker.progress.connect(self._on_progress)
        self.worker.finished.connect(self._on_finished)
        self.worker.error.connect(self._on_error)
        self.worker.start()

    def _on_progress(self, message: str, current: int, total: int) -> None:
        """Handle progress updates."""
        self.status_label.setText(message)
        if total > 0:
            self.progress_bar.setRange(0, total)
            self.progress_bar.setValue(current)
        else:
            self.progress_bar.setRange(0, 0)  # Indeterminate

    def _on_finished(self, result: ImportResult) -> None:
        """Handle import completion."""
        self.import_result = result
        self.import_btn.setEnabled(True)
        self.browse_btn.setEnabled(True)
        self.progress_bar.setValue(self.progress_bar.maximum())
        self.status_label.setText("Import complete!")

        # Show results
        self._display_results(result)

    def _on_error(self, error_message: str) -> None:
        """Handle import error."""
        self.import_btn.setEnabled(True)
        self.browse_btn.setEnabled(True)
        self.status_label.setText("Import failed!")
        self.status_label.setStyleSheet("color: red;")

        QMessageBox.critical(
            self,
            "Import Error",
            f"An error occurred during import:\n\n{error_message}"
        )

    def _display_results(self, result: ImportResult) -> None:
        """Display import results."""
        # Summary
        summary_parts = [
            f"<b>Total Parts Extracted:</b> {result.parts_extracted}",
            f"<b>Added to Library:</b> <span style='color: green;'>{result.parts_added}</span>",
            f"<b>Updated:</b> <span style='color: blue;'>{result.parts_updated}</span>",
            f"<b>Not Found in DigiKey:</b> <span style='color: orange;'>{result.parts_not_found}</span>",
            f"<b>Skipped:</b> {result.parts_skipped}",
            f"<b>Success Rate:</b> {result.success_rate:.1f}%"
        ]
        self.summary_label.setText(" | ".join(summary_parts))

        # Details table
        self.results_table.setRowCount(len(result.details))
        for row, detail in enumerate(result.details):
            # Device tag
            self.results_table.setItem(row, 0, QTableWidgetItem(detail.device_tag))

            # Part number
            self.results_table.setItem(row, 1, QTableWidgetItem(detail.part_number))

            # Status with color
            status_item = QTableWidgetItem(detail.status.value)
            if detail.status == ImportStatus.ADDED:
                status_item.setBackground(QColor(200, 255, 200))
            elif detail.status == ImportStatus.UPDATED:
                status_item.setBackground(QColor(200, 200, 255))
            elif detail.status == ImportStatus.NOT_FOUND:
                status_item.setBackground(QColor(255, 230, 200))
            elif detail.status == ImportStatus.ERROR:
                status_item.setBackground(QColor(255, 200, 200))
            self.results_table.setItem(row, 2, status_item)

            # Message
            self.results_table.setItem(row, 3, QTableWidgetItem(detail.message))

            # DigiKey link
            if detail.digikey_url:
                link_item = QTableWidgetItem("View")
                link_item.setForeground(QColor(0, 0, 255))
                link_item.setData(Qt.UserRole, detail.digikey_url)
                self.results_table.setItem(row, 4, link_item)
            else:
                self.results_table.setItem(row, 4, QTableWidgetItem("-"))

        self.results_group.setVisible(True)
        self.export_btn.setEnabled(True)

        # Show errors if any
        if result.errors:
            self.errors_text.setText("\n".join(result.errors))
            self.errors_group.setVisible(True)

    def _on_cell_double_click(self, row: int, column: int) -> None:
        """Handle double-click on results table cell."""
        if column == 4:  # DigiKey link column
            item = self.results_table.item(row, column)
            if item:
                url = item.data(Qt.UserRole)
                if url:
                    QDesktopServices.openUrl(QUrl(url))

    def _export_csv(self) -> None:
        """Export results to CSV file."""
        if not self.import_result:
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Results",
            str(Path.home() / "import_results.csv"),
            "CSV Files (*.csv)"
        )

        if not file_path:
            return

        try:
            with open(file_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    "Device Tag", "Part Number", "Status", "Message", "DigiKey URL", "Library ID"
                ])

                for detail in self.import_result.details:
                    writer.writerow([
                        detail.device_tag,
                        detail.part_number,
                        detail.status.value,
                        detail.message,
                        detail.digikey_url or "",
                        detail.library_id or ""
                    ])

            QMessageBox.information(
                self,
                "Export Complete",
                f"Results exported to:\n{file_path}"
            )

        except Exception as e:
            QMessageBox.critical(
                self,
                "Export Error",
                f"Failed to export results:\n{e}"
            )

    def closeEvent(self, event) -> None:
        """Handle dialog close."""
        if self.worker and self.worker.isRunning():
            reply = QMessageBox.question(
                self,
                "Import in Progress",
                "Import is still running. Do you want to cancel?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self.worker.terminate()
                self.worker.wait()
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()
