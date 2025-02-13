
import sys
import subprocess
import os
import pandas as pd
from PySide6.QtWidgets import (
    QApplication, QDialog, QHBoxLayout, QVBoxLayout, QPushButton, QMenuBar, 
    QMessageBox, QMainWindow, QTableWidgetItem, QFileDialog, QWidget, QInputDialog, QMenu
)
from PySide6.QtGui import QFont, QIcon
from PySide6.QtCore import QDateTime, QDate, QTime, QObject, QEvent, Qt


from UiMain import UI_main
from plotting import Plotting
from LoadProductions import LoadProductions
from ImportExcel import ImportExcelDialog
from SeisWareConnect import SeisWareConnectDialog 
from DeclineCurveAnalysis import DeclineCurveAnalysis 
from DefaultProperties import DefaultProperties
from ModelProperties import ModelProperties
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from DatabaseManager import DatabaseManager
from ProjectDialog import ProjectDialog
from LaunchCombinedCashflow import LaunchCombinedCashflow
from SaveDeclineCurveDialog import SaveDeclineCurveDialog
from numeric_table_widget_item import NumericTableWidgetItem
from ScenarioNameDialog import ScenarioNameDialog
from DateDelegate import DateDelegate
from ComboBoxDelegate import ComboBoxDelegate
from PlotTotals import plot_totals
#from AddWell import AddWell
from EurNpv import EurNpv


import sqlite3

import numpy as np
import os


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.ui = UI_main()
        self.ui.setupUI(self)

        self.dca = None
        self.last_sorted_column = 0
        self.last_sort_order = Qt.AscendingOrder
        self.UWI_df =[]
        self.model_data = [] 
        self.combined_df = None  # Assuming combined_df will be set later
        self.current_UWI_index = 0 
        self.UWI_list = [] 
        self.total_items = len(self.UWI_list)# Store the list of UWIs
        self.current_UWI = None
        self.dialog_changed_flag = False
        self.prod_rates_errors = None
        self.prod_rates_all = None
        self.prod_rates_ag = None
        self.UWI_prod_and_rates = None
        self.df_combined_all = None
        #self.ui.connect_parameters_triggers(self) 
        self.default_properties = None
        self.df_combined_all = None
        self.distribution_type = "Exponential"
        self.graph_type = "Decline Curve"
        self.script_dir = os.path.dirname(os.path.realpath(__file__))
        self.data_type = "Both"
        self.regenerated = False
        self.sum_of_errors = None
        self.iterate = False
        self.best_di = False
        self.best_error_gas = None
        self.best_error_oil= None
        self.best_di_gas = None
        self.best_di_oil = None
        self.tab_index = None
        self.scenario_id = None
        self.scenario_name = None
        self.scenario_names = []
        self.edited_model_rows = []
        self.iterate_di = False
        self.iterate_bfactor = False
        self.edited_rows = []
        self.open = False
        self.load_oil = True
        self.load_oil = True
        self.html_content_by_UWI = {}
        self.project_name = None
        self.db_path = None
        self.last_directory_path = None
        self.model_data_df = pd.DataFrame()
        self.UWI_production_rates_data = pd.DataFrame()
        self.UWI_error = pd.DataFrame()
        self.db_manager = DatabaseManager(None)
        self.dca = DeclineCurveAnalysis()
        self.eur_npv = EurNpv(self.db_manager, self.db_path)

        self.displayed_status = "Active"

     
        

        
        self.default_properties_dialog = DefaultProperties()
    


        self.updated_model = None
        self.di_value = None
        #self.ui.connect_parameters_triggers(self)
        self.ui.calculate_net_price()
        self.ui.royalty.editingFinished.connect(self.ui.calculate_net_price)
        self.ui.working_interest.editingFinished.connect(self.ui.calculate_net_price)
        self.ui.oil_price.editingFinished.connect(self.ui.calculate_net_price)
        self.ui.gas_price.editingFinished.connect(self.ui.calculate_net_price)
        self.ui.oil_price_dif.editingFinished.connect(self.ui.calculate_net_price)
        self.ui.gas_price_dif.editingFinished.connect(self.ui.calculate_net_price)
        self.ui.tax_rate.editingFinished.connect(self.ui.calculate_net_price)
        self.ui.model_properties.setContextMenuPolicy(Qt.CustomContextMenu)
        self.ui.model_properties.customContextMenuRequested.connect(self.show_context_menu)
        


    def eventFilter(self, obj, event):
        if event.type() == QEvent.KeyPress:
            if event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
                # Call the update_decline_curve method when Enter key is pressed
                self.update_decline_curve()
        return super().eventFilter(obj, event)






       
    def retrieve_data(self):
        if self.db_manager:
            
            self.db_manager.connect()
            self.scenario_id = self.db_manager.get_active_scenario_id()
            print(self.scenario_id)
            self.scenario_name = self.db_manager.get_active_scenario_name()
            self.prod_rates_all = self.db_manager.retrieve_prod_rates_all() 
            self.UWI_list  = self.db_manager.get_UWIs_by_scenario_id(self.scenario_id)
            print(self.UWI_list)
            self.scenario_names = self.db_manager.get_all_scenario_names()
            self.ui.activate_icons()

            if self.UWI_list:
                self.ui.well_dropdown.setEnabled(bool(self.UWI_list))
                self.current_UWI_index = 0  # Start at the beginning of the list
                self.current_UWI = self.UWI_list[0]

                # Populate the well dropdown
                self.populate_well_dropdown()

                self.model_data = self.db_manager.retrieve_model_data_by_scenario(self.scenario_id)
                self.sum_of_errors = self.db_manager.retrieve_sum_of_errors(self.scenario_id)
                self.eur_npv = EurNpv(self.db_manager, self.scenario_id)
                self.eur_npv.calculate_eur()
                self.eur_npv.calculate_npv_and_efr()
                
                self.update_displays()
                self.check_model_status_and_set_icon
             
                
               #printself.UWI_list)
                
                
            else:
                self.current_UWI_index = -1
                self.current_UWI = None
                QMessageBox.information(self, "No Wells", "No wells available for the selected scenario.")
                # Clear the graph
                self.ui.graph_area.setHtml("<html><body><h1>No Data Available</h1></body></html>")
                # Clear the well dropdown
                self.ui.well_dropdown.blockSignals(True)
                self.ui.well_dropdown.clear()
                self.ui.well_dropdown.blockSignals(False)
                self.populate_scenario_dropdown_tab1()



