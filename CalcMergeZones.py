from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QMessageBox, QProgressDialog)
from StyledDropdown import StyledDropdown
from StyledButton import StyledButton
import pandas as pd
from scipy.interpolate import interp1d
import numpy as np
from PySide6.QtCore import Qt, QMetaObject, QSize

class CalcMergeZoneDialog(QDialog):
    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.setWindowTitle("Merge Zones")
        self.setMinimumSize(300, 100)
        self.setup_ui()

    def setup_ui(self):
        main_layout = QVBoxLayout()
        main_layout.setSpacing(10)

        # From Zone selection using StyledDropdown
        self.from_combo = StyledDropdown(
            label_text="From Zone",
            items=["Select Zone"],
            parent=self
        )
        main_layout.addWidget(self.from_combo)

        # To Zone selection using StyledDropdown
        self.to_combo = StyledDropdown(
            label_text="To Zone",
            items=["Select Zone"],
            parent=self
        )
        main_layout.addWidget(self.to_combo)

        # Add spacing before buttons
        main_layout.addStretch()

        # Buttons Layout
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.merge_button = StyledButton(
            text="Merge",
            button_type="function",
            parent=self
        )
        self.merge_button.clicked.connect(self.do_merge)
        
        self.cancel_button = StyledButton(
            text="Close",
            button_type="close",
            parent=self
        )
        self.cancel_button.clicked.connect(self.reject)

        button_layout.addWidget(self.merge_button)
        button_layout.addWidget(self.cancel_button)

        main_layout.addLayout(button_layout)
        self.setLayout(main_layout)

        self.populate_zone_lists()

    def populate_zone_lists(self):
        """Load zones from the database into both dropdowns"""
        try:
            zones = self.db_manager.fetch_zone_names_by_type("Zone")
            zone_names = ["Select Zone"]
            zone_names.extend([zone[0] for zone in zones])
            
            self.from_combo.setItems(zone_names)
            self.to_combo.setItems(zone_names)
            
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

            # Create progress dialog
            progress = QProgressDialog("Merging zones...", "Cancel", 0, 100, self)
            progress.setWindowModality(Qt.WindowModal)
            progress.setMinimumDuration(0)  # Show immediately
            progress.setValue(0)
        
            # Update progress - 10%
            progress.setValue(10)
            progress.setLabelText("Loading zone data...")

            # Fetch data for both zones
            from_zone_data = self.db_manager.fetch_zone_depth_data(from_zone)
            to_zone_data = self.db_manager.fetch_zone_depth_data(to_zone)
        
            if from_zone_data.empty or to_zone_data.empty:
                progress.close()
                QMessageBox.warning(self, "Warning", "One or both zones have no data to merge")
                return

            # Update progress - 20%
            progress.setValue(20)
            progress.setLabelText("Processing UWIs...")

            # Store original dtypes and ensure UWI is string
            original_dtypes = to_zone_data.dtypes
            from_zone_data['UWI'] = from_zone_data['UWI'].astype(str)
            to_zone_data['UWI'] = to_zone_data['UWI'].astype(str)

            # Find common UWIs and new UWIs
            common_UWIs = set(from_zone_data['UWI']) & set(to_zone_data['UWI'])
            new_UWIs = set(from_zone_data['UWI']) - set(to_zone_data['UWI'])
        
            print(f"Common UWIs: {len(common_UWIs)}, New UWIs: {len(new_UWIs)}")

            # Update progress - 30%
            progress.setValue(30)
            progress.setLabelText("Finding new attributes...")

            # Find new attributes to add
            existing_cols = set(to_zone_data.columns)
            new_attrs = [
                col for col in from_zone_data.columns 
                if col not in existing_cols and col not in ['id', 'ID', 'UWI', 'Top_Depth', 'Base_Depth']
            ]

            if not new_attrs and not new_UWIs:
                progress.close()
                QMessageBox.warning(self, "Warning", "No new attributes or UWIs to merge")
                return

            # Process data in chunks
            chunk_size = 1000
            merged_data = []
            all_uwis = list(common_UWIs | new_UWIs)
            total_uwis = len(all_uwis)
        
            # Calculate progress step for each chunk
            progress_per_chunk = 50 / max(1, (total_uwis // chunk_size + 1))
            current_progress = 30

            for i in range(0, total_uwis, chunk_size):
                if progress.wasCanceled():
                    return

                chunk_uwis = all_uwis[i:i + chunk_size]
                progress.setLabelText(f"Processing UWIs {i+1} to {min(i+chunk_size, total_uwis)} of {total_uwis}...")
                chunk_data = []
            
                for UWI in chunk_uwis:
                    from_UWI_data = from_zone_data[from_zone_data['UWI'] == UWI]
                
                    if UWI in common_UWIs:
                        to_UWI_data = to_zone_data[to_zone_data['UWI'] == UWI]
                        merged_UWI_data = self.add_new_attributes(from_UWI_data, to_UWI_data, new_attrs)
                    else:
                        merged_UWI_data = from_UWI_data.copy()
                        for col in to_zone_data.columns:
                            if col not in merged_UWI_data.columns:
                                merged_UWI_data[col] = np.nan
                
                    chunk_data.append(merged_UWI_data)
            
                if chunk_data:
                    merged_data.append(pd.concat(chunk_data, ignore_index=True))
            
                # Update progress
                current_progress += progress_per_chunk
                progress.setValue(int(current_progress))

            if not merged_data:
                progress.close()
                QMessageBox.warning(self, "Warning", "No data available to update")
                return

            progress.setValue(80)
            progress.setLabelText("Finalizing merged data...")

            final_merged_data = pd.concat(merged_data, ignore_index=True)

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

            progress.setValue(90)
            progress.setLabelText("Saving merged data...")

            # Get the table name for the To Zone
            to_zone_table = self.db_manager.get_table_name_from_zone(to_zone)
            if not to_zone_table:
                progress.close()
                QMessageBox.critical(self, "Error", f"No table found for zone {to_zone}")
                return

            # Fill NaN values to avoid SQL errors
            final_merged_data = final_merged_data.fillna(0)

            # Save the updated To Zone
            success = self.db_manager.update_zone_data(to_zone_table, final_merged_data)

            progress.setValue(100)
            progress.close()

            if success:
                QMessageBox.information(
                    self, "Success", 
                    f"Successfully added {len(new_attrs)} new attributes and {len(new_UWIs)} new UWIs from {from_zone} to {to_zone}"
                )
                self.accept()
            else:
                QMessageBox.critical(self, "Error", "Failed to update zone data")

        except Exception as e:
            if 'progress' in locals():
                progress.close()
            print(f"Error in do_merge: {str(e)}")
            QMessageBox.critical(self, "Error", f"Error during merge: {str(e)}")
    def add_new_attributes(self, from_UWI_data, to_UWI_data, new_attrs):
        """Vectorized version of attribute addition"""
        result = to_UWI_data.copy()
        
        # Create a mask for overlapping intervals
        def find_overlaps(row):
            overlaps = (
                (from_UWI_data['Top_Depth'] <= row['Base_Depth'] + 0.001) & 
                (from_UWI_data['Base_Depth'] >= row['Top_Depth'] - 0.001)
            )
            return overlaps
        
        # Calculate overlaps for each target row
        for idx, target_row in result.iterrows():
            overlap_mask = find_overlaps(target_row)
            matching_source = from_UWI_data[overlap_mask]
            
            if not matching_source.empty:
                # Calculate means for all new attributes at once
                means = matching_source[new_attrs].mean()
                result.loc[idx, new_attrs] = means
            else:
                result.loc[idx, new_attrs] = np.nan
        
        return result