# DataLoadWellZones.py
import pandas as pd
from PySide2.QtWidgets import QDialog, QFileDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QCheckBox, QScrollArea, QWidget, QComboBox, QLineEdit, QMessageBox
from PySide2.QtCore import Qt

class DataLoadWellZonesDialog(QDialog):
    def __init__(self, uwi_list=None, parent=None):
        super(DataLoadWellZonesDialog, self).__init__()
        self.setWindowTitle("Load Well Zones and Attributes")
        self.setMinimumSize(600, 600)

        self.layout = QVBoxLayout(self)

        self.attribute_type_label = QLabel("Attribute Type:", self)
        self.layout.addWidget(self.attribute_type_label)

        self.attribute_type_combo = QComboBox(self)
        self.attribute_type_combo.addItems(["Well", "Zone"])
        self.attribute_type_combo.currentIndexChanged.connect(self.update_headers)
        self.layout.addWidget(self.attribute_type_combo)

        self.zone_name_label = QLabel("Zone Name:", self)
        self.layout.addWidget(self.zone_name_label)

        self.zone_name_input = QLineEdit(self)
        self.layout.addWidget(self.zone_name_input)

        self.zone_type_label = QLabel("Zone Type:", self)
        self.layout.addWidget(self.zone_type_label)

        self.zone_type_combo = QComboBox(self)
        self.zone_type_combo.addItems(["Completions", "Tests", "Production", "Injection"])
        self.layout.addWidget(self.zone_type_combo)

        self.file_button = QPushButton("Select CSV File", self)
        self.file_button.clicked.connect(self.select_file)
        self.layout.addWidget(self.file_button)

        self.file_label = QLabel("", self)
        self.layout.addWidget(self.file_label)

        self.scroll_area = QScrollArea(self)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_content = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_area.setWidget(self.scroll_content)
        self.layout.addWidget(self.scroll_area)

        self.import_button = QPushButton("Import", self)
        self.import_button.setEnabled(False)
        self.import_button.clicked.connect(self.import_data)
        self.layout.addWidget(self.import_button)

        self.file_path = None
        self.headers_checkboxes = []
        self.headers_dropdowns = []
        self.uwi_list = uwi_list

    def select_file(self):
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getOpenFileName(self, "Select CSV File", "", "CSV Files (*.csv);;All Files (*)", options=options)
        if file_path:
            self.file_path = file_path
            self.file_label.setText(file_path)
        self.clear_scroll_area()  # Clear the entire scroll area
        self.load_headers()

    def clear_scroll_area(self):
        # Create a new scroll content widget and set it as the scroll area widget
        self.scroll_content = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_area.setWidget(self.scroll_content)
        self.headers_checkboxes = []
        self.headers_dropdowns = []


    def load_headers(self):
        if not self.file_path:
            return

        df = pd.read_csv(self.file_path, nrows=0)
        headers = df.columns.tolist()

        # Clear previous checkboxes and dropdowns
        while self.scroll_layout.count():
            child = self.scroll_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        self.headers_checkboxes = []
        self.headers_dropdowns = []

        for header in headers:
            layout = QHBoxLayout()
            checkbox = QCheckBox(header, self.scroll_content)
            checkbox.setChecked(True)
            checkbox.stateChanged.connect(self.update_import_button)
            layout.addWidget(checkbox)
            self.headers_checkboxes.append(checkbox)

            dropdown = QComboBox(self.scroll_content)
            dropdown.addItems(["None", "Attribute", "UWI", "Top Depth", "Base Depth"])
            dropdown.setCurrentIndex(1)
            layout.addWidget(dropdown)
            self.headers_dropdowns.append(dropdown)

            self.scroll_layout.addLayout(layout)

        self.import_button.setEnabled(True)
        self.update_headers()

    def update_headers(self):
        attribute_type = self.attribute_type_combo.currentText()
        for dropdown in self.headers_dropdowns:
            if attribute_type == "Well":
                allowed_options = ["None", "Attribute", "UWI"]
            else:  # Zone
                allowed_options = ["None", "Attribute", "UWI", "Top Depth", "Base Depth"]
            
            current_text = dropdown.currentText()
            dropdown.clear()
            dropdown.addItems(allowed_options)
            if current_text in allowed_options:
                dropdown.setCurrentText(current_text)
            else:
                dropdown.setCurrentText("None")

    def update_import_button(self):
        any_checked = any(checkbox.isChecked() for checkbox in self.headers_checkboxes)
        self.import_button.setEnabled(any_checked)

    def import_data(self):
        if not self.file_path:
            return

        selected_headers = [checkbox.text() for checkbox in self.headers_checkboxes if checkbox.isChecked()]
        if not selected_headers:
            return

        df = pd.read_csv(self.file_path, usecols=selected_headers)

        attribute_type = self.attribute_type_combo.currentText()
        zone_name = self.zone_name_input.text().strip()
        zone_type = self.zone_type_combo.currentText()

        uwi_header = self.get_special_header("UWI")
        if not uwi_header:
            QMessageBox.warning(self, "Warning", f"Please select a UWI header for {attribute_type} attributes.")
            return

        if attribute_type == "Zone":
            top_depth_header = self.get_special_header("Top Depth")
            base_depth_header = self.get_special_header("Base Depth")
            if not (top_depth_header and base_depth_header):
                QMessageBox.warning(self, "Warning", "Please select Top Depth and Base Depth headers for Zone attributes.")
                return
        else:
            top_depth_header = base_depth_header = None

        # Validate UWIs
        print(df, self.uwi_list)
        df[uwi_header] = df[uwi_header].astype(str).str.strip()
        self.uwi_list = [uwi.strip() for uwi in self.uwi_list]

        # Validate UWIs
        valid_df = df[df[uwi_header].isin(self.uwi_list)]
        invalid_uwis = df[~df[uwi_header].isin(self.uwi_list)]

        if not invalid_uwis.empty:
            QMessageBox.warning(self, "Warning", f"Some UWIs in the CSV do not exist in the project and will be skipped:\n{invalid_uwis[uwi_header].tolist()}")

        if valid_df.empty:
            QMessageBox.warning(self, "Warning", "No valid UWIs found in the CSV.")
            return

        # Add required columns to the DataFrame
        valid_df['Attribute Type'] = attribute_type
        valid_df['Zone Name'] = zone_name
        valid_df['Zone Type'] = zone_type

        # Add Top Depth and Base Depth columns with NaN if they don't exist
        if top_depth_header:
            valid_df['Top Depth'] = valid_df[top_depth_header]
        else:
            valid_df['Top Depth'] = float('nan')

        if base_depth_header:
            valid_df['Base Depth'] = valid_df[base_depth_header]
        else:
            valid_df['Base Depth'] = float('nan')

        # Rename UWI column
        valid_df.rename(columns={uwi_header: 'UWI'}, inplace=True)

        # Reorder columns
        columns = ['UWI', 'Attribute Type', 'Zone Name', 'Zone Type', 'Top Depth', 'Base Depth'] + \
                  [col for col in valid_df.columns if col not in ['UWI', 'Attribute Type', 'Zone Name', 'Zone Type', 'Top Depth', 'Base Depth']]
        valid_df = valid_df[columns]

        self.accept()
        return valid_df, attribute_type, zone_name, zone_type, uwi_header, top_depth_header, base_depth_header


    def get_special_header(self, special_type):
        for checkbox, dropdown in zip(self.headers_checkboxes, self.headers_dropdowns):
            if dropdown.currentText() == special_type and checkbox.isChecked():
                return checkbox.text()
        return None

if __name__ == "__main__":
    import sys
    from PySide2.QtWidgets import QApplication

    app = QApplication(sys.argv)
    dialog = DataLoadWellZonesDialog()
    if dialog.exec_() == QDialog.Accepted:
        result = dialog.import_data()
        if result:
            df, attribute_type, zone_name, zone_type, uwi_header, top_depth_header, base_depth_header = result
            print(df)
            print(f"Attribute Type: {attribute_type}")
            print(f"Zone Name: {zone_name}")
            print(f"Zone Type: {zone_type}")
            print(f"UWI Header: {uwi_header}")
            print(f"Top Depth Header: {top_depth_header}")
            print(f"Base Depth Header: {base_depth_header}")
    sys.exit(app.exec_())
