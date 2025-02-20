from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget, QTableWidgetItem, 
    QMessageBox, QGroupBox
)
from PySide6.QtCore import Qt
from StyledButton import StyledButton
from StyledDropdown import StyledDropdown
from StyledDropdown import StyledInputBox
import math
from datetime import datetime
from shapely.geometry import LineString, Point

class PCDialog(QDialog):
    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Parent-Child Well Analysis")
        self.setModal(True)
        self.db_manager = db_manager
        self.results = []
        self.resize(900, 600)

        labels = ["Scenario", "Lateral Distance", "Maximum Angle (degrees)", "Minimum Time Difference (Months)", "Maximum TVD Difference (m)"]
        StyledDropdown.calculate_label_width(labels)

        def create_dropdown(label, items=None):
            dropdown = StyledDropdown(label)
            if items:
                dropdown.addItems(items)
            return dropdown

        def create_input(label, default_value=""):
            input_box = StyledInputBox(label, default_value)
            return input_box

        # Main layout
        layout = QVBoxLayout(self)

        # Parameters Group
        param_group = QGroupBox("Analysis Parameters")
        param_layout = QVBoxLayout()
        param_layout.setSpacing(10)

        # Create scenario dropdown and input boxes
        self.scenario_combo = create_dropdown("Scenario")
        self.lateral_input = create_input("Lateral Distance (m)", "250")
        self.angle_input = create_input("Maximum Angle (degrees)", "20")
        self.time_input = create_input("Minimum Time Difference (Months)", "3")
        self.tvd_input = create_input("Maximum TVD Difference (m)", "400")

        # Add widgets to layout
        input_layout = QVBoxLayout()
        input_layout.setSpacing(10)
        for widget in [self.scenario_combo, self.lateral_input, 
                      self.angle_input, self.time_input, self.tvd_input]:
            row_layout = QHBoxLayout()
            row_layout.setAlignment(Qt.AlignLeft)
            row_layout.addWidget(widget)
            row_layout.addStretch()
            input_layout.addLayout(row_layout)

        param_layout.addLayout(input_layout)
        param_group.setLayout(param_layout)
        layout.addWidget(param_group)


        # Rest of the code remains the same...
        # Results group
        results_group = QGroupBox("Analysis Results")
        results_layout = QVBoxLayout()

        # Results table
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(8)
        self.results_table.setHorizontalHeaderLabels([
            "Target UWI", "Target Date", 
            "Parent UWI", "Parent Date", 
            "Lateral Dist", "Angle",
            "Target TVD", "Parent TVD"
        ])
        self.results_table.horizontalHeader().setStretchLastSection(True)
        results_layout.addWidget(self.results_table)
    
        results_group.setLayout(results_layout)
        layout.addWidget(results_group)

        # Button layout - bottom right
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        # Create styled buttons
        self.calculate_button = StyledButton("Calculate", "function", self)
        self.save_button = StyledButton("Save", "export", self)
        self.close_button = StyledButton("Close", "close", self)

        # Connect buttons
        self.calculate_button.clicked.connect(self._run_analysis)
        self.save_button.clicked.connect(self.accept)
        self.close_button.clicked.connect(self.reject)

        # Add buttons to layout
        button_layout.addWidget(self.calculate_button)
        button_layout.addWidget(self.save_button)
        button_layout.addWidget(self.close_button)

        layout.addLayout(button_layout)
        self.setLayout(layout)

        # Initialize the scenario dropdown
        self.populate_scenario_options()

    def create_dropdown(self, label_text, label_width):
        """Helper to create a styled dropdown with consistent label width"""
        dropdown = StyledDropdown(
            label_text=label_text,
            parent=self
        )
        dropdown.label.setFixedWidth(label_width)
        return dropdown

    def create_input(self, label_text, default_value, label_width):
        """Helper to create a styled input with consistent label width"""
        input_box = StyledInputBox(
            label_text=label_text,
            default_value=default_value,
            parent=self
        )
        input_box.label.setFixedWidth(label_width)
        return input_box

    def _get_available_scenarios(self):
        """Retrieve scenario names from database"""
        try:
            return self.db_manager.get_scenario_names() or [1]
        except Exception as e:
            print(f"Error retrieving scenarios: {e}")
            return [1]



    def populate_scenario_options(self):
        self.scenario_combo.combo.clear()
        scenarios = self._get_available_scenarios()
        self.scenario_combo.combo.addItems([str(s) for s in scenarios])

    def _calculate_well_vector(self, heel_x, heel_y, toe_x, toe_y):
        """Calculate vector from heel to toe"""
        return (toe_x - heel_x, toe_y - heel_y)

    def _calculate_vector_angle(self, vec1, vec2):
        """Calculate angle between two vectors"""
        # Normalize vectors
        def normalize(v):
            magnitude = math.sqrt(v[0]**2 + v[1]**2)
            return (v[0]/magnitude, v[1]/magnitude) if magnitude != 0 else (0, 0)
        
        norm_vec1 = normalize(vec1)
        norm_vec2 = normalize(vec2)
        
        # Calculate dot product
        dot_product = norm_vec1[0] * norm_vec2[0] + norm_vec1[1] * norm_vec2[1]
        
        # Ensure dot product is within valid range
        dot_product = max(min(dot_product, 1), -1)
        
        # Calculate angle in degrees
        angle = math.acos(dot_product)
        return abs(math.degrees(angle))

    def _calculate_lateral_distance(self, target_line, other_point):
        """
        Calculate perpendicular distance from a point to a line
        
        Args:
            target_line (LineString): Well trajectory line
            other_point (Point): Point to measure distance from
        
        Returns:
            float: Perpendicular distance
        """
        # Project the point onto the line
        proj_point = target_line.interpolate(target_line.project(other_point))
        
        # Calculate distance between projected point and original point
        return proj_point.distance(other_point)

    def _run_analysis(self):
        try:
            # Get current parameters
            scenario_name = self.scenario_combo.currentText()
            scenario_id = self.db_manager.get_scenario_id(scenario_name)
        
            # Retrieve model and well data
            model_data = self.db_manager.retrieve_model_data_by_scenorio(scenario_id)
            wells = self.db_manager.get_UWIs_with_heel_toe()
            tvd_data = self.db_manager.get_UWIs_with_average_tvd()
        
            # Comprehensive logging
            print("=== DEBUG: Input Data Summary ===")
            print(f"Total Model Data Wells: {len(model_data)}")
            print(f"Total Wells with Geometry: {len(wells)}")
            print(f"Total Wells with TVD Data: {len(tvd_data)}")

            # Parse input parameters
            try:
                max_lateral_distance = float(self.lateral_input.text())
                max_angle = float(self.angle_input.text())
                min_months = float(self.time_input.text())
                max_tvd_diff = float(self.tvd_input.text())
            
                print("\n=== Analysis Parameters ===")
                print(f"Max Lateral Distance: {max_lateral_distance} m")
                print(f"Max Angle: {max_angle} degrees")
                print(f"Min Time Difference: {min_months} months")
                print(f"Max TVD Difference: {max_tvd_diff} m")
            except ValueError:
                print("ERROR: Invalid numeric input parameters")
                return

            # Map wells and TVD data for quick lookup
            well_map = {str(well['UWI']): well for well in wells}
            tvd_map = {str(well['UWI']): well['average_tvd'] for well in tvd_data}

            print("\n=== Debug: TVD Map Keys (first 20) ===")
            print(list(tvd_map.keys())[:20])

            # Detailed tracking of rejection reasons
            rejection_reasons = {
                'total_comparisons': 0,
                'same_well': 0,
                'no_target_tvd': 0,
                'no_parent_tvd': 0,
                'tvd_difference_exceeded': 0,
                'target_date_missing': 0,
                'parent_date_missing': 0,
                'date_time_constraint': 0,
                'no_target_geometry': 0,
                'no_parent_geometry': 0,
                'lateral_distance_exceeded': 0,
                'angle_exceeded': 0,
                'successful_matches': 0
            }

            print("\n=== Detailed Analysis Start ===")
            results = []

            for target_well in model_data:
                target_UWI = str(target_well['UWI'])
            
                # Skip if no TVD data for target well
                if target_UWI not in tvd_map:
                    rejection_reasons['no_target_tvd'] += 1
                    print(f"Skipping target well {target_UWI}: No TVD data")
                    continue

                target_tvd = tvd_map[target_UWI]
            
                # Get target production date
                target_date_str = max(
                    target_well.get('max_gas_production_date', ''),
                    target_well.get('max_oil_production_date', '')
                )
                if not target_date_str:
                    rejection_reasons['target_date_missing'] += 1
                    print(f"Skipping target well {target_UWI}: No production date")
                    continue

                # Parse target date
                target_date = datetime.strptime(target_date_str, "%Y-%m-%d")

                # Check target well geometry
                if target_UWI not in well_map:
                    rejection_reasons['no_target_geometry'] += 1
                    print(f"Skipping target well {target_UWI}: No geometry")
                    continue

                target_well_geometry = well_map[target_UWI]
                target_line = LineString([
                    (target_well_geometry['heel_x'], target_well_geometry['heel_y']),
                    (target_well_geometry['toe_x'], target_well_geometry['toe_y'])
                ])

                target_vector = self._calculate_well_vector(
                    target_well_geometry['heel_x'], target_well_geometry['heel_y'],
                    target_well_geometry['toe_x'], target_well_geometry['toe_y']
                )

                # Compare with every other well
                for parent_well in model_data:
                    rejection_reasons['total_comparisons'] += 1
                    parent_UWI = str(parent_well['UWI'])

                    # Skip comparing well with itself
                    if parent_UWI == target_UWI:
                        rejection_reasons['same_well'] += 1
                        continue

                    # Skip if no TVD data for parent well
                    if parent_UWI not in tvd_map:
                        rejection_reasons['no_parent_tvd'] += 1
                        print(f"Skipping parent well {parent_UWI}: No TVD data")
                        continue

                    parent_tvd = tvd_map[parent_UWI]
                
                    # Check TVD difference
                    tvd_difference = abs(target_tvd - parent_tvd)
                    if tvd_difference > max_tvd_diff:
                        rejection_reasons['tvd_difference_exceeded'] += 1
                        continue

                    # Get parent production date
                    parent_date_str = max(
                        parent_well.get('max_gas_production_date', ''),
                        parent_well.get('max_oil_production_date', '')
                    )
                    if not parent_date_str:
                        rejection_reasons['parent_date_missing'] += 1
                        print(f"Skipping parent well {parent_UWI}: No production date")
                        continue

                    parent_date = datetime.strptime(parent_date_str, "%Y-%m-%d")

                    # Check time difference
                    if parent_date >= target_date or (target_date - parent_date).days < (min_months * 30):
                        rejection_reasons['date_time_constraint'] += 1
                        continue

                    # Check parent well geometry
                    if parent_UWI not in well_map:
                        rejection_reasons['no_parent_geometry'] += 1
                        print(f"Skipping parent well {parent_UWI}: No geometry")
                        continue

                    parent_well_geometry = well_map[parent_well['UWI']]
                    parent_point = Point(
                        parent_well_geometry['heel_x'], 
                        parent_well_geometry['heel_y']
                    )

                    # Calculate lateral distance
                    lateral_distance = self._calculate_lateral_distance(target_line, parent_point)
                    if lateral_distance > max_lateral_distance:
                        rejection_reasons['lateral_distance_exceeded'] += 1
                        continue

                    # Calculate angle between well vectors
                    parent_vector = self._calculate_well_vector(
                        parent_well_geometry['heel_x'], parent_well_geometry['heel_y'],
                        parent_well_geometry['toe_x'], parent_well_geometry['toe_y']
                    )

                    angle = self._calculate_vector_angle(target_vector, parent_vector)
                    if angle > max_angle:
                        rejection_reasons['angle_exceeded'] += 1
                        continue

                    # If we've made it this far, we have a match!
                    rejection_reasons['successful_matches'] += 1
                    results.append({
                        'target_UWI': target_UWI,
                        'target_date': target_date_str,
                        'parent_UWI': parent_UWI,
                        'parent_date': parent_date_str,
                        'lateral_distance': round(lateral_distance, 2),
                        'angle': round(angle, 2),
                        'target_tvd': round(target_tvd, 2),
                        'parent_tvd': round(parent_tvd, 2)
                    })

            # Print detailed rejection reasons
            print("\n=== Rejection Reasons ===")
            for reason, count in rejection_reasons.items():
                print(f"{reason}: {count}")

            # Store and display results
            self.results = results
            self._display_results()

        except Exception as e:
            import traceback
            print("=== FULL ERROR TRACEBACK ===")
            traceback.print_exc()
            QMessageBox.critical(self, "Error", f"An error occurred: {str(e)}")
    def _display_results(self):
        """Display results in the table"""
        print("Displaying results:", len(self.results))  # Debug print
        self.results_table.setRowCount(len(self.results))
        for row, result in enumerate(self.results):
            self.results_table.setItem(row, 0, QTableWidgetItem(str(result['target_UWI'])))
            self.results_table.setItem(row, 1, QTableWidgetItem(result['target_date']))
            self.results_table.setItem(row, 2, QTableWidgetItem(str(result['parent_UWI'])))
            self.results_table.setItem(row, 3, QTableWidgetItem(result['parent_date']))
            self.results_table.setItem(row, 4, QTableWidgetItem(str(result['lateral_distance'])))
            self.results_table.setItem(row, 5, QTableWidgetItem(str(result['angle'])))
            self.results_table.setItem(row, 6, QTableWidgetItem(str(result['target_tvd'])))
            self.results_table.setItem(row, 7, QTableWidgetItem(str(result['parent_tvd'])))

    def accept(self):
        print("Results at accept:", self.results)  # Debug print
        super().accept()