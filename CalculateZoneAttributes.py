from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, 
                              QGroupBox, QCheckBox, QMessageBox)
from StyledDropdown import StyledDropdown
from StyledButton import StyledButton
from StyledDropdown import StyledInputBox
from StyledTwoListSelector import TwoListSelector
import pandas as pd
import numpy as np

class ZoneAttributeCalculator(QDialog):
    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.setWindowTitle("Zone Attribute Calculator")
        self.setMinimumSize(800, 600)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # Zone Selection Group
        zone_group = QGroupBox("Zone Selection")
        zone_layout = QVBoxLayout()

        # Source Zone Dropdown
        self.zone_combo = StyledDropdown(
            label_text="Source Zone",
            parent=self
        )
        zone_layout.addWidget(self.zone_combo)

        # New Zone Name Input
        self.new_zone_name = StyledInputBox(
            label_text="New Zone Name",
            parent=self
        )
        zone_layout.addWidget(self.new_zone_name)

        zone_group.setLayout(zone_layout)
        layout.addWidget(zone_group)

        # Calculation Method Selector
        self.calc_selector = TwoListSelector(
            left_title="Available Calculations",
            right_title="Selected Calculations"
        )
        # Add all calculation methods to left list
        calc_methods = [
            "Sum", "Mean", "Median", "Min", "Max", 
            "Standard Deviation", "Variance", "Count"
        ]
        self.calc_selector.set_left_items(calc_methods)
        layout.addWidget(self.calc_selector)

        # Attribute Selection using TwoListSelector
        self.attribute_selector = TwoListSelector(
            left_title="Available Attributes",
            right_title="Selected Attributes"
        )
        layout.addWidget(self.attribute_selector)

        # Bottom Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.calculate_button = StyledButton("Calculate", "function", self)
        self.close_button = StyledButton("Close", "close", self)
        
        self.calculate_button.clicked.connect(self.do_calculate)
        self.close_button.clicked.connect(self.reject)
        
        button_layout.addWidget(self.calculate_button)
        button_layout.addWidget(self.close_button)
        
        layout.addLayout(button_layout)

        # Populate zones and connect signals
        self.populate_zones()
        self.zone_combo.combo.currentTextChanged.connect(self.zone_changed)


    def populate_zones(self):
        """Load zones from the database"""
        try:
            zones = self.db_manager.fetch_zone_names_by_type("Zone")
            zone_names = ["Select Zone"]
            zone_names.extend([zone[0] for zone in zones])
            self.zone_combo.setItems(zone_names)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error loading zones: {str(e)}")

    def zone_changed(self, zone_name):
        """When zone is selected, populate available attributes list"""
        if zone_name == "Select Zone":
            self.attribute_selector.clear()
            return

        try:
            # Get zone data
            zone_data = self.db_manager.fetch_zone_depth_data(zone_name)
            if zone_data is None or zone_data.empty:
                QMessageBox.warning(self, "Warning", f"No data found for zone: {zone_name}")
                return
                
            # Find numeric columns
            numeric_cols = zone_data.select_dtypes(include=[np.number]).columns
            
            # Filter out system columns
            skip_cols = {'id', 'ID', 'Top_Depth', 'Base_Depth'}
            numeric_attrs = [col for col in numeric_cols if col not in skip_cols]
            
            # Update available attributes
            self.attribute_selector.clear()
            self.attribute_selector.set_left_items(sorted(numeric_attrs))
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error loading attributes: {str(e)}")

    def do_calculate(self):
        """Perform multiple zone attribute calculations simultaneously."""
        try:
            # Get selected calculation methods
            selected_methods = self.calc_selector.get_right_items()
            
            if not selected_methods:
                QMessageBox.warning(self, "Warning", "Please select at least one calculation method")
                return

            # Validate inputs
            zone_name = self.zone_combo.currentText()
            new_zone = self.new_zone_name.text().strip()

            if zone_name == "Select Zone":
                QMessageBox.warning(self, "Warning", "Please select a source zone")
                return
        
            if not new_zone:
                QMessageBox.warning(self, "Warning", "Please enter a new zone name")
                return

            # Check if the new zone name already exists
            if self.db_manager.zone_exists(new_zone, "Well"):
                QMessageBox.warning(self, "Warning", 
                                  f"The zone '{new_zone}' already exists. Please choose a different name.")
                return

            # Get selected attributes
            selected_attrs = self.attribute_selector.get_right_items()
            if not selected_attrs:
                QMessageBox.warning(self, "Warning", "Please select attributes to calculate")
                return

            # Fetch the source zone data
            zone_data = self.db_manager.fetch_zone_depth_data(zone_name)
            if zone_data is None or zone_data.empty:
                QMessageBox.warning(self, "Warning", f"No data found for zone: {zone_name}")
                return

            # Ensure consistent UWI type
            zone_data['UWI'] = zone_data['UWI'].astype(str)

            # Define calculation functions
            calc_func = {
                "Sum": lambda x: x.sum(),
                "Mean": lambda x: x.mean(),
                "Median": lambda x: x.median(),
                "Min": lambda x: x.min(),
                "Max": lambda x: x.max(),
                "Standard Deviation": lambda x: x.std(),
                "Variance": lambda x: x.var(),
                "Count": lambda x: x.count()
            }

            # Group by UWI and calculate all selected methods for each attribute
            results = []
            grouped = zone_data.groupby('UWI')

            for UWI, group in grouped:
                result = {'UWI': UWI}
                
                # Calculate each selected attribute using all selected methods
                for attr in selected_attrs:
                    if attr in group:
                        for method in selected_methods:
                            result[f"{attr}_{method}"] = calc_func[method](group[attr])

                results.append(result)

            if not results:
                QMessageBox.warning(self, "Warning", "No results generated. Check your data.")
                return

            # Convert results to DataFrame
            df = pd.DataFrame(results)
            print(df)

            # Add the new zone to the database
            if not self.db_manager.add_zone_names(new_zone, "Well"):
                QMessageBox.warning(self, "Warning", f"Failed to add zone '{new_zone}'")
                return

            # Create a new table with the calculated values
            if not self.db_manager.create_table_from_df(new_zone, df):
                QMessageBox.warning(self, "Warning", f"Failed to create table for zone '{new_zone}'")
                return

            # Notify the user of success
            QMessageBox.information(
                self, "Success", 
                f"Created new Well zone '{new_zone}' with {len(selected_methods)} "
                f"calculations for {len(selected_attrs)} attributes"
            )

            self.accept()

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error calculating attributes: {str(e)}")
            print(f"Error details: {str(e)}")
