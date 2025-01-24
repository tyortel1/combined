import math
from datetime import datetime, timedelta
from shapely.geometry import LineString, Point

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, 
    QDoubleSpinBox, QTableWidget, QTableWidgetItem, 
    QMessageBox, QPushButton
)
from PySide6.QtCore import Qt

class PCDialog(QDialog):
    def __init__(self, db_manager, parent=None):
       super().__init__(parent)
       self.setWindowTitle("Parent-Child Well Analysis")
       self.setModal(True)
       self.db_manager = db_manager
       self.results = []
       self.resize(900, 600)
   
       # Create spinboxes
       self.scenario_combo = QComboBox()
       scenarios = self._get_available_scenarios()
       self.scenario_combo.addItems([str(s) for s in scenarios])
   
       self.distance_spinbox = QDoubleSpinBox()
       self.angle_spinbox = QDoubleSpinBox()
       self.month_spinbox = QDoubleSpinBox()
       self.tvd_spinbox = QDoubleSpinBox()
   
       # Main layout
       layout = QVBoxLayout(self)
   
       # Input layout
       input_layout = QVBoxLayout()
       inputs = [
           ("Scenario:", self.scenario_combo),
           ("Lateral Distance (m):", self.distance_spinbox, (0, 1000), 250, 50),
           ("Maximum Angle (degrees):", self.angle_spinbox, (0, 90), 20, 5),
           ("Minimum Time Difference (Months):", self.month_spinbox, (1, 24), 6, 1),
           ("Maximum TVD Difference (m):", self.tvd_spinbox, (0, 1000), 500, 50)
       ]
   
       for input_data in inputs:
           row = QHBoxLayout()
           label = QLabel(input_data[0])
           label.setFixedWidth(200)
           row.addWidget(label)
       
           spinbox = input_data[1]
           if isinstance(spinbox, QDoubleSpinBox):
               spinbox.setRange(*input_data[2])
               spinbox.setValue(input_data[3])
               spinbox.setSingleStep(input_data[4])
       
           spinbox.setFixedWidth(150)
           row.addWidget(spinbox)
           row.addStretch()
           input_layout.addLayout(row)
   
       layout.addLayout(input_layout)
   
       # Results table
       self.results_table = QTableWidget()
       self.results_table.setColumnCount(8)
       self.results_table.setHorizontalHeaderLabels([
           "Target UWI", "Target Date", 
           "Parent UWI", "Parent Date", 
           "Lateral Dist", "Angle ",
           "Target TVD", "Parent TVD"
       ])
       layout.addWidget(self.results_table)
   
       # Button layout - bottom right
       button_layout = QHBoxLayout()
       button_layout.addStretch()
   
       for btn_text, connection in [
           ("Calculate", self._run_analysis),
           ("Save", self.accept),
           ("Cancel", self.reject)
       ]:
           btn = QPushButton(btn_text)
           btn.setFixedWidth(150)
           btn.clicked.connect(connection)
           button_layout.addWidget(btn)
   
       layout.addLayout(button_layout)
       self.setLayout(layout)

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
            wells = self.db_manager.get_uwis_with_heel_toe()
            tvd_data = self.db_manager.get_uwis_with_average_tvd()
            
            if not model_data or not wells:
                QMessageBox.warning(self, "No Data", "No model or well data found.")
                return

            # Parameters
            max_lateral_distance = self.distance_spinbox.value()
            max_angle = self.angle_spinbox.value()
            min_months = self.month_spinbox.value()
            max_tvd_diff = self.tvd_spinbox.value()

            # Map wells and TVD data for quick lookup
            well_map = {well['uwi']: well for well in wells}
            tvd_map = {well['uwi']: well['average_tvd'] for well in tvd_data}

            self.results = []

            for target_well in model_data:
                target_uwi = target_well['uwi']
                
                # Skip if no TVD data
                if target_uwi not in tvd_map:
                    continue

                target_tvd = tvd_map[target_uwi]
                
                # Rest of the existing checks...
                target_date_str = max(
                    target_well.get('max_gas_production_date', ''),
                    target_well.get('max_oil_production_date', '')
                )
                if not target_date_str:
                    continue

                target_date = datetime.strptime(target_date_str, "%Y-%m-%d")

                if target_uwi not in well_map:
                    continue

                target_well_geometry = well_map[target_uwi]
                target_line = LineString([
                    (target_well_geometry['heel_x'], target_well_geometry['heel_y']),
                    (target_well_geometry['toe_x'], target_well_geometry['toe_y'])
                ])

                target_vector = self._calculate_well_vector(
                    target_well_geometry['heel_x'], target_well_geometry['heel_y'],
                    target_well_geometry['toe_x'], target_well_geometry['toe_y']
                )

                for parent_well in model_data:
                    if parent_well['uwi'] == target_uwi:
                        continue
                        
                    # Skip if no TVD data
                    if parent_well['uwi'] not in tvd_map:
                        continue

                    parent_tvd = tvd_map[parent_well['uwi']]
                    
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

                    if parent_well['uwi'] not in well_map:
                        continue

                    parent_well_geometry = well_map[parent_well['uwi']]
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
                            'target_uwi': target_uwi,
                            'target_date': target_date_str,
                            'parent_uwi': parent_well['uwi'],
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
            self.results_table.setItem(row, 0, QTableWidgetItem(str(result['target_uwi'])))
            self.results_table.setItem(row, 1, QTableWidgetItem(result['target_date']))
            self.results_table.setItem(row, 2, QTableWidgetItem(str(result['parent_uwi'])))
            self.results_table.setItem(row, 3, QTableWidgetItem(result['parent_date']))
            self.results_table.setItem(row, 4, QTableWidgetItem(str(result['lateral_distance'])))
            self.results_table.setItem(row, 5, QTableWidgetItem(str(result['angle'])))
            self.results_table.setItem(row, 6, QTableWidgetItem(str(result['target_tvd'])))
            self.results_table.setItem(row, 7, QTableWidgetItem(str(result['parent_tvd'])))

    def accept(self):
        print("Results at accept:", self.results)  # Debug print
        super().accept()