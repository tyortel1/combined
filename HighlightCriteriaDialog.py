from PySide6.QtWidgets import QDialog, QVBoxLayout, QListWidgetItem, QHBoxLayout, QLabel, QListWidget, QFormLayout, QColorDialog, QMessageBox
from PySide6.QtGui import QColor, QPalette
from PySide6.QtCore import Qt
import pandas as pd
from StyledTwoListSelector import TwoListSelector
from StyledDropdown import StyledDropdown, StyledInputBox, StyledBaseWidget
from StyledButton import StyledButton

# Assuming you have StyledDropdown, StyledInputBox, and StyledButton
class HighlightCriteriaDialog(QDialog):
    def __init__(self, db_manager, columns, parent=None):
        super(HighlightCriteriaDialog, self).__init__(parent)
        self.setWindowTitle("Define Criteria")
        self.db_manager = db_manager  
        self.columns = columns
        self.highlight_color = QColor(Qt.yellow)  
        self.criteria_df = pd.DataFrame(columns=['Name', 'Type', 'Column', 'Operator', 'Value', 'Logical Operator', 'Color'])

        # Define labels for alignment
        labels = ["Criteria Name", "Column", "Operator", "Value", "Operator"]
        StyledDropdown.calculate_label_width(labels)

        # Layouts
        self.main_layout = QVBoxLayout(self)

        def create_dropdown(label, items=None):
            dropdown = StyledDropdown(label)
            if items:
                dropdown.addItems(items)
            return dropdown

        def create_input(label, default_value=""):
            input_box = StyledInputBox(label, default_value)
            input_box.label.setFixedWidth(StyledDropdown.label_width) 
            return input_box

        # Criteria Name Dropdown
        self.criteria_name_dropdown = create_dropdown("Name")
        self.criteria_name_dropdown.combo.setEditable(True)
        self.criteria_name_dropdown.combo.currentTextChanged.connect(self.load_criteria_from_name)
        self.main_layout.addWidget(self.criteria_name_dropdown)

        # Form Layout
        self.form_layout = QFormLayout()

        # Column Filter
        self.filter_box = create_input("Column Filter", "")
        self.filter_box.input_field.returnPressed.connect(self.filter_columns)

        self.form_layout.addRow(self.filter_box.label, self.filter_box.input_field)


        # Column Selection
        self.column_dropdown = create_dropdown("Column", self.columns)
        self.form_layout.addRow(self.column_dropdown.label, self.column_dropdown.combo)

        # Operator Selection
        self.operator_dropdown = create_dropdown("Operator", ['=', '>', '<', '>=', '<=', '!='])
        self.form_layout.addRow(self.operator_dropdown.label, self.operator_dropdown.combo)

        # Value Input
        self.value_entry = create_input("Value", "")
        self.form_layout.addRow(self.value_entry.label, self.value_entry.input_field)

        # Logical Operator
        self.logical_operator_dropdown = create_dropdown("Logic", ['AND', 'OR'])
        self.form_layout.addRow(self.logical_operator_dropdown.label, self.logical_operator_dropdown.combo)

        self.main_layout.addLayout(self.form_layout)

        # Set a standard button size (match "Delete" button size)
        button_size = (80, 25)  # Width x Height

        # Add/Delete Criteria Buttons
        self.add_criterion_button = StyledButton("Add", "function")
        self.delete_criterion_button = StyledButton("Delete", "close")

        self.add_criterion_button.setFixedSize(*button_size)
        self.delete_criterion_button.setFixedSize(*button_size)

        self.add_criterion_button.clicked.connect(self.add_criterion)
        self.delete_criterion_button.clicked.connect(self.delete_criterion)

        button_layout = QHBoxLayout()
        button_layout.addStretch()  # Push buttons to the right
        button_layout.addWidget(self.add_criterion_button)
        button_layout.addWidget(self.delete_criterion_button)
        self.main_layout.addLayout(button_layout)

        # Criteria List
        self.criteria_list = QListWidget(self)
        self.criteria_list.setEditTriggers(QListWidget.DoubleClicked)
        self.criteria_list.itemChanged.connect(self.edit_criterion_value)
        self.main_layout.addWidget(QLabel("Current Criteria:"))
        self.main_layout.addWidget(self.criteria_list)

        # Highlight Color Picker
        self.color_button = StyledButton("Color", "color")
        self.color_button.setFixedSize(*button_size)  # Force same size as other buttons
        self.color_button.clicked.connect(self.choose_color)

        self.color_preview = QLabel(self)
        self.color_preview.setFixedSize(button_size[0], button_size[1])  # Match button size
        self.color_preview.setAutoFillBackground(True)
        self.update_color_preview()

        color_layout = QHBoxLayout()
        color_layout.addStretch()  # Push to the right
        color_layout.addWidget(self.color_button)
        color_layout.addWidget(self.color_preview)
        self.main_layout.addLayout(color_layout)

        # Save and Cancel Buttons
        self.save_button = StyledButton("Save", "function")
        self.cancel_button = StyledButton("Cancel", "close")

        self.save_button.setFixedSize(*button_size)
        self.cancel_button.setFixedSize(*button_size)

        self.save_button.clicked.connect(self.save_criteria)
        self.cancel_button.clicked.connect(self.reject)

        bottom_button_layout = QHBoxLayout()
        bottom_button_layout.addStretch()
        bottom_button_layout.addWidget(self.save_button)
        bottom_button_layout.addWidget(self.cancel_button)
        self.main_layout.addLayout(bottom_button_layout)

        self.populate_criteria_names()


    def populate_criteria_names(self):
        self.criteria_name_dropdown.combo.clear()
        self.criteria_name_dropdown.combo.addItem("")
        criteria_names = self.db_manager.load_criteria_names()
        self.criteria_name_dropdown.combo.addItems(criteria_names)

    def filter_columns(self):
        text = self.filter_box.input_field.text().strip().lower()  # ✅ Fix
        filtered_columns = [col for col in self.columns if text in col.lower()]
        self.column_dropdown.combo.clear()  # ✅ Fix
        self.column_dropdown.combo.addItems(filtered_columns)  # ✅ Fix

    def load_criteria_from_name(self, name):
        """Load criteria conditions and set highlight color without clearing if renaming."""
        if not name:
            print("No criteria name provided to load.")  # Debugging output
            return

        print(f"Loading criteria for: {name}")  # Debugging output

        # Load color and conditions from the database
        highlight_color, conditions = self.db_manager.load_criteria_by_name(name)

        if highlight_color is None or conditions is None:
            print(f"No criteria found for '{name}'.")  # Debugging output
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

        print(f"Loaded {len(conditions)} criteria for '{name}'.")  # Debugging output





    def add_criterion(self):
        column = self.column_dropdown.combo.currentText()
        operator = self.operator_dropdown.combo.currentText()
        value = self.value_entry.input_field.text()
        logical_operator = self.logical_operator_dropdown.combo.currentText() if not self.criteria_df.empty else None

        if column and value:
            new_criterion = pd.DataFrame({
                'Name': [self.criteria_name_dropdown.combo.currentText()],
                'Type': ['Highlight'],
                'Column': [column],
                'Operator': [operator],
                'Value': [value],
                'Logical Operator': [logical_operator],
                'Color': [self.highlight_color.name()]
            })
            self.criteria_df = pd.concat([self.criteria_df, new_criterion], ignore_index=True)

            criterion_text = f"{column} {operator} {value}"
            if logical_operator:
                criterion_text += f" ({logical_operator})"

            item = QListWidgetItem(criterion_text)
            item.setFlags(item.flags() | Qt.ItemIsEditable)
            item.setData(Qt.UserRole, criterion_text)

            self.criteria_list.addItem(item)
            self.value_entry.input_field.clear()

    def delete_criterion(self):
        selected_items = self.criteria_list.selectedItems()
        if not selected_items:
            return

        for item in selected_items:
            self.criteria_list.takeItem(self.criteria_list.row(item))




    def edit_criterion_value(self, item):
        """Update the database when a criterion value is edited in the list."""
        if not item:
            return

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




    def choose_color(self):
        color = QColorDialog.getColor(self.highlight_color, self, "Select Highlight Color")
        if color.isValid():
            self.highlight_color = color
            self.update_color_preview()


    def load_criteria_from_name(self, name):
        """Load criteria conditions and set highlight color."""
        if not name:
            return

        # Load color and conditions from the database
        highlight_color, conditions = self.db_manager.load_criteria_by_name(name)

        if highlight_color is None:
            return  # No criteria found

        # Clear current criteria list
        self.criteria_list.clear()

        # Populate the criteria list
        for column, operator, value, logical_operator in conditions:
            criterion_text = f"{column} {operator} {value}"
            if logical_operator:
                criterion_text += f" ({logical_operator})"

            item = QListWidgetItem(criterion_text)
            item.setFlags(item.flags() | Qt.ItemIsEditable)  # Allow item to be edited
            item.setData(Qt.UserRole, criterion_text)  # Store original value for tracking
            self.criteria_list.addItem(item)

        # Set highlight color
        self.highlight_color = QColor(highlight_color)
        self.update_color_preview()


    def update_color_preview(self):
        palette = self.color_preview.palette()
        palette.setColor(QPalette.Window, self.highlight_color)
        self.color_preview.setPalette(palette)

    def save_criteria(self):
        criteria_name = self.criteria_name_dropdown.combo.currentText().strip()
        if not criteria_name:
            QMessageBox.warning(self, "Error", "Criteria Name cannot be blank.")
            return

        criteria_list = []
        for i in range(self.criteria_list.count()):
            criterion_text = self.criteria_list.item(i).text()
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

            criteria_list.append((column, operator, value.strip(), logical_operator))

        success, message = self.db_manager.save_criteria(criteria_name, self.highlight_color.name(), criteria_list)
        if success:
            QMessageBox.information(self, "Success", message)
            self.accept()
        else:


            QMessageBox.warning(self, "Error", message)



if __name__ == "__main__":
    import sys
    from PySide6.QtWidgets import QApplication

    # Example DataFrame (for testing)
    data = {
        'Column1': [300, 400, 500, 600, 300, 200, 250],
        'Column2': [50, 30, 80, 20, 70, 10, 60],
        'Column3': [1, 2, 1, 3, 2, 1, 2],
    }
    master_df = pd.DataFrame(data)
    columns = list(master_df.columns)  # Extract column names for dropdowns

    # Mock DB Manager for testing
    class MockDBManager:
        def load_criteria_names(self):
            return ["Test Criteria 1", "Test Criteria 2"]
        
        def save_criteria(self, *args, **kwargs):
            print("Mock Save Called:", args, kwargs)
            return True, "Mock Save Success"

        def load_criteria_by_name(self, name):
            return "#FFFF00", [
                ("Column1", ">", "200", "AND"),
                ("Column2", "<", "50", None)
            ]

    app = QApplication(sys.argv)
    dialog = HighlightCriteriaDialog(db_manager=MockDBManager(), columns=columns)
    dialog.exec_()
