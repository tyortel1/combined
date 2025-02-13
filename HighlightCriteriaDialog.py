from PySide6.QtWidgets import QDialog, QVBoxLayout, QListWidgetItem, QHBoxLayout, QComboBox, QMessageBox, QPushButton, QLineEdit, QLabel, QListWidget, QFormLayout, QColorDialog
from PySide6.QtGui import QColor, QPalette
from PySide6.QtCore import Qt
import pandas as pd

class HighlightCriteriaDialog(QDialog):
    def __init__(self, db_manager, columns, parent=None):
        super(HighlightCriteriaDialog, self).__init__(parent)
        self.setWindowTitle("Define Criteria")

        self.db_manager = db_manager  # Store the database manager
        self.criteria = []
        self.columns = columns
        self.highlight_color = QColor(Qt.yellow)  # Default highlight color
        self.criteria_name = None
        self.criteria_df = pd.DataFrame(columns=['Name', 'Type', 'Column', 'Operator', 'Value', 'Logical Operator', 'Color'])


        # Layouts
        self.main_layout = QVBoxLayout(self)

        # Criteria name dropdown - Editable and placed at the top
        self.criteria_name_dropdown = QComboBox(self)
        self.criteria_name_dropdown.setEditable(True)
        self.criteria_name_dropdown.currentTextChanged.connect(self.load_criteria_from_name)

        self.main_layout.addWidget(QLabel("Criteria Name:"))
        self.main_layout.addWidget(self.criteria_name_dropdown)

        # **Populate the dropdown AFTER it's created**
        self.populate_criteria_names()

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
        self.criteria_list.setEditTriggers(QListWidget.DoubleClicked)
        self.criteria_list.itemChanged.connect(self.edit_criterion_value)

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
        """Load criteria names from the database into the dropdown."""
        self.criteria_name_dropdown.clear()
        self.criteria_name_dropdown.addItem("")  # Allow empty selection

        criteria_names = self.db_manager.load_criteria_names()
        self.criteria_name_dropdown.addItems(criteria_names)


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

            # Construct the text to display in the list
            criterion_text = f"{column} {operator} {value}"
            if logical_operator:
                criterion_text += f" ({logical_operator})"

            item = QListWidgetItem(criterion_text)
            item.setFlags(item.flags() | Qt.ItemIsEditable)  # Enable inline editing
            item.setData(Qt.UserRole, criterion_text)  # Store original value

            self.criteria_list.addItem(item)
            self.value_entry.clear()


    def delete_criterion(self):
        """Delete selected criterion from the database."""
        selected_items = self.criteria_list.selectedItems()
        if not selected_items:
            return

        for item in selected_items:
            criterion_text = item.text().strip()

            # Extract column, operator, and value
            for operator in ['>=', '<=', '!=', '>', '<', '=']:
                if operator in criterion_text:
                    parts = criterion_text.split(operator, 1)
                    if len(parts) == 2:
                        column, value = parts[0].strip(), parts[1].strip()
                        break
            else:
                continue

            logical_operator = None
            if "(" in value and ")" in value:
                value, logical_operator = value.split("(", 1)
                logical_operator = logical_operator.strip(")")

            # Delete from database
            self.db_manager.delete_criteria_condition(self.criteria_name_dropdown.currentText(), column, operator, value, logical_operator)

            # Remove from UI
            index = self.criteria_list.row(item)
            self.criteria_list.takeItem(index)

        


    def choose_color(self):
        """Open a color dialog to select a highlight color and save it to the database."""
        color = QColorDialog.getColor(self.highlight_color, self, "Select Highlight Color")
        if color.isValid():
            self.highlight_color = color
            self.update_color_preview()

            # Update color in the database
            self.db_manager.update_criteria_color(self.criteria_name_dropdown.currentText(), color.name())

            # Reload criteria
            self.load_criteria_from_name(self.criteria_name_dropdown.currentText())

    def update_color_preview(self):
        """Update the preview box to show the selected color."""
        palette = self.color_preview.palette()
        palette.setColor(QPalette.Window, self.highlight_color)
        self.color_preview.setPalette(palette)

    def save_criteria(self):
        """Save criteria to the database."""
        criteria_name = self.criteria_name_dropdown.currentText().strip()

        if not criteria_name:
            QMessageBox.warning(self, "Error", "Criteria Name cannot be blank.")
            return

        # Prepare criteria list
        criteria_list = []
        for i in range(self.criteria_list.count()):
            criterion_text = self.criteria_list.item(i).text()

            # Extract column, operator, and value
            for operator in ['>=', '<=', '!=', '>', '<', '=']:
                if operator in criterion_text:
                    parts = criterion_text.split(operator, 1)
                    if len(parts) == 2:
                        column, value = parts[0].strip(), parts[1].strip()
                        break
            else:
                continue  # Skip if no valid operator is found

            logical_operator = None
            if "(" in value and ")" in value:
                value, logical_operator = value.split("(", 1)
                logical_operator = logical_operator.strip(")")

            criteria_list.append((column, operator, value.strip(), logical_operator))

        # Save criteria to the database
        success, message = self.db_manager.save_criteria(criteria_name, self.highlight_color.name(), criteria_list)

        if success:
            QMessageBox.information(self, "Success", message)
            self.accept()
        else:
            QMessageBox.warning(self, "Error", message)


    def get_criteria(self):
        """Fetch criteria from the database instead of using a DataFrame."""
        return self.db_manager.load_all_criteria()

    def load_criteria_from_name(self, name):
        """Load criteria conditions and set highlight color without clearing if renaming."""
        if not name:
            return

        # Load color and conditions from the database
        highlight_color, conditions = self.db_manager.load_criteria_by_name(name)

        if highlight_color is None:
            return  # No criteria found

        # Preserve list if renaming, otherwise clear it
        self.criteria_list.clear()

        for column, operator, value, logical_operator in conditions:
            criterion_text = f"{column} {operator} {value}"
            if logical_operator:
                criterion_text += f" ({logical_operator})"

            item = QListWidgetItem(criterion_text)
            item.setFlags(item.flags() | Qt.ItemIsEditable)  # Allow item to be editable
            item.setData(Qt.UserRole, criterion_text)  # Store original value for comparison
            self.criteria_list.addItem(item)

        # Set highlight color
        self.highlight_color = QColor(highlight_color)
        self.update_color_preview()





    def edit_criterion_value(self, item):
        """Update the database when a criterion value is edited in the list."""
        new_text = item.text().strip()

        # Extract column, operator, and value
        for operator in ['>=', '<=', '!=', '>', '<', '=']:
            if operator in new_text:
                parts = new_text.split(operator, 1)
                if len(parts) == 2:
                    column, new_value = parts[0].strip(), parts[1].strip()
                    break
        else:
            return  # Skip if no valid operator is found

        logical_operator = None
        if "(" in new_value and ")" in new_value:
            new_value, logical_operator = new_value.split("(", 1)
            logical_operator = logical_operator.strip(")")

        # Retrieve the old value from Qt.UserRole
        old_text = item.data(Qt.UserRole)

        if old_text:
            for operator in ['>=', '<=', '!=', '>', '<', '=']:
                if operator in old_text:
                    parts = old_text.split(operator, 1)
                    if len(parts) == 2:
                        old_column, old_value = parts[0].strip(), parts[1].strip()
                        break
        else:
            return  # If no old value is stored, skip update

        # Update DataFrame only if value changed
        if old_column == column and old_value != new_value:
            self.criteria_df.loc[(self.criteria_df['Column'] == column) & 
                                 (self.criteria_df['Operator'] == operator) & 
                                 (self.criteria_df['Value'] == old_value), 'Value'] = new_value

            print(f"Updated {old_column}: {old_value} → {new_value} in DataFrame")
    
        # Store new value in Qt.UserRole for tracking future edits
        item.setData(Qt.UserRole, new_text)







