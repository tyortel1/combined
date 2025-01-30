import sqlite3
import pandas as pd
import logging
import re

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



    def insert_uwi(self, uwi, status=None):
        self.connect()

        # Modify SQL query to include the status column
        insert_uwi_sql = "INSERT INTO uwis (uwi, status) VALUES (?, ?)"
        if status is None:
            status = 'Active'
        try:
            # Execute the query with both uwi and status
            self.cursor.execute(insert_uwi_sql, (uwi, status))
            self.connection.commit()
            print("uwi '{}' with status '{}' inserted successfully.".format(uwi, status))
        except sqlite3.Error as e:
            print("Error inserting uwi:", e)
        finally:
            self.disconnect()

    def create_uwi_table(self):
        self.connect()
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS uwis (
            uwi TEXT PRIMARY KEY,
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
            print("uwis table created successfully.")
        except sqlite3.Error as e:
            print("Error creating uwis table:", e)
        finally:
            self.disconnect()

    def save_uwi_data(self, total_lat_data):
        if not isinstance(total_lat_data, pd.DataFrame):
            print("Input data must be a pandas DataFrame.")
            return

        if total_lat_data.empty:
            print("The DataFrame is empty. Nothing to save.")
            return

        self.connect()

        try:
            expected_columns = [
                'uwi', 'status', 'surface_x', 'surface_y', 'lateral',
                'heel_x', 'heel_y', 'toe_x', 'toe_y', 'heel_md',
                'toe_md', 'average_tvd', 'total_length', 'spud_date'
            ]
            total_lat_data = total_lat_data[expected_columns]  # Enforce correct column order

            for _, row in total_lat_data.iterrows():
                uwi = row['uwi']
                update_columns = [col for col in row.index if col != 'uwi']
                set_clause = ", ".join([f"{col} = COALESCE(?, {col})" for col in update_columns])

                sql_update = f"""
                UPDATE uwis
                SET {set_clause}
                WHERE uwi = ?
                """

                update_values = [row[col] for col in update_columns]
                update_values.append(uwi)

                print(f"Executing SQL Update: {sql_update}")
                print(f"Values: {update_values}")
                self.cursor.execute(sql_update, update_values)

                if self.cursor.rowcount == 0:
                    columns = ['uwi'] + update_columns
                    placeholders = ", ".join(["?" for _ in columns])

                    sql_insert = f"""
                    INSERT INTO uwis ({', '.join(columns)})
                    VALUES ({placeholders})
                    """

                    # Correct insert values to avoid duplicating 'uwi'
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


    def get_uwis_with_surface_xy(self):
        """Fetches all UWIs along with their surface X and Y coordinates from the database."""
        try:
            self.connect()
            self.cursor.execute("SELECT uwi, surface_x, surface_y FROM uwis")
            results = self.cursor.fetchall()
            return [{"uwi": str(row[0]), "surface_x": row[1], "surface_y": row[2]} for row in results]
        except sqlite3.Error as e:
            print("Error retrieving UWIs with surface XY coordinates:", e)
            return []
        finally:
            self.disconnect()





    def get_uwis_with_heel_toe(self):
        """
        Fetches all UWIs along with their heel and toe coordinates from the database.
        Handles None or missing values gracefully.
        """
        try:
            self.connect()
            self.cursor.execute("SELECT uwi, heel_x, heel_y, toe_x, toe_y FROM uwis")
            results = self.cursor.fetchall()
            formatted_results = []
            for row in results:
                # Skip rows with missing critical data
                if any(value is None for value in row[1:]):
                    print(f"Skipping row for UWI {row[0]} due to missing data: {row}")
                    continue

                try:
                    formatted_results.append({
                        "uwi": str(row[0]),
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


    def get_uwis_with_average_tvd(self):
        """
        Fetches all UWIs along with their average TVD from the database.
        Handles None or missing values gracefully.
        """
        try:
            self.connect()
            self.cursor.execute("SELECT uwi, average_tvd FROM uwis")
            results = self.cursor.fetchall()
            formatted_results = []
        
            for row in results:
                # Skip rows with missing average_tvd
                if row[1] is None:
                    print(f"Skipping row for UWI {row[0]} due to missing average_tvd data: {row}")
                    continue
            
                try:
                    formatted_results.append({
                        "uwi": str(row[0]),
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



    def update_uwi_revenue_and_efr(self, uwi, npv, npv_discounted, EFR_oil, EFR_gas, EUR_oil_remaining, EUR_gas_remaining, scenario_id=1):
        self.connect()
        update_sql = """
        UPDATE model_properties
        SET npv = ?, npv_discounted = ?, EFR_oil = ?, EFR_gas = ?, EUR_oil_remaining = ?, EUR_gas_remaining = ?
        WHERE uwi = ? AND scenario_id = ?
        """
        try:
            # Execute the update query with the new parameters
            self.cursor.execute(update_sql, (npv, npv_discounted, EFR_oil, EFR_gas, EUR_oil_remaining, EUR_gas_remaining, uwi, scenario_id))
            self.connection.commit()
            print(f"UWI '{uwi}' (Scenario {scenario_id}) updated with NPV '{npv}', NPV Discounted '{npv_discounted}', "
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
        (uwi, date, oil_volume, gas_volume, cumulative_oil_volume, cumulative_gas_volume, q_gas, error_gas, q_oil, error_oil, oil_revenue, gas_revenue, total_revenue, discounted_revenue, cumulative_days)
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
            uwi TEXT NOT NULL,
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
            FOREIGN KEY (scenario_id) REFERENCES uwis(scenario_id)
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
        Update oil and gas production rates along with revenue data in the 'prod_rates_all' table using the uwi and scenario_id specified in the DataFrame.
        """
        try:
            # Ensure dataframe has the necessary columns
            required_columns = ['uwi', 'date', 'q_oil', 'q_gas', 'total_revenue', 'discounted_revenue', 'gas_revenue', 'oil_revenue']
            if not all(column in dataframe.columns for column in required_columns):
                raise ValueError("DataFrame is missing required columns.")

            uwi = dataframe['uwi'].iloc[0]  # Assumes all rows have the same uwi
            dataframe['date'] = dataframe['date'].dt.strftime('%Y-%m-%d')  # Format the date column
            self.connection.execute('BEGIN')  # Start a transaction

            # Delete existing records for the specified UWI and scenario_id
            delete_query = "DELETE FROM prod_rates_all WHERE uwi = ? AND scenario_id = ?"
            self.cursor.execute(delete_query, (uwi, scenario_id))
            deleted_rows = self.cursor.rowcount
            print(f"Deleted {deleted_rows} rows for UWI {uwi} and scenario_id {scenario_id}")

            # Insert new data
            insert_query = """
            INSERT INTO prod_rates_all (uwi, date, q_oil, q_gas, total_revenue, discounted_revenue, gas_revenue, oil_revenue, scenario_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(uwi, date, scenario_id) DO UPDATE SET
            q_oil = excluded.q_oil,
            q_gas = excluded.q_gas,
            total_revenue = excluded.total_revenue,
            discounted_revenue = excluded.discounted_revenue,
            gas_revenue = excluded.gas_revenue,
            oil_revenue = excluded.oil_revenue;
            """
    
            for index, row in dataframe.iterrows():
                self.cursor.execute(insert_query, (
                    uwi, row['date'], row['q_oil'], row['q_gas'],
                    row['total_revenue'], row['discounted_revenue'],
                    row['gas_revenue'], row['oil_revenue'], scenario_id
                ))

            self.connection.commit()
            print(f"Data updated successfully in prod_rates_all for uwi {uwi} and scenario_id {scenario_id}")
        except Exception as e:
            self.connection.rollback()
            print(f"Error updating data in prod_rates_all: {e}")
            logging.error(f"Error updating data in prod_rates_all for uwi {uwi} and scenario_id {scenario_id}: {e}")


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
            uwi TEXT NOT NULL,
            sum_error_oil REAL DEFAULT NULL,
            sum_error_gas REAL DEFAULT NULL,
            PRIMARY KEY (scenario_id, uwi)
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
                INSERT INTO sum_of_errors (scenario_id, uwi, sum_error_oil, sum_error_gas)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(scenario_id, uwi) DO UPDATE SET
                    sum_error_oil = excluded.sum_error_oil,
                    sum_error_gas = excluded.sum_error_gas
                """

                # Execute the query
                self.cursor.execute(upsert_query, (
                    row_dict['scenario_id'],
                    row_dict['uwi'],
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
            uwi TEXT NOT NULL,
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
            PRIMARY KEY (scenario_id, uwi)
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
        query = "DELETE FROM model_properties WHERE scenario_id = ?"
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(query, (scenario_id,))
                conn.commit()
        except sqlite3.Error as e:
            print(f"Error deleting model properties for scenario {scenario_id}: {e}")

    def delete_production_rates_for_scenario(self, scenario_id):
        """Delete production rates associated with a specific scenario."""
        query = "DELETE FROM prod_rates_all WHERE scenario_id = ?"
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(query, (scenario_id,))
                conn.commit()
        except sqlite3.Error as e:
            print(f"Error deleting production rates for scenario {scenario_id}: {e}")

    def save_eur_to_model_properties(self, uwi, q_oil_eur, q_gas_eur, q_oil_eur_normalized=None, q_gas_eur_normalized=None, scenario_id=1):
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
            scenario_id = ? AND uwi = ?;
        """

        try:
            self.cursor.execute(query, (q_oil_eur, q_gas_eur, q_oil_eur_normalized, q_gas_eur_normalized, scenario_id, uwi))
            if self.cursor.rowcount == 0:
                print(f"No matching row found for UWI: {uwi} and Scenario ID: {scenario_id}.")
            self.connection.commit()
        except Exception as e:
            print(f"Error updating EUR values for UWI {uwi}: {e}")
        finally:
            self.disconnect()


    #keep
    def retrieve_model_data_by_scenario_and_uwi(self, scenario_id, uwi):
        try:
            self.connect()
            print(f"Connected to database at {self.db_path}")
        
            query = "SELECT * FROM model_properties WHERE scenario_id = ? AND uwi = ?"
            self.cursor.execute(query, (scenario_id, uwi))
            data = self.cursor.fetchall()
        
            if not data:
                print(f"No data found for scenario_id: {scenario_id} and uwi: {uwi}")
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


    
    def update_payback_months(self, uwi, payback_months, scenario_id):
        """
        Updates the payback_months column in model_properties for a given UWI and scenario.
        
        :param uwi: Unique Well Identifier
        :param payback_months: Number of months required for payback
        :param scenario_id: Scenario identifier
        """
        try:
            self.connect()
            cursor = self.connection.cursor()
            query = """
                UPDATE model_properties 
                SET payback_months = ? 
                WHERE uwi = ? AND scenario_id = ?
            """
            cursor.execute(query, (payback_months, uwi, scenario_id))
            self.connection.commit()
            print(f"Updated payback months for UWI {uwi} in scenario {scenario_id}: {payback_months}")
        except Exception as e:
            print(f"Error updating payback months for UWI {uwi}: {e}")
        finally:
            self.disconnect()




    def retrieve_prod_rates_all(self, current_uwi=None, scenario_id=None):
        try:
            self.connect()
            # Get column names
            self.cursor.execute("PRAGMA table_info(prod_rates_all)")
            columns = [column[1] for column in self.cursor.fetchall()]

            if current_uwi and scenario_id:
                # Select data for the specified uwi and scenario_id
                query = "SELECT * FROM prod_rates_all WHERE uwi = ? AND scenario_id = ?"
                self.cursor.execute(query, (current_uwi, scenario_id))
            elif current_uwi:
                # Select data for the specified uwi
                query = "SELECT * FROM prod_rates_all WHERE uwi = ?"
                self.cursor.execute(query, (current_uwi,))
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





    def get_all_uwis(self):
        import pandas as pd
        try:
            self.connect()
            self.cursor.execute("SELECT * FROM uwis")  # Fetch all rows and columns
            rows = self.cursor.fetchall()

            # Extract column names
            column_names = [description[0] for description in self.cursor.description]

            # Create and return a DataFrame
            return pd.DataFrame(rows, columns=column_names)

        except sqlite3.Error as e:
            print("Error retrieving all uwis:", e)
            return pd.DataFrame()  # Return an empty DataFrame on error

        finally:
            self.disconnect()


    def get_uwis(self):
        try:
            self.connect()
            self.cursor.execute("SELECT uwi FROM uwis")
            uwis = self.cursor.fetchall()
            return [str(uwi[0]) for uwi in uwis]
        except sqlite3.Error as e:
            print("Error retrieving uwis:", e)
            return []

        finally:
            self.disconnect()

    def get_capex_for_uwi(self, uwi, scenario_id):
        """
        Retrieve capital expenditures (CapEx) for a given UWI and scenario.
    
        Args:
            uwi (str): Unique Well Identifier.
            scenario_id (int): Scenario ID.
    
        Returns:
            float: CapEx value or 0 if not found.
        """
        self.connect()
        query = """
        SELECT capital_expenditures FROM model_properties
        WHERE scenario_id = ? AND uwi = ?
        """
        try:
            self.cursor.execute(query, (scenario_id, uwi))
            result = self.cursor.fetchone()
            return result[0] if result else 0
        except Exception as e:
            print(f"Error retrieving CapEx for UWI {uwi}: {e}")
            return 0
        finally:
            self.disconnect()

    def get_opex_for_uwi(self, uwi, scenario_id):
        """
        Retrieve operating expenditures (OpEx) for a given UWI and scenario.
    
        Args:
            uwi (str): Unique Well Identifier.
            scenario_id (int): Scenario ID.
    
        Returns:
            float: OpEx value or 0 if not found.
        """
        self.connect()
        query = """
        SELECT operating_expenditures FROM model_properties
        WHERE scenario_id = ? AND uwi = ?
        """
        try:
            self.cursor.execute(query, (scenario_id, uwi))
            result = self.cursor.fetchone()
            return result[0] if result else 0
        except Exception as e:
            print(f"Error retrieving OpEx for UWI {uwi}: {e}")
            return 0
        finally:
            self.disconnect()


    def retrieve_lateral_lengths(self):
        """
        Retrieve lateral lengths for all UWIs from the database.
    
        Returns:
            pd.DataFrame: DataFrame with columns ['uwi', 'lateral']
        """
        self.connect()
        try:
            query = "SELECT uwi, lateral FROM uwis WHERE lateral IS NOT NULL"
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
            SELECT uwi 
            FROM uwis 
            WHERE status = 'Planned'
            """
            self.cursor.execute(query)
            return [row[0] for row in self.cursor.fetchall()]
        except sqlite3.Error as e:
            print(f"Error getting planned wells: {e}")
            return []
        finally:
            self.disconnect()

    def get_uwis_by_status(self, status):
        try:
            self.connect()
            self.cursor.execute("SELECT uwi FROM uwis WHERE status = ?", (status,))
            uwis = self.cursor.fetchall()
            return [str(uwi[0]) for uwi in uwis]
        except sqlite3.Error as e:
            print(f"Error retrieving {status} uwis:", e)
            return []
        finally:
            self.disconnect()
    def retrieve_tab2(self, today_date):
        try:
            self.connect()
            self.cursor.execute("SELECT date, uwi, discounted_revenue FROM prod_rates_all WHERE date >= ?", (today_date,))
            rows = self.cursor.fetchall()
            return rows
        except sqlite3.Error as e:
            print("Error retrieving data from database:", e)
            return None
        finally:
            self.disconnect()

    def get_active_uwis_with_properties(self):
        try:
            self.connect()
            query = """
            SELECT DISTINCT u.uwi 
            FROM uwis u 
            JOIN model_properties mp ON u.uwi = mp.uwi 
            WHERE u.status = 'Active'
            """
    
            self.cursor.execute(query)
            results = self.cursor.fetchall()
            return [row[0] for row in results]
        finally:
            self.disconnect()

    def get_uwis_by_scenario_id(self, scenario_id):
        try:
            self.connect()
            query = "SELECT DISTINCT uwi FROM model_properties WHERE scenario_id = ?"
            self.cursor.execute(query, (scenario_id,))
            uwis = self.cursor.fetchall()
            return [str(uwi[0]) for uwi in uwis]
        except sqlite3.Error as e:
            print(f"Error retrieving UWIs for scenario_id {scenario_id}: {e}")
            return []
        finally:
            self.disconnect()

    def retrieve_error_row(self,  current_uwi, scenario_id):
        try:
            self.connect()
            query = "SELECT * FROM sum_of_errors WHERE scenario_id = ? AND uwi = ?"
            self.cursor.execute(query, (scenario_id, current_uwi))
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


    def update_model_properties(self, df_model_properties, scenario_id):
       try:
           df_model_properties = df_model_properties.copy()
           df_model_properties['scenario_id'] = scenario_id
       
           # Convert model status columns to integer
           df_model_properties['oil_model_status'] = df_model_properties['oil_model_status'].astype(int)
           df_model_properties['gas_model_status'] = df_model_properties['gas_model_status'].astype(int)

           uwi = df_model_properties['uwi'].iloc[0]
           self.connect()

           self.cursor.execute("SELECT COUNT(*) FROM model_properties WHERE scenario_id = ? AND uwi = ?", 
                             (scenario_id, uwi))
           exists = self.cursor.fetchone()[0] > 0

           if exists:
               update_cols = [col for col in df_model_properties.columns if col not in ['uwi', 'scenario_id']]
               update_sql = f"UPDATE model_properties SET {', '.join(f'{col} = ?' for col in update_cols)} WHERE scenario_id = ? AND uwi = ?"
           
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

               values.extend([scenario_id, uwi])
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



    def update_uwi_errors(self, dataframe, scenario_id):
        """Update or insert UWI errors in the sum_of_errors table."""
        print(scenario_id)
        try:
            self.connect()

            for index, row in dataframe.iterrows():
                uwi = row['uwi']
                sum_error_oil = row['sum_error_oil']
                sum_error_gas = row['sum_error_gas']

                # Check if the scenario_id and UWI combination exists in the table
                self.cursor.execute("SELECT COUNT(*) FROM sum_of_errors WHERE scenario_id = ? AND uwi = ?", (scenario_id, uwi))
                count = self.cursor.fetchone()[0]

                if count > 0:
                    # If the combination exists, update the corresponding row
                    self.cursor.execute(
                        "UPDATE sum_of_errors SET sum_error_oil = ?, sum_error_gas = ? WHERE scenario_id = ? AND uwi = ?",
                        (sum_error_oil, sum_error_gas, scenario_id, uwi)
                    )
                else:
                    # If the combination does not exist, insert a new row
                    self.cursor.execute(
                        "INSERT INTO sum_of_errors (scenario_id, uwi, sum_error_oil, sum_error_gas) VALUES (?, ?, ?, ?)",
                        (scenario_id, uwi, sum_error_oil, sum_error_gas)
                    )

            # Commit the changes
            self.connection.commit()
            print("UWI errors updated successfully.")
        except Exception as e:
            print(f"Error updating UWI errors: {e}")
            self.connection.rollback()
        finally:
            self.disconnect()


    def update_uwi_prod_rates(self, df_production_rates, scenario_id=0):
        print(scenario_id)
        try:
            self.connect()

            # Check if the connection and cursor are valid
            if not self.connection or not self.cursor:
                print("Error: Database connection or cursor is not initialized.")
                return

            # Extract the uwi from the DataFrame
            if 'uwi' not in df_production_rates.columns:
                print("Error: 'uwi' column not found in the DataFrame")
                return

            uwi = df_production_rates['uwi'].iloc[0]
            print(f"Updating production rates for UWI: {uwi} and Scenario ID: {scenario_id}")

            # Convert date to string format
            if 'date' not in df_production_rates.columns:
                print("Error: 'date' column not found in the DataFrame")
                return

            df_production_rates['date'] = df_production_rates['date'].dt.strftime('%Y-%m-%d')

            # Start a transaction
            self.connection.execute('BEGIN')

            # Delete existing records for the specified UWI and Scenario ID
            delete_query = "DELETE FROM prod_rates_all WHERE uwi = ? AND scenario_id = ?"
            self.cursor.execute(delete_query, (uwi, scenario_id))
            deleted_rows = self.cursor.rowcount
            print(f"Deleted {deleted_rows} rows for UWI {uwi} and Scenario ID {scenario_id}")

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
            print(f"Data updated successfully in prod_rates_all for UWI: {uwi} and Scenario ID: {scenario_id}")
        except Exception as e:
            # Rollback the transaction in case of an error
            self.connection.rollback()
            print(f"Error updating data in prod_rates_all: {e}")
        finally:
            # Ensure the connection is properly closed
            self.disconnect()




    def retrieve_prod_rates_by_uwi(self, current_uwi=None):
        try:
            self.connect()
            # Get column names
            self.cursor.execute("PRAGMA table_info(prod_rates_all)")
            columns = [column[1] for column in self.cursor.fetchall()]

            if current_uwi:
                # Select data for the specified uwi
                query = "SELECT * FROM prod_rates_all WHERE uwi = ?"
                self.cursor.execute(query, (current_uwi,))
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

    def get_model_status(self, current_uwi, model_type):
        # Query the database to get the model status for the specified type and uwi
        try:
            self.connect()
            query = f"SELECT {model_type}_model_status FROM model_properties WHERE uwi = ?"
            self.cursor.execute(query, (current_uwi,))
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

    def update_model_status(self, current_uwi, new_status, model_type):
        try:
            self.connect()
            query = f"UPDATE model_properties SET {model_type}_model_status = CAST(? AS INTEGER) WHERE uwi = ?"
            self.cursor.execute(query, (int(new_status), current_uwi))
            self.connection.commit()
        except sqlite3.Error as e:
            print(f"Error updating {model_type} model status:", e)

    def delete_uwi_records(self, uwi):
        # Ensure there's an active database connection
        self.connect()  # Assuming this method sets up self.connection if not already connected

            # List of tables from which to delete records
        tables = ['model_properties', 'prod_rates_all', 'sum_of_errors', 'uwis']
        for table in tables:
            # SQL query that deletes rows where the uwi matches the given uwi
            query = f"DELETE FROM {table} WHERE uwi = ?"
            self.cursor.execute(query, (uwi,))  # Execute the query with the uwi parameter

            # Commit the changes to the database
        self.connection.commit()
      
        self.disconnect()

    def retrieve_and_sum(self):
        try:
            # Get column names
            self.connect()
            self.cursor.execute("PRAGMA table_info(prod_rates_all)")
            columns = [column[1] for column in self.cursor.fetchall()]

            self.cursor.execute("SELECT * FROM prod_rates_all")
        
            rows = self.cursor.fetchall()
        
            # Convert rows to DataFrame with column names
            df = pd.DataFrame(rows, columns=columns)
            
            # Ensure date column is in datetime format
            df['date'] = pd.to_datetime(df['date'])

            # Group by date and sum total_revenue and discounted_revenue
            combined_data = df.groupby('date').agg({
                'total_revenue': 'sum',
                'discounted_revenue': 'sum'
            }).reset_index()

            # Retrieve the first date for each well
            # Retrieve the first and last date for each well
            # Retrieve the first and last date for each well
            date_ranges = df.groupby('uwi')['date'].agg(['min', 'max']).reset_index()
            date_ranges.columns = ['uwi', 'first_date', 'last_date']
            return combined_data, date_ranges
        except sqlite3.Error as e:
            print("Error retrieving production rates:", e)
            return None
        finally:
            self.disconnect()


    def create_saved_dca_table(self):
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS saved_dca (
            id INTEGER PRIMARY KEY,
            curve_name TEXT NOT NULL,
            uwi TEXT,
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

    def save_decline_curve_to_db(self, curve_name, uwi_model_data):
        if not isinstance(uwi_model_data, pd.DataFrame):
            print("Error: uwi_model_data is not a DataFrame")
            return

        # Add curve_name column to the DataFrame
        uwi_model_data['curve_name'] = curve_name

        try:
            self.connect()

            # Retrieve columns of the saved_dca table
            self.cursor.execute("PRAGMA table_info(saved_dca)")
            columns_info = self.cursor.fetchall()
            saved_dca_columns = [col[1] for col in columns_info]

            # Ensure the DataFrame has the same columns as the table
            for col in saved_dca_columns:
                if col not in uwi_model_data.columns:
                    uwi_model_data[col] = None

            # Reorder DataFrame columns to match the table columns
            uwi_model_data = uwi_model_data[saved_dca_columns]

            # Delete existing rows with the same curve_name
            delete_sql = "DELETE FROM saved_dca WHERE curve_name = ?"
            self.cursor.execute(delete_sql, (curve_name,))

            # Insert data into the main table
            for index, row in uwi_model_data.iterrows():
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

    def get_uwi_status(self, current_uwi):
        try:
            self.connect()
            # Define the query to check the status of the current UWI
            self.cursor.execute("SELECT status FROM uwis WHERE uwi = ?", (current_uwi,))
            result = self.cursor.fetchone()
        
            print(result[0])  # Debug print to show the result
        
            if result and result[0] == 'Planned':  # Extract the status from the tuple
                return True
            else:
                return False
        except Exception as e:
            print(f"Error retrieving status for UWI {current_uwi}: {e}")
        finally:
            # Ensure the database connection is closed
            self.disconnect()


    def retrieve_aggregated_prod_rates(self, columns, scenario_id):
        print(columns)
        self.connect()
        query = f"""
        SELECT uwi, strftime('%Y-%m', date) as date, {', '.join(columns)}
        FROM prod_rates_all
        WHERE scenario_id = ?
        GROUP BY uwi, date
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
            uwi VARCHAR(255),
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
            FOREIGN KEY (uwi) REFERENCES uwis (uwi),
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

    def delete_pad(self, scenario_id, uwi):
        """Delete a pad from the database based on scenario ID and UWI."""
        query = """
        DELETE FROM well_pads
        WHERE scenario_id = ? AND uwi = ?
        """
        try:
            self.connect()
            cursor = self.connection.cursor()
            cursor.execute(query, (scenario_id, uwi))
            self.connection.commit()
            logging.info(f"Deleted pad: Scenario ID={scenario_id}, UWI={uwi}")
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

    def remove_well_pad_for_scenario(self, uwi, scenario_id):
        """
        Remove a well pad from the well_pads table for the given UWI and scenario_id.

        :param uwi: The unique well identifier (UWI) to remove.
        :param scenario_id: The scenario ID associated with the well pad to remove.
        """
        query = """
        DELETE FROM well_pads
        WHERE uwi = ? AND scenario_id = ?
        """
        try:
            self.connect()
            cursor = self.connection.cursor()
            cursor.execute(query, (uwi, scenario_id))
            self.connection.commit()
            print(f"Well pad with UWI '{uwi}' removed from scenario ID {scenario_id}.")
        except sqlite3.Error as e:
            print(f"Error removing well pad for UWI '{uwi}' and scenario ID {scenario_id}:", e)
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
        if 'uwi' not in well_pad_data or 'scenario_id' not in well_pad_data:
            raise ValueError("Both 'uwi' and 'scenario_id' are required fields.")

        query = """
        INSERT INTO well_pads (
            uwi,
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
                well_pad_data['uwi'],                           # Required
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


    def update_well_pad(self, well_pad_id, well_pad_data):
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

    def add_well_to_scenario(self, well_scenario_data):
        """Add or update a well in a scenario with more detailed data"""
        try:
            self.connect()
            query = """
            INSERT OR REPLACE INTO well_pads (
                uwi, scenario_id, start_date, decline_curve
            ) VALUES (?, ?, ?, ?)
            """
            self.cursor.execute(query, (
                well_scenario_data['uwi'], 
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
                INSERT OR REPLACE INTO sum_of_errors (scenario_id, uwi, sum_error_oil, sum_error_gas)
                VALUES (?, ?, ?, ?)
                """

                # Execute the query
                self.cursor.execute(insert_or_replace_query, (
                    row_dict['scenario_id'],
                    row_dict['uwi'],
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
            self.cursor.execute("SELECT uwi, total_length FROM uwis")
            results = self.cursor.fetchall()  # Fetch all results
            return [{"uwi": str(row[0]), "total_length": row[1]} for row in results]
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
        SELECT id, uwi, total_depth, total_capex_cost, total_opex_cost, drill_time, prod_type, oil_model_status, gas_model_status,
               pad_cost, exploration_cost, cost_per_foot, distance_to_pipe, cost_per_foot_to_pipe, start_date
        FROM well_pads
        WHERE scenario_id = ?
        """
        try:
            self.connect()
            cursor = self.connection.cursor()
            cursor.execute(query, (scenario_id,))
            rows = cursor.fetchall()
            # Get the column names
            columns = [column[0] for column in cursor.description]
            well_pads = [dict(zip(columns, row)) for row in rows]
            return well_pads
        except sqlite3.Error as e:
            print(f"Error fetching well pads for scenario_id {scenario_id}:", e)
            return []
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
            query = "SELECT uwi FROM well_pads WHERE scenario_id = ?"
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

    def get_well_pad_id(self, uwi, scenario_id):
        """
        Retrieve the well pad ID for a given UWI and scenario ID.

        :param uwi: The unique well identifier (UWI).
        :param scenario_id: The scenario ID associated with the well pad.
        :return: The well pad ID if found, otherwise None.
        """
        query = """
        SELECT id
        FROM well_pads
        WHERE uwi = ? AND scenario_id = ?
        """
        try:
            self.connect()
            self.cursor.execute(query, (uwi, scenario_id))
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
            uwi TEXT NOT NULL,
            md REAL NOT NULL,  -- Measured Depth
            tvd REAL NOT NULL,  -- True Vertical Depth
            "X Offset" REAL NOT NULL,
            "Y Offset" REAL NOT NULL,
            "Cumulative Distance" REAL NOT NULL,
            FOREIGN KEY (uwi) REFERENCES uwis(uwi)
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

    def insert_directional_survey(self, uwi, x_offset, y_offset, md_depth, tvd_depth, inclination):
        self.connect()
        insert_sql = """
        INSERT INTO directional_surveys (uwi, x_offset, y_offset, md_depth, tvd_depth, inclination)
        VALUES (?, ?, ?, ?, ?, ?)
        """
        try:
            self.cursor.execute(insert_sql, (uwi, x_offset, y_offset, md_depth, tvd_depth, inclination))
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

    def update_parent_well_counts(self, uwi_counts, scenario_id):
        """
        Update parent_wells in model_properties for matching UWI and scenario_id
        Takes a list of counts
        """
        try:
            self.connect()
        
            # Direct update for each count in the list
            for entry in uwi_counts:  # Now iterating over list
                uwi = entry[0]  # First item is UWI
                count = entry[1]  # Second item is count
                self.cursor.execute("""
                    UPDATE model_properties 
                    SET parent_wells = ?
                    WHERE uwi = ? AND scenario_id = ?
                """, (count, uwi, scenario_id))
            
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
                        # If that fails, try lowercase uwi
                        query = f"""
                        SELECT uwi, "{column}" 
                        FROM "{table}" 
                        WHERE uwi IN ({','.join(['?']*len(wells))})
                        """
                        df_attr = pd.read_sql(query, self.connection, params=wells)
                        df_attr.set_index('uwi', inplace=True)
            
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
        """
        Discover and return strictly numeric attributes from zone tables.
        Excludes any columns with mixed types or string values.
        """
        try:
            self.connect()
            numeric_columns = set()
            well_zones = self.fetch_zone_names_by_type("Well")
        
            for zone_tuple in well_zones:
                zone_name = zone_tuple[0]
                try:
                    # Fetch zone table data
                    data, columns = self.fetch_zone_table_data(zone_name)
                
                    # Process each column except UWI
                    for col in columns[1:]:  # Skip UWI column
                        col_idx = columns.index(col)
                    
                        # Enhanced numeric check
                        if self._is_numeric_column(data, col_idx):
                            # Additional validation: check for consistent data type
                            sample_values = [row[col_idx] for row in data 
                                           if row[col_idx] is not None and row[col_idx] != '']
                        
                            if sample_values:  # Only process if we have non-null values
                                try:
                                    # Convert all values to float to ensure consistency
                                    all_numeric = all(isinstance(float(val), float) 
                                                   for val in sample_values)
                                    if all_numeric:
                                        numeric_columns.add(f"{zone_name}.{col}")
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
        """
        Create the Zones table to store zone names and types if it does not already exist.
        """
        self.connect()
        try:
            query = """
            CREATE TABLE IF NOT EXISTS Zones (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ZoneName TEXT UNIQUE NOT NULL,
                Type TEXT NOT NULL
            )
            """
            self.cursor.execute(query)
            self.connection.commit()
            print("Zones table created successfully.")
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

    def create_table_from_df(self, table_name, df):
        """
        Creates a SQLite table from a pandas DataFrame with sanitized table and column names.
        Skips columns that fail sanitization or validation.

        Parameters:
            table_name (str): Desired name of the table.
            df (pd.DataFrame): The DataFrame to be converted into a table.

        Returns:
            bool: True if the table was created successfully, False if the table already exists.
        """
        import re  # Ensure re module is imported
        self.connect()
        try:
            # Validate and sanitize the table name
            table_name = table_name.lower().replace(' ', '_').replace('-', '_')
            if not table_name.isidentifier():
                table_name = f"t_{table_name}"
            if not table_name.isidentifier():
                raise ValueError("Invalid table name after sanitization")

            # Check if the table already exists
            self.cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
            if self.cursor.fetchone():
                return False

            # Sanitize column names
            def sanitize_column(col):
                replacements = {
                    '³': '3', '²': '2', '.': '_', '/': '_', '[': '', ']': '',
                    '(': '', ')': '', ' ': '_', '-': '_', '#': '_', '$': '_',
                    '%': '_', '^': '_', '&': '_', '!': '_', '@': '_'
                }
                for old, new in replacements.items():
                    col = col.replace(old, new)

                # Replace remaining invalid characters
                col = re.sub(r'[^a-zA-Z0-9_]', '_', col)

                # Ensure the column name starts with a valid character
                if not col[0].isalpha():
                    col = f"c_{col}"

                # Validate column name length
                if not col:
                    return None  # Skip invalid column names
                return col

            # Debug original columns
            print("Original DataFrame columns:", df.columns.tolist())

            # Sanitize column names and track valid columns
            valid_columns = []
            sanitized_columns = []
            for col in df.columns:
                sanitized_col = sanitize_column(col)
                if sanitized_col:
                    valid_columns.append(col)
                    sanitized_columns.append(sanitized_col)
                else:
                    print(f"Skipping invalid column: {col}")

            # Filter DataFrame to include only valid columns
            df = df[valid_columns]
            df.columns = sanitized_columns

            # Debug sanitized columns
            print("Sanitized DataFrame columns:", sanitized_columns)

            # Validate and define column data types
            columns = ["id INTEGER PRIMARY KEY AUTOINCREMENT"]
            for col, sanitized_col in zip(valid_columns, sanitized_columns):
                try:
                    col_type = self.get_sqlite_type(df[sanitized_col].dtype)
                    columns.append(f"`{sanitized_col}` {col_type}")
                except Exception as e:
                    print(f"Skipping column '{col}' due to error: {e}")

            # Create table query
            create_query = f"""CREATE TABLE `{table_name}` ({', '.join(columns)})"""
            print("Create Table Query:", create_query)
            self.cursor.execute(create_query)

            # Insert data if DataFrame is not empty
            if not df.empty:
                df = df.where(pd.notnull(df), None)  # Replace NaN with None
                placeholders = ','.join(['?' for _ in sanitized_columns])
                insert_query = f"INSERT INTO `{table_name}` (`{'`,`'.join(sanitized_columns)}`) VALUES ({placeholders})"
                print("Insert Query:", insert_query)
                self.cursor.executemany(insert_query, df.to_records(index=False).tolist())

            # Commit the transaction
            self.connection.commit()
            print(f"Table '{table_name}' created and data inserted successfully.")
            return True

        except Exception as e:
            # Rollback on error and log the exception
            self.connection.rollback()
            print(f"Error creating table '{table_name}': {e}")
            raise
        finally:
            # Disconnect from the database
            self.disconnect()



    def add_zone_names(self, zone_name, zone_type):
        """
        Add a zone entry with a specific type to the database.

        Parameters:
            zone_name (str): The name of the zone to add.
            zone_type (str): The type of the zone (must be one of 'Zones', 'Intersections', 'Well').

        Returns:
            bool: True if the zone name was added, False if it already exists.
        """
        valid_types = {'Zone', 'Intersections', 'Well'}
        if zone_type not in valid_types:
            raise ValueError(f"Invalid zone type '{zone_type}'. Must be one of {valid_types}.")

        self.connect()
        try:
            # Check if the zone name already exists
            self.cursor.execute("SELECT COUNT(*) FROM Zones WHERE ZoneName = ? AND Type = ?", (zone_name, zone_type))
            if self.cursor.fetchone()[0] > 0:
                print(f"Zone '{zone_name}' with type '{zone_type}' already exists.")
                return False  # Zone name already exists

            # Insert the zone name with the given type
            self.cursor.execute("""
                INSERT INTO Zones (ZoneName, Type)
                VALUES (?, ?)
            """, (zone_name, zone_type))
            self.connection.commit()
            print(f"Zone '{zone_name}' with type '{zone_type}' added successfully.")
            return True
        except sqlite3.Error as e:
            print(f"Error adding zone name '{zone_name}' with type '{zone_type}': {e}")
            self.connection.rollback()
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

        Parameters:
        -----------
        zone_name : str
            The name of the zone to fetch data for

        Returns:
        --------
        tuple: A tuple containing (data, columns)
            - data: List of rows from the table
            - columns: List of column names
        """
        self.connect()
        try:
            # First, try to find the correct table
            # You might need to adjust this query based on your database schema
            self.cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [table[0] for table in self.cursor.fetchall()]
        
            # Find a table that matches the zone name or contains the zone name
            matching_tables = [
                table for table in tables 
                if zone_name.lower() in table.lower() or 
                   table.lower().startswith(zone_name.lower())
            ]

            if not matching_tables:
                raise ValueError(f"No table found for zone name: {zone_name}")

            # Use the first matching table
            table_name = matching_tables[0]

            # Fetch data from the table
            query = f"SELECT * FROM {table_name}"
            self.cursor.execute(query)
        
            # Fetch all rows
            data = self.cursor.fetchall()
        
            # Get column names
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

    def fetch_correlation_data(self, table_name, column_name, uwis):
        """
        Fetch specific column data for selected UWIs.
        Parameters:
        -----------
        table_name : str
            The name of the zone/table
        column_name : str
            The specific column to fetch
        uwis : list
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
            placeholders = ','.join('?' * len(uwis))
        
            # Fetch just the specific column for the selected UWIs
            query = f"SELECT UWI, {column_name} FROM {actual_table} WHERE UWI IN ({placeholders})"
            self.cursor.execute(query, uwis)
        
            # Convert to DataFrame
            results = self.cursor.fetchall()
            return pd.DataFrame(results, columns=['UWI', column_name])
        
        except sqlite3.Error as e:
            print(f"Error fetching correlation data: {e}")
            raise
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
           return pd.read_sql(query, self.connection)
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

    def update_zone_angles(self, zone_name, uwi, angle_top, angle_base):
       """Update angles for a specific UWI in a zone table."""
       self.connect()
       try:
           query = f"""
           UPDATE {zone_name} 
           SET Angle_Top = ?, Angle_Base = ?
           WHERE UWI = ?
           """
           self.cursor.execute(query, (angle_top, angle_base, uwi))
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
