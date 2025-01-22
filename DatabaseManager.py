import sqlite3
import pandas as pd
import logging

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
            npv REAL DEFAULT NULL,
            npv_discounted REAL DEFAULT NULL,
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
        # Ensure input data is a DataFrame
        if not isinstance(total_lat_data, pd.DataFrame):
            print("Input data must be a pandas DataFrame.")
            return

        # Check if the DataFrame is empty
        if total_lat_data.empty:
            print("The DataFrame is empty. Nothing to save.")
            return

        # Connect to the database
        self.connect()

        try:
            for _, row in total_lat_data.iterrows():
                uwi = row['uwi']

                # No special handling for spud_date if it's already valid or None
                spud_date = row.get('spud_date')

                # Prepare the dynamic SQL for updating columns
                update_columns = [col for col in row.index if col != 'uwi']
                set_clause = ", ".join([f"{col} = COALESCE(?, {col})" for col in update_columns])

                sql_update = f"""
                UPDATE uwis
                SET {set_clause}
                WHERE uwi = ?
                """

                # Prepare update values
                update_values = [row[col] for col in update_columns]
                update_values.append(uwi)

                # Execute update
                self.cursor.execute(sql_update, update_values)

                # If no rows were updated, insert a new record
                if self.cursor.rowcount == 0:
                    columns = ['uwi'] + update_columns
                    placeholders = ", ".join(["?" for _ in columns])

                    sql_insert = f"""
                    INSERT INTO uwis ({', '.join(columns)})
                    VALUES ({placeholders})
                    """

                    insert_values = [uwi] + update_values
                    self.cursor.execute(sql_insert, insert_values)

            # Commit the transaction
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
        try:
            self.connect()
        
            query = """
            SELECT 
                uwi, 
                CAST(heel_x AS FLOAT) AS heel_x, 
                CAST(heel_y AS FLOAT) AS heel_y, 
                CAST(toe_x AS FLOAT) AS toe_x, 
                CAST(toe_y AS FLOAT) AS toe_y
            FROM uwis
            WHERE 
                (heel_x IS NOT NULL AND heel_y IS NOT NULL AND 
                toe_x IS NOT NULL AND toe_y IS NOT NULL)
            """
        
            self.cursor.execute(query)
        
            # Fetch all rows
            heel_toe_data = self.cursor.fetchall()
        
            # Convert rows into dictionaries and cast values as float
            result = [
                {
                    "uwi": row[0],
                    "heel_x": float(row[1]) if row[1] is not None else None,
                    "heel_y": float(row[2]) if row[2] is not None else None,
                    "toe_x": float(row[3]) if row[3] is not None else None,
                    "toe_y": float(row[4]) if row[4] is not None else None
                }
                for row in heel_toe_data
            ]
        
            print(f"Retrieved {len(result)} wells with heel and toe coordinates.")
            return result
    
        except sqlite3.Error as e:
            print(f"Error retrieving heel and toe coordinates: {e}")
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
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS model_properties (
            scenario_id INTEGER NOT NULL,
            uwi TEXT NOT NULL,
            max_oil_production REAL DEFAULT NULL,
            max_gas_production REAL DEFAULT NULL,
            max_oil_production_date TEXT DEFAULT NULL,
            max_gas_production_date TEXT DEFAULT NULL,
            one_year_oil_production REAL DEFAULT NULL,
            one_year_gas_production REAL DEFAULT NULL,
            di_oil REAL DEFAULT NULL,
            di_gas REAL DEFAULT NULL,
            oil_b_factor REAL DEFAULT NULL,
            gas_b_factor REAL DEFAULT NULL,
            min_dec_oil REAL DEFAULT NULL,
            min_dec_gas REAL DEFAULT NULL,
            model_oil TEXT DEFAULT NULL,
            model_gas TEXT DEFAULT NULL,
            economic_limit_type TEXT DEFAULT NULL,
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
            net_price_gas REAL DEFAULT NULL,
            gas_model_status TEXT DEFAULT NULL,
            oil_model_status TEXT DEFAULT NULL,
            q_oil_eur REAL DEFAULT NULL, 
            q_gas_eur REAL DEFAULT NULL,  
            EFR_oil REAL DEFAULT NULL,    
            EFR_gas REAL DEFAULT NULL,    
            EUR_oil_remaining REAL DEFAULT NULL,  
            EUR_gas_remaining REAL DEFAULT NULL,  
            npv REAL DEFAULT NULL,           
            npv_discounted REAL DEFAULT NULL,  
            payback_months REAL DEFAULT NULL,  ,
            parrent_well REAL DEFAULT NULL,  
            PRIMARY KEY (scenario_id, uwi)
        )
        """
        try:
            self.cursor.execute(create_table_sql)
            self.connection.commit()
            print("Model properties table created or updated successfully.")
        except sqlite3.Error as e:
            print("Error creating model properties table:", e)
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
    def save_eur_to_model_properties(self, uwi, q_oil_eur, q_gas_eur, scenario_id=1):
        """
        Update the EUR values in the model_properties table for the given UWI and scenario_id.
        """
        self.connect()  # Ensure the database connection is established

        # SQL query to update EUR values
        query = """
        UPDATE model_properties
        SET 
            q_oil_eur = ?, 
            q_gas_eur = ?
        WHERE 
            scenario_id = ? AND uwi = ?;
        """

        try:
            self.cursor.execute(query, (q_oil_eur, q_gas_eur, scenario_id, uwi))
            if self.cursor.rowcount == 0:
                print(f"No matching row found for UWI: {uwi} and Scenario ID: {scenario_id}.")
            self.connection.commit()  # Commit the changes
        except Exception as e:
            print(f"Error updating EUR values for UWI {uwi}: {e}")


    def retrieve_model_data_by_scenario_and_uwi(self,  scenario_id, current_uwi):
        """
        Retrieve model properties for the specified UWI and scenario_id.
        """
        print("Retrieving model properties for UWI:", current_uwi, "Scenario ID:", scenario_id)

        try:
            self.connect()
            query = "SELECT * FROM model_properties WHERE uwi = ? AND scenario_id = ?"
            self.cursor.execute(query, (current_uwi, scenario_id))
            data = self.cursor.fetchone()
            if data:
                # Extract column names from the cursor description
                columns = [description[0] for description in self.cursor.description]
                # Convert fetched data to a DataFrame
                df = pd.DataFrame([data], columns=columns)

                return df
            else:
                return None
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
    def retrieve_model_data_by_scenario_and_uwi(self, scenario_id, uwi):
        try:
            self.connect()
            print(f"Connected to database at {self.db_path}")
            
            query = "SELECT * FROM model_properties WHERE scenario_id = ? AND uwi = ?"
            self.cursor.execute(query, (scenario_id, uwi))
            rows = self.cursor.fetchall()
            
            if not rows:
                print(f"No data found for scenario_id: {scenario_id} and uwi: {uwi}")
                return None
            
            column_names = [description[0] for description in self.cursor.description]
            print(f"Column names: {column_names}")
            
            # Convert rows to DataFrame
            model_data_df = pd.DataFrame(rows, columns=column_names)
            return model_data_df
        
        except sqlite3.Error as e:
            print("Error retrieving model data:", e)
            return None
        
        finally:
            self.disconnect()
            print("Disconnected from database")



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










    def retrieve_sum_of_errors(self):
        try:
            self.connect()
            self.cursor.execute("SELECT * FROM sum_of_errors")
            rows = self.cursor.fetchall()
            column_names = [description[0] for description in self.cursor.description]
            df = pd.DataFrame(rows, columns=column_names)
            return df
        except sqlite3.Error as e:
            print("Error retrieving sum of errors:", e)
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
   
        print(df_model_properties)
        try:
            # If model_data is a list, convert it to a DataFrame
                
            df_model_properties = df_model_properties

            # Add the scenario_id column to the dataframe
            df_model_properties['scenario_id'] = scenario_id
        
            # Extract uwi from the DataFrame

            uwi = df_model_properties['uwi'].iloc[0]
            self.connect()

            # Check if the combination of scenario_id and UWI exists in the table
            self.cursor.execute("SELECT COUNT(*) FROM model_properties WHERE scenario_id = ? AND uwi = ?", (scenario_id, uwi))
            exists = self.cursor.fetchone()[0] > 0

            if exists:
                # Generate the SQL UPDATE statement, excluding the specified fields
                update_sql = f"UPDATE model_properties SET {', '.join([f'{col} = ?' for col in df_model_properties.columns if col not in ['uwi', 'scenario_id']])} WHERE scenario_id = ? AND uwi = ?"
            
                # Extract the values to be updated from the DataFrame and perform data type conversion
                values = []
                for col in df_model_properties.columns:
                    if col not in ['uwi', 'scenario_id']:
                        value = df_model_properties[col].iloc[0]
                        # Perform data type conversion based on the data types expected by SQLite
                        if isinstance(value, pd.Timestamp):  # Convert datetime64[ns] to string
                            value = value.strftime('%Y-%m-%d')  # Extract date part only
                        elif isinstance(value, pd.Series):  # Extract scalar value from pandas Series
                            value = value.item()
                        elif isinstance(value, bool):  # Convert boolean to integer
                            value = int(value)
                        # Append the converted value to the values list
                        values.append(value)
            
                # Ensure scenario_id and uwi are the last values in the list
                values.extend([scenario_id, uwi])

                # Print values for debugging
                print("Values to be updated:", values)

                # Execute the UPDATE statement
                self.cursor.execute(update_sql, values)
                self.connection.commit()
                print(f"Model properties updated successfully for scenario_id {scenario_id} and uwi {uwi}.")
            else:
                # Insert the new record
                df_model_properties.to_sql('model_properties', self.connection, if_exists='append', index=False)
                self.connection.commit()
                print(f"Model properties inserted successfully for scenario_id {scenario_id} and uwi {uwi}.")

        except sqlite3.Error as e:
            print("Error updating model properties:", e)
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
        # Update the model status in the database for the specified type and uwi
        try:
            self.connect()
            query = f"UPDATE model_properties SET {model_type}_model_status = ? WHERE uwi = ?"
            self.cursor.execute(query, (new_status, current_uwi))
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
            decline_curve VARCHAR(255),
            total_depth DECIMAL(10, 2),
            total_capex_cost DECIMAL(15, 2),
            total_opex_cost DECIMAL(15, 2),
            drill_time INTEGER,
            prod_type VARCHAR(50),
            oil_model_status BOOLEAN,
            gas_model_status BOOLEAN,
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