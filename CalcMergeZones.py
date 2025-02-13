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
        """Merge new attributes from the source zone into the target zone."""
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
    
            print("UWI type in from_zone_data:", from_zone_data['UWI'].dtype)
            print("UWI type in to_zone_data:", to_zone_data['UWI'].dtype)

            # Store original dtypes before any operations
            original_dtypes = to_zone_data.dtypes
    
            if from_zone_data.empty or to_zone_data.empty:
                QMessageBox.warning(self, "Warning", "One or both zones have no data to merge")
                return

            # Ensure UWI is string type in both dataframes
            from_zone_data['UWI'] = from_zone_data['UWI'].astype(str)
            to_zone_data['UWI'] = to_zone_data['UWI'].astype(str)

            print("UWI type after conversion in from_zone_data:", from_zone_data['UWI'].dtype)
            print("UWI type after conversion in to_zone_data:", to_zone_data['UWI'].dtype)

            # Find common UWIs and new UWIs
            common_UWIs = set(from_zone_data['UWI']) & set(to_zone_data['UWI'])
            new_UWIs = set(from_zone_data['UWI']) - set(to_zone_data['UWI'])
    
            print(f"Common UWIs: {len(common_UWIs)}, New UWIs: {len(new_UWIs)}")
            print("Sample common UWIs:", list(common_UWIs)[:5])
            print("Sample new UWIs:", list(new_UWIs)[:5])

            # Find new attributes to add
            existing_cols = set(to_zone_data.columns)
            new_attrs = [
                col for col in from_zone_data.columns 
                if col not in existing_cols and col not in ['id', 'ID', 'UWI', 'Top_Depth', 'Base_Depth']
            ]
    
            if not new_attrs and not new_UWIs:
                QMessageBox.warning(self, "Warning", "No new attributes or UWIs to merge")
                return

            # Process each UWI (both common and new)
            merged_data = []
            for UWI in common_UWIs | new_UWIs:
                from_UWI_data = from_zone_data[from_zone_data['UWI'] == UWI]
        
                if UWI in common_UWIs:
                    to_UWI_data = to_zone_data[to_zone_data['UWI'] == UWI]
                    merged_UWI_data = self.add_new_attributes(from_UWI_data, to_UWI_data, new_attrs)
                else:
                    # For new UWIs, add all data from the source zone
                    merged_UWI_data = from_UWI_data.copy()
                    # Add any missing columns from the target zone
                    for col in to_zone_data.columns:
                        if col not in merged_UWI_data.columns:
                            merged_UWI_data[col] = np.nan

                merged_data.append(merged_UWI_data)

            # Combine all merged UWI data
            final_merged_data = pd.concat(merged_data, ignore_index=True)

            print("UWI type after merging:", final_merged_data['UWI'].dtype)
            print("Sample UWIs after merging:", final_merged_data['UWI'].head().tolist())

            # Ensure merged data is valid
            if final_merged_data.empty:
                QMessageBox.warning(self, "Warning", "No data available to update")
                return

            # Convert columns back to original types
            for col in final_merged_data.columns:
                if col in original_dtypes:
                    if col == 'UWI':
                        final_merged_data[col] = final_merged_data[col].astype(str)
                    else:
                        try:
                            final_merged_data[col] = final_merged_data[col].astype(original_dtypes[col])
                        except ValueError:
                            print(f"Warning: Could not convert column '{col}' to {original_dtypes[col]}. Keeping as is.")

            print("Final UWI type:", final_merged_data['UWI'].dtype)
            print("Final sample UWIs:", final_merged_data['UWI'].head().tolist())

            # Get the table name for the To Zone
            to_zone_table = self.db_manager.get_table_name_from_zone(to_zone)
            if not to_zone_table:
                QMessageBox.critical(self, "Error", f"No table found for zone {to_zone}")
                return

            # Fill NaN values to avoid SQL errors
            final_merged_data = final_merged_data.fillna(0)

            # Save the updated To Zone
            success = self.db_manager.update_zone_data(to_zone_table, final_merged_data)
    
            if success:
                QMessageBox.information(
                    self, "Success", 
                    f"Successfully added {len(new_attrs)} new attributes and {len(new_UWIs)} new UWIs from {from_zone} to {to_zone}"
                )
                self.accept()
            else:
                QMessageBox.critical(self, "Error", "Failed to update zone data")

        except Exception as e:
            print(f"Error in do_merge: {str(e)}")
            QMessageBox.critical(self, "Error", f"Error during merge: {str(e)}")

    def add_new_attributes(self, from_UWI_data, to_UWI_data, new_attrs):
        """
        For each row in target zone, find matching depths in source zone and sample values.
        """
        # Start with target zone data
        result = to_UWI_data.copy()
    

    
        # For each row in target zone
        for idx, target_row in result.iterrows():
            target_top = target_row['Top_Depth']
            target_base = target_row['Base_Depth']
        
           
        
            # Find source rows that overlap with this depth range
            matching_source = from_UWI_data[
                (from_UWI_data['Top_Depth'] <= target_base + 0.001) & 
                (from_UWI_data['Base_Depth'] >= target_top - 0.001)
            ]
        

            #if len(matching_source) > 0:
            #    print("Overlapping source depths:")
            #    print(matching_source[['Top_Depth', 'Base_Depth']].head())
        
            # For each new attribute
            for attr in new_attrs:
                if matching_source.empty:
                    result.loc[idx, attr] = np.nan
                    
                else:
                    # Take average of overlapping values
                    value = matching_source[attr].mean()
                    result.loc[idx, attr] = value
                    
    
        return result