from PySide6.QtWidgets import (
    QDialog, QLabel, QDoubleSpinBox, QComboBox, QVBoxLayout, 
    QHBoxLayout, QPushButton, QMessageBox, QListWidget, QWidget,
    QGroupBox
)
from PySide6.QtCore import Qt

from PySide6.QtWidgets import (
    QDialog, QLabel, QDoubleSpinBox, QComboBox, QVBoxLayout,
    QHBoxLayout, QPushButton, QMessageBox, QListWidget, QSpinBox, QDateTimeEdit, QGroupBox
)
from PySide6.QtCore import Qt, QDate




class PUDWellSelector(QDialog):
    def __init__(self, parent=None, decline_curves=[], scenarios=[], existing_wells=[], db_manager=None):
        super().__init__(parent)
        self.setWindowTitle("PUD Scenarios")
        self.setGeometry(100, 100, 600, 600)
        self.db_manager = db_manager 

        main_layout = QVBoxLayout()

        # Well Selection (Two-list selector)
        well_selector_group = QGroupBox("Well Selection")
        well_selector_layout = QHBoxLayout(well_selector_group)

        available_wells_layout = QVBoxLayout()
        self.available_label = QLabel("Available Wells:")
        self.available_wells = QListWidget()
        self.available_wells.addItems(existing_wells)
        available_wells_layout.addWidget(self.available_label)
        available_wells_layout.addWidget(self.available_wells)

        transfer_buttons_layout = QVBoxLayout()
        self.add_button = QPushButton(">")
        self.remove_button = QPushButton("<")
        self.add_all_button = QPushButton(">>")
        self.remove_all_button = QPushButton("<<")
        for btn in [self.add_button, self.remove_button, self.add_all_button, self.remove_all_button]:
            transfer_buttons_layout.addWidget(btn)
        transfer_buttons_layout.addStretch()

        selected_wells_layout = QVBoxLayout()
        self.selected_label = QLabel("Selected Wells:")
        self.selected_wells = QListWidget()
        selected_wells_layout.addWidget(self.selected_label)
        selected_wells_layout.addWidget(self.selected_wells)

        well_selector_layout.addLayout(available_wells_layout)
        well_selector_layout.addLayout(transfer_buttons_layout)
        well_selector_layout.addLayout(selected_wells_layout)

        main_layout.addWidget(well_selector_group)


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
        self.drill_time_input.setRange(1, 100)
        drill_time_layout.addWidget(self.drill_time_label)
        drill_time_layout.addWidget(self.drill_time_input)
        main_layout.addLayout(drill_time_layout)


                # Add this in the constructor (__init__)
        start_date_layout = QHBoxLayout()
        self.start_date_label = QLabel("Start Date:")
        self.start_date_input = QDateTimeEdit()
        self.start_date_input.setCalendarPopup(True)
        self.start_date_input.setDate(QDate.currentDate())  # Default to today's date
        start_date_layout.addWidget(self.start_date_label)
        start_date_layout.addWidget(self.start_date_input)
        main_layout.addLayout(start_date_layout)



        # CAPEX Inputs and Calculation
        self.create_cost_inputs(main_layout)

        # Scenario Selection
        scenario_layout = QHBoxLayout()
        self.scenario_label = QLabel("Scenario:")
        self.scenario_input = QComboBox()
        self.scenario_input.addItems(scenarios)
        self.scenario_input.setEditable(True)
        scenario_layout.addWidget(self.scenario_label)
        scenario_layout.addWidget(self.scenario_input)
        main_layout.addLayout(scenario_layout)


        decline_type_layout = QHBoxLayout()
        self.decline_type_label = QLabel("Decline Curve Type:")
        self.decline_type_input = QComboBox()
        self.decline_type_input.addItems(["UWI", "Saved DC"])
        decline_type_layout.addWidget(self.decline_type_label)
        decline_type_layout.addWidget(self.decline_type_input)
        main_layout.addLayout(decline_type_layout)


        # Initialize Decline Curve Input first
        decline_curve_layout = QHBoxLayout()
        self.decline_curve_label = QLabel("Type Curve:")
        self.decline_curve_input = QComboBox()
        self.decline_curve_input.addItems(decline_curves)
        decline_curve_layout.addWidget(self.decline_curve_label)
        decline_curve_layout.addWidget(self.decline_curve_input)
        main_layout.addLayout(decline_curve_layout)

        # Connect signals after initialization
        self.decline_type_input.currentTextChanged.connect(self.update_decline_curve_options)
        self.update_decline_curve_options(self.decline_type_input.currentText())

        # Buttons
        buttons_layout = QHBoxLayout()
        self.ok_button = QPushButton("Add Well")
        self.ok_button.clicked.connect(self.accept)
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        buttons_layout.addStretch()
        buttons_layout.addWidget(self.ok_button)
        buttons_layout.addWidget(self.cancel_button)
        main_layout.addLayout(buttons_layout)

        self.setLayout(main_layout)
        self.connect_signals()

    def create_cost_inputs(self, main_layout):
        """Helper function to create CAPEX and cost inputs."""
        cost_layout = QVBoxLayout()

        # Appx Total Depth
        total_depth_layout = QHBoxLayout()
        self.total_depth_label = QLabel("Appx Total Depth (feet):")
        self.total_depth_input = QDoubleSpinBox()
        self.total_depth_input.setRange(0.0, 50_000.0)
        self.total_depth_input.setDecimals(2)
        total_depth_layout.addWidget(self.total_depth_label)
        total_depth_layout.addWidget(self.total_depth_input)
        cost_layout.addLayout(total_depth_layout)

        self.exploration_cost_input = self.create_double_input("Exploration Cost:", cost_layout)
        self.pad_cost_input = self.create_double_input("Pad Cost:", cost_layout)
        self.cost_per_foot_input = self.create_double_input("Cost per Foot:", cost_layout)
        self.distance_to_pipe_input = self.create_double_input("Distance to Pipe (feet):", cost_layout)
        self.cost_per_foot_to_pipe_input = self.create_double_input("Cost per Foot to Pipe:", cost_layout)

        # Approx. CAPEX Cost
        capex_layout = QHBoxLayout()
        self.capex_cost_label = QLabel("Appx CAPEX Cost:")
        self.capex_cost_output = QLabel("$0.00")
        capex_layout.addWidget(self.capex_cost_label)
        capex_layout.addWidget(self.capex_cost_output)
        cost_layout.addLayout(capex_layout)

        main_layout.addLayout(cost_layout)

        # Separate OPEX input
        opex_layout = QHBoxLayout()
        self.opex_label = QLabel("Expected OPEX Cost (per well):")
        self.opex_input = QDoubleSpinBox()
        self.opex_input.setMinimum(0.0)
        self.opex_input.setMaximum(1_000_000.0)
        self.opex_input.setDecimals(2)
        opex_layout.addWidget(self.opex_label)
        opex_layout.addWidget(self.opex_input)
        main_layout.addLayout(opex_layout)

    def create_double_input(self, label_text, layout):
        """Helper function to create a labeled QDoubleSpinBox."""
        layout_row = QHBoxLayout()
        label = QLabel(label_text)
        input_field = QDoubleSpinBox()
        input_field.setRange(0.0, 1_000_000.0)
        input_field.setDecimals(2)
        layout_row.addWidget(label)
        layout_row.addWidget(input_field)
        layout.addLayout(layout_row)
        return input_field

    def connect_signals(self):
        self.add_button.clicked.connect(self.add_selected)
        self.remove_button.clicked.connect(self.remove_selected)
        self.add_all_button.clicked.connect(self.add_all)
        self.remove_all_button.clicked.connect(self.remove_all)

        self.exploration_cost_input.valueChanged.connect(self.calculate_appx_capex)
        self.pad_cost_input.valueChanged.connect(self.calculate_appx_capex)
        self.total_depth_input.valueChanged.connect(self.calculate_appx_capex)
        self.cost_per_foot_input.valueChanged.connect(self.calculate_appx_capex)
        self.distance_to_pipe_input.valueChanged.connect(self.calculate_appx_capex)
        self.cost_per_foot_to_pipe_input.valueChanged.connect(self.calculate_appx_capex)

    def calculate_appx_capex(self):
        """Update the calculation to include Appx Total Depth."""
        exploration_cost = self.exploration_cost_input.value()


        pad_cost = self.pad_cost_input.value()
        total_depth = self.total_depth_input.value()  # Updated variable name
        cost_per_foot = self.cost_per_foot_input.value()
        distance_to_pipe = self.distance_to_pipe_input.value()
        cost_per_foot_to_pipe = self.cost_per_foot_to_pipe_input.value()

        capex_cost = (
            exploration_cost + pad_cost +
            total_depth * cost_per_foot +
            distance_to_pipe * cost_per_foot_to_pipe
        )
        self.capex_cost_output.setText(f"${capex_cost:.2f}")    

    def add_selected(self):
        for item in self.available_wells.selectedItems():
            self.selected_wells.addItem(item.text())
            self.available_wells.takeItem(self.available_wells.row(item))

    def remove_selected(self):
        for item in self.selected_wells.selectedItems():
            self.available_wells.addItem(item.text())
            self.selected_wells.takeItem(self.selected_wells.row(item))

    def add_all(self):
        while self.available_wells.count() > 0:
            item = self.available_wells.takeItem(0)
            self.selected_wells.addItem(item.text())

    def remove_all(self):
        while self.selected_wells.count() > 0:
            item = self.selected_wells.takeItem(0)
            self.available_wells.addItem(item.text())

    def accept(self):
        # Validate inputs
        if self.selected_wells.count() == 0:
            QMessageBox.warning(self, "Warning", "Please select at least one well")
            return
        if not self.scenario_input.currentText():
            QMessageBox.warning(self, "Warning", "Please select a scenario")
            return
        
        # Fetch total lengths for the selected wells
        selected_well_names = self.get_selected_wells()
        all_wells_with_lengths = self.db_manager.get_total_lengths()  # Fetch all wells with total lengths
        selected_wells_data = [
            well for well in all_wells_with_lengths if well["uwi"] in selected_well_names
        ]
    
        # Create list to store data for each well
        well_data_list = []
    
        for well in selected_wells_data:
            total_length = well["total_length"]
            exploration_cost = self.exploration_cost_input.value()
            pad_cost = self.pad_cost_input.value()
            cost_per_foot = self.cost_per_foot_input.value()
            distance_to_pipe = self.distance_to_pipe_input.value()
            cost_per_foot_to_pipe = self.cost_per_foot_to_pipe_input.value()
    
            well_capex = (
                exploration_cost + pad_cost +
                total_length * cost_per_foot +
                distance_to_pipe * cost_per_foot_to_pipe
            )
    
            # Create a row for each well with all the data
            well_row = {
                "uwi": well["uwi"],
                "total_depth": total_length,
                "total_capex_cost": well_capex,
                "scenario": self.scenario_input.currentText(),
                "decline_curve": self.decline_curve_input.currentText(),
                "prod_type": self.prod_type_input.currentText(),
                "drill_time": self.drill_time_input.value(),
                "exploration_cost": exploration_cost,
                "pad_cost": pad_cost,
                "cost_per_foot": cost_per_foot,
                "distance_to_pipe": distance_to_pipe,
                "cost_per_foot_to_pipe": cost_per_foot_to_pipe,
                "opex_cost": self.opex_input.value(),
                "decline_curve_type": self.decline_type_input.currentText(),
                "start_date": self.start_date_input.date().toString("yyyy-MM-dd")
            }
            well_data_list.append(well_row)

        # Convert to DataFrame
        import pandas as pd
        self.well_data = pd.DataFrame(well_data_list)
    
        # Call the parent class's accept method to close the dialog
        super().accept()
    def get_selected_wells(self):
        """Return a list of selected well names"""
        return [self.selected_wells.item(i).text() for i in range(self.selected_wells.count())]

    def update_decline_curve_options(self, selected_type):
        self.decline_curve_input.clear()
    
        if selected_type == "UWI":
            # Get active UWIs that have model properties
            active_uwis = self.db_manager.get_active_uwis_with_properties()
            self.decline_curve_input.addItems(active_uwis)
        else:  # "Saved DC"
            # Use the original decline curves list
            decline_curve_names = self.db_manager.get_decline_curve_names()
            self.decline_curve_input.addItems(decline_curve_names)



