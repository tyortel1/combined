
import sys
import pandas as pd
from PyQt5.QtWidgets import QApplication, QDialog, QHBoxLayout, QVBoxLayout, QPushButton, QMenuBar, QMessageBox, QMainWindow, QTableWidgetItem, QFileDialog, QWidget, QTableWidgetItem, QInputDialog
import os
from PyQt5.QtCore import QDateTime, QDate, QTime
from PyQt5.QtGui import QIcon, QDoubleValidator
from PyQt5.QtCore import QObject, QEvent, Qt
from ui_main import UI_main
from plotting import Plotting
from LoadProductions import LoadProductions
from ImportExcel import ImportExcelDialog
from SeisWareConnect import SeisWareConnectDialog 
from DeclineCurveAnalysis import DeclineCurveAnalysis 
from DefaultProperties import DefaultProperties
from ModelProperties import ModelProperties
import pickle
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from DatabaseManager import DatabaseManager
from ProjectDialog import ProjectDialog

import sqlite3

import numpy as np
import os


class MainWindow(QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()
        self.ui = UI_main()
        self.ui.setupUI(self)


        self.dca = None
        self.uwi_df =[]
        self.model_data = [] 
        self.combined_df = None  # Assuming combined_df will be set later
        self.current_uwi_index = 0 
        self.uwi_list = [] 
        self.total_items = len(self.uwi_list)# Store the list of UWIs
        self.current_uwi = None
        self.dialog_changed_flag = False
        self.prod_rates_errors = None
        self.prod_rates_all = None
        self.uwi_prod_and_rates = None
        self.df_combined_all = None
        self.ui.connect_parameters_triggers(self) 
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
        self.iterate_di = False
        self.iterate_bfactor = False
        self.open = False
        self.load_oil = True
        self.load_oil = True
        self.html_content_by_uwi = {}
        self.project_name = None
        self.db_path = None
        self.db_manager = None
        self.last_directory_path = None
        self.model_data_df = pd.DataFrame()
        self.uwi_production_rates_data = pd.DataFrame()
        self.uwi_error = pd.DataFrame()
        self.db_manager = DatabaseManager(None)
        self.dca = DeclineCurveAnalysis()



        

        
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


    def create_project(self):
        # Create an instance of the custom dialog
        dialog = ProjectDialog()

        # Get the last used directory from the file
        default_dir = self.get_last_directory()  # Ensure this method reads the path from the file
        if not default_dir:
            default_dir = ""  # Fallback to the empty string if no directory is retu
        if default_dir:
            dialog.directory_input.setText(default_dir)  # Assuming directory_input is a QLineEdit

        if dialog.exec_():
            # Retrieve the project name and directory from the dialog
            project_name = dialog.project_name_input.text()
            directory = dialog.directory_input.text()

            # Construct the full path for the database file
            self.db_path = os.path.join(directory, f"{project_name}.db")

            # Create the SQLite database file
            self.create_database()

            # Save the used directory as the last directory
            self.save_last_directory(directory)


    def create_database(self):
        # Check if the database path is valid
        if self.db_path:
            try:
                # Create or connect to the SQLite database
                self.db_manager = DatabaseManager(self.db_path)
                self.db_manager.connect()

            # Create the UWIs table
                self.db_manager.create_uwi_table()
                self.db_manager.create_prod_rates_all_table()
                # Additional database initialization if needed
                # For example, creating tables or setting up initial data

                # Show a message indicating successful database creation
                QMessageBox.information(self, "Database Created", f"The database '{os.path.basename(self.db_path)}' has been created successfully.", QMessageBox.Ok)
                self.ui.activate_icons()
            except Exception as e:
                # Show an error message if database creation fails
                QMessageBox.critical(self, "Error", f"Failed to create database: {str(e)}", QMessageBox.Ok)
        else:
            # Show an error message if the database path is not specified
            QMessageBox.critical(self, "Error", "Database path is not specified.", QMessageBox.Ok)

            # Import Data
    def connectToSeisWare(self):
        dialog = SeisWareConnectDialog()
        if dialog.exec_() == QDialog.Accepted:
            production_data = dialog.production_data 
            self.prepare_and_update(production_data)
    def import_excel(self):
        dialog = ImportExcelDialog()
        if dialog.exec_() == QDialog.Accepted:
            production_data = dialog.production_data
            self.prepare_and_update(production_data)

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


    def get_last_directory(self):
        last_directory_path = os.path.join(os.path.expanduser('~'), 'last_directory.txt')
        try:
            if os.path.exists(last_directory_path):
                with open(last_directory_path, 'r') as file:
                    return file.readline().strip()  # Read the first line containing the path
        except Exception as e:
            print(f"Error reading last directory: {str(e)}")
        return None  # Return None if no path is stored or in case of an error

    def save_last_directory(self, directory):
        last_directory_path = os.path.join(os.path.expanduser('~'), 'last_directory.txt')
        try:
            with open(last_directory_path, 'w') as file:
                file.write(directory)
        except Exception as e:
            print(f"Failed to save last directory: {str(e)}")
       
    def retrieve_data(self):
        if self.db_manager:
            self.db_manager.connect()  # Ensure connection is open
            self.prod_rates_all = self.db_manager.retrieve_prod_rates_all() 
            self.model_data = self.db_manager.retrieve_model_data()
            self.sum_of_errors = self.db_manager.retrieve_sum_of_errors()
            self.uwi_list  = self.db_manager.get_uwis()
            self.ui.activate_icons()
            self.update_displays()
          

# Create Model and Production DataFrames
    def prepare_and_update(self, production_data):
        
        print('Data Prepared')
        self.production_data = sorted(production_data, key=lambda x: (x['uwi'], x['date']))

        if production_data:
            load_productions = LoadProductions()
            self.combined_df, self.uwi_list = load_productions.prepare_data(production_data,self.db_path) 
            #print(self.combined_df)
            self.handle_default_parameters()
            self.ui.activate_icons() 
            self.decline_analysis()

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
        self.ui.end_forcast_type_value = self.default_properties.get("economic_limit_type", "")
        self.ui.end_forcast_type.setCurrentText(self.ui.end_forcast_type_value)
        self.ui.gas_b_factor_input.setText(str(self.default_properties.get("b_factor_gas", "")))
        self.ui.min_dec_gas.setText(str(self.default_properties.get("min_dec_gas", "")))
        self.ui.oil_b_factor_input.setText(str(self.default_properties.get("b_factor_oil", "")))
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
 

     
        self.sum_of_errors.iloc[:, 1:] = self.sum_of_errors.iloc[:, 1:].round(2)
        
        # Ensure database manager is initialized and connected
        if self.db_manager:
            self.db_manager.connect()  # Ensure connection is open
            self.db_manager.prod_rates_all(self.prod_rates_all, 'prod_rates_all')
            self.db_manager.create_model_properties_table()
            self.db_manager.store_model_data(self.model_data_df)
            self.db_manager.create_sum_of_errors_table()
            self.db_manager.store_sum_of_errors_dataframe(self.sum_of_errors, 'sum_of_errors')
                # Close the connection after the operation

        self.update_displays()


    def update_displays(self):
        print("updating")
        
        self.db_manager.connect() 
        self.iterate_di = False
        if not self.current_uwi_index:
            self.current_uwi = self.uwi_list[0]
        self.current_uwi = self.uwi_list[self.current_uwi_index]

        self.uwi_prod_rates_all = self.db_manager.retrieve_prod_rates_all(self.current_uwi)
        self.model_data = self.db_manager.retrieve_model_data()
        self.update_excel_widget()
        self.model_parameters()
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
        self.populate_tab_2() # Assuming date is in the first column
        print("Excel Updated")

    def populate_tab_2(self):
        print("pop2 start")
        try:
            self.db_manager = DatabaseManager(self.db_path)
            self.db_manager.connect()
            today = datetime.today()
            today_date = today.date()
            rows = self.db_manager.retrieve_tab2(today_date)
            # Convert rows to a dictionary where each key is a date and the value is a dictionary of UWIs and their revenues
            date_uwi_revenue_dict = {}
            all_uwis = set()  # Track all unique UWIs
            for row in rows:
                date = row[0]
                uwi = row[1]
                revenue = row[2]
                if date not in date_uwi_revenue_dict:
                    date_uwi_revenue_dict[date] = {}
                date_uwi_revenue_dict[date][uwi] = revenue
                all_uwis.add(uwi)

            # Sort dates
            sorted_dates = sorted(date_uwi_revenue_dict.keys())

            # Prepare table headers
            self.ui.total_prod_rev_excel_widget.setColumnCount(len(all_uwis) + 1)  # Add one for the date column
            self.ui.total_prod_rev_excel_widget.setRowCount(len(sorted_dates))
            header_labels = ['Date'] + sorted(all_uwis)
            header_labels = [str(label) for label in header_labels] 
            self.ui.total_prod_rev_excel_widget.setHorizontalHeaderLabels(header_labels)

            # Populate table
            for row_index, date in enumerate(sorted_dates):
                self.ui.total_prod_rev_excel_widget.setItem(row_index, 0, QTableWidgetItem(str(date)))  # Date column
                for col_index, uwi in enumerate(header_labels[1:]):  # Exclude the first 'Date' column
                    revenue = date_uwi_revenue_dict[date].get(uwi, '')  # Get revenue for the UWI on the date (if available)
                    self.ui.total_prod_rev_excel_widget.setItem(row_index, col_index + 1, QTableWidgetItem(str(revenue)))

        except sqlite3.Error as e:
            print("Error populating tab 2:", e)
        print("pop2 emd")




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
            net_price_oil = nri*(oil_price - oil_price_dif)*(1-tax_rate/100)*(1-royalty/100)
            net_price_gas = nri*(gas_price - gas_price_dif)*(1-tax_rate/100)*(1-royalty/100)


            # Update QLabel with calculated net price
            self.ui.net_price_oil.setText(f"{net_price_oil:.2f}")
            self.ui.net_price_gas.setText(f"{net_price_gas:.2f}")

        except ValueError:

            pass  # Handle invalid input

    def model_parameters(self):
        # Get current UWI index
        self.db_manager = DatabaseManager(self.db_path)
        self.db_manager.connect()

        self.uwi_model_data = self.db_manager.retrieve_model_properties(self.current_uwi)

        self.current_error_row = self.db_manager.retrieve_error_row(self.current_uwi)
 

        initial_gas_prod_rate = float(self.uwi_model_data['max_gas_production'])
        self.ui.initial_gas_production_rate_input.setText(str(initial_gas_prod_rate))
        initial_gas_decline_rate = float(self.uwi_model_data['di_gas'])
        self.ui.initial_gas_decline_rate_input.setText(str(initial_gas_decline_rate))
        b_factor_gas = float(self.uwi_model_data['b_factor_gas'])
        self.ui.gas_b_factor_input.setText(str(b_factor_gas))
    
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

        oil_b_factor = float(self.uwi_model_data['b_factor_oil'])
        self.ui.oil_b_factor_input.setText(str(oil_b_factor))

        min_dec_oil = float(self.uwi_model_data['min_dec_oil'])
        self.ui.min_dec_oil.setText(str(min_dec_oil))

 
        sum_error_oil_value = self.current_error_row['sum_error_oil'].values
 
        sum_error_oil_value = round(sum_error_oil_value[0], 2)
        self.ui.error_oil.setText(str(sum_error_oil_value))

        current_error_gas_values = self.current_error_row['sum_error_gas'].values
        current_error_gas = round(current_error_gas_values[0], 2)
        self.ui.error_gas.setText(str(current_error_gas))
        print("error")


        if self.open:

            # Set values for each parameter
            self.ui.end_forcast_type_value = self.uwi_model_data.get("economic_limit_type", "").iloc[0]
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


        self.uwi_model_data = []
        # Get the current indexed UWI
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
        economic_limit_type = self.ui.end_forcast_type.currentText()
        economic_limit_date = self.ui.ecl_date.text()
        net_price_oil = self.ui.net_price_oil.text()
        net_price_gas = self.ui.net_price_gas.text()


                # Create a dictionary with the model parameters
        # Create a dictionary with the model parameters
        updated_model_data = {
            'UWI': self.current_uwi,
            'max_oil_production': float(max_oil_production),
            'max_gas_production': float(max_gas_production),
            'max_oil_production_date': pd.to_datetime(max_oil_production_date),
            'max_gas_production_date': pd.to_datetime(max_gas_production_date),
            'di_oil': float(di_oil),
            'di_gas': float(di_gas),
            'b_factor_oil': float(oil_b_factor),
            'b_factor_gas': float(gas_b_factor),
            'min_dec_oil': float(min_dec_oil),
            'min_dec_gas': float(min_dec_gas),
            'discount_rate': float(discount_rate),
            'working_interest': float(working_interest),
            #'net_revenue' : net_revenue,
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
            'net_price_gas' : float(net_price_gas)
            
        }
        self.ui.calculate_net_price()
    
        self.uwi_model_data.append(updated_model_data)
   
        
        self.db_manager = DatabaseManager(self.db_path)
        self.db_manager.connect()
        self.uwi_combined_df = self.db_manager.retrieve_prod_rates_by_uwi(self.current_uwi)

        
        self.uwi_production_rates_data, self.uwi_error, self.uwi_model_data = self.dca.update_prod_rate(self.uwi_model_data, self.uwi_combined_df, iterate)
        self.uwi_error = self.dca.uwi_error


        #self.regenerate_html_for_uwi(self.current_uwi)
        self.update_db()
        self.update_displays()
        self.regenerated = False
            


    def update_db(self):
        self.db_manager = DatabaseManager(self.db_path)
        self.db_manager.connect()
        pd.set_option('display.max_rows', None)
        pd.set_option('display.max_columns', None)

    
        # Update model properties
    
        df_uwi_model_data = pd.DataFrame([self.uwi_model_data], index=[0])
        print(df_uwi_model_data)
        print(df_uwi_model_data.dtypes)
        self.db_manager.update_model_properties(df_uwi_model_data)


        self.db_manager.update_uwi_prod_rates(self.uwi_production_rates_data)
        

        self.db_manager.update_uwi_errors(self.uwi_error)


    def iterate_di(self):
        self.iterate = True
        self.update_decline_curve(iterate=True)
        self.iterate = False

    def navigate_back(self):
        #self.ui.disconnect_parameters_triggers(self)
        if self.current_uwi_index > 0:
            self.current_uwi_index -= 1
            self.update_displays()
            self.update_navigation_buttons()
            self.check_model_status_and_set_icon()
    def navigate_forward(self):
        
#Window Navigation
        #self.ui.disconnect_parameters_triggers(self)
        if self.current_uwi_index < len(self.uwi_list) - 1:
            self.current_uwi_index += 1
            self.update_displays()
            self.update_navigation_buttons()
            self.check_model_status_and_set_icon()





    def update_navigation_buttons(self):
        # Check if at the first UWI
        if self.current_uwi_index == 0:
            self.ui.back_button.setEnabled(False)
        else:
            self.ui.back_button.setEnabled(True)

        # Check if at the last UWI
        if self.current_uwi_index >= len(self.uwi_list) - 1:

            
            self.ui.forward_button.setEnabled(False)
        else:
            self.ui.forward_button.setEnabled(True)

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


    def delete_well(self):

        
    
        # Check if there are wells to delete
        if self.uwi_list:
            try:
                # Remove UWI from all relevant tables in the database
                print(self.current_uwi)
                self.db_manager.delete_uwi_records(self.current_uwi)

                # Remove UWI from uwi_list
                del self.uwi_list[self.current_uwi_index]

                 #Update current index and displays
                if self.current_uwi_index >= len(self.uwi_list):
                    self.current_uwi_index = len(self.uwi_list) - 1
                self.update_displays()
                self.update_navigation_buttons()

            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to delete well: {str(e)}", QMessageBox.Ok)




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

if __name__ == "__main__":
    app = QApplication(sys.argv)
    main_window = MainWindow()
    main_window.show()
    sys.exit(app.exec_())