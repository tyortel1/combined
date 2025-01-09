from PySide6.QtWidgets import (QDialog, QListWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
                               QTableWidget, QTableWidgetItem, QMessageBox, QSpacerItem, QSizePolicy, QListWidgetItem, QComboBox, QCheckBox)
from PySide6.QtGui import QIcon
from PySide6.QtCore import Qt, QSize
import pandas as pd
import numpy as np

class CalculateCorrelations(QDialog):
    def __init__(self, master_df, parent=None):
        super().__init__(parent)
        self.master_df = master_df
        self.initUI()

    def initUI(self):
        self.setWindowTitle("Correlation Analysis")
        self.setGeometry(100, 100, 800, 800)

        available_columns = sorted([col for col in self.master_df.columns])
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

        # Checkbox for excluding zeros
        self.exclude_zeros_checkbox = QCheckBox("Exclude zeros in calculation")
        main_layout.addWidget(self.exclude_zeros_checkbox)

        # Dropdown for threshold selection
        self.threshold_dropdown = QComboBox(self)
        self.threshold_dropdown.addItems(["0", "0.1", "0.2", "0.3", "0.4", "0.5", "0.6", "0.7", "0.8", "0.9"])
        self.threshold_dropdown.setFixedSize(QSize(150, 25))  # 1.5 inches wide (approx 150 pixels)

        main_layout.addWidget(QLabel("Select Correlation Threshold:"))
        main_layout.addWidget(self.threshold_dropdown)

        # Dropdown for attribute filtering
        self.filter_dropdown = QComboBox(self)
        self.filter_dropdown.setFixedSize(QSize(150, 25))  # Set the size of the filter dropdown
        self.filter_dropdown.setVisible(False)  # Initially hidden
        self.filter_dropdown.addItem("Show All")  # Default option to show all rows
        main_layout.addWidget(QLabel("Filter Results by Attribute:"))
        main_layout.addWidget(self.filter_dropdown)
        self.filter_dropdown.currentIndexChanged.connect(self.filter_results_by_attribute)

        # Table widget to display correlation results
        self.results_table = QTableWidget(self)
        self.results_table.setColumnCount(5)
        self.results_table.setHorizontalHeaderLabels(
            ["Attribute 1", "Attribute 2", "Correlation Type", "Correlation Coefficient", "Standard Error"])
        self.results_table.setSortingEnabled(True)  # Enable sorting by columns
        main_layout.addWidget(self.results_table)

        # OK/Cancel buttons
        button_layout = QHBoxLayout()
        self.ok_button = QPushButton("Calculate")
        self.cancel_button = QPushButton("Cancel")
        self.ok_button.setFixedSize(QSize(150, 25))
        self.cancel_button.setFixedSize(QSize(150, 25))
        button_layout.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Expanding, QSizePolicy.Minimum))
        button_layout.addWidget(self.ok_button)
        button_layout.addWidget(self.cancel_button)

        self.ok_button.clicked.connect(self.calculate_and_display_correlation)
        self.cancel_button.clicked.connect(self.reject)

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

    def calculate_and_display_correlation(self):
        selected_attributes = [item.text() for item in self.attribute_selected_listbox.findItems("", Qt.MatchContains)]
        if len(selected_attributes) < 2:
            QMessageBox.warning(self, "Selection Error", "Please select at least two attributes.")
            return

        df_filtered = self.master_df[selected_attributes]
        results_df = self.calculate_correlation_analysis(df_filtered)

        # Populate the filter dropdown with selected attributes
        self.populate_filter_dropdown(selected_attributes)

        # Display results in the table
        self.display_results_in_table(results_df)

    def calculate_correlation_analysis(self, df):
        self.reset_state()
        # Check if the user wants to exclude zeros
        if self.exclude_zeros_checkbox.isChecked():
            df = df.replace(0, np.nan)  # Replace zeros with NaN to exclude from correlation

        # Calculate the correlation matrix
        corr_matrix = df.corr()

        # Prepare a DataFrame to store results
        results = []

        # Calculate the correlation and standard error
        for i in range(len(corr_matrix.columns)):
            for j in range(i+1, len(corr_matrix.columns)):
                attr1 = corr_matrix.columns[i]
                attr2 = corr_matrix.columns[j]
                r = corr_matrix.iloc[i, j]
                n = len(df.dropna(subset=[attr1, attr2]))  # Drop NaN rows for correct sample size
                se = np.sqrt((1 - r**2) / (n - 2)) if n > 2 else np.nan  # Avoid division by zero

                # Determine correlation type
                if r > 0:
                    corr_type = "Positive"
                elif r < 0:
                    corr_type = "Negative"
                else:
                    corr_type = "Flat"

                results.append({
                    "Attribute 1": attr1,
                    "Attribute 2": attr2,
                    "Correlation Type": corr_type,
                    "Correlation Coefficient": r,
                    "Standard Error": se
                })

        # Convert the results into a DataFrame and return
        results_df = pd.DataFrame(results)
        return results_df

    def display_results_in_table(self, results_df):
        # Clear the table first
        self.results_table.setRowCount(0)

        # Get the threshold value selected by the user
        threshold = float(self.threshold_dropdown.currentText())

        # Populate the table with the results, filtering by the threshold (absolute value)
        for row_idx, row in results_df.iterrows():
            if abs(row["Correlation Coefficient"]) >= threshold:
                self.results_table.insertRow(row_idx)
                self.results_table.setItem(row_idx, 0, QTableWidgetItem(str(row["Attribute 1"])))
                self.results_table.setItem(row_idx, 1, QTableWidgetItem(str(row["Attribute 2"])))
                self.results_table.setItem(row_idx, 2, QTableWidgetItem(row["Correlation Type"]))
                self.results_table.setItem(row_idx, 3, QTableWidgetItem(f"{row['Correlation Coefficient']:.4f}"))
                self.results_table.setItem(row_idx, 4, QTableWidgetItem(f"{row['Standard Error']:.4f}"))

    def populate_filter_dropdown(self, attributes):
        # Show the filter dropdown and populate it with selected attributes
        self.filter_dropdown.setVisible(True)
        self.filter_dropdown.clear()  # Clear existing items
        self.filter_dropdown.addItem("Show All")  # Add the "Show All" option
        self.filter_dropdown.addItems(attributes)  # Add selected attributes

    def filter_results_by_attribute(self):
        selected_attribute = self.filter_dropdown.currentText()

        # First, reset all rows to be visible
        for row in range(self.results_table.rowCount()):
            self.results_table.setRowHidden(row, False)

        # If "Show All" is selected, leave all rows visible
        if selected_attribute == "Show All":
            return

        # Apply the filter: hide rows that don't contain the selected attribute
        for row in range(self.results_table.rowCount()):
            attr1 = self.results_table.item(row, 0).text()
            attr2 = self.results_table.item(row, 1).text()

            # Show only rows where one of the attributes matches the selected attribute
            if selected_attribute not in [attr1, attr2]:
                self.results_table.setRowHidden(row, True)

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
        # Save the scroll position
        scroll_pos = source_list.verticalScrollBar().value()

        for item in source_list.selectedItems():
            target_list.addItem(item.text())
            source_list.takeItem(source_list.row(item))

        # Restore the scroll position
        source_list.verticalScrollBar().setValue(scroll_pos)

    def move_all_items(self, source_list, target_list):
        while source_list.count() > 0:
            item = source_list.takeItem(0)
            target_list.addItem(item.text())

    def reset_state(self):
        self.results_table.clearContents()  # Clear previous results
        self.results_table.setRowCount(0)   # Reset row count
        self.attribute_selected_listbox.clearSelection()  # Reset list selections


# Example usage
if __name__ == "__main__":
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
    dialog = CalculateCorrelations(master_df)
    dialog.exec_()
