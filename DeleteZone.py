from PySide6.QtWidgets import QDialog, QVBoxLayout, QComboBox, QPushButton, QMessageBox

class DeleteZone(QDialog):
    def __init__(self, df, zone_names, parent=None):
        super().__init__(parent)
        self.df = df
        self.zone_names = zone_names

        # Dialog layout and controls setup
        layout = QVBoxLayout(self)

        # Dropdown for zone names
        self.zone_dropdown = QComboBox(self)
        self.zone_dropdown.addItems(self.zone_names)
        layout.addWidget(self.zone_dropdown)

        # Delete button
        self.delete_button = QPushButton("Delete Zone", self)
        self.delete_button.clicked.connect(self.delete_selected_zone)
        layout.addWidget(self.delete_button)

    def delete_selected_zone(self):
        selected_zone = self.zone_dropdown.currentText()

        if not selected_zone:
            QMessageBox.warning(self, "No Selection", "Please select a zone to delete.")
            return

        reply = QMessageBox.question(
            self, 'Confirm Deletion',
            f"Are you sure you want to delete the zone '{selected_zone}'?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            if 'Zone Name' in self.df.columns:
                self.df = self.df[self.df['Zone Name'] != selected_zone]
                self.zone_names.remove(selected_zone)
                QMessageBox.information(self, "Success", f"Zone '{selected_zone}' deleted successfully.")
                self.accept()  # Close the dialog after deletion
            else:
                QMessageBox.warning(self, "Error", "'Zone Name' column not found in DataFrame.")
