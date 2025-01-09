from PySide6.QtWidgets import QDialog, QLabel, QLineEdit, QSpinBox, QDateTimeEdit, QDoubleSpinBox, QComboBox, QVBoxLayout, QHBoxLayout, QPushButton, QMessageBox
from PySide6.QtCore import QDate

class AddWell(QDialog):
    def __init__(self, parent=None, decline_curves=[], scenarios=[]):
        super().__init__(parent)
        self.setWindowTitle("Add Well")
        self.setGeometry(100, 100, 400, 400)
        
        main_layout = QVBoxLayout()

        # UWI
        uwi_layout = QHBoxLayout()
        self.uwi_label = QLabel("UWI:")
        self.uwi_input = QLineEdit()
        uwi_layout.addWidget(self.uwi_label)
        uwi_layout.addWidget(self.uwi_input)
        main_layout.addLayout(uwi_layout)

        # Number of Wells
        num_wells_layout = QHBoxLayout()
        self.num_wells_label = QLabel("Number of Wells:")
        self.num_wells_input = QSpinBox()
        self.num_wells_input.setMinimum(1)
        self.num_wells_input.setMaximum(10000)  # Set a higher maximum value if needed
        num_wells_layout.addWidget(self.num_wells_label)
        num_wells_layout.addWidget(self.num_wells_input)
        main_layout.addLayout(num_wells_layout)

        # Production Type
        prod_type_layout = QHBoxLayout()
        self.prod_type_label = QLabel("Prod. Type:")
        self.prod_type_input = QComboBox()
        self.prod_type_input.addItems(["Both", "Oil", "Gas"])
        prod_type_layout.addWidget(self.prod_type_label)
        prod_type_layout.addWidget(self.prod_type_input)
        main_layout.addLayout(prod_type_layout)

        # Drill Time
        drill_time_layout = QHBoxLayout()
        self.drill_time_label = QLabel("Drill Time (months):")
        self.drill_time_input = QSpinBox()
        self.drill_time_input.setMinimum(1)
        self.drill_time_input.setMaximum(100)  # Set a higher maximum value if needed
        drill_time_layout.addWidget(self.drill_time_label)
        drill_time_layout.addWidget(self.drill_time_input)
        main_layout.addLayout(drill_time_layout)

        # CAPEX Calculation
        self.capex_label = QLabel("CAPEX Calculation")
        main_layout.addWidget(self.capex_label)

        exploration_cost_layout = QHBoxLayout()
        self.exploration_cost_label = QLabel("Exploration Cost:")
        self.exploration_cost_input = QDoubleSpinBox()
        self.exploration_cost_input.setMinimum(0.0)
        self.exploration_cost_input.setMaximum(1000000.0)  # Set a higher maximum value if needed
        self.exploration_cost_input.setDecimals(2)
        exploration_cost_layout.addWidget(self.exploration_cost_label)
        exploration_cost_layout.addWidget(self.exploration_cost_input)
        main_layout.addLayout(exploration_cost_layout)

        pad_cost_layout = QHBoxLayout()
        self.pad_cost_label = QLabel("Pad Cost:")
        self.pad_cost_input = QDoubleSpinBox()
        self.pad_cost_input.setMinimum(0.0)
        self.pad_cost_input.setMaximum(10000000.0)  # Set a higher maximum value if needed
        self.pad_cost_input.setDecimals(2)
        pad_cost_layout.addWidget(self.pad_cost_label)
        pad_cost_layout.addWidget(self.pad_cost_input)
        main_layout.addLayout(pad_cost_layout)

        total_lateral_layout = QHBoxLayout()
        self.total_lateral_label = QLabel("Total Lateral (feet):")
        self.total_lateral_input = QDoubleSpinBox()
        self.total_lateral_input.setMinimum(0.0)
        self.total_lateral_input.setMaximum(1000000.0)  # Set a higher maximum value if needed
        self.total_lateral_input.setDecimals(2)
        total_lateral_layout.addWidget(self.total_lateral_label)
        total_lateral_layout.addWidget(self.total_lateral_input)
        main_layout.addLayout(total_lateral_layout)

        cost_per_foot_layout = QHBoxLayout()
        self.cost_per_foot_label = QLabel("Cost per Foot:")
        self.cost_per_foot_input = QDoubleSpinBox()
        self.cost_per_foot_input.setMinimum(0.0)
        self.cost_per_foot_input.setMaximum(100000.0)  # Set a higher maximum value if needed
        self.cost_per_foot_input.setDecimals(2)
        cost_per_foot_layout.addWidget(self.cost_per_foot_label)
        cost_per_foot_layout.addWidget(self.cost_per_foot_input)
        main_layout.addLayout(cost_per_foot_layout)

        distance_to_pipe_layout = QHBoxLayout()
        self.distance_to_pipe_label = QLabel("Distance to Pipe (feet):")
        self.distance_to_pipe_input = QDoubleSpinBox()
        self.distance_to_pipe_input.setMinimum(0.0)
        self.distance_to_pipe_input.setMaximum(1000000.0)  # Set a higher maximum value
        self.distance_to_pipe_input.setDecimals(2)
        distance_to_pipe_layout.addWidget(self.distance_to_pipe_label)
        distance_to_pipe_layout.addWidget(self.distance_to_pipe_input)
        main_layout.addLayout(distance_to_pipe_layout)

        cost_per_foot_to_pipe_layout = QHBoxLayout()
        self.cost_per_foot_to_pipe_label = QLabel("Cost per Foot to Pipe:")
        self.cost_per_foot_to_pipe_input = QDoubleSpinBox()
        self.cost_per_foot_to_pipe_input.setMinimum(0.0)
        self.cost_per_foot_to_pipe_input.setMaximum(10000.0)  # Set a higher maximum value if needed
        self.cost_per_foot_to_pipe_input.setDecimals(2)
        cost_per_foot_to_pipe_layout.addWidget(self.cost_per_foot_to_pipe_label)
        cost_per_foot_to_pipe_layout.addWidget(self.cost_per_foot_to_pipe_input)
        main_layout.addLayout(cost_per_foot_to_pipe_layout)

        capex_cost_layout = QHBoxLayout()
        self.capex_cost_label = QLabel("Total CAPEX Cost:")
        self.capex_cost_output = QLabel()
        capex_cost_layout.addWidget(self.capex_cost_label)
        capex_cost_layout.addWidget(self.capex_cost_output)
        main_layout.addLayout(capex_cost_layout)

        self.exploration_cost_input.valueChanged.connect(self.calculate_capex)
        self.pad_cost_input.valueChanged.connect(self.calculate_capex)
        self.total_lateral_input.valueChanged.connect(self.calculate_capex)
        self.cost_per_foot_input.valueChanged.connect(self.calculate_capex)
        self.distance_to_pipe_input.valueChanged.connect(self.calculate_capex)
        self.cost_per_foot_to_pipe_input.valueChanged.connect(self.calculate_capex)

        # OPEX Calculation
        opex_layout = QHBoxLayout()
        self.opex_label = QLabel("Expected OPEX Cost (per well):")
        self.opex_input = QDoubleSpinBox()
        self.opex_input.setMinimum(0.0)
        self.opex_input.setMaximum(1000000.0)  # Set a higher maximum value if needed
        self.opex_input.setDecimals(2)
        opex_layout.addWidget(self.opex_label)
        opex_layout.addWidget(self.opex_input)
        main_layout.addLayout(opex_layout)

        # Scenario Selection
        scenario_layout = QHBoxLayout()
        self.scenario_label = QLabel("Scenario:")
        self.scenario_input = QComboBox()
        self.scenario_input.addItems(scenarios)
        #self.scenario_input.currentIndexChanged.connect()
        self.scenario_input.setEditable(True) 
        scenario_layout.addWidget(self.scenario_label)
        scenario_layout.addWidget(self.scenario_input)
        main_layout.addLayout(scenario_layout)

        # Start Date
        start_date_layout = QHBoxLayout()
        self.start_date_label = QLabel("Start Date:")
        self.start_date_input = QDateTimeEdit()
        self.start_date_input.setCalendarPopup(True)
        self.start_date_input.setDisplayFormat("yyyy-MM-dd")
        self.start_date_input.setDate(QDate.currentDate())
        start_date_layout.addWidget(self.start_date_label)
        start_date_layout.addWidget(self.start_date_input)
        main_layout.addLayout(start_date_layout)

        
        # Decline Curve
        decline_curve_layout = QHBoxLayout()
        self.decline_curve_label = QLabel("Type Curve:")
        self.decline_curve_input = QComboBox()
        self.decline_curve_input.addItems(decline_curves)
        decline_curve_layout.addWidget(self.decline_curve_label)
        decline_curve_layout.addWidget(self.decline_curve_input)
        main_layout.addLayout(decline_curve_layout)

        # Buttons
        buttons_layout = QHBoxLayout()
        self.add_button = QPushButton("Add Well")
        self.add_button.clicked.connect(self.accept)
        buttons_layout.addWidget(self.add_button)

        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        buttons_layout.addWidget(self.cancel_button)

        main_layout.addLayout(buttons_layout)

        self.setLayout(main_layout)


    def calculate_capex(self):
        exploration_cost = self.exploration_cost_input.value()
        pad_cost = self.pad_cost_input.value()
        total_lateral = self.total_lateral_input.value()
        cost_per_foot = self.cost_per_foot_input.value()
        distance_to_pipe = self.distance_to_pipe_input.value()
        cost_per_foot_to_pipe = self.cost_per_foot_to_pipe_input.value()

        capex_cost = (exploration_cost + pad_cost +
                      total_lateral * cost_per_foot +
                      distance_to_pipe * cost_per_foot_to_pipe)

        self.capex_cost_output.setText(f"${capex_cost:.2f}")

    def accept(self):
        base_uwi = self.uwi_input.text()
        num_wells = self.num_wells_input.value()
        total_capex_cost = self.capex_cost_output.text().replace('$', '')
        total_opex_cost = self.opex_input.value()

        if not base_uwi:
            QMessageBox.critical(self, "Error", "Base UWI cannot be empty")
            return
        if not self.is_valid_base_name(base_uwi):
            QMessageBox.critical(self, "Error", "Base UWI is not valid")
            return
        if num_wells <= 0:
            QMessageBox.critical(self, "Error", "Number of wells must be greater than zero")
            return
        if not total_capex_cost:
            QMessageBox.critical(self, "Error", "Total CAPEX cost cannot be empty")
            return
        try:
            total_capex_cost = float(total_capex_cost)
        except ValueError:
            QMessageBox.critical(self, "Error", "Total CAPEX cost must be a valid number")
            return
        if not total_opex_cost:
            QMessageBox.critical(self, "Error", "Total OPEX cost cannot be empty")
            return

        # If all checks pass, accept the dialog
        super().accept()

    def is_valid_base_name(self, base_name):
        # Add your validation logic here
        return True  # Replace with actual validation logic
