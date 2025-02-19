from pickle import TRUE
from PySide6.QtWidgets import (
    QDialog, QGridLayout, QToolBar, QTableWidget, QComboBox,
    QSizePolicy, QTableWidgetItem, QMessageBox, QStyledItemDelegate,
    QDateEdit
)
from PySide6.QtGui import QAction, QIcon
from PySide6.QtCore import QSize, Qt, Signal, QDate, QSignalBlocker, QDateTime
from PudWellSelector import PUDWellSelector
import logging
import datetime
import os
from ScenarioNameDialog import ScenarioNameDialog
import pandas as pd
from DeclineCurveAnalysis import DeclineCurveAnalysis
from LaunchCombinedCashflow import LaunchCombinedCashflow
from datetime import datetime


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
        self.setWindowTitle("Pad Production Scenario Builder")
        self.db_manager = db_manager
        self.setup_logging()
        
        # Initialize state
        self.edited_rows = set()
        self.scenario_name = None
        self.active_scenario_name = None
        self.scenario_id = None
        self.tab_index = 3  # Default tab index

        self.TABLE_HEADERS = [
            "Pad Name",           # maps to UWI
            "Start Date",         # maps to start_date
            "Decline Curve Type", # maps to decline_curve_type
            "Decline Curve",      # maps to decline_curve
            "Total Depth",        # maps to total_depth
            "Total CAPEX Cost",   # maps to total_capex_cost
            "Total OPEX Cost",    # maps to total_opex_cost
            "Drill Time",         # maps to drill_time
            "Prod Type",          # maps to prod_type
            "Oil Model Status",   # maps to oil_model_status
            "Gas Model Status",   # maps to gas_model_status
            "Pad Cost",          # maps to pad_cost
            "Exploration Cost",   # maps to exploration_cost
            "Cost per Foot",     # maps to cost_per_foot
            "Distance to Pipe",   # maps to distance_to_pipe
            "Cost per Foot to Pipe" # maps to cost_per_foot_to_pipe
        ]
    
        # Update key mapping to match headers exactly
        self.key_mapping = {
            "Pad Name": "UWI",
            "Start Date": "start_date",
            "Decline Curve Type": "decline_curve_type",
            "Decline Curve": "decline_curve",
            "Total Depth": "total_depth",
            "Total CAPEX Cost": "total_capex_cost",
            "Total OPEX Cost": "total_opex_cost",
            "Drill Time": "drill_time",
            "Prod Type": "prod_type",
            "Oil Model Status": "oil_model_status",
            "Gas Model Status": "gas_model_status",
            "Pad Cost": "pad_cost",
            "Exploration Cost": "exploration_cost",
            "Cost per Foot": "cost_per_foot",
            "Distance to Pipe": "distance_to_pipe",
            "Cost per Foot to Pipe": "cost_per_foot_to_pipe"
        }



        
        self.setup_ui()
        self.setup_connections()
        self.load_initial_data()
        self.existing_wells = None  # Initialize as None
        self.decline_curvenames = None  # Initialize as None
        self.scenarios = None  # Initialize as None
        
        logging.info("PUDPropertiesDialog initialized")
        self.dca = DeclineCurveAnalysis()
        self.modified_rows = set()  # Track rows that have been modified
        self.modified_data = {}     # Store modified data for each row
        self.has_unsaved_changes = False # Alternatively, track by UWI


 
        
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
                'run_scenario4': ('Icons/Update Curve', "Update Scenario", self.update_scenario),
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
        try:
            self.well_pads_table = QTableWidget()
            self.well_pads_table.setObjectName("WellPadsTable")
    
            print("Setup Table Headers:", self.TABLE_HEADERS)  # Debug print
        
            self.well_pads_table.setColumnCount(len(self.TABLE_HEADERS))
            self.well_pads_table.setHorizontalHeaderLabels(self.TABLE_HEADERS)
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
                self.well_pads_table.itemChanged.connect(self.track_widget_change)
            
                # Add save and run buttons to toolbar
                save_action = QAction(QIcon("Icons/save"), "Save Changes", self)
                save_action.triggered.connect(self.update_scenario)

            
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
            dialog = PUDWellSelector(self, self.decline_curves, self.scenarios, self.existing_wells, self.db_manager)

            # Show the dialog and check if it was accepted
            if dialog.exec_() == QDialog.Accepted:
                # Extract well data from the dialog
                well_data = dialog.well_data
                scenario_name = well_data['scenario'].iloc[0]  # Get the first value
          
                # Check if the scenario exists; if not, create it
                self.scenario_id = self.db_manager.get_scenario_id(scenario_name)
                print(self.scenario_id)
                if self.scenario_id is None:
                    self.scenario_id = self.db_manager.insert_scenario_name(scenario_name)
                    self.db_manager.set_active_scenario(self.scenario_id)
                    scenarios = self.db_manager.get_scenario_names()
                    filtered_scenarios = [s for s in scenarios if s != 'Active_Wells']
                    print(filtered_scenarios)
                    
                    self.decline_curves = self.db_manager.get_decline_curve_names()
                    print(self.decline_curves)
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
                self.run_scenario()
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
            selected_wells = well_data['UWI']
            decline_curve = well_data['decline_curve']
            start_date = well_data.get('start_date', None)  # Optional field

            # Fetch existing wells for the scenario from well_pads
            existing_uiws = self.db_manager.get_uiws_for_scenario(scenario_id)
            print(well_data)
            # Iterate over selected wells
            for _, row in well_data.iterrows():
                UWI = row['UWI']
                well_pad_data = {
                    'UWI': row['UWI'],  # Ensure you extract scalar values
                    'scenario_id': scenario_id,
                    'start_date': row['start_date'],
                    'total_depth': row['total_depth'],
                    'total_capex_cost': row['total_capex_cost'],
                    'total_opex_cost': row['opex_cost'],
                    'drill_time': row['drill_time'],
                    'prod_type': row['prod_type'],
                    'oil_model_status': 1 if row['prod_type'] in ["Oil", "Both"] else 0,
                    'gas_model_status': 1 if row['prod_type'] in ["Gas", "Both"] else 0,
                    'pad_cost': row['pad_cost'],
                    'exploration_cost': row['exploration_cost'],
                    'cost_per_foot': row['cost_per_foot'],
                    'distance_to_pipe': row['distance_to_pipe'],
                    'cost_per_foot_to_pipe': row['cost_per_foot_to_pipe'],
                    'decline_curve_type': row['decline_curve_type'],
                    'decline_curve': row['decline_curve'],
                }
                

                if UWI in existing_uiws:
                    logging.info(f"Updating well pad for UWI: {UWI}")
                    # Update existing well pad
                    well_pad_id = self.db_manager.get_well_pad_id(UWI, scenario_id)
                    self.db_manager.update_well_pad(well_pad_id, well_pad_data)
                else:
                    logging.info(f"Inserting new well pad for UWI: {UWI}")
                    # Insert new well pad

                    self.db_manager.insert_well_pad(well_pad_data)

            # Remove wells not in the selected list
            uiws_to_remove = [UWI for UWI in existing_uiws if UWI not in selected_wells]
            for UWI in uiws_to_remove:
                logging.info(f"Removing well pad for UWI: {UWI}")
                self.db_manager.delete_pad(scenario_id, UWI)
               

            QMessageBox.information(self, "Success", f"Scenario updated successfully!")
            logging.info(f"Scenario {scenario_id} updated with {len(selected_wells)} wells.")

        except Exception as e:
            logging.error(f"Error saving wells to database: {e}")
            QMessageBox.critical(self, "Error", f"Failed to save wells: {e}")

    def extract_well_data(self, dialog):
        """Extract well data from the dialog inputs"""
        try:
            data = {
                'UWI': dialog.UWI_input.text(),
                'start_date': dialog.start_date_input.date().toString('yyyy-MM-dd'),  # Extract from QDateEdit
                'decline_curve': dialog.decline_curve_input.currentText(),           # Extract from QComboBox
                'total_depth': dialog.total_depth_input.value(),
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
            
                # Use class variable for headers
                self.well_pads_table.setColumnCount(len(self.TABLE_HEADERS))
                self.well_pads_table.setHorizontalHeaderLabels(self.TABLE_HEADERS)
            
                # Get well pad data for the active scenario
                well_pads = self.db_manager.get_well_pads(self.scenario_id)
                print("Well pads data:", well_pads)  # Debug print
            
                if well_pads:
                    self.well_pads_table.setRowCount(len(well_pads))
                
                    # Temporarily disable sorting for performance
                    self.well_pads_table.setSortingEnabled(False)
                
                    # Populate rows
                    for row_idx, pad in enumerate(well_pads):
                        self.populate_table_row(row_idx, pad)
                
                    # Enable sorting after the table is populated
                    self.well_pads_table.setSortingEnabled(True)
            
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
            UWI = pad['UWI']
            self.well_pads_table.setItem(row_idx, 0, QTableWidgetItem(str(UWI)))

            # Column 1: Start Date as QDateEdit
            start_date_edit = QDateEdit()
            start_date_edit.setCalendarPopup(True)
            start_date = pad.get('start_date', '')
            if start_date:
                start_date_edit.setDate(QDate.fromString(start_date, 'yyyy-MM-dd'))
            # Add date change tracking
            start_date_edit.dateChanged.connect(
                lambda: self.track_widget_change(row_idx, 1, start_date_edit.date().toString('yyyy-MM-dd'))
            )
            self.well_pads_table.setCellWidget(row_idx, 1, start_date_edit)

            # Column 2: Decline Curve Type as QComboBox
            decline_curve_type_combo = QComboBox()
            decline_curve_type_combo.addItems(["UWI", "Saved DC"])  # Options for Decline Curve Type
            decline_curve_type = pad.get('decline_curve_type', 'UWI')  # Default to 'UWI'
            decline_curve_type_combo.setCurrentText(decline_curve_type)

            # Column 3: Decline Curve as QComboBox
            decline_curve_combo = QComboBox()
            decline_curve_combo.addItems(self.get_decline_curve_options(decline_curve_type))  # Populate based on type
            decline_curve = pad.get('decline_curve', '')
            if decline_curve:
                decline_curve_combo.setCurrentText(decline_curve)

                    # Update tracking when widgets change



            # Update tracking when Decline Curve Type changes
            def update_decline_curve_options():
                selected_type = decline_curve_type_combo.currentText()
                decline_curve_combo.clear()
                new_options = self.get_decline_curve_options(selected_type)
                decline_curve_combo.addItems(new_options)
                if new_options:
                    decline_curve_combo.setCurrentText(new_options[0])  # Default to the first option
                self.modified_rows.add(row_idx)  # Track modified row only

            def update_decline_curve():
                self.modified_rows.add(row_idx)  # Track modified row only

            decline_curve_type_combo.currentTextChanged.connect(update_decline_curve_options)
            decline_curve_combo.currentTextChanged.connect(update_decline_curve)

            decline_curve_type_combo.currentTextChanged.connect(update_decline_curve_options)
            decline_curve_combo.currentTextChanged.connect(update_decline_curve)

            self.well_pads_table.setCellWidget(row_idx, 2, decline_curve_type_combo)
            self.well_pads_table.setCellWidget(row_idx, 3, decline_curve_combo)

            # Remaining columns as QTableWidgetItem
            column_mapping = [
                ('total_depth', 4, "{:.2f}"),
                ('total_capex_cost', 5, "${:.2f}"),
                ('total_opex_cost', 6, "${:.2f}"),
                ('drill_time', 7, "{}"),              # Changed order
                ('prod_type', 8, "{}"),               # Changed order
                ('oil_model_status', 9, "{}"),        # Changed order
                ('gas_model_status', 10, "{}"),       # Changed order
                ('pad_cost', 11, "${:.2f}"),
                ('exploration_cost', 12, "${:.2f}"),
                ('cost_per_foot', 13, "${:.2f}"),
                ('distance_to_pipe', 14, "{:.2f}"),
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

    def refresh_row(self, row_idx, pad):
        """
        Refresh the data in a specific row of the table.
        :param row_idx: Row index in the table.
        :param pad: Updated dictionary containing well pad data.
        """
        self.populate_table_row(row_idx, pad)

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
            
            self.run_scenario4.setEnabled(not is_active_wells)
            self.add_well4.setEnabled(not is_active_wells)
            
            # Update table editability
            self.well_pads_table.setEnabled(not is_active_wells)
            
            logging.debug(f"UI updated for scenario: {self.scenario_name}")
            
        except Exception as e:
            logging.error(f"Error updating UI for scenario: {e}")
            raise
            
    def track_change(self, row, column, new_value):
        """Track changes made to the table"""
        try:
            if row not in self.modified_data:
                self.modified_data[row] = {}
            
            # Get the column header
            header = self.well_pads_table.horizontalHeaderItem(column).text()
            
            # Store the modified value
            self.modified_data[row][header] = new_value
            self.modified_rows.add(row)
            self.has_unsaved_changes = True
            
            # Update window title to indicate unsaved changes
            self.setWindowTitle("Pad Properties *")
            
            logging.debug(f"Tracked change - Row: {row}, Column: {header}, Value: {new_value}")
            
        except Exception as e:
            logging.error(f"Error tracking change: {e}")

    def track_widget_change(self, row, column, new_value):
        """Track changes from widgets like QComboBox and QDateEdit"""
        try:
            print(f"Widget changed - Row: {row}, Column: {column}, New Value: {new_value}")  # Debug print
            self.modified_rows.add(row)
            self.has_unsaved_changes = True
            self.setWindowTitle("Pad Properties *")
            logging.info(f"Widget change tracked - Row: {row}, Column: {column}, Value: {new_value}")
        except Exception as e:
            logging.error(f"Error tracking widget change: {e}")
    


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
            
    
       
            
    def run_scenario(self):
        """Run scenario for all wells, ensuring oil_model_status and gas_model_status are taken from scenario_wells_df."""
        try:
            self.db_manager.delete_model_properties_for_scenario(self.scenario_id)
            self.db_manager.delete_production_rates_for_scenario(self.scenario_id)

            scenario_wells_df = self.db_manager.get_scenario_wells(self.scenario_id)

            if scenario_wells_df is None or scenario_wells_df.empty:
                logging.warning("No wells found for this scenario.")
                QMessageBox.warning(self, "Warning", "No wells found for this scenario.")
                return

            total_wells = len(scenario_wells_df)
            processed_wells = 0
            error_wells = []

            for _, well_data in scenario_wells_df.iterrows():
                try:
                    UWI = well_data['UWI']
                    decline_curve_type = well_data['decline_curve_type']
                    decline_curve_name = well_data['decline_curve']
                    start_date = well_data.get('start_date', None)

                    decline_curve_data = None

                    if decline_curve_type == 'UWI':
                        decline_curve_df = self.db_manager.retrieve_model_data_by_scenario_and_UWI(
                            scenario_id=1,  
                            UWI=decline_curve_name
                        )

                        if decline_curve_df is not None and not decline_curve_df.empty:
                            decline_curve_data = decline_curve_df.iloc[0].to_dict()
                        else:
                            logging.warning(f"No model properties found for reference UWI: {decline_curve_name}")
                            error_wells.append((UWI, "No model properties found"))
                            continue

                    elif decline_curve_type == 'Saved DC':
                        decline_curve_data = self.db_manager.get_saved_decline_curve_data(decline_curve_name)

                        if decline_curve_data is None:
                            logging.warning(f"No saved decline curve found: {decline_curve_name}")
                            error_wells.append((UWI, "No saved decline curve found"))
                            continue

                    else:
                        logging.error(f"Unknown decline curve type: {decline_curve_type}")
                        error_wells.append((UWI, f"Unknown decline curve type: {decline_curve_type}"))
                        continue

                    # Ensure all required fields exist in decline_curve_data
                    required_fields = [
                        "max_oil_production", "max_gas_production", "max_oil_production_date",
                        "max_gas_production_date", "one_year_oil_production", "one_year_gas_production",
                        "di_oil", "di_gas", "oil_b_factor", "gas_b_factor", "min_dec_oil", "min_dec_gas",
                        "model_oil", "model_gas", "economic_limit_type", "economic_limit_date",
                        "oil_price", "gas_price", "oil_price_dif", "gas_price_dif", "discount_rate",
                        "working_interest", "royalty", "tax_rate", "capital_expenditures", "operating_expenditures",
                        "net_price_oil", "net_price_gas", "gas_model_status", "oil_model_status"
                    ]

                    for field in required_fields:
                        if field not in decline_curve_data:
                            decline_curve_data[field] = None  # Fill missing fields

                    # Ensure `oil_model_status` and `gas_model_status` come from `scenario_wells_df`
                    decline_curve_data['oil_model_status'] = well_data.get('oil_model_status', None)
                    decline_curve_data['gas_model_status'] = well_data.get('gas_model_status', None)
                    decline_curve_data['max_oil_production_date'] = well_data.get('start_date', None)

                    decline_curve_data['max_gas_production_date'] = well_data.get('start_date', None)
                    
                    

                    # Assign UWI and scenario ID
                    decline_curve_data['UWI'] = UWI
                    decline_curve_data['scenario_id'] = self.scenario_id

                    # Process the scenario with updated decline curve data
                    self.handle_scenario(self.scenario_id, decline_curve_data)
                    processed_wells += 1

                    if processed_wells % 5 == 0:
                        logging.info(f"Processed {processed_wells}/{total_wells} wells")

                except Exception as e:
                    error_msg = str(e)
                    logging.error(f"Error processing well {well_data.get('UWI', 'unknown')}: {error_msg}")
                    error_wells.append((well_data.get('UWI', 'unknown'), error_msg))
                    continue

            # Show results
            success_count = processed_wells - len(error_wells)
            if error_wells:
                error_msg = "\n".join([f"UWI: {UWI} - Error: {error}" for UWI, error in error_wells])
                QMessageBox.warning(
                    self,
                    "Scenario Processing Complete",
                    f"Processed {success_count}/{total_wells} wells successfully.\n"
                    f"{len(error_wells)} wells had errors:\n{error_msg}"
                )
            else:
                QMessageBox.information(
                    self,
                    "Scenario Processing Complete",
                    f"Successfully processed all {total_wells} wells!"
                )

        except Exception as e:
            logging.error(f"Error in run_scenario: {e}")
            QMessageBox.critical(self, "Error", f"Failed to run scenario: {str(e)}")




    def handle_scenario(self, scenario_id, well_data):
        
        df_UWI_model_data = pd.DataFrame([well_data])
        if 'id' in df_UWI_model_data.columns:
            df_UWI_model_data = df_UWI_model_data.drop(columns=['id'])
            
        date_columns = ['max_oil_production_date', 'max_gas_production_date', 'economic_limit_date']
        for col in date_columns:
            if col in df_UWI_model_data.columns:
                df_UWI_model_data[col] = pd.to_datetime(df_UWI_model_data[col], errors='coerce').dt.strftime('%Y-%m-%d')
                
        # These are the columns that match the model_properties table schema
        required_columns = [
            "scenario_id", "UWI", 
            "max_oil_production", "max_gas_production",
            "max_oil_production_date", "max_gas_production_date",
            "one_year_oil_production", "one_year_gas_production", 
            "di_oil", "di_gas",
            "oil_b_factor", "gas_b_factor", 
            "min_dec_oil", "min_dec_gas", 
            "model_oil", "model_gas", 
            "economic_limit_type", "economic_limit_date", 
            "oil_price", "gas_price", 
            "oil_price_dif", "gas_price_dif", 
            "discount_rate", "working_interest", 
            "royalty", "tax_rate", 
            "capital_expenditures", "operating_expenditures",
            "net_price_oil", "net_price_gas",
            "gas_model_status", "oil_model_status"
        ]

        # Reorder columns to match the database schema
        df_UWI_model_data = df_UWI_model_data[required_columns]
        print(df_UWI_model_data)
    
        self.db_manager.update_model_properties(df_UWI_model_data, scenario_id)
    
        self.UWI_production_rates_data, self.UWI_error, self.UWI_model_data = self.dca.planned_prod_rate(df_UWI_model_data)
        self.db_manager.update_UWI_prod_rates(self.UWI_production_rates_data, scenario_id)
    
        self.UWI_error = pd.DataFrame({
            'UWI': well_data['UWI'],
            'sum_error_oil': [0],
            'sum_error_gas': [0]
        })
    
        self.db_manager.update_UWI_errors(self.UWI_error, scenario_id)
    
        
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
            UWI_item = self.well_pads_table.item(row, 0)
            print(UWI_item)# Assuming column 0 contains UWI
            if UWI_item is None:
                QMessageBox.warning(self, "Warning", "Unable to determine the UWI for the selected pad")
                return

            UWI = UWI_item.text()
            logging.debug(f"UWI: {UWI}")


            # Confirm deletion
            reply = QMessageBox.question(
                self,
                "Confirm Deletion",
                f"Are you sure you want to delete the pad for UWI '{UWI}' in the current scenario?",
                QMessageBox.Yes | QMessageBox.No
            )

            if reply == QMessageBox.Yes:
                # Perform the deletion in the database
                self.db_manager.delete_pad(self.scenario_id, UWI)

                # Remove the row from the table
                self.well_pads_table.removeRow(row)
                logging.info(f"Pad deleted: UWI={UWI}, Scenario ID={self.scenario_id}")
                self.populate_well_pads_table()

        except Exception as e:
            logging.error(f"Error deleting pad: {e}")
            QMessageBox.critical(self, "Error", "Failed to delete pad")
            
    def launch_combined_cashflow(self):
        self.cashflow_window = LaunchCombinedCashflow()
        # Example data
        combined_data, date_ranges = self.db_manager.retrieve_and_sum()
        model_data = self.db_manager.retrieve_model_data()
        model_data_df = pd.DataFrame(model_data)
        merged_df = pd.merge(date_ranges, model_data_df, on='UWI', how='inner')

        # Select only the UWI, first_date (start date), and capital_expenditures (CapEx) columns
        capex_df = merged_df[['UWI', 'first_date', 'capital_expenditures']]
       #printcapex_df)

        self.cashflow_window.display_cashflow(combined_data, date_ranges, model_data_df )
        self.cashflow_window.show()


    def update_scenario(self):
        try:
            if not self.modified_rows:
                logging.info("No modifications to update")
                return

            # Retrieve the latest well data from the database
            scenario_wells_df = self.db_manager.get_scenario_wells(self.scenario_id)

            if scenario_wells_df is None or scenario_wells_df.empty:
                logging.warning("No wells found for this scenario.")
                QMessageBox.warning(self, "Warning", "No wells found for this scenario.")
                return

            # Get column indices from headers
            headers = [self.well_pads_table.horizontalHeaderItem(col).text() 
                      for col in range(self.well_pads_table.columnCount())]
        
            # Map the actual table headers to the columns we need
            UWI_idx = headers.index('Pad Name')  # "Pad Name" contains UWI
            start_date_idx = headers.index('Start Date')
            decline_curve_type_idx = headers.index('Decline Curve Type')
            decline_curve_idx = headers.index('Decline Curve')

            modified_well_data = []
        
            # Convert set to list for iteration
            modified_row_list = list(self.modified_rows)
        
            for row_idx in modified_row_list:
                logging.info(f"Processing row index: {row_idx}")
            
                # Verify row index is valid
                if row_idx >= self.well_pads_table.rowCount():
                    logging.error(f"Row index {row_idx} is out of bounds")
                    continue

                # Get UWI from table item
                UWI_item = self.well_pads_table.item(row_idx, UWI_idx)
                if not UWI_item:
                    logging.warning(f"Missing UWI (Pad Name) in row {row_idx}")
                    continue
                UWI = UWI_item.text()

                # Get Start Date from QDateEdit widget
                date_widget = self.well_pads_table.cellWidget(row_idx, start_date_idx)
                start_date = date_widget.date().toString('yyyy-MM-dd') if date_widget else None

                # Get Decline Curve Type from QComboBox widget
                dc_type_widget = self.well_pads_table.cellWidget(row_idx, decline_curve_type_idx)
                decline_curve_type = dc_type_widget.currentText() if dc_type_widget else None

                # Get Decline Curve from QComboBox widget
                dc_widget = self.well_pads_table.cellWidget(row_idx, decline_curve_idx)
                decline_curve = dc_widget.currentText() if dc_widget else None

                logging.info(f"Row {row_idx} values:")
                logging.info(f"UWI: {UWI}")
                logging.info(f"Start Date: {start_date}")
                logging.info(f"DC Type: {decline_curve_type}")
                logging.info(f"DC: {decline_curve}")

                # Find the well pad ID and save basic updates
                well_pad_row = scenario_wells_df[scenario_wells_df["UWI"] == UWI]
                if not well_pad_row.empty:
                    well_pad_id = well_pad_row.iloc[0]["id"]
                
                    # Save the basic column updates first
                    self.db_manager.update_well_pad_decline_data(
                        well_pad_id=well_pad_id,
                        start_date=start_date,
                        decline_curve_type=decline_curve_type,
                        decline_curve=decline_curve
                    )
                
                    # Build well data dictionary for decline curve processing
                    well_pad_data = {
                        "id": well_pad_id,
                        "UWI": UWI,
                        "start_date": start_date,
                        "decline_curve_type": decline_curve_type,
                        "decline_curve": decline_curve,
                        "oil_model_status": well_pad_row.iloc[0].get('oil_model_status', 0),
                        "gas_model_status": well_pad_row.iloc[0].get('gas_model_status', 0)
                    }
                    modified_well_data.append(well_pad_data)
                
                    logging.info(f"Updated basic data for UWI {UWI}")
                else:
                    logging.warning(f"No well pad ID found for UWI: {UWI}")

            if not modified_well_data:
                logging.info("No valid well pad data to update.")
                return

            # Step 2: Process each modified well with its decline curve data
            for well_pad_data in modified_well_data:
                try:
                    UWI = well_pad_data["UWI"]
                    decline_curve_type = well_pad_data["decline_curve_type"]
                    decline_curve_name = well_pad_data["decline_curve"]
                    start_date = well_pad_data["start_date"]

                    decline_curve_data = None

                    if decline_curve_type == "UWI":
                        decline_curve_df = self.db_manager.retrieve_model_data_by_scenario_and_UWI(
                            scenario_id=self.scenario_id,
                            UWI=decline_curve_name
                        )
                        decline_curve_data = decline_curve_df.iloc[0].to_dict() if not decline_curve_df.empty else None

                    elif decline_curve_type == "Saved DC":
                        decline_curve_data = self.db_manager.get_saved_decline_curve_data(decline_curve_name)

                    if decline_curve_data is None:
                        logging.warning(f"No valid decline curve found for {UWI}")
                        continue

                    # Step 3: Ensure all required fields exist in decline_curve_data
                    required_fields = [
                        "max_oil_production", "max_gas_production", "max_oil_production_date",
                        "max_gas_production_date", "one_year_oil_production", "one_year_gas_production",
                        "di_oil", "di_gas", "oil_b_factor", "gas_b_factor", "min_dec_oil", "min_dec_gas",
                        "model_oil", "model_gas", "economic_limit_type", "economic_limit_date",
                        "oil_price", "gas_price", "oil_price_dif", "gas_price_dif", "discount_rate",
                        "working_interest", "royalty", "tax_rate", "capital_expenditures", 
                        "operating_expenditures", "net_price_oil", "net_price_gas"
                    ]

                    for field in required_fields:
                        decline_curve_data.setdefault(field, None)

                    # Overwrite necessary values
                    decline_curve_data["max_oil_production_date"] = start_date
                    decline_curve_data["max_gas_production_date"] = start_date
                
                    # Preserve the model status from the well pad data
                    decline_curve_data["oil_model_status"] = well_pad_data["oil_model_status"]
                    decline_curve_data["gas_model_status"] = well_pad_data["gas_model_status"]

                    # Assign UWI and scenario ID
                    decline_curve_data["UWI"] = UWI
                    decline_curve_data["scenario_id"] = self.scenario_id

                    # Process the scenario with updated decline curve data
                    self.handle_scenario(self.scenario_id, decline_curve_data)

                except Exception as e:
                    logging.error(f"Error processing well {UWI}: {str(e)}")

            # Step 4: Final cleanup
            self.modified_rows.clear()
            self.has_unsaved_changes = False
            self.setWindowTitle("Pad Properties")
            self.populate_well_pads_table()

            QMessageBox.information(self, "Success", "Scenario updated successfully!")

        except Exception as e:
            logging.error(f"Error in update_scenario: {e}")
            QMessageBox.critical(self, "Error", f"Failed to update scenario: {str(e)}")
    def get_decline_curve_options(self, decline_curve_type):
        """
        Get options for the Decline Curve dropdown based on the selected Decline Curve Type.
        :param decline_curve_type: The type of decline curve ("UWI" or "Saved DC").
        :return: A list of decline curve options.
        """
        if decline_curve_type == "UWI":
            return self.db_manager.get_active_UWIs_with_properties()  # Fetch UWI options
        elif decline_curve_type == "Saved DC":
            return self.db_manager.get_decline_curve_names()  # Fetch Saved DC options
        else:
            return []
            
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