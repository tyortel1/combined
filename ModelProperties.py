import numpy as np
import pandas as pd
import math
from PyQt5.QtCore import QDateTime
from ui_main import UI_main




class  ModelProperties:
    def __init__(self, combined_df):
        self.ui = UI_main()
        self.combined_df = combined_df
        self.model_data = []
        self.load_oil = True
        self.load_gas = True
        self.iterate_di = False

        # Convert model_data to DataFrame


    def dca_model_properties(self, default_properties): 
        self.default_properties = default_properties
 

        for uwi, group in self.combined_df.groupby('UWI'):
            group = group.sort_values(by='date').reset_index(drop=True)
            max_oil_volume, max_gas_volume = 0, 0
            one_year_oil_volume, one_year_gas_volume = 0, 0
            di_oil, di_gas = 0, 0
            max_oil_production_date, max_gas_production_date = 0, 0



            if 'oil_volume' in group.columns and group['oil_volume'].notna().any():
            # Find the index of the maximum oil and gas volumes
                max_oil_index = group['oil_volume'].idxmax()
                max_oil_volume = group.loc[max_oil_index, 'oil_volume']
                max_oil_volume_days = group.loc[max_oil_index, 'cumulative_days']
                last_index_value = group.tail(1).index[-1]
                
                            # Calculate the index of the row 12 lines after the maximum oil row
                if len(group) >= max_oil_index + 11:
                    one_year_oil_row_index = max_oil_index + 11
                else:
                    one_year_oil_row_index = group.index[-1]   # Use the index of the last row
                one_year_oil_volume = group.loc[one_year_oil_row_index, 'oil_volume']

                if max_oil_volume != 0:
                    di_oil = (max_oil_volume - one_year_oil_volume) / max_oil_volume * 100
                    if di_oil == 100:
                       di_oil=99
                else:
                    di_oil = 0

                #print(di_oil)
                max_oil_production_date = group.loc[max_oil_index, 'date']
                max_oil_production_date = pd.to_datetime(max_oil_production_date).strftime('%Y-%m-%d')
            else:
                self.load_oil = False


            if 'gas_volume' in group.columns and group['gas_volume'].notna().any():
                max_gas_index = group['gas_volume'].idxmax()
                max_gas_volume = group.loc[max_gas_index, 'gas_volume']
                max_gas_volume_days = group.loc[max_gas_index, 'cumulative_days']
                last_index_value = group.tail(1).index[-1]
                if len(group) >= max_gas_index + 11:
                    one_year_gas_row_index = max_gas_index + 11
                else:
                    one_year_gas_row_index = last_index_value  # Use the index of the last row
                one_year_gas_volume = group.loc[one_year_gas_row_index, 'gas_volume']
                if max_gas_volume != 0:
                    di_gas = (max_gas_volume - one_year_gas_volume) / max_gas_volume * 100
                    if di_gas == 100:
                        di_gas = 99
                else:
                    di_gas = 0
              
                                # Extract the date from the row with the maximum gas volume
                max_gas_production_date = group.loc[max_gas_index, 'date']
                max_gas_production_date = pd.to_datetime(max_gas_production_date).strftime('%Y-%m-%d')
            else:
                self.load_gas = False

            # Set b factor to 1.05 for both oil and gas
           # Set default values for b factors and min dec
            b_factor_oil = self.default_properties.get("oil_b_factor")
            b_factor_gas = self.default_properties.get("gas_b_factor")
            min_dec_oil = self.default_properties.get("min_dec_oil")
            min_dec_gas = self.default_properties.get("min_dec_gas")
            iterate_di_text = self.default_properties.get("iterate_di")
            if iterate_di_text == "True":
                self.iterate_di = True
            elif iterate_di_text == "False":
                self.iterate_di = False
            else:
                # Handle the case where iterate_di_text is neither "True" nor "False"
                # For example, you might want to set a default value
                self.iterate_di  = False 
           

            max_oil_volume = round(max_oil_volume, 2)
            max_gas_volume = round(max_gas_volume, 2)
            one_year_oil_volume = round(one_year_oil_volume, 2)
            one_year_gas_volume = round(one_year_gas_volume, 2)
            di_oil = round(di_oil, 2)
            di_gas = round(di_gas, 2)
            b_factor_oil = round(b_factor_oil, 2)
            b_factor_gas = round(b_factor_gas, 2)
            min_dec_oil = round(min_dec_oil, 2)
            min_dec_gas = round(min_dec_gas, 2)
            # Store the data for the current UWI
            uwi_data = {
                        'UWI': uwi,
                        'max_oil_production': max_oil_volume,
                        'max_gas_production': max_gas_volume,
                        'max_oil_production_date': max_oil_production_date,
                        'max_gas_production_date': max_gas_production_date,
                        'one_year_oil_production': one_year_oil_volume,
                        'one_year_gas_production': one_year_gas_volume,
                        'di_oil': di_oil,
                        'di_gas': di_gas,
                        'b_factor_oil': b_factor_oil,
                        'b_factor_gas': b_factor_gas,
                        'min_dec_oil' : min_dec_oil,
                        'min_dec_gas' : min_dec_gas,
                        'model_oil': 'exponential',
                        'model_gas': 'exponential',
                        # Add default properties
                        'gas_b_factor': self.default_properties.get("gas_b_factor", ""),
                        'min_dec_gas': self.default_properties.get("min_dec_gas", ""),
                        'oil_b_factor': self.default_properties.get("oil_b_factor", ""),
                        'min_dec_oil': self.default_properties.get("min_dec_oil", ""),
                        #'cf_start_date': self.default_properties.get("cf_start_date", QDateTime.currentDateTime().toString("yyyy-MM-dd")),
                        'oil_price': self.default_properties.get("oil_price", ""),
                        'gas_price': self.default_properties.get("gas_price", ""),
                        'oil_price_dif': self.default_properties.get("oil_price_dif", ""),
                        'gas_price_dif': self.default_properties.get("gas_price_dif", ""),
                        'discount_rate': self.default_properties.get("discount_rate", ""),
                        'working_interest': self.default_properties.get("working_interest", ""),
                        'royalty': self.default_properties.get("royalty", ""),
                        #'net_revenue': self.default_properties.get("net_revenue", ""),
                        'tax_rate': self.default_properties.get("tax_rate", ""),
                        'capital_expenditures': self.default_properties.get("capital_expenditures", ""),
                        'operating_expenditures': self.default_properties.get("operating_expenditures", ""),
                        'economic_limit_type': self.default_properties.get("economic_limit_type", ""),
                        'economic_limit_date': self.default_properties.get("economic_limit_date", QDateTime.currentDateTime().toString("yyyy-MM-dd")),
                        'net_price_oil' : self.default_properties.get("net_price_oil", ""),
                        'net_price_gas' : self.default_properties.get("net_price_gas", ""),
                        'gas_model_status': self.load_gas,  # Adding new column 'gas_model_status' with initial value 'on'
                        'oil_model_status': self.load_oil   # Adding new column 'oil_model_status' with ini
                    }

            
            # Append the uwi_data to the list
            self.model_data.append(uwi_data)

        return self.model_data, self.iterate_di
