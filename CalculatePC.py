from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, 
    QDoubleSpinBox, QDialogButtonBox, QTableWidget, QTableWidgetItem, QMessageBox
)
from PySide6.QtCore import Qt
from shapely.geometry import LineString, Point
from datetime import datetime, timedelta

class PCDialog(QDialog):
    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Parent-Child Well Analysis")
        self.setModal(True)
        self.db_manager = db_manager

        # Main layout
        layout = QVBoxLayout(self)

        # Scenario selection
        scenario_layout = QHBoxLayout()
        scenario_label = QLabel("Scenario:")
        self.scenario_combo = QComboBox()
        
        # Populate scenarios from database
        scenarios = self.get_available_scenarios()
        self.scenario_combo.addItems([str(scenario) for scenario in scenarios])

        scenario_layout.addWidget(scenario_label)
        scenario_layout.addWidget(self.scenario_combo)
        layout.addLayout(scenario_layout)

        # Distance input
        distance_layout = QHBoxLayout()
        distance_label = QLabel("Maximum Distance (m):")
        self.distance_spinbox = QDoubleSpinBox()
        self.distance_spinbox.setRange(0, 10000)  # Adjust range as needed
        self.distance_spinbox.setSuffix(" m")
        self.distance_spinbox.setValue(500)  # Default value
        self.distance_spinbox.setSingleStep(100)

        distance_layout.addWidget(distance_label)
        distance_layout.addWidget(self.distance_spinbox)
        layout.addLayout(distance_layout)

        # Month input
        month_layout = QHBoxLayout()
        month_label = QLabel("Time Window (Months):")
        self.month_spinbox = QDoubleSpinBox()
        self.month_spinbox.setRange(1, 24)  # Allow up to 2 years
        self.month_spinbox.setValue(6)  # Default is 6 months
        self.month_spinbox.setSingleStep(1)

        month_layout.addWidget(month_label)
        month_layout.addWidget(self.month_spinbox)
        layout.addLayout(month_layout)

        # Results table
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(4)
        self.results_table.setHorizontalHeaderLabels(["Target UWI", "Target Max Date", "Intersecting UWI", "Intersecting Max Date"])
        layout.addWidget(self.results_table)

        # Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.run_analysis)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        self.setLayout(layout)

    def get_available_scenarios(self):
        """
        Retrieve available scenarios from the database
        """
        try:
            scenarios = self.db_manager.get_scenario_names()
            return scenarios if scenarios else [1]  # Default to 1 if no scenarios found
        except Exception as e:
            print(f"Error retrieving scenarios: {e}")
            return [1]  # Default scenario

    def get_scenario(self):
        """
        Return the selected scenario
        """
        scenario_name = self.scenario_combo.currentText()
        self.scenario_id = self.db_manager.get_scenario_id(scenario_name)
        return scenario_name

    def get_distance(self):
        """
        Return the selected maximum distance from the distance spinbox
        """
        return self.distance_spinbox.value()

    def get_months(self):
        """
        Return the selected time window in months
        """
        return self.month_spinbox.value()

    def calculate_well_counts(self):
        """
        Calculate how many wells meet the criteria for each UWI,
        considering both spatial and temporal filters.
        """
        try:
            # Retrieve model data for the selected scenario
            self.get_scenario()
            model_data = self.db_manager.retrieve_model_data_by_scenario(self.scenario_id)
            if not model_data:
                print(f"No model data found for scenario {self.scenario_id}.")
                return []

            # Retrieve well data with heel and toe coordinates
            wells = self.db_manager.get_uwis_with_heel_toe()
            if not wells:
                print("No well data available.")
                return []

            # Map well data by UWI for quick lookup
            well_map = {item["uwi"]: item for item in wells}
            results = []

            max_distance = self.get_distance()
            time_window = self.get_months()

            for target in model_data:
                target_uwi = target["uwi"]
                target_date = max(
                    target.get("max_gas_production_date"),
                    target.get("max_oil_production_date"),
                )
                if not target_date:
                    print(f"Skipping UWI {target_uwi} due to missing production dates.")
                    continue

                target_date = datetime.strptime(target_date, "%Y-%m-%d")

                # Check if target well exists in well_map
                if target_uwi not in well_map:
                    print(f"Skipping UWI {target_uwi} as it is not in the well data.")
                    continue

                target_well = well_map[target_uwi]
                target_line = LineString([
                    (target_well["heel_x"], target_well["heel_y"]),
                    (target_well["toe_x"], target_well["toe_y"]),
                ])

                for other in model_data:
                    other_uwi = other["uwi"]
                    if other_uwi == target_uwi:
                        continue

                    other_date = max(
                        other.get("max_gas_production_date"),
                        other.get("max_oil_production_date"),
                    )
                    if not other_date:
                        continue

                    other_date = datetime.strptime(other_date, "%Y-%m-%d")
                    if not (target_date - timedelta(days=int(time_window * 30)) <= other_date <= target_date - timedelta(days=1)):
                        continue

                    # Check if other well exists in well_map
                    if other_uwi not in well_map:
                        continue

                    other_well = well_map[other_uwi]
                    other_point = Point(other_well["heel_x"], other_well["heel_y"])
                    distance = target_line.distance(other_point)
                    if distance <= max_distance:
                        results.append({
                            "target_uwi": target_uwi,
                            "target_date": target_date.strftime('%Y-%m-%d'),
                            "intersecting_uwi": other_uwi,
                            "intersecting_date": other_date.strftime('%Y-%m-%d')
                        })

            return results
        except Exception as e:
            print(f"Error calculating well counts: {e}")
            return []

    def display_well_counts(self, results):
        """
        Display well counts meeting the criteria in the table.
        """
        self.results_table.setRowCount(len(results))
        for row, entry in enumerate(results):
            self.results_table.setItem(row, 0, QTableWidgetItem(entry["target_uwi"]))
            self.results_table.setItem(row, 1, QTableWidgetItem(entry["target_date"]))
            self.results_table.setItem(row, 2, QTableWidgetItem(entry["intersecting_uwi"]))
            self.results_table.setItem(row, 3, QTableWidgetItem(entry["intersecting_date"]))

    def run_analysis(self):
        """
        Run the analysis and display results.
        """
        try:
            results = self.calculate_well_counts()
            self.display_well_counts(results)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"An error occurred: {e}")
