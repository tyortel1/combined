from PySide6.QtWidgets import (
    QDialog, QLabel, QDoubleSpinBox, QComboBox, QVBoxLayout, 
    QHBoxLayout, QPushButton, QMessageBox, QListWidget, QWidget,
    QGroupBox, QLineEdit, QSpinBox, QDateTimeEdit
)
from PySide6.QtCore import Qt, QDate
import pandas as pd
import logging

class PUDWellSelector(QDialog):
    def __init__(self, parent=None, decline_curves=[], scenarios=[], existing_wells=[], db_manager=None):
        super().__init__(parent)
        self.setWindowTitle("PUD Scenarios")
        self.setGeometry(100, 100, 1200, 800)
        self.setMinimumSize(800, 600)
        self.db_manager = db_manager
        
        # Store initial data
        self._initial_wells = list(existing_wells)
        self._decline_curves = list(decline_curves)
        self._scenarios = list(scenarios)
        
        main_layout = QHBoxLayout()
        self._setup_ui(main_layout)
        self.setLayout(main_layout)
        self._connect_signals()
        
        # Initialize calculator
        self.calculate_appx_capex()
        
    def _setup_ui(self, main_layout):
        left_panel = self._create_left_panel()
        right_panel = self._create_right_panel()
        
        main_layout.addWidget(left_panel, stretch=2)
        main_layout.addWidget(right_panel, stretch=1)

    def _create_left_panel(self):
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # Search
        search_group = QGroupBox("Search")
        search_layout = QVBoxLayout(search_group)
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search wells...")
        search_layout.addWidget(self.search_input)
        layout.addWidget(search_group)
        
        # Well Selection
        well_group = QGroupBox("Well Selection")
        well_layout = QVBoxLayout(well_group)
        lists_layout = QHBoxLayout()
        
        # Available wells
        available_layout = QVBoxLayout()
        self.available_label = QLabel("Available Wells:")
        self.available_wells = QListWidget()
        self.available_wells.addItems(self._initial_wells)
        self.available_wells.setSelectionMode(QListWidget.ExtendedSelection)
        available_layout.addWidget(self.available_label)
        available_layout.addWidget(self.available_wells)
        
        # Transfer buttons
        button_layout = QVBoxLayout()
        button_layout.addStretch()
        
        self.select_all_button = QPushButton("Select All")
        self.add_button = QPushButton(">")
        self.remove_button = QPushButton("<")
        self.move_up_button = QPushButton("↑")
        self.move_down_button = QPushButton("↓")
        self.deselect_all_button = QPushButton("Deselect All")
        
        for btn in [self.select_all_button, self.add_button, self.remove_button, 
                   self.move_up_button, self.move_down_button, self.deselect_all_button]:
            button_layout.addWidget(btn)
        button_layout.addStretch()
        
        # Selected wells
        selected_layout = QVBoxLayout()
        self.selected_label = QLabel("Selected Wells (in order):")
        self.selected_wells = QListWidget()
        self.selected_wells.setSelectionMode(QListWidget.ExtendedSelection)
        selected_layout.addWidget(self.selected_label)
        selected_layout.addWidget(self.selected_wells)
        
        lists_layout.addLayout(available_layout)
        lists_layout.addLayout(button_layout)
        lists_layout.addLayout(selected_layout)
        well_layout.addLayout(lists_layout)
        layout.addWidget(well_group)
        
        return panel

    def _create_right_panel(self):
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # Basic Parameters
        basic_group = QGroupBox("Basic Parameters")
        basic_layout = QVBoxLayout(basic_group)
        
        # Production Type
        prod_type_layout = QHBoxLayout()
        self.prod_type_label = QLabel("Prod. Type:")
        self.prod_type_input = QComboBox()
        self.prod_type_input.addItems(["Both", "Oil", "Gas"])
        prod_type_layout.addWidget(self.prod_type_label)
        prod_type_layout.addWidget(self.prod_type_input)
        basic_layout.addLayout(prod_type_layout)
        
        # Drill Time
        drill_time_layout = QHBoxLayout()
        self.drill_time_label = QLabel("Drill Time (months):")
        self.drill_time_input = QSpinBox()
        self.drill_time_input.setRange(1, 100)
        self.drill_time_input.setValue(3)  # Default: 3 months
        drill_time_layout.addWidget(self.drill_time_label)
        drill_time_layout.addWidget(self.drill_time_input)
        basic_layout.addLayout(drill_time_layout)
        
        # Start Date
        start_date_layout = QHBoxLayout()
        self.start_date_label = QLabel("Start Date:")
        self.start_date_input = QDateTimeEdit()
        self.start_date_input.setCalendarPopup(True)
        self.start_date_input.setDate(QDate.currentDate())
        start_date_layout.addWidget(self.start_date_label)
        start_date_layout.addWidget(self.start_date_input)
        basic_layout.addLayout(start_date_layout)
        
        layout.addWidget(basic_group)
        
        # Cost Parameters
        cost_group = QGroupBox("Cost Parameters")
        cost_layout = QVBoxLayout(cost_group)
        
        # Total Depth
        self.total_depth_input = self._create_double_input("Appx Total Depth (feet):", cost_layout, max_value=50_000.0)
        self.total_depth_input.setValue(2000)  # Default depth
        
        # Cost inputs with defaults
        self.cost_per_foot_input = self._create_double_input("Cost per Foot:", cost_layout)
        self.cost_per_foot_input.setValue(500)  # Default cost per foot
        
        self.exploration_cost_input = self._create_double_input("Exploration Cost:", cost_layout)
        self.exploration_cost_input.setValue(50000)  # Default exploration cost
        
        self.pad_cost_input = self._create_double_input("Pad Cost:", cost_layout)
        self.pad_cost_input.setValue(50000)  # Default pad cost
        
        self.distance_to_pipe_input = self._create_double_input("Distance to Pipe (feet):", cost_layout)
        self.distance_to_pipe_input.setValue(300)  # Default distance
        
        self.cost_per_foot_to_pipe_input = self._create_double_input("Cost per Foot to Pipe:", cost_layout)
        self.cost_per_foot_to_pipe_input.setValue(25)  # Default cost per foot to pipe
        
        # CAPEX Output
        capex_layout = QHBoxLayout()
        self.capex_cost_label = QLabel("Appx CAPEX Cost:")
        self.capex_cost_output = QLabel("$0.00")
        capex_layout.addWidget(self.capex_cost_label)
        capex_layout.addWidget(self.capex_cost_output)
        cost_layout.addLayout(capex_layout)
        
        # OPEX Input
        self.opex_input = self._create_double_input("Expected OPEX Cost (per well):", cost_layout)
        self.opex_input.setValue(8000)  # Default cost per foot to pipe
        
        layout.addWidget(cost_group)
        
        # Decline Parameters
        decline_group = QGroupBox("Decline Curve Parameters")
        decline_layout = QVBoxLayout(decline_group)
        
        # Scenario Selection
        scenario_layout = QHBoxLayout()
        self.scenario_label = QLabel("Scenario:")
        self.scenario_input = QComboBox()
        self.scenario_input.addItems(self._scenarios)
        self.scenario_input.setEditable(True)
        scenario_layout.addWidget(self.scenario_label)
        scenario_layout.addWidget(self.scenario_input)
        decline_layout.addLayout(scenario_layout)
        
        # Decline Type
        decline_type_layout = QHBoxLayout()
        self.decline_type_label = QLabel("Decline Curve Type:")
        self.decline_type_input = QComboBox()
        self.decline_type_input.addItems(["UWI", "Saved DC"])
        decline_type_layout.addWidget(self.decline_type_label)
        decline_type_layout.addWidget(self.decline_type_input)
        decline_layout.addLayout(decline_type_layout)
        
        # Type Curve
        decline_curve_layout = QHBoxLayout()
        self.decline_curve_label = QLabel("Type Curve:")
        self.decline_curve_input = QComboBox()
        
        if self.db_manager:
            initial_curves = self.db_manager.get_active_UWIs_with_properties()
            self.decline_curve_input.addItems(initial_curves)
        
        decline_curve_layout.addWidget(self.decline_curve_label)
        decline_curve_layout.addWidget(self.decline_curve_input)
        decline_layout.addLayout(decline_curve_layout)
        
        layout.addWidget(decline_group)
        
        # Bottom buttons
        buttons_layout = QHBoxLayout()
        self.ok_button = QPushButton("Add Well")
        self.cancel_button = QPushButton("Cancel")
        buttons_layout.addStretch()
        buttons_layout.addWidget(self.ok_button)
        buttons_layout.addWidget(self.cancel_button)
        layout.addLayout(buttons_layout)
        
        return panel

    def _create_double_input(self, label_text, layout, max_value=1_000_000.0, decimals=2):
        input_layout = QHBoxLayout()
        label = QLabel(label_text)
        input_field = QDoubleSpinBox()
        input_field.setRange(0.0, max_value)
        input_field.setDecimals(decimals)
        input_field.setGroupSeparatorShown(True)
        input_layout.addWidget(label)
        input_layout.addWidget(input_field)
        layout.addLayout(input_layout)
        return input_field

    def _connect_signals(self):
        self.search_input.textChanged.connect(self.filter_wells)
        self.select_all_button.clicked.connect(self.add_all)
        self.deselect_all_button.clicked.connect(self.remove_all)
        self.add_button.clicked.connect(self.add_selected)
        self.remove_button.clicked.connect(self.remove_selected)
        self.move_up_button.clicked.connect(self.move_selected_up)
        self.move_down_button.clicked.connect(self.move_selected_down)
        self.decline_type_input.currentTextChanged.connect(self.update_decline_curve_options)
        
        for input_field in [
            self.exploration_cost_input,
            self.pad_cost_input,
            self.total_depth_input,
            self.cost_per_foot_input,
            self.distance_to_pipe_input,
            self.cost_per_foot_to_pipe_input
        ]:
            input_field.valueChanged.connect(self.calculate_appx_capex)
        
        self.ok_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)

    def filter_wells(self, search_text):
        for i in range(self.available_wells.count()):
            item = self.available_wells.item(i)
            item.setHidden(search_text.lower() not in item.text().lower())

    def add_all(self):
        visible_wells = []
        for i in range(self.available_wells.count()):
            item = self.available_wells.item(i)
            if not item.isHidden():
                visible_wells.append(item.text())
        
        self.selected_wells.addItems(visible_wells)
        
        for well in visible_wells:
            items = self.available_wells.findItems(well, Qt.MatchExactly)
            for item in items:
                self.available_wells.takeItem(self.available_wells.row(item))

    def remove_all(self):
        while self.selected_wells.count() > 0:
            item = self.selected_wells.takeItem(0)
            self.available_wells.addItem(item.text())

    def move_selected_up(self):
        current_row = self.selected_wells.currentRow()
        if current_row > 0:
            item = self.selected_wells.takeItem(current_row)
            self.selected_wells.insertItem(current_row - 1, item)
            self.selected_wells.setCurrentItem(item)

    def move_selected_down(self):
        current_row = self.selected_wells.currentRow()
        if current_row < self.selected_wells.count() - 1:
            item = self.selected_wells.takeItem(current_row)
            self.selected_wells.insertItem(current_row + 1, item)
            self.selected_wells.setCurrentItem(item)

    def add_selected(self):
        for item in self.available_wells.selectedItems():
            self.selected_wells.addItem(item.text())
            self.available_wells.takeItem(self.available_wells.row(item))

    def remove_selected(self):
        for item in self.selected_wells.selectedItems():
            self.available_wells.addItem(item.text())
            self.selected_wells.takeItem(self.selected_wells.row(item))

    def calculate_appx_capex(self):
        try:
            exploration_cost = self.exploration_cost_input.value()
            pad_cost = self.pad_cost_input.value()
            total_depth = self.total_depth_input.value()
            cost_per_foot = self.cost_per_foot_input.value()
            distance_to_pipe = self.distance_to_pipe_input.value()
            cost_per_foot_to_pipe = self.cost_per_foot_to_pipe_input.value()

            capex_cost = (
                exploration_cost + pad_cost +
                total_depth * cost_per_foot +
                distance_to_pipe * cost_per_foot_to_pipe
            )
            self.capex_cost_output.setText(f"${capex_cost:,.2f}")
        except Exception as e:
            self.capex_cost_output.setText("Error in calculation")
            logging.error(f"CAPEX calculation error: {str(e)}")

    def calculate_appx_capex(self):
        """Calculate approximate CAPEX based on inputs"""
        exploration_cost = self.exploration_cost_input.value()
        pad_cost = self.pad_cost_input.value()
        total_depth = self.total_depth_input.value()
        cost_per_foot = self.cost_per_foot_input.value()
        distance_to_pipe = self.distance_to_pipe_input.value()
        cost_per_foot_to_pipe = self.cost_per_foot_to_pipe_input.value()

        capex_cost = (
            exploration_cost + pad_cost +
            total_depth * cost_per_foot +
            distance_to_pipe * cost_per_foot_to_pipe
        )
        self.capex_cost_output.setText(f"${capex_cost:,.2f}")

    def update_decline_curve_options(self, selected_type):
        """Update decline curve options based on selected type"""
        if not self.db_manager:
            raise ValueError("Database manager is required")
            
        self.decline_curve_input.clear()
    
        if selected_type == "UWI":
            active_UWIs = self.db_manager.get_active_UWIs_with_properties()
            self.decline_curve_input.addItems(active_UWIs)
        else:  # "Saved DC"
            decline_curve_names = self.db_manager.get_decline_curve_names()
            self.decline_curve_input.addItems(decline_curve_names)

    def get_selected_wells(self):
        """Return list of selected wells in order"""
        return [self.selected_wells.item(i).text() for i in range(self.selected_wells.count())]

    def accept(self):
        # Validates inputs
        if self.selected_wells.count() == 0:
            QMessageBox.warning(self, "Warning", "Please select at least one well")
            return
        if not self.scenario_input.currentText():
            QMessageBox.warning(self, "Warning", "Please select a scenario")
            return

        base_start_date = self.start_date_input.date()
        drill_time_months = self.drill_time_input.value()
        well_data_list = []
    
        # Process wells in list order
        for i in range(self.selected_wells.count()):
            well_name = self.selected_wells.item(i).text()
            well_start_date = base_start_date.addMonths(i * drill_time_months)
        
            # Get well length
            total_length = 0
            if self.db_manager:
                well_data = self.db_manager.get_total_lengths()
                matching_wells = [w for w in well_data if w["UWI"] == well_name]
                if matching_wells:
                    total_length = matching_wells[0]["total_length"]
                else:
                    total_length = self.total_depth_input.value()
            else:
                total_length = self.total_depth_input.value()

            # Calculate CAPEX
            well_capex = (
                self.exploration_cost_input.value() + 
                self.pad_cost_input.value() +
                total_length * self.cost_per_foot_input.value() +
                self.distance_to_pipe_input.value() * self.cost_per_foot_to_pipe_input.value()
            )

            well_row = {
                "UWI": well_name,
                "total_depth": total_length,
                "total_capex_cost": well_capex,
                "scenario": self.scenario_input.currentText(),
                "decline_curve": self.decline_curve_input.currentText(),
                "prod_type": self.prod_type_input.currentText(),
                "drill_time": drill_time_months,
                "exploration_cost": self.exploration_cost_input.value(),
                "pad_cost": self.pad_cost_input.value(),
                "cost_per_foot": self.cost_per_foot_input.value(),
                "distance_to_pipe": self.distance_to_pipe_input.value(),
                "cost_per_foot_to_pipe": self.cost_per_foot_to_pipe_input.value(),
                "opex_cost": self.opex_input.value(),
                "decline_curve_type": self.decline_type_input.currentText(),
                "start_date": well_start_date.toString("yyyy-MM-dd")
            }
            well_data_list.append(well_row)

        self.well_data = pd.DataFrame(well_data_list)
        super().accept()

if __name__ == "__main__":
    import sys
    import logging
    from PySide6.QtWidgets import QApplication
    
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('pud_selector_test.log'),
            logging.StreamHandler()
        ]
    )
    logger = logging.getLogger(__name__)
    
    try:
        test_wells = [f"100{i:02d}0000" for i in range(1, 11)]
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
        logger.exception("Test failed")
    finally:
        sys.exit(app.exec_())