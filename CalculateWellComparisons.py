from PySide6.QtWidgets import (
    QDialog, QLabel, QVBoxLayout, QPushButton, QListWidget, QListWidgetItem,
    QAbstractItemView, QGroupBox, QLineEdit, QMessageBox, QTableWidget, 
    QTableWidgetItem, QHeaderView, QWidget, QCheckBox, QHBoxLayout,QRadioButton, QSlider, QComboBox, QFormLayout, QFileDialog, QSpacerItem, QSizePolicy
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
import pandas as pd
import numpy as np
from typing import List, Dict, Tuple, Optional, Any

from PySide6.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QHBoxLayout, QListWidget, 
    QPushButton, QLineEdit, QAbstractItemView
)
from PySide6.QtCore import Qt
from DeclineCurveAnalysis import DeclineCurveAnalysis
from PUDProperties import PUDPropertiesDialog
from StyledDropdown import StyledDropdown
from StyledButton import StyledButton
from StyledTwoListSelector import TwoListSelector 



class ScenarioNameDialog(QDialog):
    """Dialog to select an existing scenario or create a new one."""
    
    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select Scenario")
        self.setMinimumWidth(300)
        self.db_manager = db_manager
        self.scenario_id = None

        layout = QVBoxLayout(self)

        # Step 1: Fetch existing scenario names
        self.scenario_names = self.db_manager.get_scenario_names()

        # Step 2: Create Dropdown for Existing Scenarios
        self.scenario_dropdown = QComboBox(self)
        layout.addWidget(QLabel("Select a Scenario:"))

        if self.scenario_names:
            self.scenario_dropdown.addItems(self.scenario_names)
            layout.addWidget(self.scenario_dropdown)
        else:
            layout.addWidget(QLabel("No existing scenarios found. Please create one."))

        # Step 3: Buttons
        button_layout = QHBoxLayout()

        if self.scenario_names:
            self.ok_button = QPushButton("OK")
            self.ok_button.clicked.connect(self.accept)
            button_layout.addWidget(self.ok_button)
        else:
            self.create_button = QPushButton("Create Scenario")
            self.create_button.clicked.connect(self.create_new_scenario)
            button_layout.addWidget(self.create_button)

        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_button)

        layout.addLayout(button_layout)

    def get_selected_scenario(self):
        """Return the selected scenario name."""
        if self.scenario_names:
            return self.scenario_dropdown.currentText().strip()
        return None

    def create_new_scenario(self):
        # Assuming self.db_manager exists in the parent class
        dialog = PUDPropertiesDialog(self.db_manager, parent=self)
        dialog.exec_()





class WeightsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Adjust Weights & Sensitivity")
        self.setMinimumWidth(400)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # Sensitivity Slider
        self.sensitivity_label = QLabel("Outlier Sensitivity (IQR Multiplier)")
        self.sensitivity_slider = QSlider(Qt.Horizontal)
        self.sensitivity_slider.setMinimum(1)
        self.sensitivity_slider.setMaximum(5)
        self.sensitivity_slider.setValue(2)
        layout.addWidget(self.sensitivity_label)
        layout.addWidget(self.sensitivity_slider)

        # Checkboxes
        self.normalize_checkbox = QCheckBox("Normalize Values")
        self.normalize_checkbox.setChecked(False)
        layout.addWidget(self.normalize_checkbox)

        self.zero_outliers_checkbox = QCheckBox("Set Outliers to Zero (instead of NaN)")
        self.zero_outliers_checkbox.setChecked(False)
        layout.addWidget(self.zero_outliers_checkbox)

        # Attribute Weights
        self.weights_group = QGroupBox("Attribute Weights")
        self.weights_layout = QFormLayout()
        self.weights_group.setLayout(self.weights_layout)
        layout.addWidget(self.weights_group)

        # Save Button
        self.save_button = QPushButton("Apply")
        self.save_button.clicked.connect(self.accept)
        layout.addWidget(self.save_button)

    def add_weight_sliders(self, attributes: List[str], weights: dict = None):
        print(f"Attributes: {attributes}")
        print(f"Weights: {weights}")
    
        # Clear existing sliders
        for i in reversed(range(self.weights_layout.count())):
            self.weights_layout.itemAt(i).widget().setParent(None)
    
        self.weight_sliders = {}
    
        for attr in attributes:
            print(f"Processing attribute: {attr}")
        
            slider = QSlider(Qt.Horizontal)
            slider.setMinimum(1)
            slider.setMaximum(100)
        
            # Set weight based on provided weights or default to 50
            if weights and attr in weights:
                weight = weights[attr]
                print(f"Weight for {attr}: {weight}")
            
                # Convert weight to slider value
                if weight <= 1:
                    slider_value = int(weight * 100)
                else:
                    slider_value = int(weight)
            
                # Ensure slider value is between 1 and 100
                slider_value = max(1, min(100, slider_value))
            
                print(f"Setting slider for {attr} to: {slider_value}")
            
                slider.setValue(slider_value)
            else:
                print(f"No weight found for {attr}, defaulting to 50")
                slider.setValue(50)  # Default weight
        
            self.weights_layout.addRow(f"{attr}:", slider)
            self.weight_sliders[attr] = slider


