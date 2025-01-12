
import sys
import subprocess
import os
import pandas as pd
from PySide6.QtWidgets import (
    QApplication, QDialog, QHBoxLayout, QVBoxLayout, QPushButton, QMenuBar, 
    QMessageBox, QMainWindow, QTableWidgetItem, QFileDialog, QWidget, QInputDialog
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
from AddWell import AddWell


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
        self.uwi_df =[]
        self.model_data = [] 
        self.combined_df = None  # Assuming combined_df will be set later
        self.current_uwi_index = 0 
        self.uwi_list = [] 
        self.total_items = len(self.uwi_list)# Store the list of uwis
        self.current_uwi = None
        self.dialog_changed_flag = False
        self.prod_rates_errors = None
        self.prod_rates_all = None
        self.prod_rates_ag = None
        self.uwi_prod_and_rates = None
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
        self.html_content_by_uwi = {}
        self.project_name = None
        self.db_path = None
        self.last_directory_path = None
        self.model_data_df = pd.DataFrame()
        self.uwi_production_rates_data = pd.DataFrame()
        self.uwi_error = pd.DataFrame()
        self.db_manager = DatabaseManager(None)
        self.dca = DeclineCurveAnalysis()

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
        


    def eventFilter(self, obj, event):
        if event.type() == QEvent.KeyPress:
            if event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
                # Call the update_decline_curve method when Enter key is pressed
                self.update_decline_curve()
        return super().eventFilter(obj, event)



    def open_project(self):
        self.open = True
        # Initialize the file dialog with the default directory if available
        default_dir = self.get_last_directory()  # Use the newly defined method
        if not default_dir:
            default_dir = ""  # Fallback to the empty string if no directory is returned

        options = QFileDialog.Options()
        file_dialog = QFileDialog()
        file_dialog.setDirectory(default_dir)
        file_dialog.setNameFilter("Database Files (*.db)")
        file_dialog.setFileMode(QFileDialog.ExistingFile)
        if file_dialog.exec_():
            selected_files = file_dialog.selectedFiles()
            if selected_files:
                self.db_path = selected_files[0]
                directory = os.path.dirname(self.db_path)
                try:
                    self.db_manager = DatabaseManager(self.db_path)
                    self.db_manager.connect()
                    QMessageBox.information(self, "Project Opened", f"The project '{os.path.basename(self.db_path)}' has been opened successfully.", QMessageBox.Ok)
                    self.retrieve_data()
                    self.save_last_directory(directory)  # Save the directory of the opened file
                except Exception as e:
                    QMessageBox.critical(self, "Error", f"Failed to open project: {str(e)}", QMessageBox.Ok)
        else:
            print("Error: No database file selected.")



       
    def retrieve_data(self):
        if self.db_manager:
            self.db_manager.connect()
            self.scenario_id = self.db_manager.get_active_scenario_id()
            print(self.scenario_id)
            self.scenario_name = self.db_manager.get_active_scenario_name()
            self.prod_rates_all = self.db_manager.retrieve_prod_rates_all() 
            self.uwi_list  = self.db_manager.get_uwis_by_scenario_id(self.scenario_id)
            self.scenario_names = self.db_manager.get_all_scenario_names()
            self.ui.activate_icons()

            if self.uwi_list:
                self.ui.well_dropdown.setEnabled(bool(self.uwi_list))
                self.current_uwi_index = 0  # Start at the beginning of the list
                self.current_uwi = self.uwi_list[0]

                # Populate the well dropdown
                self.populate_well_dropdown()

                self.model_data = self.db_manager.retrieve_model_data_by_scenario(self.scenario_id)
                self.sum_of_errors = self.db_manager.retrieve_sum_of_errors()
                self.calculate_eur()
                self.calculate_npv_and_efr()
                
               #printself.uwi_list)
                
                
            else:
                self.current_uwi_index = -1
                self.current_uwi = None
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
        self.production_data = sorted(production_data, key=lambda x: (x['uwi'], x['date']))
        
        if production_data:
            load_productions = LoadProductions()
            self.combined_df, self.uwi_list = load_productions.prepare_data(production_data,self.db_path) 
            #print(self.combined_df)
            self.handle_default_parameters()
            self.ui.activate_icons() 
            self.decline_analysis()
            print('gafag',well_data_df)
            if not directional_survey_values.empty:

                self.db_manager.insert_survey_dataframe_into_db(directional_survey_values, )
                self.db_manager.save_uwi_data(well_data_df)
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

         
        self.dca = DeclineCurveAnalysis(self.combined_df, self.model_data, self.iterate_di, self.uwi_list)
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
        self.calculate_eur()
        self.calculate_npv_and_efr()
        

    def calculate_eur(self):
        self.db_manager = DatabaseManager(self.db_path)   
        # Retrieve production rates from the database
        self.db_manager = DatabaseManager(self.db_path)
        self.prod_rates_all = self.db_manager.retrieve_prod_rates_all()

        # Group by UWI and sum the production columns
        eur_df = self.prod_rates_all.groupby('uwi').agg(
            q_oil_eur=('q_oil', 'sum'),  # Sum of oil production
            q_gas_eur=('q_gas', 'sum')  # Sum of gas production
        ).reset_index()

        # Insert the EUR values for each UWI into the database or display
        for _, row in eur_df.iterrows():
            uwi = row['uwi']
            q_oil_eur = row['q_oil_eur']
            q_gas_eur = row['q_gas_eur']
            # Print or log EUR values
            print(f"UWI: {uwi}, Q_Oil_EUR: {q_oil_eur}, Q_Gas_EUR: {q_gas_eur}")
            # Update the database
            self.db_manager.save_eur_to_model_properties(uwi, q_oil_eur, q_gas_eur)

        # Update display or logging after calculations
    



    def calculate_npv_and_efr(self):
        from datetime import datetime

        self.model_data = self.db_manager.retrieve_model_data()

        # Get today's date
        today = datetime.today().strftime('%Y-%m-%d')

        # Filter the DataFrame for dates >= today's date
        filtered_df = self.prod_rates_all[self.prod_rates_all['date'] >= today]

        # Group by UWI and calculate NPV, discounted NPV, EFR_gas, and EFR_oil
        results = filtered_df.groupby('uwi').agg(
            npv=('total_revenue', 'sum'),
            npv_discounted=('discounted_revenue', 'sum'),
            EFR_oil=('q_oil', 'sum'),  # Sum q_oi for oil
            EFR_gas=('q_gas', 'sum')  # Sum q_gas for gas
        ).reset_index()

        # Insert the results for each UWI into the database
        for _, row in results.iterrows():
            uwi = row['uwi']
            npv = row['npv']
            npv_discounted = row['npv_discounted']
            EFR_oil = row['EFR_oil']
            EFR_gas = row['EFR_gas']
        
            # Grab q_oil_eru and q_gas_eur from self.model_data for the UWI
            q_oil_eru = self.model_data.loc[self.model_data['uwi'] == uwi, 'q_oil_eru'].values[0]
            q_gas_eur = self.model_data.loc[self.model_data['uwi'] == uwi, 'q_gas_eur'].values[0]

            # Subtract the EUR values from EFR values and calculate percentage remaining
            EUR_oil_remaining = (EFR_oil - q_oil_eru) / q_oil_eru if q_oil_eru != 0 else 0
            EUR_gas_remaining = (EFR_gas - q_gas_eur) / q_gas_eur if q_gas_eur != 0 else 0

            print(f"UWI: {uwi}, NPV: {npv}, NPV Discounted: {npv_discounted}, EFR Oil: {EFR_oil}, EFR Gas: {EFR_gas}")
            print(f"EUR Oil Remaining: {EUR_oil_remaining*100:.2f}%, EUR Gas Remaining: {EUR_gas_remaining*100:.2f}%")

            # Update the database with the calculated values and the remaining EUR percentages
                        # Add the scenario (assuming it's 1 for now)
            scenario = 1  # You can adjust this value as needed

            # Update the database with the new values
            self.db_manager.update_uwi_revenue_and_efr(
                uwi, npv, npv_discounted, EFR_oil, EFR_gas, EUR_oil_remaining, EUR_gas_remaining, scenario)
        self.update_displays()


    def update_displays(self):
       #printself.scenario_id)
        self.ui.activate_icons()
        self.db_manager.connect() 
        self.iterate_di = False
        if not self.current_uwi_index:
            self.current_uwi = self.uwi_list[0]
        self.current_uwi = self.uwi_list[self.current_uwi_index]
       #printself.current_uwi)
        self.uwi_prod_rates_all = self.db_manager.retrieve_prod_rates_all(self.current_uwi, self.scenario_id)
        self.model_data = self.db_manager.retrieve_model_data()
        self.update_excel_widget()
        self.model_parameters()
        self.populate_well_dropdown()
        self.populate_scenario_dropdown_tab1()
        self.update_graph()
        self.db_manager.disconnect() 

        
    def update_excel_widget(self):
        # Clear previous content
        self.ui.excel_widget.clearContents()

        # Set the number of rows in the Excel widget to match the length of the DataFrame
        self.ui.excel_widget.setRowCount(len(self.uwi_prod_rates_all))
       

        # Update the Excel widget with the production data and cumulative volumes
                        # Update the Excel widget with the production data, cumulative volumes, and additional columns
        for row_index, (_, row_data) in enumerate(self.uwi_prod_rates_all.iterrows()):
            date_str = row_data['date'] 
            self.ui.excel_widget.setItem(row_index, 0, QTableWidgetItem(date_str))

            columns_to_format = ['oil_volume', 'cumulative_oil_volume', 'q_oil', 'error_oil', 'oil_revenue',
                                    'gas_volume', 'cumulative_gas_volume', 'q_gas', 'error_gas', 'gas_revenue',
                                    'total_revenue', 'discounted_revenue']
            for col_index, column in enumerate(columns_to_format, start=2):
                value = row_data[column]
                if value is not None:
                    self.ui.excel_widget.setItem(row_index, col_index, QTableWidgetItem('{:.2f}'.format(value)))
                else:
                    self.ui.excel_widget.setItem(row_index, col_index, QTableWidgetItem(''))

        # Resize rows to fit content
        self.ui.excel_widget.resizeRowsToContents()

        # Sort the values in the Excel widget by date
        self.ui.excel_widget.sortItems(0)
     
        print("Excel Updated")



    def on_tab_changed(self, index):
        print(index)
        self.tab_index = index
        # Assuming Tab 2 is at index 1
        if index == 1:
            self.populate_scenario_dropdown_tab2()
        elif index == 2:
            self.populate_scenario_dropdown_tab3()
        elif index == 3:
            self.populate_scenario_dropdown_tab4()


    def on_scenario_changed_tab1(self):
        self.scenario_name = self.ui.scenario_dropdown1.currentText()
        self.scenario_id = self.db_manager.get_scenario_id(self.scenario_name)
        self.uwi_list = self.db_manager.get_uwis_by_scenario_id(self.scenario_id)

        # Reset the current index and UWI
        if self.uwi_list:
            self.ui.well_dropdown.setEnabled(bool(self.uwi_list))
            self.current_uwi_index = 0  # Start at the beginning of the list
            self.current_uwi = self.uwi_list[0]

            # Populate the well dropdown
            self.populate_well_dropdown()

            # Perform the updates only if uwi_list is not empty
            self.update_displays()
            self.update_navigation_buttons()
            self.check_model_status_and_set_icon()
        else:
            self.current_uwi_index = -1
            self.current_uwi = None
            QMessageBox.information(self, "No Wells", "No wells available for the selected scenario.")
            # Clear the graph
            self.ui.graph_area.setHtml("<html><body><h1>No Data Available</h1></body></html>")
            # Clear the well dropdown
            self.ui.well_dropdown.blockSignals(True)
            self.ui.well_dropdown.clear()
            self.ui.well_dropdown.blockSignals(False)


    def on_scenario_changed2(self):
                #print(df_uwi_model_data)
        #print(df_uwi_model_data.dtypes)
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
     
    def populate_scenario_dropdown_tab4(self):
        self.ui.scenario_dropdown4.blockSignals(True)  # Temporarily block signals
        self.ui.scenario_dropdown4.clear()
        self.model_data = self.db_manager.retrieve_model_data_by_scenario(self.scenario_id)


        for scenario in self.scenario_names:
            self.ui.scenario_dropdown4.addItem(scenario)

        self.ui.scenario_dropdown4.setCurrentText(self.scenario_name)

        self.ui.scenario_dropdown4.blockSignals(False)
        self.populate_well_pads_table()
 


    def populate_tab_2(self):
       #print"pop2 start")
        self.ui.model_properties.blockSignals(True)

        try:
  

            # Define headers based on the keys of the dictionaries
            headers = [
                "uwi", "max_oil_production", "max_gas_production", "max_oil_production_date", "max_gas_production_date",
                "one_year_oil_production", "one_year_gas_production", "di_oil", "di_gas", "oil_b_factor", "gas_b_factor",
                "min_dec_oil", "min_dec_gas", "model_oil", "model_gas", "oil_price", "gas_price", "oil_price_dif", "gas_price_dif",
                "discount_rate", "working_interest", "royalty", "tax_rate", "capital_expenditures", "operating_expenditures",
                "economic_limit_type", "economic_limit_date", "net_price_oil", "net_price_gas", "gas_model_status", "oil_model_status"
            ]

            # Clear existing data
            self.ui.model_properties.clearContents()
                     
            # Set headers
            self.ui.model_properties.setColumnCount(len(headers))
            self.ui.model_properties.setHorizontalHeaderLabels(headers)

            # Set row count based on the number of entries in model_data
            self.ui.model_properties.setRowCount(len(self.model_data))

            # Populate table with data
            for row_index, row_data in enumerate(self.model_data):
                for col_index, header in enumerate(headers):
                    col_data = row_data.get(header, "")
                    item = QTableWidgetItem()
                    
                    # Handle UWI and other large numbers to avoid scientific notation
                    if header == "uwi":
                        item.setData(Qt.EditRole, str(col_data))
                    elif "date" in header or "model" in header or "type" in header:
                        # Treat these fields as strings
                        item.setData(Qt.DisplayRole, str(col_data))
                    else:
                        try:
                            numeric_value = float(col_data)
                            item.setData(Qt.EditRole, numeric_value)
                        except ValueError:
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
            self.ui.model_properties.sortItems(self.last_sorted_column, self.last_sort_order)
            self.ui.model_properties.blockSignals(False)
        except Exception as e:
            print("Error populating tab 2:", e)
        print("pop2 end")
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
        self.prod_rates_ag['uwi'] = self.prod_rates_ag['uwi'].astype(str)

        # Extract unique UWIs and determine the min and max dates
        unique_uwis = self.prod_rates_ag['uwi'].unique()

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
        self.ui.data_table3.setRowCount(len(unique_uwis) + 1)  # +1 for totals row

        # Set the horizontal header labels
        header_labels = ["UWI", "NPV"] + date_labels
        self.ui.data_table3.setHorizontalHeaderLabels(header_labels)

        # Set font for "UWI" and "Total" headers
        for i in range(2):
            item = self.ui.data_table3.horizontalHeaderItem(i)
            if item:
                item.setFont(header_font)

        # Create a pivoted DataFrame for each column and fill NaN with 0
        pivoted_data = {column: self.prod_rates_ag.pivot(index='uwi', columns='date', values=column).fillna(0) for column in columns}

        # Ensure pivoted data indices are strings
        for column in columns:
            pivoted_data[column].index = pivoted_data[column].index.astype(str)

        # Initialize arrays to store row totals and grand total
        row_totals = np.zeros(len(unique_uwis))
        column_totals = np.zeros(len(date_range))

        # Populate the QTableWidget with well data and calculate totals
        for row, uwi in enumerate(unique_uwis, start=1):
            uwi = str(uwi)

            if uwi not in pivoted_data[columns[0]].index:
                continue

            # UWI
            uwi_item = QTableWidgetItem(uwi)
            self.ui.data_table3.setItem(row, 0, uwi_item)

            # Fetch row data for all dates and columns at once
            row_data = sum(pivoted_data[column].loc[uwi, date_range].values for column in columns)
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
                    'total_lateral', 'total_capex_cost', 'total_opex_cost', 'num_wells', 'drill_time',
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
            "uwi", "max_oil_production", "max_gas_production", "max_oil_production_date", "max_gas_production_date",
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
            uwi = df_model_properties['uwi'].iloc[0]
            status = self.db_manager.get_uwi_status(uwi)
           # print(status)
            # Update the model properties with the retrieved DataFrame
            self.db_manager.update_model_properties(df_model_properties, self.scenario_id)
        
            

            # Retrieve the updated model properties
            updated_model_df = self.db_manager.retrieve_model_data_by_scenario_and_uwi(self.scenario_id, row_data['uwi'])


            # Run planned production rate calculations
            if status == False:
                iterate = False
                self.uwi_combined_df = self.db_manager.retrieve_prod_rates_by_uwi(uwi)
                self.uwi_production_rates_data, self.uwi_error, self.uwi_model_data = self.dca.update_prod_rate(updated_model_df, self.uwi_combined_df, iterate)
                self.uwi_error = self.dca.uwi_error
            else:
                self.uwi_production_rates_data, self.uwi_error, self.uwi_model_data = self.dca.planned_prod_rate(updated_model_df)
        
        # Clear the edited rows after updating
        self.edited_model_rows.clear()
        self.update_db()
        self.calculate_eur()
        self.calculate_npv_and_efr()
        self.calculate_eur()
        print("Model properties updated for all edited rows.")


    def scenario_active(self):

        current_scenario_name = self.ui.scenario_dropdown.currentText()
        active_scenario_id = self.db_manager.get_scenario_id(current_scenario_name)
        self.db_manager.set_active_scenario(active_scenario_id)

    def update_scenario(self):


    
        for edited_row in self.edited_rows:
            # Fetch data from the edited row
            original_name = self.ui.well_pads_table.item(edited_row, 0).text()
            start_date = self.ui.well_pads_table.item(edited_row, 1).text()
            decline_curve_name = self.ui.well_pads_table.item(edited_row, 2).text()
            
        
  
            try:
                QDateTime.fromString(start_date, "yyyy-MM-dd")
            except ValueError:
               # print(f"Error: Invalid date format in row {edited_row}. Skipping update.")
                continue


            # Get well_pad_id and decline_curve_id
            well_pad_id = self.db_manager.get_well_pad_id(original_name)
           # print('wellpad', well_pad_id)
            decline_curve_id = self.db_manager.get_decline_curve_id(decline_curve_name)

            # Prepare scenario data
            scenario_data = {
                'scenario_id': self.scenario_id,
                'well_pad_id': well_pad_id,
                'start_date': start_date,
                'decline_curve_id': decline_curve_id
            }
           # print(scenario_data)
        
            # Add or update scenario in the database
            self.db_manager.add_or_update_scenario(scenario_data)

            # Prepare well_pad_data dictionary for columns in well_pads table
            well_pad_data = {}

            # Read columns dynamically starting from index 3
            num_columns = self.ui.well_pads_table.columnCount()
            for col in range(3, num_columns):
                column_item = self.ui.well_pads_table.item(edited_row, col)
                if column_item is None:
                    print(f"Warning: Missing data in column {col} of row {edited_row}.")
                    continue
                column_name = self.ui.well_pads_table.horizontalHeaderItem(col).text()
                column_value = column_item.text()
                well_pad_data[column_name] = column_value
    
        
            # Update well pad in the well_pads table
            try:
                self.db_manager.update_well_pad(well_pad_id, {
                    'total_lateral': well_pad_data.get('Total Lateral', ''),
                    'total_capex_cost': well_pad_data.get('Total Capex Cost', ''),
                    'total_opex_cost': well_pad_data.get('Total Opex Cost', ''),
                    'num_wells': well_pad_data.get('Num Wells', ''),
                    'drill_time': well_pad_data.get('Drill Time', ''),
                    'prod_type': well_pad_data.get('Prod Type', ''),
                    'oil_model_status': well_pad_data.get('Oil Model Status', ''),
                    'gas_model_status': well_pad_data.get('Gas Model Status', ''),
                    'pad_cost': well_pad_data.get('Pad Cost', ''),
                    'exploration_cost': well_pad_data.get('Exploration Cost', ''),
                    'cost_per_foot': well_pad_data.get('Cost Per Foot', ''),
                    'distance_to_pipe': well_pad_data.get('Distance To Pipe', ''),
                    'cost_per_foot_to_pipe': well_pad_data.get('Cost Per Foot To Pipe', ''),
                })
                print(f"Updated well pad '{well_pad_id}' successfully.")
            except Exception as e:
                print(f"Exception occurred while updating well pad '{well_pad_id}': {e}")
    
        # After updating scenarios, refresh the well pads table
        self.populate_well_pads_table()
        print('hi1')
        # Clear edited rows list after processing
        self.edited_rows.clear()
        print('hi2')
        self.ui.well_pads_table.blockSignals(False)


  
    def run_scenario4(self):
        # Fetch current scenario details

        # Iterate through each row in the well_pads_table
        num_rows = self.ui.well_pads_table.rowCount()
        for row in range(num_rows):
            # Fetch data from the well_pads_table
            original_name_item = self.ui.well_pads_table.item(row, 0)
            start_date_item = self.ui.well_pads_table.item(row, 1)
            decline_curve_name = self.ui.well_pads_table.item(row, 2).text()
        


            # Convert start_date_item to the appropriate format
            start_date = QDateTime.fromString(start_date_item.text(), "yyyy-MM-dd").date()

            # Get other well pad data dynamically
            well_pad_data = {}
            num_columns = self.ui.well_pads_table.columnCount()
            for col in range(3, num_columns):
                column_name = self.ui.well_pads_table.horizontalHeaderItem(col).text()
                column_value = self.ui.well_pads_table.item(row, col).text()
                well_pad_data[column_name] = column_value

            # Get decline curve data and scenario data from the database
            decline_curve_id = self.db_manager.get_decline_curve_id(decline_curve_name)
            decline_curve_data = self.db_manager.get_decline_curve_data(decline_curve_name)

            # Determine other parameters needed for handle_scenario
            num_wells = int(well_pad_data.get('Num Wells', 0))
            base_uwi = original_name_item.text()
            drill_time = int(well_pad_data.get('Drill Time', 0))
            total_capex_cost = float(well_pad_data.get('Total Capex Cost', 0))
            total_opex_cost = float(well_pad_data.get('Total Opex Cost', 0))
            prod_type = well_pad_data.get('Prod Type', '')
            oil_model_status = int(well_pad_data.get('Oil Model Status', 0))
            gas_model_status = int(well_pad_data.get('Gas Model Status', 0))

            # Call handle_scenario with retrieved data
            self.handle_scenario(self.scenario_id, start_date, num_wells, base_uwi, decline_curve_data, drill_time,
                                 total_capex_cost, total_opex_cost, prod_type, oil_model_status, gas_model_status)



    def add_well(self):
        decline_curves = self.db_manager.get_decline_curve_names()
        scenarios = self.db_manager.get_scenario_names()
      
        scenarios = [scenario for scenario in scenarios if scenario != 'Active_Wells']
        # Fetch scenario names from the database
        dialog = AddWell(self, decline_curves, scenarios)
    
        if dialog.exec_() == QDialog.Accepted:
            
            base_uwi = dialog.uwi_input.text()
            num_wells = dialog.num_wells_input.value()
            drill_time = dialog.drill_time_input.value()
            total_capex_cost = float(dialog.capex_cost_output.text().replace('$', ''))
            total_opex_cost = dialog.opex_input.value()
            prod_type = dialog.prod_type_input.currentText()
            pad_cost = dialog.pad_cost_input.value()  # Correct way to get the value from QDoubleSpinBox
            exploration_cost = dialog.exploration_cost_input.value()
            total_lateral = dialog.total_lateral_input.value()
            cost_per_foot = dialog.cost_per_foot_input.value()
            distance_to_pipe = dialog.distance_to_pipe_input.value()
            cost_per_foot_to_pipe = dialog.cost_per_foot_to_pipe_input.value()

            # Determine model statuses based on production type
            oil_model_status = 1 if prod_type in ["Oil", "Both"] else 0
            gas_model_status = 1 if prod_type in ["Gas", "Both"] else 0

            # Insert data into well_pads table
            well_pad_data = {
                'original_name': base_uwi,
                'total_lateral': total_lateral,
                'total_capex_cost': total_capex_cost,
                'total_opex_cost': total_opex_cost,
                'num_wells': num_wells,
                'drill_time': drill_time,
                'prod_type': prod_type,
                'oil_model_status': oil_model_status,
                'gas_model_status': gas_model_status,
                'pad_cost': pad_cost,
                'exploration_cost': exploration_cost,
                'cost_per_foot': cost_per_foot,
                'distance_to_pipe': distance_to_pipe,
                'cost_per_foot_to_pipe': cost_per_foot_to_pipe
            }
            self.db_manager.insert_well_pad(well_pad_data)



            scenario_selected = dialog.scenario_input.currentIndex() != -1
            if scenario_selected:
                decline_curve = dialog.decline_curve_input.currentText()
                decline_curve_data = self.db_manager.get_decline_curve_data(decline_curve)
  

                # Fetch decline curve ID
                
       

                scenario = dialog.scenario_input.currentText()
               ## print(scenario)
                scenario_id = self.db_manager.get_scenario_id(scenario)
                start_date = dialog.start_date_input.date()
                decline_curve_id = self.db_manager.get_decline_curve_id(decline_curve)
                well_pad_id = self.db_manager.get_well_pad_id(base_uwi)
               # print(well_pad_id)
                # Insert scenario into scenarios table
                scenario_data = {
                    'scenario_id': scenario_id,
                    'well_pad_id': well_pad_id,
                    'start_date': start_date.toString("yyyy-MM-dd"),
                    'decline_curve_id': decline_curve_id
                }
               # print(scenario_data)
                inserted_scenario_id = self.db_manager.add_or_update_scenario(scenario_data)
                if not inserted_scenario_id:
                    print("Error inserting scenario data.")
                    return
                #print(scenario_id)
                self.handle_scenario(scenario_id, start_date, num_wells, base_uwi, decline_curve_data, drill_time, total_capex_cost, total_opex_cost, prod_type, oil_model_status, gas_model_status)

        if self.tab_index == 3:
            self.populate_well_pads_table() 


    def add_scenario(self):
        dialog = ScenarioNameDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            scenario_name = dialog.get_scenario_name()
            is_active = False  # Get the active status from the dialog

            if scenario_name:
                self.db_manager.insert_scenario_name(scenario_name, is_active)
                self.scenario_names = self.db_manager.get_all_scenario_names()
                # Refresh the dropdown lists on tab1 and tab3
                self.populate_scenario_dropdown_tab1()
                self.populate_scenario_dropdown_tab2()
                self.populate_scenario_dropdown_tab4()
            else:
                QMessageBox.warning(self, "Warning", "Scenario name cannot be empty.")
        
        
    def handle_scenario(self, scenario_id, start_date, num_wells, base_uwi, decline_curve_data, drill_time, total_capex_cost, total_opex_cost, prod_type, oil_model_status, gas_model_status):
        #print(scenario_id)
        if decline_curve_data is None:
            print("Skipping scenario handling due to missing decline curve data.")
            return
        # Divide total CAPEX and OPEX costs by the number of wells
        capex_cost_per_well = total_capex_cost / num_wells
        opex_cost_per_well = total_opex_cost / num_wells

        for i in range(num_wells):
            uwi = f"{base_uwi}_{i+1}"
            well_start_date = start_date.addMonths(i * drill_time).toString("yyyy-MM-dd")

            well_data = {
                'uwi': uwi,
                'max_oil_production': decline_curve_data['max_oil_production'],
                'max_gas_production': decline_curve_data['max_gas_production'],
                'max_oil_production_date': well_start_date,
                'max_gas_production_date': well_start_date,
                'one_year_oil_production': decline_curve_data['one_year_oil_production'],
                'one_year_gas_production': decline_curve_data['one_year_gas_production'],
                'di_oil': decline_curve_data['di_oil'],
                'di_gas': decline_curve_data['di_gas'],
                'oil_b_factor': decline_curve_data['oil_b_factor'],
                'gas_b_factor': decline_curve_data['gas_b_factor'],
                'min_dec_oil': decline_curve_data['min_dec_oil'],
                'min_dec_gas': decline_curve_data['min_dec_gas'],
                'model_oil': decline_curve_data['model_oil'],
                'model_gas': decline_curve_data['model_gas'],
                'oil_price': decline_curve_data['oil_price'],
                'gas_price': decline_curve_data['gas_price'],
                'oil_price_dif': decline_curve_data['oil_price_dif'],
                'gas_price_dif': decline_curve_data['gas_price_dif'],
                'discount_rate': decline_curve_data['discount_rate'],
                'working_interest': decline_curve_data['working_interest'],
                'royalty': decline_curve_data['royalty'],
                'tax_rate': decline_curve_data['tax_rate'],
                'capital_expenditures': capex_cost_per_well,
                'operating_expenditures': opex_cost_per_well,
                'economic_limit_type': decline_curve_data['economic_limit_type'],
                'economic_limit_date': decline_curve_data['economic_limit_date'],
                'net_price_oil': decline_curve_data['net_price_oil'],
                'net_price_gas': decline_curve_data['net_price_gas'],
                'gas_model_status': gas_model_status,
                'oil_model_status': oil_model_status,
                }

            df_uwi_model_data = pd.DataFrame([well_data])
            #print(df_uwi_model_data)
            status = "Planned"
            self.db_manager.insert_uwi(uwi, status)
            self.db_manager.update_model_properties(df_uwi_model_data, scenario_id)

            self.uwi_production_rates_data, self.uwi_error, self.uwi_model_data = self.dca.planned_prod_rate(df_uwi_model_data)
            #printscenario_id)
            self.db_manager.update_uwi_prod_rates(self.uwi_production_rates_data, scenario_id)

            self.uwi_error = pd.DataFrame({
                'uwi': uwi,
                'sum_error_oil': [0],
                'sum_error_gas': [0]
            })
           #printself.senario_id)
            self.db_manager.update_uwi_errors(self.uwi_error, scenario_id)



            if self.displayed_status == "Planned":
                self.uwi_list = self.db_manager.get_uwis_by_status(self.displayed_status)
                self.current_uwi_index = len(self.uwi_list) - 1
                self.current_uwi = uwi

        
        self.calculate_eur()
        self.calculate_npv_and_efr()

        self.update_navigation_buttons()




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
        # Get current uwi index
        self.db_manager = DatabaseManager(self.db_path)
        self.db_manager.connect()

        self.uwi_model_data = self.db_manager.retrieve_model_properties(self.current_uwi, self.scenario_id)
       #printself.uwi_model_data)

        self.current_error_row = self.db_manager.retrieve_error_row(self.current_uwi, self.scenario_id)
        print(self.current_error_row)
 

        initial_gas_prod_rate = float(self.uwi_model_data['max_gas_production'])
        self.ui.initial_gas_production_rate_input.setText(str(initial_gas_prod_rate))
        initial_gas_decline_rate = float(self.uwi_model_data['di_gas'])
        self.ui.initial_gas_decline_rate_input.setText(str(initial_gas_decline_rate))
        gas_b_factor = float(self.uwi_model_data['gas_b_factor'])
        self.ui.gas_b_factor_input.setText(str(gas_b_factor))
    
        #gas_hyperbolic_exponent = current_data.get('hyperbolic_exponent_gas', 0.5)  # Default to 0.5 if not available
        #self.ui.gas_hyperbolic_exponent_input.setText(str(gas_hyperbolic_exponent))

        gas_start_date = self.uwi_model_data['max_gas_production_date'].iloc[0] 
        
        # Parse the string date into a datetime object
        gas_start_datetime = datetime.strptime(gas_start_date, '%Y-%m-%d')
      
        # Extract the date part from the datetime object
        gas_start_date_only = gas_start_datetime.date()

        # Now create the QDate object
        gas_start_qdate = QDate(gas_start_date_only)
        self.ui.gas_time_input.setDate(gas_start_qdate)

        min_dec_gas = float(self.uwi_model_data['min_dec_gas'])
        self.ui.min_dec_gas.setText(str(min_dec_gas))



        # Set oil parameters
        initial_oil_prod_rate = float(self.uwi_model_data['max_oil_production'])
        self.ui.initial_oil_production_rate_input.setText(str(initial_oil_prod_rate))

        oil_start_date = self.uwi_model_data['max_oil_production_date'].iloc[0] 
        
        # Parse the string date into a datetime object
        oil_start_datetime = datetime.strptime(oil_start_date, '%Y-%m-%d')

        # Extract the date part from the datetime object
        oil_start_date_only = oil_start_datetime.date()

        # Now create the QDate object
        oil_start_qdate = QDate(oil_start_date_only)
        self.ui.oil_time_input.setDate(oil_start_qdate)


        initial_oil_decline_rate = float(self.uwi_model_data['di_oil'])
        self.ui.initial_oil_decline_rate_input.setText(str(initial_oil_decline_rate))

        oil_b_factor = float(self.uwi_model_data['oil_b_factor'])
        self.ui.oil_b_factor_input.setText(str(oil_b_factor))

        min_dec_oil = float(self.uwi_model_data['min_dec_oil'])
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
            economic_limit_type = self.uwi_model_data.get("economic_limit_type", "").iloc[0]

            if economic_limit_type == "Net Dollars":  # Economic Limit selected
                self.ui.ecl_date.setEnabled(False)  # Disable date input
            elif economic_limit_type == "End Date":  # Date selected
                self.ui.ecl_date.setEnabled(True)   # Enable date input
            elif economic_limit_type == "GOR":  # Another option, for example
                self.ui.ecl_date.setEnabled(False)  # Adjust as needed for GOR
            self.ui.end_forecast_type.setCurrentText(economic_limit_type)

            economic_limit_date_value = self.uwi_model_data.get("economic_limit_date", QDateTime.currentDateTime().toString("yyyy-MM-dd"))
            economic_limit_date_str = str(economic_limit_date_value)
            self.ui.ecl_date.setDateTime(QDateTime.fromString(economic_limit_date_str, "yyyy-MM-dd"))


            self.ui.oil_price.setText(str(self.uwi_model_data.get("oil_price", "").iloc[0]))
            self.ui.gas_price.setText(str(self.uwi_model_data.get("gas_price", "").iloc[0]))
            self.ui.oil_price_dif.setText(str(self.uwi_model_data.get("oil_price_dif", "").iloc[0]))
            self.ui.gas_price_dif.setText(str(self.uwi_model_data.get("gas_price_dif", "").iloc[0]))
            #self.ui.discount_rate_input.setText(str(current_data.get("discount_rate", "")))
            self.ui.working_interest.setText(str(self.uwi_model_data.get("working_interest", "").iloc[0]))
            self.ui.royalty.setText(str(self.uwi_model_data.get("royalty", "").iloc[0]))
            self.ui.discount_rate.setText(str(self.uwi_model_data.get("discount_rate", "").iloc[0]))
            self.ui.tax_rate.setText(str(self.uwi_model_data.get("tax_rate", "").iloc[0]))
            self.ui.capital_expenditures.setText(str(self.uwi_model_data.get("capital_expenditures", "").iloc[0]))
            self.ui.operating_expenditures.setText(str(self.uwi_model_data.get("operating_expenditures", "").iloc[0]))
            self.ui.net_price_oil.setText(str(self.uwi_model_data.get("net_price_oil", "").iloc[0]))
            self.ui.net_price_gas.setText(str(self.uwi_model_data.get("net_price_gas", "").iloc[0]))





        print("parameters set")
             


    def update_graph(self):
        plotting = Plotting()
        plotting.generate_plot_html(self.uwi_prod_rates_all, self.current_uwi, self.graph_type, self.distribution_type, self.uwi_model_data)
        html_content = plotting.html_content
        self.ui.graph_area.setHtml(html_content)
        
 

#Upated Current Decline Curves and the models
    def update_decline_curve(self, di_oil=None, di_gas=None, iterate=None):
        if iterate == None:
            iterate = False

        self.ui.calculate_net_price()
        uwi_model_data = []
        # Get the current indexed uwi
        self.current_uwi = self.uwi_list[self.current_uwi_index]

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
        oil_model_status = self.db_manager.get_model_status(self.current_uwi, 'oil')
        gas_model_status = self.db_manager.get_model_status(self.current_uwi, 'gas')

                # Create a dictionary with the model parameters
        # Create a dictionary with the model parameters
        updated_model_data = {
            'uwi': self.current_uwi,
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
            'oil_model_status' : (oil_model_status),
            'gas_model_status' : (gas_model_status),
            
        }
        self.ui.calculate_net_price()
        uwi_model_data.append(updated_model_data)

        # Convert the list of dictionaries to a DataFrame
        df_uwi_model_data = pd.DataFrame(uwi_model_data)
       #printdf_uwi_model_data)
        
        self.db_manager = DatabaseManager(self.db_path)
        self.db_manager.connect()
        self.db_manager.update_model_properties(df_uwi_model_data, self.scenario_id)
       #printdf_uwi_model_data)
        self.uwi_model_data  = self.db_manager.retrieve_model_data_by_scenario_and_uwi(self.scenario_id, self.current_uwi )
       #printself.uwi_model_data)



        current_uwi_status = self.db_manager.get_uwi_status(self.current_uwi)  # Get the status of the current UWI
       #printcurrent_uwi_status)
        if current_uwi_status == True:
            self.uwi_production_rates_data, self.uwi_error, self.uwi_model_data = self.dca.planned_prod_rate(self.uwi_model_data)
        else:
            self.uwi_combined_df = self.db_manager.retrieve_prod_rates_by_uwi(self.current_uwi)
            self.uwi_production_rates_data, self.uwi_error, self.uwi_model_data = self.dca.update_prod_rate(self.uwi_model_data, self.uwi_combined_df, iterate)
           
            self.db_manager.update_model_properties(self.uwi_model_data, self.scenario_id)
            self.uwi_error = self.dca.uwi_error


        #self.regenerate_html_for_uwi(self.current_uwi)
        self.update_db()
        self.calculate_eur()
        self.calculate_npv_and_efr()
        
        self.regenerated = False
            
    def update_db(self):
        self.db_manager = DatabaseManager(self.db_path)
        self.db_manager.connect()
        pd.set_option('display.max_rows', None)
        pd.set_option('display.max_columns', None)
    
        #df_uwi_model_data = pd.DataFrame([self.uwi_model_data], index=[0])


        #print(self.uwi_production_rates_data)
        self.db_manager.update_uwi_prod_rates(self.uwi_production_rates_data, self.scenario_id)
        

        self.db_manager.update_uwi_errors(self.uwi_error, self.scenario_id)
        
        #print(self.uwi_error)


    def iterate_di(self):
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

        self.db_manager = DatabaseManager(self.db_path)
        self.db_manager.connect()
    
        # Get the current status of the gas model from the database
        gas_model_status = self.db_manager.get_model_status(self.current_uwi, 'gas')
    
        # Toggle the status
        new_status = 1 if gas_model_status == 0 else 0

    # Update the database with the new status
        self.db_manager.update_model_status(self.current_uwi, new_status, 'gas')

        
        icon_name = f"gas_{'on' if new_status == 1 else 'off'}"  # Assuming your icon names are "gas_on.png" and "gas_off.png"
        icon_path = os.path.join(self.script_dir, "Icons", f"{icon_name}.png")
        self.ui.gas_model.setIcon(QIcon(icon_path))
        self.update_decline_curve()

    def oil_model(self):
        self.db_manager = DatabaseManager(self.db_path)
        self.db_manager.connect()
        oil_model_status = self.db_manager.get_model_status(self.current_uwi, 'oil')

        new_status = 1 if oil_model_status == 0 else 0

            # Update the database with the new status
        self.db_manager.update_model_status(self.current_uwi, new_status, 'oil')

        # Update the icon based on the new status
        icon_name = f"oil_{'on' if new_status == 1 else 'off'}"  # Assuming your icon names are "oil_on.png" and "oil_off.png"
        icon_path = os.path.join(self.script_dir, "Icons", f"{icon_name}.png")
        self.ui.oil_model.setIcon(QIcon(icon_path))
        self.update_decline_curve()

    def delete_well(self):

        
    
        # Check if there are wells to delete
        if self.uwi_list:
            try:
                # Remove uwi from all relevant tables in the database
               #printself.current_uwi)
                self.db_manager.delete_uwi_records(self.current_uwi)

                # Remove uwi from uwi_list
                del self.uwi_list[self.current_uwi_index]

                 #Update current index and displays
                if self.current_uwi_index >= len(self.uwi_list):
                    self.current_uwi_index = len(self.uwi_list) - 1
                self.update_displays()
                self.update_navigation_buttons()

            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to delete well: {str(e)}", QMessageBox.Ok)

    def delete_pad(self):
        pass




    def check_model_status_and_set_icon(self):
        current_data = self.model_data[self.current_uwi_index]

        # Check oil model status and set icon
        if current_data.get('oil_model_status', 'on') == "off":
            oil_icon_path = os.path.join(self.script_dir, "Icons", "oil_off")
        else:
            oil_icon_path = os.path.join(self.script_dir, "Icons", "oil_on")
        self.ui.oil_model.setIcon(QIcon(oil_icon_path))

        # Check gas model status and set icon
        if current_data.get('gas_model_status', 'on') == "off":
            gas_icon_path = os.path.join(self.script_dir, "Icons", "gas_off")
        else:
            gas_icon_path = os.path.join(self.script_dir, "Icons", "gas_on")
        self.ui.gas_model.setIcon(QIcon(gas_icon_path))


    def save_dc(self):
        # Assume self.uwis contains the list of available uwis
        dialog = SaveDeclineCurveDialog(self, uwis=self.uwi_list)
        if dialog.exec_() == QDialog.Accepted:
            curve_name = dialog.get_curve_name()
            if not curve_name:  # Check if the curve name is blank
                QMessageBox.warning(self, "No Curve Name", "Please provide a name for the decline curve.")
                return

            selected_option = dialog.get_selected_option()
            
            if selected_option == "Current Well":
                # Save the current uwi_model_data to the database with the provided name
                self.db_manager.save_decline_curve_to_db(curve_name, self.uwi_model_data)
            elif selected_option == "Average":
                selected_uwis = dialog.get_selected_uwis()
                if not selected_uwis:
                    QMessageBox.warning(self, "No UWI Selected", "Please select at least one UWI to average.")
                    return
                averaged_data = self.average_uwis(selected_uwis)
                self.db_manager.save_decline_curve_to_db(curve_name, averaged_data)
            elif selected_option == "Manual":
                manual_data = dialog.get_manual_data()
                manual_df = pd.DataFrame([manual_data])
                self.db_manager.save_decline_curve_to_db(curve_name, manual_df)

    def save_scenario(self):
        pass

    def delete_pad(self):
        pass
    
    def average_uwis(self, selected_uwis):
        if isinstance(self.model_data, list):
            self.model_data_df = pd.DataFrame(self.model_data)
        # Filter self.model_data based on the selected uwis
        filtered_data = self.model_data_df[self.model_data_df['uwi'].isin(selected_uwis)]

        
        # Check if filtered_data is empty
        if filtered_data.empty:
            QMessageBox.warning(self, "No Data", "No data found for the selected uwis.")
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
        #    self.uwi_list = self.db_manager.get_uwis_by_status("Planned")
        
        #    if not self.uwi_list:
        #        # Show a message box indicating no planned wells
        #        QMessageBox.information(self, "No Planned Wells", "No planned wells available. Switching to Active wells.")
        #        # Switch back to Active wells
        #        self.displayed_status = "Active"
        #        self.uwi_list = self.db_manager.get_uwis_by_status("Active")
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
        #        self.uwi_list = self.db_manager.get_uwis_by_scenario_id(self.scenario_id)
        #elif value == "Active":
        #    self.displayed_status = "Active"
        #    # Fetch UWIs with active status
        #    self.uwi_list = self.db_manager.get_uwis_by_status("Active")
        #    # Disable the scenario dropdown for Active wells
        #    self.ui.option1_dropdown.setEnabled(False)
        #    self.ui.scenarios_dropdown1.setEnabled(False)
        #    self.ui.scenarios_dropdown1.setVisible(False)
        #    self.scenario_id = self.db_manager.get_active_scenario_id()
        #    self.scenario_name = self.db_manager.get_active_scenario_name()

        ## Enable or disable the well dropdown based on UWI list
        #self.ui.well_dropdown.setEnabled(bool(self.uwi_list))

        ## Reset the current index and UWI
        #if self.uwi_list:
        #    self.current_uwi_index = 0  # Start at the beginning of the list
        #    self.current_uwi = self.uwi_list[0]
        #else:
        #    self.current_uwi_index = -1
        #    self.current_uwi = None

        #self.update_displays()
        #self.update_navigation_buttons()
        #self.check_model_status_and_set_icon()




    def navigate_forward(self):
        
#Window Navigation
        #self.ui.disconnect_parameters_triggers(self)
        if self.current_uwi_index < len(self.uwi_list) - 1:
            self.current_uwi_index += 1
            self.update_displays()
            self.current_uwi = self.uwi_list[self.current_uwi_index]
            self.update_dropdown() 
            self.update_navigation_buttons()
            self.check_model_status_and_set_icon()

    def navigate_back(self):
        # Window Navigation
        # self.ui.disconnect_parameters_triggers(self)
        if self.current_uwi_index > 0:
            self.current_uwi_index -= 1
            self.update_displays()
            self.current_uwi = self.uwi_list[self.current_uwi_index]
            self.update_dropdown()
            self.update_navigation_buttons()
            self.check_model_status_and_set_icon()

    def update_navigation_buttons(self):
        # Check if at the first uwi
        if self.current_uwi_index == 0:
            self.ui.back_button.setEnabled(False)
        else:
            self.ui.back_button.setEnabled(True)

        # Check if at the last uwi
        if self.current_uwi_index >= len(self.uwi_list) - 1:

            
            self.ui.forward_button.setEnabled(False)
        else:
            self.ui.forward_button.setEnabled(True)


    def populate_well_dropdown(self):
        self.ui.well_dropdown.blockSignals(True)  # Temporarily block signals
        self.ui.well_dropdown.clear()
    
       #printself.uwi_list)
    
        # Add well names to the dropdown
        for well_name in self.uwi_list:
            self.ui.well_dropdown.addItem(str(well_name))
    
        # Find the index of self.current_uwi and set it
        if self.current_uwi in self.uwi_list:
            index = self.uwi_list.index(self.current_uwi)
            self.ui.well_dropdown.setCurrentIndex(index)
    
        self.ui.well_dropdown.blockSignals(False) 


    def on_well_selected(self, index):
        # Update the current UWI and index based on the selected item
        self.current_uwi_index = index
        self.current_uwi = self.uwi_list[index]
        self.update_displays()
        self.update_dropdown()
        self.update_navigation_buttons()
        self.check_model_status_and_set_icon()

    def update_dropdown(self):
        self.ui.well_dropdown.blockSignals(True)  # Temporarily block signals
        self.ui.well_dropdown.setCurrentText(self.current_uwi) 
        self.ui.well_dropdown.blockSignals(False) 



    def launch_combined_cashflow(self):
        self.cashflow_window = LaunchCombinedCashflow()
        # Example data
        combined_data, date_ranges = self.db_manager.retrieve_and_sum()
        model_data = self.db_manager.retrieve_model_data()
        model_data_df = pd.DataFrame(model_data)
        merged_df = pd.merge(date_ranges, model_data_df, on='uwi', how='inner')

        # Select only the uwi, first_date (start date), and capital_expenditures (CapEx) columns
        capex_df = merged_df[['uwi', 'first_date', 'capital_expenditures']]
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