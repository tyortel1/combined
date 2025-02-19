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

        # Main layout
        layout = QVBoxLayout(self)

        # Parameters Group
        param_group = QGroupBox("Analysis Parameters")
        param_layout = QVBoxLayout()
        param_layout.setSpacing(10)  # Add spacing between elements

        # Change to QHBoxLayout for each input row to control alignment
        input_layout = QVBoxLayout()
        input_layout.setSpacing(10)
        input_layout.setAlignment(Qt.AlignLeft)  # Align the entire layout to the left

        # Create all inputs first with consistent label widths
        input_params = [
            ("Scenario", self.create_dropdown),
            ("Lateral Distance (m)", self.create_input, "250"),
            ("Maximum Angle (degrees)", self.create_input, "20"),
            ("Minimum Time Difference (Months)", self.create_input, "600"),
            ("Maximum TVD Difference (m)", self.create_input, "500")
        ]

        # Find the longest label width
        label_width = 200  # Starting minimum width
        for label_text, *_ in input_params:
            test_label = QLabel(label_text)
            label_width = max(label_width, test_label.sizeHint().width() + 30)  # Add padding

        # Create inputs with consistent label width and left alignment
        self.inputs = {}
        for label_text, create_func, *args in input_params:
            # Create a horizontal layout for each row
            row_layout = QHBoxLayout()
            row_layout.setAlignment(Qt.AlignLeft)  # Align the row contents to the left
            
            if create_func == self.create_dropdown:
                widget = self.create_dropdown(label_text, label_width)
                self.scenario_combo = widget  # Keep reference for scenario combo
            else:
                widget = self.create_input(label_text, args[0], label_width)
                self.inputs[label_text] = widget
            
            row_layout.addWidget(widget)
            row_layout.addStretch()  # Add stretch after the widget to push everything to the left
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
        scenarios = self._get_available_scenarios()
        self.scenario_combo.setItems([str(s) for s in scenarios])

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
        """Run the parent-child well analysis"""
        try:
            # Get current parameters
            scenario_name = self.scenario_combo.currentText()
            scenario_id = self.db_manager.get_scenario_id(scenario_name)
            
            # Retrieve model and well data
            model_data = self.db_manager.retrieve_model_data_by_scenorio(scenario_id)
            wells = self.db_manager.get_UWIs_with_heel_toe()
            tvd_data = self.db_manager.get_UWIs_with_average_tvd()
            
            if not model_data or not wells:
                QMessageBox.warning(self, "No Data", "No model or well data found.")
                return

            try:
                max_lateral_distance = float(self.inputs["Lateral Distance (m)"].text())
                max_angle = float(self.inputs["Maximum Angle (degrees)"].text())
                min_months = float(self.inputs["Minimum Time Difference (Months)"].text())
                max_tvd_diff = float(self.inputs["Maximum TVD Difference (m)"].text())
            except ValueError:
                QMessageBox.warning(self, "Invalid Input", 
                                  "Please ensure all numeric inputs are valid numbers.")
                return


            # Map wells and TVD data for quick lookup
            well_map = {well['UWI']: well for well in wells}
            tvd_map = {well['UWI']: well['average_tvd'] for well in tvd_data}

            self.results = []

            for target_well in model_data:
                target_UWI = target_well['UWI']
                
                # Skip if no TVD data
                if target_UWI not in tvd_map:
                    continue

                target_tvd = tvd_map[target_UWI]
                
                # Rest of the existing checks...
                target_date_str = max(
                    target_well.get('max_gas_production_date', ''),
                    target_well.get('max_oil_production_date', '')
                )
                if not target_date_str:
                    continue

                target_date = datetime.strptime(target_date_str, "%Y-%m-%d")

                if target_UWI not in well_map:
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

                for parent_well in model_data:
                    if parent_well['UWI'] == target_UWI:
                        continue
                        
                    # Skip if no TVD data
                    if parent_well['UWI'] not in tvd_map:
                        continue

                    parent_tvd = tvd_map[parent_well['UWI']]
                    
                    # Check TVD difference
                    tvd_difference = abs(target_tvd - parent_tvd)
                    if tvd_difference > max_tvd_diff:
                        continue

                    # Rest of the existing parent well checks...
                    parent_date_str = max(
                        parent_well.get('max_gas_production_date', ''),
                        parent_well.get('max_oil_production_date', '')
                    )
                    if not parent_date_str:
                        continue

                    parent_date = datetime.strptime(parent_date_str, "%Y-%m-%d")

                    if parent_date >= target_date or (target_date - parent_date).days < (min_months * 30):
                        continue

                    if parent_well['UWI'] not in well_map:
                        continue

                    parent_well_geometry = well_map[parent_well['UWI']]
                    parent_point = Point(
                        parent_well_geometry['heel_x'], 
                        parent_well_geometry['heel_y']
                    )

                    lateral_distance = self._calculate_lateral_distance(target_line, parent_point)
                    parent_vector = self._calculate_well_vector(
                        parent_well_geometry['heel_x'], parent_well_geometry['heel_y'],
                        parent_well_geometry['toe_x'], parent_well_geometry['toe_y']
                    )

                    angle = self._calculate_vector_angle(target_vector, parent_vector)

                    if (lateral_distance <= max_lateral_distance and 
                        angle <= max_angle):
                        self.results.append({
                            'target_UWI': target_UWI,
                            'target_date': target_date_str,
                            'parent_UWI': parent_well['UWI'],
                            'parent_date': parent_date_str,
                            'lateral_distance': round(lateral_distance, 2),
                            'angle': round(angle, 2),
                            'target_tvd': round(target_tvd, 2),
                            'parent_tvd': round(parent_tvd, 2)
                        })

            self._display_results()

        except Exception as e:
            QMessageBox.critical(self, "Error", f"An error occurred: {str(e)}")

    def _display_results(self):
        """Display results in the table"""
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