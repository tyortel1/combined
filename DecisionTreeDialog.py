from PySide6.QtWidgets import (QDialog, QListWidget, QVBoxLayout, QTextEdit, 
    QFormLayout, QPushButton, QSpacerItem, QSizePolicy, QLabel, QMessageBox, 
    QHBoxLayout, QListWidgetItem, QComboBox, QLineEdit, QColorDialog)
from PySide6.QtGui import QIcon, QColor, QPalette
from PySide6.QtCore import Qt
from sklearn.tree import DecisionTreeClassifier, DecisionTreeRegressor, _tree
import numpy as np
from collections import defaultdict, Counter
from HighlightCriteriaDialog import HighlightCriteriaDialog
import pandas as pd
from PySide6.QtCore import Signal
from StyledTwoListSelector import TwoListSelector
from StyledDropdown import StyledDropdown, StyledInputBox, StyledBaseWidget
from StyledButton import StyledButton



class DecisionTreeDialog(QDialog):



    criteriaGenerated = Signal(pd.DataFrame)
    def __init__(self, master_df, db_manager, parent=None):
        super().__init__(parent)
        print("DecisionTreeDialog initialization started")
    
        # Detailed input validation
        print(f"Master DataFrame shape: {master_df.shape}")
        print(f"Columns: {list(master_df.columns)}")
        print(f"Database Manager: {db_manager}")
    
        # Create a deep copy of the DataFrame at initialization
        self.master_df = master_df.copy()
        self.db_manager = db_manager 
    
        try:
            print("About to call initUI()")
            self.initUI()
            print("initUI() completed successfully")
        
            # Explicit visibility settings
            self.setWindowFlags(Qt.Window)  # Ensure it's a window
            self.setWindowModality(Qt.NonModal)
            self.setAttribute(Qt.WA_DontCreateNativeAncestors)
            self.setAttribute(Qt.WA_ShowWithoutActivating)
        
            # Force visibility
            print("Attempting to make dialog visible")
            self.setVisible(True)
        
        except Exception as e:
            print(f"Error in initialization: {e}")
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "Initialization Error", str(e))

    def show(self):
        print("Custom show method called")
        super().show()
        self.raise_()  # Bring to front
        self.activateWindow() 

    def initUI(self):
        self.setWindowTitle("Decision Tree Selection")
        self.setGeometry(100, 100, 800, 600)

        # Calculate label widths for consistent alignment
        labels = [
            "Outcome",    # Used by outcome dropdown
            "Operator",   # Used by threshold operator dropdown
            "Value",      # Used by threshold value input
        ]
        StyledDropdown.calculate_label_width(labels)
    

        # Set dialog styling
        self.setStyleSheet("""
            QDialog {
                background-color: white;
            }
            QLabel {
                color: black;
            }
            QPushButton {
                background-color: white;
                border: none;
            }
        """)

        def create_dropdown(label):
            dropdown = StyledDropdown(label)
            dropdown.setStyleSheet("""
                QLabel, QComboBox {
                    background-color: transparent;
                    border: none;
                    padding: 0;
                    margin: 0;
                }
            """)
            return dropdown
        def create_input(label, default_value='', validator=None):
            input_box = StyledInputBox(label, default_value, validator)
            input_box.label.setFixedWidth(StyledDropdown.label_width)  # Set width explicitly
            input_box.setStyleSheet("""
                QLabel {
                    background-color: transparent;
                    border: none;
                    padding: 0;
                    margin: 0;
                }
            """)
            return input_box

        main_layout = QVBoxLayout(self)
    
        # Outcome selection layout
        outcome_layout = QHBoxLayout()
        self.outcome_dropdown = create_dropdown("Outcome")
        available_columns = sorted([col for col in self.master_df.columns])
        self.outcome_dropdown.addItems(available_columns)
        self.outcome_dropdown.combo.currentIndexChanged.connect(self.reset_master_df)
        outcome_layout.addWidget(self.outcome_dropdown)
        outcome_layout.addStretch()

        threshold_layout = QVBoxLayout()  # Change to vertical layout

        self.threshold_operator = create_dropdown("Operator")  # Matches labels list
        self.threshold_operator.addItems(['>', '<', '=', '>=', '<='])
        threshold_layout.addWidget(self.threshold_operator)

        # Create value input and add below operator
        self.threshold_value = create_input("Value", "0")  # Matches labels list
        threshold_layout.addWidget(self.threshold_value)

        # Create a container for the threshold section
        threshold_container = QHBoxLayout()
        threshold_container.addLayout(threshold_layout)
        threshold_container.addStretch()
    
        # Initialize TwoListSelector for attributes
        self.attribute_selector = TwoListSelector(
            "Available Attributes", 
            "Selected Attributes"
        )
        self.attribute_selector.setStyleSheet("""
            QLabel {
                background-color: transparent;
                border: none;
                padding: 0;
                margin: 0;
            }
        """)
    
        # Populate available attributes
        self.attribute_selector.set_left_items(available_columns)
    
        # Buttons in bottom right
        button_layout = QHBoxLayout()
        button_layout.addStretch()
    
        self.run_button = StyledButton("Run", "function")
        self.close_button = StyledButton("Close", "close")
    
        # Set fixed size for buttons
        self.run_button.setFixedSize(80, 25)
        self.close_button.setFixedSize(80, 25)
    
        self.run_button.clicked.connect(self.build_decision_tree)
        self.close_button.clicked.connect(self.reject)
    
        button_layout.addWidget(self.run_button)
        button_layout.addWidget(self.close_button)
    
        # Add all components to main layout in the correct order
        main_layout.addLayout(outcome_layout)
        main_layout.addLayout(threshold_container)  # Use container instead of threshold_layout
        main_layout.addWidget(self.attribute_selector)
        main_layout.addLayout(button_layout)
    
        # Add some spacing between sections
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(10, 10, 10, 10)


    def build_decision_tree(self):
        # Get selected attributes from new TwoListSelector
        selected_attributes = self.attribute_selector.get_right_items()
        # Get selected outcome from StyledDropdown
        selected_outcome = self.outcome_dropdown.combo.currentText()
    
        if len(selected_attributes) > 0:
            relevant_columns = selected_attributes + [selected_outcome]
            self.df_filtered = self.master_df[relevant_columns].copy()
        
            # Just remove NA values - we'll handle the comparison in plot_decision_tree
            self.df_filtered = self.df_filtered.loc[
                self.df_filtered[selected_outcome].notna()
            ]

            # Get user-specified threshold and operator
            threshold_value = float(self.threshold_value.text())
            operator = self.threshold_operator.combo.currentText()
        
            print(f"\nUsing {operator} {threshold_value} for outcome {selected_outcome}")
            predicted_outcomes = self.plot_decision_tree(selected_attributes, selected_outcome, threshold_value)
        
            if predicted_outcomes is not None:
                # Calculate total matches based on our criteria
                matching_count = predicted_outcomes.sum()
                total_possible = len(self.master_df)
                match_rate = matching_count / total_possible
                print(f"Found {matching_count} matches out of {total_possible} total rows ({match_rate:.2%})")

    def analyze_most_likely_values(self, attributes, outcome):
        try:
            print("Starting analysis...")
            analysis_results = []
        
            # Get our threshold criteria
            operator = self.threshold_operator.combo.currentText()
            threshold_value = float(self.threshold_value.text())
        
            # Make a copy of df_filtered
            working_df = self.df_filtered.copy()
        
            for attribute in attributes:
                print(f"Processing attribute: {attribute}")
            
                # Handle nulls and convert to numeric
                working_df.loc[:, attribute] = working_df[attribute].fillna(0)
                working_df.loc[:, attribute] = pd.to_numeric(working_df[attribute], errors='coerce').fillna(0)
            
                if pd.api.types.is_numeric_dtype(working_df[attribute]):
                    # Find matching rows based on our criteria
                    if operator == '>':
                        matching_rows = working_df[outcome] > threshold_value
                    elif operator == '<':
                        matching_rows = working_df[outcome] < threshold_value
                    elif operator == '=':
                        matching_rows = np.abs(working_df[outcome] - threshold_value) < 1e-6
                    elif operator == '>=':
                        matching_rows = working_df[outcome] >= threshold_value
                    elif operator == '<=':
                        matching_rows = working_df[outcome] <= threshold_value
                
                    # Get attribute values where our condition is met
                    matching_values = working_df.loc[matching_rows, attribute]
                
                    if not matching_values.empty:
                        q1 = matching_values.quantile(0.25)
                        q3 = matching_values.quantile(0.75)
                    
                        # Add to analysis results
                        analysis_results.append({
                            "Attribute": attribute,
                            "Condition": f"between {q1:.2f} and {q3:.2f}"
                        })
                    
                        print(f"Analysis for {attribute}: between {q1:.2f} and {q3:.2f}")
        
            print("Final analysis results:", analysis_results)
            self.show_result_dialog(analysis_results)

        except Exception as e:
            print(f"Error analyzing most likely values: {e}")
            QMessageBox.critical(self, "Error", f"An error occurred: {e}")

    def plot_decision_tree(self, attributes, outcome, threshold_value):
        try:
            X = self.df_filtered[attributes]
            y = self.df_filtered[outcome]
        
            # Clean data
            X = X.replace([np.inf, -np.inf], np.nan).dropna()
            y = y[X.index]

            if X.empty or y.empty:
                QMessageBox.warning(self, "No Valid Data", "No valid data found after cleaning.")
                return None

            # Get operator
            operator = self.threshold_operator.combo.currentText()

            # Fit the tree
            is_continuous = y.dtype.kind in 'fc'
            tree_model = DecisionTreeRegressor(random_state=42) if is_continuous else DecisionTreeClassifier(random_state=42)
            tree_model.fit(X, y)

            # Make predictions on the filtered dataset to maintain consistency
            if is_continuous:
                y_pred = tree_model.predict(X)
            else:
                y_pred = tree_model.predict_proba(X)[:, 1]

            # Apply the selected comparison
            if operator == '>':
                predicted_outcomes = (y_pred > threshold_value).astype(int)
                original_outcomes = (y > threshold_value).astype(int)
            elif operator == '<':
                predicted_outcomes = (y_pred < threshold_value).astype(int)
                original_outcomes = (y < threshold_value).astype(int)
            elif operator == '=':
                predicted_outcomes = (np.abs(y_pred - threshold_value) < 1e-6).astype(int)
                original_outcomes = (np.abs(y - threshold_value) < 1e-6).astype(int)
            elif operator == '>=':
                predicted_outcomes = (y_pred >= threshold_value).astype(int)
                original_outcomes = (y >= threshold_value).astype(int)
            elif operator == '<=':
                predicted_outcomes = (y_pred <= threshold_value).astype(int)
                original_outcomes = (y <= threshold_value).astype(int)

            # Print prediction details
            print("\nPrediction details:")
            print(f"Total predicted outcomes: {predicted_outcomes.sum()}")
            print("Matching indices with original outcomes:")
            matching_indices = np.where((predicted_outcomes == 1) & (original_outcomes == 1))[0]
            print(f"Number of matching outcomes: {len(matching_indices)}")
            print(f"Accuracy: {(predicted_outcomes == original_outcomes).mean():.2%}")

            # Generate and show most likely values
            most_likely_values = self._generate_most_likely_values(attributes, predicted_outcomes)
            self.show_result_dialog(most_likely_values)

            return predicted_outcomes

        except Exception as e:
            print(f"Error in decision tree analysis: {e}")
            QMessageBox.critical(self, "Error", f"An error occurred: {e}")
            return None

    def _generate_most_likely_values(self, attributes, predictions):
        """Generate most likely values based on prediction patterns"""
        most_likely_values = []
        operator = self.threshold_operator.combo.currentText()
        threshold_value = self.threshold_value.text()
    
        print(f"Finding attribute ranges where outcome is {operator} {threshold_value}")
    
        for attr in attributes:
            # Get values where predictions match our criteria
            matching_values = self.master_df[predictions == 1][attr]
        
            if not matching_values.empty:
                lower = matching_values.quantile(0.25)
                upper = matching_values.quantile(0.75)
            
                most_likely_values.append({
                    "Attribute": attr,
                    "Condition": f"between {lower:.2f} and {upper:.2f}"
                })
            
                print(f"{attr}: typically between {lower:.2f} and {upper:.2f} "
                      f"when criteria is met")
    
        return most_likely_values


    def tree_to_code(self, tree, feature_names):
        tree_ = tree.tree_
        feature_name = [
            feature_names[i] if i != _tree.TREE_UNDEFINED else "undefined!"
            for i in tree_.feature
        ]

        paths = []

        def recurse(node, path):
            if tree_.feature[node] != _tree.TREE_UNDEFINED:
                name = feature_name[node]
                threshold = tree_.threshold[node]
                recurse(tree_.children_left[node], path + [(name, "<=", threshold)])
                recurse(tree_.children_right[node], path + [(name, ">", threshold)])
            else:
                paths.append((path, tree_.value[node]))

        recurse(0, [])
        return paths


 
    def reset_master_df(self):
        """
        Reset the master DataFrame and available columns when the outcome is changed.
        """
        # Get the currently selected outcome
        selected_outcome = self.outcome_dropdown.combo.currentText()
    
        # Get available columns excluding the selected outcome
        available_columns = sorted([col for col in self.master_df.columns if col != selected_outcome])
    
        # Reset the attribute selector with new available columns
        self.attribute_selector.clear_lists()  # Clear both lists
        self.attribute_selector.set_left_items(available_columns)  # Set new available items

    def show_result_dialog(self, most_likely_values):
        try:
            print("\n===== SHOW RESULT DIALOG =====")
            # Prepare the criteria DataFrame
            criteria_records = []
            for result in most_likely_values:
                attribute = result['Attribute']
                condition = result['Condition']
    
                # Parse the 'between' condition
                if 'between' in condition:
                    parts = condition.split('between')
                    lower_bound = float(parts[1].split('and')[0].strip())
                    upper_bound = float(parts[1].split('and')[1].strip())
        
                    # Create two criteria records for lower and upper bounds
                    criteria_records.extend([
                        {
                            'Name': 'Decision Tree Criteria',
                            'Type': 'Highlight',
                            'Column': attribute,
                            'Operator': '>=',
                            'Value': str(lower_bound),
                            'Logical Operator': 'AND',
                            'Color': '#FFFF00'
                        },
                        {
                            'Name': 'Decision Tree Criteria',
                            'Type': 'Highlight',
                            'Column': attribute,
                            'Operator': '<=',
                            'Value': str(upper_bound),
                            'Logical Operator': 'AND',
                            'Color': '#FFFF00'
                        }
                    ])
                else:
                    # Handle other condition types if needed
                    parts = condition.split()
                    if len(parts) == 2:
                        criteria_records.append({
                            'Name': 'Decision Tree Criteria',
                            'Type': 'Highlight',
                            'Column': attribute,
                            'Operator': parts[0],
                            'Value': parts[1],
                            'Logical Operator': 'AND',
                            'Color': '#FFFF00'
                        })
    
            criteria_df = pd.DataFrame(criteria_records)
            print("Generated Criteria:")
            print(criteria_df)

            # Create highlight dialog
            highlight_dialog = HighlightCriteriaDialog(
                db_manager=self.db_manager,
                columns=list(self.master_df.columns), 
                parent=self
            )
            # Explicitly set the criteria name

            # Temporarily block signals to prevent multiple triggers
            highlight_dialog.criteria_name_dropdown.blockSignals(True)

            # Add each criterion to the dialog
            # Add each criterion to the dialog
            for _, row in criteria_df.iterrows():
                # Set the column dropdown to the current column
                column_index = highlight_dialog.column_dropdown.combo.findText(row['Column'])
                if column_index != -1:
                    highlight_dialog.column_dropdown.combo.setCurrentIndex(column_index)  # Fix: Use `.combo`

                # Set operator
                operator_index = highlight_dialog.operator_dropdown.combo.findText(row['Operator'])  # Fix: Use `.combo`
                if operator_index != -1:
                    highlight_dialog.operator_dropdown.combo.setCurrentIndex(operator_index)

                # Set value
                highlight_dialog.value_entry.setText(str(row['Value']))

                # Add the criterion
                highlight_dialog.add_criterion()

            # Unblock signals
            highlight_dialog.criteria_name_dropdown.blockSignals(False)

            # Execute the dialog
            if highlight_dialog.exec_() == QDialog.Accepted:
                # Find the original ZoneViewerDialog
                parent = self.parent()
                while parent and not hasattr(parent, 'populate_criteria_dropdowns'):
                    parent = parent.parent()
    
                if parent:
                    parent.populate_criteria_dropdowns()
    
                # Emit the generated criteria
                self.criteriaGenerated.emit(criteria_df)
                return 'Decision Tree Criteria'

        except Exception as e:
            QMessageBox.critical(self, "Error", f"An error occurred: {str(e)}")
            print(f"Error in show_result_dialog: {e}")
            import traceback
            traceback.print_exc()

        return None
# Test code
if __name__ == "__main__":
    import sys
    from PySide6.QtWidgets import QApplication

    # Example DataFrame
    data = {
        'Pressure': [300, 400, 500, 600, 300, 200, 250],
        'Fluid_Pressure': [50, 30, 80, 20, 70, 10, 60],
        'Attribute1': [1, 2, 1, 3, 2, 1, 2],
        'Attribute2': [5, 3, 6, 2, 5, 4, 6],
        'Attribute3': [1.5, 2.3, 3.1, 4.2, 2.5, 1.9, 2.8],
    }
    master_df = pd.DataFrame(data)

    # Mock db_manager for testing
    class MockDBManager:
        def load_criteria_names(self):
            return []
        def save_criteria(self, *args, **kwargs):
            return True, "Success"
        def load_criteria_by_name(self, name):
            return "#FFFF00", []
        
    app = QApplication(sys.argv)
    dialog = DecisionTreeDialog(master_df, db_manager=MockDBManager())
    dialog.exec_()