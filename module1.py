def _calculate_production_rates_for_uwi(self, uwi_model_data, uwi_combined_df):
        analysis.profile_function()
        # Core logic for calculating production rates for a single UWI
        di_oil = float(uwi_model_data['di_oil'])
        qi_oil = float(uwi_model_data['max_oil_production'])
        b_factor_oil = float(uwi_model_data['b_factor_oil'])
        di_gas = float(uwi_model_data['di_gas'])
        qi_gas = float(uwi_model_data['max_gas_production'])
        b_factor_gas = float(uwi_model_data['b_factor_gas'])
        max_oil_date = uwi_model_data['max_oil_production_date']
        max_gas_date = uwi_model_data['max_gas_production_date']
        min_dec_oil = float(uwi_model_data['min_dec_oil'])
        min_dec_gas = float(uwi_model_data['min_dec_gas'])
        max_oil_date_timestamp = pd.to_datetime(max_oil_date)
        max_gas_date_timestamp = pd.to_datetime(max_gas_date)
        production_rates_data = []
    
        
        time_switch_gas = None
      
        q_prev_gas = None
        if di_oil == 100:
            di_oil == 99.9
        if di_gas == 100:
            di_gas = 99.9

        nominal_di_oil = self.calculate_nominal_di(di_oil, b_factor_oil, fluid_type='oil')
        nominal_di_gas = self.calculate_nominal_di(di_gas, b_factor_gas, fluid_type='gas')

        #print(di_oil, nominal_di_oil)
        for _, row in uwi_combined_df.iterrows():
            row_date_timestamp = pd.to_datetime(row['date'])
            time_oil = (row_date_timestamp - max_oil_date_timestamp)
            time_gas = (row_date_timestamp - max_gas_date_timestamp)
            time_oil_years = time_oil.days / 365 if time_oil.days >= 0 else np.nan
            time_gas_years = time_gas.days / 365 if time_gas.days >= 0 else np.nan



            # Calculate time_dt_oil
            if nominal_di_oil == 0:
                time_dt_oil = np.nan  # Set to NaN if nominal_di_oil is zero
            else:
                time_dt_oil = nominal_di_oil / (1 + b_factor_oil * nominal_di_oil * time_oil_years)

            # Calculate time_dt_gas
            if nominal_di_gas == 0:
                time_dt_gas = np.nan  # Set to NaN if nominal_di_gas is zero
            else:
                time_dt_gas = nominal_di_gas / (1 + b_factor_gas * nominal_di_gas * time_gas_years)


            #print(time_switch_oil, time_dt_oil, time_dt_gas, min_dec_oil, min_dec_gas, time_oil_years, time_gas_years)
            if time_oil_years < 0:
                q_oil = None
            # Check if time is less than the minimum decline period for oil
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

            elif b_factor_oil == 0:
            # Arps Exponential
                q_oil = qi_oil * math.exp(-(nominal_di_oil * time_oil_years))
                
            elif b_factor_oil == 1.0:
                # Arps Harmonic
                q_oil = qi_oil / (1 + nominal_di_oil * time_oil_years)
            else:
                # Calculate production rates using hyperbolic decline equation
                q_oil = qi_oil / (1 + (b_factor_oil * nominal_di_oil  * time_oil_years))** (1 / b_factor_oil) if not np.isnan(time_oil_years) else np.nan
                
                #print(b_factor_oil, di_oil, time_oil_years, qi_oil, q_oil)


            if time_gas_years < 0:
                q_gas = None
            # Check if time is less than the minimum decline period for gas
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

            elif b_factor_gas == 0:
            # Arps Exponential
                q_gas = qi_gas * math.exp(-(nominal_di_gas * time_gas_years))
            elif b_factor_gas == 1.0:
                # Arps Harmonic
                q_gas = qi_gas / (1 + nominal_di_gas * time_gas_years)
            else:
                q_gas = qi_gas / (1 + (b_factor_gas * nominal_di_gas * time_gas_years)) ** (1 / b_factor_gas) if not np.isnan(time_gas_years) else np.nan
            #print(nominal_di_oil, q_oil)

            # Append the calculated production rates for the specific row to the list
            if q_oil < 0:
                q_oil = np.nan

            if q_gas < 0:
                q_gas = np.nan

            production_rates_data.append({
                'UWI': row['UWI'],
                'date': row_date_timestamp,
                'q_oil': q_oil,
                'q_gas': q_gas
            })
            #print(q_oil)
        return production_rates_data

    def calculate_nominal_di(self, di, b_factor, fluid_type='oil'):

   
        if b_factor == 0:
            return di / 100
        elif b_factor == 1.0:
            return (((1 - (di / 100)) ** (-b_factor)) - 1) / b_factor
        else:
            return (((1 - (di / 100)) ** (-b_factor)) - 1) / b_factor

    def extend_dataframe(self):
        start_time = time.time()
        combined_df_extended = pd.DataFrame()

        # Iterate over each unique UWI
        for uwi in self.combined_df['UWI'].unique():
            # Filter the DataFrame for the current UWI
            uwi_data = self.combined_df[self.combined_df['UWI'] == uwi]
    
            # Find the last date for the current UWI
            last_date = uwi_data['date'].max()

            # Skip if last_date is NaN
            if pd.isnull(last_date):
                continue

            # Initialize a list to store the additional dates
            additional_dates = []

            # Generate additional dates for the next 10 years (120 months)
            for i in range(1, 121):
                additional_date = last_date + pd.DateOffset(months=i)
                additional_dates.append({'UWI': uwi, 'date': additional_date})

            # Create a DataFrame from the additional dates
            additional_dates_df = pd.DataFrame(additional_dates)

            # Concatenate the additional dates DataFrame with the original DataFrame
            combined_df_extended = pd.concat([combined_df_extended, additional_dates_df], ignore_index=True)

        # Concatenate the extended DataFrame with the original DataFrame

        self.combined_df_extended = pd.concat([self.combined_df, combined_df_extended], ignore_index=True)
        end_time = time.time()
        execution_time = end_time - start_time
        print("extend time:", execution_time)
        return self.combined_df_extended

    def calculate_errors(self):
        start_time = time.time()
        self.prod_rates_extended_errors = self.prod_rates_extended

        # Compute the absolute differences between 'oil_volume' and 'q_oil' for each row
        self.prod_rates_extended_errors['oil_difference'] = np.where(
            self.prod_rates_extended_errors['oil_volume'] == 0,
            0,  # If oil volume is 0, difference is 0
            np.where(
                abs((self.prod_rates_extended_errors['oil_volume'] - self.prod_rates_extended_errors['q_oil']) / self.prod_rates_extended_errors['oil_volume']) * 100 > 300,
                0,  # If difference exceeds 500%, set it to 0
                abs((self.prod_rates_extended_errors['oil_volume'] - self.prod_rates_extended_errors['q_oil']) / self.prod_rates_extended_errors['oil_volume']) * 100
            )
        )

        # Compute the absolute differences between 'gas_volume' and 'q_gas' for each row
        self.prod_rates_extended_errors['gas_difference'] = np.where(
            self.prod_rates_extended_errors['gas_volume'] == 0,
            0,  # If gas volume is 0, difference is 0
            np.where(
                abs((self.prod_rates_extended_errors['gas_volume'] - self.prod_rates_extended_errors['q_gas']) / self.prod_rates_extended_errors['gas_volume']) * 100 > 300,
                0,  # If difference exceeds 500%, set it to 0
                abs((self.prod_rates_extended_errors['gas_volume'] - self.prod_rates_extended_errors['q_gas']) / self.prod_rates_extended_errors['gas_volume']) * 100
            )
        )
        # Replace any NaN values in the differences columns with 0
        self.prod_rates_extended_errors['oil_difference'].fillna(0, inplace=True)
        self.prod_rates_extended_errors['gas_difference'].fillna(0, inplace=True)

                # Convert 'date' column to datetime objects and extract date part
        # Round all columns to two decimal places (excluding 'date' column)
        self.prod_rates_extended_errors = self.prod_rates_extended_errors.round(2)


        #print("combined", self.prod_rates_extended_errors.to_string())
        self.prod_rates_all = self.prod_rates_extended_errors
        self.sum_of_errors = self.prod_rates_extended_errors.groupby('UWI').agg({
        'oil_difference': 'sum',
        'gas_difference': 'sum'
    }).reset_index()
        self.sum_of_errors[['oil_difference', 'gas_difference']] = self.sum_of_errors[['oil_difference', 'gas_difference']].round(2)
        print(self.sum_of_errors)

        end_time = time.time()
        execution_time = end_time - start_time
        print("eror time:", execution_time)
        return self.prod_rates_all,self.sum_of_errors

    def profile_function(self):
        start_time = time.time()
        result = self._calculate_production_rates_for_uwi(self.uwi_model_data, self.uwi_combined_df)
        end_time = time.time()
        execution_time = end_time - start_time
        print("profile:", execution_time)

        # Call the profile_function
        self.profile_function()

        # Run the profiler
        cProfile.run('self.profile_function()')
ChatGPT
It looks like you're implementing a class for decline curve analysis. I see you have methods for calculating production rates, extending dataframes, updating production rates, calculating errors, and profiling functi