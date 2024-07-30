import sys
import ast
import pandas as pd
import xml.etree.ElementTree as ET
import shutil
import os
from PySide2.QtWidgets import (
    QApplication, QDialog, QVBoxLayout, QTableWidget, QTableWidgetItem, QPushButton, QMessageBox, QHeaderView, QFileDialog, QHBoxLayout, QLineEdit, QInputDialog
)


class SWPropertiesEdit(QDialog):
    def __init__(self, zone_color_df):
        super().__init__()
        self.zone_color_df = zone_color_df
        #self.extension_name = self.ask_for_extension_name()
        #if not self.extension_name:
        #    QMessageBox.warning(self, "No Extension Name", "You must provide an extension name to proceed.")
        #    sys.exit(0)
        ## Apply the extension name to each zone name in the DataFrame
        ##self.zone_color_df['Zone Name'] = self.zone_color_df['Zone Name'].apply(lambda name: f"{self.extension_name} {name}")
        self.init_ui()
        self.new_file_path = None

    #def ask_for_extension_name(self):
    #    text, ok = QInputDialog.getText(self, 'Input Extension Name', 'Enter the extension name:')
    #    if ok and text:
    #        return text
    #    return None

    def init_ui(self):
        self.setWindowTitle("Edit Zone Properties")
        base_width = 500  # Assuming 500 as the base width for the default window size
        base_height = 400  # Assuming 400 as the base height for the default window size
        new_width = int(base_width * 3)
        new_height = int(base_height * 1.4)
        self.resize(new_width, new_height)


        layout = QVBoxLayout()

        self.table = QTableWidget()
        self.table.setRowCount(len(self.zone_color_df))
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            'Zone Name', 'Red', 'Green', 'Blue', 'Enabled', 
            'Style', 'MinWidth', 'MaxWidth'
        ])

        for row, (index, zone) in enumerate(self.zone_color_df.iterrows()):
            self.table.setItem(row, 0, QTableWidgetItem(zone['Zone Name']))
            rgb = self.clean_rgb_string(zone['Zone Color (RGB)'])
            self.table.setItem(row, 1, QTableWidgetItem(str(rgb[0])))
            self.table.setItem(row, 2, QTableWidgetItem(str(rgb[1])))
            self.table.setItem(row, 3, QTableWidgetItem(str(rgb[2])))
            self.table.setItem(row, 4, QTableWidgetItem("True"))  # Default to True
            self.table.setItem(row, 5, QTableWidgetItem("0"))  # Default to 0
            self.table.setItem(row, 6, QTableWidgetItem("7"))  # Default to 3
            self.table.setItem(row, 7, QTableWidgetItem("7"))  # Default to 3

        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.table)

        # Row layout for Select XML File button and uneditable box
        select_layout = QHBoxLayout()
        select_button = QPushButton("Select XML File")
        select_button.setMaximumWidth(self.width() // 4)
        select_button.clicked.connect(self.select_file)
        select_layout.addWidget(select_button)
        self.select_box = QLineEdit()
        self.select_box.setReadOnly(True)
        select_layout.addWidget(self.select_box)
        layout.addLayout(select_layout)

        # Row layout for Save button and uneditable box
        save_layout = QHBoxLayout()
        save_button = QPushButton("Save")
        save_button.setMaximumWidth(self.width() // 4)
        save_button.clicked.connect(self.save_data)
        save_layout.addWidget(save_button)
        self.save_box = QLineEdit()
        self.save_box.setReadOnly(True)
        save_layout.addWidget(self.save_box)
        layout.addLayout(save_layout)

        self.setLayout(layout)
        self.selected_file = None

    def clean_rgb_string(self, rgb_string):
        if isinstance(rgb_string, str):
            try:
                return ast.literal_eval(rgb_string.strip())
            except (ValueError, SyntaxError):
                return (0, 0, 0)  # Default to black if there's an error
        elif isinstance(rgb_string, tuple):
            return rgb_string
        else:
            return (0, 0, 0)  # Default to black if there's an error

    def save_data(self):
        print(f"Saving data to {self.new_file_path}")
        if not self.new_file_path:
            QMessageBox.warning(self, "No File Selected", "Please select an XML file first.")
            return

        for row in range(self.table.rowCount()):
            zone_name = self.table.item(row, 0).text()
            red = int(self.table.item(row, 1).text())
            green = int(self.table.item(row, 2).text())
            blue = int(self.table.item(row, 3).text())
            enabled = self.table.item(row, 4).text()
            style = self.table.item(row, 5).text()
            min_width = self.table.item(row, 6).text()
            max_width = self.table.item(row, 7).text()

            self.zone_color_df.loc[self.zone_color_df['Zone Name'] == zone_name, 'Zone Color (RGB)'] = str((red, green, blue))
            self.zone_color_df.loc[self.zone_color_df['Zone Name'] == zone_name, 'Enabled'] = enabled
            self.zone_color_df.loc[self.zone_color_df['Zone Name'] == zone_name, 'Style'] = style
            self.zone_color_df.loc[self.zone_color_df['Zone Name'] == zone_name, 'MinWidth'] = min_width
            self.zone_color_df.loc[self.zone_color_df['Zone Name'] == zone_name, 'MaxWidth'] = max_width

        print(f"Updating XML with path: {self.new_file_path}")
        self.update_xml(self.new_file_path)

        QMessageBox.information(self, "Success", f"Data saved successfully and XML file updated! New file: {self.new_file_path}")
        self.accept()

    def create_copy_of_file(self):
        directory = os.path.dirname(self.selected_file)
        new_file_name = 'ZoneMapDefaults.mapx'
        self.new_file_path = os.path.normpath(os.path.join(directory, new_file_name))
        shutil.copy2(self.selected_file, self.new_file_path)
        self.save_box.setText(self.new_file_path)
        print(f"New file path set to {self.new_file_path}")
        return self.new_file_path

    def select_file(self):
        options = QFileDialog.Options()
        options |= QFileDialog.ReadOnly
        file, _ = QFileDialog.getOpenFileName(self, "Select XML File", "", "XML Files (*.mapx);;All Files (*)", options=options)
        if file:
            self.selected_file = os.path.normpath(file)
            self.select_box.setText(file)  # Set the file path in the uneditable box
            QMessageBox.information(self, "File Selected", f"Selected file: {file}")
            self.new_file_path = self.create_copy_of_file()  # Ensure new_file_path is set correctly
            print(f"File selected: {file}")
            print(f"New file path after selecting: {self.new_file_path}")

    def generate_deviation_display(self, zone_name, color, enabled, style, min_width, max_width):
        deviation_display = ET.Element("DeviationDisplay")

        enabled_elem = ET.SubElement(deviation_display, "Enabled")
        enabled_elem.text = enabled

        field_name = ET.SubElement(deviation_display, "FieldName")
        field_name.text = f"Zone:{zone_name}"

        style_elem = ET.SubElement(deviation_display, "Style")
        style_elem.text = style

        min_width_elem = ET.SubElement(deviation_display, "MinWidth")
        min_width_elem.text = min_width

        max_width_elem = ET.SubElement(deviation_display, "MaxWidth")
        max_width_elem.text = max_width

        top_color = ET.SubElement(deviation_display, "TopColor", 
                                  red=str(color[0]), 
                                  green=str(color[1]), 
                                  blue=str(color[2]))
        return deviation_display

    def update_xml(self, file_path):
        print(f"Updating XML file: {file_path}")
        tree = ET.parse(file_path)
        root = tree.getroot()

        well_view = root.find(".//WellView")
        if well_view is None:
            well_view = ET.SubElement(root, "WellView")

        for _, row in self.zone_color_df.iterrows():
            zone_name = row['Zone Name']
            color = ast.literal_eval(row['Zone Color (RGB)']) if isinstance(row['Zone Color (RGB)'], str) else row['Zone Color (RGB)']
            enabled = row['Enabled']
            style = row['Style']
            min_width = row['MinWidth']
            max_width = row['MaxWidth']
            deviation_display = self.generate_deviation_display(zone_name, color, enabled, style, min_width, max_width)
            well_view.append(deviation_display)

        tree.write(file_path, xml_declaration=True, encoding='utf-8')

# Example usage
if __name__ == "__main__":
    app = QApplication(sys.argv)

    # Example DataFrame
    data = {
        "Zone Name": ["Zone 0", "Zone 1", "Zone 2", "Zone 3", "Zone 4", "Zone 5"],
        "Zone Color (Hex)": ["#ff0000", "#ffff00", "#00ff00", "#00ffff", "#0000ff", "#ff00ff"],
        "Zone Color (RGB)": ["(255, 0, 0)", "(255, 255, 0)", "(0, 255, 0)", "(0, 255, 255)", "(0, 0, 255)", "(255, 0, 255)"],
        "Enabled": ["True", "True", "True", "True", "True", "True"],
        "Style": ["0", "0", "0", "0", "0", "0"],
        "MinWidth": ["3", "3", "3", "3", "3", "3"],
        "MaxWidth": ["3", "3", "3", "3", "3", "3"]
    }
    zone_color_df = pd.DataFrame(data)

    dialog = SWPropertiesEdit(zone_color_df)
    dialog.show()

    sys.exit(app.exec_())