if __name__ == "__main__":
    import sys
    import logging
    from PySide6.QtWidgets import QApplication
    
    # Set up logging
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(levelname)s - %(message)s',  # Simplified format
        handlers=[
            logging.FileHandler('pud_selector_test.log'),
            logging.StreamHandler()
        ]
    )
    logger = logging.getLogger(__name__)
    
    try:
        # Create test data with more realistic names
        test_wells = [f"100{i:02d}0000" for i in range(1, 11)]  # Creates well names like 10010000
        test_scenarios = ["Base Case", "High Price", "Low Price"]
        test_curves = ["Oil Type 1", "Gas Type 1", "Mixed Type 1"]
        
        print("Starting test application with:")
        print(f"Wells: {test_wells}")
        print(f"Scenarios: {test_scenarios}")
        print(f"Type Curves: {test_curves}")
        
        app = QApplication(sys.argv)
        dialog = PUDWellSelector(
            decline_curves=test_curves,
            scenarios=test_scenarios,
            existing_wells=test_wells

        )
        
        result = dialog.exec_()
        
        if result == QDialog.Accepted:
            print("\nResults:")
            print("-" * 50)
            print(f"Selected wells: {dialog.get_selected_wells()}")
            print(f"Scenario: {dialog.scenario_input.currentText()}")
            print(f"Type Curve: {dialog.decline_curve_input.currentText()}")
            print("-" * 50)
        else:
            print("\nDialog cancelled by user")
        
    except Exception as e:
        print(f"Error during testing: {str(e)}")
        logger.exception("Test failed")
    finally:
        sys.exit(app.exec_()) 