
from pickle import FALSE
import numpy as np
import pandas as pd
import math
from PyQt5.QtCore import QDateTime
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QProgressBar, QLabel, QApplication
from scipy.optimize import curve_fit
from PyQt5.QtCore import Qt
from PyQt5.QtCore import Qt, QTimer

import time



class DeclineCurveAnalysis:
    def __init__(self, combined_df=None, model_data=None, iterate_di=None, uwi_list=None):
        self.model_data = model_data

        self.uwi_model_data = None
        self.combined_df = combined_df
        self.uwi_combined_df = pd.DataFrame()
        self.uwi_prod_rates_all = pd.DataFrame()
        self.production_rates_data = []
        self.production_rates_temp = pd.DataFrame()
        self.production_rates = None 
        self.prod_rates_all = pd.DataFrame()
        self.sum_of_errors = pd.DataFrame()
        self.best_params = None
        self.results = []
        self.uwi_list = uwi_list
 


        self.economic_limit_oil = 250
        self.economic_limit_gas = 1000
        self.uwi_error = pd.DataFrame()

        self.best_di = False
        self.update = False
        self.best_error_oil = None  # Initialize with positive infinity
        self.best_error_gas = None # Initialize with positive infinity
        self.best_di_oil = None  # Initialize as None
        self.best_di_gas = None
        self.load_oil = True
        self.load_gas = True
        self.planned = True

        if iterate_di:
            self.iterate_di= iterate_di
            self.iterate_di = iterate_di.lower() == 'true'
        else:
             self.iterate_di = False 

        self.row = None


                # Initialize error tracking and best values
        self.uwi_error = pd.DataFrame()
        self.best_error_oil = float('inf')
        self.best_error_gas = float('inf')
        self.best_di_oil = None
        self.best_di_gas = None

        # Initialize static parameters for production calculations
        self.di_oil = None
        self.qi_oil = None
        self.oil_b_factor = None
        self.max_oil_date_timestamp = None
        self.min_dec_oil = None
        self.nominal_di_oil = None
        self.time_switch_oil = None
        self.q_prev_oil = None
        self.time_switch_oil = None
        self.q_prev_oil = None

        self.di_gas = None
        self.qi_gas = None
        self.gas_b_factor = None
        self.max_gas_date_timestamp = None
        self.min_dec_gas = None
        self.nominal_di_gas = None
        self.time_switch_gas = None
        self.q_prev_gas = None
        self.time_switch_gas = None
        self.q_prev_gas = None
    

        # Initialize error and production rate variables
        self.error_oil = None
        self.error_gas = None
        self.q_oil = None
        self.q_gas = None
        self.current_uwi = None

    def calculate_production_rates(self):
        self.prod_rates_all = self.combined_df.copy()  # Make a copy to avoid modifying the original DataFrame
        self.production_rates_temp = pd.DataFrame()
        total_uwis = self.prod_rates_all['uwi'].nunique()

        #print(f"Starting with {total_uwis} unique uwis.")



        for uwi, group in self.prod_rates_all.groupby('uwi'):
            group = group.sort_values(by='date').reset_index(drop=True)
            self.uwi_model_data = next((data for data in self.model_data if data['uwi'] == uwi), None)
            
    
            if self.uwi_model_data:
                self.load_oil = bool(self.uwi_model_data.get('oil_model_status', 0))
                self.load_gas = bool(self.uwi_model_data.get('gas_model_status', 0))
                #print(self.load_oil)
                # Calculate production rates for the current 
                
                self.uwi_combined_df = group.sort_values(by='date')
                self.iterate_nominal_di()
                self.forcast_rates()
                

                #print("load", self.production_rates_data)
                # Convert the list of dictionaries to a DataFrame
                if self.production_rates_data:  # Check if there is data to process
                    temp_df = pd.DataFrame(self.production_rates_data)
                    self.production_rates_temp = pd.concat([self.production_rates_temp, temp_df], ignore_index=True)

            self.sum_of_errors = self.sum_of_errors.append(self.uwi_error, ignore_index=True)
            total_uwis -= 1
            print(f"Finished processing uwi {uwi}. {total_uwis} uwis remaining.")
   
        self.prod_rates_all = self.production_rates_temp.copy()

        self.sum_of_errors = pd.DataFrame(self.sum_of_errors)  
        #print(self.model_data)
        model_data_df = pd.DataFrame(self.model_data)
        return self.prod_rates_all, self.sum_of_errors, model_data_df

    def planned_prod_rate(self, updated_model, uwi_combined_df=None, iterate = False):
        print(updated_model)

        self.iterate_di = iterate
        if not updated_model.empty:
            self.uwi_model_data = updated_model.iloc[0].to_dict()  # Convert the first row to a dictionary
            self.current_uwi = self.uwi_model_data['uwi']
        else:
            raise ValueError("Empty DataFrame received in planned_prod_rate")
        self.current_uwi = self.uwi_model_data['uwi']
        print(self.uwi_model_data)
        self.production_rates_data = None
        self.load_oil = bool(self.uwi_model_data.get('oil_model_status', 0))
        self.load_gas = bool(self.uwi_model_data.get('gas_model_status', 0))
        self.di_oil = float(self.uwi_model_data['di_oil']) if self.load_oil == True else None
        self.di_gas = float(self.uwi_model_data['di_gas']) if self.load_gas == True else None
        self.qi_oil = float(self.uwi_model_data['max_oil_production']) if self.load_oil == True else None
        self.qi_gas = float(self.uwi_model_data['max_gas_production']) if self.load_gas == True else None
        #print(self.load_oil)

        self.initialize_gas_parameters()
        self.initialize_oil_parameters()
        self.forcast_rates()

        self.uwi_production_rates_data = pd.DataFrame(self.production_rates_data)
        self.uwi_error = pd.DataFrame(self.uwi_error)
        



        self.update = False
        self.iterate_di = False
        return self.uwi_production_rates_data, self.uwi_error, self.uwi_model_data

    def update_prod_rate(self, updated_model, uwi_combined_df=None, iterate = False):
        print(updated_model)

        self.iterate_di = iterate
        self.update = True
                # Check if uwi_combined_df is provided
        if uwi_combined_df is not None:
            self.uwi_combined_df = uwi_combined_df
            print("Using provided uwi_combined_df")
        else:
            iterate = False
            print("No uwi_combined_df provided, proceeding without it")
        #print("df", self.uwi_combined_df)
        self.uwi_model_data = updated_model.iloc[0].to_dict() 
        #print(self.uwi_model_data)
        self.current_uwi = self.uwi_model_data['uwi']
        #print(self.uwi_model_data)
        self.production_rates_data = None
        self.load_oil = bool(self.uwi_model_data.get('oil_model_status', 0))
        self.load_gas = bool(self.uwi_model_data.get('gas_model_status', 0))
        #print(self.load_oil)

        self.iterate_nominal_di()
        self.forcast_rates()
        df_uwi_model_data = pd.DataFrame([self.uwi_model_data])
        self.uwi_production_rates_data = pd.DataFrame(self.production_rates_data)
        self.uwi_error = pd.DataFrame(self.uwi_error)
        



        self.update = False
        self.iterate_di = False
        return self.uwi_production_rates_data, self.uwi_error, df_uwi_model_data

    def iterate_nominal_di(self):
                # Core logic for calculating production rates for a single uwi
        self.best_error_oil = float('inf')
        self.best_error_gas = float('inf')
        self.best_di_oil = None
        self.best_di_gas = None
        self.error_oil = None
        self.error_gas = None
        self.di_oil = None
        self.di_gas = None
        self.time_switch_gas = None
        self.time_switch_oil = None
        self.q_prev_oil = None
        self.q_prev_gas = None
        uwi = self.uwi_model_data['uwi']
   


        if self.iterate_di == False:
          
            self.di_oil = float(self.uwi_model_data['di_oil']) if self.load_oil == True else None
            self.di_gas = float(self.uwi_model_data['di_gas']) if self.load_gas == True else None
            self.qi_oil = float(self.uwi_model_data['max_oil_production']) if self.load_oil == True else None
            self.qi_gas = float(self.uwi_model_data['max_gas_production']) if self.load_gas == True else None
            self.production_rates_data = self._calculate_production_rates_for_uwi_individual()

        else:
            self.iterate_di = False
       
            if self.uwi_model_data:
                
                self.initialize_oil_parameters()
                
                self.initialize_gas_parameters()
                self.qi_oil = float(self.uwi_model_data['max_oil_production']) if self.load_oil == True else None
                self.qi_gas = float(self.uwi_model_data['max_gas_production']) if self.load_gas == True else None

            self.uwi_combined_df['date'] = pd.to_datetime(self.uwi_combined_df['date'])
            filtered_df = self.uwi_combined_df[self.uwi_combined_df['date'] >= self.max_oil_date_timestamp]
            #print(filter)
            q_data_oil = filtered_df['oil_volume'].values
            q_data_gas = filtered_df['gas_volume'].values
   
            filtered_df['date'] = pd.to_datetime(filtered_df['date'])

            t_data = (filtered_df['date'] - self.max_oil_date_timestamp).apply(lambda x: x.days) / 365.25
              

              
            # Set reasonable initial guesses
 


            try:
                                # Set reasonable initial guesses
                initial_guesses_oil = [self.qi_oil, self.nominal_di_oil, self.oil_b_factor]
                bounds_oil = ([self.qi_oil-10000, 1.1 , .05], [self.qi_oil+10000, np.inf, .95])
                popt, _ = curve_fit(DeclineCurveAnalysis.hyperbolic_decline, t_data, q_data_oil, p0=initial_guesses_oil, bounds=bounds_oil)
                qi, di, b = popt
                # Check if b is within the valid range
                if 0 < b < 1:
                    print(f"Fitted parameters for uwi {uwi} - Qi: {qi}, Di: {di}, b-factor: {b}")
                    self.qi_oil = round(qi, 2)
                    self.nominal_di_oil = round(di, 2)
                    self.oil_b_factor = round(b, 2)
                   
                else:
                    print(f"b-factor out of bounds for uwi {uwi}")
            except Exception as e:
                print(f"An error occurred during curve fitting for uwi {uwi}: {e}")


            # Fit the model
            try:
                initial_guesses_gas = [self.qi_gas, self.nominal_di_gas, self.gas_b_factor]
                bounds_gas = ([self.qi_gas, 1.1 , 0.05], [self.qi_gas+1, np.inf, .95])
                popt, _ = curve_fit(DeclineCurveAnalysis.hyperbolic_decline, t_data, q_data_gas, p0=initial_guesses_gas, bounds=bounds_gas)
                qi, di, b = popt
                # Check if b is within the valid range
                if 0 < b < 1:
                    print(f"Fitted parameters for uwi GAS {uwi} - Qi: {qi}, Di: {di}, b-factor: {b}")
                    self.qi_gas = round(qi, 2)
                    self.nominal_di_gas = round(di, 2)
                    self.gas_b_factor = round(b, 2)
           
                else:
                    print(f"b-factor out of bounds for uwi {uwi}")
            except Exception as e:
                print(f"An error occurred during curve fitting for uwi {uwi}: {e}")
        
          
            self.iterate_di = True
            self.production_rates_data = self._calculate_production_rates_for_uwi_individual()
    
            try:
                # Attempt to calculate self.di_oil using the given formula
           
                self.di_oil = round((1- ((1 / (self.nominal_di_oil * self.oil_b_factor + 1)) ** (1 / self.oil_b_factor))) * 100,2)
          
                self.nominal_di_oil = (((1 - (self.di_oil / 100)) ** (-self.oil_b_factor)) - 1) / self.oil_b_factor
             
            except Exception as e:
                # If an error occurs, log the error and set self.di_oil to zero
                #print(f"An error occurred during the calculation of di_oil: {str(e)}")
                self.di_oil = 0
            try:
                # Attempt to calculate self.di_gas using the given formula
                
                self.di_gas = round((1- ((1 / (self.nominal_di_gas * self.gas_b_factor + 1)) ** (1 / self.gas_b_factor))) * 100,2)
                #print(self.di_gas)
                self.nominal_di_gas = (((1 - (self.di_gas / 100)) ** (-self.gas_b_factor)) - 1) / self.gas_b_factor 
           

            except Exception as e:
                # If an error occurs, log the error and set self.di_gas to zero
               # print(f"An error occurred during the calculation of di_gas: {str(e)}")
                self.di_gas = 0

            if self.update == False:
                index_to_update = next((i for i, data in enumerate(self.model_data) if data['uwi'] == uwi), None)

                # If a matching uwi is found, update the dictionary with the new values
                if index_to_update is not None:
                    self.model_data[index_to_update]['max_oil_production'] = self.qi_oil
                    self.model_data[index_to_update]['di_oil'] = self.di_oil
                    self.model_data[index_to_update]['oil_b_factor'] = self.oil_b_factor
                    self.model_data[index_to_update]['max_gas_production'] = self.qi_gas
                    self.model_data[index_to_update]['di_gas'] = self.di_gas
                    self.model_data[index_to_update]['gas_b_factor'] = self.gas_b_factor
              
            else:
                self.uwi_model_data['max_oil_production'] = self.qi_oil
                self.uwi_model_data['di_oil'] = self.di_oil
                self.uwi_model_data['oil_b_factor'] = self.oil_b_factor
                self.uwi_model_data['max_gas_production'] = self.qi_gas
                self.uwi_model_data['di_gas'] = self.di_gas
                self.uwi_model_data['gas_b_factor'] = self.gas_b_factor
                #print(self.uwi_model_data)

        if self.update:
           return self.uwi_model_data
        else:
            return self.model_data

    def hyperbolic_decline(t, qi, di, b):
        return qi / ((1 + b * di * t) ** (1/b))

    def initialize_oil_parameters(self):

        if self.iterate_di == False:
                 # Initialize static parameters for oil
            self.di_oil = 99.9 if self.di_oil == 100 else self.di_oil
            self.di_oil = float(self.uwi_model_data['di_oil']) 
            self.oil_b_factor = float(self.uwi_model_data['oil_b_factor'])
            self.max_oil_date_timestamp = pd.to_datetime(self.uwi_model_data['max_oil_production_date'])
            
            self.nominal_di_oil = (((1 - (self.di_oil / 100)) ** (-self.oil_b_factor)) - 1) / self.oil_b_factor if self.oil_b_factor != 0 else self.di_oil / 100
        self.min_dec_oil = float(self.uwi_model_data['min_dec_oil'])
        self.time_switch_oil = None
        self.q_prev_oil = None

    def initialize_gas_parameters(self):
        # Initialize static parameters for gas
        if self.iterate_di == False:
            self.di_gas = 99.9 if self.di_gas == 100 else self.di_gas
            self.di_gas = float(self.uwi_model_data['di_gas']) 
            self.gas_b_factor = float(self.uwi_model_data['gas_b_factor'])
            self.max_gas_date_timestamp = pd.to_datetime(self.uwi_model_data['max_gas_production_date'])
            self.nominal_di_gas = (((1 - (self.di_gas / 100)) ** (-self.gas_b_factor)) - 1) / self.gas_b_factor if self.gas_b_factor != 0 else self.di_gas / 100
        self.min_dec_gas = float(self.uwi_model_data['min_dec_gas'])
  
        self.time_switch_gas = None
        self.q_prev_gas = None

    def _calculate_production_rates_for_uwi_individual(self):
        self.uwi_error = pd.DataFrame()
        error_oil = None
        error_gas = None
        oil_revenue = 0
        gas_revenue = 0
     

        if self.load_oil:
            self.initialize_oil_parameters()
            
        if self.load_gas:
            self.initialize_gas_parameters()


        self.production_rates_data = []
          
        for index, row in self.uwi_combined_df.iterrows():
            self.row = row
            row_date_timestamp = pd.to_datetime(row['date'])
            cum_oil = row['cumulative_oil_volume']
            cum_gas = row['cumulative_gas_volume']
            net_price_oil = float(self.uwi_model_data['net_price_oil'])
        #print(net_price_oil)
            net_price_gas = float(self.uwi_model_data['net_price_gas'])

            discount_rate = float(self.uwi_model_data['discount_rate'])

            self.current_uwi = row['uwi']
            if self.load_oil:
                oil_volume = row.get('oil_volume')
                q_oil, error_oil = self._calculate_oil_production(row,row_date_timestamp)
                if oil_volume:
                    oil_revenue = oil_volume * net_price_oil
                else:
                    oil_revenue = 0
            else:
                error_oil = 0
                q_oil = 0
                oil_volume= 0

            if self.load_gas:
                q_gas, error_gas = self._calculate_gas_production(row, row_date_timestamp)
                gas_volume = row.get('gas_volume')


                if gas_volume:
                    gas_revenue = gas_volume * net_price_gas
                else:
                    gas_revenue = 0
            else:
                error_gas = 0
                q_gas = 0
                gas_volume= 0

            if self.load_gas and self.load_oil:
                total_revenue = gas_revenue + oil_revenue
           
            elif self.load_gas and not self.load_oil:
                total_revenue = gas_revenue
                oil_revenue = 0

            elif self.load_oil and  not self.load_gas:
                total_revenue = oil_revenue
                gas_revenue = 0
            else:
                total_revenue = 0

            discounted_revenue = total_revenue * 1/(1+discount_rate/100)

           
            self.production_rates_data.append({
                    'uwi': self.current_uwi,
                    'date': row_date_timestamp,
                    'gas_volume': row.get('gas_volume', np.nan),
                    'q_gas': q_gas,
                    'error_gas': error_gas,
                    'oil_volume': row.get('oil_volume', np.nan),
                    'q_oil': q_oil,
                    'error_oil': error_oil,
                    'cumulative_oil_volume' : cum_oil,
                    'cumulative_gas_volume' : cum_gas,
                    'oil_revenue' : oil_revenue,
                    'gas_revenue' : gas_revenue,
                    'total_revenue': total_revenue, 
                    'discounted_revenue':discounted_revenue

                })

        production_df = pd.DataFrame(self.production_rates_data)

  
     
        # Filter rows where 'error_oil' is zero
        filtered_production_df_oil = production_df.loc[production_df['error_oil'] != 0]
        # Check if the filtered DataFrame is empty
        if filtered_production_df_oil.empty:
            # If the filtered DataFrame is empty, set the median error for oil to zero
            uwi_error_oil = 0
        else:
            # If the filtered DataFrame is not empty, calculate the median error for oil
            uwi_error_oil = filtered_production_df_oil['error_oil'].median()

        # Filter rows where 'error_gas' is zero
        filtered_production_df_gas = production_df.loc[production_df['error_gas'] != 0]
        if filtered_production_df_gas.empty:
            # If the filtered DataFrame is empty, set the median error for gas to zero
            uwi_error_gas = 0
        else:
            # If the filtered DataFrame is not empty, calculate the median error for gas
            uwi_error_gas = filtered_production_df_gas['error_gas'].median()

        # Group by 'uwi' and calculate the median of 'error_oil' and 'error_gas' separately for each group

        # Rename the columns for clarity
        self.uwi_error = pd.DataFrame({'uwi': [self.current_uwi], 'sum_error_oil': [uwi_error_oil], 'sum_error_gas': [uwi_error_gas]})

     
        return self.production_rates_data

    def _calculate_oil_production(self, row, row_date_timestamp):
        q_oil = self.qi_oil   # Calculate oil production if oil data is available
        try:
            oil_volume = row['oil_volume']
        except KeyError:
            oil_volume = None
    
        time_oil_years = (row_date_timestamp - self.max_oil_date_timestamp).days / 365
        #print(time_oil_years, row_date_timestamp, self.max_oil_date_timestamp)
        if self.nominal_di_oil == 0:
            time_dt_oil = np.nan  # Set to NaN if nominal_di_oil is zero
        else:
            time_dt_oil = self.nominal_di_oil / (1 + self.oil_b_factor * self.nominal_di_oil * time_oil_years)
            
        if time_oil_years < 0:
            q_oil = None

        elif time_dt_oil < (self.min_dec_oil / 100):
            if self.time_switch_oil is None:
                print("switch_oil")
                # Store the time when switching to exponential decline
                last_row_date = self.production_rates_data[-1]['date']
             
                self.time_switch_oil= (last_row_date - self.max_oil_date_timestamp).days / 365
                if not self.production_rates_data:
                    self.q_prev_oil = 0
                else:
                    self.q_prev_oil = self.production_rates_data[-1]['q_oil']

            # Calculate the exponential decline for oil production rate
            time_oil_years = time_oil_years - self.time_switch_oil
            if time_oil_years  == None or self.q_prev_oil == None:
                q_oil = 0
            else:                   
                q_oil = self.q_prev_oil * math.exp(-(self.min_dec_oil / 100 * time_oil_years))


        elif self.oil_b_factor == 0:
            q_oil = self.qi_oil * math.exp(-(self.nominal_di_oil * time_oil_years))
        elif self.oil_b_factor == 1.0:
            q_oil = self.qi_oil / (1 + self.nominal_di_oil * time_oil_years)
        else:
            q_oil = self.qi_oil / (1 + (self.oil_b_factor * self.nominal_di_oil  * time_oil_years))** (1 / self.oil_b_factor) if not np.isnan(time_oil_years) else np.nan
            #print(q_oil, self.qi_oil, self.oil_b_factor, self.nominal_di_oil, time_oil_years)
        if oil_volume is not None and oil_volume > 0 and q_oil is not None:
            error_oil = float(abs((oil_volume - q_oil) / oil_volume) * 100)
        else:
            error_oil = 0 

        return q_oil, error_oil

    def _calculate_gas_production(self, row, row_date_timestamp):
        #q_gas = self.qi_gas   # Calculate oil production if oil data is available

         
        
        try:
            gas_volume = row['gas_volume']
        except KeyError:
            gas_volume = None


 
        time_gas_years = (row_date_timestamp - self.max_gas_date_timestamp).days / 365
        if self.nominal_di_gas == 0:
            time_dt_gas = np.nan  # Set to NaN if nominal_di_gas is zero
        else:
            time_dt_gas = self.nominal_di_gas / (1 + self.gas_b_factor * self.nominal_di_gas * time_gas_years)
        #print(time_dt_gas)
        #print(row_date_timestamp)
            
        if time_gas_years < 0:
            q_gas = None

        elif time_dt_gas < (self.min_dec_gas / 100):
            #print('YUPPP')
            if self.time_switch_gas is None:
                #print("switch")
                # Store the time when switching to exponential decline
                last_row_date = self.production_rates_data[-1]['date']
             
                self.time_switch_gas= (last_row_date - self.max_gas_date_timestamp).days / 365

             
                # Store the previous production rate for exponential decline calculation
                if not self.production_rates_data:
                    self.q_prev_gas = 0
                else:
                    self.q_prev_gas = self.production_rates_data[-1]['q_gas']
               
            # Calculate the exponential decline for gas production rate
            time_gas_years = time_gas_years - self.time_switch_gas
            if time_gas_years == None or self.q_prev_gas == None:
                q_gas = 0
            else:
                q_gas = self.q_prev_gas * math.exp(-(self.min_dec_gas / 100 * time_gas_years))

        elif self.gas_b_factor == 0:
            q_gas = self.qi_gas * math.exp(-(self.nominal_di_gas * time_gas_years))
        elif self.gas_b_factor == 1.0:
            q_gas = self.qi_gas / (1 + self.nominal_di_gas * time_gas_years)
        else:
            q_gas = self.qi_gas / (1 + (self.gas_b_factor * self.nominal_di_gas * time_gas_years)) ** (1 / self.gas_b_factor) if not np.isnan(time_gas_years) else np.nan
        if gas_volume is not None and gas_volume > 0 and q_gas is not None:
            error_gas = float(abs((gas_volume - q_gas) / gas_volume) * 100)
        else:
            error_gas = 0 
 
        #print(q_gas)       
        return q_gas, error_gas

    def forcast_rates(self):


        print('forecasting')
        #print(self.di_gas)
        #print(self.uwi_model_data)
        # Assuming last recorded data is already in production_rates_data
        if self.production_rates_data:
            last_entry = self.production_rates_data[-1]
            last_date = pd.to_datetime(last_entry['date'])
            last_q_oil = last_entry['q_oil']
            last_q_gas = last_entry['q_gas']
   
        else:
            self.production_rates_data = []

            last_date = pd.to_datetime(self.uwi_model_data['max_oil_production_date'])
            last_q_oil = self.uwi_model_data['max_oil_production']
            last_q_gas = self.uwi_model_data['max_gas_production']
         


        net_price_oil = float(self.uwi_model_data['net_price_oil'])
        #print(net_price_oil)
        net_price_gas = float(self.uwi_model_data['net_price_gas'])

        operatingexpenditures = float(self.uwi_model_data['operating_expenditures'])
        discount_rate = float(self.uwi_model_data['discount_rate'])
        # Start forecasting from the month following the last recorded date
        row_date_timestamp = last_date + pd.DateOffset(months=1)
        economic_limit_type = self.uwi_model_data['economic_limit_type']
        economic_limit_date = pd.Timestamp(self.uwi_model_data['economic_limit_date'])
        uwi = self.uwi_model_data['uwi']
        # Create a synthetic row for forecasting purposes
        forecast_data = []

        # Forecast oil and gas rates
        while True:
            # Calculate the end forecast
                    # Print all variables
            #print("last_q_oil:", last_q_oil)
            #print("last_q_gas:", last_q_gas)
            #print("net_price_oil:", net_price_oil)
            #print("net_price_gas:", net_price_gas)
            #print("operating_expenditures:", operatingexpenditures)
            end_forecast = 0
            if last_q_oil is not None and last_q_gas is not None:
                end_forecast = (last_q_oil * net_price_oil + net_price_gas * last_q_gas) - operatingexpenditures
        
            # Check if the end forecast becomes negative
            if economic_limit_type == 'Net Dollars' and end_forecast < 0:
                print("Warning: End forecast became negative. Stopping forecasting.")
                break  # Exit the loop if the end forecast is negative
        
            # Check if the date exceeds the cutoff
            if economic_limit_type == 'End Date' and row_date_timestamp > economic_limit_date:
                break 
            elif row_date_timestamp > pd.Timestamp('2200-01-01'):
                print("Warning: Generated date is beyond the cutoff date. Stopping forecasting.")
                break  # Exit the loop if the cutoff is exceeded

            # Create a new row
            new_row = {
                'date': row_date_timestamp,
                'uwi': uwi  # Assuming 'uwi' is available in last_entry
            } # Update the date in the row

            if self.load_oil:
                q_oil, error_oil = self._calculate_oil_production(new_row, row_date_timestamp)
                oil_revenue = q_oil * net_price_oil if q_oil is not None else 0
            else:
                q_oil = 0
                error_oil =0
                oil_revenue = 0
     
            new_row.update({
                'oil_volume': np.nan,
                # Update if you calculate volume
                'q_oil': q_oil,
                'error_oil': error_oil,
                'oil_revenue' : oil_revenue
      
            })
            last_q_oil = q_oil



            # Calculate gas production rate and error

            if self.load_gas:
                q_gas, error_gas = self._calculate_gas_production(new_row, row_date_timestamp)
                gas_revenue = q_gas * net_price_gas if q_gas is not None else 0
            else:
                q_gas = 0
                error_gas = 0
                gas_revenue = 0
            total_revenue = gas_revenue + oil_revenue
            discounted_revenue = total_revenue * 1/(1+discount_rate/100)
            new_row.update({
                'gas_volume': np.nan,  # Update if you calculate volume
                'q_gas': q_gas,
                'error_gas': error_gas,
                'gas_revenue' : gas_revenue,
                'total_revenue': total_revenue, 
                'discounted_revenue':discounted_revenue
            })
            last_q_gas = q_gas

            # Append the new row to the production rates data
            self.production_rates_data.append(new_row)


            # Update row_date_timestamp for the next iteration
            row_date_timestamp += pd.DateOffset(months=1)




 
    
        ## Convert the list to DataFrame if necessary
        #production_df = pd.DataFrame(self.production_rates_data)

        #return production_df
        





   
        
            





   