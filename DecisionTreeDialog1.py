import pandas as pd
from PySide6.QtWidgets import QDialog, QListWidget, QVBoxLayout,QTextEdit, QFormLayout, QPushButton, QSpacerItem, QSizePolicy, QLabel, QMessageBox, QHBoxLayout, QListWidgetItem, QComboBox, QLineEdit
from PySide6.QtGui import QIcon
from PySide6.QtCore import Qt
from sklearn.tree import DecisionTreeClassifier
import matplotlib.pyplot as plt
from sklearn import tree
from sklearn.tree import DecisionTreeClassifier, DecisionTreeRegressor
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from sklearn.tree import _tree
import numpy as np
from collections import defaultdict, Counter
from sklearn.feature_selection import SelectKBest, f_classif
from sklearn.model_selection import train_test_split
from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTextEdit, QComboBox, QColorDialog
from PySide6.QtGui import QColor, QPalette
from PySide6.QtCore import Qt

class DecisionTreeDialog(QDialog):
    def __init__(self, master_df, parent=None):
        super().__init__(parent)
        self.master_df = master_df
        self.initUI()

    def initUI(self):
        self.setWindowTitle("Decision Tree Selection")
        self.setGeometry(100, 100, 800, 600)

        available_columns = sorted([col for col in self.master_df.columns])
        self.df_filtered = pd.DataFrame()
        main_layout = QVBoxLayout(self)

        # Layout for attribute selection
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

    def setup_selector_layout(self, main_layout, label_text, available_items, move_all_right_callback, move_right_callback, move_left_callback, move_all_left_callback, available_list_attr, selected_list_attr):
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

    # Methods for moving attributes
    def move_all_attributes_right(self):
        self.move_all_items(self.attribute_available_listbox, self.attribute_selected_listbox)

    def move_selected_attributes_right(self):
        self.move_selected_items(self.attribute_available_listbox, self.attribute_selected_listbox)

    def move_selected_attributes_left(self):
        self.move_selected_items(self.attribute_selected_listbox, self.attribute_available_listbox)

    def move_all_attributes_left(self):
        self.move_all_items(self.attribute_selected_listbox, self.attribute_available_listbox)

    # Helper methods for moving items between list boxes
    def move_selected_items(self, source_list, target_list):
        for item in source_list.selectedItems():
            target_list.addItem(item.text())
            source_list.takeItem(source_list.row(item))

    def move_all_items(self, source_list, target_list):
        while source_list.count() > 0:
            item = source_list.takeItem(0)
            target_list.addItem(item.text())

    def reset_master_df(self):
        # Reset the master DataFrame to its original state
        self.df_filtered = self.master_df.copy()


        # You can also reset any other UI elements or internal variables as needed

        print("Master DataFrame and UI have been reset.")

    def build_decision_tree(self):
        selected_attributes = [self.attribute_selected_listbox.item(i).text() for i in range(self.attribute_selected_listbox.count())]
        selected_outcome = self.outcome_dropdown.currentText()

        if len(selected_attributes) > 0:
            # Create a copy of the master DataFrame including only the selected columns
            relevant_columns = selected_attributes + [selected_outcome]
            self.df_filtered = self.master_df[relevant_columns].copy()

            # Filter the DataFrame to include only rows where the outcome is not zero or NaN
            self.df_filtered = self.df_filtered.loc[
                (self.df_filtered[selected_outcome] != 0) & 
                (self.df_filtered[selected_outcome].notna())
            ]

            print(self.df_filtered)  # Debugging output
        
            if self.df_filtered.empty:
                QMessageBox.warning(self, "No Data", "Filtered data is empty. Please check your selections.")
                return

            if len(selected_attributes) > 0:
                # Check if the filtered outcome column contains only the value 1
                if self.df_filtered[selected_outcome].nunique() == 1 and self.df_filtered[selected_outcome].iloc[0] == 1:
                    # Outcome is always 1, use distribution analysis
                    print("Outcome is always 1. Running distribution analysis...")
                    self.analyze_most_likely_values(selected_attributes, selected_outcome)
                else:
                    # Outcome has varying values, use decision tree analysis
                    threshold = float(self.threshold_edit.text())
                    print(f"Outcome varies. Running decision tree analysis with threshold {threshold}...")
                    self.plot_decision_tree(selected_attributes, selected_outcome, threshold)
            else:
                QMessageBox.warning(self, "Invalid Selection", "Please select at least one attribute.")


    def analyze_most_likely_values(self, attributes, outcome):
        try:
            print("Starting analysis...")
            analysis_results = []
            tolerance = 1e-5  # Small tolerance for floating-point comparison

            for attribute in attributes:
                print(f"Processing attribute: {attribute}")
                self.df_filtered[attribute].fillna(0, inplace=True)
                self.df_filtered[attribute] = pd.to_numeric(self.df_filtered[attribute], errors='coerce').fillna(0)

                if pd.api.types.is_numeric_dtype(self.df_filtered[attribute]):
                    median_value = self.df_filtered[attribute].median()

                    above_median_count = (self.df_filtered[attribute] > median_value + tolerance).sum()
                    below_median_count = (self.df_filtered[attribute] < median_value - tolerance).sum()
                    equal_median_count = (
                        (self.df_filtered[attribute] >= median_value - tolerance) &
                        (self.df_filtered[attribute] <= median_value + tolerance)
                    ).sum()

                    if above_median_count > below_median_count and above_median_count > equal_median_count:
                        most_likely = f"above {median_value:.2f}"
                    elif below_median_count > above_median_count and below_median_count > equal_median_count:
                        most_likely = f"below {median_value:.2f}"
                    else:
                        most_likely = f"equal to {median_value:.2f}"

                    analysis_results.append({"Attribute": attribute, "Condition": most_likely})
                else:
                    analysis_results.append({"Attribute": attribute, "Condition": "non-numeric or missing"})

            print("Final analysis results:", analysis_results)
        
            # Pass the analysis results as a list of dictionaries to the dialog
            dialog = ResultDisplayDialog(analysis_results, self)
            dialog.exec_()

        except Exception as e:
            print(f"Error analyzing most likely values: {e}")
            QMessageBox.critical(self, "Error", f"An error occurred: {e}")




    def plot_decision_tree(self, attributes, outcome, threshold):
        try:
            # Filter the DataFrame to include only rows where the outcome is not zero, not NaN, and meets/exceeds the threshold
            df_filtered = self.master_df.loc[
                (self.master_df[outcome] != 0) & 
                (self.master_df[outcome].notna())
            ]
            print(df_filtered)
            X = df_filtered[attributes]
            y = df_filtered[outcome]

            # Handle NaN, infinite, and large values in X
            X = X.replace([np.inf, -np.inf], np.nan).dropna()  # Replace infinities with NaN and then drop them
            y = y[X.index]  # Ensure y matches the cleaned X

            if X.empty or y.empty:
                QMessageBox.warning(self, "No Valid Data", "No valid data found after cleaning.")
                return

            # Fit the model
            is_continuous = y.dtype.kind in 'fc'
            tree_model = DecisionTreeRegressor(random_state=42) if is_continuous else DecisionTreeClassifier(random_state=42)
            tree_model.fit(X, y)

            # Get paths from the tree
            paths = self.tree_to_code(tree_model, attributes)

            # Filter paths based on the threshold (This may now be redundant since we've pre-filtered)
            above_threshold_paths = []
            for path, value in paths:
                predicted_value = value[0][0] if is_continuous else value[0][1] / np.sum(value[0]) if np.sum(value[0]) > 0 else 0
        
                if predicted_value >= threshold:
                    above_threshold_paths.append(path)

            if not above_threshold_paths:
                QMessageBox.information(self, "No Paths Found", f"No paths found leading to {outcome} above {threshold}")
                return

            # Track the most common conditions across all paths
            condition_counter = defaultdict(Counter)
            for path in above_threshold_paths:
                for attribute, comparison, threshold_value in path:
                    condition_counter[attribute][(comparison, threshold_value)] += 1

            # Determine the most likely value for each attribute
            most_likely_values = []
            for attribute, conditions in condition_counter.items():
                most_common_condition = conditions.most_common(1)[0]
                comparison, threshold_value = most_common_condition[0]
                most_likely_values.append({
                    "Attribute": attribute,
                    "Condition": f"{comparison} {threshold_value:.2f}"
                })

            # Display the results in the dialog
            self.show_result_dialog(most_likely_values)

        except Exception as e:
            print(f"Error finding paths above threshold: {e}")
            QMessageBox.critical(self, "Error", f"An error occurred: {e}")
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
    # Update the show_result_dialog method in DecisionTreeDialog
    def show_result_dialog(self, most_likely_values):
        dialog = ResultDisplayDialog(most_likely_values, self)
        dialog.exec_()





