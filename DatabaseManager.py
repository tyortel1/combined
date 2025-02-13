import sqlite3
import pandas as pd
import logging
import re
import numpy as np




class DatabaseManager:
    def __init__(self, db_path):
        self.db_path = db_path
        self.connection = None
        self.cursor = None


    def connect(self):
        self.connection = sqlite3.connect(self.db_path)


        self.cursor = self.connection.cursor()

    def disconnect(self):
        if self.connection:
            self.connection.close()



    def insert_UWI(self, UWI, status=None):
        self.connect()

        # Modify SQL query to include the status column
        insert_UWI_sql = "INSERT INTO UWIs (UWI, status) VALUES (?, ?)"
        if status is None:
            status = 'Active'
        try:
            # Execute the query with both UWI and status
            self.cursor.execute(insert_UWI_sql, (UWI, status))
            self.connection.commit()
            print("UWI '{}' with status '{}' inserted successfully.".format(UWI, status))
        except sqlite3.Error as e:
            print("Error inserting UWI:", e)
        finally:
            self.disconnect()

    def create_UWI_table(self):
        self.connect()
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS UWIs (
            UWI TEXT PRIMARY KEY,
            status TEXT DEFAULT 'Active',
            surface_x REAL DEFAULT NULL,
            surface_y REAL DEFAULT NULL,
            lateral REAL DEFAULT NULL,
            heel_x REAL DEFAULT NULL,
            heel_y REAL DEFAULT NULL,
            toe_x REAL DEFAULT NULL,
            toe_y REAL DEFAULT NULL,
            heel_md REAL DEFAULT NULL,
            toe_md REAL DEFAULT NULL,
            average_tvd REAL DEFAULT NULL,
            total_length REAL DEFAULT NULL,
            spud_date TEXT DEFAULT NULL
        )
        """
        try:
            self.cursor.execute(create_table_sql)
            self.connection.commit()
            print("UWIs table created successfully.")
        except sqlite3.Error as e:
            print("Error creating UWIs table:", e)
        finally:
            self.disconnect()

    def save_UWI_data(self, total_lat_data):
        if not isinstance(total_lat_data, pd.DataFrame):
            print("Input data must be a pandas DataFrame.")
            return

        if total_lat_data.empty:
            print("The DataFrame is empty. Nothing to save.")
            return

        self.connect()

        try:
            expected_columns = [
                'UWI', 'status', 'surface_x', 'surface_y', 'lateral',
                'heel_x', 'heel_y', 'toe_x', 'toe_y', 'heel_md',
                'toe_md', 'average_tvd', 'total_length', 'spud_date'
            ]
            total_lat_data = total_lat_data[expected_columns]  # Enforce correct column order

            for _, row in total_lat_data.iterrows():
                UWI = row['UWI']
                update_columns = [col for col in row.index if col != 'UWI']
                set_clause = ", ".join([f"{col} = COALESCE(?, {col})" for col in update_columns])

                sql_update = f"""
                UPDATE UWIs
                SET {set_clause}
                WHERE UWI = ?
                """

                update_values = [row[col] for col in update_columns]
                update_values.append(UWI)

                print(f"Executing SQL Update: {sql_update}")
                print(f"Values: {update_values}")
                self.cursor.execute(sql_update, update_values)

                if self.cursor.rowcount == 0:
                    columns = ['UWI'] + update_columns
                    placeholders = ", ".join(["?" for _ in columns])

                    sql_insert = f"""
                    INSERT INTO UWIs ({', '.join(columns)})
                    VALUES ({placeholders})
                    """

                    # Correct insert values to avoid duplicating 'UWI'
                    insert_values = [row[col] for col in columns]

                    print(f"Executing SQL Insert: {sql_insert}")
                    print(f"Values: {insert_values}")
                    self.cursor.execute(sql_insert, insert_values)

            self.connection.commit()
            print("Well data updated successfully.")

        except Exception as e:
            print(f"Error updating well data: {e}")
            self.connection.rollback()

        finally:
            self.disconnect()


    def get_UWIs_with_surface_xy(self):
        """Fetches all UWIs along with their surface X and Y coordinates from the database."""
        try:
            self.connect()
            self.cursor.execute("SELECT UWI, surface_x, surface_y FROM UWIs")
            results = self.cursor.fetchall()
            return [{"UWI": str(row[0]), "surface_x": row[1], "surface_y": row[2]} for row in results]
        except sqlite3.Error as e:
            print("Error retrieving UWIs with surface XY coordinates:", e)
            return []
        finally:
            self.disconnect()





    def get_UWIs_with_heel_toe(self):
        """
        Fetches all UWIs along with their heel and toe coordinates from the database.
        Handles None or missing values gracefully.
        """
        try:
            self.connect()
            self.cursor.execute("SELECT UWI, heel_x, heel_y, toe_x, toe_y FROM UWIs")
            results = self.cursor.fetchall()
            formatted_results = []
            for row in results:
                # Skip rows with missing critical data
                if any(value is None for value in row[1:]):
                    print(f"Skipping row for UWI {row[0]} due to missing data: {row}")
                    continue

                try:
                    formatted_results.append({
                        "UWI": str(row[0]),
                        "heel_x": float(row[1]),
                        "heel_y": float(row[2]),
                        "toe_x": float(row[3]),
                        "toe_y": float(row[4]),
                    })
                except ValueError as ve:
                    print(f"Skipping invalid row for UWI {row[0]}: {ve}")
                    continue
            return formatted_results
        except sqlite3.Error as e:
            print("Error retrieving UWIs with heel/toe coordinates:", e)
            return []
        finally:
            self.disconnect()


    def get_UWIs_with_average_tvd(self):
        """
        Fetches all UWIs along with their average TVD from the database.
        Handles None or missing values gracefully.
        """
        try:
            self.connect()
            self.cursor.execute("SELECT UWI, average_tvd FROM UWIs")
            results = self.cursor.fetchall()
            formatted_results = []
        
            for row in results:
                # Skip rows with missing average_tvd
                if row[1] is None:
                    print(f"Skipping row for UWI {row[0]} due to missing average_tvd data: {row}")
                    continue
            
                try:
                    formatted_results.append({
                        "UWI": str(row[0]),
                        "average_tvd": float(row[1])
                    })
                except ValueError as ve:
                    print(f"Skipping invalid row for UWI {row[0]}: {ve}")
                    continue
                
            return formatted_results
        
        except sqlite3.Error as e:
            print("Error retrieving UWIs with average TVD:", e)
            return []
        finally:
            self.disconnect()



    def update_UWI_revenue_and_efr(self, UWI, npv, npv_discounted, EFR_oil, EFR_gas, EUR_oil_remaining, EUR_gas_remaining, scenario_id=1):
        self.connect()
        update_sql = """
        UPDATE model_properties
        SET npv = ?, npv_discounted = ?, EFR_oil = ?, EFR_gas = ?, EUR_oil_remaining = ?, EUR_gas_remaining = ?
        WHERE UWI = ? AND scenario_id = ?
        """

        try:
            # Execute the update query with the new parameters
            self.cursor.execute(update_sql, (npv, npv_discounted, EFR_oil, EFR_gas, EUR_oil_remaining, EUR_gas_remaining, UWI, scenario_id))
            self.connection.commit()
            print(f"UWI '{UWI}' (Scenario {scenario_id}) updated with NPV '{npv}', NPV Discounted '{npv_discounted}', "
                  f"EFR Oil '{EFR_oil}', EFR Gas '{EFR_gas}', EUR Oil Remaining '{EUR_oil_remaining}', "
                  f"EUR Gas Remaining '{EUR_gas_remaining}' successfully.")
        except sqlite3.Error as e:
            print("Error updating UWI revenue:", e)
        finally:
            self.disconnect()


    def insert_production_data(self, data):
        """Insert production data into the prod_rates_all table."""
        insert_sql = '''
        INSERT INTO prod_rates_all
        (UWI, date, oil_volume, gas_volume, cumulative_oil_volume, cumulative_gas_volume, q_gas, error_gas, q_oil, error_oil, oil_revenue, gas_revenue, total_revenue, discounted_revenue, cumulative_days)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        '''
        try:
            self.connect()  # Ensure the connection is established
            cursor = self.connection.cursor()
            cursor.executemany(insert_sql, data)
            self.connection.commit()
        except sqlite3.Error as e:
            print("An error occurred:", e)
            self.connection.rollback()
        finally:
            cursor.close()
            self.disconnect() 


    def create_prod_rates_all_table(self):

        create_table_sql = """
        CREATE TABLE IF NOT EXISTS prod_rates_all (
            scenario_id INTEGER NOT NULL,
            UWI TEXT NOT NULL,
            date TEXT,
            gas_volume REAL,
            q_gas REAL,
            error_gas REAL,
            oil_volume REAL,
            q_oil REAL,
            error_oil REAL,
            cumulative_oil_volume REAL,
            cumulative_gas_volume REAL,
            oil_revenue REAL,
            gas_revenue REAL,
            total_revenue REAL,
            discounted_revenue REAL,
            cumulative_days REAL,
            FOREIGN KEY (scenario_id) REFERENCES UWIs(scenario_id)
        )
        """
        try:
            self.connect()
            with self.connection:  # This automatically commits or rolls back
                self.cursor.execute(create_table_sql)
            print("prod_rates_all table created successfully.")
        except sqlite3.Error as e:
            print("Error creating prod_rates_all table:", e)
        finally:
            self.disconnect()


    def prod_rates_all(self, dataframe, table_name, scenario_id):
        """Store the dataframe into the specified table in the database."""
        try:
            dataframe['date'] = dataframe['date'].dt.strftime('%Y-%m-%d')
            dataframe['scenario_id'] = scenario_id  # Set scenario_id from parameter
            self.connect()
            dataframe.to_sql(table_name, self.connection, if_exists='replace', index=False)
            print(f"Data stored successfully in {table_name}")
        except Exception as e:
            print(f"Error storing data in {table_name}: {e}")
        finally:
            self.disconnect()


  

    def update_prod_rates(self, dataframe, scenario_id):
        """
        Update oil and gas production rates along with revenue data in the 'prod_rates_all' table using the UWI and scenario_id specified in the DataFrame.
        """
        try:
            # Ensure dataframe has the necessary columns
            required_columns = ['UWI', 'date', 'q_oil', 'q_gas', 'total_revenue', 'discounted_revenue', 'gas_revenue', 'oil_revenue']
            if not all(column in dataframe.columns for column in required_columns):
                raise ValueError("DataFrame is missing required columns.")

            UWI = dataframe['UWI'].iloc[0]  # Assumes all rows have the same UWI
            dataframe['date'] = dataframe['date'].dt.strftime('%Y-%m-%d')  # Format the date column
            self.connection.execute('BEGIN')  # Start a transaction

            # Delete existing records for the specified UWI and scenario_id
            delete_query = "DELETE FROM prod_rates_all WHERE UWI = ? AND scenario_id = ?"
            self.cursor.execute(delete_query, (UWI, scenario_id))
            deleted_rows = self.cursor.rowcount
            print(f"Deleted {deleted_rows} rows for UWI {UWI} and scenario_id {scenario_id}")

            # Insert new data
            insert_query = """
            INSERT INTO prod_rates_all (UWI, date, q_oil, q_gas, total_revenue, discounted_revenue, gas_revenue, oil_revenue, scenario_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(UWI, date, scenario_id) DO UPDATE SET
            q_oil = excluded.q_oil,
            q_gas = excluded.q_gas,
            total_revenue = excluded.total_revenue,
            discounted_revenue = excluded.discounted_revenue,
            gas_revenue = excluded.gas_revenue,
            oil_revenue = excluded.oil_revenue;
            """
    
            for index, row in dataframe.iterrows():
                self.cursor.execute(insert_query, (
                    UWI, row['date'], row['q_oil'], row['q_gas'],
                    row['total_revenue'], row['discounted_revenue'],
                    row['gas_revenue'], row['oil_revenue'], scenario_id
                ))

            self.connection.commit()
            print(f"Data updated successfully in prod_rates_all for UWI {UWI} and scenario_id {scenario_id}")
        except Exception as e:
            self.connection.rollback()
            print(f"Error updating data in prod_rates_all: {e}")
            logging.error(f"Error updating data in prod_rates_all for UWI {UWI} and scenario_id {scenario_id}: {e}")


    def rollback(self):
        if self.connection:
            self.connection.rollback()

    def execute_query(self, query, parameters=None):
        if parameters:
            self.cursor.execute(query, parameters)
        else:
            self.cursor.execute(query)

    def commit(self):
            self.connection.commit()

    def create_sum_of_errors_table(self):
        self.connect()
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS sum_of_errors (
            scenario_id INTEGER NOT NULL,
            UWI TEXT NOT NULL,
            sum_error_oil REAL DEFAULT NULL,
            sum_error_gas REAL DEFAULT NULL,
            PRIMARY KEY (scenario_id, UWI)
        )
        """
        try:
            self.cursor.execute(create_table_sql)
            self.connection.commit()
            print("Sum of errors table created successfully.")
        except sqlite3.Error as e:
            print("Error creating sum of errors table:", e)
        finally:
            self.disconnect()

    def store_sum_of_errors_dataframe(self, sum_of_errors_dataframe, scenario_id):
        """Store the sum of errors DataFrame into a specified table in the database."""
        try:
            self.connect()  # Ensure connection is open

            for index, row in sum_of_errors_dataframe.iterrows():
                # Convert the row to a dictionary
                row_dict = row.to_dict()
                row_dict['scenario_id'] = scenario_id

                # Create an upsert query (update if exists, insert if not)
                upsert_query = """
                INSERT INTO sum_of_errors (scenario_id, UWI, sum_error_oil, sum_error_gas)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(scenario_id, UWI) DO UPDATE SET
                    sum_error_oil = excluded.sum_error_oil,
                    sum_error_gas = excluded.sum_error_gas
                """

                # Execute the query
                self.cursor.execute(upsert_query, (
                    row_dict['scenario_id'],
                    row_dict['UWI'],
                    row_dict['sum_error_oil'],
                    row_dict['sum_error_gas']
                ))

            self.connection.commit()
            print(f"Sum of errors data stored successfully for scenario_id {scenario_id}")
        except Exception as e:
            print(f"Error storing sum of errors data for scenario_id {scenario_id}: {e}")
            self.connection.rollback()
        finally:
            self.disconnect()


    def create_model_properties_table(self):
        self.connect()
    
        # Define the table creation SQL
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS model_properties (
            scenario_id INTEGER NOT NULL,
            UWI TEXT NOT NULL,
            max_oil_production REAL DEFAULT 0,
            max_gas_production REAL DEFAULT 0,
            max_oil_production_date TEXT DEFAULT '0000-00-00',
            max_gas_production_date TEXT DEFAULT '0000-00-00',
            one_year_oil_production REAL DEFAULT 0,
            one_year_gas_production REAL DEFAULT 0,
            di_oil REAL DEFAULT 0,
            di_gas REAL DEFAULT 0,
            oil_b_factor REAL DEFAULT 0,
            gas_b_factor REAL DEFAULT 0,
            min_dec_oil REAL DEFAULT 0,
            min_dec_gas REAL DEFAULT 0,
            model_oil TEXT DEFAULT '',
            model_gas TEXT DEFAULT '',
            economic_limit_type TEXT DEFAULT '',
            economic_limit_date TEXT DEFAULT '0000-00-00',
            oil_price REAL DEFAULT 0,
            gas_price REAL DEFAULT 0,
            oil_price_dif REAL DEFAULT 0,
            gas_price_dif REAL DEFAULT 0,
            discount_rate REAL DEFAULT 0,
            working_interest REAL DEFAULT 0,
            royalty REAL DEFAULT 0,
            tax_rate REAL DEFAULT 0,
            capital_expenditures REAL DEFAULT 0,
            operating_expenditures REAL DEFAULT 0,
            net_price_oil REAL DEFAULT 0,
            net_price_gas REAL DEFAULT 0,
            gas_model_status TEXT DEFAULT '',
            oil_model_status TEXT DEFAULT '',
            q_oil_eur REAL DEFAULT 0, 
            q_gas_eur REAL DEFAULT 0,
            q_oil_eur_normalized REAL DEFAULT 0, 
            q_gas_eur_normalized REAL DEFAULT 0,  
            EFR_oil REAL DEFAULT 0,    
            EFR_gas REAL DEFAULT 0,    
            EUR_oil_remaining REAL DEFAULT 0,  
            EUR_gas_remaining REAL DEFAULT 0,  
            npv REAL DEFAULT 0,           
            npv_discounted REAL DEFAULT 0,  
            payback_months REAL DEFAULT 0,  
            parent_wells REAL DEFAULT 0,  
            PRIMARY KEY (scenario_id, UWI)
        )
        """
    
        try:
            # Execute the table creation
            self.cursor.execute(create_table_sql)
            self.connection.commit()
            print("Model properties table checked/created successfully.")

            # Check if the new columns exist
            self.cursor.execute("PRAGMA table_info(model_properties)")
            existing_columns = {column[1] for column in self.cursor.fetchall()}
        
            # List of new columns to add
            new_columns = {
                "q_oil_eur_normalized": "REAL DEFAULT 0",
                "q_gas_eur_normalized": "REAL DEFAULT 0"
            }

            for column, dtype in new_columns.items():
                if column not in existing_columns:
                    alter_sql = f"ALTER TABLE model_properties ADD COLUMN {column} {dtype}"
                    self.cursor.execute(alter_sql)
                    print(f"Added column {column} to model_properties table.")

            self.connection.commit()
        except sqlite3.Error as e:
            print("Error creating/updating model properties table:", e)
        finally:
            self.disconnect()

    def delete_model_properties_for_scenario(self, scenario_id):
        """Delete model properties associated with a specific scenario."""
        try:
            self.connect()
            query = "DELETE FROM model_properties WHERE scenario_id = ?"
            self.cursor.execute(query, (scenario_id,))
            self.connection.commit()
        except sqlite3.Error as e:
            print(f"Error deleting model properties for scenario {scenario_id}: {e}")
            self.connection.rollback()
        finally:
            self.disconnect()

    def delete_production_rates_for_scenario(self, scenario_id):
        """Delete production rates associated with a specific scenario."""
        try:
            self.connect()
            query = "DELETE FROM prod_rates_all WHERE scenario_id = ?"
            self.cursor.execute(query, (scenario_id,))
            self.connection.commit()
        except sqlite3.Error as e:
            print(f"Error deleting production rates for scenario {scenario_id}: {e}")
            self.connection.rollback()
        finally:
            self.disconnect()


    def delete_model_properties_for_wells(self, scenario_id, well_UWIs):
        """Delete model properties for a list of wells within a specific scenario."""
        if not well_UWIs:
            return  # No wells provided, nothing to delete

        try:
            self.connect()
            query = f"DELETE FROM model_properties WHERE scenario_id = ? AND UWI IN ({','.join(['?'] * len(well_UWIs))})"
            self.cursor.execute(query, (scenario_id, *well_UWIs))
            self.connection.commit()
        except sqlite3.Error as e:
            print(f"Error deleting model properties for scenario {scenario_id}, wells {well_UWIs}: {e}")
            self.connection.rollback()
        finally:
            self.disconnect()

    def delete_production_rates_for_wells(self, scenario_id, well_UWIs):
        """Delete production rates for a list of wells within a specific scenario."""
        if not well_UWIs:
            return  # No wells provided, nothing to delete

        try:
            self.connect()
            query = f"DELETE FROM prod_rates_all WHERE scenario_id = ? AND UWI IN ({','.join(['?'] * len(well_UWIs))})"
            self.cursor.execute(query, (scenario_id, *well_UWIs))
            self.connection.commit()
        except sqlite3.Error as e:
            print(f"Error deleting production rates for scenario {scenario_id}, wells {well_UWIs}: {e}")
            self.connection.rollback()
        finally:
            self.disconnect()



    def save_eur_to_model_properties(self, UWI, q_oil_eur, q_gas_eur, q_oil_eur_normalized=None, q_gas_eur_normalized=None, scenario_id=1):
        """
        Update the EUR values in the model_properties table for the given UWI and scenario_id.
        """
        self.connect()

        query = """
        UPDATE model_properties
        SET 
            q_oil_eur = ?, 
            q_gas_eur = ?, 
            q_oil_eur_normalized = ?, 
            q_gas_eur_normalized = ?
        WHERE 
            scenario_id = ? AND UWI = ?;
        """

        try:
            self.cursor.execute(query, (q_oil_eur, q_gas_eur, q_oil_eur_normalized, q_gas_eur_normalized, scenario_id, UWI))
            if self.cursor.rowcount == 0:
                print(f"No matching row found for UWI: {UWI} and Scenario ID: {scenario_id}.")
            self.connection.commit()
        except Exception as e:
            print(f"Error updating EUR values for UWI {UWI}: {e}")
        finally:
            self.disconnect()


    #keep
    def retrieve_model_data_by_scenario_and_UWI(self, scenario_id, UWI):
        try:
            self.connect()
            print(f"Connected to database at {self.db_path}")
        
            query = "SELECT * FROM model_properties WHERE scenario_id = ? AND UWI = ?"
            self.cursor.execute(query, (scenario_id, UWI))
            data = self.cursor.fetchall()
        
            if not data:
                print(f"No data found for scenario_id: {scenario_id} and UWI: {UWI}")
                return None
            
            columns = [description[0] for description in self.cursor.description]
            df = pd.DataFrame(data, columns=columns)
            print(f"Retrieved data shape: {df.shape}")
            return df
        
        except sqlite3.Error as e:
            print("Error retrieving model data:", e)
            return None
        finally:
            self.disconnect()

    def store_model_data(self, model_data_dataframe, scenario_id):
        try:
            # Add the scenario_id column to the dataframe
            model_data_dataframe['scenario_id'] = scenario_id
        
            # Print the dataframe columns to debug
            print("Storing the following model data:")
            print(model_data_dataframe.columns)
        
            self.connect()
        
            # Use the append mode instead of replace to avoid dropping the table
            model_data_dataframe.to_sql('model_properties', self.connection, if_exists='append', index=False)
            print("Model data stored successfully in model_properties table.")
        except Exception as e:
            print(f"Error storing model data: {e}")
        finally:
            self.disconnect()


    
    def update_payback_months(self, UWI, payback_months, scenario_id):
        """
        Updates the payback_months column in model_properties for a given UWI and scenario.
        
        :param UWI: Unique Well Identifier
        :param payback_months: Number of months required for payback
        :param scenario_id: Scenario identifier
        """
        try:
            self.connect()
            cursor = self.connection.cursor()
            query = """
                UPDATE model_properties 
                SET payback_months = ? 
                WHERE UWI = ? AND scenario_id = ?
            """
            cursor.execute(query, (payback_months, UWI, scenario_id))
            self.connection.commit()
            print(f"Updated payback months for UWI {UWI} in scenario {scenario_id}: {payback_months}")
        except Exception as e:
            print(f"Error updating payback months for UWI {UWI}: {e}")
        finally:
            self.disconnect()




    def retrieve_prod_rates_all(self, current_UWI=None, scenario_id=None):
        try:
            self.connect()
            # Get column names
            self.cursor.execute("PRAGMA table_info(prod_rates_all)")
            columns = [column[1] for column in self.cursor.fetchall()]

            if current_UWI and scenario_id:
                # Select data for the specified UWI and scenario_id
                query = "SELECT * FROM prod_rates_all WHERE UWI = ? AND scenario_id = ?"
                self.cursor.execute(query, (current_UWI, scenario_id))
            elif current_UWI:
                # Select data for the specified UWI
                query = "SELECT * FROM prod_rates_all WHERE UWI = ?"
                self.cursor.execute(query, (current_UWI,))
            elif scenario_id:
                # Select data for the specified scenario_id
                query = "SELECT * FROM prod_rates_all WHERE scenario_id = ?"
                self.cursor.execute(query, (scenario_id,))
            else:
                # Select all data from the table
                self.cursor.execute("SELECT * FROM prod_rates_all")
    
            rows = self.cursor.fetchall()
    
            # Convert rows to DataFrame with column names
            df = pd.DataFrame(rows, columns=columns)
    
            return df
        except sqlite3.Error as e:
            print("Error retrieving production rates:", e)
            return None
        finally:
            self.disconnect()

    def retrieve_model_data(self):
        try:
            self.connect()
            self.cursor.execute("SELECT * FROM model_properties")
            rows = self.cursor.fetchall()
            # Convert rows to list of dictionaries or return as necessary
            model_data = []
            column_names = [description[0] for description in self.cursor.description]
            for row in rows:
                model_data.append(dict(zip(column_names, row)))
            return model_data
        except sqlite3.Error as e:
            print("Error retrieving model data:", e)
            return None

        finally:
            self.disconnect()

    def retrieve_all_model_properties(self, scenario_id):
        """
        Retrieve model properties for all UWIs for the specified scenario_id.
    
        Args:
            scenario_id (int): The scenario ID to retrieve properties for
    
        Returns:
            pandas.DataFrame: A DataFrame containing model properties for all UWIs in the scenario
            or None if no data is found
        """
        print(f"Retrieving model properties for Scenario ID: {scenario_id}")
        try:
            self.connect()
            query = "SELECT * FROM model_properties WHERE scenario_id = ?"
            self.cursor.execute(query, (scenario_id,))
        
            # Fetch all rows
            data = self.cursor.fetchall()
        
            if data:
                # Extract column names from the cursor description
                columns = [description[0] for description in self.cursor.description]
            
                # Convert fetched data to a DataFrame
                df = pd.DataFrame(data, columns=columns)
                return df
            else:
                print(f"No model properties found for scenario {scenario_id}")
                return None
        except sqlite3.Error as e:
            print(f"Error retrieving model properties for scenario {scenario_id}: {e}")
            return None
        finally:
            self.disconnect()


    def retrieve_model_data_by_scenorio(self, scenario_id):
        """
        Retrieve model data for a specific scenario from the database.
        Returns list of dictionaries with model properties data, replacing NULL with 0.
        """
        try:
            self.connect()
            self.cursor.execute("SELECT * FROM model_properties WHERE scenario_id = ?", (scenario_id,))
            rows = self.cursor.fetchall()
        
            model_data = []
            column_names = [description[0] for description in self.cursor.description]
            for row in rows:
                # Replace None values with 0 when creating dictionary
                row_dict = {col: (0 if val is None else val) 
                           for col, val in zip(column_names, row)}
                model_data.append(row_dict)
            return model_data
        
        except sqlite3.Error as e:
            print("Error retrieving model data:", e)
            return []
        finally:
            self.disconnect()

    def get_model_properties(self, scenario):
        try:
            self.connect()
            query = "SELECT * FROM model_properties WHERE scenario_id = ?"
            self.cursor.execute(query, (scenario,))
        
            # Fetch column names
            columns = [column[0] for column in self.cursor.description]
        
            # Fetch all rows
            data = self.cursor.fetchall()
        
            # Convert to DataFrame
            return pd.DataFrame(data, columns=columns)
    
        except sqlite3.Error as e:
            print(f"Error retrieving model properties: {e}")
            return pd.DataFrame()  # Return empty DataFrame
        finally:
            self.disconnect()





    def retrieve_model_data_by_scenario(self, scenario):
        try:
            self.connect()
            self.cursor.execute("SELECT * FROM model_properties WHERE scenario_id = ?", (scenario,))
            rows = self.cursor.fetchall()
            # Convert rows to list of dictionaries or return as necessary
            model_data = []
            column_names = [description[0] for description in self.cursor.description]
            for row in rows:
                model_data.append(dict(zip(column_names, row)))
            return model_data
        except sqlite3.Error as e:
            print("Error retrieving model data:", e)
            return None
        finally:
            self.disconnect()


    def retrieve_sum_of_errors(self, scenario_id=None):
        try:
            self.connect()
            if scenario_id is not None:
                self.cursor.execute("SELECT * FROM sum_of_errors WHERE scenario_id = ?", (scenario_id,))
            else:
                self.cursor.execute("SELECT * FROM sum_of_errors")
        
            rows = self.cursor.fetchall()
            column_names = [description[0] for description in self.cursor.description]
            df = pd.DataFrame(rows, columns=column_names)
            return df
        
        except sqlite3.Error as e:
            print(f"Error retrieving sum of errors for scenario {scenario_id}: {e}")
            return None
        finally:
            self.disconnect()





    def get_all_UWIs(self):
        import pandas as pd
        try:
            self.connect()
            self.cursor.execute("SELECT * FROM UWIs")  # Fetch all rows and columns
            rows = self.cursor.fetchall()

            # Extract column names
            column_names = [description[0] for description in self.cursor.description]

            # Create and return a DataFrame
            return pd.DataFrame(rows, columns=column_names)

        except sqlite3.Error as e:
            print("Error retrieving all UWIs:", e)
            return pd.DataFrame()  # Return an empty DataFrame on error

        finally:
            self.disconnect()


    def get_UWIs(self):
        try:
            self.connect()
            self.cursor.execute("SELECT UWI FROM UWIs")
            UWIs = self.cursor.fetchall()
            return [str(UWI[0]) for UWI in UWIs]
        except sqlite3.Error as e:
            print("Error retrieving UWIs:", e)
            return []

        finally:
            self.disconnect()

    def get_capex_for_UWI(self, UWI, scenario_id):
        """
        Retrieve capital expenditures (CapEx) for a given UWI and scenario.
    
        Args:
            UWI (str): Unique Well Identifier.
            scenario_id (int): Scenario ID.
    
        Returns:
            float: CapEx value or 0 if not found.
        """
        self.connect()
        query = """
        SELECT capital_expenditures FROM model_properties
        WHERE scenario_id = ? AND UWI = ?
        """
        try:
            self.cursor.execute(query, (scenario_id, UWI))
            result = self.cursor.fetchone()
            return result[0] if result else 0
        except Exception as e:
            print(f"Error retrieving CapEx for UWI {UWI}: {e}")
            return 0
        finally:
            self.disconnect()

    def get_opex_for_UWI(self, UWI, scenario_id):
        """
        Retrieve operating expenditures (OpEx) for a given UWI and scenario.
    
        Args:
            UWI (str): Unique Well Identifier.
            scenario_id (int): Scenario ID.
    
        Returns:
            float: OpEx value or 0 if not found.
        """
        self.connect()
        query = """
        SELECT operating_expenditures FROM model_properties
        WHERE scenario_id = ? AND UWI = ?
        """
        try:
            self.cursor.execute(query, (scenario_id, UWI))
            result = self.cursor.fetchone()
            return result[0] if result else 0
        except Exception as e:
            print(f"Error retrieving OpEx for UWI {UWI}: {e}")
            return 0
        finally:
            self.disconnect()


    def retrieve_lateral_lengths(self):
        """
        Retrieve lateral lengths for all UWIs from the database.
    
        Returns:
            pd.DataFrame: DataFrame with columns ['UWI', 'lateral']
        """
        self.connect()
        try:
            query = "SELECT UWI, lateral FROM UWIs WHERE lateral IS NOT NULL"
            df = pd.read_sql(query, self.connection)
            return df
        except Exception as e:
            print(f"Error retrieving lateral lengths: {e}")
            return pd.DataFrame()
        finally:
            self.disconnect()

    def get_planned_wells(self):
        """Get all wells with 'Planned' status"""
        try:
            self.connect()
            query = """
            SELECT UWI 
            FROM UWIs 
            WHERE status = 'Planned'
            """
            self.cursor.execute(query)
            return [row[0] for row in self.cursor.fetchall()]
        except sqlite3.Error as e:
            print(f"Error getting planned wells: {e}")
            return []
        finally:
            self.disconnect()

    def get_UWIs_by_status(self, status):
        try:
            self.connect()
            self.cursor.execute("SELECT UWI FROM UWIs WHERE status = ?", (status,))
            UWIs = self.cursor.fetchall()
            return [str(UWI[0]) for UWI in UWIs]
        except sqlite3.Error as e:
            print(f"Error retrieving {status} UWIs:", e)
            return []
        finally:
            self.disconnect()
    def retrieve_tab2(self, today_date):
        try:
            self.connect()
            self.cursor.execute("SELECT date, UWI, discounted_revenue FROM prod_rates_all WHERE date >= ?", (today_date,))
            rows = self.cursor.fetchall()
            return rows
        except sqlite3.Error as e:
            print("Error retrieving data from database:", e)
            return None
        finally:
            self.disconnect()

    def get_active_UWIs_with_properties(self):
        try:
            self.connect()
            query = """
            SELECT DISTINCT u.UWI 
            FROM UWIs u 
            JOIN model_properties mp ON u.UWI = mp.UWI 
            WHERE u.status = 'Active'
            """
    
            self.cursor.execute(query)
            results = self.cursor.fetchall()
            return [row[0] for row in results]
        finally:
            self.disconnect()

    def get_UWIs_by_scenario_id(self, scenario_id):
        try:
            self.connect()
            query = "SELECT DISTINCT UWI FROM model_properties WHERE scenario_id = ?"
            self.cursor.execute(query, (scenario_id,))
            UWIs = self.cursor.fetchall()
            return [str(UWI[0]) for UWI in UWIs]
        except sqlite3.Error as e:
            print(f"Error retrieving UWIs for scenario_id {scenario_id}: {e}")
            return []
        finally:
            self.disconnect()

    def retrieve_error_row(self,  current_UWI, scenario_id):
        try:
            self.connect()
            query = "SELECT * FROM sum_of_errors WHERE scenario_id = ? AND UWI = ?"
            self.cursor.execute(query, (scenario_id, current_UWI))
            error_row = self.cursor.fetchone()
            if error_row:
                # Extract column names from the cursor description
                columns = [description[0] for description in self.cursor.description]
                # Convert fetched data to a DataFrame
                df = pd.DataFrame([error_row], columns=columns)
                return df
            else:
                return None
        except sqlite3.Error as e:
            print("Error retrieving error row:", e)
        finally:
            self.disconnect()

    def overwrite_model_properties(self, df_model_properties, scenario_id):
        """
        Forcefully overwrite model properties for the given UWI in a scenario.
        Deletes any existing records and inserts new ones.
        """
        try:
            df_model_properties = df_model_properties.copy()
            df_model_properties['scenario_id'] = scenario_id

            UWI_planned = df_model_properties['UWI'].iloc[0]

            print(f" Overwriting model properties for UWI: {UWI_planned}, Scenario ID: {scenario_id}")

            self.connect()

            # Step 1: Delete existing record for this planned UWI
            delete_sql = "DELETE FROM model_properties WHERE scenario_id = ? AND UWI = ?"
            self.cursor.execute(delete_sql, (scenario_id, UWI_planned))
            print(f" Deleted existing model properties for UWI: {UWI_planned}")

            # Step 2: Ensure all fields are correctly formatted
            for col in ['oil_model_status', 'gas_model_status']:
                if col in df_model_properties:
                    df_model_properties[col] = df_model_properties[col].astype(int)

            # Step 3: Convert datetime columns to strings
            date_columns = ['max_oil_production_date', 'max_gas_production_date', 'economic_limit_date']
            for col in date_columns:
                if col in df_model_properties.columns:
                    df_model_properties[col] = pd.to_datetime(df_model_properties[col], errors='coerce').dt.strftime('%Y-%m-%d')

            # Step 4: Insert new record
            df_model_properties.to_sql('model_properties', self.connection, 
                                       if_exists='append', index=False,
                                       dtype={'oil_model_status': 'INTEGER',
                                              'gas_model_status': 'INTEGER'})
            self.connection.commit()
            print(f" Inserted new model properties for UWI: {UWI_planned}")

        except sqlite3.Error as e:
            print(f" Error overwriting model properties: {e}")
            self.connection.rollback()
        finally:
            self.disconnect()

    def update_model_properties(self, df_model_properties, scenario_id):
       try:
           df_model_properties = df_model_properties.copy()
           df_model_properties['scenario_id'] = scenario_id
       
           # Convert model status columns to integer
           df_model_properties['oil_model_status'] = df_model_properties['oil_model_status'].astype(int)
           df_model_properties['gas_model_status'] = df_model_properties['gas_model_status'].astype(int)

           UWI = df_model_properties['UWI'].iloc[0]
           self.connect()

           self.cursor.execute("SELECT COUNT(*) FROM model_properties WHERE scenario_id = ? AND UWI = ?", 
                             (scenario_id, UWI))
           exists = self.cursor.fetchone()[0] > 0

           if exists:
               update_cols = [col for col in df_model_properties.columns if col not in ['UWI', 'scenario_id']]
               update_sql = f"UPDATE model_properties SET {', '.join(f'{col} = ?' for col in update_cols)} WHERE scenario_id = ? AND UWI = ?"
           
               values = []
               for col in update_cols:
                   value = df_model_properties[col].iloc[0]
                   if isinstance(value, pd.Timestamp):
                       value = value.strftime('%Y-%m-%d')
                   elif isinstance(value, pd.Series):
                       value = value.item()
                   elif isinstance(value, bool):
                       value = int(value)
                   elif col in ['oil_model_status', 'gas_model_status']:
                       value = int(value)
                   values.append(value)

               values.extend([scenario_id, UWI])
               self.cursor.execute(update_sql, values)
           else:
               # For new records, ensure integer types before insertion
               df_model_properties.to_sql('model_properties', self.connection, 
                                        if_exists='append', index=False,
                                        dtype={
                                            'oil_model_status': 'INTEGER',
                                            'gas_model_status': 'INTEGER'
                                        })
       
           self.connection.commit()
       except sqlite3.Error as e:
           print(f"Error updating model properties: {e}")
           self.connection.rollback()
       finally:
           self.disconnect()



    def update_UWI_errors(self, dataframe, scenario_id):
        """Update or insert UWI errors in the sum_of_errors table."""
        print(scenario_id)
        try:
            self.connect()

            for index, row in dataframe.iterrows():
                UWI = row['UWI']
                sum_error_oil = row['sum_error_oil']
                sum_error_gas = row['sum_error_gas']

                # Check if the scenario_id and UWI combination exists in the table
                self.cursor.execute("SELECT COUNT(*) FROM sum_of_errors WHERE scenario_id = ? AND UWI = ?", (scenario_id, UWI))
                count = self.cursor.fetchone()[0]

                if count > 0:
                    # If the combination exists, update the corresponding row
                    self.cursor.execute(
                        "UPDATE sum_of_errors SET sum_error_oil = ?, sum_error_gas = ? WHERE scenario_id = ? AND UWI = ?",
                        (sum_error_oil, sum_error_gas, scenario_id, UWI)
                    )
                else:
                    # If the combination does not exist, insert a new row
                    self.cursor.execute(
                        "INSERT INTO sum_of_errors (scenario_id, UWI, sum_error_oil, sum_error_gas) VALUES (?, ?, ?, ?)",
                        (scenario_id, UWI, sum_error_oil, sum_error_gas)
                    )

            # Commit the changes
            self.connection.commit()
            print("UWI errors updated successfully.")
        except Exception as e:
            print(f"Error updating UWI errors: {e}")
            self.connection.rollback()
        finally:
            self.disconnect()


    def update_UWI_prod_rates(self, df_production_rates, scenario_id=0):
        print(scenario_id)
        try:
            self.connect()

            # Check if the connection and cursor are valid
            if not self.connection or not self.cursor:
                print("Error: Database connection or cursor is not initialized.")
                return

            # Extract the UWI from the DataFrame
            if 'UWI' not in df_production_rates.columns:
                print("Error: 'UWI' column not found in the DataFrame")
                return

            UWI = df_production_rates['UWI'].iloc[0]
            print(f"Updating production rates for UWI: {UWI} and Scenario ID: {scenario_id}")

            # Convert date to string format
            if 'date' not in df_production_rates.columns:
                print("Error: 'date' column not found in the DataFrame")
                return

            df_production_rates['date'] = df_production_rates['date'].dt.strftime('%Y-%m-%d')

            # Start a transaction
            self.connection.execute('BEGIN')

            # Delete existing records for the specified UWI and Scenario ID
            delete_query = "DELETE FROM prod_rates_all WHERE UWI = ? AND scenario_id = ?"
            self.cursor.execute(delete_query, (UWI, scenario_id))
            deleted_rows = self.cursor.rowcount
            print(f"Deleted {deleted_rows} rows for UWI {UWI} and Scenario ID {scenario_id}")

            # Retrieve columns of the prod_rates_all table
            self.cursor.execute("PRAGMA table_info(prod_rates_all)")
            columns_info = self.cursor.fetchall()
            prod_rates_all_columns = [col[1] for col in columns_info]

            # Ensure the DataFrame has the same columns as the table, filling missing ones with None
            for col in prod_rates_all_columns:
                if col == 'scenario_id':
                    df_production_rates[col] = scenario_id  # Set the scenario_id directly
                elif col not in df_production_rates.columns:
                    df_production_rates[col] = None

            # Filter DataFrame to only include columns that exist in the table
            df_production_rates = df_production_rates[prod_rates_all_columns]

            # Insert new data
            insert_query = f"""
            INSERT INTO prod_rates_all ({', '.join(prod_rates_all_columns)})
            VALUES ({', '.join(['?' for _ in prod_rates_all_columns])})
            """

            for index, row in df_production_rates.iterrows():
                values = [row[col] if pd.notna(row[col]) else None for col in prod_rates_all_columns]
                try:
                    # Execute the INSERT statement
                    self.cursor.execute(insert_query, values)
                except Exception as e:
                    print(f"Error executing INSERT query for index {index}: {e}")
                    self.connection.rollback()
                    return

            # Commit the transaction
            self.connection.commit()
            print(f"Data updated successfully in prod_rates_all for UWI: {UWI} and Scenario ID: {scenario_id}")
        except Exception as e:
            # Rollback the transaction in case of an error
            self.connection.rollback()
            print(f"Error updating data in prod_rates_all: {e}")
        finally:
            # Ensure the connection is properly closed
            self.disconnect()




    def retrieve_prod_rates_by_UWI(self, current_UWI=None):
        try:
            self.connect()
            # Get column names
            self.cursor.execute("PRAGMA table_info(prod_rates_all)")
            columns = [column[1] for column in self.cursor.fetchall()]

            if current_UWI:
                # Select data for the specified UWI
                query = "SELECT * FROM prod_rates_all WHERE UWI = ?"
                self.cursor.execute(query, (current_UWI,))
            else:
                # Select all data from the table
                self.cursor.execute("SELECT * FROM prod_rates_all")
    
            rows = self.cursor.fetchall()
    
            # Convert rows to DataFrame with column names
            df = pd.DataFrame(rows, columns=columns)


            # Find the index of the last occurrence of oil_volume
            last_oil_index = df[df['oil_volume'].notnull()].index.max()

            # Find the index of the last occurrence of gas_volume
            last_gas_index = df[df['gas_volume'].notnull()].index.max()

            # Determine the maximum index
            max_index = max(last_oil_index, last_gas_index)

            # Slice the DataFrame to keep rows up to the maximum index
            df = df.iloc[:max_index + 1]
    
            return df
        except sqlite3.Error as e:
            print("Error retrieving production rates:", e)
            return None
        finally:
            self.disconnect()

    def get_model_status(self, current_UWI, model_type):
        # Query the database to get the model status for the specified type and UWI
        try:
            self.connect()
            query = f"SELECT {model_type}_model_status FROM model_properties WHERE UWI = ?"
            self.cursor.execute(query, (current_UWI,))
            result = self.cursor.fetchone()
            if result:
                return result[0]  # Assuming the model status is the first column in the result
            else:
                return None
        except sqlite3.Error as e:
            print(f"Error retrieving {model_type} model status:", e)
            return None
        finally:
            self.disconnect()

    def update_model_status(self, current_UWI, new_status, model_type):
        try:
            self.connect()
            query = f"UPDATE model_properties SET {model_type}_model_status = CAST(? AS INTEGER) WHERE UWI = ?"
            self.cursor.execute(query, (int(new_status), current_UWI))
            self.connection.commit()
        except sqlite3.Error as e:
            print(f"Error updating {model_type} model status:", e)

    def delete_UWI_records(self, UWI):
        # Ensure there's an active database connection
        self.connect()  # Assuming this method sets up self.connection if not already connected

            # List of tables from which to delete records
        tables = ['model_properties', 'prod_rates_all', 'sum_of_errors', 'UWIs']
        for table in tables:
            # SQL query that deletes rows where the UWI matches the given UWI
            query = f"DELETE FROM {table} WHERE UWI = ?"
            self.cursor.execute(query, (UWI,))  # Execute the query with the UWI parameter

            # Commit the changes to the database
        self.connection.commit()
      
        self.disconnect()

    def retrieve_and_sum(self, scenario_id):
        try:
            self.connect()

            # Get column names
            self.cursor.execute("PRAGMA table_info(prod_rates_all)")
            columns = [column[1] for column in self.cursor.fetchall()]

            # Define query to fetch data based on scenario_id
            if scenario_id == 1:
                self.cursor.execute("SELECT * FROM prod_rates_all WHERE scenario_id = ?", (scenario_id,))
            else:
                self.cursor.execute("SELECT * FROM prod_rates_all WHERE scenario_id IN (?, ?)", (1, scenario_id))

            rows = self.cursor.fetchall()

            # Convert rows to DataFrame with column names
            df = pd.DataFrame(rows, columns=columns)

            if df.empty:
                print(f"No production rate data found for scenario {scenario_id}")
                return None, None

            # Ensure date column is in datetime format
            df['date'] = pd.to_datetime(df['date'])

            # Group by date and sum total_revenue and discounted_revenue
            combined_data = df.groupby('date').agg({
                'total_revenue': 'sum',
                'discounted_revenue': 'sum'
            }).reset_index()

            # Retrieve the first and last date for each well
            date_ranges = df.groupby('UWI')['date'].agg(['min', 'max']).reset_index()
            date_ranges.columns = ['UWI', 'first_date', 'last_date']

            return combined_data, date_ranges

        except sqlite3.Error as e:
            print("Error retrieving production rates:", e)
            return None, None

        finally:
            self.disconnect()



    def create_saved_dca_table(self):
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS saved_dca (
            id INTEGER PRIMARY KEY,
            curve_name TEXT NOT NULL,
            UWI TEXT,
            max_oil_production REAL NULL,
            max_gas_production REAL NULL,
            max_oil_production_date TEXT DEFAULT NULL,
            max_gas_production_date TEXT DEFAULT NULL,
            one_year_oil_production REAL NULL,
            one_year_gas_production REAL NULL,
            di_oil REAL NULL,
            di_gas REAL NULL,
            gas_b_factor REAL DEFAULT NULL,
            min_dec_gas REAL DEFAULT NULL,
            oil_b_factor REAL DEFAULT NULL,
            min_dec_oil REAL DEFAULT NULL,
            model_oil TEXT DEFAULT NULL,
            model_gas TEXT DEFAULT NULL,
            economic_limit_type TEXT DEFAULT 'Net Dollars',
            economic_limit_date TEXT DEFAULT NULL,
            oil_price REAL DEFAULT NULL,
            gas_price REAL DEFAULT NULL,
            oil_price_dif REAL DEFAULT NULL,
            gas_price_dif REAL DEFAULT NULL,
            discount_rate REAL DEFAULT NULL,
            working_interest REAL DEFAULT NULL,
            royalty REAL DEFAULT NULL,
            tax_rate REAL DEFAULT NULL,
            capital_expenditures REAL DEFAULT NULL,
            operating_expenditures REAL DEFAULT NULL,

            net_price_oil REAL DEFAULT NULL,
            net_price_gas REAL DEFAULT NULL
            
        )
        """
        try:
            self.connect()
            self.cursor.execute(create_table_sql)
            self.connection.commit()
            print("saved_dca table created successfully.")
        except sqlite3.Error as e:
            print("Error creating saved_dca table:", e)
        finally:
            self.disconnect()

    def save_decline_curve_to_db(self, curve_name, UWI_model_data):
        if not isinstance(UWI_model_data, pd.DataFrame):
            print("Error: UWI_model_data is not a DataFrame")
            return

        # Add curve_name column to the DataFrame
        UWI_model_data['curve_name'] = curve_name

        try:
            self.connect()

            # Retrieve columns of the saved_dca table
            self.cursor.execute("PRAGMA table_info(saved_dca)")
            columns_info = self.cursor.fetchall()
            saved_dca_columns = [col[1] for col in columns_info]

            # Ensure the DataFrame has the same columns as the table
            for col in saved_dca_columns:
                if col not in UWI_model_data.columns:
                    UWI_model_data[col] = None

            # Reorder DataFrame columns to match the table columns
            UWI_model_data = UWI_model_data[saved_dca_columns]

            # Delete existing rows with the same curve_name
            delete_sql = "DELETE FROM saved_dca WHERE curve_name = ?"
            self.cursor.execute(delete_sql, (curve_name,))

            # Insert data into the main table
            for index, row in UWI_model_data.iterrows():
                insert_sql = """
                INSERT INTO saved_dca ({})
                VALUES ({})
                """.format(
                    ", ".join(saved_dca_columns),
                    ", ".join(["?"] * len(saved_dca_columns))
                )
                self.cursor.execute(insert_sql, tuple(row))

            # Commit the transaction
            self.connection.commit()
            print(f"Data saved successfully in saved_dca for curve_name {curve_name}")
        except Exception as e:
            # Rollback the transaction in case of an error
            self.connection.rollback()
            print(f"Error saving data to saved_dca: {e}")
        finally:
            self.disconnect()


    def get_decline_curve_names(self):
        try:
            self.connect()
            self.cursor.execute("SELECT DISTINCT curve_name FROM saved_dca")
            decline_curves = [row[0] for row in self.cursor.fetchall()]
        except sqlite3.Error as e:
            print(f"An error occurred while retrieving decline curve names: {e}")
            decline_curves = []
        finally:
            self.disconnect()
        return decline_curves

    def get_decline_curve_name(self, decline_curve_id):
        self.connect()
        try:
            query = "SELECT curve_name FROM saved_dca WHERE id = ?"
            self.cursor.execute(query, (decline_curve_id,))
            result = self.cursor.fetchone()
            if result:
                return result[0]
            else:
                return None
        except sqlite3.Error as e:
            print("Error fetching decline curve name:", e)
            return None
        finally:
            self.disconnect()

    def get_decline_curve_data(self, curve_name):
        try:
            self.connect()
            self.cursor.execute("SELECT * FROM saved_dca WHERE curve_name = ?", (curve_name,))
            row = self.cursor.fetchone()
            if row:
                # Assuming the columns are in the same order as in your database table
                columns = [col[0] for col in self.cursor.description]
                decline_curve_data = dict(zip(columns, row))
                return decline_curve_data
            else:
                return None
        except sqlite3.Error as e:
            print(f"Error fetching decline curve data: {e}")
            return None
        finally:
            self.disconnect()

    def get_saved_decline_curve_data(self, curve_name):
        """
        Fetch all relevant decline curve data from the saved_dca table using the curve name.
        :param curve_name: Name of the saved decline curve.
        :return: Dictionary with decline curve data.
        """
        self.connect()
        try:
            query = """
            SELECT curve_name, UWI, max_oil_production, max_gas_production,
                   max_oil_production_date, max_gas_production_date, one_year_oil_production,
                   one_year_gas_production, di_oil, di_gas, oil_b_factor, gas_b_factor,
                   min_dec_oil, min_dec_gas, model_oil, model_gas, economic_limit_type,
                   economic_limit_date, oil_price, gas_price, oil_price_dif, gas_price_dif,
                   discount_rate, working_interest, royalty, tax_rate, capital_expenditures,
                   operating_expenditures, net_price_oil, net_price_gas
            FROM saved_dca
            WHERE curve_name = ?;
            """
            self.cursor.execute(query, (curve_name,))
            result = self.cursor.fetchone()

            if result:
                columns = [desc[0] for desc in self.cursor.description]
                return dict(zip(columns, result))
            else:
                logging.warning(f"No saved decline curve found for curve_name: {curve_name}")
                return None
        except Exception as e:
            logging.error(f"Error fetching saved decline curve data: {e}")
            return None
        finally:
            self.disconnect()



    def get_UWI_status(self, current_UWI):
        try:
            self.connect()
            # Define the query to check the status of the current UWI
            self.cursor.execute("SELECT status FROM UWIs WHERE UWI = ?", (current_UWI,))
            result = self.cursor.fetchone()
        
            print(result[0])  # Debug print to show the result
        
            if result and result[0] == 'Planned':  # Extract the status from the tuple
                return True
            else:
                return False
        except Exception as e:
            print(f"Error retrieving status for UWI {current_UWI}: {e}")
        finally:
            # Ensure the database connection is closed
            self.disconnect()


    def retrieve_aggregated_prod_rates(self, columns, scenario_id):
        print(columns)
        self.connect()
        query = f"""
        SELECT UWI, strftime('%Y-%m', date) as date, {', '.join(columns)}
        FROM prod_rates_all
        WHERE scenario_id = ?
        GROUP BY UWI, date
        """
        try:
            df = pd.read_sql_query(query, self.connection, params=(scenario_id,))
        finally:
            self.disconnect()
        return df

    def create_well_pads_table(self):
        self.connect()
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS well_pads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pad_name VARCHAR(255) UNIQUE,
            UWI VARCHAR(255),
            scenario_id INTEGER,
            start_date DATE,
            decline_curve_type VARCHAR(255),
            decline_curve VARCHAR(255),
            total_depth DECIMAL(10, 2),
            total_capex_cost DECIMAL(15, 2),
            total_opex_cost DECIMAL(15, 2),
            drill_time INTEGER,
            prod_type VARCHAR(50),
            oil_model_status INTEGER,
            gas_model_status INTEGER,
            pad_cost DECIMAL(15, 2),
            exploration_cost DECIMAL(15, 2),
            cost_per_foot DECIMAL(10, 2),
            distance_to_pipe DECIMAL(10, 2),
            cost_per_foot_to_pipe DECIMAL(10, 2),
            FOREIGN KEY (UWI) REFERENCES UWIs (UWI),
            FOREIGN KEY (scenario_id) REFERENCES scenario_names (id)
        )
        """
        try:
            self.cursor.execute(create_table_sql)
            self.connection.commit()
            print("well_pads table created successfully.")
        except sqlite3.Error as e:
            print("Error creating well_pads table:", e)
        finally:
            self.disconnect()

    def delete_pad(self, scenario_id, UWI):
        """Delete a pad from the database based on scenario ID and UWI."""
        query = """
        DELETE FROM well_pads
        WHERE scenario_id = ? AND UWI = ?
        """
        try:
            self.connect()
            cursor = self.connection.cursor()
            cursor.execute(query, (scenario_id, UWI))
            self.connection.commit()
            logging.info(f"Deleted pad: Scenario ID={scenario_id}, UWI={UWI}")
        except sqlite3.Error as e:
            logging.error(f"Error deleting pad: {e}")
            self.connection.rollback()
            raise
        finally:
            cursor.close()
            self.disconnect()



    def get_scenario_wells(self, scenario_id):
        """Get all well data currently in a specific scenario"""
        try:
            self.connect()
            query = """
            SELECT * 
            FROM well_pads 
            WHERE scenario_id = ?
            """
        
            # Read directly into DataFrame using pandas
            scenario_wells_df = pd.read_sql_query(query, self.connection, params=(scenario_id,))
        
            print("DataFrame retrieved from database:")
            print(scenario_wells_df)
            print("\nColumns:", scenario_wells_df.columns.tolist())
        
            return scenario_wells_df
        
        except sqlite3.Error as e:
            print(f"Error getting scenario wells: {e}")
            logging.error(f"Database error: {e}")
            return pd.DataFrame()  # Return empty DataFrame on error
        finally:
            self.disconnect()

    def remove_well_pad_for_scenario(self, UWI, scenario_id):
        """
        Remove a well pad from the well_pads table for the given UWI and scenario_id.

        :param UWI: The unique well identifier (UWI) to remove.
        :param scenario_id: The scenario ID associated with the well pad to remove.
        """
        query = """
        DELETE FROM well_pads
        WHERE UWI = ? AND scenario_id = ?
        """
        try:
            self.connect()
            cursor = self.connection.cursor()
            cursor.execute(query, (UWI, scenario_id))
            self.connection.commit()
            print(f"Well pad with UWI '{UWI}' removed from scenario ID {scenario_id}.")
        except sqlite3.Error as e:
            print(f"Error removing well pad for UWI '{UWI}' and scenario ID {scenario_id}:", e)
            self.connection.rollback()
        finally:
            cursor.close()
            self.disconnect()



    def insert_well_pad(self, well_pad_data):
        """
        Insert a new well pad into the well_pads table.

        :param well_pad_data: A dictionary containing well pad data.
        """
        # Validate required keys
        if 'UWI' not in well_pad_data or 'scenario_id' not in well_pad_data:
            raise ValueError("Both 'UWI' and 'scenario_id' are required fields.")

        query = """
        INSERT INTO well_pads (
            UWI,
            scenario_id,
            total_depth,
            total_capex_cost,
            total_opex_cost,
            drill_time,
            prod_type,
            oil_model_status,
            gas_model_status,
            pad_cost,
            exploration_cost,
            cost_per_foot,
            distance_to_pipe,
            cost_per_foot_to_pipe,
            decline_curve,
            decline_curve_type,
            start_date
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        try:
            self.connect()
            cursor = self.connection.cursor()

            # Use .get() for optional fields to provide default value (None) if they are missing
            cursor.execute(query, (
                well_pad_data['UWI'],                           # Required
                well_pad_data['scenario_id'],                  # Required
                well_pad_data.get('total_depth'),            # Optional
                well_pad_data.get('total_capex_cost'),         # Optional
                well_pad_data.get('total_opex_cost'),          # Optional
                well_pad_data.get('drill_time'),               # Optional
                well_pad_data.get('prod_type'),                # Optional
                well_pad_data.get('oil_model_status'),         # Optional
                well_pad_data.get('gas_model_status'),         # Optional
                well_pad_data.get('pad_cost'),                 # Optional
                well_pad_data.get('exploration_cost'),         # Optional
                well_pad_data.get('cost_per_foot'),            # Optional
                well_pad_data.get('distance_to_pipe'),         # Optional
                well_pad_data.get('cost_per_foot_to_pipe'),    # Optional
                well_pad_data.get('decline_curve'),   
                well_pad_data.get('decline_curve_type'),# Optional
                well_pad_data.get('start_date')               # Optional
            ))

            self.connection.commit()
            print("Well pad inserted successfully.")
            return cursor.lastrowid  # Return the ID of the inserted row
        except sqlite3.Error as e:
            print("Error inserting well pad into well_pads table:", e)
            self.connection.rollback()
            return None
        finally:
            cursor.close()
            self.disconnect()

    def update_well_pad_decline_curve(self, planned_UWI, scenario_id, matched_UWI):
        """
        Update the decline_curve for a planned well in a specific scenario.
        Only updates if the well exists in the given scenario.
    
        :param planned_UWI: The UWI of the planned well
        :param scenario_id: The scenario ID to check/update
        :param matched_UWI: The matched UWI to set as decline_curve
        """
        # First check if well exists in this scenario
        check_query = """
        SELECT UWI 
        FROM well_pads 
        WHERE UWI = ? AND scenario_id = ?
        """
    
        # Update query to run if match found
        update_query = """
        UPDATE well_pads
        SET 
            decline_curve = ?,
            decline_curve_type = 'UWI'
        WHERE
            UWI = ? 
            AND scenario_id = ?
        """
    
        try:
            self.connect()
            cursor = self.connection.cursor()
        
            # Check for existing well in scenario
            cursor.execute(check_query, (planned_UWI, scenario_id))
            result = cursor.fetchone()
        
            if result:
                # Well exists in scenario, proceed with update
                # Fixed parameter order to ensure matched_UWI goes into decline_curve
                cursor.execute(update_query, (matched_UWI, planned_UWI, scenario_id))
                self.connection.commit()
            
                # Updated print statement to show actual values being set
                print(f"✅ Well pad for UWI {planned_UWI} updated:")
                print(f"   → decline_curve = {matched_UWI}, decline_curve_type = 'UWI', scenario_id = {scenario_id}")
            else:
                print(f"❌ No matching well found for UWI {planned_UWI} in Scenario {scenario_id}")
            
        except sqlite3.Error as e:
            print(f"❌ Error updating decline curve: {e}")
            self.connection.rollback()
        finally:
            cursor.close()
            self.disconnect()



    def update_well_pad_decline_curve(self, planned_UWI, scenario_id, matched_UWI):
        """
        Update the decline_curve for a planned well in a specific scenario.
        Only updates if the well exists in the given scenario.
    
        :param planned_UWI: The UWI of the planned well
        :param scenario_id: The scenario ID to check/update
        :param matched_UWI: The matched UWI to set as decline_curve
        """
        check_query = """
        SELECT UWI 
        FROM well_pads 
        WHERE UWI = ? AND scenario_id = ?
        """
    
        update_query = """
        UPDATE well_pads
        SET decline_curve = ?,
            decline_curve_type = 'UWI'
        WHERE UWI = ? AND scenario_id = ?
        """
    
        try:
            self.connect()
            cursor = self.connection.cursor()
        
            print("DEBUG - Input values:")
            print(f"planned_UWI: {planned_UWI}")
            print(f"scenario_id: {scenario_id}")
            print(f"matched_UWI: {matched_UWI}")
        
            cursor.execute(check_query, (planned_UWI, scenario_id))
            result = cursor.fetchone()
        
            if result:
                cursor.execute(update_query, (matched_UWI, planned_UWI, scenario_id))
                self.connection.commit()
            
                print("\nDEBUG - After update:")
                print(f"SET decline_curve = {matched_UWI}")
                print(f"WHERE UWI = {planned_UWI}")
                print(f"AND scenario_id = {scenario_id}")
            
            else:
                print(f"No matching well found for UWI {planned_UWI} in Scenario {scenario_id}")
            
        except sqlite3.Error as e:
            print(f"Error updating decline curve: {e}")
            self.connection.rollback()
        finally:
            cursor.close()
            self.disconnect()

    def update_well_pad_all(self, well_pad_id, well_pad_data):
        """
        Update well pad data in the well_pads table.

        :param well_pad_id: The ID of the well pad to update.
        :param well_pad_data: A dictionary containing updated well pad data.
        """
        query = """
        UPDATE well_pads
        SET 
            total_depth = ?,
            total_capex_cost = ?,
            total_opex_cost = ?,
            drill_time = ?,
            prod_type = ?,
            oil_model_status = ?,
            gas_model_status = ?,
            pad_cost = ?,
            exploration_cost = ?,
            cost_per_foot = ?,
            distance_to_pipe = ?,
            cost_per_foot_to_pipe = ?,
            decline_curve = ?,
            decline_curve_type = ?,
            start_date = ?
        WHERE
            id = ?
        """
        try:
            self.connect()
            cursor = self.connection.cursor()
            cursor.execute(query, (
                well_pad_data['total_depth'],
                well_pad_data['total_capex_cost'],
                well_pad_data['total_opex_cost'],
                well_pad_data['drill_time'],
                well_pad_data['prod_type'],
                well_pad_data['oil_model_status'],
                well_pad_data['gas_model_status'],
                well_pad_data['pad_cost'],
                well_pad_data['exploration_cost'],
                well_pad_data['cost_per_foot'],
                well_pad_data['distance_to_pipe'],
                well_pad_data['cost_per_foot_to_pipe'],
                well_pad_data['decline_curve'],
                well_pad_data['decline_curve_type'],
                well_pad_data['start_date'],  # Added start_date
                well_pad_id
            ))
            self.connection.commit()
            print(f"Well pad with ID {well_pad_id} updated successfully.")
        except sqlite3.Error as e:
            print("Error updating well pad in well_pads table:", e)
            self.connection.rollback()
        finally:
            cursor.close()
            self.disconnect()

    def update_well_pad_decline_data(self, well_pad_id, start_date, decline_curve_type, decline_curve):
        """Update only Start Date, Decline Curve Type, and Decline Curve in the well_pads table."""
        query = """
        UPDATE well_pads
        SET start_date = ?, decline_curve_type = ?, decline_curve = ?
        WHERE id = ?
        """
        try:
            self.connect()
            cursor = self.connection.cursor()
            cursor.execute(query, (start_date, decline_curve_type, decline_curve, well_pad_id))
            self.connection.commit()
            print(f"Updated Well Pad ID {well_pad_id}: Start Date = {start_date}, Decline Curve Type = {decline_curve_type}, Decline Curve = {decline_curve}")
        except sqlite3.Error as e:
            print("Error updating well pad:", e)
            self.connection.rollback()
        finally:
            cursor.close()
            self.disconnect()

    def add_well_to_scenario(self, well_scenario_data):
        """Add or update a well in a scenario with more detailed data"""
        try:
            self.connect()
            query = """
            INSERT OR REPLACE INTO well_pads (
                UWI, scenario_id, start_date, decline_curve
            ) VALUES (?, ?, ?, ?)
            """
            self.cursor.execute(query, (
                well_scenario_data['UWI'], 
                well_scenario_data['scenario_id'], 
                well_scenario_data['start_date'], 
                well_scenario_data['decline_curve']
            ))
            self.connection.commit()
            return True
        except sqlite3.Error as e:
            print(f"Error adding well to scenario: {e}")
            self.connection.rollback()
            return False
        finally:
            self.disconnect()



    def store_sum_of_errors_dataframe(self, sum_of_errors_dataframe, scenario_id):
        """Store the sum of errors DataFrame into a specified table in the database."""
        try:
            self.connect()  # Ensure connection is open

            for index, row in sum_of_errors_dataframe.iterrows():
                # Convert the row to a dictionary
                row_dict = row.to_dict()
                row_dict['scenario_id'] = scenario_id

                # Create an insert or replace query
                insert_or_replace_query = """
                INSERT OR REPLACE INTO sum_of_errors (scenario_id, UWI, sum_error_oil, sum_error_gas)
                VALUES (?, ?, ?, ?)
                """

                # Execute the query
                self.cursor.execute(insert_or_replace_query, (
                    row_dict['scenario_id'],
                    row_dict['UWI'],
                    row_dict['sum_error_oil'],
                    row_dict['sum_error_gas']
                ))

            self.connection.commit()
            print(f"Sum of errors data stored successfully for scenario_id {scenario_id}")
        except Exception as e:
            print(f"Error storing sum of errors data for scenario_id {scenario_id}: {e}")
            self.connection.rollback()
        finally:
            self.disconnect()


    def update_well_pad(self, well_pad_id, well_pad_data):
        """Update well pad data in the well_pads table."""
        query = """
        UPDATE well_pads
        SET 
            total_depth = ?,
            total_capex_cost = ?,
            total_opex_cost = ?,
            drill_time = ?,
            prod_type = ?,
            oil_model_status = ?,
            gas_model_status = ?,
            pad_cost = ?,
            exploration_cost = ?,
            cost_per_foot = ?,
            distance_to_pipe = ?,
            cost_per_foot_to_pipe = ?,
            start_date = ?
        WHERE
            id = ?
        """
        try:
            self.connect()
            cursor = self.connection.cursor()
            cursor.execute(query, (
                well_pad_data['total_depth'],
                well_pad_data['total_capex_cost'],
                well_pad_data['total_opex_cost'],
                well_pad_data['drill_time'],
                well_pad_data['prod_type'],
                well_pad_data['oil_model_status'],
                well_pad_data['gas_model_status'],
                well_pad_data['pad_cost'],
                well_pad_data['exploration_cost'],
                well_pad_data['cost_per_foot'],
                well_pad_data['distance_to_pipe'],
                well_pad_data['cost_per_foot_to_pipe'],
                well_pad_data['start_date'],  # Add start_date here
                well_pad_id
            ))
            self.connection.commit()
            print(f"Well pad with ID {well_pad_id} updated successfully.")
        except sqlite3.Error as e:
            print("Error updating well pad in well_pads table:", e)
            self.connection.rollback()
        finally:
            cursor.close()
            self.disconnect()

    def get_total_lengths(self):
        """
        Fetches the UWI and total length from the database.
        """
        try:
            self.connect()  # Ensure your database connection method is functional
            self.cursor.execute("SELECT UWI, total_length FROM UWIs")
            results = self.cursor.fetchall()  # Fetch all results
            return [{"UWI": str(row[0]), "total_length": row[1]} for row in results]
        except sqlite3.Error as e:
            print("Error retrieving UWIs and total lengths:", e)
            return []
        finally:
            self.disconnect()  # Ensure the connection is properly closed

    def get_scenario_id(self, scenario_name):
        """
        Fetches the scenario_id based on the provided scenario_name.

        Args:
            scenario_name (str): The name of the scenario to look up.

        Returns:
            int: The scenario_id associated with the given scenario_name.
            None: If the scenario_name does not exist or an error occurs.
        """
        self.connect()
        select_sql = "SELECT scenario_id FROM scenario_names WHERE scenario_name = ?"
        try:
            self.cursor.execute(select_sql, (scenario_name,))
            scenario_id = self.cursor.fetchone()
            if scenario_id:
                return scenario_id[0]  # Return the scenario ID as an integer
            else:
                return None  # Return None if scenario_name is not found
        except sqlite3.Error as e:
            print("Error fetching scenario ID:", e)
            return None
        finally:
            self.disconnect()


    def get_scenario_names(self):
        self.connect()
        select_sql = "SELECT scenario_name FROM scenario_names"
        try:
            self.cursor.execute(select_sql)
            scenarios = [row[0] for row in self.cursor.fetchall()]
            return scenarios
        except sqlite3.Error as e:
            print("Error fetching scenario names:", e)
            return []
        finally:
            self.disconnect()

    def get_scenario_name(self, scenario_id):
        self.connect()
        select_sql = "SELECT scenario_name FROM scenario_names WHERE scenario_id = ?"
        try:
            self.cursor.execute(select_sql, (scenario_id,))
            scenario_name = self.cursor.fetchone()
            if scenario_name:
                return scenario_name[0]  # Return the scenario name as a string
            else:
                return None  # Return None if scenario_id is not found
        except sqlite3.Error as e:
            print("Error fetching scenario name:", e)
            return None
        finally:
            self.disconnect()

    def get_well_pads(self, scenario_id):
        query = """
        SELECT 
            id, 
            UWI, 
            start_date,
            decline_curve_type,
            decline_curve,
            total_depth, 
            total_capex_cost, 
            total_opex_cost, 
            drill_time, 
            prod_type, 
            oil_model_status, 
            gas_model_status,
            pad_cost, 
            exploration_cost, 
            cost_per_foot, 
            distance_to_pipe, 
            cost_per_foot_to_pipe
        FROM well_pads
        WHERE scenario_id = ?
        """
        try:
            self.connect()
            cursor = self.connection.cursor()
            cursor.execute(query, (scenario_id,))
            rows = cursor.fetchall()
        
            # Get the column names from cursor description
            columns = [column[0] for column in cursor.description]
        
            # Create list of dictionaries with all fields
            well_pads = [dict(zip(columns, row)) for row in rows]
        
            # Debug print
            print(f"\nDEBUG - Database Query Results:")
            print(f"Columns retrieved: {columns}")
            if well_pads:
                print(f"First well pad data: {well_pads[0]}")
        
            return well_pads
        
        except sqlite3.Error as e:
            print(f"Error fetching well pads for scenario_id {scenario_id}:", e)
            return []
        finally:
            cursor.close()
            self.disconnect()

    def get_well_pad_data(self, well_pad_id):
        """
        Retrieve data for a specific well pad by its ID.
    
        :param well_pad_id: The ID of the well pad to retrieve
        :return: Dictionary containing well pad data or None if not found
        """
        query = """
        SELECT 
            id, 
            UWI, 
            start_date,
            decline_curve_type,
            decline_curve,
            total_depth, 
            total_capex_cost, 
            total_opex_cost, 
            drill_time, 
            prod_type, 
            oil_model_status, 
            gas_model_status,
            pad_cost, 
            exploration_cost, 
            cost_per_foot, 
            distance_to_pipe, 
            cost_per_foot_to_pipe
        FROM well_pads
        WHERE id = ?
        """
    
        try:
            self.connect()
            cursor = self.connection.cursor()
            cursor.execute(query, (well_pad_id,))
            row = cursor.fetchone()
        
            if row:
                # Get the column names from cursor description
                columns = [column[0] for column in cursor.description]
                # Create dictionary with field names
                well_pad_data = dict(zip(columns, row))
                return well_pad_data
            return None
        
        except sqlite3.Error as e:
            print(f"Error fetching well pad data for id {well_pad_id}:", e)
            return None
        finally:
            cursor.close()
            self.disconnect()
    def get_well_pads_for_wells(self, scenario_id, well_UWIs):
        """
        Retrieve well pad data for specific wells in a given scenario.

        :param scenario_id: Scenario ID to filter well pads.
        :param well_UWIs: List of UWIs to filter the well pads.
        :return: DataFrame containing well pad data for the specified wells.
        """
        if not well_UWIs:
            return pd.DataFrame()  # Return an empty DataFrame if no wells are selected

        query = """
        SELECT id, UWI, total_depth, total_capex_cost, total_opex_cost, drill_time, prod_type, oil_model_status, gas_model_status,
               pad_cost, exploration_cost, cost_per_foot, distance_to_pipe, cost_per_foot_to_pipe, start_date
        FROM well_pads
        WHERE scenario_id = ? AND UWI IN ({})
        """.format(",".join("?" * len(well_UWIs)))

        try:
            self.connect()
            cursor = self.connection.cursor()
            cursor.execute(query, [scenario_id] + well_UWIs)
            rows = cursor.fetchall()

            # Get the column names
            columns = [column[0] for column in cursor.description]

            # Convert to a DataFrame
            well_pads_df = pd.DataFrame(rows, columns=columns)

            return well_pads_df
        except sqlite3.Error as e:
            print(f"Error fetching well pads for scenario_id {scenario_id} and selected wells:", e)
            return pd.DataFrame()
        finally:
            cursor.close()
            self.disconnect()



    def create_scenario_names_table(self):
        self.connect()
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS scenario_names (
            scenario_id INTEGER PRIMARY KEY AUTOINCREMENT,
            scenario_name VARCHAR(255) NOT NULL UNIQUE,
            active BOOLEAN NOT NULL DEFAULT 0
        )
        """
        try:
            self.cursor.execute(create_table_sql)
            self.connection.commit()
            print("scenario_names table created successfully.")
        except sqlite3.Error as e:
            print("Error creating scenario_names table:", e)
        finally:
            self.disconnect()

    def insert_scenario_name(self, scenario_name):
        """
        Insert a new scenario into the scenario_names table with active = 0 by default.

        :param scenario_name: Name of the scenario to insert.
        :return: The ID of the newly inserted scenario, or None if an error occurs.
        """
        try:
            self.connect()

            # Insert scenario with active = 0 by default
            insert_sql = """
            INSERT INTO scenario_names (scenario_name, active)
            VALUES (?, 0)
            """
            self.cursor.execute(insert_sql, (scenario_name,))
            self.connection.commit()

            inserted_id = self.cursor.lastrowid
            logging.info(f"Scenario '{scenario_name}' added successfully with ID {inserted_id}. Active: 0")
            return inserted_id

        except sqlite3.IntegrityError:
            logging.warning(f"Scenario '{scenario_name}' already exists.")
            return None

        except sqlite3.Error as e:
            logging.error(f"Error adding scenario '{scenario_name}': {e}")
            self.connection.rollback()
            return None

        finally:
            self.disconnect()

    def get_all_scenarios(self):
        query = "SELECT scenario_id, scenario_name FROM scenario_names"
        self.connect()
        try:
            self.cursor.execute(query)
            scenarios = self.cursor.fetchall()
            return [{'id': row[0], 'name': row[1]} for row in scenarios]
        except sqlite3.Error as e:
            print("Error fetching scenarios:", e)
            return []
        finally:
            self.disconnect()

    def get_all_scenario_names(self):
        query = "SELECT scenario_name FROM scenario_names"
        self.connect()
        try:
            self.cursor.execute(query)
            scenario_names = self.cursor.fetchall()
            return [row[0] for row in scenario_names]
        except sqlite3.Error as e:
            print("Error fetching scenario names:", e)
            return []
        finally:
            self.disconnect()

    def get_active_scenario_id(self):
        query = "SELECT scenario_id FROM scenario_names WHERE active = 1"
        self.connect()
        try:
            self.cursor.execute(query)
            active_scenario = self.cursor.fetchone()
            return active_scenario[0] if active_scenario else None
        except sqlite3.Error as e:
            print("Error fetching active scenario:", e)
            return None
        finally:
            self.disconnect()

    def get_uiws_for_scenario(self, scenario_id):
        """Retrieve all UIWs associated with a specific scenario."""
        try:
            self.connect()
            query = "SELECT UWI FROM well_pads WHERE scenario_id = ?"
            self.cursor.execute(query, (scenario_id,))
            rows = self.cursor.fetchall()
            return [row[0] for row in rows]  # Extract UIWs
        except sqlite3.Error as e:
            logging.error(f"Error retrieving UIWs for scenario {scenario_id}: {e}")
            return []
        finally:
            self.disconnect()

    def deactivate_all_scenarios(self, disconnect_after=True):
        update_sql = "UPDATE scenario_names SET active = 0"
        self.connect()
        try:
            self.cursor.execute(update_sql)
            self.connection.commit()
            print("All scenarios deactivated.")
        except sqlite3.Error as e:
            print("Error deactivating scenarios:", e)
            self.connection.rollback()
        finally:
            if disconnect_after:
                self.disconnect()

    def set_active_scenario(self, scenario_id):
        self.deactivate_all_scenarios(False)
        update_sql = "UPDATE scenario_names SET active = 1 WHERE scenario_id = ?"
        self.connect()
        try:
            self.cursor.execute(update_sql, (scenario_id,))
            self.connection.commit()
            print(f"Scenario {scenario_id} set as active.")
        except sqlite3.Error as e:
            print(f"Error setting scenario {scenario_id} as active:", e)
            self.connection.rollback()
        finally:
            self.disconnect()




    def add_or_update_scenario(self, scenario_data):
        self.connect()
        try:
            # Check if the scenario exists for the given scenario_id and well_pad_id
            select_sql = "SELECT scenario_id FROM scenarios WHERE scenario_id = ? AND well_pad_id = ?"
            self.cursor.execute(select_sql, (scenario_data['scenario_id'], scenario_data['well_pad_id']))
            existing_scenario = self.cursor.fetchone()

            if existing_scenario:
                # Scenario exists, update the start_date and decline_curve_id
                update_sql = """
                UPDATE scenarios
                SET start_date = ?,
                    decline_curve_id = ?
                WHERE scenario_id = ? AND well_pad_id = ?
                """
                self.cursor.execute(update_sql, (
                    scenario_data['decline_curve_id'],
                    scenario_data['scenario_id'],
                    scenario_data['well_pad_id']
                ))
                print(f"Scenario updated successfully for scenario_id: {scenario_data['scenario_id']} and well_pad_id: {scenario_data['well_pad_id']}")

                # Fetch the updated scenario_id
                updated_scenario_id = scenario_data['scenario_id']
                return updated_scenario_id

            else:
                # Scenario does not exist, insert a new scenario
                insert_sql = """
                INSERT INTO scenarios (scenario_id, well_pad_id, start_date, decline_curve_id)
                VALUES (?, ?, ?, ?)
                """
                self.cursor.execute(insert_sql, (
                    scenario_data['scenario_id'],
                    scenario_data['well_pad_id'],
                    scenario_data['decline_curve_id']
                ))
                print("Scenario inserted successfully.")

                # Fetch the newly inserted scenario_id
                new_scenario_id = self.cursor.lastrowid
                return new_scenario_id

            self.connection.commit()  # Commit the transaction

        except sqlite3.Error as e:
            print("Error adding or updating scenario:", e)
            self.connection.rollback()  # Rollback in case of error
            return None

        finally:
            self.connection.commit() 
            self.disconnect()  # Disconnect from the database




    def get_active_scenario_name(self):
        self.connect()
        query = "SELECT scenario_name FROM scenario_names WHERE Active = 1"
        try:
            self.cursor.execute(query)
            result = self.cursor.fetchone()
            if result:
                return result[0]  # Return the scenario name as a string
            else:
                return None  # Return None if no active scenario found
        except sqlite3.Error as e:
            print("Error fetching active scenario name:", e)
            return None
        finally:
            self.disconnect()

    def get_active_scenario_id(self):
        self.connect()
        query_sql = """
        SELECT scenario_id FROM scenario_names WHERE active = 1
        """
        try:
            self.cursor.execute(query_sql)
            result = self.cursor.fetchone()
            if result:
                return result[0]
            else:
                return None
        except sqlite3.Error as e:
            print("Error getting active scenario ID:", e)
        finally:
            self.disconnect()

    def get_scenario_details(self, scenario_id):
        self.connect()
        query = """
        SELECT well_pad_id, start_date, decline_curve_id
        FROM well_pads 
        WHERE scenario_id = ?
        """
        try:
            self.cursor.execute(query, (scenario_id,))
            scenarios = self.cursor.fetchall()
            scenario_details_list = []

            for scenario in scenarios:
                columns = [column[0] for column in self.cursor.description]
                scenario_details = dict(zip(columns, scenario))
                scenario_details_list.append(scenario_details)
            print(scenario_details_list)
            return scenario_details_list if scenario_details_list else None

        except sqlite3.Error as e:
            print(f"Error retrieving scenario details: {e}")
            return None
        finally:
            self.disconnect()


    def get_scenario_id(self, scenario_name):
        self.connect()
        query = "SELECT scenario_id FROM scenario_names WHERE scenario_name = ?"
        try:
            self.cursor.execute(query, (scenario_name,))
            result = self.cursor.fetchone()
            if result:
                return result[0]
            else:
                return None
        except sqlite3.Error as e:
            print("Error fetching scenario ID:", e)
            return None

    def get_well_pad_id(self, UWI, scenario_id):
        """
        Retrieve the well pad ID for a given UWI and scenario ID.

        :param UWI: The unique well identifier (UWI).
        :param scenario_id: The scenario ID associated with the well pad.
        :return: The well pad ID if found, otherwise None.
        """
        query = """
        SELECT id
        FROM well_pads
        WHERE UWI = ? AND scenario_id = ?
        """
        try:
            self.connect()
            self.cursor.execute(query, (UWI, scenario_id))
            result = self.cursor.fetchone()
            return result[0] if result else None
        except sqlite3.Error as e:
            print(f"Error retrieving well pad ID: {e}")
            return None
        finally:
            self.disconnect()


    # Method to get decline curve ID by name
    def get_decline_curve_id(self, curve_name):
        self.connect()
        print(curve_name)
        query = "SELECT id FROM saved_dca WHERE curve_name = ?"
        try:
            self.cursor.execute(query, (curve_name,))
            result = self.cursor.fetchone()
            if result:
                return result[0]
            else:
                return None
        except sqlite3.Error as e:
            print("Error Geting Curve Id:", e)
        finally:
            self.disconnect()



    def create_directional_surveys_table(self):
        self.connect()
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS directional_surveys (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            UWI TEXT NOT NULL,
            md REAL NOT NULL,  -- Measured Depth
            tvd REAL NOT NULL,  -- True Vertical Depth
            "X Offset" REAL NOT NULL,
            "Y Offset" REAL NOT NULL,
            "Cumulative Distance" REAL NOT NULL,
            FOREIGN KEY (UWI) REFERENCES UWIs(UWI)
        );
        """
        try:
            self.cursor.execute(create_table_sql)
            self.connection.commit()
            print("directional_surveys table created successfully.")
        except sqlite3.Error as e:
            print("Error creating directional_surveys table:", e)
        finally:
            self.disconnect()

    def insert_directional_survey(self, UWI, x_offset, y_offset, md_depth, tvd_depth, inclination):
        self.connect()
        insert_sql = """
        INSERT INTO directional_surveys (UWI, x_offset, y_offset, md_depth, tvd_depth, inclination)
        VALUES (?, ?, ?, ?, ?, ?)
        """
        try:
            self.cursor.execute(insert_sql, (UWI, x_offset, y_offset, md_depth, tvd_depth, inclination))
            self.connection.commit()
            print("Directional survey inserted successfully.")
        except sqlite3.Error as e:
            print("Error inserting directional survey:", e)
        finally:
            self.disconnect()

    def get_directional_surveys(self):
        self.connect()
        query_sql = "SELECT * FROM directional_surveys"
        try:
            self.cursor.execute(query_sql)
            rows = self.cursor.fetchall()
        
            # Print rows for debugging purposes
            for row in rows:
                print(row)
        
            # Return the rows to be used later
            return rows
        except sqlite3.Error as e:
            print("Error querying directional surveys:", e)
            return None  # Return None if there's an error
        finally:
            self.disconnect()



    def get_directional_surveys_dataframe(self):
        """
        Fetches directional survey data from the database and returns it as a pandas DataFrame.

        Returns:
            pd.DataFrame: DataFrame containing the directional survey data.
        """
        self.connect()
        query_sql = "SELECT * FROM directional_surveys"  # Modify table name if needed

        try:
            self.cursor.execute(query_sql)
            rows = self.cursor.fetchall()  # Fetch all rows

            # Get column names from cursor.description
            column_names = [desc[0] for desc in self.cursor.description]

            # Convert to DataFrame
            df = pd.DataFrame(rows, columns=column_names)

            # Debugging: Print first few rows to verify correctness
            print(f"🔹 Retrieved {len(df)} rows from directional_surveys")
            print(df.head())

            return df  # Return the DataFrame directly

        except sqlite3.Error as e:
            print("Error querying directional surveys:", e)
            return pd.DataFrame()  # Return an empty DataFrame on error

        finally:
            self.disconnect()





    def update_parent_well_counts(self, UWI_counts, scenario_id):
        """
        Update parent_wells in model_properties for matching UWI and scenario_id
        Takes a list of counts
        """
        try:
            self.connect()
        
            # Direct update for each count in the list
            for entry in UWI_counts:  # Now iterating over list
                UWI = entry[0]  # First item is UWI
                count = entry[1]  # Second item is count
                self.cursor.execute("""
                    UPDATE model_properties 
                    SET parent_wells = ?
                    WHERE UWI = ? AND scenario_id = ?
                """, (count, UWI, scenario_id))
            
            self.connection.commit()
        
        except Exception as e:
            print(f"Error updating parent wells: {e}")
            raise
        finally:
            self.disconnect()

    def insert_survey_dataframe_into_db(self, df):
        self.connect()
        try:
            df.to_sql('directional_surveys', self.connection, if_exists='append', index=False)
            print("DataFrame inserted successfully.")
        except sqlite3.Error as e:
            print("Error inserting DataFrame into the database:", e)
        finally:
            self.disconnect()


    def get_well_attributes(self, wells, attributes):
        """
        Retrieve specified attributes for given wells from multiple tables

        Parameters:
        -----------
        wells : list
            List of UWIs to retrieve data for
        attributes : list
            List of attributes in format 'table_name.column_name'

        Returns:
        --------
        pd.DataFrame with wells as index and attributes as columns
        """
        try:
            self.connect()
    
            # Prepare a DataFrame to store results
            result_df = pd.DataFrame(index=wells)
    
            for attr in attributes:
                # Split attribute into table and column name
                table, column = attr.split('.')
                print(table, column)
                try:
                    # Try uppercase UWI first
                    try:
                        query = f"""
                        SELECT UWI, "{column}" 
                        FROM "{table}" 
                        WHERE UWI IN ({','.join(['?']*len(wells))})
                        """
                        df_attr = pd.read_sql(query, self.connection, params=wells)
                        df_attr.set_index('UWI', inplace=True)
                
                    except:
                        # If that fails, try lowercase UWI
                        query = f"""
                        SELECT UWI, "{column}" 
                        FROM "{table}" 
                        WHERE UWI IN ({','.join(['?']*len(wells))})
                        """
                        df_attr = pd.read_sql(query, self.connection, params=wells)
                        df_attr.set_index('UWI', inplace=True)
            
                    # Add to result DataFrame
                    result_df[attr] = df_attr[column]
        
                except Exception as e:
                    print(f"Error fetching attribute {attr}: {e}")
                    continue
    
            return result_df

        except Exception as e:
            print(f"Error retrieving well attributes: {e}")
            return pd.DataFrame()
        finally:
            self.disconnect()


    def _is_numeric_column(self, data, col_idx):
        """
        Strictly check if a column contains only numeric values.
        Returns True only if ALL non-NULL values are numeric.
        """
        try:
            self.connect()
            for row in data:
                if row[col_idx] is not None and row[col_idx] != '':
                    # Try converting to float to check if numeric
                    try:
                        float(row[col_idx])
                    except (ValueError, TypeError):
                        return False
            return True
        except Exception:
            return False

    def get_numeric_attributes(self):
        try:
            self.connect()
            numeric_columns = set()
            well_zones = self.fetch_zone_names_by_type("Well")
            print("Well zones:", well_zones)
            for zone_tuple in well_zones:
                zone_name = zone_tuple[0]
                try:
                    zone_table_name = self.get_table_name_from_zone(zone_name)
                    print(zone_table_name)
                    data, columns = self.fetch_zone_table_data(zone_table_name)
                
                    for col in columns[1:]:  # Skip UWI column
                        col_idx = columns.index(col)
                    
                        if self._is_numeric_column(data, col_idx):
                            sample_values = [row[col_idx] for row in data 
                                           if row[col_idx] is not None and row[col_idx] != '']
                        
                            if sample_values:
                                try:
                                    all_numeric = all(isinstance(float(val), float) 
                                                   for val in sample_values)
                                    if all_numeric:
                                        numeric_columns.add(f"{zone_table_name}.{col}")
                                except (ValueError, TypeError):
                                    continue
                        
                except Exception as zone_error:
                    print(f"Skipping zone {zone_name}: {zone_error}")
                    continue
                
            return sorted(list(numeric_columns))
    
        except Exception as e:
            print(f"Error discovering numeric attributes: {e}")
            return []
    
        finally:
            self.disconnect()

    def create_zones_table(self):
        """Create the Zones tracking table if it doesn't exist."""
        self.connect()
        try:
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS Zones (
                    ZoneName TEXT PRIMARY KEY,
                    Type TEXT NOT NULL,
                    TableName TEXT NOT NULL,  -- Add this column
                    UNIQUE(TableName)  -- Ensure table names are unique
                )
            """)
            self.connection.commit()
        except sqlite3.Error as e:
            print(f"Error creating Zones table: {e}")
            raise
        finally:
            self.disconnect()

    def get_sqlite_type(self, pandas_dtype):
        """Convert pandas dtype to SQLite column type."""
        if pd.api.types.is_integer_dtype(pandas_dtype):
            return "INTEGER"
        elif pd.api.types.is_float_dtype(pandas_dtype):
            return "REAL"
        elif pd.api.types.is_bool_dtype(pandas_dtype):
            return "INTEGER"  # SQLite doesn't have boolean, use INTEGER
        else:
            return "TEXT"  # Default to TEXT for other types

    def sanitize_name(self, name):
        """
        Sanitize names for database use (tables, columns, etc.)
        """
        replacements = {
            '³': '3', '²': '2', '.': '_', '/': '_', '[': '', ']': '',
            '(': '', ')': '', ' ': '_', '-': '_', '#': '_', '$': '_',
            '%': '_', '^': '_', '&': '_', '!': '_', '@': '_'
        }
        # Apply replacements
        for old, new in replacements.items():
            name = name.replace(old, new)
    
        # Replace remaining invalid characters
        name = re.sub(r'[^a-zA-Z0-9_]', '_', name)
    
        # Ensure name starts with a letter
        if not name[0].isalpha():
            name = f"t_{name}"
        
        return name



    def create_table_from_df(self, zone_name, df):
        """
        Creates a SQLite table from a pandas DataFrame for a specific zone.
    
        Parameters:
            zone_name (str): The zone name this table is for
            df (pd.DataFrame): The DataFrame to be converted into a table
        """
        self.connect()
        try:
            # Get the table name from Zones table
            self.cursor.execute("SELECT TableName FROM Zones WHERE ZoneName = ?", (zone_name,))
            result = self.cursor.fetchone()
            if not result:
                raise ValueError(f"No zone found with name {zone_name}")
        
            table_name = result[0]
        
            # Create column definitions
            columns = []
            for col in df.columns:
                sql_type = self.get_sqlite_type(df[col].dtype)
                safe_col_name = self.sanitize_name(col)
                columns.append(f"{safe_col_name} {sql_type}")
        
            # Create the table
            create_table_sql = f"""
            CREATE TABLE IF NOT EXISTS {table_name} (
                {', '.join(columns)}
            )
            """
            self.cursor.execute(create_table_sql)
        
            # Insert the data
            # Convert column names to their sanitized versions
            sanitized_columns = [self.sanitize_name(col) for col in df.columns]
        
            # Create the INSERT statement
            placeholders = ', '.join(['?' for _ in sanitized_columns])
            column_names = ', '.join(sanitized_columns)
            insert_sql = f"INSERT INTO {table_name} ({column_names}) VALUES ({placeholders})"
        
            # Convert DataFrame to list of tuples for insertion
            # Replace NaN with None for SQLite compatibility
            data = df.replace({np.nan: None}).values.tolist()
        
            # Execute the insert
            self.cursor.executemany(insert_sql, data)
            self.connection.commit()
        
            return True
        
        except Exception as e:
            self.connection.rollback()
            print(f"Error creating table for zone '{zone_name}': {e}")
            raise
        finally:
            self.disconnect()


    def add_zone_names(self, zone_name, zone_type):
        """
        Add a zone entry with a specific type to the database.
        """
        if not zone_name or not zone_name.strip():
            raise ValueError("Zone name cannot be empty")
        
        zone_name = zone_name.strip()
        valid_types = {'Zone', 'Intersections', 'Well'}
        if zone_type not in valid_types:
            raise ValueError(f"Invalid zone type '{zone_type}'. Must be one of {valid_types}.")
    
        # Sanitize the table name
        table_name = self.sanitize_name(zone_name)
    
        self.connect()
        try:

        
            # Check if the zone name already exists
            self.cursor.execute("SELECT COUNT(*) FROM Zones WHERE ZoneName = ? OR TableName = ?", 
                              (zone_name, table_name))
            if self.cursor.fetchone()[0] > 0:
                print(f"Zone '{zone_name}' or table '{table_name}' already exists.")
                return False

            # Insert the zone name with the given type and sanitized table name
            self.cursor.execute("""
                INSERT INTO Zones (ZoneName, Type, TableName)
                VALUES (?, ?, ?)
            """, (zone_name, zone_type, table_name))
    
            self.connection.commit()
            return True
        
        except Exception as e:
            self.connection.rollback()
            print(f"Error adding zone '{zone_name}': {e}")
            raise
        finally:
            self.disconnect()

    def fetch_zone_names_by_type(self, zone_type=None):
        print(zone_type)
        """
        Fetch zone names from the Zones table, optionally filtered by type.

        Parameters:
            zone_type (str, optional): The type of zones to fetch. 
                                       If None, fetch all zone names.

        Returns:
            list: A list of zone names, optionally filtered by type.
        """
        self.connect()
        try:
            if zone_type and zone_type != "All":
                query = "SELECT ZoneName FROM Zones WHERE Type = ? ORDER BY ZoneName"
                self.cursor.execute(query, (zone_type,))
            else:
                query = "SELECT ZoneName FROM Zones ORDER BY ZoneName"
                self.cursor.execute(query)
        
            return self.cursor.fetchall()
        except sqlite3.Error as e:
            print(f"Error fetching zone names: {e}")
            raise
        finally:
            self.disconnect()

    def fetch_zone_table_data(self, zone_name):
        """
        Fetch entire table data for a specific zone name.
        """
        self.connect()
        try:
            # Get all tables
            self.cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [table[0] for table in self.cursor.fetchall()]
        
            # First try exact match
            exact_matches = [table for table in tables if table.lower() == zone_name.lower()]
            if exact_matches:
                table_name = exact_matches[0]
            else:
                # If no exact match, then look for prefix match
                prefix_matches = [table for table in tables if table.lower().startswith(zone_name.lower() + "_")]
                if prefix_matches:
                    table_name = prefix_matches[0]
                else:
                    raise ValueError(f"No matching table found for zone name: {zone_name}")
        
            print(f"Selected table for zone {zone_name}: {table_name}")  # Debug print
        
            # Fetch data from the table
            query = f"SELECT * FROM {table_name}"
            self.cursor.execute(query)
        
            data = self.cursor.fetchall()
            columns = [description[0] for description in self.cursor.description]
        
            return data, columns
        
        except sqlite3.Error as e:
            print(f"Error fetching zone table data: {e}")
            raise
        except ValueError as e:
            print(str(e))
            raise
        finally:
            self.disconnect()

    def append_zone_data(self, zone_name, new_data):
        """
        Appends new UWI data to an existing zone table while preserving existing records.
    
        Args:
            zone_name (str): Name of the zone table
            new_data (pd.DataFrame): DataFrame containing new UWI records to be added
        
        Returns:
            bool: True if successful, False otherwise
        """
        print(f"\n🔹 Appending new UWIs to table: {zone_name}")
        print(f"Number of new records to append: {len(new_data)}")
        print(f"Column types of new data: {new_data.dtypes}")
    
        self.connect()
        if not self.connection:
            return False
        
        try:
            # Ensure the table exists by creating it if necessary
            dtype_mapping = {
                'UWI': 'TEXT',
                'Zone_Name': 'TEXT',
                'Top_Depth': 'REAL',
                'Base_Depth': 'REAL',
                'Top_X_Offset': 'REAL',
                'Top_Y_Offset': 'REAL',
                'Base_X_Offset': 'REAL',
                'Base_Y_Offset': 'REAL',
                'Angle_Top': 'REAL',
                'Angle_Base': 'REAL'
            }
        
            # Clean column names to match database convention
            new_data.columns = [col.replace(' ', '_') for col in new_data.columns]
        
            # If table doesn't exist, create it with the new data
            cursor = self.connection.cursor()
            cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{zone_name}'")
            table_exists = cursor.fetchone() is not None
        
            if not table_exists:
                new_data.to_sql(
                    zone_name,
                    self.connection,
                    if_exists='replace',
                    index=False,
                    dtype=dtype_mapping
                )
            else:
                # Append only new records
                new_data.to_sql(
                    zone_name,
                    self.connection,
                    if_exists='append',
                    index=False,
                    dtype=dtype_mapping
                )
        
            # Verify the append operation
            cursor.execute(f"SELECT COUNT(*) FROM {zone_name}")
            total_records = cursor.fetchone()[0]
            print(f"\n✅ Successfully appended new records!")
            print(f"Total records in table: {total_records}")
        
            # Verify column types
            cursor.execute(f"PRAGMA table_info({zone_name})")
            table_info = cursor.fetchall()
            print("\nColumn types in database:")
            for col in table_info:
                print(f"{col[1]}: {col[2]}")
            
            return True
        
        except Exception as e:
            print(f"❌ Error appending to table: {e}")
            self.connection.rollback()
            return False
        
        finally:
            self.disconnect()
    def zone_exists(self, zone_name, zone_type):
        """Check if a zone with the given name and type already exists."""
        self.connect()
        try:
            self.cursor.execute("SELECT COUNT(*) FROM Zones WHERE ZoneName = ? AND Type = ?", (zone_name, zone_type))
            return self.cursor.fetchone()[0] > 0
        finally:
            self.disconnect()

    def update_zone_column_data(self, table_name, column_name, data):
        """
        Adds a new column to the specified table if it does not exist and updates values for all rows.
        Args:
            table_name (str): The name of the table (zone name).
            column_name (str): The column to add/update.
            data (pd.DataFrame): DataFrame containing all rows with the new column values.
        Returns:
            bool: True if successful, False otherwise.
        """
        self.connect()
        if not self.connection:
            return False
        try:
            cursor = self.connection.cursor()
            # Step 1: Ensure the column exists
            cursor.execute(f"PRAGMA table_info({table_name})")
            existing_columns = [row[1] for row in cursor.fetchall()]
            if column_name not in existing_columns:
                alter_query = f"ALTER TABLE {table_name} ADD COLUMN {column_name} REAL DEFAULT 0;"
                cursor.execute(alter_query)
                self.connection.commit()
                print(f"✅ Column '{column_name}' added to table '{table_name}'.")
        
            # Step 2: Update all rows
            update_query = f"UPDATE {table_name} SET {column_name} = ? WHERE UWI = ? AND Top_Depth = ? AND Base_Depth = ?"
            update_data = [(row[column_name], row['UWI'], row['Top_Depth'], row['Base_Depth']) for _, row in data.iterrows()]
            cursor.executemany(update_query, update_data)
        
            self.connection.commit()
            print(f"✅ Successfully updated column '{column_name}' in table '{table_name}'.")
            return True
        except Exception as e:
            print(f"❌ Error updating column '{column_name}' in table '{table_name}': {e}")
            self.connection.rollback()
            return False
        finally:
            self.disconnect()






    def save_merged_zone(self, merged_data: pd.DataFrame, new_zone_name: str) -> bool:
        """
        Save the merged zone data to a new table named after the new zone
        
        Parameters:
            merged_data (pd.DataFrame): The merged zone data
            new_zone_name (str): Name for the new merged zone (will be table name)
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            self.db_manager.connect()
            
            # Create new table query
            columns = merged_data.columns
            create_query = f"""
                CREATE TABLE IF NOT EXISTS {new_zone_name} (
                    {', '.join(f"{col} {'TEXT' if col == 'UWI' else 'REAL'}" 
                              for col in columns)}
                )
            """
            self.db_manager.cursor.execute(create_query)
            
            # Insert data query
            placeholders = ','.join(['?' for _ in columns])
            insert_query = f"""
                INSERT INTO {new_zone_name} 
                ({','.join(columns)})
                VALUES ({placeholders})
            """
            
            # Convert DataFrame to list of tuples and insert
            records = merged_data.to_records(index=False)
            self.db_manager.cursor.executemany(insert_query, records)
            
            # Add the new zone to the Zones table if it exists
            try:
                self.db_manager.cursor.execute(
                    "INSERT INTO Zones (ZoneName, Type) VALUES (?, 'Zone')",
                    (new_zone_name,)
                )
            except sqlite3.Error:
                # Zones table might not exist, skip this step
                pass
                
            self.db_manager.commit()
            return True
            
        except Exception as e:
            print(f"Error saving merged zone: {e}")
            self.db_manager.rollback()
            return False
        finally:
            self.db_manager.disconnect()


    def fetch_correlation_data(self, table_name, column_name, UWIs):
        """
        Fetch specific column data for selected UWIs.
        Parameters:
        -----------
        table_name : str
            The name of the zone/table
        column_name : str
            The specific column to fetch
        UWIs : list
            List of UWIs to fetch data for
        Returns:
        --------
        pd.Series: Series containing the values for the specified column
        """
        self.connect()
        try:
            # First, find the actual table name using same logic as fetch_zone_table_data
            self.cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [table[0] for table in self.cursor.fetchall()]
        
            matching_tables = [
                table for table in tables 
                if table_name.lower() in table.lower() or 
                   table.lower().startswith(table_name.lower())
            ]
            if not matching_tables:
                raise ValueError(f"No table found for: {table_name}")
        
            actual_table = matching_tables[0]
        
            # Create placeholders for SQL IN clause
            placeholders = ','.join('?' * len(UWIs))
        
            # Fetch just the specific column for the selected UWIs
            query = f"SELECT UWI, {column_name} FROM {actual_table} WHERE UWI IN ({placeholders})"
            self.cursor.execute(query, UWIs)
        
            # Convert to DataFrame
            results = self.cursor.fetchall()
            return pd.DataFrame(results, columns=['UWI', column_name])
        
        except sqlite3.Error as e:
            print(f"Error fetching correlation data: {e}")
            raise
        finally:
            self.disconnect()



    def fetch_zone_depth_data(self, zone_name):
        self.connect()
        if not self.connection:
            print("Connection failed.")
            return pd.DataFrame()
        try:
            sanitized_zone_name = zone_name.replace(" ", "_")
            query = f"SELECT * FROM {sanitized_zone_name}"
            df = pd.read_sql_query(query, self.connection)
        
            if 'UWI' in df.columns:
                df['UWI'] = df['UWI'].astype(str)
                print("UWI dtype after fetching:", df['UWI'].dtype)
                print("Sample UWIs:", df['UWI'].head().tolist())
        
            df.columns = [col.strip() for col in df.columns]
            column_mapping = {
                'TOP_DEPTH': 'Top_Depth',
                'BASE_DEPTH': 'Base_Depth',
                'Top Depth': 'Top_Depth',
                'Base Depth': 'Base_Depth'
            }
            df.rename(columns=column_mapping, inplace=True)
            df.replace(["", "NULL", "null", "N/A", "n/a", "NaN", "nan"], np.nan, inplace=True)
        
            non_numeric_cols = ["well_depth_units", "UWI"]
            numeric_cols = [col for col in df.columns if col not in non_numeric_cols and col != 'UWI']
        
            def clean_numeric(value):
                if isinstance(value, str):
                    cleaned = re.sub(r"[^\d.-]", "", value)
                    return cleaned if cleaned else np.nan
                return value
        
            for col in numeric_cols:
                df[col] = df[col].astype(str).str.strip()
                df[col] = df[col].apply(clean_numeric)
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
            print("DEBUG: Rows with NaN after conversion:")
            print(df[df.isna().any(axis=1)])
        
            if "UWI" in df.columns and "Top_Depth" in df.columns:
                df.sort_values(['UWI', 'Top_Depth'], inplace=True)
        
            return df
        except Exception as e:
            print(f"Error fetching zone data for table {zone_name}: {e}")
            return pd.DataFrame()
        finally:
            self.disconnect()




    def update_zone_data(self, zone_name, updated_data):
        """Overwrites the entire zone table with new data instead of updating row-by-row."""
        print(f"\n🔹 Overwriting Table: {zone_name}")
        print(f"Column types before save: {updated_data.dtypes}")  # Log types before save
        updated_data['UWI'] = updated_data['UWI'].astype(str)
        self.connect()
        if not self.connection:
            return False
    
        try:
            # Drop the existing table if it exists
            cursor = self.connection.cursor()
            cursor.execute(f"DROP TABLE IF EXISTS {zone_name}")
            self.connection.commit()
        
            # Define SQLite data types explicitly for critical columns
            dtype_mapping = {
                'UWI': 'TEXT',  # Store UWI as TEXT since it's a string
                'Top_Depth': 'REAL',
                'Base_Depth': 'REAL'
                # Add any other columns that need specific types
            }
        
            # Save the updated DataFrame back to the database with explicit dtypes
            updated_data.to_sql(
                zone_name, 
                self.connection, 
                if_exists="replace", 
                index=False,
                dtype=dtype_mapping
            )
        
            # Verify the types after save
            cursor = self.connection.cursor()
            cursor.execute(f"PRAGMA table_info({zone_name})")
            table_info = cursor.fetchall()
            print("\n✅ Table successfully overwritten!")
            print("Column types in database:")
            for col in table_info:
                print(f"{col[1]}: {col[2]}")  # col[1] is name, col[2] is type
            
            return True
        
        except Exception as e:
            print(f"❌ Error overwriting table: {e}")
            self.connection.rollback()
            return False
        finally:
            self.disconnect()

    def fetch_zone_data(self, zone_name):
        self.connect()
        try:
            query = f"""
            SELECT UWI, Top_X_Offset, Top_Y_Offset, Base_X_Offset, Base_Y_Offset, 
                   Top_Depth, Base_Depth, Angle_Top, Angle_Base 
            FROM {zone_name}
            """
            df = pd.read_sql(query, self.connection)
        
            # Ensure UWI is treated as a string
            df['UWI'] = df['UWI'].astype(str)
        
            print("UWI dtype after fetching:", df['UWI'].dtype)
            print("Sample UWIs:", df['UWI'].head().tolist())
        
            return df
        finally:
            self.disconnect()

    def plot_zones(self, zone_name):
       query = f"""
       SELECT UWI, Top_X_Offset, Top_Y_Offset, Base_X_Offset, Base_Y_Offset, 
              Top_Depth, Base_Depth, Angle_Top, Angle_Base 
       FROM {zone_name}
       """
       zone_data_df = pd.read_sql(query, self.db_manager.connection)
       return zone_data_df

    def update_zone_angles(self, zone_name, UWI, angle_top, angle_base):
       """Update angles for a specific UWI in a zone table."""
       self.connect()
       try:
           query = f"""
           UPDATE {zone_name} 
           SET Angle_Top = ?, Angle_Base = ?
           WHERE UWI = ?
           """
           self.cursor.execute(query, (angle_top, angle_base, UWI))
           self.connection.commit()
       finally:
           self.disconnect()

    def fetch_table_data(self, table_name):
        """Fetch all data from a table."""
        self.connect()
        try:
            return pd.read_sql(f"SELECT * FROM {table_name}", self.connection)
        finally:
            self.disconnect()

    def get_table_name_from_zone(self, zone_name):
        """
        Get the associated table name for a given zone name.
    
        Parameters:
            zone_name (str): The name of the zone
        
        Returns:
            str: The associated table name, or None if not found
        """
        self.connect()
        try:
            self.cursor.execute("SELECT TableName FROM Zones WHERE ZoneName = ?", (zone_name,))
            result = self.cursor.fetchone()
            return result[0] if result else None
        except Exception as e:
            print(f"Error getting table name for zone '{zone_name}': {e}")
            return None


    def fetch_table_columns(self, table_name):
        """
        Fetch all column names from a given SQLite table.

        Parameters:
            table_name (str): The name of the table.

        Returns:
            list: A list of column names in the table.
        """
        self.connect()  # Establish connection
        try:
            # Ensure the table name is valid
            if not table_name.isidentifier():
                raise ValueError("Invalid table name")

            # Query SQLite PRAGMA to get column names
            query = f"PRAGMA table_info(`{table_name}`)"
            self.cursor.execute(query)
            columns_info = self.cursor.fetchall()

            # Extract column names from the query result
            column_names = [col_info[1] for col_info in columns_info]  # `col_info[1]` is the column name
            return column_names

        except Exception as e:
            print(f"Error fetching columns for table '{table_name}': {e}")
            raise

        finally:
            self.disconnect()  # Close connection


    def fetch_zone_attribute(self, zone_name, attribute_name):
        """
        Fetches a specific attribute column for the given zone name from the database.

        Parameters:
            zone_name (str): The name of the zone (table name).
            attribute_name (str): The name of the column (attribute) to fetch.

        Returns:
            pd.DataFrame: A DataFrame containing the requested column and related UWI and depth information.
        """
        self.connect()  # Establish connection
        try:
            query = f"""
                SELECT `UWI`, `Top_Depth`, `Base_Depth`, `Top_X_Offset`, `Top_Y_Offset`, 
                       `Base_X_Offset`, `Base_Y_Offset`, `{attribute_name}`
                FROM `{zone_name}`
            """
            return pd.read_sql(query, self.connection)

        except Exception as e:
            raise ValueError(f"Failed to fetch attribute '{attribute_name}' for zone '{zone_name}': {e}")

        finally:
            self.disconnect()  # Close connection

    def fetch_entire_database(self):
        """
        Fetches all data from all tables in the database and loads it into memory.

        Returns:
            dict: A dictionary where keys are table names and values are DataFrames containing the table data.
        """
        self.connect()
        try:
            # Fetch all table names from the database
            query = "SELECT name FROM sqlite_master WHERE type='table';"
            self.cursor.execute(query)
            table_names = [row[0] for row in self.cursor.fetchall()]

            # Dictionary to store data from all tables
            db_data = {}

            # Load data from each table into a DataFrame
            for table_name in table_names:
                print(f"Loading data from table: {table_name}")  # Debug log
                table_query = f"SELECT * FROM `{table_name}`"
                db_data[table_name] = pd.read_sql(table_query, self.connection)

            return db_data

        except Exception as e:
            print(f"Error loading database: {e}")
            raise

        finally:
            self.disconnect()

    def create_regression_values_table(self):
        """Creates template for tables storing regression values"""
        self.connect()
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS r_values_template (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            UWI TEXT NOT NULL,
            attribute_name TEXT NOT NULL,
            attribute_value REAL,
            source_table TEXT,
            source_column TEXT,
            FOREIGN KEY (UWI) REFERENCES UWIs(UWI),
            UNIQUE(UWI, attribute_name)
        )
        """
        try:
            self.cursor.execute(create_table_sql)
            self.connection.commit()
            print("Regression values template created successfully.")
        except sqlite3.Error as e:
            print("Error creating regression values template:", e)
        finally:
            self.disconnect()

    def create_regression_attributes_table(self):
        """Creates template for tables storing which attributes are used in each regression"""
        self.connect()
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS r_attributes_template (
            attribute_name TEXT PRIMARY KEY,
            is_target BOOLEAN DEFAULT FALSE,
            notes TEXT
        )
        """
        try:
            self.cursor.execute(create_table_sql)
            self.connection.commit()
            print("Regression attributes template created successfully.")
        except sqlite3.Error as e:
            print("Error creating regression attributes template:", e)
        finally:
            self.disconnect()

    def create_regression_table(self):
        """Creates the main catalog tracking regression analyses and their associated table names"""
        self.connect()
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS r_catalog (
            regression_id INTEGER PRIMARY KEY AUTOINCREMENT,
            regression_name TEXT UNIQUE NOT NULL,
            values_table_name TEXT UNIQUE NOT NULL,
            attributes_table_name TEXT UNIQUE NOT NULL,
            description TEXT,
            date_created TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
        try:
            self.cursor.execute(create_table_sql)
            self.connection.commit()
            print("Regression catalog created successfully.")
        except sqlite3.Error as e:
            print("Error creating regression catalog:", e)
        finally:
            self.disconnect()

    def add_regression_table(self, table_name, description, within_transaction=False):
        """Add a regression entry to the r_catalog table
        Args:
            table_name: Base name for the regression (without r_ prefix)
            description: Optional description
            within_transaction: If True, doesn't commit (for use in larger transactions)
        """
        if not within_transaction:
            self.connect()
        try:
            # Clean table name - replace spaces with underscores
            safe_table_name = table_name.replace(" ", "_")
            values_table = f"r_{safe_table_name}_values"
            attrs_table = f"r_{safe_table_name}_attributes"
        
            insert_sql = """
            INSERT INTO r_catalog (
                regression_name,
                values_table_name,
                attributes_table_name,
                description
            ) VALUES (?, ?, ?, ?)
            """
    
            self.cursor.execute(insert_sql, (
                table_name,  # Keep original name with spaces for display
                values_table,
                attrs_table,
                description
            ))
    
            if not within_transaction:
                self.connection.commit()
                print(f"Added regression '{table_name}' to catalog with tables: {values_table}, {attrs_table}")
            
        except sqlite3.Error as e:
            if not within_transaction:
                self.connection.rollback()
            print(f"Error adding regression '{table_name}' to catalog: {e}")
            raise e
        finally:
            if not within_transaction:
                self.disconnect()


    def delete_regression_table(self, table_name, within_transaction=False):
        """Delete a regression's tables and its catalog entry"""
        if not within_transaction:
            self.connect()
        try:
            # Get the values and attributes table names from catalog
            self.cursor.execute("""
                SELECT values_table_name, attributes_table_name 
                FROM r_catalog 
                WHERE regression_name = ?
            """, (table_name,))
        
            result = self.cursor.fetchone()
            if result:
                values_table, attrs_table = result
            
                # Drop both tables if they exist
                self.cursor.execute(f'DROP TABLE IF EXISTS "{values_table}"')
                self.cursor.execute(f'DROP TABLE IF EXISTS "{attrs_table}"')
            
                # Delete from the catalog
                self.cursor.execute("""
                    DELETE FROM r_catalog
                    WHERE regression_name = ?
                """, (table_name,))
        
            if not within_transaction:
                self.connection.commit()
                print(f"Regression '{table_name}' and associated tables deleted successfully.")
            
        except sqlite3.Error as e:
            if not within_transaction:
                self.connection.rollback()
            print(f"Error deleting regression '{table_name}': {e}")
            raise e
        finally:
            if not within_transaction:
                self.disconnect()


    def save_correlation_to_regression(self, table_name, data_matrix, description=None, replace_mode=True):
        """
        Save selected attribute data to regression tables
        Args:
            table_name: Base name for the regression (without r_ prefix)
            data_matrix: Pandas DataFrame containing the raw data (indexed by UWI)
            description: Optional description for the table 
            replace_mode: If True, replaces existing data, if False, adds to it
        """
        # Clean table names - replace spaces with underscores for SQL safety
        safe_table_name = table_name.replace(" ", "_")
        values_table = f"r_{safe_table_name}_values"
        attrs_table = f"r_{safe_table_name}_attributes"

        self.connect()
        try:
            # Start transaction
            self.connection.execute("BEGIN")

            if replace_mode:
                # Delete existing tables if they exist
                self.cursor.execute(f'DROP TABLE IF EXISTS "{values_table}"')
                self.cursor.execute(f'DROP TABLE IF EXISTS "{attrs_table}"')

                # Add to regression catalog
                self.add_regression_table(table_name, description, within_transaction=True)

                # Create the new values table
                create_values_sql = f"""
                CREATE TABLE "{values_table}" (
                    id INTEGER PRIMARY KEY,
                    attribute_name TEXT,
                    attribute_value REAL,
                    UWI TEXT,
                    source_table TEXT,
                    source_column TEXT,
                    FOREIGN KEY (UWI) REFERENCES UWIs(UWI)
                )
                """
                self.cursor.execute(create_values_sql)

                # Create the new attributes table
                create_attrs_sql = f"""
                CREATE TABLE "{attrs_table}" (
                    attribute_name TEXT PRIMARY KEY,
                    weight REAL DEFAULT 1.0,
                    is_target BOOLEAN DEFAULT FALSE,
                    notes TEXT
                )
                """
                self.cursor.execute(create_attrs_sql)

            else:
                # If tables don't exist, create them
                create_values_sql = f"""
                CREATE TABLE IF NOT EXISTS "{values_table}" (
                    id INTEGER PRIMARY KEY,
                    attribute_name TEXT,
                    attribute_value REAL,
                    UWI TEXT,
                    source_table TEXT,
                    source_column TEXT,
                    FOREIGN KEY (UWI) REFERENCES UWIs(UWI)
                )
                """
                self.cursor.execute(create_values_sql)

                create_attrs_sql = f"""
                CREATE TABLE IF NOT EXISTS "{attrs_table}" (
                    attribute_name TEXT PRIMARY KEY,
                    weight REAL DEFAULT 1.0,
                    is_target BOOLEAN DEFAULT FALSE,
                    notes TEXT
                )
                """
                self.cursor.execute(create_attrs_sql)

                # Update catalog if needed
                if not self.get_regression_table_by_name(table_name, within_transaction=True):
                    self.add_regression_table(table_name, description, within_transaction=True)

            # Insert data into values table
            insert_values_sql = f"""
            INSERT INTO "{values_table}" 
            (attribute_name, attribute_value, UWI, source_table, source_column)
            VALUES (?, ?, ?, ?, ?)
            """

            # Insert into attributes table
            insert_attrs_sql = f"""
            INSERT OR REPLACE INTO "{attrs_table}" 
            (attribute_name, weight, is_target, notes)
            VALUES (?, 1.0, FALSE, NULL)
            """

            # Ensure UWI is a column in the DataFrame
            if data_matrix.index.name == 'UWI':
                data_matrix = data_matrix.reset_index()

            print("Filtered Data Columns:", data_matrix.columns.tolist())  # Debugging output

            # Iterate through columns
            for col in data_matrix.columns:
                if col == 'UWI':  # Skip UWI column
                    continue

                # Debugging print
                print(f"Processing column: {col}")  # Helps detect unexpected column names

                # Handle case where column name doesn't contain '.'
                if '.' in col:
                    source_table, source_column = col.split('.', 1)
                else:
                    source_table = "Unknown"  # Assign a default value if the column has no dot
                    source_column = col

                if not replace_mode:
                    # Delete existing entries for this attribute if in add mode
                    self.cursor.execute(f"""
                        DELETE FROM "{values_table}"
                        WHERE attribute_name = ?
                    """, (str(col),))

                # Add to attributes table
                self.cursor.execute(insert_attrs_sql, (str(col),))

                # Add values
                for index, row in data_matrix.iterrows():
                    value = row[col]
                    UWI = row['UWI']

                    # Only insert if value is not null/NaN
                    if isinstance(value, (int, float)) and not pd.isna(value):
                        self.cursor.execute(insert_values_sql, 
                            (str(col), float(value), str(UWI), str(source_table), str(source_column)))

            self.connection.commit()
            print(f"Data saved to regression tables: {values_table} and {attrs_table}")

        except sqlite3.Error as e:
            self.connection.rollback()
            print(f"Error saving to regression tables: {e}")
            raise e
        finally:
            self.disconnect()

    def get_regression_tables(self):
        """Get list of all regression entries with their associated table names"""
        self.connect()
        try:
            self.cursor.execute("""
                SELECT 
                    regression_id,
                    regression_name,
                    values_table_name,
                    attributes_table_name,
                    description,
                    date_created
                FROM r_catalog
                ORDER BY regression_id
            """)
            tables = self.cursor.fetchall()
            return tables
        except sqlite3.Error as e:
            print(f"Error fetching regression tables: {e}")
            return []
        finally:
            self.disconnect()

    def get_regression_table_by_name(self, table_name, within_transaction=False):
        """Get specific regression table info"""
        if not within_transaction:
            self.connect()
        try:
            self.cursor.execute("""
                SELECT table_name, description 
                FROM regression_tables 
                WHERE table_name = ?
            """, (table_name,))
            return self.cursor.fetchone()
        except sqlite3.Error as e:
            print(f"Error fetching regression table info: {e}")
            return None
        finally:
            if not within_transaction:
                self.disconnect()

    def save_regression_feature_weights(self, regression_name, adjusted_weights, target_variable):
        """
        Save feature weights for a specific regression table
    
        Args:
            regression_name (str): Name of the regression table
            adjusted_weights (dict): Dictionary of feature names and their corresponding weights
            target_variable (str): Name of the target variable
        """
        # Construct the attributes table name
        safe_table_name = regression_name.replace(" ", "_")
        attrs_table = f"r_{safe_table_name}_attributes"

        self.connect()
        try:
            # Start transaction
            self.connection.execute("BEGIN")

            # First, set all is_target to 0
            reset_sql = f"""
            UPDATE "{attrs_table}"
            SET is_target = 0
            """
            self.cursor.execute(reset_sql)

            # Fetch the default weight for the target variable if not in adjusted_weights
            self.cursor.execute(f"""
                SELECT weight FROM "{attrs_table}" 
                WHERE attribute_name = ?
            """, (target_variable,))
            default_weight_result = self.cursor.fetchone()
            default_weight = default_weight_result[0] if default_weight_result else 1.0

            # Then set the specific target variable to 1
            target_update_sql = f"""
            UPDATE "{attrs_table}"
            SET is_target = 1, weight = ?
            WHERE attribute_name = ?
            """

            # Update weights for each feature
            update_sql = f"""
            UPDATE "{attrs_table}"
            SET weight = ?
            WHERE attribute_name = ?
            """

            # Set the target variable's weight and mark as target
            self.cursor.execute(target_update_sql, (
                adjusted_weights.get(target_variable, default_weight), 
                target_variable
            ))

            # Update weights for other features
            for feature, weight in adjusted_weights.items():
                if feature != target_variable:
                    self.cursor.execute(update_sql, (weight, feature))

            # Commit the transaction
            self.connection.commit()
            print(f"Weights updated for regression: {regression_name}")

        except sqlite3.Error as e:
            self.connection.rollback()
            print(f"Error saving regression feature weights: {e}")
            raise
        finally:
            self.disconnect()


    def fetch_correlation_data(self, UWIs, selected_attrs):
        """Fetch well attribute data for correlation analysis."""
        try:
            if not UWIs or not selected_attrs:
                raise ValueError("No UWIs or attributes selected.")

            attr_selects = []
            tables = set()

            # Extract table and column names
            for attr in selected_attrs:
                table_name, col_name = attr.split('.')
                tables.add(table_name)
                if col_name.upper() == 'UWI':
                    continue  # Skip UWI column
                attr_selects.append(f'"{table_name}"."{col_name}"')  # Double Quotes for SQL safety

            if not tables:
                raise ValueError("No valid tables found for the selected attributes.")

            base_table = list(tables)[0]
            joins = []

            # Create JOINs for multiple tables
            for table in tables:
                if table != base_table:
                    joins.append(f"""
                        LEFT JOIN {table} ON 
                        CASE 
                            WHEN EXISTS (SELECT 1 FROM pragma_table_info('{table}') WHERE name = 'UWI')
                            THEN {base_table}.UWI = {table}.UWI
                            ELSE {base_table}.UWI = {table}.UWI
                        END
                    """)

            # SQL IN clause placeholders
            UWI_placeholders = ', '.join(['?'] * len(UWIs))

            # Build final SQL query
            query = f"""
            SELECT 
                CASE 
                    WHEN EXISTS (SELECT 1 FROM pragma_table_info('{base_table}') WHERE name = 'UWI')
                    THEN {base_table}.UWI
                    ELSE {base_table}.UWI
                END as UWI,
                {', '.join(attr_selects)}
            FROM {base_table}
            {' '.join(joins)}
            WHERE {base_table}.UWI IN ({UWI_placeholders})
               OR {base_table}.UWI IN ({UWI_placeholders})
            """

            # Execute query
            self.connect()
            self.cursor.execute(query, UWIs + UWIs)
            results = self.cursor.fetchall()
            self.disconnect()

            return results

        except Exception as e:
            print(f"Database Query Error: {e}")
            return None





    def get_regression_data(self, regression_name, UWIs):
        """Get data from a regression's values table for specified UWIs"""
        self.connect()
        try:
            # Get table names using safe name conversion
            safe_table_name = regression_name.replace(" ", "_")
            values_table = f"r_{safe_table_name}_values"
        
            # Build query with proper UWI list
            UWI_placeholders = ','.join(['?' for _ in UWIs])
        
            query = f"""
            SELECT UWI, attribute_name, attribute_value
            FROM "{values_table}"
            WHERE UWI IN ({UWI_placeholders})
            """
        
            self.cursor.execute(query, UWIs)
            rows = self.cursor.fetchall()
        
            if not rows:
                return None
            
            # Convert to DataFrame
            df = pd.DataFrame(rows, columns=['UWI', 'attribute_name', 'attribute_value'])
        
            # Data is already in long format, which is what we want
            return df
        
        except sqlite3.Error as e:
            print(f"Error getting regression data: {e}")
            return None
        finally:
            self.disconnect()

    def get_regression_attributes(self, regression_name):
        """Get attributes for a regression from its attributes table"""
        self.connect()
        try:
            safe_table_name = regression_name.replace(" ", "_")
            attrs_table = f"r_{safe_table_name}_attributes"
        
            self.cursor.execute(f"""
                SELECT attribute_name, weight, is_target 
                FROM "{attrs_table}"
                ORDER BY attribute_name
            """)
        
            return self.cursor.fetchall()
        except sqlite3.Error as e:
            print(f"Error getting regression attributes: {e}")
            return []
        finally:
            self.disconnect()



    def get_regression_feature_weights(self, regression_name):
        """
        Fetch feature weights for a specific regression table
        """
        # Construct the attributes table name
        safe_table_name = regression_name.replace(" ", "_")
        attrs_table = f"r_{safe_table_name}_attributes"

        self.connect()
        try:
            # Query weights for non-target attributes
            self.cursor.execute(f"""
                SELECT attribute_name, weight 
                FROM "{attrs_table}"
                WHERE is_target = 0
                ORDER BY weight DESC
            """)
        
            # Fetch all results
            weights = dict(self.cursor.fetchall())
        
            print(f"Raw weights from database: {weights}")
        
            return weights
    
        except sqlite3.Error as e:
            print(f"Error fetching regression weights: {e}")
            return {}
        finally:
            # Always disconnect
            self.disconnect()




    def create_criteria_tables(self):
        """
        Creates necessary tables for storing highlight criteria.
        """
        self.connect()
        try:
            # Table for storing unique criteria names and their colors
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS criteria_names (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    color TEXT NOT NULL
                )
            """)

            # Table for storing individual conditions linked to criteria names
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS criteria_conditions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    criteria_id INTEGER NOT NULL,
                    column_name TEXT NOT NULL,
                    operator TEXT NOT NULL,
                    value TEXT NOT NULL,
                    logical_operator TEXT,
                    FOREIGN KEY (criteria_id) REFERENCES criteria_names(id) ON DELETE CASCADE
                )
            """)

            self.connection.commit()

        except sqlite3.Error as e:
            print(f"Error creating criteria tables: {e}")

        finally:
            self.disconnect()


    def save_criteria(self, criteria_name, highlight_color, criteria_list):
        """Save or update criteria name and conditions in the database."""
        self.connect()
        try:
            # Insert or update criteria name and color
            self.cursor.execute("""
                INSERT INTO criteria_names (name, color)
                VALUES (?, ?)
                ON CONFLICT(name) DO UPDATE SET color = excluded.color
            """, (criteria_name, highlight_color))

            # Get the criteria_id
            self.cursor.execute("SELECT id FROM criteria_names WHERE name = ?", (criteria_name,))
            criteria_id = self.cursor.fetchone()[0]

            # Delete old conditions for this criteria name
            self.cursor.execute("DELETE FROM criteria_conditions WHERE criteria_id = ?", (criteria_id,))

            # Insert new conditions
            for column, operator, value, logical_operator in criteria_list:
                self.cursor.execute("""
                    INSERT INTO criteria_conditions (criteria_id, column_name, operator, value, logical_operator)
                    VALUES (?, ?, ?, ?, ?)
                """, (criteria_id, column, operator, value, logical_operator))

            self.connection.commit()
            return True, "Criteria saved successfully."

        except sqlite3.Error as e:
            return False, str(e)

        finally:
            self.disconnect()

    def load_criteria_names(self):
        """Fetch all unique criteria names from the database."""
        self.connect()
        try:
            self.cursor.execute("SELECT DISTINCT name FROM criteria_names")
            return [row[0] for row in self.cursor.fetchall()]
        finally:
            self.disconnect()

    def load_criteria_by_name(self, criteria_name):
        """Load criteria conditions and highlight color for the given criteria name."""
        if not criteria_name:
            return None, []

        self.connect()
        try:
            # Step 1: Fetch criteria ID & highlight color from criteria_names
            query = "SELECT id, color FROM criteria_names WHERE name = ?"
            self.cursor.execute(query, (criteria_name,))
            result = self.cursor.fetchone()

            if not result:
                print(f"🔴 No criteria found for {criteria_name} in criteria_names")
                return None, []

            criteria_id, highlight_color = result
            print(f"✅ Found criteria: ID={criteria_id}, Color={highlight_color}")

            # Step 2: Fetch all conditions for this criteria_id
            query = "SELECT column_name, operator, value, logical_operator FROM criteria_conditions WHERE criteria_id = ?"
            self.cursor.execute(query, (criteria_id,))
            conditions = self.cursor.fetchall()

            if not conditions:
                print(f"⚠️ No conditions found for criteria ID {criteria_id}")
                return highlight_color, []

            print(f"✅ Loaded {len(conditions)} conditions for {criteria_name}")
            return highlight_color, conditions

        except Exception as e:
            print(f"❌ Error in load_criteria_by_name: {e}")
            return None, []

        finally:
            self.disconnect()



    def delete_criteria_condition(self, criteria_name, column, operator, value, logical_operator):
        """Delete a specific condition from the criteria."""
        self.connect()
        try:
            self.cursor.execute("""
                DELETE FROM criteria_conditions
                WHERE criteria_id = (SELECT id FROM criteria_names WHERE name = ?)
                AND column_name = ? AND operator = ? AND value = ? AND (logical_operator = ? OR logical_operator IS NULL)
            """, (criteria_name, column, operator, value, logical_operator))
            self.connection.commit()
        finally:
            self.disconnect()

    def update_criterion_value(self, criteria_name, column, old_value, new_value):
        """Update a specific criterion's value in the database."""
        self.connect()
        try:
            self.cursor.execute("""
                UPDATE criteria_conditions 
                SET value = ?
                WHERE criteria_id = (SELECT id FROM criteria_names WHERE name = ?)
                AND column_name = ? AND value = ?
            """, (new_value, criteria_name, column, old_value))
            self.connection.commit()
        finally:
            self.disconnect()

    def update_criteria_color(self, criteria_name, color):
        """Update the highlight color of a criteria."""
        self.connect()
        try:
            self.cursor.execute("UPDATE criteria_names SET color = ? WHERE name = ?", (color, criteria_name))
            self.connection.commit()
        finally:
            self.disconnect()

    def get_criteria_color_by_name(self, criteria_name):
        """Fetch the highlight color for a given criteria name."""
        if not criteria_name:
            return None

        self.connect()
        try:
            query = "SELECT color FROM criteria_names WHERE name = ?"
            self.cursor.execute(query, (criteria_name,))
            result = self.cursor.fetchone()

            if result:
                return result[0]  # Return the color
            else:
                print(f"⚠️ No color found for criteria: {criteria_name}")
                return None

        except Exception as e:
            print(f"❌ Error in get_criteria_color_by_name: {e}")
            return None

        finally:
            self.disconnect()

