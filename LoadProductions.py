import pandas as pd
from DefaultProperties import DefaultProperties
from DatabaseManager import DatabaseManager


class LoadProductions:
    def __init__(self):
        self.combined_df = None
        self.model_data = None
        self.db_path = None

        self.data_to_insert = []
        self.uwi_list = None


    def prepare_data(self, production_data, db_path):
        self.db_path = db_path
        # Initialize an empty list to store combined data and UWIs
        combined_data = []
        self.model_data = []
        self.uwi_list = []

        # Iterate over each entry in production data
        for entry in production_data:
            # Extract UWI (Well ID)
            uwi = entry['uwi']
            oil_volume = entry.get('oil_volume', 0)
            gas_volume = entry.get('gas_volume', 0)
            
            ## Add UWI to uwi_list if not already present
            #if uwi not in self.uwi_list:
            #    self.uwi_list.append(uwi)

            # Append the data to combined_data list
            combined_data.append({
                'UWI': uwi,
                'date': pd.to_datetime(entry['date']).date(), 
                'oil_volume': oil_volume,
                'gas_volume': gas_volume
            })

        # Convert combined_data list to a DataFrame
        self.combined_df = pd.DataFrame(combined_data)
        self.combined_df = self.combined_df.sort_values(by=['UWI', 'date'])
        self.uwi_list = self.combined_df['UWI'].unique().tolist()

        # Iterate over combined_df for each UWI and calculate cumulative days, oil, and gas volumes
# Use groupby to handle data by UWI in a vectorized manner
        grouped = self.combined_df.groupby('UWI')
        self.combined_df['cumulative_days'] = grouped['date'].transform(lambda x: (x - x.iloc[0]).dt.days / 365)
        try:
            production_data['oil_volume'] = pd.to_numeric(production_data['oil_volume'], errors='coerce')
            self.combined_df['cumulative_oil_volume'] = production_data.groupby('some_grouping_column')['oil_volume'].cumsum()
        except Exception as e:
            print(f"Failed to process data: {e}")
            # Assuming self.combined_df already exists and is properly structured
            if 'cumulative_oil_volume' in self.combined_df.columns:
                self.combined_df['cumulative_oil_volume'] = 0  # Set all to 0
            else:
                # If combined_df does not already have the column, create it and set to 0
                self.combined_df['cumulative_oil_volume'] = pd.Series([0] * len(self.combined_df))


        try:
            # Convert gas volume to numeric, coercing errors
            production_data['gas_volume'] = pd.to_numeric(production_data['gas_volume'], errors='coerce')
            # Calculate the cumulative sum of gas volume and store it in combined_df
            self.combined_df['cumulative_gas_volume'] = production_data.groupby('some_grouping_column')['gas_volume'].cumsum()
        except Exception as e:
            print(f"Failed to process gas data: {e}")
            # Set the cumulative_gas_volume to 0 if there is an error
            if 'cumulative_gas_volume' in self.combined_df.columns:
                self.combined_df['cumulative_gas_volume'] = 0  # Set all to 0
            else:
                # Create the column if it does not exist and initialize to 0
                self.combined_df['cumulative_gas_volume'] = pd.Series([0] * len(self.combined_df))



        #self.prepare_data_for_insertion()
        #self.save_uwi_list_to_database()
        #print(self.combined_df)
        print("loaddone")



        if self.db_path and self.uwi_list:
            try:
                # Create a DatabaseManager instance and connect to the database
                db_manager = DatabaseManager(self.db_path)
                db_manager.connect()

                # Create or connect to the 'uwis' table
                db_manager.create_uwi_table()

                # Insert UWIs into the 'uwis' table
                for uwi in self.uwi_list:
                    db_manager.insert_uwi(uwi)
                # Commit changes and disconnect from the database
                db_manager.connection.commit()
                db_manager.disconnect()
                print("Data Loaded Succesfully")
            except Exception as e:
                print("Error saving UWIs to the database:", e)
        else:
            print("Database path or UWI list is not specified.")
    
        return self.combined_df, self.uwi_list
        #####print(self.uwi_list)  # Print uwi_list for verification

    #def prepare_data_for_insertion(self):
    #    self.combined_df['date'] = pd.to_datetime(self.combined_df['date'])
    #    # Ensure necessary columns are in string format or properly formatted for SQL insertion
    #    self.combined_df['date'] = self.combined_df['date'].dt.strftime('%Y-%m-%d')

    #    # Use DataFrame.to_records to convert DataFrame to a structured array
    #    data_records = self.combined_df.to_records(index=False)

    #    # Convert structured array to a list of tuples if needed (some database APIs accept records directly)
    #    self.data_to_insert = [tuple(rec) for rec in data_records]
 
    #def save_uwi_list_to_database(self):
    #    if self.db_path and self.uwi_list:
    #        try:
    #            # Create a DatabaseManager instance and connect to the database
    #            db_manager = DatabaseManager(self.db_path)
    #            db_manager.connect()

    #            # Create or connect to the 'uwis' table
    #            db_manager.create_uwi_table()

    #            # Insert UWIs into the 'uwis' table
    #            for uwi in self.uwi_list:
    #                db_manager.insert_uwi(uwi)


    #            db_manager.insert_production_data(self.data_to_insert)  # Assuming this method matches your updated schema and data


    #            # Commit changes and disconnect from the database
    #            db_manager.connection.commit()

    #            db_manager.disconnect()
    #            print("Data Loaded Succesfully")
    #        except Exception as e:
    #            print("Error saving UWIs to the database:", e)
    #    else:
    #        print("Database path or UWI list is not specified.")