class WellComparisonDialog(QDialog):
    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.setup_ui()
        self.weight_sliders = {}
 
        self.dca = DeclineCurveAnalysis()
        self.normalize_values = False
        self.zero_outliers = False
        self.iqr_multiplier = 1.5

    def setup_ui(self):
        self.setWindowTitle("Well Comparison")
        self.setMinimumWidth(1400)
        self.setMinimumHeight(800)
        self.setWindowState(Qt.WindowMaximized)
        self.selected_attributes = []
        main_layout = QHBoxLayout(self)

        left_layout = QVBoxLayout()
    
        # Attribute Selection Mode Group
        selection_mode_group = QWidget()
        selection_mode_layout = QVBoxLayout(selection_mode_group)
    
        self.manual_mode_radio = QRadioButton("Manual Attribute Selection")
        self.regression_mode_radio = QRadioButton("Use Regression Attributes")
    
        self.manual_mode_radio.setChecked(True)
    
        selection_mode_layout.addWidget(self.manual_mode_radio)
        selection_mode_layout.addWidget(self.regression_mode_radio)
    
        self.manual_mode_radio.toggled.connect(self.toggle_attribute_selection)
        self.regression_mode_radio.toggled.connect(self.toggle_attribute_selection)
    
        left_layout.addWidget(selection_mode_group)

        labels = ["Regression"]
        StyledDropdown.calculate_label_width(labels)  # Update the label width

        regression_layout = QHBoxLayout()

        # Now create the dropdown after updating the width
        self.regression_dropdown = StyledDropdown("Regression")
        self.regression_dropdown.setEnabled(False)

        # 🔹 Add the dropdown first to keep it aligned left
        regression_layout.addWidget(self.regression_dropdown)

        # 🔹 Add stretch AFTER to push any additional elements to the right
        regression_layout.addStretch(1)

        # 🔹 Finally, add the layout to the main layout
        left_layout.addLayout(regression_layout)


        # Connect dropdown signal
        self.regression_dropdown.combo.currentIndexChanged.connect(self.update_attributes_from_regression)






        # Selectors
        self.planned_selector = TwoListSelector("Available Planned Wells", "Selected Planned Wells")
        self.active_selector = TwoListSelector("Available Active Wells", "Selected Active Wells")
        self.attr_selector = TwoListSelector("Available Attributes", "Selected Attributes")

        left_layout.addWidget(self.planned_selector)
        left_layout.addWidget(self.active_selector)
        left_layout.addWidget(self.attr_selector)

        # Create left widget
        left_widget = QWidget()
        left_widget.setLayout(left_layout)

        # === RIGHT PANEL ===
        right_layout = QVBoxLayout()

        # Results table
        self.results_table = QTableWidget()
        self._setup_table()
        right_layout.addWidget(self.results_table, 1)

        # Buttons layout
        # Buttons layout
        button_layout = QHBoxLayout()

        # Create buttons
        self.weights_button = StyledButton("Weights", button_type="function")
        self.calculate_button = StyledButton("Calculate", button_type="function")
        self.decline_curve_button = StyledButton("Assign DC", button_type="function")
        self.export_button = StyledButton("Export", button_type="export")
        self.close_button = StyledButton("Close", button_type="close")

        # Set fixed width for all buttons (reduced width)
        button_width = 100 # Reduced from 150 to 120
        for button in [self.weights_button, self.calculate_button, 
                       self.decline_curve_button, self.export_button, self.close_button]:
            button.setFixedWidth(button_width)

        # Add a spacer to push buttons to the right
        button_layout.addStretch()

        # Add buttons in the desired order
        button_layout.addWidget(self.weights_button)
        button_layout.addWidget(self.calculate_button)
        button_layout.addWidget(self.decline_curve_button)
        button_layout.addWidget(self.export_button)
        button_layout.addWidget(self.close_button)

        # Add buttons BELOW the table
        right_layout.addLayout(button_layout)

        # Create right widget
        right_widget = QWidget()
        right_widget.setLayout(right_layout)

        # Add panels to main layout
        main_layout.addWidget(left_widget, 1)
        main_layout.addWidget(right_widget, 2)

        # Connect signals


        # Connect button signals
        self.close_button.clicked.connect(self.reject)
        self.weights_button.clicked.connect(self.open_weights_dialog)
        self.calculate_button.clicked.connect(self.run_comparison)
        self.decline_curve_button.clicked.connect(self.assign_type_curve)
        self.export_button.clicked.connect(self.export_to_excel)

        # Set the layout
        self.setLayout(main_layout)

        # Load initial data
        self.load_data()

    def _setup_table(self):
        """Setup the results table with fixed column widths."""
        self.results_table.setColumnCount(4)
        self.results_table.setHorizontalHeaderLabels([
            "Planned Well", "Matched Active Well", "Similarity Score", "Details"
        ])
        header = self.results_table.horizontalHeader()
    
        # Set fixed widths for columns
        total_width = self.results_table.width()
        header.setMinimumSectionSize(100)
        header.resizeSection(0, 150)  # Planned Well
        header.resizeSection(1, 150)  # Matched Well
        header.resizeSection(2, 100)  # Similarity Score
        header.resizeSection(3, 200)  # Details - fixed width but can expand
    
        # Last column stretches to fill remaining space
        header.setStretchLastSection(True)

    def load_data(self):
        """Load initial data for the selectors."""
        try:
            # Get numeric attributes only
            numeric_columns = self.db_manager.get_numeric_attributes()
            planned_wells = self.db_manager.get_UWIs_by_status("Planned")
    
            # Get initial active wells list
            active_wells = self.db_manager.get_UWIs_by_status("Active")
    
            # Filter active wells to only those with model properties
            filtered_active_wells = []
            for UWI in active_wells:
                # Check if well has model properties in scenario 1 (reference scenario)
                model_properties_df = self.db_manager.retrieve_model_data_by_scenario_and_UWI(
                    scenario_id=1,
                    UWI=UWI
                )
                if model_properties_df is not None and not model_properties_df.empty:
                    filtered_active_wells.append(UWI)
    
            # Load regression tables
            regression_tables = self.db_manager.get_regression_tables()
            self.regression_dropdown.clear()
            self.regression_dropdown.addItem("Select Regression")
        
            for regression in regression_tables:
                # Assuming regression is a tuple with (id, name, ...)
                regression_name = regression[1]  # Adjust index based on your get_regression_tables method
                self.regression_dropdown.addItem(regression_name)

            # Populate lists
            self.planned_selector.set_left_items(planned_wells)
            self.active_selector.set_left_items(filtered_active_wells)
            self.attr_selector.set_left_items(sorted(numeric_columns))
    
        except Exception as e:
            print(f"Error loading data: {e}")


    def assign_type_curve(self):
        """Assign type curves to selected planned wells, run DCA, and update production rates."""

        # Step 1: Get scenario name from user
        scenario_dialog = ScenarioNameDialog(self.db_manager, self)
        if scenario_dialog.exec() == QDialog.Rejected:
            return  # User canceled

        scenario_name = scenario_dialog.get_selected_scenario().strip()

        if not scenario_name:
            QMessageBox.warning(self, "Invalid Scenario", "Please enter a valid scenario name.")
            return

        # Step 2: Check if scenario exists, else create it
        self.scenario_id = self.db_manager.get_scenario_id(scenario_name)
        print(self.scenario_id)
        if self.scenario_id:
            self.db_manager.set_active_scenario(self.scenario_id)
        else:
            # 🔹 Scenario doesn't exist, so create it
            self.scenario_id = self.db_manager.insert_scenario_name(scenario_name)
            if self.scenario_id:
                self.db_manager.set_active_scenario(self.scenario_id)
            else:
                QMessageBox.critical(self, "Error", f"Failed to create scenario '{scenario_name}'.")
                return  # ⛔ Exit if creation failed

      # Update active scenario

        # Step 3: Get selected wells from planned list
        selected_planned_wells = self.planned_selector.get_right_items()

        if not selected_planned_wells:
            QMessageBox.warning(self, "No Selection", "Please select at least one planned well.")
            return

        # Step 2: Get well pad properties for selected planned wells
        well_pads_df = self.db_manager.get_well_pads_for_wells(self.scenario_id, selected_planned_wells)
        well_pad_dict = well_pads_df.set_index("UWI").to_dict(orient="index")

        total_wells = len(selected_planned_wells)
        processed_wells = 0
        skipped_wells = 0
        error_wells = []

        # Step 3: Iterate only over planned wells that exist in the model
        for UWI_planned in selected_planned_wells:
            try:
                # Step 4: Get the best-matched active well from the comparison table
                matched_UWI = self._get_matched_UWI_from_table(UWI_planned)
                print(f"Matched UWI for {UWI_planned}: {matched_UWI}")

                if not matched_UWI:
                    skipped_wells += 1
                    continue  # Skip if no match found

                # Step 5: Retrieve model properties for the matched UWI
                model_properties_df = self.db_manager.retrieve_model_data_by_scenario_and_UWI(
                    scenario_id=1,  # Use reference scenario for UWI lookup
                    UWI=matched_UWI
                )

                if model_properties_df is None or model_properties_df.empty:
                    skipped_wells += 1
                    continue  # Skip if no model properties found

                model_properties = model_properties_df.iloc[0].to_dict()  # Convert DataFrame row to dict

                # Step 6: Delete old model properties & production rates **ONLY IF the well has a decline curve**
                self.db_manager.delete_model_properties_for_wells(self.scenario_id, [UWI_planned])
                self.db_manager.delete_production_rates_for_wells(self.scenario_id, [UWI_planned])

                # Step 7: Get well pad data for this planned UWI (if available)
                well_pad_data = well_pad_dict.get(UWI_planned, {})
                print(well_pad_data)

                # Step 8: Map well pad fields to model properties
                # Step 8: Map well pad fields to model properties
                field_mapping = {
                    'max_oil_production_date': 'start_date',
                    'max_gas_production_date': 'start_date',
                    'capital_expenditures': 'total_capex_cost',
                    'operating_expenditures': 'total_opex_cost'
                }

                # Apply field mapping from well pad data
                for target_field, source_field in field_mapping.items():
                    if source_field in well_pad_data and well_pad_data[source_field] not in [None, np.nan, ""]:
                        model_properties[target_field] = well_pad_data[source_field]
                    else:
                        print(f"Skipping {target_field} - No valid data found in well pad.")

                # 🔹 Force overwrite critical values to ensure planned well's data is always used
                model_properties["max_oil_production_date"] = well_pad_data.get("start_date", model_properties.get("max_oil_production_date", "Unknown"))
                model_properties["max_gas_production_date"] = well_pad_data.get("start_date", model_properties.get("max_gas_production_date", "Unknown"))

                # 🔹 Force overwrite CAPEX and OPEX values
                model_properties["capital_expenditures"] = well_pad_data.get("total_capex_cost", model_properties.get("capital_expenditures", 0))
                model_properties["operating_expenditures"] = well_pad_data.get("total_opex_cost", model_properties.get("operating_expenditures", 0))

                # 🔹 Ensure UWI is always the planned well
                model_properties["UWI"] = UWI_planned
                model_properties['scenario_id'] = self.scenario_id

                # Step 9: Ensure required columns exist
                required_columns = [
                    "scenario_id", "UWI",  # UWI should now reference the planned well
                    "max_oil_production", "max_gas_production",
                    "max_oil_production_date", "max_gas_production_date",
                    "one_year_oil_production", "one_year_gas_production",
                    "di_oil", "di_gas",
                    "oil_b_factor", "gas_b_factor",
                    "min_dec_oil", "min_dec_gas",
                    "model_oil", "model_gas",
                    "economic_limit_type", "economic_limit_date",
                    "oil_price", "gas_price",
                    "oil_price_dif", "gas_price_dif",
                    "discount_rate", "working_interest",
                    "royalty", "tax_rate",
                    "capital_expenditures", "operating_expenditures",
                    "net_price_oil", "net_price_gas",
                    "gas_model_status", "oil_model_status",
                    "q_oil_eur", "q_gas_eur",
                    "EFR_oil", "EFR_gas",
                    "EUR_oil_remaining", "EUR_gas_remaining",
                    "npv", "npv_discounted"
                ]

                # Step 10: Convert dictionary to DataFrame for storage
                df_UWI_model_data = pd.DataFrame([model_properties])[required_columns]
                print(df_UWI_model_data)

                # Step 11: Convert date columns to formatted strings
                date_columns = ['max_oil_production_date', 'max_gas_production_date', 'economic_limit_date']
                for col in date_columns:
                    if col in df_UWI_model_data.columns:
                        df_UWI_model_data[col] = pd.to_datetime(df_UWI_model_data[col], errors='coerce').dt.strftime('%Y-%m-%d')


                self.db_manager.update_well_pad_decline_curve(UWI_planned, self.scenario_id, matched_UWI)

                # Step 12: Save model properties to DB
                self.db_manager.overwrite_model_properties(df_UWI_model_data, self.scenario_id)

                # Step 13: Run Decline Curve Analysis (DCA)
                self.UWI_production_rates_data, self.UWI_error, self.UWI_model_data = self.dca.planned_prod_rate(df_UWI_model_data)

                # Step 14: Save production rates to DB
                self.db_manager.update_UWI_prod_rates(self.UWI_production_rates_data, self.scenario_id)

                # Step 15: Save error tracking
                self.UWI_error = pd.DataFrame({
                    'UWI': [UWI_planned],  # Use planned well for tracking
                    'sum_error_oil': [0],
                    'sum_error_gas': [0]
                })
                self.db_manager.update_UWI_errors(self.UWI_error, self.scenario_id)


                processed_wells += 1

            except Exception as e:
                error_wells.append((UWI_planned, str(e)))
                continue

        # Step 16: Show Results Summary
        if error_wells:
            error_msg = "\n".join([f"UWI: {UWI_planned} - Error: {error}" for UWI_planned, error in error_wells])
            QMessageBox.warning(
                self,
                "Type Curve Assignment Complete",
                f"Assigned type curves for {processed_wells}/{total_wells} wells.\n"
                f"Skipped {skipped_wells} wells (no matching model properties or decline curve).\n"
                f"{len(error_wells)} wells had errors:\n{error_msg}"
            )
        else:
            QMessageBox.information(
                self,
                "Type Curve Assignment Complete",
                f"Successfully assigned type curves to {processed_wells}/{total_wells} wells!\n"
                f"Skipped {skipped_wells} wells (no matching model properties or decline curve)."
            )


    def _get_matched_UWI_from_table(self, planned_UWI):
        """
        Retrieve the matched UWI from the results table for a given planned UWI.
        """
        for row in range(self.results_table.rowCount()):
            table_planned_UWI = self.results_table.item(row, 0).text()  # Column 0 = Planned Well
            if table_planned_UWI == planned_UWI:
                matched_UWI = self.results_table.item(row, 1).text()  # Column 1 = Matched Well
                return matched_UWI if matched_UWI and matched_UWI != "No Match" else None
        return None  # If not found
    def export_to_excel(self):
        """Exports the comparison results to an Excel file."""
        file_path, _ = QFileDialog.getSaveFileName(self, "Save as Excel", "", "Excel Files (*.xlsx)")
        if not file_path:
            return  # User canceled

        # Convert table data to a DataFrame
        data = []
        for row in range(self.results_table.rowCount()):
            row_data = [self.results_table.item(row, col).text() if self.results_table.item(row, col) else "" 
                        for col in range(self.results_table.columnCount())]
            data.append(row_data)

        columns = [self.results_table.horizontalHeaderItem(col).text() for col in range(self.results_table.columnCount())]
        df = pd.DataFrame(data, columns=columns)

        try:
            df.to_excel(file_path, index=False)
            QMessageBox.information(self, "Export Successful", f"Results exported to {file_path}")
        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Failed to save Excel file:\n{str(e)}")

