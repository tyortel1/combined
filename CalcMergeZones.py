from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QComboBox, 
                              QPushButton, QLabel, QMessageBox)
import pandas as pd
from scipy.interpolate import interp1d
import numpy as np

class CalcMergeZoneDialog(QDialog):
    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.setWindowTitle("Merge Zones")
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # From Zone selection
        from_layout = QHBoxLayout()
        from_layout.addWidget(QLabel("From Zone:"))
        self.from_combo = QComboBox()
        from_layout.addWidget(self.from_combo)
        layout.addLayout(from_layout)

        # To Zone selection
        to_layout = QHBoxLayout()
        to_layout.addWidget(QLabel("To Zone:"))
        self.to_combo = QComboBox()
        to_layout.addWidget(self.to_combo)
        layout.addLayout(to_layout)

        # Buttons
        button_layout = QHBoxLayout()
        self.merge_button = QPushButton("Merge")
        self.merge_button.clicked.connect(self.do_merge)
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.merge_button)
        button_layout.addWidget(self.cancel_button)
        layout.addLayout(button_layout)

        self.populate_zone_lists()

    def populate_zone_lists(self):
        """Load zones from the database into both dropdowns"""
        try:
            zones = self.db_manager.fetch_zone_names_by_type("Zone")
            for combo in [self.from_combo, self.to_combo]:
                combo.clear()
                combo.addItem("Select Zone")
                for zone in zones:
                    combo.addItem(zone[0])
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error loading zones: {str(e)}")

    def do_merge(self):
        """Merge new attributes from the source zone into the target zone"""
        try:
            from_zone = self.from_combo.currentText()
            to_zone = self.to_combo.currentText()
            print(f"\nAttempting to merge from {from_zone} to {to_zone}")

            # Validate selections
            if from_zone == "Select Zone" or to_zone == "Select Zone":
                QMessageBox.warning(self, "Warning", "Please select both zones")
                return

            if from_zone == to_zone:
                QMessageBox.warning(self, "Warning", "Please select different zones")
                return

            # Fetch data for both zones
            from_zone_data = self.db_manager.fetch_zone_depth_data(from_zone)
            to_zone_data = self.db_manager.fetch_zone_depth_data(to_zone)
            print(f"\nFetched data:")
            print(f"From zone rows: {len(from_zone_data)}")
            print(f"From zone columns: {from_zone_data.columns.tolist()}")
            print(f"To zone rows: {len(to_zone_data)}")
            print(f"To zone columns: {to_zone_data.columns.tolist()}")

            if from_zone_data.empty or to_zone_data.empty:
                QMessageBox.warning(self, "Warning", "One or both zones have no data to merge")
                return

            # Process each UWI separately
            common_uwis = set(from_zone_data['UWI']) & set(to_zone_data['UWI'])
            print(f"\nFound {len(common_uwis)} common UWIs")
            print(f"Common UWIs: {common_uwis}")
        
            if not common_uwis:
                QMessageBox.warning(self, "Warning", "No common UWIs found between zones")
                return

            # Find new attributes to add
            existing_cols = set(to_zone_data.columns)
            new_attrs = [col for col in from_zone_data.columns 
                        if col not in existing_cols and 
                        col not in ['id', 'ID', 'UWI', 'Top_Depth', 'Base_Depth']]
            print(f"\nFound {len(new_attrs)} new attributes to add:")
            print(f"New attributes: {new_attrs}")

            if not new_attrs:
                QMessageBox.warning(self, "Warning", "No new attributes to merge")
                return

            # Process each UWI
            merged_data = []
            for uwi in common_uwis:
                print(f"\nProcessing UWI: {uwi}")
                from_uwi_data = from_zone_data[from_zone_data['UWI'] == uwi]
                to_uwi_data = to_zone_data[to_zone_data['UWI'] == uwi]
                print(f"From zone has {len(from_uwi_data)} rows for this UWI")
                print(f"To zone has {len(to_uwi_data)} rows for this UWI")
            
                merged_uwi_data = self.add_new_attributes(from_uwi_data, to_uwi_data, new_attrs)
                print(f"After merge, got {len(merged_uwi_data)} rows")
                print(f"New columns have values: {merged_uwi_data[new_attrs].notnull().any().tolist()}")
                merged_data.append(merged_uwi_data)

            # Combine all merged UWI data
            final_merged_data = pd.concat(merged_data, ignore_index=True)
            print(f"\nFinal merged data has {len(final_merged_data)} rows")
            print(f"New columns still have values: {final_merged_data[new_attrs].notnull().any().tolist()}")

            # Save the updated To Zone
            success = self.db_manager.update_zone_data(to_zone, final_merged_data)
            if success:
                QMessageBox.information(self, "Success", 
                    f"Successfully added {len(new_attrs)} new attributes from {from_zone} to {to_zone}")
                self.accept()
            else:
                QMessageBox.critical(self, "Error", "Failed to update zone data")

        except Exception as e:
            print(f"Error in do_merge: {str(e)}")
            QMessageBox.critical(self, "Error", f"Error during merge: {str(e)}")

    def add_new_attributes(self, from_uwi_data, to_uwi_data, new_attrs):
        """
        For each row in target zone, find matching depths in source zone and sample values.
        """
        # Start with target zone data
        result = to_uwi_data.copy()
    
        print(f"\nProcessing UWI: {to_uwi_data['UWI'].iloc[0]}")
        print(f"Source zone has {len(from_uwi_data)} rows")
        print(f"Target zone has {len(to_uwi_data)} rows")
        print("\nSource depth ranges:")
        print(from_uwi_data[['Top_Depth', 'Base_Depth']].head())
        print("\nTarget depth ranges:")
        print(to_uwi_data[['Top_Depth', 'Base_Depth']].head())
    
        # For each row in target zone
        for idx, target_row in result.iterrows():
            target_top = target_row['Top_Depth']
            target_base = target_row['Base_Depth']
        
            print(f"\nLooking for overlap with target depths: {target_top} - {target_base}")
        
            # Find source rows that overlap with this depth range
            matching_source = from_uwi_data[
                (from_uwi_data['Top_Depth'] <= target_base + 0.001) & 
                (from_uwi_data['Base_Depth'] >= target_top - 0.001)
            ]
        
            print(f"Found {len(matching_source)} overlapping rows")
            if len(matching_source) > 0:
                print("Overlapping source depths:")
                print(matching_source[['Top_Depth', 'Base_Depth']].head())
        
            # For each new attribute
            for attr in new_attrs:
                if matching_source.empty:
                    result.loc[idx, attr] = np.nan
                    print(f"No overlap - setting {attr} to NaN")
                else:
                    # Take average of overlapping values
                    value = matching_source[attr].mean()
                    result.loc[idx, attr] = value
                    print(f"Setting {attr} to {value} (average of {len(matching_source)} values)")
    
        return result