# Create Model and Production DataFrames
    def prepare_and_update(self, production_data, directional_survey_values=None, well_data_df=None):
 
                # Ensure directional_survey_values is not None
        if directional_survey_values is None:
            directional_survey_values = pd.DataFrame()



        print('Data Prepared')
        self.production_data = sorted(production_data, key=lambda x: (x['UWI'], x['date']))
        
        if production_data:
            load_productions = LoadProductions()
            self.combined_df, self.UWI_list = load_productions.prepare_data(production_data,self.db_path) 
            #print(self.combined_df)
            self.handle_default_parameters()
            self.ui.activate_icons() 
            self.decline_analysis()
            print('gafag',well_data_df)
            if not directional_survey_values.empty:

                self.db_manager.insert_survey_dataframe_into_db(directional_survey_values, )
                self.db_manager.save_UWI_data(well_data_df)
            else:
                print("No directional survey data to insert.")

    def handle_default_parameters(self):
        self.default_properties_dialog.exec_()
        self.default_properties = self.default_properties_dialog.properties
    


        # Calculate net revenue
        working_interest = self.default_properties.get("working_interest", 0)
        royalty = self.default_properties.get("royalty", 0)
        net_revenue = (working_interest/100) * (1 - (royalty/100))


        self.iterate_di = self.default_properties.get("iterate_di", "")
        self.iterate_bfactor = self.default_properties.get("iterate_bfactor", "")
    
        # Set values for each parameter
        self.ui.end_forecast_type_value = self.default_properties.get("economic_limit_type", "")
        self.ui.end_forecast_type.setCurrentText(self.ui.end_forecast_type_value)
        self.ui.gas_b_factor_input.setText(str(self.default_properties.get("gas_b_factor", "")))
        self.ui.min_dec_gas.setText(str(self.default_properties.get("min_dec_gas", "")))
        self.ui.oil_b_factor_input.setText(str(self.default_properties.get("oil_b_factor", "")))
        self.ui.min_dec_oil.setText(str(self.default_properties.get("min_dec_oil", "")))
        self.ui.ecl_date.setDateTime(QDateTime.fromString(self.default_properties.get("economic_limit_date", QDateTime.currentDateTime().toString("yyyy-MM-dd")), "yyyy-MM-dd"))
        self.ui.oil_price.setText(str(self.default_properties.get("oil_price", "")))
        self.ui.gas_price.setText(str(self.default_properties.get("gas_price", "")))
        self.ui.oil_price_dif.setText(str(self.default_properties.get("oil_price_dif", "")))
        self.ui.gas_price_dif.setText(str(self.default_properties.get("gas_price_dif", "")))
        #self.ui.discount_rate_input.setText(str(self.default_properties.get("discount_rate", "")))
        self.ui.working_interest.setText(str(working_interest))
        self.ui.royalty.setText(str(royalty))
        self.ui.discount_rate.setText(str(self.default_properties.get("discount_rate", "")))
        self.ui.tax_rate.setText(str(self.default_properties.get("tax_rate", "")))
        self.ui.capital_expenditures.setText(str(self.default_properties.get("capital_expenditures", "")))
        self.ui.operating_expenditures.setText(str(self.default_properties.get("operating_expenditures", "")))
        self.ui.net_price_oil.setText(str(self.default_properties.get("net_price_oil", "")))
        self.ui.net_price_gas.setText(str(self.default_properties.get("net_price_gas", "")))

    def decline_analysis(self):
 
        model_properties = ModelProperties(self.combined_df)
        self.decline_curves = model_properties.dca_model_properties(self.default_properties)
        self.model_data = model_properties.model_data
        self.model_data_df = pd.DataFrame(self.model_data)

         
        self.dca = DeclineCurveAnalysis(self.combined_df, self.model_data, self.iterate_di, self.UWI_list)
        self.prod_rates_all, self.sum_of_errors, self.model_data = self.dca.calculate_production_rates()
        self.model_data_df = pd.DataFrame(self.model_data)
       #printself.model_data)
 

     
        self.sum_of_errors.iloc[:, 1:] = self.sum_of_errors.iloc[:, 1:].round(2)
        
        # Ensure database manager is initialized and connected
        if self.db_manager:
            self.db_manager.connect()  # Ensure connection is open
            self.scenario_name = "Active_Wells"
            self.db_manager.insert_scenario_name(self.scenario_name, True)
            self.scenario_id = self.db_manager.get_scenario_id(self.scenario_name)
            self.scenario_names = self.db_manager.get_all_scenario_names()
           #printself.scenario_id, self.scenario_name)


            self.db_manager.prod_rates_all(self.prod_rates_all, 'prod_rates_all', self.scenario_id)
            self.db_manager.store_model_data(self.model_data_df, self.scenario_id)
            self.db_manager.store_sum_of_errors_dataframe(self.sum_of_errors, self.scenario_id)
            
            
                # Close the connection after the operation
        
        self.eur_npv = EurNpv(self.db_manager, self.db_path)        
        self.eur_npv.calculate_eur()
        self.eur_npv.calculate_npv_and_efr()
        self.update_displays()
        




    def update_displays(self):
       #printself.scenario_id)
        self.ui.activate_icons()
        self.db_manager.connect() 
        self.iterate_di = False
        if not self.current_UWI_index:
            self.current_UWI = self.UWI_list[0]
        self.current_UWI = self.UWI_list[self.current_UWI_index]
       #printself.current_UWI)
        
        self.UWI_prod_rates_all = self.db_manager.retrieve_prod_rates_all(self.current_UWI, self.scenario_id)
        print(self.UWI_prod_rates_all)
        self.model_data = self.db_manager.retrieve_model_data_by_scenorio(self.scenario_id)
        self.update_excel_widget()
        self.model_parameters()
        self.populate_well_dropdown()
        self.populate_scenario_dropdown_tab1()
        self.update_graph()
        self.db_manager.disconnect() 

        
    def update_excel_widget(self):
        # Clear previous content
        self.ui.excel_widget.clearContents()

        if self.UWI_prod_rates_all.empty:
            print("No data available to update Excel widget.")
            return

        # Set the number of rows and columns dynamically
        self.ui.excel_widget.setRowCount(len(self.UWI_prod_rates_all))
        self.ui.excel_widget.setColumnCount(len(self.UWI_prod_rates_all.columns))

        # Set column headers dynamically
        self.ui.excel_widget.setHorizontalHeaderLabels(self.UWI_prod_rates_all.columns)

        # Populate the Excel widget with data
        for row_index, (_, row_data) in enumerate(self.UWI_prod_rates_all.iterrows()):
            for col_index, column in enumerate(self.UWI_prod_rates_all.columns):
                value = row_data[column]
                item = QTableWidgetItem()

                # Ensure date stays as a string
                if "date" in column.lower():
                    item.setData(Qt.DisplayRole, str(value))

                # Ensure no scientific notation for numeric values
                elif isinstance(value, (int, float)):
                    formatted_value = f"{value:.10f}".rstrip("0").rstrip(".")
                    item.setData(Qt.EditRole, formatted_value)

                else:
                    item.setData(Qt.DisplayRole, str(value) if value is not None else "")

                self.ui.excel_widget.setItem(row_index, col_index, item)

        # Resize rows and columns to fit content
        self.ui.excel_widget.resizeRowsToContents()
        self.ui.excel_widget.resizeColumnsToContents()

        # Sort by date column if it exists
        if "date" in self.UWI_prod_rates_all.columns:
            self.ui.excel_widget.sortItems(self.UWI_prod_rates_all.columns.get_loc("date"))

        print("Excel Updated")




    def on_tab_changed(self, index):
        print(index)
        self.tab_index = index
        # Assuming Tab 2 is at index 1
        if index == 1:
            self.populate_scenario_dropdown_tab2()
        elif index == 2:
            self.populate_scenario_dropdown_tab3()



    def on_scenario_changed_tab1(self):
        self.scenario_name = self.ui.scenario_dropdown1.currentText()
        self.scenario_id = self.db_manager.get_scenario_id(self.scenario_name)
        self.UWI_list = self.db_manager.get_UWIs_by_scenario_id(self.scenario_id)

        # Reset the current index and UWI
        if self.UWI_list:
            self.ui.well_dropdown.setEnabled(bool(self.UWI_list))
            self.current_UWI_index = 0  # Start at the beginning of the list
            self.current_UWI = self.UWI_list[0]

            # Populate the well dropdown
            self.populate_well_dropdown()

            # Perform the updates only if UWI_list is not empty
            self.update_displays()
            self.update_navigation_buttons()
            self.check_model_status_and_set_icon()
        else:
            self.current_UWI_index = -1
            self.current_UWI = None
            QMessageBox.information(self, "No Wells", "No wells available for the selected scenario.")
            # Clear the graph
            self.ui.graph_area.setHtml("<html><body><h1>No Data Available</h1></body></html>")
            # Clear the well dropdown
            self.ui.well_dropdown.blockSignals(True)
            self.ui.well_dropdown.clear()
            self.ui.well_dropdown.blockSignals(False)


    def on_scenario_changed2(self):
                #print(df_UWI_model_data)
        #print(df_UWI_model_data.dtypes)
        self.scenario_name = self.ui.scenario_dropdown2.currentText()
        self.scenario_id = self.db_manager.get_scenario_id(self.scenario_name)
        self.model_data = self.db_manager.retrieve_model_data_by_scenario(self.scenario_id)
        #print(self.model_data)
        self.populate_scenario_dropdown_tab1()
        self.populate_tab_2()  

    def on_scenario_changed3(self):

        self.scenario_name = self.ui.scenario_dropdown3.currentText()
        self.scenario_id = self.db_manager.get_scenario_id(self.scenario_name)
        
        
        self.populate_scenario_dropdown_tab3()

    def on_scenario_changed4(self):

        self.scenario_name = self.ui.scenario_dropdown4.currentText()
        self.scenario_id = self.db_manager.get_scenario_id(self.scenario_name)
        
        self.populate_well_pads_table()  
        self.populate_scenario_dropdown_tab1()

    def populate_scenario_dropdown_tab1(self):
        self.ui.scenario_dropdown1.blockSignals(True)  # Temporarily block signals
        self.ui.scenario_dropdown1.clear()
     
        self.model_data = self.db_manager.retrieve_model_data_by_scenario(self.scenario_id)

        for scenario in self.scenario_names:
            self.ui.scenario_dropdown1.addItem(scenario)

        self.ui.scenario_dropdown1.setCurrentText(self.scenario_name)
        
    
        self.ui.scenario_dropdown1.blockSignals(False)

    def populate_scenario_dropdown_tab2(self):
        self.ui.scenario_dropdown2.blockSignals(True)  # Temporarily block signals
        self.ui.scenario_dropdown2.clear()
        
    
        for scenario in self.scenario_names:
            self.ui.scenario_dropdown2.addItem(scenario)

        self.ui.scenario_dropdown2.setCurrentText(self.scenario_name)
       #printself.scenario_name)
 
        self.ui.scenario_dropdown2.blockSignals(False)
        self.populate_tab_2()

    def populate_scenario_dropdown_tab3(self):
            self.ui.scenario_dropdown3.blockSignals(True)  # Temporarily block signals
            self.ui.scenario_dropdown3.clear()
        
    
            for scenario in self.scenario_names:
                self.ui.scenario_dropdown3.addItem(scenario)

            self.ui.scenario_dropdown3.setCurrentText(self.scenario_name)
           #printself.scenario_name)
 
            self.ui.scenario_dropdown3.blockSignals(False)
            self.updateTable3()
     



    def populate_tab_2(self):
        # print("pop2 start")
        self.ui.model_properties.blockSignals(True)

        try:
            if not self.model_data:
                print("No data available to populate tab 2.")
                self.ui.model_properties.clearContents()
                return

            # Dynamically determine headers from the first dictionary in the dataset
            headers = list(self.model_data[0].keys()) if self.model_data else []

            # Clear existing data
            self.ui.model_properties.clearContents()

            # Set headers dynamically
            self.ui.model_properties.setColumnCount(len(headers))
            self.ui.model_properties.setHorizontalHeaderLabels(headers)

            # Set row count based on the number of entries in model_data
            self.ui.model_properties.setRowCount(len(self.model_data))

            # Populate table with data
            for row_index, row_data in enumerate(self.model_data):
                for col_index, header in enumerate(headers):
                    col_data = row_data.get(header, "")
                    item = QTableWidgetItem()

                    # Handle UWI as a string to prevent numeric conversion
                    if header == "UWI":
                        item.setData(Qt.EditRole, str(col_data))

                    # Handle dates, model names, and types as strings
                    elif "date" in header or "model" in header or "type" in header:
                        item.setData(Qt.DisplayRole, str(col_data))

                    else:
                        try:
                            numeric_value = float(col_data)

                            # Ensure no scientific notation & limit to 2 decimal places
                            formatted_value = f"{numeric_value:.2f}"
                            item.setData(Qt.EditRole, formatted_value)

                        except (ValueError, TypeError):
                            item.setData(Qt.DisplayRole, str(col_data))

                    self.ui.model_properties.setItem(row_index, col_index, item)

            # Adjust row height and column width for better readability
            for i in range(self.ui.model_properties.rowCount()):
                self.ui.model_properties.setRowHeight(i, 30)  # Adjust row height as needed

            for i in range(self.ui.model_properties.columnCount()):
                self.ui.model_properties.setColumnWidth(i, 100)  # Adjust column width as needed

            # Enable sorting after populating the table
            self.ui.model_properties.setSortingEnabled(False)

            # Sort by UWI initially or use the last sorted column and order
            if hasattr(self, "last_sorted_column") and hasattr(self, "last_sort_order"):
                self.ui.model_properties.sortItems(self.last_sorted_column, self.last_sort_order)

            self.ui.model_properties.blockSignals(False)
        except Exception as e:
            import traceback
            print("Error populating tab 2:", e)
            traceback.print_exc()

        print("pop2 end")



    def show_context_menu(self, position):
        """
        Show context menu for the model properties table when right-clicked.
        """
        context_menu = QMenu(self)
        save_decline_action = context_menu.addAction("Save Decline Curve Parameters")
    
        action = context_menu.exec_(self.ui.model_properties.viewport().mapToGlobal(position))
    
        if action == save_decline_action:
            # Collect UWIs from all selected rows
            selected_UWIs = []
            selected_ranges = self.ui.model_properties.selectedRanges()
        
            for selected_range in selected_ranges:
                for row in range(selected_range.topRow(), selected_range.bottomRow() + 1):
                    UWI_item = self.ui.model_properties.item(row, 0)  # UWI is in first column
                    if UWI_item and UWI_item.text():
                        selected_UWIs.append(UWI_item.text())
        
            if selected_UWIs:
                # Call save_dc with context menu parameters
                self.save_dc(from_context_menu=True, selected_UWIs=selected_UWIs)


    def updateTable3(self):
            # Clear the current data and sorting in the table
        self.ui.data_table3.clear()
        self.ui.data_table3.setSortingEnabled(False)
        selected_option = self.ui.data_type_dropdown3.currentText()
        if selected_option == "Gas Production":
            self.populate_table3("q_gas")
        elif selected_option == "Oil Production":
            self.populate_table3("q_oil")
        elif selected_option == "Total Revenues":
            self.populate_table3("total_revenue")
    def populate_table3(self, *columns):
        # Retrieve aggregated production rates data
        self.prod_rates_ag = pd.DataFrame()
       

        if self.scenario_id == 1:
            self.ui.include_active_wells_checkbox.setEnabled(False)
            self.ui.include_active_wells_checkbox.setChecked(False) 
        else:
            self.ui.include_active_wells_checkbox.setEnabled(True)

        include_active_wells = self.ui.include_active_wells_checkbox.isChecked()

        try:
            self.prod_rates_ag = pd.DataFrame()
            prod_rates_active = pd.DataFrame()  # Initialize an empty DataFrame
            if include_active_wells:
                # Assuming scenario_id 1 corresponds to active wells
                prod_rates_active = self.db_manager.retrieve_aggregated_prod_rates(columns, 1)

            self.prod_rates_ag = self.db_manager.retrieve_aggregated_prod_rates(columns, self.scenario_id)
        
            if not prod_rates_active.empty:
                self.prod_rates_ag = pd.concat([self.prod_rates_ag, prod_rates_active], ignore_index=True)
        
            print(self.prod_rates_ag)
        except Exception as e:
            print(f"Failed to retrieve data: {e}")
            return

        # Ensure the 'date' column is in datetime format and normalize to remove time components
        self.prod_rates_ag['date'] = pd.to_datetime(self.prod_rates_ag['date']).dt.normalize()

        # Ensure UWI is treated as a string
        self.prod_rates_ag['UWI'] = self.prod_rates_ag['UWI'].astype(str)

        # Extract unique UWIs and determine the min and max dates
        unique_UWIs = self.prod_rates_ag['UWI'].unique()

        min_date = pd.Timestamp.today().normalize()  # Current date normalized
        max_date = self.prod_rates_ag['date'].max()

        # Generate a list of all months between min_date and max_date
        date_range = pd.date_range(start=min_date, end=max_date, freq='MS').normalize()
        date_labels = [date.strftime('%b %Y') for date in date_range]

        # Filter the dates to only include from the current month onwards
        date_range = [date for date in date_range if date >= min_date]

        # Clear the current data and sorting in the table
        self.ui.data_table3.clear()
        self.ui.data_table3.setSortingEnabled(False)

        # Define the bold font for headers
        header_font = QFont()
        header_font.setBold(True)
        header_font.setPointSize(10)

        # Update the horizontal and vertical headers
        self.ui.data_table3.setColumnCount(len(date_range) + 2)  # +2 for UWI and Total columns
        self.ui.data_table3.setRowCount(len(unique_UWIs) + 1)  # +1 for totals row

        # Set the horizontal header labels
        header_labels = ["UWI", "NPV"] + date_labels
        self.ui.data_table3.setHorizontalHeaderLabels(header_labels)

        # Set font for "UWI" and "Total" headers
        for i in range(2):
            item = self.ui.data_table3.horizontalHeaderItem(i)
            if item:
                item.setFont(header_font)

        # Create a pivoted DataFrame for each column and fill NaN with 0
        pivoted_data = {column: self.prod_rates_ag.pivot(index='UWI', columns='date', values=column).fillna(0) for column in columns}

        # Ensure pivoted data indices are strings
        for column in columns:
            pivoted_data[column].index = pivoted_data[column].index.astype(str)

        # Initialize arrays to store row totals and grand total
        row_totals = np.zeros(len(unique_UWIs))
        column_totals = np.zeros(len(date_range))

        # Populate the QTableWidget with well data and calculate totals
        for row, UWI in enumerate(unique_UWIs, start=1):
            UWI = str(UWI)

            if UWI not in pivoted_data[columns[0]].index:
                continue

            # UWI
            UWI_item = QTableWidgetItem(UWI)
            self.ui.data_table3.setItem(row, 0, UWI_item)

            # Fetch row data for all dates and columns at once
            row_data = sum(pivoted_data[column].loc[UWI, date_range].values for column in columns)
            row_totals[row - 1] = row_data.sum()
            column_totals += row_data

            for col, value in enumerate(row_data, start=2):
                cell_item = NumericTableWidgetItem(value)
                self.ui.data_table3.setItem(row, col, cell_item)

            total_item = NumericTableWidgetItem(row_totals[row - 1])
            total_item.setFont(header_font)
            self.ui.data_table3.setItem(row, 1, total_item)

        # Populate the totals row
        total_label_item = QTableWidgetItem("TOTALS")
        total_label_item.setFont(header_font)
        self.ui.data_table3.setItem(0, 0, total_label_item)

        for col, total in enumerate(column_totals, start=2):
            total_sum_item = NumericTableWidgetItem(total)
            total_sum_item.setFont(header_font)
            self.ui.data_table3.setItem(0, col, total_sum_item)

        # Total for all wells
        grand_total = row_totals.sum()
        grand_total_item = NumericTableWidgetItem(grand_total)
        grand_total_item.setFont(header_font)
        self.ui.data_table3.setItem(0, 1, grand_total_item)

        # Enable sorting
        self.ui.data_table3.setSortingEnabled(True)

        # Sort by the "Total" column by default in descending order
        self.ui.data_table3.sortItems(1, order=Qt.DescendingOrder)

        # Force update to ensure the table redraws correctly
        self.ui.data_table3.viewport().update()

        # Generate and display the plot
        html_content = plot_totals(date_labels, column_totals)
    
        with open("plot.html", "w") as file:
            file.write(html_content)    

        self.ui.graph_area3.setHtml(html_content)


    def populate_well_pads_table(self):
        try:
            self.ui.well_pads_table.blockSignals(True)
            self.ui.well_pads_table.clear()


            active_scenario_well_pad_ids = []
            date_map = {}
            decline_curve_map = {}

            if self.scenario_id:
                # Fetch all scenario details for the active scenario ID
                all_scenario_details = self.db_manager.get_scenario_details(self.scenario_id)
                #print(all_scenario_details)

                if all_scenario_details:
                    # Populate mappings for well_pad_id, start_date, and decline_curve_id
                    for scenario in all_scenario_details:
                        well_pad_id = scenario.get('well_pad_id', '')
                        if well_pad_id:
                            active_scenario_well_pad_ids.append(well_pad_id)
                            date_map[well_pad_id] = scenario.get('start_date', '')
                            decline_curve_id = scenario.get('decline_curve_id', '')
                            decline_curve_map[well_pad_id] = self.db_manager.get_decline_curve_name(decline_curve_id)

            well_pads = self.db_manager.get_well_pads()

            self.ui.well_pads_table.setRowCount(len(well_pads))
            columns = [
                'Pad Name', 'Start Date', 'Decline Curve', 'Total Lateral', 'Total Capex Cost',
                'Total Opex Cost', 'Num Wells', 'Drill Time', 'Prod Type', 'Oil Model Status',
                'Gas Model Status', 'Pad Cost', 'Exploration Cost', 'Cost Per Foot', 'Distance To Pipe',
                'Cost Per Foot To Pipe'
            ]

            self.ui.well_pads_table.setColumnCount(len(columns))
            self.ui.well_pads_table.setHorizontalHeaderLabels(columns)

            # Create a ComboBox delegate for the "Decline Curve" column
            decline_curve_names = self.db_manager.get_decline_curve_names()
            decline_curve_delegate = ComboBoxDelegate(self.ui.well_pads_table)
            decline_curve_delegate.setDeclineCurveNames(decline_curve_names)
            self.ui.well_pads_table.setItemDelegateForColumn(2, decline_curve_delegate)

            for row_idx, pad in enumerate(well_pads):
                # Set the Original Name in the first column
                self.ui.well_pads_table.setItem(row_idx, 0, QTableWidgetItem(str(pad['original_name'])))

                # Add date and decline curve to the correct well pad row if IDs match
                if pad['id'] in active_scenario_well_pad_ids:
                    self.ui.well_pads_table.setItem(row_idx, 1, QTableWidgetItem(date_map.get(pad['id'], '')))
                    self.ui.well_pads_table.setItem(row_idx, 2, QTableWidgetItem(str(decline_curve_map.get(pad['id'], ''))))
                else:
                    self.ui.well_pads_table.setItem(row_idx, 1, QTableWidgetItem(''))
                    self.ui.well_pads_table.setItem(row_idx, 2, QTableWidgetItem(''))

                # Set the rest of the values in the appropriate columns
                col_idx = 3
                for key in [
                    'total_lateral', 'total_capex_cost', 'total_opex_cost', 'drill_time',
                    'prod_type', 'oil_model_status', 'gas_model_status', 'pad_cost', 'exploration_cost',
                    'cost_per_foot', 'distance_to_pipe', 'cost_per_foot_to_pipe'
                ]:
                    value = pad.get(key, '')
                    self.ui.well_pads_table.setItem(row_idx, col_idx, QTableWidgetItem(str(value)))
                    col_idx += 1

            # Set the custom date delegate for the "Start Date" column (index 1)
            try:
                date_delegate = DateDelegate(self.ui.well_pads_table)
                self.ui.well_pads_table.setItemDelegateForColumn(1, date_delegate)
                print("Date delegate set successfully.")
            except Exception as e:
                print(f"Error setting date delegate: {e}")
        
        except Exception as e:
            print(f"Error populating well pads table: {e}")
        finally:
            print('hi')
            self.ui.well_pads_table.blockSignals(False)
    def on_table_item_changed(self, item):
        if self.scenario_name == "Active_Wells":
            # Display a warning message
            QMessageBox.warning(self, "Warning", "Adding plans to the 'Active_Wells' scenario is not allowed.")
            self.ui.well_pads_table.blockSignals(True)  # Block signals to prevent recursion
            item.setText("")  # Clear the cell content
            self.ui.well_pads_table.blockSignals(False)
            return  # Exit the function without storing anything
        else: 
            # Handle changes in the table
            self.edited_rows.clear()
            row = item.row()
            column = item.column()
            new_value = item.text()
            print(row)
            # Store the edited row
            if row not in self.edited_rows:
                self.edited_rows.append(row)
            # print("ROW", self.edited_rows)
            self.update_scenario()


    def on_model_properties_item_changed(self, item):
        # Handle changes in the table
        row = item.row()
        new_value = item.text()
       # print(f"Row: {row}, New Value: {new_value}")

        # Store the edited row index if it is not already in the list
        if row not in self.edited_model_rows:
            self.edited_model_rows.append(row)
       # print("Edited Rows:", self.edited_model_rows)

    def model_table_update(self):
        headers = [
            "UWI", "max_oil_production", "max_gas_production", "max_oil_production_date", "max_gas_production_date",
            "one_year_oil_production", "one_year_gas_production", "di_oil", "di_gas", "oil_b_factor", "gas_b_factor",
            "min_dec_oil", "min_dec_gas", "model_oil", "model_gas", "oil_price", "gas_price", "oil_price_dif", "gas_price_dif",
            "discount_rate", "working_interest", "royalty", "tax_rate", "capital_expenditures", "operating_expenditures",
            "economic_limit_type", "economic_limit_date", "net_price_oil", "net_price_gas", "gas_model_status", "oil_model_status"
        ]
    
        for row in self.edited_model_rows:
            # Extract data from the row
            row_data = {}
            for col, header in enumerate(headers):
                item = self.ui.model_properties.item(row, col)
                row_data[header] = item.text() if item is not None else None
            
            # Create a DataFrame from the row data
            df_model_properties = pd.DataFrame([row_data])
            UWI = df_model_properties['UWI'].iloc[0]
            status = self.db_manager.get_UWI_status(UWI)
           # print(status)
            # Update the model properties with the retrieved DataFrame
            self.db_manager.update_model_properties(df_model_properties, self.scenario_id)
        
            

            # Retrieve the updated model properties
            updated_model_df = self.db_manager.retrieve_model_data_by_scenario_and_UWI(self.scenario_id, row_data['UWI'])


            # Run planned production rate calculations
            if status == False:
                iterate = False
                self.UWI_combined_df = self.db_manager.retrieve_prod_rates_by_UWI(UWI)
                self.UWI_production_rates_data, self.UWI_error, self.UWI_model_data = self.dca.update_prod_rate(updated_model_df, self.UWI_combined_df, iterate)
                self.UWI_error = self.dca.UWI_error
            else:
                self.UWI_production_rates_data, self.UWI_error, self.UWI_model_data = self.dca.planned_prod_rate(updated_model_df)
        
        # Clear the edited rows after updating
        self.edited_model_rows.clear()
        self.update_db()
        self.eur_npv = EurNpv(self.db_manager, self.db_path)
        self.eur_npv.calculate_eur()
        self.eur_npv.calculate_npv_and_efr()
       
        self.update_displays()
        print("Model properties updated for all edited rows.")


    def scenario_active(self):

        current_scenario_name = self.ui.scenario_dropdown.currentText()
        active_scenario_id = self.db_manager.get_scenario_id(current_scenario_name)
        self.db_manager.set_active_scenario(active_scenario_id)



 



    def on_header_clicked(self, logicalIndex):
        current_order = self.ui.model_properties.horizontalHeader().sortIndicatorOrder()
        self.ui.model_properties.sortItems(logicalIndex, current_order)
        self.last_sorted_column = logicalIndex
        self.last_sort_order = current_order


    def calculate_net_price(self):
        try:
            # Get tax rate and operating expenditures from QLineEdit widgets
            royalty = float(self.royalty.text())
            working_interest = float(self.working_interest.text())
            nri = working_interest/100*(1-royalty/100)
            oil_price = float(self.oil_price.text())
            gas_price = float(self.gas_price.text())
            oil_price_dif = float(self.oil_price_dif.text())
            gas_price_dif = float(self.gas_price_dif.text())
            tax_rate = float(self.tax_rate.text())
            net_price_oil = float(nri*(oil_price - oil_price_dif)*(1-tax_rate/100)*(1-royalty/100))
            net_price_gas = float(nri*(gas_price - gas_price_dif)*(1-tax_rate/100)*(1-royalty/100))


            # Update QLabel with calculated net price
            self.ui.net_price_oil.setText(f"{net_price_oil:.2f}")
            self.ui.net_price_gas.setText(f"{net_price_gas:.2f}")

        except ValueError:

            pass  # Handle invalid input

    def model_parameters(self):
        # Get current UWI index
        self.db_manager = DatabaseManager(self.db_path)
        self.db_manager.connect()

        self.UWI_model_data = self.db_manager.retrieve_model_data_by_scenario_and_UWI( self.scenario_id, self.current_UWI)
        print(self.UWI_model_data)
       #printself.UWI_model_data)

        self.current_error_row = self.db_manager.retrieve_error_row(self.current_UWI, self.scenario_id)
        print(self.current_error_row)
 

        initial_gas_prod_rate = float(self.UWI_model_data['max_gas_production'])
        self.ui.initial_gas_production_rate_input.setText(str(initial_gas_prod_rate))
        initial_gas_decline_rate = float(self.UWI_model_data['di_gas'])
        self.ui.initial_gas_decline_rate_input.setText(str(initial_gas_decline_rate))
        gas_b_factor = float(self.UWI_model_data['gas_b_factor'])
        self.ui.gas_b_factor_input.setText(str(gas_b_factor))
    
        #gas_hyperbolic_exponent = current_data.get('hyperbolic_exponent_gas', 0.5)  # Default to 0.5 if not available
        #self.ui.gas_hyperbolic_exponent_input.setText(str(gas_hyperbolic_exponent))

        gas_start_date = self.UWI_model_data['max_gas_production_date'].iloc[0] 
        
        # Parse the string date into a datetime object
        gas_start_datetime = datetime.strptime(gas_start_date, '%Y-%m-%d')
      
        # Extract the date part from the datetime object
        gas_start_date_only = gas_start_datetime.date()

        # Now create the QDate object
        gas_start_qdate = QDate(gas_start_date_only)
        self.ui.gas_time_input.setDate(gas_start_qdate)

        min_dec_gas = float(self.UWI_model_data['min_dec_gas'])
        self.ui.min_dec_gas.setText(str(min_dec_gas))



        # Set oil parameters
        initial_oil_prod_rate = float(self.UWI_model_data['max_oil_production'])
        self.ui.initial_oil_production_rate_input.setText(str(initial_oil_prod_rate))

        oil_start_date = self.UWI_model_data['max_oil_production_date'].iloc[0] 
        
        # Parse the string date into a datetime object
        oil_start_datetime = datetime.strptime(oil_start_date, '%Y-%m-%d')

        # Extract the date part from the datetime object
        oil_start_date_only = oil_start_datetime.date()

        # Now create the QDate object
        oil_start_qdate = QDate(oil_start_date_only)
        self.ui.oil_time_input.setDate(oil_start_qdate)


        initial_oil_decline_rate = float(self.UWI_model_data['di_oil'])
        self.ui.initial_oil_decline_rate_input.setText(str(initial_oil_decline_rate))

        oil_b_factor = float(self.UWI_model_data['oil_b_factor'])
        self.ui.oil_b_factor_input.setText(str(oil_b_factor))

        min_dec_oil = float(self.UWI_model_data['min_dec_oil'])
        self.ui.min_dec_oil.setText(str(min_dec_oil))

 
        
        try:
            if self.current_error_row is None or self.current_error_row.empty:
                print("Error: current_error_row is None or empty.")
                self.ui.error_oil.setText("N/A")  # Optional: Set a default value
                return

            if 'sum_error_oil' not in self.current_error_row:
                print("Error: 'sum_error_oil' column not found in current_error_row.")
                self.ui.error_oil.setText("N/A")  # Optional: Set a default value
                return

            sum_error_oil_values = self.current_error_row['sum_error_oil'].values
            if len(sum_error_oil_values) == 0:
                print("Error: 'sum_error_oil' has no values.")
                self.ui.error_oil.setText("N/A")  # Optional: Set a default value
                return

            sum_error_oil_value = round(sum_error_oil_values[0], 2)
            self.ui.error_oil.setText(str(sum_error_oil_value))
        except Exception as e:
            print(f"Unexpected error: {e}")
            self.ui.error_gas.setText("Error")  # Optional: Set an error indicator

        try:
            if self.current_error_row is None or self.current_error_row.empty:
                print("Error: current_error_row is None or empty.")
                self.ui.error_gas.setText("N/A")  # Optional: Set a default value
                return

            if 'sum_error_gas' not in self.current_error_row:
                print("Error: 'sum_error_gas' column not found in current_error_row.")
                self.ui.error_gas.setText("N/A")  # Optional: Set a default value
                return

            current_error_gas_values = self.current_error_row['sum_error_gas'].values
            if len(current_error_gas_values) == 0:
                print("Error: 'sum_error_gas' has no values.")
                self.ui.error_gas.setText("N/A")  # Optional: Set a default value
                return

            current_error_gas = round(current_error_gas_values[0], 2)
            self.ui.error_gas.setText(str(current_error_gas))
            # print("Error calculated successfully.")  # Uncomment for debugging
        except Exception as e:
            print(f"Unexpected error: {e}")
            self.ui.error_gas.setText("Error")  # Optional: Set an error indicator


        if self.open:

            # Set values for each parameter
            economic_limit_type = self.UWI_model_data.get("economic_limit_type", "").iloc[0]

            if economic_limit_type == "Net Dollars":  # Economic Limit selected
                self.ui.ecl_date.setEnabled(False)  # Disable date input
            elif economic_limit_type == "End Date":  # Date selected
                self.ui.ecl_date.setEnabled(True)   # Enable date input
            elif economic_limit_type == "GOR":  # Another option, for example
                self.ui.ecl_date.setEnabled(False)  # Adjust as needed for GOR
            self.ui.end_forecast_type.setCurrentText(economic_limit_type)

            economic_limit_date_value = self.UWI_model_data.get("economic_limit_date", QDateTime.currentDateTime().toString("yyyy-MM-dd"))
            economic_limit_date_str = str(economic_limit_date_value)
            self.ui.ecl_date.setDateTime(QDateTime.fromString(economic_limit_date_str, "yyyy-MM-dd"))


            self.ui.oil_price.setText(str(self.UWI_model_data.get("oil_price", "").iloc[0]))
            self.ui.gas_price.setText(str(self.UWI_model_data.get("gas_price", "").iloc[0]))
            self.ui.oil_price_dif.setText(str(self.UWI_model_data.get("oil_price_dif", "").iloc[0]))
            self.ui.gas_price_dif.setText(str(self.UWI_model_data.get("gas_price_dif", "").iloc[0]))
            #self.ui.discount_rate_input.setText(str(current_data.get("discount_rate", "")))
            self.ui.working_interest.setText(str(self.UWI_model_data.get("working_interest", "").iloc[0]))
            self.ui.royalty.setText(str(self.UWI_model_data.get("royalty", "").iloc[0]))
            self.ui.discount_rate.setText(str(self.UWI_model_data.get("discount_rate", "").iloc[0]))
            self.ui.tax_rate.setText(str(self.UWI_model_data.get("tax_rate", "").iloc[0]))
            self.ui.capital_expenditures.setText(str(self.UWI_model_data.get("capital_expenditures", "").iloc[0]))
            self.ui.operating_expenditures.setText(str(self.UWI_model_data.get("operating_expenditures", "").iloc[0]))
            self.ui.net_price_oil.setText(str(self.UWI_model_data.get("net_price_oil", "").iloc[0]))
            self.ui.net_price_gas.setText(str(self.UWI_model_data.get("net_price_gas", "").iloc[0]))





        print("parameters set")
             


    def update_graph(self):
        plotting = Plotting()
        plotting.generate_plot_html(self.UWI_prod_rates_all, self.current_UWI, self.graph_type, self.distribution_type, self.UWI_model_data)
        html_content = plotting.html_content
        self.ui.graph_area.setHtml(html_content)
        
 

