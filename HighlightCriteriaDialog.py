from PySide2.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QComboBox, QPushButton, QLineEdit, QLabel, QListWidget, QFormLayout, QColorDialog
from PySide2.QtGui import QColor, QPalette
from PySide2.QtCore import Qt
import pandas as pd

class HighlightCriteriaDialog(QDialog):
    def __init__(self, columns, existing_criteria_df=None, parent=None):
        super(HighlightCriteriaDialog, self).__init__(parent)
        self.setWindowTitle("Define Criteria")

        self.criteria = []
        self.columns = columns
        self.highlight_color = QColor(Qt.yellow)  # Default highlight color
        self.criteria_df = existing_criteria_df if existing_criteria_df is not None else pd.DataFrame(columns=['Name', 'Type', 'Column', 'Operator', 'Value', 'Logical Operator', 'Color'])
        self.criteria_name = None
        # Layouts
        self.main_layout = QVBoxLayout(self)

        # Criteria name dropdown - Editable and placed at the top
        self.criteria_name_dropdown = QComboBox(self)
        self.criteria_name_dropdown.setEditable(True)
        self.populate_criteria_names()
        self.criteria_name_dropdown.currentTextChanged.connect(self.load_criteria_from_name)

        self.main_layout.addWidget(QLabel("Criteria Name:"))
        self.main_layout.addWidget(self.criteria_name_dropdown)

        self.form_layout = QFormLayout()

        # Filter box for column search
        self.filter_box = QLineEdit(self)
        self.filter_box.setPlaceholderText("Type to filter columns and press Enter")
        self.filter_box.returnPressed.connect(self.filter_columns)

        # Column dropdown
        self.column_dropdown = QComboBox(self)
        self.column_dropdown.addItems(self.columns)

        # Add filter box and dropdown to form layout
        self.form_layout.addRow("Column Filter", self.filter_box)
        self.form_layout.addRow("Column", self.column_dropdown)

        # Comparison operator dropdown
        self.operator_dropdown = QComboBox(self)
        self.operator_dropdown.addItems(['=', '>', '<', '>=', '<=', '!='])

        # Value entry
        self.value_entry = QLineEdit(self)

        # Logical operator dropdown
        self.logical_operator_dropdown = QComboBox(self)
        self.logical_operator_dropdown.addItems(['AND', 'OR'])

        # Add to form layout
        self.form_layout.addRow("Operator", self.operator_dropdown)
        self.form_layout.addRow("Value", self.value_entry)
        self.form_layout.addRow("Logical Operator", self.logical_operator_dropdown)
        self.main_layout.addLayout(self.form_layout)

        # Buttons for adding and deleting criteria
        self.add_criterion_button = QPushButton("Add Criterion")
        self.add_criterion_button.clicked.connect(self.add_criterion)

        self.delete_criterion_button = QPushButton("Delete Criterion")
        self.delete_criterion_button.clicked.connect(self.delete_criterion)

        # Button layout for add and delete buttons
        self.button_layout = QHBoxLayout()
        self.button_layout.addWidget(self.add_criterion_button)
        self.button_layout.addWidget(self.delete_criterion_button)

        self.main_layout.addLayout(self.button_layout)

        # Criteria list
        self.criteria_list = QListWidget(self)

        # Add criteria list to the main layout
        self.main_layout.addWidget(QLabel("Current Criteria:"))
        self.main_layout.addWidget(self.criteria_list)

        # Color picker for highlight color with a preview
        self.color_button = QPushButton("Choose Highlight Color")
        self.color_button.clicked.connect(self.choose_color)

        self.color_preview = QLabel(self)
        self.color_preview.setFixedSize(20, 20)
        self.color_preview.setAutoFillBackground(True)
        self.update_color_preview()  # Initialize with the default color

        # Layout for color button and preview
        self.color_layout = QHBoxLayout()
        self.color_layout.addWidget(self.color_button)
        self.color_layout.addWidget(self.color_preview)

        self.main_layout.addLayout(self.color_layout)

        # Save and cancel buttons
        self.save_button = QPushButton("Save Criteria")
        self.save_button.clicked.connect(self.save_criteria)
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)

        # Button layout for save and cancel buttons
        self.bottom_button_layout = QHBoxLayout()
        self.bottom_button_layout.addWidget(self.save_button)
        self.bottom_button_layout.addWidget(self.cancel_button)
        self.main_layout.addLayout(self.bottom_button_layout)

    def populate_criteria_names(self):
        self.criteria_name_dropdown.addItem("")  
        """Populate the criteria dropdown with unique names from the existing criteria DataFrame."""
        if self.criteria_df is not None and not self.criteria_df.empty:
            unique_names = self.criteria_df['Name'].unique()
            self.criteria_name_dropdown.addItems(unique_names)

    def filter_columns(self):
        """Filter the column dropdown based on the text in the filter box."""
        text = self.filter_box.text().strip().lower()
        filtered_columns = [col for col in self.columns if text in col.lower()]
        self.column_dropdown.clear()
        self.column_dropdown.addItems(filtered_columns)

    def add_criterion(self):
        column = self.column_dropdown.currentText()
        operator = self.operator_dropdown.currentText()
        value = self.value_entry.text()
        logical_operator = self.logical_operator_dropdown.currentText() if not self.criteria_df.empty else None

        if column and value:
            new_criterion = pd.DataFrame({
                'Name': [self.criteria_name_dropdown.currentText()],
                'Type': ['Highlight'],
                'Column': [column],
                'Operator': [operator],
                'Value': [value],
                'Logical Operator': [logical_operator],
                'Color': [self.highlight_color.name()]
            })
            self.criteria_df = pd.concat([self.criteria_df, new_criterion], ignore_index=True)

            # Construct the text to display in the list, including the logical operator if it's not None
            criterion_text = f"{column} {operator} {value}"
            if logical_operator:
                criterion_text += f" ({logical_operator})"
        
            self.criteria_list.addItem(criterion_text)
            self.value_entry.clear()

    def delete_criterion(self):
        selected_items = self.criteria_list.selectedItems()
        if not selected_items:
            return

        for item in selected_items:
            # Extract the criterion text from the selected item
            criterion_text = item.text()
            parts = criterion_text.split(' ', 2)
            if len(parts) != 3:
                print(f"Invalid criterion format: {criterion_text}")
                continue
        
            column, operator, value = parts
            value = value.strip()  # Remove leading/trailing whitespace
    
            print(f"Attempting to delete - Column: '{column}', Operator: '{operator}', Value: '{value}'")
            print(f"Current Name selection: '{self.criteria_name_dropdown.currentText()}'")
        
            # Find the matching row in the criteria DataFrame and remove it
            matching_rows = self.criteria_df[
                (self.criteria_df['Name'].astype(str).str.strip() == self.criteria_name_dropdown.currentText().strip()) &
                (self.criteria_df['Column'].astype(str).str.strip() == column.strip()) &
                (self.criteria_df['Operator'].astype(str).str.strip() == operator.strip()) &
                (self.criteria_df['Value'].astype(str).str.strip() == value.strip())
            ]
    
            if not matching_rows.empty:
                self.criteria_df = self.criteria_df.drop(matching_rows.index)
                print(f"Deleted criterion: {criterion_text}")
            else:
                print(f"No matching criterion found for: {criterion_text}")
                print("Debugging information:")
                for _, row in self.criteria_df.iterrows():
                    print(f"Name: '{row['Name']}', Column: '{row['Column']}', Operator: '{row['Operator']}', Value: '{row['Value']}'")

            # Remove the item from the criteria list
            index = self.criteria_list.row(item)
            self.criteria_list.takeItem(index)

        # Reset the DataFrame index after dropping rows
        self.criteria_df.reset_index(drop=True, inplace=True)
    
        print("Updated criteria DataFrame:")
        print(self.criteria_df)

    def choose_color(self):
        """Open a color dialog to select a highlight color."""
        color = QColorDialog.getColor(self.highlight_color, self, "Select Highlight Color")
        if color.isValid():
            self.highlight_color = color
            self.update_color_preview()

            # Update the color for all rows in the DataFrame that match the current Name
            criteria_name = self.criteria_name_dropdown.currentText().strip()
            self.criteria_df.loc[self.criteria_df['Name'] == criteria_name, 'Color'] = color.name()

            # Optionally, update the UI or provide feedback to the user
            self.criteria_list.clear()
            self.load_criteria_from_name(criteria_name)

    def update_color_preview(self):
        """Update the preview box to show the selected color."""
        palette = self.color_preview.palette()
        palette.setColor(QPalette.Window, self.highlight_color)
        self.color_preview.setPalette(palette)

    def save_criteria(self):
        print (self.criteria_df)
        self.criteria_name = self.criteria_name_dropdown.currentText().strip()
        self.accept()
    

    def get_criteria(self):
        return self.criteria_df

    def load_criteria_from_name(self, name):
        if not self.criteria_df.empty:
            criteria = self.criteria_df[self.criteria_df['Name'] == name]
            self.criteria_list.clear()

            for _, row in criteria.iterrows():
                criterion_text = f"{row['Column']} {row['Operator']} {row['Value']}"
                self.criteria_list.addItem(criterion_text)
                self.highlight_color = QColor(row['Color'])
                self.update_color_preview()

            self.criteria_name_dropdown.setCurrentText(name)

