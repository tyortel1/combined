from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QComboBox, QLineEdit, QPushButton, QMessageBox
import pandas as pd

class CriteriaToZoneDialog(QDialog):
    def __init__(self, df, df_criteria, parent=None):
        super(CriteriaToZoneDialog, self).__init__(parent)
        self.setWindowTitle("Save Criteria as Attribute")
        self.resize(400, 200)
        
        self.df = df
        self.df_criteria = df_criteria
        self.attribute_name = None

        # Layout for the dialog
        layout = QVBoxLayout(self)

        # Criteria dropdown
        layout.addWidget(QLabel("Select Criteria:"))
        self.criteria_dropdown = QComboBox(self)
        self.criteria_dropdown.addItems(self.df_criteria['Name'].unique())
        layout.addWidget(self.criteria_dropdown)

        # Attribute name input
        layout.addWidget(QLabel("Attribute Name:"))
        self.attribute_name_input = QLineEdit(self)
        layout.addWidget(self.attribute_name_input)

        # Save button
        self.save_button = QPushButton("Save", self)
        self.save_button.clicked.connect(self.save_criteria_as_attribute)
        layout.addWidget(self.save_button)

    def save_criteria_as_attribute(self):
        selected_criteria = self.criteria_dropdown.currentText()
        self.attribute_name = self.attribute_name_input.text().strip()

        if not self.attribute_name:
            QMessageBox.warning(self, "Input Error", "Please provide an attribute name.")
            return

        # Initialize the new column with 0s
        self.df[self.attribute_name] = 0

        # Get the criteria conditions
        criteria_conditions = self.df_criteria[self.df_criteria['Name'] == selected_criteria]
    
        # Initialize final_mask with all True values (or False, depending on your logic)
        final_mask = pd.Series([True] * len(self.df), index=self.df.index)
    
        # Use this temporary mask for OR conditions
        temp_mask = pd.Series([False] * len(self.df), index=self.df.index)

        # Apply the criteria to each row in the DataFrame
        for _, criterion in criteria_conditions.iterrows():
            column = criterion['Column']
            operator = criterion['Operator']
            value = criterion['Value']
            logical_operator = criterion.get('Logical Operator', 'AND')

            # Apply the filter condition based on the operator
            if operator == '=':
                mask = self.df[column] == value
            elif operator == '>':
                mask = self.df[column] > float(value)
            elif operator == '<':
                mask = self.df[column] < float(value)
            elif operator == '>=':
                mask = self.df[column] >= float(value)
            elif operator == '<=':
                mask = self.df[column] <= float(value)
            elif operator == '!=':
                mask = self.df[column] != value
            else:
                mask = pd.Series([False] * len(self.df), index=self.df.index)

            # Combine masks using the logical operator
            if logical_operator == 'AND':
                final_mask &= mask
            elif logical_operator == 'OR':
                temp_mask |= mask

        # If OR conditions were used, combine them with the final mask
        final_mask |= temp_mask

        # Set the attribute column based on the final mask
        self.df.loc[final_mask, self.attribute_name] = 1
        print(self.df)
        self.accept()
