from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QMessageBox
from PySide6.QtCore import Qt
import pandas as pd
from StyledDropdown import StyledDropdown, StyledInputBox, StyledBaseWidget
from StyledButton import StyledButton



class CriteriaToZoneDialog(QDialog):
    def __init__(self, df, db_manager, zone_name, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Save Criteria as Attribute")
        self.resize(400, 200)

        self.df = df
        self.db_manager = db_manager
        self.zone_name = str(zone_name).strip()
        self.attribute_name = None

        # Define labels for alignment
        labels = ["Select criteria", "Attribute name"]
        StyledDropdown.calculate_label_width(labels)

        # Main layout
        self.main_layout = QVBoxLayout(self)

        # Helper functions
        def create_dropdown(label, items=None):
            dropdown = StyledDropdown(label)
            if items:
                dropdown.addItems(items)
            dropdown.setStyleSheet("""
                QLabel, QComboBox {
                    background-color: transparent;
                    border: none;
                    padding: 0;
                    margin: 0;
                }
            """)
            return dropdown

        def create_input(label, default_value=""):
            input_box = StyledInputBox(label, default_value)
            input_box.label.setFixedWidth(StyledDropdown.label_width)
            return input_box

        # Criteria dropdown
        criteria_names = self.db_manager.load_criteria_names()
        if not criteria_names:
            QMessageBox.warning(self, "No Criteria", "No criteria found in database. Please create criteria first.")
            self.reject()
            return

        criteria_names.insert(0, "None")
        self.criteria_dropdown = create_dropdown("Select criteria:", criteria_names)
        self.main_layout.addWidget(self.criteria_dropdown)

        # Attribute name input
        self.attribute_name_input = create_input("Attribute name:")
        self.main_layout.addWidget(self.attribute_name_input)

        # Button layout (for right alignment)
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        # Save button
        self.save_button = StyledButton("Save", button_type="function")
        self.save_button.clicked.connect(self.save_criteria_as_attribute)
        button_layout.addWidget(self.save_button)

        # Close button
        self.close_button = StyledButton("Close", button_type="function")
        self.close_button.clicked.connect(self.reject)
        button_layout.addWidget(self.close_button)

        self.main_layout.addLayout(button_layout)

    def save_criteria_as_attribute(self):
        selected_criteria = self.criteria_dropdown.currentText()
        self.attribute_name = self.attribute_name_input.text().strip()

        if not self.attribute_name:
            QMessageBox.warning(self, "Input Error", "Please provide an attribute name.")
            return


        print(f"\n🔹 Applying Criteria to Zone: {self.zone_name}")

        # Initialize the new column with 0s
        self.df[self.attribute_name] = 0

        # Get criteria from database
        _, conditions = self.db_manager.load_criteria_by_name(selected_criteria)
        if not conditions:
            QMessageBox.warning(self, "Criteria Not Found", "No matching criteria found.")
            return

        print(f"\n🔹 Applying Criteria: {selected_criteria}")
        print(conditions)

        # Start with a mask of all True values (AND logic)
        group_mask = pd.Series(True, index=self.df.index)
        
        for column, operator, value, logical_op in conditions:
            print(f"Applying condition: {column} {operator} {value} (Logical: {logical_op})")
        
            try:
                numeric_col = pd.to_numeric(self.df[column], errors='coerce')
                if operator == '=':
                    mask = numeric_col == float(value)
                elif operator == '>':
                    mask = numeric_col > float(value)
                elif operator == '<':
                    mask = numeric_col < float(value)
                elif operator == '>=':
                    mask = numeric_col >= float(value)
                elif operator == '<=':
                    mask = numeric_col <= float(value)
                elif operator == '!=':
                    mask = numeric_col != float(value)
                else:
                    print(f"❌ Unsupported operator: {operator}")
                    continue
                    
                # Apply AND/OR logic
                if logical_op == 'OR':
                    group_mask |= mask  # OR logic
                else:
                    group_mask &= mask  # AND logic (default)
                    
            except Exception as e:
                print(f"❌ Error processing criterion: {e}")

        # Set the attribute to 1 for rows that match the criteria
        self.df.loc[group_mask, self.attribute_name] = 1

        print("\n🔹 Final Mask Summary:")
        print(f"  - Total rows selected: {group_mask.sum()}")
        print(f"  - Sample selected rows:")
        print(self.df[group_mask].head().to_string())
        print(f"  - Table Name: {self.zone_name}")

        print(f"\n  Updated DataFrame with new attribute '{self.attribute_name}':")
        print(self.df[[self.attribute_name]].value_counts())

        if self.db_manager:
            # Update database with new attribute
            success = self.db_manager.update_zone_column_data(self.zone_name, self.attribute_name, self.df)
            
            if success:
                print(f"  Successfully saved '{self.attribute_name}' to database.")
            else:
                print(f"❌ Failed to save '{self.attribute_name}' to database.")

        self.accept()