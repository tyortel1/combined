import pandas as pd
import numpy as np
from PySide6.QtWidgets import (
    QApplication, QDialog, QFileDialog, QProgressDialog, 
    QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QCheckBox, 
    QScrollArea, QWidget, QComboBox, QLineEdit, QMessageBox
)
from PySide6.QtCore import Qt
from StyledDropdown import StyledDropdown
from StyledButton import StyledButton

class DataLoadWellZonesDialog(QDialog):
    def __init__(self, UWI_list=None, directional_surveys_df=None, parent=None):
        """
        Initialize the Well Zones Data Load Dialog
        
        :param UWI_list: List of Well Unique Well Identifiers
        :param directional_surveys_df: DataFrame of directional surveys
        :param parent: Parent widget
        """
        super().__init__(parent)
        
        # Dialog setup
        self.setWindowTitle("Load Well Zones and Attributes")
        self.setMinimumSize(600, 600)
        
        # Main layout
        self.layout = QVBoxLayout(self)
        
        # Zone Type Dropdown
        self.zone_type_dropdown = StyledDropdown("Zone Type:", parent=self)
        self.zone_type_dropdown.setItems(["Well", "Zone", "Intersections"])
        self.zone_type_dropdown.combo.currentIndexChanged.connect(self.update_headers)
        self.layout.addWidget(self.zone_type_dropdown)
        
        # Zone Name Input
        self.zone_name_input = StyledDropdown("Zone Name:", parent=self)
        self.zone_name_input.combo.setEditable(True)
        self.layout.addWidget(self.zone_name_input)
        
        # Unit Dropdown
        self.unit_dropdown = StyledDropdown("Unit of Measurement:", parent=self)
        self.unit_dropdown.setItems(["Feet", "Meters"])
        self.layout.addWidget(self.unit_dropdown)
        
        # File Selection Layout
        file_layout = QHBoxLayout()
        
        # Small Select CSV Button (left-aligned)
        self.file_button = StyledButton("Select CSV", "secondary")
        self.file_button.setFixedWidth(100)  # Make it small
        self.file_button.clicked.connect(self.select_file)
        file_layout.addWidget(self.file_button)
        
        # File path label
        self.file_label = QLabel("No file selected", self)
        file_layout.addWidget(self.file_label)
        file_layout.addStretch()  # Push everything to the left
        
        self.layout.addLayout(file_layout)
        
        # Scroll Area for Headers
        self.scroll_area = QScrollArea(self)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_content = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_area.setWidget(self.scroll_content)
        self.layout.addWidget(self.scroll_area)
        
        # Button Layout (for Load Data button)
        button_layout = QHBoxLayout()
        button_layout.addStretch()  # Push the button to the right
        
        # Load Data Button
        self.load_button = StyledButton("Load Data", "function")
        self.load_button.clicked.connect(self.accept_import)
        button_layout.addWidget(self.load_button)
        
        self.layout.addLayout(button_layout)
        
        # Instance variables
        self.file_path = None
        self.headers_checkboxes = []
        self.headers_dropdowns = []
        self.UWI_list = UWI_list
        self.directional_surveys_df = directional_surveys_df


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
        zone_type = self.zone_type_combo.currentText()
        for dropdown in self.headers_dropdowns:
            if zone_type == "Well":
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

    def accept_import(self):
        self.accept()

    def import_data(self):
        if not self.file_path:
            return
        
        # Show the loading dialog
        loading_dialog = QProgressDialog("Processing data, please wait...", None, 0, 0, self)
        loading_dialog.setWindowTitle("Processing")
        loading_dialog.setWindowModality(Qt.ApplicationModal)
        loading_dialog.setCancelButton(None)
        loading_dialog.show()

        try:

            selected_headers = [checkbox.text() for checkbox in self.headers_checkboxes if checkbox.isChecked()]
            if not selected_headers:
                return

            df = pd.read_csv(self.file_path, usecols=selected_headers)

            zone_type = self.zone_type_dropdown.combo.currentText()
            zone_name = self.zone_name_input.combo.currentText().strip()
            unit = self.unit_dropdown.combo.currentText()

            UWI_header = self.get_special_header("UWI")
            if not UWI_header:
                QMessageBox.warning(self, "Warning", f"Please select a UWI header for {zone_type} attributes.")
                return

            if zone_type == "Zone":
                top_depth_header = self.get_special_header("Top Depth")
                base_depth_header = self.get_special_header("Base Depth")
                if not (top_depth_header and base_depth_header):
                    QMessageBox.warning(self, "Warning", "Please select Top Depth and Base Depth headers for Zone attributes.")
                    return
            else:
                top_depth_header = base_depth_header = None


            # Validate UWIs
            df[UWI_header] = df[UWI_header].astype(str).str.strip()
            self.UWI_list = [UWI.strip() for UWI in self.UWI_list]
            valid_df = df[df[UWI_header].isin(self.UWI_list)]

           
            invalid_UWIs = df[~df[UWI_header].isin(self.UWI_list)][UWI_header].unique()
            # Convert to a list for better readability
            invalid_UWIs = invalid_UWIs.tolist()

            # Notify the user about the invalid UWIs
            if invalid_UWIs:
                QMessageBox.warning(self, "Warning", f"Some UWIs in the CSV do not exist in the project and will be skipped:\n{invalid_UWIs}")
            if valid_df.empty:
                QMessageBox.warning(self, "Warning", "No valid UWIs found in the CSV.")
                return

            # Add required columns to the DataFrame

            valid_df['Zone Name'] = zone_name
            valid_df['Zone Type'] = zone_type
        
                # Add columns for angles
           # Handle 'Zone' attribute-specific logic
            rename_map = {}
            if UWI_header:
                rename_map[UWI_header] = "UWI"
            if top_depth_header:
                rename_map[top_depth_header] = "Top Depth"
            if base_depth_header:
                rename_map[base_depth_header] = "Base Depth"

            valid_df.rename(columns=rename_map, inplace=True)

            if zone_type == "Zone":
          
                # Add columns for angles

                valid_df['Angle Top'] = None
                valid_df['Angle Base'] = None

                # Calculate offsets
                for i, row in valid_df.iterrows():
                    UWI = row['UWI']
                    top_md = row["Top Depth"]
                    base_md = row["Base Depth"]
                    top_x, top_y, base_x, base_y = self.calculate_offsets(UWI, top_md, base_md)

                    valid_df.at[i, 'Top X Offset'] = top_x
                    valid_df.at[i, 'Top Y Offset'] = top_y
                    valid_df.at[i, 'Base X Offset'] = base_x
                    valid_df.at[i, 'Base Y Offset'] = base_y

                # Reorder columns
                #columns = ['UWI', 'Attribute Type', 'Zone Name', 'Zone Type', 'Top Depth', 'Base Depth', 
                #           'Top X Offset', 'Top Y Offset', 'Base X Offset', 'Base Y Offset', 'Angle Top', 'Angle Base']
                #valid_df = valid_df[columns]

                # Calculate angles
          
                valid_df = self.calculate_angles(valid_df)

            else:
                # If attribute type is "Well", simply assign the first and last offsets from the directional survey data
                valid_df.rename(columns={UWI_header: 'UWI'}, inplace=True)



                for i, row in valid_df.iterrows():
                    UWI = row['UWI']
                    well_data = self.directional_surveys_df[self.directional_surveys_df['UWI'] == UWI]

                    if well_data.empty:
                        continue

                    # Get the first and last entries from the directional survey data
                    first_entry = well_data.iloc[0]
                    last_entry = well_data.iloc[-1]

                    # Assign the first and last offsets directly
                    valid_df.at[i, 'Top X Offset'] = first_entry['X Offset']
                    valid_df.at[i, 'Top Y Offset'] = first_entry['Y Offset']
                    valid_df.at[i, 'Base X Offset'] = last_entry['X Offset']
                    valid_df.at[i, 'Base Y Offset'] = last_entry['Y Offset']

  
            # Convert depths if necessary
            if unit == "Feet":
                if 'Top Depth' in valid_df.columns:
                    valid_df['Top Depth'] = (valid_df['Top Depth'] * 0.3048).round(2)  # Convert feet to meters and round to 2 decimals
                if 'Base Depth' in valid_df.columns:
                    valid_df['Base Depth'] = (valid_df['Base Depth'] * 0.3048).round(2)

            # Rename UWI column
            valid_df.rename(columns={UWI_header: 'UWI'}, inplace=True)



            return valid_df, zone_type, zone_name
        finally:
            # Ensure the loading dialog is closed even if an error occurs
            loading_dialog.close()



    def calculate_offsets(self, UWI, top_md, base_md):
        well_data = self.directional_surveys_df[self.directional_surveys_df['UWI'] == UWI]
        
        if well_data.empty:
            return None, None, None, None

        # Interpolate for top and base MDs
        top_x, top_y, _, _, _, _ = self.interpolate(top_md, well_data)
        base_x, base_y, _, _, _, _ = self.interpolate(base_md, well_data)
      
        return top_x, top_y, base_x, base_y

    def interpolate(self, md, data):
        # Find the two bracketing points
        below = data[data['MD'] <= (md + .1)]
        above = data[data['MD'] >= (md - .1)]
        if below.empty or above.empty:
            return None, None, None, None, None, None

        below = below.iloc[-1]
        above = above.iloc[0]

        if below['MD'] == above['MD']:  # Exact match
            return below['X Offset'], below['Y Offset'], below['X Offset'], below['Y Offset'], above['X Offset'], above['Y Offset']

        # Linear interpolation
        x = below['X Offset'] + (above['X Offset'] - below['X Offset']) * (md - below['MD']) / (above['MD'] - below['MD'])
        y = below['Y Offset'] + (above['Y Offset'] - below['Y Offset']) * (md - below['MD']) / (above['MD'] - below['MD'])
        return x, y, below['X Offset'], below['Y Offset'], above['X Offset'], above['Y Offset']

    def calculate_angles(self, valid_df):
        # Loop over each unique UWI in the valid_df
        for UWI in valid_df['UWI'].unique():
            UWI_data = valid_df[valid_df['UWI'] == UWI]

            # Extract the first and last rows for the current UWI
            first_row = UWI_data.iloc[0]
            last_row = UWI_data.iloc[-1]

            # Extract the corresponding X and Y offsets
            x1, y1 = first_row.get('Top X Offset'), first_row.get('Top Y Offset')
            x2, y2 = last_row.get('Base X Offset'), last_row.get('Base Y Offset')



            # Calculate the angle in radians
            dx, dy = x2 - x1, y1 - y2
            angle = np.arctan2(dy, dx)

            # Normalize the angle to [0, 2π)
            if angle < 0:
                angle += 2 * np.pi

            # Define target angles for snapping
            target_angles = [0, np.pi/2, np.pi, 3*np.pi/2, 2*np.pi]

            # Round to the nearest target angle and rotate by 90 degrees
            rounded_angle = min(target_angles, key=lambda x: abs(x - angle))
            rotated_angle = (rounded_angle + np.pi/2) % (2 * np.pi)

            # Update the angle for all rows with the current UWI
            valid_df.loc[valid_df['UWI'] == UWI, 'Angle Top'] = rotated_angle
            valid_df.loc[valid_df['UWI'] == UWI, 'Angle Base'] = rotated_angle
        return valid_df

    def get_special_header(self, special_type):
        for checkbox, dropdown in zip(self.headers_checkboxes, self.headers_dropdowns):
            if dropdown.currentText() == special_type and checkbox.isChecked():
                return checkbox.text()
        return None

    def get_first_xy_from_survey(self, UWI, coord):
        """Helper function to get the first X or Y value from the directional surveys."""
        survey = self.directional_surveys_df[self.directional_surveys_df['UWI'] == UWI]
        if not survey.empty:
            if coord == 'X':
                return survey.iloc[0]['X Offset']
            elif coord == 'Y':
                return survey.iloc[0]['Y Offset']
        return float('nan')

if __name__ == "__main__":
    import sys
    from PySide6.QtWidgets import QApplication

    app = QApplication(sys.argv)
    dialog = DataLoadWellZonesDialog()
    if dialog.exec_() == QDialog.Accepted:
        result = dialog.import_data()
        if result:
            df, zone_type, zone_name = result



    sys.exit(app.exec_())
