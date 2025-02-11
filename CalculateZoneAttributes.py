from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, 
                              QPushButton, QLabel, QMessageBox, QComboBox,
                              QListWidget, QLineEdit)
import pandas as pd
import numpy as np

class ZoneAttributeCalculator(QDialog):
    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.setWindowTitle("Zone Attribute Calculator")
        self.resize(800, 600)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # Zone selection
        zone_layout = QHBoxLayout()
        zone_layout.addWidget(QLabel("Source Zone:"))
        self.zone_combo = QComboBox()
        zone_layout.addWidget(self.zone_combo)
        layout.addLayout(zone_layout)

        # New zone name
        new_zone_layout = QHBoxLayout()
        new_zone_layout.addWidget(QLabel("New Zone Name:"))
        self.new_zone_name = QLineEdit()
        new_zone_layout.addWidget(self.new_zone_name)
        layout.addLayout(new_zone_layout)

        # Calculation method selection
        calc_layout = QHBoxLayout()
        calc_layout.addWidget(QLabel("Calculation Method:"))
        self.calc_combo = QComboBox()
        self.calc_combo.addItems([
            "Sum", "Mean", "Median", "Min", "Max", 
            "Standard Deviation", "Variance", "Count"
        ])
        calc_layout.addWidget(self.calc_combo)
        layout.addLayout(calc_layout)

        # Attribute selection lists
        lists_layout = QHBoxLayout()
        
        # Available attributes
        avail_layout = QVBoxLayout()
        avail_layout.addWidget(QLabel("Available Attributes:"))
        self.avail_list = QListWidget()
        self.avail_list.setSelectionMode(QListWidget.ExtendedSelection)
        avail_layout.addWidget(self.avail_list)
        lists_layout.addLayout(avail_layout)

        # Transfer buttons
        button_layout = QVBoxLayout()
        self.add_button = QPushButton(">>")
        self.remove_button = QPushButton("<<")
        self.add_button.clicked.connect(self.add_attributes)
        self.remove_button.clicked.connect(self.remove_attributes)
        button_layout.addStretch()
        button_layout.addWidget(self.add_button)
        button_layout.addWidget(self.remove_button)
        button_layout.addStretch()
        lists_layout.addLayout(button_layout)

        # Selected attributes
        selected_layout = QVBoxLayout()
        selected_layout.addWidget(QLabel("Selected Attributes:"))
        self.selected_list = QListWidget()
        self.selected_list.setSelectionMode(QListWidget.ExtendedSelection)
        selected_layout.addWidget(self.selected_list)
        lists_layout.addLayout(selected_layout)

        layout.addLayout(lists_layout)

        # Buttons
        button_layout = QHBoxLayout()
        self.calculate_button = QPushButton("Calculate")
        self.cancel_button = QPushButton("Cancel")
        self.calculate_button.clicked.connect(self.do_calculate)
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.calculate_button)
        button_layout.addWidget(self.cancel_button)
        layout.addLayout(button_layout)

        # Populate zones and connect signals
        self.populate_zones()
        self.zone_combo.currentTextChanged.connect(self.zone_changed)

    def populate_zones(self):
        """Load zones from the database"""
        try:
            zones = self.db_manager.fetch_zone_names_by_type("Zone")
            self.zone_combo.clear()
            self.zone_combo.addItem("Select Zone")
            for zone in zones:
                self.zone_combo.addItem(zone[0])
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error loading zones: {str(e)}")

    def zone_changed(self, zone_name):
        """When zone is selected, populate available attributes list"""
        if zone_name == "Select Zone":
            self.avail_list.clear()
            self.selected_list.clear()
            return

        try:
            # Get zone data
            zone_data = self.db_manager.fetch_zone_depth_data(zone_name)
            
            # Find numeric columns
            numeric_cols = zone_data.select_dtypes(include=[np.number]).columns
            
            # Filter out system columns
            skip_cols = {'id', 'ID', 'Top_Depth', 'Base_Depth'}
            numeric_attrs = [col for col in numeric_cols if col not in skip_cols]
            
            # Update available list
            self.avail_list.clear()
            self.selected_list.clear()
            self.avail_list.addItems(sorted(numeric_attrs))
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error loading attributes: {str(e)}")

    def add_attributes(self):
        """Move selected attributes from available to selected list"""
        items = self.avail_list.selectedItems()
        for item in items:
            self.selected_list.addItem(item.text())
            self.avail_list.takeItem(self.avail_list.row(item))

    def remove_attributes(self):
        """Move selected attributes from selected back to available list"""
        items = self.selected_list.selectedItems()
        for item in items:
            self.avail_list.addItem(item.text())
            self.selected_list.takeItem(self.selected_list.row(item))

    def do_calculate(self):
        try:
            # Validate inputs
            zone_name = self.zone_combo.currentText()
            new_zone = self.new_zone_name.text().strip()
            calc_method = self.calc_combo.currentText()
        
            if zone_name == "Select Zone":
                QMessageBox.warning(self, "Warning", "Please select a zone")
                return
            
            if not new_zone:
                QMessageBox.warning(self, "Warning", "Please enter a new zone name")
                return
            
            selected_attrs = [self.selected_list.item(i).text() 
                            for i in range(self.selected_list.count())]
            if not selected_attrs:
                QMessageBox.warning(self, "Warning", "Please select attributes to calculate")
                return

            # Get zone data
            zone_data = self.db_manager.fetch_zone_depth_data(zone_name)
            print(zone_data)
        
            # Get directional survey data from database

            directional_rows = self.db_manager.get_directional_surveys()
        
            # Convert directional survey rows to DataFrame with correct columns
            directional_data = pd.DataFrame(directional_rows, 
                columns=['id', 'UWI', 'MD', 'TVD', 'X Offset', 'Y Offset', 'Cumulative Distance'])
            
            # Make sure we're using 'UWI' consistently
            if 'UWI' in zone_data.columns:
                zone_data = zone_data.rename(columns={'UWI': 'UWI'})
            
            print(zone_data['UWI'])



            zone_data['UWI'] = zone_data['UWI'].astype(str)
            directional_data['UWI'] = directional_data['UWI'].astype(str)

        
            # Group by UWI
            grouped = zone_data.groupby('UWI')
        
            # Calculate based on selected method
            calc_func = {
                "Sum": lambda x: x.sum(),
                "Mean": lambda x: x.mean(),
                "Median": lambda x: x.median(),
                "Min": lambda x: x.min(),
                "Max": lambda x: x.max(),
                "Standard Deviation": lambda x: x.std(),
                "Variance": lambda x: x.var(),
                "Count": lambda x: x.count()
            }[calc_method]
        
            # Calculate new values with offsets from directional surveys
            results = []
            for UWI, group in grouped:
                # Get directional data for this UWI
                well_data = directional_data[directional_data['UWI'] == UWI]
                if well_data.empty:
                    print(f"No directional survey data found for UWI: {UWI}")
                    continue
                
                # Get first and last entries from directional survey
                first_entry = well_data.iloc[0]
                last_entry = well_data.iloc[-1]
            
                result = {
                    'UWI': UWI,
                    'Top_X_Offset': int(first_entry['X Offset']),
                    'Top_Y_Offset': int(first_entry['Y Offset']),
                    'Base_X_Offset': int(last_entry['X Offset']),
                    'Base_Y_Offset': int(last_entry['Y Offset'])
                }
            
                # Calculate selected attributes
                for attr in selected_attrs:
                    if attr in group:
                        result[f"{attr}_{calc_method}"] = calc_func(group[attr])
            
                results.append(result)
        
            if not results:
                QMessageBox.warning(self, "Warning", "No results generated. Check directional survey data.")
                return
            
            # Create DataFrame
            df = pd.DataFrame(results)
        
            # Add the zone and create table
            zone_added = self.db_manager.add_zone_names(new_zone, "Well")
            if not zone_added:
                QMessageBox.warning(self, "Warning", f"Zone '{new_zone}' already exists")
                return
            
            # Create table name
            table_name = f"{new_zone.replace(' ', '_').replace('-', '_').lower()}"
            if not table_name[0].isalpha():
                table_name = f"z_{table_name}"
            
            # Create the table
            table_created = self.db_manager.create_table_from_df(table_name, df)
            if not table_created:
                QMessageBox.warning(self, "Warning", f"Table '{table_name}' already exists")
                return
            
            QMessageBox.information(self, "Success", 
                f"Created new zone '{new_zone}' with {calc_method} of selected attributes")
            self.accept()
        
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error calculating attributes: {str(e)}")
            print(f"Error details: {str(e)}")  # For debugging