#Upated Current Decline Curves and the models
    def update_decline_curve(self, di_oil=None, di_gas=None, iterate=False):


        self.ui.calculate_net_price()
        UWI_model_data = []
        # Get the current indexed UWI
        self.current_UWI = self.UWI_list[self.current_UWI_index]

        # Get model parameters from the UI
        max_oil_production = self.ui.initial_oil_production_rate_input.text()
        max_gas_production = self.ui.initial_gas_production_rate_input.text()
        min_dec_oil = self.ui.min_dec_oil.text()
        min_dec_gas = self.ui.min_dec_gas.text()
        max_oil_production_date = self.ui.oil_time_input.date().toString("yyyy-MM-dd")
        max_gas_production_date = self.ui.gas_time_input.date().toString("yyyy-MM-dd")

        di_oil = self.ui.initial_oil_decline_rate_input.text()
        di_gas = self.ui.initial_gas_decline_rate_input.text()
          
  

        oil_b_factor = self.ui.oil_b_factor_input.text()
        gas_b_factor = self.ui.gas_b_factor_input.text()


        # Get additional model parameters from the UI
        discount_rate = self.ui.discount_rate.text()
        working_interest = self.ui.working_interest.text()
        royalty = self.ui.royalty.text()
        oil_price = self.ui.oil_price.text()
        gas_price = self.ui.gas_price.text()
        oil_price_dif = self.ui.oil_price_dif.text()
        gas_price_dif = self.ui.gas_price_dif.text()
        tax_rate = self.ui.tax_rate.text()
        capital_expenditures = self.ui.capital_expenditures.text()
        operating_expenditures = self.ui.operating_expenditures.text()
        working_interest = float(working_interest)
        royalty = float(royalty)
        economic_limit_type = self.ui.end_forecast_type.currentText()
        economic_limit_date = self.ui.ecl_date.text()
        net_price_oil = self.ui.net_price_oil.text()
        net_price_gas = self.ui.net_price_gas.text()

        self.db_manager = DatabaseManager(self.db_path)
        self.db_manager.connect()
        oil_model_status = self.db_manager.get_model_status(self.current_UWI, 'oil')
        gas_model_status = self.db_manager.get_model_status(self.current_UWI, 'gas')

                # Create a dictionary with the model parameters
        # Create a dictionary with the model parameters
        updated_model_data = {
            'UWI': self.current_UWI,
            'max_oil_production': float(max_oil_production),
            'max_gas_production': float(max_gas_production),
            'max_oil_production_date': pd.to_datetime(max_oil_production_date),
            'max_gas_production_date': pd.to_datetime(max_gas_production_date),
            'di_oil': float(di_oil),
            'di_gas': float(di_gas),
            'oil_b_factor': float(oil_b_factor),
            'gas_b_factor': float(gas_b_factor),
            'min_dec_oil': float(min_dec_oil),
            'min_dec_gas': float(min_dec_gas),
            'discount_rate': float(discount_rate),
            'working_interest': float(working_interest),
            'royalty': float(royalty),
            'oil_price': float(oil_price),
            'gas_price': float(gas_price),
            'oil_price_dif': float(oil_price_dif),
            'gas_price_dif': float(gas_price_dif),
            'tax_rate': float(tax_rate),
            'capital_expenditures': float(capital_expenditures),
            'operating_expenditures': float(operating_expenditures),
            'economic_limit_type': economic_limit_type,
            'economic_limit_date': pd.to_datetime(economic_limit_date),
            'net_price_oil' : float(net_price_oil),
            'net_price_gas' : float(net_price_gas),
            'oil_model_status' : int(oil_model_status),
            'gas_model_status' : int(gas_model_status)
            
        }
        self.ui.calculate_net_price()
        UWI_model_data.append(updated_model_data)
     
        # Convert the list of dictionaries to a DataFrame
        df_UWI_model_data = pd.DataFrame(UWI_model_data)
       #printdf_UWI_model_data)
        
        self.db_manager = DatabaseManager(self.db_path)
        self.db_manager.connect()
        self.scenario_id = 1
        self.db_manager.update_model_properties(df_UWI_model_data, self.scenario_id)
        print(df_UWI_model_data)
        self.scenario_id = 1

        self.UWI_model_data  = self.db_manager.retrieve_model_data_by_scenario_and_UWI(self.scenario_id, self.current_UWI )
        print(self.UWI_model_data)



        current_UWI_status = self.db_manager.get_UWI_status(self.current_UWI)  # Get the status of the current UWI
       #printcurrent_UWI_status)
        if current_UWI_status == True:
            self.UWI_production_rates_data, self.UWI_error, self.UWI_model_data = self.dca.planned_prod_rate(self.UWI_model_data)
        else:
            self.UWI_combined_df = self.db_manager.retrieve_prod_rates_by_UWI(self.current_UWI)
            self.UWI_production_rates_data, self.UWI_error, self.UWI_model_data = self.dca.update_prod_rate(self.UWI_model_data, self.UWI_combined_df, iterate)
           
            self.db_manager.update_model_properties(self.UWI_model_data, self.scenario_id)
            self.UWI_error = self.dca.UWI_error


        #self.regenerate_html_for_UWI(self.current_UWI)
        self.update_db()
        self.eur_npv = EurNpv(self.db_manager, self.scenario_id) 
        self.eur_npv.calculate_eur()
        self.eur_npv.calculate_npv_and_efr()
        self.eur_npv.calculate_payback_months()
        self.update_displays()
        
        self.regenerated = False
            
    def update_db(self):
        self.db_manager = DatabaseManager(self.db_path)
        self.db_manager.connect()
        pd.set_option('display.max_rows', None)
        pd.set_option('display.max_columns', None)
    
        #df_UWI_model_data = pd.DataFrame([self.UWI_model_data], index=[0])


        #print(self.UWI_production_rates_data)
        self.db_manager.update_UWI_prod_rates(self.UWI_production_rates_data, self.scenario_id)
        

        self.db_manager.update_UWI_errors(self.UWI_error, self.scenario_id)
        
        #print(self.UWI_error)


    def iterate_curve(self):
        self.iterate = True
        self.update_decline_curve(iterate=True)
        self.iterate = False



    def set_graph_type(self):
        self.graph_type = self.ui.option1_dropdown.currentText()
        self.update_graph()


    def set_distribution_type(self):

        #print(self.distribution_type)
        if self.distribution_type == "Exponential":
            self.distribution_type = "Normal"
            icon_path = os.path.join(self.script_dir, "Icons", "noun-linear-4373759")
            self.ui.graph_type.setIcon(QIcon(icon_path))
        else:
           self.distribution_type = "Exponential"
           icon_path = os.path.join(self.script_dir, "Icons", "noun-exponential-function-5648634")
           self.ui.graph_type.setIcon(QIcon(icon_path))
        #print(self.distribution_type)
        self.update_graph()
    
        

    def gas_model(self):


    
        # Get the current status of the gas model from the database
        gas_model_status = int(self.db_manager.get_model_status(self.current_UWI, 'gas'))
    
        # Toggle the status
        new_status = 0 if gas_model_status == 1 else 1

    # Update the database with the new status
        self.db_manager.update_model_status(self.current_UWI, new_status, 'gas')

        
        icon_name = f"gas_{'on' if new_status == 1 else 'off'}"  # Assuming your icon names are "gas_on.png" and "gas_off.png"
        icon_path = os.path.join(self.script_dir, "Icons", f"{icon_name}.png")
        self.ui.gas_model.setIcon(QIcon(icon_path))
        self.update_decline_curve()

    def oil_model(self):
       oil_model_status = int(self.db_manager.get_model_status(self.current_UWI, 'oil'))

   
       # Convert to integers for consistent comparison
       oil_model_status = int(oil_model_status)
       new_status = 0 if oil_model_status == 1 else 1
   
       self.db_manager.update_model_status(self.current_UWI, new_status, 'oil')

       icon_name = f"oil_{'on' if new_status == 1 else 'off'}"
       icon_path = os.path.join(self.script_dir, "Icons", f"{icon_name}.png")
       self.ui.oil_model.setIcon(QIcon(icon_path))
       self.update_decline_curve()


    def delete_well(self):

        
    
        # Check if there are wells to delete
        if self.UWI_list:
            try:
                # Remove UWI from all relevant tables in the database
               #printself.current_UWI)
                self.db_manager.delete_UWI_records(self.current_UWI)

                # Remove UWI from UWI_list
                del self.UWI_list[self.current_UWI_index]

                 #Update current index and displays
                if self.current_UWI_index >= len(self.UWI_list):
                    self.current_UWI_index = len(self.UWI_list) - 1
                self.update_displays()
                self.update_navigation_buttons()

            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to delete well: {str(e)}", QMessageBox.Ok)

    def delete_pad(self):
        pass




    def check_model_status_and_set_icon(self):
       oil_status = int(self.db_manager.get_model_status(self.current_UWI, 'oil'))
       gas_status = int(self.db_manager.get_model_status(self.current_UWI, 'gas'))
   
       oil_icon = os.path.join(self.script_dir, "Icons", f"oil_{'on' if oil_status == 1 else 'off'}.png")
       gas_icon = os.path.join(self.script_dir, "Icons", f"gas_{'on' if gas_status == 1 else 'off'}.png") 

       self.ui.oil_model.setIcon(QIcon(oil_icon))
       self.ui.gas_model.setIcon(QIcon(gas_icon))


    def save_dc(self, from_context_menu=False, selected_UWIs=None):
        if from_context_menu and selected_UWIs:
            # Simplified dialog for context menu - only need name
            dialog = SaveDeclineCurveDialog(self, UWIs=selected_UWIs, from_context_menu=True)
            dialog.options.setCurrentText("Average")  # Force Average option
            dialog.options.setEnabled(False)  # Disable changing the option
        
            if dialog.exec_() == QDialog.Accepted:
                curve_name = dialog.get_curve_name()
                if not curve_name:
                    QMessageBox.warning(self, "No Curve Name", "Please provide a name for the decline curve.")
                    return
            
                # Process the average directly since we know that's what we want
                averaged_data = self.average_UWIs(selected_UWIs)
                self.db_manager.save_decline_curve_to_db(curve_name, averaged_data)
            
        else:
            # Original save_dc functionality
            dialog = SaveDeclineCurveDialog(self, UWIs=self.UWI_list)
            if dialog.exec_() == QDialog.Accepted:
                curve_name = dialog.get_curve_name()
                if not curve_name:
                    QMessageBox.warning(self, "No Curve Name", "Please provide a name for the decline curve.")
                    return
                selected_option = dialog.get_selected_option()
            
                if selected_option == "Current Well":
                    self.db_manager.save_decline_curve_to_db(curve_name, self.UWI_model_data)
                elif selected_option == "Average":
                    selected_UWIs = dialog.get_selected_UWIs()
                    if not selected_UWIs:
                        QMessageBox.warning(self, "No UWI Selected", "Please select at least one UWI to average.")
                        return
                    averaged_data = self.average_UWIs(selected_UWIs)
                    self.db_manager.save_decline_curve_to_db(curve_name, averaged_data)
                elif selected_option == "Manual":
                    manual_data = dialog.get_manual_data()
                    manual_df = pd.DataFrame([manual_data])
                    self.db_manager.save_decline_curve_to_db(curve_name, manual_df)

    def save_scenario(self):
        pass

    def delete_pad(self):

        pass
    
    def average_UWIs(self, selected_UWIs):
        if isinstance(self.model_data, list):
            self.model_data_df = pd.DataFrame(self.model_data)
        # Filter self.model_data based on the selected UWIs
        filtered_data = self.model_data_df[self.model_data_df['UWI'].isin(selected_UWIs)]

        
        # Check if filtered_data is empty
        if filtered_data.empty:
            QMessageBox.warning(self, "No Data", "No data found for the selected UWIs.")
            return pd.DataFrame()

        # Calculate the average for each column, ignoring non-numeric columns
        averaged_data = filtered_data.mean(numeric_only=True).to_frame().T
        
        # Convert the averaged data to a DataFrame
        averaged_df = pd.DataFrame(averaged_data)
        
        return averaged_df




    def set_well_type(self, value):
        pass
        #if value == "Planned":
        #    self.displayed_status = "Planned"
        #    # Fetch UWIs with planned status
        #    self.UWI_list = self.db_manager.get_UWIs_by_status("Planned")
        
        #    if not self.UWI_list:
        #        # Show a message box indicating no planned wells
        #        QMessageBox.information(self, "No Planned Wells", "No planned wells available. Switching to Active wells.")
        #        # Switch back to Active wells
        #        self.displayed_status = "Active"
        #        self.UWI_list = self.db_manager.get_UWIs_by_status("Active")
        #        # Disable the scenario dropdown for Active wells
        #        self.ui.option1_dropdown.setEnabled(False)
        #        self.ui.scenarios_dropdown1.setEnabled(False)
        #        self.ui.scenarios_dropdown1.setVisible(False)
        #        self.ui.well_type_dropdown.setCurrentText("Active")
        #        self.scenario_id = self.db_manager.get_active_scenario_id()
        #        self.scenario_name = self.db_manager.get_active_scenario_name()

        #    else:
        #        # Enable the necessary dropdowns and populate the scenario dropdown
        #        self.ui.option1_dropdown.setEnabled(True)
        #        self.ui.scenarios_dropdown1.setEnabled(True)
        #        self.ui.scenarios_dropdown1.setVisible(True)
        #        self.populate_scenario_dropdown_tab1()

        #        # Get the current scenario ID
        #        self.scenario_id = self.db_manager.get_scenario_id(self.ui.scenarios_dropdown1.currentText())
        #        # Filter wells based on the scenario ID
        #        self.UWI_list = self.db_manager.get_UWIs_by_scenario_id(self.scenario_id)
        #elif value == "Active":
        #    self.displayed_status = "Active"
        #    # Fetch UWIs with active status
        #    self.UWI_list = self.db_manager.get_UWIs_by_status("Active")
        #    # Disable the scenario dropdown for Active wells
        #    self.ui.option1_dropdown.setEnabled(False)
        #    self.ui.scenarios_dropdown1.setEnabled(False)
        #    self.ui.scenarios_dropdown1.setVisible(False)
        #    self.scenario_id = self.db_manager.get_active_scenario_id()
        #    self.scenario_name = self.db_manager.get_active_scenario_name()

        ## Enable or disable the well dropdown based on UWI list
        #self.ui.well_dropdown.setEnabled(bool(self.UWI_list))

        ## Reset the current index and UWI
        #if self.UWI_list:
        #    self.current_UWI_index = 0  # Start at the beginning of the list
        #    self.current_UWI = self.UWI_list[0]
        #else:
        #    self.current_UWI_index = -1
        #    self.current_UWI = None

        #self.update_displays()
        #self.update_navigation_buttons()
        #self.check_model_status_and_set_icon()




    def navigate_forward(self):
        
