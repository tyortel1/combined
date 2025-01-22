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

class DecisionTreeDialog(QDialog):



    criteriaGenerated = Signal(pd.DataFrame)
    def __init__(self, master_df, parent=None):
        super().__init__(parent)
        # Create a deep copy of the DataFrame at initialization
        self.master_df = master_df.copy()
        self.initUI()

    def initUI(self):
        self.setWindowTitle("Decision Tree Selection")
        self.setGeometry(100, 100, 800, 600)

        available_columns = sorted([col for col in self.master_df.columns])
        self.df_filtered = pd.DataFrame()
        main_layout = QVBoxLayout(self)

        # Changed to match the actual method name
        self.setup_selector_layout(main_layout, "Select Attributes", 
                                   available_items=available_columns,
                                   move_all_right_callback=self.move_all_attributes_right,
                                   move_right_callback=self.move_selected_attributes_right,
                                   move_left_callback=self.move_selected_attributes_left,
                                   move_all_left_callback=self.move_all_attributes_left,
                                   available_list_attr='attribute_available_listbox', 
                                   selected_list_attr='attribute_selected_listbox')

        # Dropdown for outcome selection
        outcome_layout = QHBoxLayout()
        outcome_label = QLabel("Select Outcome:")
        self.outcome_dropdown = QComboBox()
        self.outcome_dropdown.addItems(available_columns)
        outcome_layout.addWidget(outcome_label)
        outcome_layout.addWidget(self.outcome_dropdown)
        self.outcome_dropdown.currentIndexChanged.connect(self.reset_master_df)
        main_layout.addLayout(outcome_layout)

        # Editable threshold box
        threshold_layout = QHBoxLayout()
        threshold_label = QLabel("Threshold:")
        self.threshold_edit = QLineEdit()
        self.threshold_edit.setText("0.5")  # Default value
        threshold_layout.addWidget(threshold_label)
        threshold_layout.addWidget(self.threshold_edit)
        main_layout.addLayout(threshold_layout)

        # OK/Cancel buttons
        button_layout = QHBoxLayout()
        self.ok_button = QPushButton("OK")
        self.cancel_button = QPushButton("Cancel")
        self.ok_button.clicked.connect(self.build_decision_tree)
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.ok_button)
        button_layout.addWidget(self.cancel_button)
        main_layout.addLayout(button_layout)


    def setup_selector_layout(self, main_layout, label_text, available_items, move_all_right_callback, 
                        move_right_callback, move_left_callback, move_all_left_callback, 
                        available_list_attr, selected_list_attr):
        section_label = QLabel(label_text)
        main_layout.addWidget(section_label)

        list_layout = QHBoxLayout()

        available_listbox = QListWidget()
        available_listbox.setSelectionMode(QListWidget.ExtendedSelection)
        setattr(self, available_list_attr, available_listbox)
        for item in available_items:
            QListWidgetItem(item, available_listbox)
        list_layout.addWidget(available_listbox)

        arrow_layout = QVBoxLayout()

        self.move_all_right_button = QPushButton()
        self.move_all_right_button.setIcon(QIcon("icons/arrow_double_right.png"))
        self.move_all_right_button.clicked.connect(move_all_right_callback)
        arrow_layout.addWidget(self.move_all_right_button)

        self.move_right_button = QPushButton()
        self.move_right_button.setIcon(QIcon("icons/arrow_right.ico"))
        self.move_right_button.clicked.connect(move_right_callback)
        arrow_layout.addWidget(self.move_right_button)

        self.move_left_button = QPushButton()
        self.move_left_button.setIcon(QIcon("icons/arrow_left.ico"))
        self.move_left_button.clicked.connect(move_left_callback)
        arrow_layout.addWidget(self.move_left_button)

        self.move_all_left_button = QPushButton()
        self.move_all_left_button.setIcon(QIcon("icons/arrow_double_left.png"))
        self.move_all_left_button.clicked.connect(move_all_left_callback)
        arrow_layout.addWidget(self.move_all_left_button)

        arrow_layout.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding))
        list_layout.addLayout(arrow_layout)

        selected_listbox = QListWidget()
        selected_listbox.setSelectionMode(QListWidget.ExtendedSelection)
        setattr(self, selected_list_attr, selected_listbox)
    
        list_layout.addWidget(selected_listbox)
        main_layout.addLayout(list_layout)

    def move_all_attributes_right(self):
        self.move_all_items(self.attribute_available_listbox, self.attribute_selected_listbox)

    def move_selected_attributes_right(self):
        self.move_selected_items(self.attribute_available_listbox, self.attribute_selected_listbox)

    def move_selected_attributes_left(self):
        self.move_selected_items(self.attribute_selected_listbox, self.attribute_available_listbox)

    def move_all_attributes_left(self):
        self.move_all_items(self.attribute_selected_listbox, self.attribute_available_listbox)

    def move_selected_items(self, source_list, target_list):
        for item in source_list.selectedItems():
            target_list.addItem(item.text())
            source_list.takeItem(source_list.row(item))

    def move_all_items(self, source_list, target_list):
        while source_list.count() > 0:
            item = source_list.takeItem(0)
            target_list.addItem(item.text())



    def build_decision_tree(self):
        selected_attributes = [self.attribute_selected_listbox.item(i).text() 
                             for i in range(self.attribute_selected_listbox.count())]
        selected_outcome = self.outcome_dropdown.currentText()

        # Calculate total number of existing bad frac stages
        total_bad_fracs = self.master_df[selected_outcome].sum()
        print(f"Total existing bad frac stages: {total_bad_fracs}")

        if len(selected_attributes) > 0:
            relevant_columns = selected_attributes + [selected_outcome]
            self.df_filtered = self.master_df[relevant_columns].copy()

            self.df_filtered = self.df_filtered.loc[
                (self.df_filtered[selected_outcome] != 0) & 
                (self.df_filtered[selected_outcome].notna())
            ]

            # Try progressively lower thresholds
            thresholds = [0.3, 0.2, 0.1, 0.05]
            for threshold in thresholds:
                print(f"\nTrying threshold: {threshold}")
                predicted_bad_fracs = self.plot_decision_tree(selected_attributes, selected_outcome, threshold)
            
                # If we capture a good portion of existing bad fracs, stop
                if predicted_bad_fracs is not None:
                    capture_rate = predicted_bad_fracs.sum() / total_bad_fracs
                    print(f"Capture rate: {capture_rate:.2%}")
                    if capture_rate > 0.7:  # Adjust this threshold as needed
                        break

    def analyze_most_likely_values(self, attributes, outcome):
        try:
            print("Starting analysis...")
            analysis_results = []
            tolerance = 1e-5  # Small tolerance for floating-point comparison
    
            # Make a copy of df_filtered to avoid SettingWithCopyWarning
            working_df = self.df_filtered.copy()
    
            for attribute in attributes:
                print(f"Processing attribute: {attribute}")
        
                # Create a copy of the column and process it
                working_df.loc[:, attribute] = working_df[attribute].fillna(0)
                working_df.loc[:, attribute] = pd.to_numeric(working_df[attribute], errors='coerce').fillna(0)
        
                if pd.api.types.is_numeric_dtype(working_df[attribute]):
                    median_value = working_df[attribute].median()
                    q1 = working_df[attribute].quantile(0.25)
                    q3 = working_df[attribute].quantile(0.75)
            
                    # Calculate count of values above and below median
                    above_median_count = (working_df[attribute] > median_value + tolerance).sum()
                    below_median_count = (working_df[attribute] < median_value - tolerance).sum()
            
                    # Determine the condition based on distribution
                    if above_median_count > below_median_count:
                        # If mostly above median, provide a range description
                        condition = f"between {median_value:.2f} and {q3:.2f}"
                    elif below_median_count > above_median_count:
                        # If mostly below median, provide a range description
                        condition = f"between {q1:.2f} and {median_value:.2f}"
                    else:
                        # If evenly distributed, provide a broader range
                        condition = f"between {q1:.2f} and {q3:.2f}"
            
                    # Add to analysis results
                    analysis_results.append({
                        "Attribute": attribute, 
                        "Condition": condition
                    })
            
                    print(f"Analysis for {attribute}: {condition}")
    
            print("Final analysis results:", analysis_results)

            # Directly call show_result_dialog with the analysis results
            self.show_result_dialog(analysis_results)

        except Exception as e:
            print(f"Error analyzing most likely values: {e}")
            QMessageBox.critical(self, "Error", f"An error occurred: {e}")

    def plot_decision_tree(self, attributes, outcome, threshold):
        try:
            X = self.df_filtered[attributes]
            y = self.df_filtered[outcome]

            X = X.replace([np.inf, -np.inf], np.nan).dropna()
            y = y[X.index]

            if X.empty or y.empty:
                QMessageBox.warning(self, "No Valid Data", "No valid data found after cleaning.")
                return None

            is_continuous = y.dtype.kind in 'fc'
            tree_model = DecisionTreeRegressor(random_state=42) if is_continuous else DecisionTreeClassifier(random_state=42)
            tree_model.fit(X, y)

            # Predict probabilities
            if is_continuous:
                y_pred_proba = tree_model.predict(self.master_df[attributes])
            else:
                y_pred_proba = tree_model.predict_proba(self.master_df[attributes])[:, 1]

            # Create a prediction series
            predicted_bad_fracs = (y_pred_proba >= threshold).astype(int)
        
            print("Prediction details:")
            print(f"Total predicted bad stages: {predicted_bad_fracs.sum()}")
            print("Matching indices with original bad stages:")
            matching_indices = np.where((predicted_bad_fracs == 1) & (self.master_df[outcome] == 1))[0]
            print(f"Number of matching bad stages: {len(matching_indices)}")

            # Open the highlight dialog with these predictions
            most_likely_values = self._generate_most_likely_values(attributes, predicted_bad_fracs)
            self.show_result_dialog(most_likely_values)

            return predicted_bad_fracs

        except Exception as e:
            print(f"Error in decision tree analysis: {e}")
            QMessageBox.critical(self, "Error", f"An error occurred: {e}")
            return None

    def _generate_most_likely_values(self, attributes, predictions):
        """Generate most likely values based on prediction patterns"""
        most_likely_values = []
        for attr in attributes:
            # Find significant differences in the attribute for predicted bad stages
            bad_stage_values = self.master_df[predictions == 1][attr]
        
            # Calculate range for bad stages
            if not bad_stage_values.empty:
                lower = bad_stage_values.quantile(0.25)
                upper = bad_stage_values.quantile(0.75)
            
                most_likely_values.append({
                    "Attribute": attr,
                    "Condition": f"between {lower:.2f} and {upper:.2f}"
                })
    
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
        # Reset the available attributes list
        self.attribute_available_listbox.clear()
        self.attribute_selected_listbox.clear()

        # Repopulate the available attributes, excluding the selected outcome
        selected_outcome = self.outcome_dropdown.currentText()
        available_columns = sorted([col for col in self.master_df.columns if col != selected_outcome])
    
        for item in available_columns:
            QListWidgetItem(item, self.attribute_available_listbox)

    def show_result_dialog(self, most_likely_values):
        try:
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
                            'Color': '#FFFF00'  # Default yellow
                        },
                        {
                            'Name': 'Decision Tree Criteria',
                            'Type': 'Highlight',
                            'Column': attribute,
                            'Operator': '<=',
                            'Value': str(upper_bound),
                            'Logical Operator': 'AND',
                            'Color': '#FFFF00'  # Default yellow
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
                            'Color': '#FFFF00'  # Default yellow
                        })
        
            # Create the criteria DataFrame
            criteria_df = pd.DataFrame(criteria_records)
        
            # Open the HighlightCriteriaDialog directly
            highlight_dialog = HighlightCriteriaDialog(
                columns=list(self.master_df.columns), 
                existing_criteria_df=criteria_df, 
                parent=self
            )
        
            # Pre-fill the criteria name
            highlight_dialog.criteria_name_dropdown.setCurrentText('Decision Tree Criteria')
        
            # Execute the dialog
            if highlight_dialog.exec_() == QDialog.Accepted:
                return highlight_dialog.criteria_name
    
        except Exception as e:
            QMessageBox.critical(self, "Error", f"An error occurred: {str(e)}")
            print(f"Error in show_result_dialog: {e}")
    
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

    app = QApplication(sys.argv)
    dialog = DecisionTreeDialog(master_df)
    dialog.exec_()