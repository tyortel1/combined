from PySide6.QtWidgets import (
    QDialog, QLabel, QVBoxLayout, QPushButton, QListWidget, QListWidgetItem,
    QAbstractItemView, QGroupBox, QLineEdit, QMessageBox, QTableWidget, 
    QTableWidgetItem, QHeaderView, QWidget, QHBoxLayout, QSlider, QFormLayout, QFileDialog, QSpacerItem, QSizePolicy
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

class DualListSelector(QWidget):
    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.setup_ui(title)

    def setup_ui(self, title: str):
        main_layout = QVBoxLayout(self)

        # Title label
        label = QLabel(title)
        main_layout.addWidget(label)

        # Search bar
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Search...")
        main_layout.addWidget(self.search_bar)
        self.search_bar.textChanged.connect(self._filter_available_list)

        # Horizontal layout for the lists and buttons
        list_layout = QHBoxLayout()

        # Available items list
        self.available_list = QListWidget()
        self.available_list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        list_layout.addWidget(self.available_list)

        # Transfer buttons
        button_layout = QVBoxLayout()
        self.add_button = QPushButton(">")
        self.add_all_button = QPushButton(">>")
        self.remove_button = QPushButton("<")
        self.remove_all_button = QPushButton("<<")

        button_layout.addStretch()
        button_layout.addWidget(self.add_button)
        button_layout.addWidget(self.add_all_button)
        button_layout.addWidget(self.remove_button)
        button_layout.addWidget(self.remove_all_button)
        button_layout.addStretch()

        list_layout.addLayout(button_layout)

        # Selected items list
        self.selected_list = QListWidget()
        self.selected_list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        list_layout.addWidget(self.selected_list)

        main_layout.addLayout(list_layout)

        # Store original items for filtering
        self.all_available_items = []

        # Connect signals
        self.add_button.clicked.connect(self._move_selected_to_right)
        self.add_all_button.clicked.connect(self._move_all_to_right)
        self.remove_button.clicked.connect(self._move_selected_to_left)
        self.remove_all_button.clicked.connect(self._move_all_to_left)

    def add_items(self, items):
        """Add items to the available list and store them for filtering."""
        self.all_available_items = sorted(items)  # Store full list
        self.available_list.addItems(self.all_available_items)

    def get_selected_items(self):
        """Get items from the selected list."""
        return [self.selected_list.item(i).text() for i in range(self.selected_list.count())]

    def _filter_available_list(self):
        """Filter available list based on search input."""
        filter_text = self.search_bar.text().strip().lower()
        self.available_list.clear()

        if not filter_text:
            self.available_list.addItems(self.all_available_items)
        else:
            filtered_items = [item for item in self.all_available_items if filter_text in item.lower()]
            self.available_list.addItems(filtered_items)

    def _move_items(self, source_list, target_list, items):
        """Move items between lists while preventing duplicates."""
        existing_items = {target_list.item(i).text() for i in range(target_list.count())}
        for item in items:
            text = item.text()
            if text not in existing_items:
                source_list.takeItem(source_list.row(item))
                target_list.addItem(text)

    def _move_selected_to_right(self):
        items = self.available_list.selectedItems()
        self._move_items(self.available_list, self.selected_list, items)

    def _move_all_to_right(self):
        items = [self.available_list.item(i) for i in range(self.available_list.count())]
        self._move_items(self.available_list, self.selected_list, items)

    def _move_selected_to_left(self):
        items = self.selected_list.selectedItems()
        self._move_items(self.selected_list, self.available_list, items)

    def _move_all_to_left(self):
        items = [self.selected_list.item(i) for i in range(self.selected_list.count())]
        self._move_items(self.selected_list, self.available_list, items)


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

        # Attribute Weights
        self.weights_group = QGroupBox("Attribute Weights")
        self.weights_layout = QFormLayout()
        self.weights_group.setLayout(self.weights_layout)
        layout.addWidget(self.weights_group)

        # Save Button
        self.save_button = QPushButton("Apply")
        self.save_button.clicked.connect(self.accept)
        layout.addWidget(self.save_button)

    def add_weight_sliders(self, attributes: List[str]):
        """Dynamically create sliders for each selected attribute."""
        for i in reversed(range(self.weights_layout.count())):
            self.weights_layout.itemAt(i).widget().setParent(None)

        self.weight_sliders = {}
        for attr in attributes:
            slider = QSlider(Qt.Horizontal)
            slider.setMinimum(1)
            slider.setMaximum(100)
            slider.setValue(50)  # Default weight
            self.weights_layout.addRow(f"{attr}:", slider)
            self.weight_sliders[attr] = slider

class WellComparisonDialog(QDialog):
    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.setup_ui()
        self.weight_sliders = {}
        self.iqr_multiplier = 2.0  # Default value

    def setup_ui(self):
        self.setWindowTitle("Well Comparison")
        self.setMinimumWidth(1400)
        self.setMinimumHeight(800)
        self.setWindowState(Qt.WindowMaximized)
        self.selected_attributes = []
        main_layout = QHBoxLayout(self)

        # === LEFT PANEL ===
        left_layout = QVBoxLayout()

        # Selectors
        self.planned_selector = DualListSelector("Planned Wells")
        self.active_selector = DualListSelector("Active Wells")
        self.attr_selector = DualListSelector("Attributes")

        left_layout.addWidget(self.planned_selector)
        left_layout.addWidget(self.active_selector)
        left_layout.addWidget(self.attr_selector)

        # Create left widget
        left_widget = QWidget()
        left_widget.setLayout(left_layout)


        # === RIGHT PANEL ===
        right_layout = QVBoxLayout()

        # Results table (this should take priority in resizing)
        self.results_table = QTableWidget()
        self._setup_table()
        right_layout.addWidget(self.results_table, 1)  # The '1' makes it expand properly

        # Buttons layout
        button_layout = QHBoxLayout()

        # Create buttons
        self.weights_button = QPushButton("Weights")
        self.calculate_button = QPushButton("Calculate")
        self.decline_curve_button = QPushButton("Assign Type Curve")
        self.export_button = QPushButton("Export")

        # Set fixed width to 1.5 inches (~144 pixels)
        button_width = 144
        self.weights_button.setFixedWidth(button_width)
        self.calculate_button.setFixedWidth(button_width)
        self.decline_curve_button.setFixedWidth(button_width)
        self.export_button.setFixedWidth(button_width)

        # Add a spacer to push buttons to the right
        button_layout.addStretch()  # Push buttons to the right
        button_layout.addWidget(self.weights_button)
        button_layout.addWidget(self.calculate_button)
        button_layout.addWidget(self.decline_curve_button)
        button_layout.addWidget(self.export_button)

        # Ensure button signals are connected
        self.weights_button.clicked.connect(self.open_weights_dialog)
        self.calculate_button.clicked.connect(self.run_comparison)
        self.decline_curve_button.clicked.connect(self.apply_decline_curve)
        self.export_button.clicked.connect(self.export_to_excel)


        # Wrap the button layout inside a vertical layout
        button_wrapper = QVBoxLayout()
        button_wrapper.addStretch()  # Pushes buttons to the bottom
        button_wrapper.addLayout(button_layout)

        # Add buttons BELOW the table, without shrinking the table
        right_layout.addLayout(button_wrapper, 0)  # The '0' prevents it from taking extra space

        # Create right widget
        right_widget = QWidget()
        right_widget.setLayout(right_layout)


        # Add panels to main layout
        main_layout.addWidget(left_widget, 1)
        main_layout.addWidget(right_widget, 2)

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
            planned_wells = self.db_manager.get_uwis_by_status("Planned")
            active_wells = self.db_manager.get_uwis_by_status("Active")

            # Populate lists
            self.planned_selector.add_items(planned_wells)
            self.active_selector.add_items(active_wells)
            self.attr_selector.add_items(sorted(numeric_columns))
            
        except Exception as e:
            QMessageBox.critical(self, "Data Loading Error", str(e))


    def apply_decline_curve(self):
        """Placeholder for applying a decline curve model."""
        QMessageBox.information(self, "Decline Curve", "Decline curve applied successfully!")

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
        """Opens the Weights & Sensitivity dialog."""
        dialog = WeightsDialog(self)
        selected_attributes = self.attr_selector.get_selected_items()
        
        if not selected_attributes:
            QMessageBox.warning(self, "No Attributes Selected", 
                              "Please select attributes before adjusting weights.")
            return
            
        dialog.add_weight_sliders(selected_attributes)

        if dialog.exec():
            self.iqr_multiplier = dialog.sensitivity_slider.value()
            self.weight_sliders = {
                attr: slider.value() / 100.0  # Convert to 0-1 range
                for attr, slider in dialog.weight_sliders.items()
            }

    def run_comparison(self):
        """Execute the well comparison."""
        try:
            # Get selected items
            selected_attributes = self.attr_selector.get_selected_items()
            planned_wells = self.planned_selector.get_selected_items()
            active_wells = self.active_selector.get_selected_items()

            # Debugging output
            print(f"Selected Attributes: {selected_attributes}")
            print(f"Planned Wells: {planned_wells}")
            print(f"Active Wells: {active_wells}")

            # Validate selections
            if not self._validate_selections(selected_attributes, planned_wells, active_wells):
                return
        
            # Get well data
            planned_data = self.db_manager.get_well_attributes(planned_wells, selected_attributes)
            active_data = self.db_manager.get_well_attributes(active_wells, selected_attributes)

            # Validate retrieved data
            if planned_data.empty:
                QMessageBox.warning(self, "No Data", "No data found for the selected planned wells and attributes.")
                return
        
            if active_data.empty:
                QMessageBox.warning(self, "No Data", "No data found for the selected active wells and attributes.")
                return
        
            # Debugging output
            print("Planned Well Data:")
            print(planned_data)
            print("Active Well Data:")
            print(active_data)

            # Run appropriate comparison
            if len(selected_attributes) == 1:
                results = self._single_attribute_comparison(planned_data, active_data)
            else:
                results = self._multi_attribute_comparison(planned_data, active_data)

            # Display results and pass selected_attributes
            if results:
                self._display_results(results, selected_attributes)  # Pass selected_attributes
            else:
                QMessageBox.warning(self, "Comparison Failed", "No valid comparisons could be made.")
    
        except Exception as e:
            error_message = f"Comparison Error: {str(e)}"
            print(error_message)
            QMessageBox.critical(self, "Comparison Error", error_message)



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
        """
        Replaces outlier values with NaN using vectorized operations.
        Only processes numeric columns and preserves non-numeric data.
    
        Args:
            df: Input DataFrame
        
        Returns:
            DataFrame with outliers masked as NaN
        """
        # Get numeric columns only
        numeric_cols = df.select_dtypes(include=['int64', 'float64']).columns
        if numeric_cols.empty:
            print("Warning: No numeric columns found for outlier detection")
            return df.copy()
        
        try:
            def apply_iqr_mask(col):
                try:
                    Q1 = col.quantile(0.25)
                    Q3 = col.quantile(0.75)
                    IQR = Q3 - Q1
                
                    lower_bound = Q1 - (self.iqr_multiplier * IQR)
                    upper_bound = Q3 + (self.iqr_multiplier * IQR)
                
                    masked = col.where((col >= lower_bound) & (col <= upper_bound), np.nan)
                
                    # Count and log outliers
                    outlier_count = (masked.isna() & col.notna()).sum()
                    if outlier_count > 0:
                        print(f"Column {col.name}: {outlier_count} outliers masked")
                    
                    return masked
                
                except Exception as e:
                    print(f"Error processing column {col.name}: {str(e)}")
                    return col
        
            # Create copy and only process numeric columns
            result = df.copy()
            result[numeric_cols] = result[numeric_cols].apply(apply_iqr_mask)
            return result
        
        except Exception as e:
            print(f"Error in outlier detection: {str(e)}")
            return df.copy()  # Return original if error occurs

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
        """Compare wells using multiple attributes with weights and calculate overall similarity."""
        results = []

        try:
            # Get numeric columns and filter data
            numeric_cols = planned_data.select_dtypes(include=['int64', 'float64']).columns
            if numeric_cols.empty:
                raise ValueError("No numeric columns available for comparison")

            planned_data = planned_data[numeric_cols]
            active_data = active_data[numeric_cols]

            # Mask outliers
            planned_data = self.mask_outliers(planned_data)
            active_data = self.mask_outliers(active_data)

            # Normalize using robust scaling
            normalized_planned = planned_data.copy()
            normalized_active = active_data.copy()

            for column in planned_data.columns:
                all_values = pd.concat([planned_data[column], active_data[column]])
                median_val = all_values.median()
                mad = (all_values - median_val).abs().median()

                if mad > 0:
                    normalized_planned[column] = (planned_data[column] - median_val) / mad
                    normalized_active[column] = (active_data[column] - median_val) / mad
                else:
                    normalized_planned[column] = planned_data[column] - median_val
                    normalized_active[column] = active_data[column] - median_val

            # Ensure we have weights for all attributes
            total_weight = sum(self.weight_sliders.values()) if self.weight_sliders else len(numeric_cols)
            weights = {col: self.weight_sliders.get(col, 1.0) / total_weight for col in numeric_cols}

            # Compare each planned well with all active wells
            for planned_well in normalized_planned.index:
                planned_values = normalized_planned.loc[planned_well]
                original_planned = planned_data.loc[planned_well]
                best_match = None
                best_similarity = -float('inf')
                best_details = {}

                # Compare with each active well
                for active_well in normalized_active.index:
                    active_values = normalized_active.loc[active_well]
                    original_active = active_data.loc[active_well]

                    # Calculate similarity for each attribute
                    similarities = []
                    attr_details = {}
                    valid_comparison = False

                    for attr in numeric_cols:
                        if pd.isna(planned_values[attr]) or pd.isna(active_values[attr]):
                            continue

                        try:
                            # Calculate normalized difference
                            diff = abs(planned_values[attr] - active_values[attr])

                            # Convert to similarity score (0-1)
                            attr_similarity = 1 / (1 + diff)

                            # Apply weight
                            weight = weights[attr]
                            weighted_similarity = attr_similarity * weight
                            similarities.append(weighted_similarity)

                            # Store details
                            attr_details[attr] = {
                                'planned_val': original_planned[attr],
                                'active_val': original_active[attr],
                                'weight': weight,
                                'similarity': attr_similarity,
                                'diff': diff  # Storing difference for easier access
                            }
                            valid_comparison = True

                        except Exception as e:
                            print(f"Error comparing {attr}: {str(e)}")
                            continue

                    # Calculate overall similarity if we have valid comparisons
                    if valid_comparison:
                        overall_similarity = sum(similarities) / sum(weights[attr] for attr in attr_details.keys())

                        if overall_similarity > best_similarity:
                            best_similarity = overall_similarity
                            best_match = active_well
                            best_details = attr_details

                # Format results
                if best_match and best_similarity > -float('inf'):
                    results.append({
                        'planned_well': planned_well,
                        'matched_well': best_match,
                        'similarity': best_similarity,
                        **best_details  # Store structured attributes separately
                    })
                else:
                    results.append({
                        'planned_well': planned_well,
                        'matched_well': 'No Match',
                        'similarity': -1,
                        'details': 'No valid comparison possible'
                    })

        except Exception as e:
            print(f"Error in multi-attribute comparison: {str(e)}")
            QMessageBox.warning(self, "Comparison Error", f"Error performing comparison: {str(e)}")
            return []

        return results

    





    def _display_results(self, results, selected_attributes):
        """Display comparison results in table with each attribute in its own column."""
    
        # Define base columns
        base_columns = ["Planned Well", "Matched Active Well", "Similarity Score"]
    
        # Create dynamic column headers for attributes
        columns = base_columns + selected_attributes
    
        # Set the table column count
        self.results_table.setColumnCount(len(columns))
        self.results_table.setHorizontalHeaderLabels(columns)
    
        self.results_table.setRowCount(len(results))

        for row, result in enumerate(results):
            # Debugging: Ensure the result structure is as expected
            print(f"Processing row {row}: {result}")  # Debugging line
        
            # Planned Well
            self.results_table.setItem(row, 0, QTableWidgetItem(str(result['planned_well'])))

            # Matched Well
            self.results_table.setItem(row, 1, QTableWidgetItem(str(result['matched_well'])))

            # Similarity Score
            similarity = result['similarity']
            if similarity >= 0:
                score_text = f"{similarity:.3f}"
                score_item = QTableWidgetItem(score_text)

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

            # Add each attribute in a separate column
            for col_idx, attr in enumerate(selected_attributes, start=3):
                # Debugging: Check if the attribute exists in the result
                if attr not in result:
                    print(f"Warning: Attribute '{attr}' missing in result for row {row}")  # Debugging line
                    continue

                attr_details = result[attr]
                if attr_details:  # Ensure attr_details is not None or empty
                    attr_text = (
                        f"Planned: {attr_details.get('planned_val', 'N/A'):.2f}\n"
                        f"Active: {attr_details.get('active_val', 'N/A'):.2f}\n"
                        f"Weight: {attr_details.get('weight', 'N/A'):.2f}\n"
                        f"Diff: {attr_details.get('diff', 0) * 100:.1f}%"
                    )
                
                    attr_item = QTableWidgetItem(f"{attr_details.get('diff', 0) * 100:.1f}%")
                    attr_item.setToolTip(attr_text)  # Full details in tooltip
                
                    self.results_table.setItem(row, col_idx, attr_item)
                else:
                    print(f"Warning: No details for attribute '{attr}' in row {row}")  # Debugging line