#Window Navigation
        #self.ui.disconnect_parameters_triggers(self)
        if self.current_UWI_index < len(self.UWI_list) - 1:
            self.current_UWI_index += 1
            self.update_displays()
            self.current_UWI = self.UWI_list[self.current_UWI_index]
            self.update_dropdown() 
            self.update_navigation_buttons()
            self.check_model_status_and_set_icon()

    def navigate_back(self):
        # Window Navigation
        # self.ui.disconnect_parameters_triggers(self)
        if self.current_UWI_index > 0:
            self.current_UWI_index -= 1
            self.update_displays()
            self.current_UWI = self.UWI_list[self.current_UWI_index]
            self.update_dropdown()
            self.update_navigation_buttons()
            self.check_model_status_and_set_icon()

    def update_navigation_buttons(self):
        # Check if at the first UWI
        if self.current_UWI_index == 0:
            self.ui.back_button.setEnabled(False)
        else:
            self.ui.back_button.setEnabled(True)

        # Check if at the last UWI
        if self.current_UWI_index >= len(self.UWI_list) - 1:

            
            self.ui.forward_button.setEnabled(False)
        else:
            self.ui.forward_button.setEnabled(True)


    def populate_well_dropdown(self):
        self.ui.well_dropdown.blockSignals(True)  # Temporarily block signals
        self.ui.well_dropdown.clear()
    
       #printself.UWI_list)
    
        # Add well names to the dropdown
        for well_name in self.UWI_list:
            self.ui.well_dropdown.addItem(str(well_name))
    
        # Find the index of self.current_UWI and set it
        if self.current_UWI in self.UWI_list:
            index = self.UWI_list.index(self.current_UWI)
            self.ui.well_dropdown.setCurrentIndex(index)
    
        self.ui.well_dropdown.blockSignals(False) 


    def on_well_selected(self, index):
        # Update the current UWI and index based on the selected item
        self.current_UWI_index = index
        self.current_UWI = self.UWI_list[index]
        self.update_displays()
        self.update_dropdown()
        self.update_navigation_buttons()
        self.check_model_status_and_set_icon()

    def update_dropdown(self):
        self.ui.well_dropdown.blockSignals(True)  # Temporarily block signals
        self.ui.well_dropdown.setCurrentText(self.current_UWI) 
        self.ui.well_dropdown.blockSignals(False) 



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

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
            self.update_decline_curve()

    def closeEvent(self, event):
        # Clean up any resources before closing the application
        if self.ui.graph_area.page():
            self.ui.graph_area.page().deleteLater()  # Delete the WebEnginePage object
        super().closeEvent(event)

    def show_help(self):
        # Display help information
        QMessageBox.information(self, "Help", "This is where help information about the Plotly graph goes.")

    def show_error_message(self, message):
        QMessageBox.critical(self, "Error", message)





if __name__ == "__main__":
    app = QApplication(sys.argv)
    main_window = MainWindow()
    main_window.show()
    sys.exit(app.exec_())