from pickle import TRUE
from PySide6.QtWidgets import (
    QDialog, QGridLayout, QToolBar, QTableWidget, QComboBox,
    QSizePolicy, QTableWidgetItem, QMessageBox, QStyledItemDelegate,
    QDateEdit
)
from PySide6.QtGui import QAction, QIcon
from PySide6.QtCore import QSize, Qt, Signal, QDate, QSignalBlocker
from PudWellSelector import PUDWellSelector
import logging
import datetime
import os


class DateDelegate(QStyledItemDelegate):
    def __init__(self, parent=None):
        super().__init__(parent)
        
    def createEditor(self, parent, option, index):
        editor = QDateEdit(parent)
        editor.setCalendarPopup(True)
        editor.setDisplayFormat("yyyy-MM-dd")
        return editor
        
    def setEditorData(self, editor, index):
        value = index.model().data(index, Qt.DisplayRole)
        try:
            date = QDate.fromString(value, "yyyy-MM-dd")
            editor.setDate(date)
        except Exception as e:
            logging.error(f"Error setting editor data: {e}")
            editor.setDate(QDate.currentDate())
            
    def setModelData(self, editor, model, index):
        value = editor.date().toString("yyyy-MM-dd")
        model.setData(index, value, Qt.EditRole)

class PUDPropertiesDialog(QDialog):
    """Dialog for managing PUD (Proved Undeveloped) Properties"""
    
    # Signals
    dataChanged = Signal()
    scenarioChanged = Signal(str)
    
    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.setup_logging()
        
        # Initialize state
        self.edited_rows = set()
        self.scenario_name = None
        self.active_scenario_name = None
        self.scenario_id = None
        self.tab_index = 3  # Default tab index
        
        self.setup_ui()
        self.setup_connections()
        self.load_initial_data()
        self.existing_wells = None  # Initialize as None
        self.decline_curvenames = None  # Initialize as None
        self.scenarios = None  # Initialize as None
        
        logging.info("PUDPropertiesDialog initialized")
    
        
    def setup_logging(self):
        """Configure logging for the dialog"""
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('pud_dialog.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
    def setup_ui(self):
        """Initialize the user interface"""
        try:
            self.setWindowTitle("Pad Properties")
            self.setMinimumSize(800, 600)
            
            # Main layout
            self.main_layout = QGridLayout(self)
            
            # Setup toolbar
            self.setup_toolbar()
            
            # Setup scenario dropdown
            self.setup_scenario_dropdown()
            
            # Setup well pads table
            self.setup_table()
            
            logging.debug("UI setup completed successfully")
            
        except Exception as e:
            logging.error(f"Error in setup_ui: {e}")
            raise
            
    def setup_toolbar(self):
        """Initialize toolbar and its actions"""
        try:
            pad_toolbar = QToolBar("Pad Toolbar")
            pad_toolbar.setIconSize(QSize(32, 32))
            script_dir = os.path.dirname(__file__)
            icons_dir = os.path.join(script_dir, "Icons")
            
            # Define actions with their icons, tooltips, and slots
            actions = {
                'add_scenario4': ('Icons/Add Scenario', "Add Scenario", self.add_scenario),
                'run_scenario4': ('Icons/Update Curve', "Update Curve", self.run_scenario),
                'delete_pad4': ('Icons/delete', "Delete Pad", self.delete_pad),
                'add_well4': ('Icons/add', "Add Wells", self.scenario_pud_select),
                'launch_combined_cashflow4': ('Icons/Launch Graph', "Launch Combined Cashflow", 
                                           self.launch_combined_cashflow)
            }
            
            # Create and connect actions
            for attr_name, (icon_path, tooltip, slot) in actions.items():
                action = QAction(QIcon(icon_path), tooltip, self)
                action.triggered.connect(slot)
                setattr(self, attr_name, action)
                pad_toolbar.addAction(action)
                
            self.main_layout.addWidget(pad_toolbar, 0, 1, 1, 10)
            logging.debug("Toolbar setup completed")
            
        except Exception as e:
            logging.error(f"Error in setup_toolbar: {e}")
            raise
            
    def setup_scenario_dropdown(self):
        """Initialize the scenario dropdown"""
        try:
            self.scenario_dropdown4 = QComboBox()
            self.scenario_dropdown4.setFixedHeight(32)
            self.scenario_dropdown4.setObjectName("ScenarioDropdown")
            self.main_layout.addWidget(self.scenario_dropdown4, 0, 0, 1, 1)
            logging.debug("Scenario dropdown setup completed")
            
        except Exception as e:
            logging.error(f"Error in setup_scenario_dropdown: {e}")
            raise
            
    def setup_table(self):
        """Initialize the well pads table"""
        try:
            self.well_pads_table = QTableWidget()
            self.well_pads_table.setObjectName("WellPadsTable")
            
            # Set up columns
            headers = [
                "Pad Name", "Start Date", "Decline Curve", "Total Lateral", 
                "Total CAPEX Cost", "Total OPEX Cost", "Drill Time",
                "Prod Type", "Oil Model Status", "Gas Model Status", "Pad Cost",
                "Exploration Cost", "Cost per Foot", "Distance to Pipe",
                "Cost per Foot to Pipe"
            ]
            
            self.well_pads_table.setColumnCount(len(headers))
            self.well_pads_table.setHorizontalHeaderLabels(headers)
            self.well_pads_table.verticalHeader().setVisible(False)
            
            # Set up delegates
            date_delegate = DateDelegate(self.well_pads_table)
            self.well_pads_table.setItemDelegateForColumn(1, date_delegate)
            
            self.main_layout.addWidget(self.well_pads_table, 1, 0, 1, 11)
            logging.debug("Table setup completed")
            
        except Exception as e:
            logging.error(f"Error in setup_table: {e}")
            raise
            
    def setup_connections(self):
        """Set up signal/slot connections"""
        try:
            self.scenario_dropdown4.currentTextChanged.connect(self.on_scenario_changed)
            self.well_pads_table.itemChanged.connect(self.on_table_item_changed)
            logging.debug("Signal connections established")
            
        except Exception as e:
            logging.error(f"Error in setup_connections: {e}")
            raise
            
    def load_initial_data(self):
        """Load initial data into the dialog"""
        try:
            # Load scenarios into dropdown, excluding Active_Wells
            scenarios = self.db_manager.get_scenario_names()
            filtered_scenarios = [s for s in scenarios if s != 'Active_Wells']
            print(filtered_scenarios)
            self.decline_curves = self.db_manager.get_decline_curve_names()
            # Only proceed if we have scenarios to show
            if filtered_scenarios:
                # Block signals while adding items to the dropdown
                with QSignalBlocker(self.scenario_dropdown4):
                    self.scenario_dropdown4.clear()  # Clear existing items
                    self.scenario_dropdown4.addItems(filtered_scenarios)

                # Retrieve and set the active scenario ID
                self.scenario_id = self.db_manager.get_active_scenario_id()
                self.active_scenario_name = self.db_manager.get_active_scenario_name()

                if self.scenario_id is not None:
                    # Find and select the active scenario in the dropdown
                    
                    index = self.scenario_dropdown4.findText(self.active_scenario_name)
                    if index >= 0:
                        self.scenario_dropdown4.setCurrentIndex(index)

                    self.populate_well_pads_table()
                    logging.info("Initial data loaded successfully.")
                else:
                    logging.warning("No active scenario found.")
                    QMessageBox.warning(self, "Warning", "No active scenario found. Please select or create a scenario.")
            else:
                logging.info("No scenarios to load.")

        except Exception as e:
            logging.error(f"Error loading initial data: {e}")
            QMessageBox.critical(self, "Error", "Failed to load initial data.")
            
    def scenario_pud_select(self):
        try:
            # Fetch the required data for the dialog
            self.existing_wells = self.db_manager.get_planned_wells()
            self.decline_curves = self.db_manager.get_decline_curve_names()
            self.scenarios = [s for s in self.db_manager.get_scenario_names() if s != 'Active_Wells']

            # Initialize the dialog with available data
            dialog = PUDWellSelector(self, self.decline_curves, self.scenarios, self.existing_wells)

            # Show the dialog and check if it was accepted
            if dialog.exec_() == QDialog.Accepted:
                # Extract well data from the dialog
                well_data = dialog.well_data
                scenario_name = well_data['scenario']
          
                # Check if the scenario exists; if not, create it
                self.scenario_id = self.db_manager.get_scenario_id(scenario_name)
                if self.scenario_id is None:
                    self.scenario_id = self.db_manager.insert_scenario_name(scenario_name)
                    self.db_manager.set_active_scenario(self.scenario_id)
                    scenarios = self.db_manager.get_scenario_names()
                    filtered_scenarios = [s for s in scenarios if s != 'Active_Wells']
                    print(filtered_scenarios)
                    self.decline_curves = self.db_manager.get_decline_curve_names()
                    # Only proceed if we have scenarios to show
                    if filtered_scenarios:
                        # Block signals while adding items to the dropdown
                        with QSignalBlocker(self.scenario_dropdown4):
                            self.scenario_dropdown4.clear()  # Clear existing items
                            self.scenario_dropdown4.addItems(filtered_scenarios)
                        index = self.scenario_dropdown4.findText(scenario_name)
                        if index >= 0:
                            self.scenario_dropdown4.setCurrentIndex(index)
                        else:
                            logging.warning(f"Scenario '{scenario_name}' not found in dropdown.")

                    if self.scenario_id is None:
                        QMessageBox.critical(self, "Error", f"Failed to create scenario '{scenario_name}'")
                        return

                # Save selected wells to the database using the well data
                self.save_selected_uiws_to_database(well_data, self.scenario_id)

                # Refresh the UI to reflect the updated scenario and wells
  
                self.populate_well_pads_table()

                QMessageBox.information(self, "Success", f"Scenario '{scenario_name}' updated successfully.")
        except Exception as e:
            logging.error(f"Error in scenario_pud_select: {e}")
            QMessageBox.critical(self, "Error", f"An error occurred: {e}")

    def save_selected_uiws_to_database(self, well_data, scenario_id):
        """
        Save selected wells and associated data to the database.

        :param well_data: Dictionary containing well data from the dialog.
        :param scenario_id: ID of the scenario.
        """
        try:
            selected_wells = well_data['selected_wells']
            decline_curve = well_data['decline_curve']
            start_date = well_data.get('start_date', None)  # Optional field

            # Fetch existing wells for the scenario from well_pads
            existing_uiws = self.db_manager.get_uiws_for_scenario(scenario_id)

            # Iterate over selected wells
            for uwi in selected_wells:
                well_pad_data = {
                    'uwi': uwi,
                    'scenario_id': scenario_id,
                    'start_date': well_data['start_date'],
                    'total_lateral': well_data['total_lateral'],
                    'total_capex_cost': well_data['total_capex_cost'],
                    'total_opex_cost': well_data['opex_cost'],
                    'drill_time': well_data['drill_time'],
                    'prod_type': well_data['prod_type'],
                    'oil_model_status': 1 if well_data['prod_type'] in ["Oil", "Both"] else 0,
                    'gas_model_status': 1 if well_data['prod_type'] in ["Gas", "Both"] else 0,
                    'pad_cost': well_data['pad_cost'],
                    'exploration_cost': well_data['exploration_cost'],
                    'cost_per_foot': well_data['cost_per_foot'],
                    'distance_to_pipe': well_data['distance_to_pipe'],
                    'cost_per_foot_to_pipe': well_data['cost_per_foot_to_pipe'],
                    'decline_curve': decline_curve,
                }

                if uwi in existing_uiws:
                    logging.info(f"Updating well pad for UWI: {uwi}")
                    # Update existing well pad
                    well_pad_id = self.db_manager.get_well_pad_id(uwi, scenario_id)
                    self.db_manager.update_well_pad(well_pad_id, well_pad_data)
                else:
                    logging.info(f"Inserting new well pad for UWI: {uwi}")
                    # Insert new well pad
                    self.db_manager.insert_well_pad(well_pad_data)

            # Remove wells not in the selected list
            uiws_to_remove = [uwi for uwi in existing_uiws if uwi not in selected_wells]
            for uwi in uiws_to_remove:
                logging.info(f"Removing well pad for UWI: {uwi}")
                self.db_manager.delete_pad(scenario_id, uwi)
               

            QMessageBox.information(self, "Success", f"Scenario updated successfully!")
            logging.info(f"Scenario {scenario_id} updated with {len(selected_wells)} wells.")

        except Exception as e:
            logging.error(f"Error saving wells to database: {e}")
            QMessageBox.critical(self, "Error", f"Failed to save wells: {e}")

    def extract_well_data(self, dialog):
        """Extract well data from the dialog inputs"""
        try:
            data = {
                'uwi': dialog.uwi_input.text(),
                'start_date': dialog.start_date_input.date().toString('yyyy-MM-dd'),  # Extract from QDateEdit
                'decline_curve': dialog.decline_curve_input.currentText(),           # Extract from QComboBox
                'total_lateral': dialog.total_lateral_input.value(),
                'total_capex_cost': float(dialog.capex_cost_output.text().replace('$', '')),
                'total_opex_cost': dialog.opex_input.value(),
                'drill_time': dialog.drill_time_input.value(),
                'prod_type': dialog.prod_type_input.currentText(),
                'oil_model_status': 1 if dialog.prod_type_input.currentText() in ["Oil", "Both"] else 0,
                'gas_model_status': 1 if dialog.prod_type_input.currentText() in ["Gas", "Both"] else 0,
                'pad_cost': dialog.pad_cost_input.value(),
                'exploration_cost': dialog.exploration_cost_input.value(),
                'cost_per_foot': dialog.cost_per_foot_input.value(),
                'distance_to_pipe': dialog.distance_to_pipe_input.value(),
                'cost_per_foot_to_pipe': dialog.cost_per_foot_to_pipe_input.value()
            }
            logging.debug(f"Extracted well data: {data}")
            return data
        except Exception as e:
            logging.error(f"Error extracting well data: {e}")
            raise

        
    def populate_well_pads_table(self):
        """Populate the well pads table with data"""
        try:
            with QSignalBlocker(self.well_pads_table):
                self.well_pads_table.clear()
            
                # Reset table headers
                # Reset table headers
                headers = [
                    "UWI", "Start Date", "Decline Curve", "Total Lateral", "Total CAPEX Cost",
                    "Total OPEX Cost", "Drill Time", "Production Type",
                    "Oil Model Status", "Gas Model Status", "Pad Cost", "Exploration Cost",
                    "Cost Per Foot", "Distance to Pipe", "Cost Per Foot to Pipe"
                ]
                self.well_pads_table.setColumnCount(len(headers))
                self.well_pads_table.setHorizontalHeaderLabels(headers)

                # Get well pad data for the active scenario
                well_pads = self.db_manager.get_well_pads(self.scenario_id)
                self.well_pads_table.setRowCount(len(well_pads))

                # Enable sorting after the table is populated
                self.well_pads_table.setSortingEnabled(True) 

        # Temporarily disable sorting for performance

                # Populate rows
                for row_idx, pad in enumerate(well_pads):
                    self.populate_table_row(row_idx, pad)

        
            logging.info("Well pads table populated successfully.")
        
        except Exception as e:
            logging.error(f"Error populating well pads table: {e}")
            QMessageBox.critical(self, "Error", "Failed to populate well pads table")

    def populate_table_row(self, row_idx, pad):
        """
        Populate a single row in the well pads table.
        :param row_idx: Row index in the table.
        :param pad: Dictionary containing well pad data.
        """
        try:
            # Column 0: UWI
            self.well_pads_table.setItem(row_idx, 0, QTableWidgetItem(str(pad['uwi'])))

            # Column 1: Start Date as QDateEdit
            start_date_edit = QDateEdit()
            start_date_edit.setCalendarPopup(True)
            start_date = pad.get('start_date', '')
            if start_date:
                start_date_edit.setDate(QDate.fromString(start_date, 'yyyy-MM-dd'))
            self.well_pads_table.setCellWidget(row_idx, 1, start_date_edit)

            # Column 2: Decline Curve as QComboBox
            decline_curve_combo = QComboBox()
            decline_curve_combo.addItems(self.decline_curves or [])  # Use preloaded decline curve names
            decline_curve = pad.get('decline_curve', '')
            if decline_curve:
                decline_curve_combo.setCurrentText(decline_curve)
            self.well_pads_table.setCellWidget(row_idx, 2, decline_curve_combo)

            # Remaining columns as QTableWidgetItem
            column_mapping = [
                ('total_lateral', 3, "{:.2f}"),
                ('total_capex_cost', 4, "${:.2f}"),
                ('total_opex_cost', 5, "${:.2f}"),
                ('drill_time', 7, "{}"),
                ('prod_type', 8, "{}"),
                ('oil_model_status', 9, "{}"),
                ('gas_model_status', 10, "{}"),
                ('pad_cost', 11, "${:.2f}"),
                ('exploration_cost', 12, "${:.2f}"),
                ('cost_per_foot', 13, "${:.2f}"),
                ('distance_to_pipe', 14, "${:.2f}"),
                ('cost_per_foot_to_pipe', 15, "${:.2f}")
            ]

            for key, col, fmt in column_mapping:
                value = pad.get(key, '')
                formatted_value = fmt.format(value) if value != '' else ''
                self.well_pads_table.setItem(row_idx, col, QTableWidgetItem(formatted_value))

        except KeyError as e:
            logging.error(f"Key error while populating row {row_idx}: {e}")
        except Exception as e:
            logging.error(f"Unexpected error while populating row {row_idx}: {e}")
            
    def on_scenario_changed(self, scenario_name):
        """Handle scenario selection changes"""
        try:
            logging.info(f"Scenario changed to: {scenario_name}")
            
            self.scenario_name = scenario_name
            if scenario_name:
                self.scenario_id = self.db_manager.get_scenario_id(scenario_name)
                
            # Update UI based on scenario
            self.update_ui_for_scenario()
            
            # Refresh table data
            self.populate_well_pads_table()
            
            # Emit signal for parent widgets
            self.scenarioChanged.emit(scenario_name)
            
        except Exception as e:
            logging.error(f"Error in on_scenario_changed: {e}")
            QMessageBox.critical(self, "Error", "Failed to change scenario")
            
    def update_ui_for_scenario(self):
        """Update UI elements based on selected scenario"""
        try:
            is_active_wells = self.scenario_name == "Active_Wells"
            
            # Disable certain actions for Active_Wells scenario
            self.add_scenario4.setEnabled(not is_active_wells)
            self.run_scenario4.setEnabled(not is_active_wells)
            self.add_well4.setEnabled(not is_active_wells)
            
            # Update table editability
            self.well_pads_table.setEnabled(not is_active_wells)
            
            logging.debug(f"UI updated for scenario: {self.scenario_name}")
            
        except Exception as e:
            logging.error(f"Error updating UI for scenario: {e}")
            raise
            
    def on_table_item_changed(self, item):
        """Handle changes in table items"""
        try:
            if self.scenario_name == "Active_Wells":
                QMessageBox.warning(self, "Warning", 
                                  "Adding plans to the 'Active_Wells' scenario is not allowed.")
                with QSignalBlocker(self.well_pads_table):
                    item.setText("")
                return
                
            row = item.row()
            column = item.column()
            new_value = item.text()
            
            logging.debug(f"Table item changed - Row: {row}, Column: {column}, Value: {new_value}")
            
            # Add to edited rows
            self.edited_rows.add(row)
            
            # Update scenario with changes
            self.update_scenario()
            
        except Exception as e:
            logging.error(f"Error handling table item change: {e}")
            QMessageBox.critical(self, "Error", "Failed to update table item")
            
    def update_scenario(self):
        """Update scenario with changed data"""
        try:
            if not self.edited_rows:
                return
                
            for row in self.edited_rows:
                scenario_data = self.collect_row_data(row)
                if scenario_data:
                    self.db_manager.update_scenario_data(scenario_data)
                    
            self.edited_rows.clear()
            self.dataChanged.emit()
            logging.info("Scenario updated successfully")
            
        except Exception as e:
            logging.error(f"Error updating scenario: {e}")
            QMessageBox.critical(self, "Error", "Failed to update scenario")
            
    def collect_row_data(self, row):
        """Collect all data from a table row"""
        try:
            data = {}
            for col in range(self.well_pads_table.columnCount()):
                item = self.well_pads_table.item(row, col)
                if item:
                    header = self.well_pads_table.horizontalHeaderItem(col).text()
                    data[header] = item.text()
            return data
            
        except Exception as e:
            logging.error(f"Error collecting row data for row {row}: {e}")
            return None
            
    def add_scenario(self):
        """Handle adding a new scenario"""
        try:
            # Implement scenario addition logic
            logging.info("Adding new scenario")
            # TODO: Implement scenario addition dialog and logic
            
        except Exception as e:
            logging.error(f"Error adding scenario: {e}")
            QMessageBox.critical(self, "Error", "Failed to add scenario")
            
    def run_scenario(self):
        """Handle running a scenario"""
        try:
            if not self.scenario_name:
                QMessageBox.warning(self, "Warning", "Please select a scenario first")
                return
                
            logging.info(f"Running scenario: {self.scenario_name}")
            # TODO: Implement scenario execution logic
            
        except Exception as e:
            logging.error(f"Error running scenario: {e}")
            QMessageBox.critical(self, "Error", "Failed to run scenario")
            
    def delete_pad(self):
        """Handle deleting a pad using the current scenario ID and UWI."""
        try:
            selected_items = self.well_pads_table.selectedItems()
            if not selected_items:
                QMessageBox.warning(self, "Warning", "Please select a pad to delete")
                return

            # Get the row of the selected pad
            row = selected_items[0].row()
            logging.debug(f"Selected row: {row}")

            # Extract the UWI
            uwi_item = self.well_pads_table.item(row, 0)
            print(uwi_item)# Assuming column 0 contains UWI
            if uwi_item is None:
                QMessageBox.warning(self, "Warning", "Unable to determine the UWI for the selected pad")
                return

            uwi = uwi_item.text()
            logging.debug(f"UWI: {uwi}")


            # Confirm deletion
            reply = QMessageBox.question(
                self,
                "Confirm Deletion",
                f"Are you sure you want to delete the pad for UWI '{uwi}' in the current scenario?",
                QMessageBox.Yes | QMessageBox.No
            )

            if reply == QMessageBox.Yes:
                # Perform the deletion in the database
                self.db_manager.delete_pad(self.scenario_id, uwi)

                # Remove the row from the table
                self.well_pads_table.removeRow(row)
                logging.info(f"Pad deleted: UWI={uwi}, Scenario ID={self.scenario_id}")
                self.populate_well_pads_table()

        except Exception as e:
            logging.error(f"Error deleting pad: {e}")
            QMessageBox.critical(self, "Error", "Failed to delete pad")
            
    def launch_combined_cashflow(self):
        """Handle launching combined cashflow analysis"""
        try:
            if not self.scenario_name:
                QMessageBox.warning(self, "Warning", "Please select a scenario first")
                return
                
            logging.info(f"Launching combined cashflow for scenario: {self.scenario_name}")
            # TODO: Implement combined cashflow analysis launch
            
        except Exception as e:
            logging.error(f"Error launching combined cashflow: {e}")
            QMessageBox.critical(self, "Error", "Failed to launch combined cashflow analysis")
            
    def closeEvent(self, event):
        """Handle dialog close event"""
        try:
            if self.edited_rows:
                reply = QMessageBox.question(self, "Unsaved Changes",
                                           "There are unsaved changes. Do you want to save before closing?",
                                           QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel)
                                           
                if reply == QMessageBox.Yes:
                    self.update_scenario()
                    event.accept()
                elif reply == QMessageBox.No:
                    event.accept()
                else:
                    event.ignore()
            else:
                event.accept()
                
            logging.info("Dialog closed successfully")
            
        except Exception as e:
            logging.error(f"Error in closeEvent: {e}")
            event.accept()
            
    def handle_scenario(self, scenario_id, start_date, base_uwi, decline_curve_data, 
                       drill_time, total_capex_cost, total_opex_cost, prod_type, oil_model_status, 
                       gas_model_status):
        """Handle scenario processing"""
        try:
            # Implementation of scenario handling logic
            logging.info(f"Processing scenario {scenario_id}")
            # TODO: Implement scenario processing logic
            
        except Exception as e:
            logging.error(f"Error handling scenario: {e}")
            raise

if __name__ == "__main__":
    import sys
    from PySide6.QtWidgets import QApplication
    
    # Set up logging for standalone execution
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('pud_dialog_standalone.log'),
            logging.StreamHandler()
        ]
    )
    
    try:
        app = QApplication(sys.argv)
        
        # Create a mock database manager for testing
        class MockDBManager:
            def get_scenario_names(self):
                return ["Scenario 1", "Scenario 2", "Active_Wells"]
                
            def get_decline_curve_names(self):
                return ["Curve 1", "Curve 2"]
                
            # Add other required mock methods
        
        dialog = PUDPropertiesDialog(MockDBManager())
        dialog.show()
        
        sys.exit(app.exec())
        
    except Exception as e:
        logging.critical(f"Application failed to start: {e}")
        sys.exit(1)