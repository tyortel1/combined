import pandas as pd
from DefaultProperties import DefaultProperties
from DatabaseManager import DatabaseManager


class LoadProductions:
    def __init__(self):
        self.combined_df = None
        self.model_data = None
        self.db_path = None

        self.data_to_insert = []
        self.UWI_list = None


    def prepare_data(self, production_data, db_path):
        self.db_path = db_path
        # Initialize an empty list to store combined data and UWIs
        combined_data = []
        self.model_data = []
        self.UWI_list = []

        # Iterate over each entry in production data
        for entry in production_data:
            # Extract UWI (Well ID)
            UWI = entry['UWI']
            oil_volume = entry.get('oil_volume', 0)
            gas_volume = entry.get('gas_volume', 0)
            
            ## Add UWI to UWI_list if not already present
            #if UWI not in self.UWI_list:
            #    self.UWI_list.append(UWI)

            # Append the data to combined_data list
            combined_data.append({
                'UWI': UWI,
                'date': pd.to_datetime(entry['date']).date(), 
                'oil_volume': oil_volume,
                'gas_volume': gas_volume
            })
        self.combined_df = pd.DataFrame(combined_data)
        self.combined_df = self.combined_df.sort_values(by=['UWI', 'date'])
        self.UWI_list = self.combined_df['UWI'].unique().tolist()

        # Ensure 'date' is in datetime format
        self.combined_df['date'] = pd.to_datetime(self.combined_df['date'], errors='coerce')

        # Calculate cumulative days grouped by 'UWI'
        self.combined_df['cumulative_days'] = (
            self.combined_df.groupby('UWI')['date']
            .transform(lambda x: (x - x.min()).dt.days / 365))



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
        #self.save_UWI_list_to_database()
        #print(self.combined_df)
        print("loaddone")



        if self.db_path and self.UWI_list:
            try:
                # Create a DatabaseManager instance and connect to the database
                db_manager = DatabaseManager(self.db_path)
                db_manager.connect()

                # Create or connect to the 'UWIs' table
                db_manager.create_UWI_table()

                # Insert UWIs into the 'UWIs' table
                for UWI in self.UWI_list:
                    db_manager.insert_UWI(UWI)
                # Commit changes and disconnect from the database

                print("Data Loaded Succesfully")
            except Exception as e:
                print("Error saving UWIs to the database:", e)
        else:
            print("Database path or UWI list is not specified.")
    
        return self.combined_df, self.UWI_list
        #####print(self.UWI_list)  # Print UWI_list for verification

    #def prepare_data_for_insertion(self):
    #    self.combined_df['date'] = pd.to_datetime(self.combined_df['date'])
    #    # Ensure necessary columns are in string format or properly formatted for SQL insertion
    #    self.combined_df['date'] = self.combined_df['date'].dt.strftime('%Y-%m-%d')

    #    # Use DataFrame.to_records to convert DataFrame to a structured array
    #    data_records = self.combined_df.to_records(index=False)

    #    # Convert structured array to a list of tuples if needed (some database APIs accept records directly)
    #    self.data_to_insert = [tuple(rec) for rec in data_records]
 
    #def save_UWI_list_to_database(self):
    #    if self.db_path and self.UWI_list:
    #        try:
    #            # Create a DatabaseManager instance and connect to the database
    #            db_manager = DatabaseManager(self.db_path)
    #            db_manager.connect()

    #            # Create or connect to the 'UWIs' table
    #            db_manager.create_UWI_table()

    #            # Insert UWIs into the 'UWIs' table
    #            for UWI in self.UWI_list:
    #                db_manager.insert_UWI(UWI)


    #            db_manager.insert_production_data(self.data_to_insert)  # Assuming this method matches your updated schema and data


    #            # Commit changes and disconnect from the database
    #            db_manager.connection.commit()

    #            db_manager.disconnect()
    #            print("Data Loaded Succesfully")
    #        except Exception as e:
    #            print("Error saving UWIs to the database:", e)
    #    else:
    #        print("Database path or UWI list is not specified.")

