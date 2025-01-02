
import numpy as np
import pandas as pd
import math
from PyQt5.QtCore import QDateTime
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QProgressBar, QLabel, QApplication

from PyQt5.QtCore import Qt
from PyQt5.QtCore import Qt, QTimer

import time


class ProgressBarDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        # Set up the progress bar
        self.progress_bar = QProgressBar(self)
        self.progress_bar.setMaximum(10)
        self.progress_bar.setValue(10)
        self.progress_bar.setAlignment(Qt.AlignCenter)

        # Layout manager
        layout = QVBoxLayout()
        layout.addWidget(self.progress_bar)
        self.setLayout(layout)

        # Window settings
        self.setWindowTitle('Progress Bar')
        self.setGeometry(300, 300, 250, 50)
        self.show()

        # Timer setup
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_progress)
        self.timer.start(1000)  # Update every second

    def update_progress(self):
        current_value = self.progress_bar.value()
        if current_value > 0:
            self.progress_bar.setValue(current_value - 1)
        else:
            self.timer.stop()
            self.accept()  

class DeclineCurveAnalysis:
    def __init__(self, combined_df, model_data, iterate_di, iterate_bfactor, load_gas, load_oil, uwi_list):
        self.model_data = model_data
        self.uwi_model_data = None
        self.combined_df = combined_df
        self.combined_df_extended = None
        self.production_rates_data = pd.DataFrame()
        self.updated_production_rates_data = pd.DataFrame()
        self.production_rates = None 
        self.updated_production_rates_data = None
        self.prod_rates_all = pd.DataFrame()
        self.prod_rates_updated = pd.DataFrame
        self.sum_of_errors = pd.DataFrame()
        self.best_params = None
        self.results = []
        self.uwi_list = uwi_list
 
        self.iterate_di = iterate_di
        self.iterate_di = iterate_di.lower() == 'true'


        self.economic_limit_oil = 250
        self.economic_limit_gas = 1000
        self.uwi_error = pd.DataFrame()

        self.best_di = False
        self.best_error_oil = None  # Initialize with positive infinity
        self.best_error_gas = None # Initialize with positive infinity
        self.best_di_oil = None  # Initialize as None
        self.best_di_gas = None
        self.iterate_bfactor = False
        self.uwi_combined_df = pd.DataFrame()
        self.uwi_production_rates = None
        self.load_oil = load_oil
        self.load_gas = load_gas
        #print(load_oil, load_gas)
        self.calculate_production_rates()

        # Convert model_data to DataFrame

    

    def calculate_production_rates(self):



        self.prod_rates_all = self.combined_df.copy()  # Make a copy to avoid modifying the original DataFrame
        

        for uwi, group in self.prod_rates_all.groupby('uwi'):
            group = group.sort_values(by='date').reset_index(drop=True)
            self.uwi_model_data = next((data for data in self.model_data if data['uwi'] == uwi), None)
    
            if self.uwi_model_data:
                # Calculate production rates for the current 
                self.uwi_combined_df = group.sort_values(by='date')
                self.iterate_nominal_di(self.uwi_model_data, uwi)
                
                # Convert the list of dictionaries to a DataFrame
                production_rates_df = pd.DataFrame(self.uwi_production_rates)

                # Add production rate columns to the combined DataFrame
                self.prod_rates_all.loc[self.prod_rates_all['uwi'] == uwi, 'q_oil'] = production_rates_df['q_oil'].values
                self.prod_rates_all.loc[self.prod_rates_all['uwi'] == uwi, 'q_gas'] = production_rates_df['q_gas'].values
                self.prod_rates_all.loc[self.prod_rates_all['uwi'] == uwi, 'error_oil'] = abs((self.prod_rates_all['oil_volume']-self.prod_rates_all['q_oil'])/self.prod_rates_all['oil_volume'])*100
                self.prod_rates_all.loc[self.prod_rates_all['uwi'] == uwi, 'error_gas'] = abs((self.prod_rates_all['gas_volume']-self.prod_rates_all['q_gas'])/self.prod_rates_all['gas_volume'])*100
            #print(self.uwi_error)
            self.sum_of_errors = self.sum_of_errors.append(self.uwi_error, ignore_index=True)
   

        # Convert the list of dictionaries to a DataFrame
        self.sum_of_errors = pd.DataFrame(self.sum_of_errors)
        print(uwi)
        #self.iterate()
        
        return self.prod_rates_all, self.sum_of_errors
    def update_prod_rate(self, updated_model, prod_rates_all):
        self.iterate_di = False
        #print(self.sum_of_errors)
        self.prod_rates_all = prod_rates_all

        self.uwi_model_data = updated_model[0]  # Assuming updated_model is a list of dictionaries

        # Assuming only one uwi in the updated_model_data list
        uwi = self.uwi_model_data['uwi']
        uwi_combined_df = self.prod_rates_all[self.prod_rates_all['uwi'] == uwi]

        # Calculate updated production rates
        updated_production_rates_data = self._calculate_production_rates_for_uwi_individual(self.uwi_model_data, uwi_combined_df, uwi)
        updated_production_rates_df = pd.DataFrame(updated_production_rates_data)

        # Update production rates and errors for the specific uwi
        for index, row in updated_production_rates_df.iterrows():
            mask = (self.prod_rates_all['uwi'] == row['uwi']) & (self.prod_rates_all['date'] == row['date'])
            self.prod_rates_all.loc[mask, 'q_oil'] = row['q_oil']
            self.prod_rates_all.loc[mask, 'q_gas'] = row['q_gas']
            self.prod_rates_all.loc[mask, 'error_oil'] = row['error_oil']
            self.prod_rates_all.loc[mask, 'error_gas'] = row['error_gas']

        #print(self.uwi_error)
       #print(self.sum_of_errors)
        for index, row in self.uwi_error.iterrows():
            # Find the index in self.sum_of_errors corresponding to the current 'uwi'
            index_to_update = self.sum_of_errors.index[self.sum_of_errors['uwi'] == row['uwi']]

            # Check if the index is found
            if not index_to_update.empty:
                index_to_update = index_to_update[0]  # Extract the index value from the Pandas series
        
                # Update the values in self.sum_of_errors with the median error values
                self.sum_of_errors.at[index_to_update, 'sum_error_gas'] = row['sum_error_gas']
                self.sum_of_errors.at[index_to_update, 'sum_error_oil'] = row['sum_error_oil']
    
        # Optionally, print to verify the update
        #print("Updated self.sum_of_errors:\n", self.sum_of_errors)

        return self.prod_rates_all, self.sum_of_errors
    def _calculate_production_rates_for_uwi_individual(self, uwi_model_data, uwi_combined_df, uwi, di_gas = None, di_oil = None):
        self.uwi_error = pd.DataFrame()
        q_oil = None 
        q_gas = None
        error_oil = None
        error_gas = None
        #print(uwi)

        if self.load_oil:
            
            if self.iterate_di:
                di_oil = di_oil
            else:
                di_oil = float(uwi_model_data['di_oil'])
            qi_oil = float(uwi_model_data['max_oil_production'])
            oil_b_factor = float(uwi_model_data['oil_b_factor'])
            max_oil_date = uwi_model_data['max_oil_production_date']
            min_dec_oil = float(uwi_model_data['min_dec_oil'])
            max_oil_date_timestamp = pd.to_datetime(max_oil_date)
            if di_oil == 100:
                di_oil == 99.9

            nominal_di_oil = (((1 - (di_oil / 100)) ** (-oil_b_factor)) - 1) / oil_b_factor if oil_b_factor != 0 else di_oil / 100
                        # Calculate time_dt_oil
            
            time_switch_oil = None
            q_prev_oil = None
        if self.load_gas:
            if self.iterate_di:
                di_gas = di_gas
                #print(di_gas)
            else:
                di_gas = float(uwi_model_data['di_gas'])
            qi_gas = float(uwi_model_data['max_gas_production'])
            gas_b_factor = float(uwi_model_data['gas_b_factor'])
            max_gas_date = uwi_model_data['max_gas_production_date']
            max_gas_date_timestamp = pd.to_datetime(max_gas_date)
            min_dec_gas = float(uwi_model_data['min_dec_gas'])
            if di_gas == 100:
                di_gas = 99.9       
            nominal_di_gas = (((1 - (di_gas / 100)) ** (-gas_b_factor)) - 1) / gas_b_factor if gas_b_factor != 0 else di_gas / 100
           # Calculate time_dt_gas
            time_switch_gas = None
            q_prev_gas = None
        production_rates_data = []
    
        for index, row in uwi_combined_df.iterrows():
            row_date_timestamp = pd.to_datetime(row['date'])
            row_uwi = row['uwi']
            q_gas=q_gas
            print(q_gas)

            # Calculate gas production if gas data is available
            if self.load_gas == True and (q_gas == None or q_gas >= self.economic_limit_gas):

                gas_volume = row['gas_volume']
                time_gas_years = (row_date_timestamp - max_gas_date_timestamp).days / 365
                if nominal_di_gas == 0:
                    time_dt_gas = np.nan  # Set to NaN if nominal_di_gas is zero
                else:
                    time_dt_gas = nominal_di_gas / (1 + gas_b_factor * nominal_di_gas * time_gas_years)
    
            
                if time_gas_years < 0:
                    q_gas = None

                elif time_dt_gas < (min_dec_gas / 100):
                    if time_switch_gas is None:
                        # Store the time when switching to exponential decline
                        time_switch_gas = time_gas_years
                        # Store the previous production rate for exponential decline calculation
                        q_prev_gas = production_rates_data[-1]['q_gas']
                    # Calculate the exponential decline for gas production rate
                    time_gas_years = time_gas_years - time_switch_gas
                    if time_gas_years == None or q_prev_gas == None:
                        q_gas = 0
                    else:
                        q_gas = q_prev_gas * math.exp(-(min_dec_gas / 100 * time_gas_years))

                elif gas_b_factor == 0:
                    q_gas = qi_gas * math.exp(-(nominal_di_gas * time_gas_years))
                elif gas_b_factor == 1.0:
                    q_gas = qi_gas / (1 + nominal_di_gas * time_gas_years)
                else:
                    q_gas = qi_gas / (1 + (gas_b_factor * nominal_di_gas * time_gas_years)) ** (1 / gas_b_factor) if not np.isnan(time_gas_years) else np.nan
                if gas_volume > 0 and q_gas is not None:
                    error_gas = float(abs((gas_volume - q_gas) / gas_volume) * 100)
                else:
                    error_gas = 0 
            else:
                error_gas = 0
                q_gas = 0
                gas_volume= 0
           
            q_oil = qi_oil   # Calculate oil production if oil data is available
            if self.load_oil == True and (q_oil == None or q_oil >= self.economic_limit_oil):
                oil_volume = row['oil_volume']
                time_oil_years = (row_date_timestamp - max_oil_date_timestamp).days / 365
                if nominal_di_oil == 0:
                    time_dt_oil = np.nan  # Set to NaN if nominal_di_oil is zero
                else:
                    time_dt_oil = nominal_di_oil / (1 + oil_b_factor * nominal_di_oil * time_oil_years)

                if time_oil_years < 0:
                    q_oil = None

                elif time_dt_oil < (min_dec_oil / 100):
                    if time_switch_oil is None:
                        # Store the time when switching to exponential decline
                        time_switch_oil = time_oil_years
                        # Store the previous production rate for exponential decline calculation
                        q_prev_oil = production_rates_data[-1]['q_oil']

                    # Calculate the exponential decline for oil production rate
                    time_oil_years = time_oil_years - time_switch_oil
                    if time_oil_years  == None or q_prev_oil == None:
                        q_oil = 0
                    else:
                        q_oil = q_prev_oil * math.exp(-(min_dec_oil / 100 * time_oil_years))


                elif oil_b_factor == 0:
                    q_oil = qi_oil * math.exp(-(nominal_di_oil * time_oil_years))
                elif oil_b_factor == 1.0:
                    q_oil = qi_oil / (1 + nominal_di_oil * time_oil_years)
                else:
                    q_oil = qi_oil / (1 + (oil_b_factor * nominal_di_oil  * time_oil_years))** (1 / oil_b_factor) if not np.isnan(time_oil_years) else np.nan
                    
                if oil_volume > 0 and q_oil is not None:
                    error_oil = float(abs((oil_volume - q_oil) / oil_volume) * 100)
                else:
                    error_oil = 0 
            else:
                    error_oil = 0
                    q_oil = 0
                    oil_volume = 0



            production_rates_data.append({
                    'uwi': row_uwi,
                    'date': row_date_timestamp,
                    'gas_volume': row.get('gas_volume', np.nan),
                    'q_gas': q_gas,
                    'error_gas': error_gas,
                    'oil_volume': row.get('oil_volume', np.nan),
                    'q_oil': q_oil,
                    'error_oil': error_oil
                })

        production_df = pd.DataFrame(production_rates_data)
        self.uwi_error = production_df.groupby('uwi')[['error_oil', 'error_gas']].median().reset_index()
        self.uwi_error = self.uwi_error.rename(columns={'error_oil': 'sum_error_oil', 'error_gas': 'sum_error_gas'})
     
        return production_rates_data




    def iterate_nominal_di(self, uwi_model_data, uwi):
                # Core logic for calculating production rates for a single uwi
        self.best_error_oil = float('inf')
        self.best_error_gas = float('inf')
        self.best_di_oil = None
        self.best_di_gas = None
        error_oil = None
        error_gas = None
        di_oil = None
        di_gas = None
      


        if self.iterate_di == False:
            di_oil = float(uwi_model_data['di_oil']) if self.load_oil == True else None
            di_gas = float(uwi_model_data['di_gas']) if self.load_gas == True else None
            self.uwi_production_rates = self._calculate_production_rates_for_uwi_individual(self.uwi_model_data, self.uwi_combined_df, uwi, di_gas, di_oil)
        else:
            for di_value in range(40, 95, 5):
                
                di_oil = di_value
                di_gas = di_value
                #print(di_gas, di_oil)
                self.uwi_production_rates = self._calculate_production_rates_for_uwi_individual(self.uwi_model_data, self.uwi_combined_df, uwi, di_gas, di_oil)

                error_oil = self.uwi_error['sum_error_oil'].iloc[0]  # Access the error for the current iteration
                error_gas = self.uwi_error['sum_error_gas'].iloc[0]


                #print("Current error oil:", error_oil)
                #print("Current error gas:", error_gas)
                #print(self.best_error_oil, self.best_di_oil)

                # Update the best error and best di values based on the current iteration
                if error_oil < self.best_error_oil:
                    self.best_error_oil = error_oil
                    self.best_di_oil = di_oil
                    #print('oilyah', self.best_di_oil)

                if error_gas < self.best_error_gas:
                    self.best_error_gas = error_gas
                    self.best_di_gas = di_gas

            # Print the best di values found
            #print(f"Best di value for oil found: {self.best_di_oil}")
           
            # Use the best values for the final iteration
            di_oil = self.best_di_oil
            di_gas = self.best_di_gas
            uwi_model_data['di_oil'] =  di_oil       
            uwi_model_data['di_gas'] = di_gas
            self.uwi_production_rates = self._calculate_production_rates_for_uwi_individual(self.uwi_model_data, self.uwi_combined_df, uwi, di_gas, di_oil)






   