class ResultDisplayDialog(QDialog):
    def __init__(self, most_likely_values, parent=None):
        super(ResultDisplayDialog, self).__init__(parent)
        self.setWindowTitle("Most Likely Values")
        self.setGeometry(100, 100, 400, 600)

        # Main layout
        layout = QVBoxLayout(self)

        # Criteria name dropdown (read-only, pre-filled)
        self.criteria_name_dropdown = QComboBox(self)
        self.criteria_name_dropdown.setEditable(True)
        self.criteria_name_dropdown.addItem("Most Likely Values")
        self.criteria_name_dropdown.setCurrentText("Most Likely Values")

        layout.addWidget(QLabel("Criteria Name:"))
        layout.addWidget(self.criteria_name_dropdown)

        # Current Criteria text area (pre-filled, read-only)
        self.criteria_text_edit = QTextEdit(self)
        self.criteria_text_edit.setReadOnly(True)
        layout.addWidget(QLabel("Current Criteria:"))
        layout.addWidget(self.criteria_text_edit)

        # Populate the criteria text area with the most likely values
        criteria_text = ""
        for i, entry in enumerate(most_likely_values):
            criteria_text += f"{entry['Attribute']} {entry['Condition']}"
            if i < len(most_likely_values) - 1:
                criteria_text += " AND\n"
        self.criteria_text_edit.setPlainText(criteria_text)

        # Highlight color button and preview (read-only, pre-filled)
        color_layout = QHBoxLayout()
        self.color_button = QPushButton("Choose Highlight Color")
        self.color_button.clicked.connect(self.choose_color)

        self.color_preview = QLabel(self)
        self.color_preview.setFixedSize(20, 20)
        self.color_preview.setAutoFillBackground(True)
        self.highlight_color = QColor(Qt.yellow)
        self.update_color_preview()

        color_layout.addWidget(self.color_button)
        color_layout.addWidget(self.color_preview)

        layout.addLayout(color_layout)

        # Save and Cancel buttons
        button_layout = QHBoxLayout()
        save_button = QPushButton("Save Criteria")
        cancel_button = QPushButton("Cancel")

        button_layout.addWidget(save_button)
        button_layout.addWidget(cancel_button)

        save_button.clicked.connect(self.accept)
        cancel_button.clicked.connect(self.reject)

        layout.addLayout(button_layout)

    def choose_color(self):
        color = QColorDialog.getColor(self.highlight_color, self, "Select Highlight Color")
        if color.isValid():
            self.highlight_color = color
            self.update_color_preview()

    def update_color_preview(self):
        palette = self.color_preview.palette()
        palette.setColor(QPalette.Window, self.highlight_color)
        self.color_preview.setPalette(palette)



# Example usage
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