### CONTINUE WITH EXISTING CODE:


    def open_weights_dialog(self):
        dialog = WeightsDialog(self)
        selected_attributes = self.attr_selector.get_right_items()

        if not selected_attributes:
            QMessageBox.warning(self, "No Attributes Selected", 
                              "Please select attributes before adjusting weights.")
            return
    
        # If regression mode is on and a regression is selected, use those weights
        if (self.regression_mode_radio.isChecked() and 
            self.regression_dropdown.currentIndex() > 0):
            regression_name = self.regression_dropdown.currentText()
            weights = self.db_manager.get_regression_feature_weights(regression_name)
            dialog.add_weight_sliders(selected_attributes, weights)
        else:
            # Default to manual mode
            dialog.add_weight_sliders(selected_attributes)

        if dialog.exec():
            self.iqr_multiplier = dialog.sensitivity_slider.value()
            self.normalize_values = dialog.normalize_checkbox.isChecked()
            self.zero_outliers = dialog.zero_outliers_checkbox.isChecked()
            self.weight_sliders = {
                attr: slider.value() / 100.0
                for attr, slider in dialog.weight_sliders.items()
            }

    def run_comparison(self):
        """Execute the well comparison."""
        try:
            # Get selected items with debug logging
            selected_attributes = self.attr_selector.get_right_items()
            planned_wells = self.planned_selector.get_right_items()
            active_wells = self.active_selector.get_right_items()

            print("\nDEBUG: Initial Selection")
            print(f"Selected Attributes: {selected_attributes}")
            print(f"Planned Wells: {planned_wells}")
            print(f"Active Wells: {active_wells}")

            # Validate selections
            if not self._validate_selections(selected_attributes, planned_wells, active_wells):
                return

            # Get well data from database with error handling
            try:
                planned_data = self.db_manager.get_well_attributes(planned_wells, selected_attributes)
                print("\nDEBUG: Retrieved Planned Data")
                print(f"Shape: {planned_data.shape}")
                print(f"Columns: {planned_data.columns.tolist()}")
                print("\nSample of planned data:")
                print(planned_data.head())
            
                active_data = self.db_manager.get_well_attributes(active_wells, selected_attributes)
                print("\nDEBUG: Retrieved Active Data")
                print(f"Shape: {active_data.shape}")
                print(f"Columns: {active_data.columns.tolist()}")
                print("\nSample of active data:")
                print(active_data.head())

            except Exception as e:
                print(f"Error retrieving data: {str(e)}")
                QMessageBox.critical(self, "Data Error", 
                    f"Failed to retrieve well data from database: {str(e)}")
                return

            # Validate data exists and has content
            if planned_data.empty:
                QMessageBox.warning(self, "No Data", 
                    "No data found for the selected planned wells and attributes.")
                return
        
            if active_data.empty:
                QMessageBox.warning(self, "No Data", 
                    "No data found for the selected active wells and attributes.")
                return

            # Check for missing columns
            missing_cols = set(selected_attributes) - set(planned_data.columns)
            if missing_cols:
                print(f"Warning: Missing columns in planned data: {missing_cols}")
                QMessageBox.warning(self, "Missing Data", 
                    f"Some selected attributes are missing from planned wells: {missing_cols}")
            
            missing_cols = set(selected_attributes) - set(active_data.columns)
            if missing_cols:
                print(f"Warning: Missing columns in active data: {missing_cols}")
                QMessageBox.warning(self, "Missing Data", 
                    f"Some selected attributes are missing from active wells: {missing_cols}")

            # Print data statistics
            print("\nDEBUG: Data Statistics")
            print("\nPlanned Wells Data Statistics:")
            for col in planned_data.columns:
                non_null = planned_data[col].count()
                total = len(planned_data)
                print(f"{col}: {non_null}/{total} non-null values")
            
            print("\nActive Wells Data Statistics:")
            for col in active_data.columns:
                non_null = active_data[col].count()
                total = len(active_data)
                print(f"{col}: {non_null}/{total} non-null values")

            # Run appropriate comparison
            try:
                if len(selected_attributes) == 1:
                    print("\nRunning single attribute comparison")
                    results = self._single_attribute_comparison(planned_data, active_data)
                else:
                    print("\nRunning multi-attribute comparison")
                    results = self._multi_attribute_comparison(planned_data, active_data)

                # Validate results
                if not results:
                    QMessageBox.warning(self, "Comparison Failed", 
                        "No valid comparisons could be made with the selected data.")
                    return

                print("\nDEBUG: Comparison Results")
                print(f"Number of results: {len(results)}")
                print("First result sample:", results[0])

                # Display results
                try:
                    self._display_results(results, selected_attributes)
                    print("\nResults displayed successfully")
                except Exception as e:
                    print(f"Error displaying results: {str(e)}")
                    import traceback
                    traceback.print_exc()
                    QMessageBox.critical(self, "Display Error", 
                        f"Error displaying comparison results: {str(e)}")

            except Exception as e:
                print(f"Error during comparison: {str(e)}")
                import traceback
                traceback.print_exc()
                QMessageBox.critical(self, "Comparison Error", 
                    f"Error performing comparison: {str(e)}")

        except Exception as e:
            print(f"Error in run_comparison: {str(e)}")
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "Error", 
                f"An error occurred while running the comparison: {str(e)}")



    def _validate_selections(self, attributes: List[str], planned_wells: List[str], 
                           active_wells: List[str]) -> bool:
        """Validate user selections before comparison."""
        if not attributes:
            QMessageBox.warning(self, "Invalid Selection", 
                              "Please select at least one attribute")
            return False
            
        if not planned_wells:
            QMessageBox.warning(self, "Invalid Selection", 
                              "Please select at least one planned well")
            return False
            
        if not active_wells:
            QMessageBox.warning(self, "Invalid Selection", 
                              "Please select at least one active well")
            return False
            
        return True

    def mask_outliers(self, df: pd.DataFrame) -> pd.DataFrame:
        """Replaces outlier values with NaN or 0."""
        numeric_cols = df.select_dtypes(include=['int64', 'float64']).columns
        if numeric_cols.empty:
            return df.copy()
    
        try:
            def apply_iqr_mask(col):
                try:
                    Q1 = col.quantile(0.25)
                    Q3 = col.quantile(0.75)
                    IQR = Q3 - Q1
            
                    lower_bound = Q1 - (self.iqr_multiplier * IQR)
                    upper_bound = Q3 + (self.iqr_multiplier * IQR)
            
                    # Replace outliers with 0 or NaN based on checkbox
                    replacement = 0 if hasattr(self, 'zero_outliers') and self.zero_outliers else np.nan
                    masked = col.where((col >= lower_bound) & (col <= upper_bound), replacement)
                
                    outlier_count = ((col < lower_bound) | (col > upper_bound)).sum()
                    if outlier_count > 0:
                        print(f"Column {col.name}: {outlier_count} outliers masked")
                
                    return masked
            
                except Exception as e:
                    print(f"Error processing column {col.name}: {str(e)}")
                    return col
    
            result = df.copy()
            result[numeric_cols] = result[numeric_cols].apply(apply_iqr_mask)
            return result
    
        except Exception as e:
            print(f"Error in outlier detection: {str(e)}")
            return df.copy()

    def _single_attribute_comparison(self, planned_data: pd.DataFrame, 
                                   active_data: pd.DataFrame) -> List[Dict]:
        """Compare wells using a single attribute."""
        results = []
        attribute = planned_data.columns[0]

        for planned_well in planned_data.index:
            planned_val = planned_data.loc[planned_well, attribute]
            best_match = None
            best_diff = float('inf')
            best_active_val = None

            for active_well in active_data.index:
                active_val = active_data.loc[active_well, attribute]
                if pd.isna(planned_val) or pd.isna(active_val):
                    continue

                try:
                    diff = abs(planned_val - active_val) / max(abs(planned_val), 
                                                             abs(active_val), 1e-6) * 100

                    if diff < best_diff:
                        best_diff = diff
                        best_match = active_well
                        best_active_val = active_val
                except ZeroDivisionError:
                    continue

            if best_match:
                similarity = 1 / (1 + best_diff / 100)
                results.append({
                    'planned_well': planned_well,
                    'matched_well': best_match,
                    'similarity': similarity,
                    'details': f"{attribute}:\nPlanned: {planned_val:.2f}\n"
                              f"Active: {best_active_val:.2f}\nDiff: {best_diff:.1f}%"
                })
            else:
                results.append({
                    'planned_well': planned_well,
                    'matched_well': 'No Match',
                    'similarity': -1,
                    'details': ''
                })

        return results
        

    def _multi_attribute_comparison(self, planned_data: pd.DataFrame, active_data: pd.DataFrame) -> List[Dict]:
        """Compare wells using multiple attributes with weights."""
        results = []
    
        try:
            print("\nDEBUG: Starting Multi-Attribute Comparison")
            print("Planned data shape:", planned_data.shape)
            print("Active data shape:", active_data.shape)
        
            # Get numeric columns with detailed logging
            numeric_cols = planned_data.select_dtypes(include=['int64', 'float64']).columns
            print(f"\nNumeric columns found: {numeric_cols.tolist()}")
        
            if numeric_cols.empty:
                raise ValueError("No numeric columns available for comparison")

            # Print data sample for debugging
            print("\nPlanned Data Sample:")
            print(planned_data.head())
            print("\nActive Data Sample:")
            print(active_data.head())

            # Handle data normalization if enabled
            normalized_planned = planned_data.copy()
            normalized_active = active_data.copy()
        
            if hasattr(self, 'normalize_values') and self.normalize_values:
                print("\nNormalizing data...")
                for column in numeric_cols:
                    all_values = pd.concat([planned_data[column], active_data[column]])
                    mean_val = all_values.mean()
                    std_val = all_values.std()
                
                    if std_val > 0:
                        normalized_planned[column] = (planned_data[column] - mean_val) / std_val
                        normalized_active[column] = (active_data[column] - mean_val) / std_val
                        print(f"Normalized {column} - Mean: {mean_val}, Std: {std_val}")

            # Get or create weights
            weights = {}
            if hasattr(self, 'weight_sliders') and self.weight_sliders:
                print("\nUsing custom weights:", self.weight_sliders)
                total_weight = sum(self.weight_sliders.values())
                weights = {col: self.weight_sliders.get(col, 1.0) / total_weight 
                          for col in numeric_cols}
            else:
                print("\nUsing equal weights")
                weight_value = 1.0 / len(numeric_cols)
                weights = {col: weight_value for col in numeric_cols}

            print("\nFinal weights being used:", weights)

            # Compare each planned well
            for planned_well in planned_data.index:
                try:
                    print(f"\nProcessing planned well: {planned_well}")
                    planned_values = normalized_planned.loc[planned_well]
                    best_match = None
                    best_similarity = -float('inf')
                    best_details = {}
                
                    print(f"Values for {planned_well}:")
                    for col in numeric_cols:
                        print(f"{col}: {planned_values[col]}")
                
                    # Compare with each active well
                    for active_well in active_data.index:
                        try:
                            active_values = normalized_active.loc[active_well]
                            similarities = []
                            attr_details = {}
                            valid_comparisons = 0
                            non_zero_comparisons = 0
                        
                            print(f"\nComparing with active well: {active_well}")
                        
                            # Compare each attribute
                            for attr in numeric_cols:
                                try:
                                    p_val = float(planned_values[attr])
                                    a_val = float(active_values[attr])
                                
                                    # Skip if both values are 0 unless it's specifically meaningful
                                    if p_val == 0 and a_val == 0 and not any(x in attr.lower() for x in ['count', 'parent']):
                                        print(f"Skipping {attr} - both values are 0")
                                        continue
                                    
                                    valid_comparisons += 1
                                    if p_val != 0 or a_val != 0:
                                        non_zero_comparisons += 1
                                
                                    # Calculate normalized difference
                                    diff = abs(p_val - a_val)
                                    max_val = max(abs(p_val), abs(a_val), 1e-10)
                                    normalized_diff = diff / max_val
                                
                                    # Calculate similarity score (0-1)
                                    attr_similarity = 1 / (1 + normalized_diff)
                                
                                    # Apply weight
                                    weight = weights[attr]
                                    weighted_similarity = attr_similarity * weight
                                    similarities.append(weighted_similarity)
                                
                                    # Store comparison details
                                    attr_details[attr] = {
                                        'planned_val': float(planned_data.loc[planned_well, attr]),
                                        'active_val': float(active_data.loc[active_well, attr]),
                                        'weight': weight,
                                        'similarity': float(attr_similarity),
                                        'diff': float(normalized_diff)
                                    }
                                
                                    print(f"Compared {attr}: similarity={attr_similarity:.3f}, "
                                          f"weight={weight:.3f}, weighted={weighted_similarity:.3f}")
                                
                                except Exception as e:
                                    print(f"Error comparing {attr}: {str(e)}")
                                    continue

                            # Calculate overall similarity if we have enough valid comparisons
                            min_required_comparisons = max(3, len(numeric_cols) * 0.3)
                            if valid_comparisons >= min_required_comparisons and non_zero_comparisons > 0:
                                # Calculate weighted average similarity
                                overall_similarity = sum(similarities) / sum(weights[attr] 
                                    for attr in attr_details.keys())
                            
                                print(f"Overall similarity with {active_well}: {overall_similarity:.3f} "
                                      f"({valid_comparisons} valid, {non_zero_comparisons} non-zero)")
                            
                                if overall_similarity > best_similarity:
                                    best_similarity = overall_similarity
                                    best_match = active_well
                                    best_details = attr_details
                            else:
                                print(f"Skipping {active_well} - insufficient comparisons "
                                      f"(valid: {valid_comparisons}, non-zero: {non_zero_comparisons}, "
                                      f"required: {min_required_comparisons})")
                    
                        except Exception as e:
                            print(f"Error processing active well {active_well}: {str(e)}")
                            continue

                    # Store results for this planned well
                    result = {
                        'planned_well': planned_well,
                        'matched_well': best_match if best_match else 'No Match',
                        'similarity': float(best_similarity) if best_similarity > -float('inf') else 0.0
                    }
                    result.update(best_details)  # Add all attribute details
                    results.append(result)
                
                    print(f"\nFinal match for {planned_well}: {result['matched_well']} "
                          f"(similarity: {result['similarity']:.3f})")
                    print("Attribute details:", best_details)

                except Exception as e:
                    print(f"Error processing planned well {planned_well}: {str(e)}")
                    continue

        except Exception as e:
            print(f"Error in multi-attribute comparison: {str(e)}")
            import traceback
            traceback.print_exc()
            QMessageBox.warning(self, "Comparison Error", f"Error performing comparison: {str(e)}")
            return []

        return results
    

    def toggle_attribute_selection(self):
        """Enable regression dropdown and update attributes when switching modes."""
        is_regression_mode = self.regression_mode_radio.isChecked()
        self.regression_dropdown.setEnabled(is_regression_mode)
    
        if is_regression_mode:
            if self.regression_dropdown.currentIndex() > 0:  # Ensure a regression is selected
                self.update_attributes_from_regression()
        else:
            self.load_original_attributes()


    def load_original_attributes(self):
        """Reload original numeric attributes when switching back to manual mode"""
        try:
            # Get numeric attributes only
            numeric_columns = self.db_manager.get_numeric_attributes()
    
            self.attr_selector.clear_left_items()
            self.attr_selector.clear_right_items() 
            self.attr_selector.set_left_items(sorted(numeric_columns))
    
        except Exception as e:
            print(f"Error loading original attributes: {e}")

    def update_attributes_from_regression(self):
        """Update the attribute selector and weight sliders when a regression is selected."""
        # Ensure we are in regression mode
        if not self.regression_mode_radio.isChecked():
            return
    
        selected_regression = self.regression_dropdown.currentText()
    
        if selected_regression and selected_regression != "Select Regression":
            # Fetch attributes for the selected regression
            attributes = self.db_manager.get_regression_attributes(selected_regression)
        
            # Clear existing attribute selections
        
                        # CORRECT
            self.attr_selector.clear_left_items()
            self.attr_selector.clear_right_items()
        
            # Add attributes to available list
            if attributes:
                # Assuming attributes is a list of tuples or just attribute names
                attribute_names = [attr[0] if isinstance(attr, tuple) else attr for attr in attributes]
                self.attr_selector.set_left_items(attribute_names)
        
            # Fetch and set weights from the regression
            self.load_regression_weights(selected_regression)
        else:
            # If no regression selected, restore original attributes
            self.load_original_attributes()

 

    def load_regression_weights(self, regression_name):
        """Load weights from the regression table"""
        try:
            # Fetch weights from the database
            weights = self.db_manager.get_regression_feature_weights(regression_name)
        
            print("Weights retrieved:", weights)
        
            # Update weight sliders if weights are available
            if weights:
                # Open weights dialog
                dialog = WeightsDialog(self)
            
                # Get the attributes from the regression
                attributes = self.db_manager.get_regression_attributes(regression_name)
                attribute_names = [attr[0] if isinstance(attr, tuple) else attr for attr in attributes]
            
                print("Attributes:", attribute_names)
                print("Weights before passing:", weights)
            
                # Add weight sliders with retrieved weights
                dialog.add_weight_sliders(attribute_names, weights)
            
                # Store the weights
                self.weight_sliders = {attr: weight for attr, weight in weights.items()}
            
                print("Stored weights:", self.weight_sliders)
            else:
                print("No weights found for this regression")
    
        except Exception as e:
            print(f"Error loading regression weights: {e}")
            import traceback
            traceback.print_exc()



    def _display_results(self, results: List[Dict], selected_attributes: List[str]):
        """Display comparison results in table."""
        try:
            print("\nDisplaying Results")
            
            # Set up table columns
            columns = ["Planned Well", "Matched Active Well", "Similarity Score"] + selected_attributes
            self.results_table.setColumnCount(len(columns))
            self.results_table.setHorizontalHeaderLabels(columns)
            self.results_table.setRowCount(len(results))

            # Populate table
            for row, result in enumerate(results):
                print(f"\nProcessing result row {row}:")
                print(result)
                
                # Add planned well
                self.results_table.setItem(row, 0, 
                    QTableWidgetItem(str(result['planned_well'])))

                # Add matched well
                self.results_table.setItem(row, 1, 
                    QTableWidgetItem(str(result['matched_well'])))

                # Add similarity score with color coding
                similarity = result['similarity']
                if similarity >= 0:
                    score_item = QTableWidgetItem(f"{similarity:.3f}")
                    
                    # Color code based on similarity
                    if similarity >= 0.8:
                        score_item.setBackground(QColor(144, 238, 144))  # Light green
                    elif similarity >= 0.5:
                        score_item.setBackground(QColor(255, 255, 224))  # Light yellow
                    else:
                        score_item.setBackground(QColor(255, 182, 193))  # Light red
                else:
                    score_item = QTableWidgetItem("N/A")
                
                self.results_table.setItem(row, 2, score_item)

                # Add attribute details
                for col_idx, attr in enumerate(selected_attributes, start=3):
                    if attr in result:
                        attr_details = result[attr]
                        if isinstance(attr_details, dict):
                            similarity = attr_details.get('similarity', 0)
                            weight = attr_details.get('weight', 0)
                            weighted = similarity * weight
                            
                            # Format cell text to show similarity score
                            cell_text = f"{similarity:.3f}"
                            
                            # Format the tooltip with all details
                            attr_text = (
                                f"Attribute: {attr}\n"
                                f"Planned Value: {attr_details['planned_val']:.3f}\n"
                                f"Active Value: {attr_details['active_val']:.3f}\n"
                                f"Similarity: {similarity:.3f}\n"
                                f"Weight: {weight:.3f}\n"
                                f"Weighted Score: {weighted:.3f}"
                            )
                            
                            # Create cell item
                            diff_item = QTableWidgetItem(cell_text)
                            diff_item.setToolTip(attr_text)
                            
                            # Color code based on similarity
                            if similarity >= 0.8:
                                diff_item.setBackground(QColor(144, 238, 144))  # Light green
                            elif similarity >= 0.5:
                                diff_item.setBackground(QColor(255, 255, 224))  # Light yellow
                            else:
                                diff_item.setBackground(QColor(255, 182, 193))  # Light red
                                
                            self.results_table.setItem(row, col_idx, diff_item)
                        else:
                            self.results_table.setItem(row, col_idx, 
                                QTableWidgetItem("Invalid data"))
                    else:
                        self.results_table.setItem(row, col_idx, 
                            QTableWidgetItem("No data"))

            # Auto-adjust column widths
            self.results_table.resizeColumnsToContents()

        except Exception as e:
            print(f"Error displaying results: {str(e)}")
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "Display Error", str(e))