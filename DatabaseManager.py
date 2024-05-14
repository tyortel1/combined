import sqlite3
import pandas as pd

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

    def insert_uwi(self, uwi):
        insert_uwi_sql = "INSERT INTO uwis (uwi) VALUES (?)"
        try:
            self.cursor.execute(insert_uwi_sql, (uwi,))
            self.connection.commit()
            print("UWI '{}' inserted successfully.".format(uwi))
        except sqlite3.Error as e:
            print("Error inserting UWI:", e)

    def create_uwi_table(self):
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS uwis (
            id INTEGER PRIMARY KEY,
            uwi TEXT UNIQUE NOT NULL
        )
        """
        try:
            self.cursor.execute(create_table_sql)
            self.connection.commit()
            print("UWIs table created successfully.")
        except sqlite3.Error as e:
            print("Error creating UWIs table:", e)

    def insert_production_data(self, data):
        """Insert production data into the prod_rates_all table."""
        insert_sql = '''
        INSERT INTO prod_rates_all
        (UWI, date, oil_volume, gas_volume, cumulative_oil_volume, cumulative_gas_volume, q_gas, error_gas, q_oil, error_oil, oil_revenue, gas_revenue, total_revenue, discounted_revenue, cumulative_days)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        '''
        try:
            cursor = self.connection.cursor()
            cursor.executemany(insert_sql, data)
            self.connection.commit()
        except sqlite3.Error as e:
            print("An error occurred:", e)
            self.connection.rollback()
        finally:
            cursor.close()


    def create_prod_rates_all_table(self):
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS prod_rates_all (
            id INTEGER PRIMARY KEY,
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

            FOREIGN KEY (UWI) REFERENCES uwis(uwi)
        )
        """
        try:
            with self.connection:  # This automatically commits or rolls back
                self.cursor.execute(create_table_sql)
            print("prod_rates_all table created successfully.")
        except sqlite3.Error as e:
            print("Error creating prod_rates_all table:", e)


    def prod_rates_all(self, dataframe, table_name):
        """Store the dataframe into the specified table in the database."""
        try:
            dataframe['date'] = dataframe['date'].dt.strftime('%Y-%m-%d')
            dataframe.to_sql(table_name, self.connection, if_exists='replace', index=False)
            print(f"Data stored successfully in {table_name}")
        except Exception as e:
            print(f"Error storing data in {table_name}: {e}")


    def update_prod_rates(self, dataframe):
        """
        Update oil and gas production rates along with revenue data in the 'prod_rates_all' table using the UWI specified in the DataFrame.
        """
        try:
            uwi = dataframe['uwi_id'].iloc[0]  # Assumes all rows have the same UWI
            dataframe['date'] = dataframe['date'].dt.strftime('%Y-%m-%d')  # Format the date column
            self.connection.execute('BEGIN')  # Start a transaction

            for index, row in dataframe.iterrows():
                query = f"""
                INSERT INTO prod_rates_all (uwi_id, date, q_oil, q_gas, total_revenue, discounted_revenue, gas_revenue, oil_revenue)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(uwi_id, date) DO UPDATE SET
                q_oil = excluded.q_oil,
                q_gas = excluded.q_gas,
                total_revenue = excluded.total_revenue,
                discounted_revenue = excluded.discounted_revenue,
                gas_revenue = excluded.gas_revenue,
                oil_revenue = excluded.oil_revenue;
                """
                self.cursor.execute(query, (
                    uwi, row['date'], row['q_oil'], row['q_gas'],
                    row['total_revenue'], row['discounted_revenue'],
                    row['gas_revenue'], row['oil_revenue']
                ))

            self.connection.commit()
            print(f"Data updated successfully in prod_rates_all for UWI {uwi}")
        except Exception as e:
            self.connection.rollback()
            print(f"Error updating data in prod_rates_all: {e}")



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

    def create_model_properties_table(self):
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS model_properties (
            id INTEGER PRIMARY KEY,
            uwi_id INTEGER,
            economic_limit_type TEXT DEFAULT NULL,
            b_factor_gas REAL DEFAULT NULL,
            min_dec_gas REAL DEFAULT NULL,
            b_factor_oil REAL DEFAULT NULL,
            min_dec_oil REAL DEFAULT NULL,
            economic_limit_date TEXT DEFAULT NULL,
            oil_price REAL DEFAULT NULL,
            gas_price REAL DEFAULT NULL,
            oil_price_dif REAL DEFAULT NULL,
            gas_price_dif REAL DEFAULT NULL,
            discount_rate REAL DEFAULT NULL,
            tax_rate REAL DEFAULT NULL,
            capital_expenditures REAL DEFAULT NULL,
            operating_expenditures REAL DEFAULT NULL,
            net_price_oil REAL DEFAULT NULL,
            net_price_gas REAL DEFAULT NULL,
            FOREIGN KEY (uwi_id) REFERENCES uwis(id)
        )
        """
        try:
            self.cursor.execute(create_table_sql)
            self.connection.commit()
            print("Model properties table created successfully.")
        except sqlite3.Error as e:
            print("Error creating model properties table:", e)

    

    def create_sum_of_errors_table(self):
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS sum_of_errors (
            id INTEGER PRIMARY KEY,
            uwi_id INTEGER,
            sum_error_oil REAL DEFAULT NULL,
            sum_error_gas REAL DEFAULT NULL,
            FOREIGN KEY (uwi_id) REFERENCES uwis(id)
        )
        """
        try:
            self.cursor.execute(create_table_sql)
            self.connection.commit()
            print("Sum of errors table created successfully.")
        except sqlite3.Error as e:
            print("Error creating sum of errors table:", e)

    def store_sum_of_errors_dataframe(self, sum_of_errors_dataframe, table_name):
        """Store the sum of errors DataFrame into a specified table in the database."""
        try:
            self.connect()  # Ensure connection is open
            sum_of_errors_dataframe.to_sql(table_name, self.connection, if_exists='replace', index=False)
            print(f"Sum of errors data stored successfully in {table_name}")
        except Exception as e:
            print(f"Error storing sum of errors data in {table_name}: {e}")


    def create_model_properties_table(self):
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS model_properties (
            id INTEGER PRIMARY KEY,
            uwi_id INTEGER,
            economic_limit_type TEXT DEFAULT NULL,
            b_factor_gas REAL DEFAULT NULL,
            min_dec_gas REAL DEFAULT NULL,
            b_factor_oil REAL DEFAULT NULL,
            min_dec_oil REAL DEFAULT NULL,
            economic_limit_date TEXT DEFAULT NULL,
            oil_price REAL DEFAULT NULL,
            gas_price REAL DEFAULT NULL,
            oil_price_dif REAL DEFAULT NULL,
            gas_price_dif REAL DEFAULT NULL,
            discount_rate REAL DEFAULT NULL,
            tax_rate REAL DEFAULT NULL,
            capital_expenditures REAL DEFAULT NULL,
            operating_expenditures REAL DEFAULT NULL,
            net_price_oil REAL DEFAULT NULL,
            net_price_gas REAL DEFAULT NULL,
            FOREIGN KEY (uwi_id) REFERENCES uwis(id)
        )
        """
        try:
            self.cursor.execute(create_table_sql)
            self.connection.commit()
            print("Model properties table created successfully.")
        except sqlite3.Error as e:
            print("Error creating model properties table:", e)

    def store_model_data(self, model_data_dataframe):
        print(model_data_dataframe)
        try:
            self.connect()
            model_data_dataframe.to_sql('model_properties', self.connection, if_exists='replace', index=False)
            print("Model data stored successfully in model_properties table.")
        except Exception as e:
            print(f"Error storing model data: {e}")

    def retrieve_prod_rates_all(self, current_uwi=None):
        try:
            # Get column names
            self.cursor.execute("PRAGMA table_info(prod_rates_all)")
            columns = [column[1] for column in self.cursor.fetchall()]

            if current_uwi:
                # Select data for the specified UWI
                query = "SELECT * FROM prod_rates_all WHERE UWI = ?"
                self.cursor.execute(query, (current_uwi,))
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


    def retrieve_model_data(self):
        try:
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

    def retrieve_sum_of_errors(self):
        try:
            self.cursor.execute("SELECT * FROM sum_of_errors")
            rows = self.cursor.fetchall()
            column_names = [description[0] for description in self.cursor.description]
            df = pd.DataFrame(rows, columns=column_names)
            return df
        except sqlite3.Error as e:
            print("Error retrieving sum of errors:", e)
            return None

    def get_uwis(self):
        try:
            self.cursor.execute("SELECT uwi FROM uwis")
            uwis = self.cursor.fetchall()
            return [uwi[0] for uwi in uwis]
        except sqlite3.Error as e:
            print("Error retrieving UWIs:", e)
            return []

    def retrieve_tab2(self, today_date):
        try:
            self.cursor.execute("SELECT date, UWI, discounted_revenue FROM prod_rates_all WHERE date >= ?", (today_date,))
            rows = self.cursor.fetchall()
            return rows
        except sqlite3.Error as e:
            print("Error retrieving data from database:", e)
            return None

    def retrieve_model_properties(self, current_uwi):
        print("fuck this",current_uwi)
        try:
            query = "SELECT * FROM model_properties WHERE UWI = ?"
            self.cursor.execute(query, (current_uwi,))
            print(current_uwi)
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

    def retrieve_error_row(self, current_uwi):
        try:
            query = "SELECT * FROM sum_of_errors WHERE UWI = ?"
            self.cursor.execute(query, (current_uwi,))
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






    def update_model_properties(self, df_model_properties):
      

        try:
            # Extract UWI from the DataFrame
            uwi = df_model_properties['UWI'].iloc[0]
            self.connect()
            # Generate the SQL UPDATE statement
            update_sql = f"UPDATE model_properties SET {', '.join([f'{col} = ?' for col in df_model_properties.columns if col != 'UWI'])} WHERE UWI = ?"

            # Extract the values to be updated from the DataFrame and perform data type conversion
            values = []
            for col in df_model_properties.columns:
                if col != 'UWI':
                    value = df_model_properties[col].iloc[0]
                    # Perform data type conversion based on the data types expected by SQLite
                    if isinstance(value, pd.Timestamp):  # Convert datetime64[ns] to string
                        value = value.date().strftime('%Y-%m-%d') # Extract date part only
                    elif isinstance(value, pd.Series):  # Extract scalar value from pandas Series
                        value = value.item()
                    # Append the converted value to the values list
                    values.append(value)

            values.append(uwi)

            # Execute the UPDATE statement
            self.cursor.execute(update_sql, values)
            self.connection.commit()
            print(f"Model properties updated successfully for UWI {uwi}.")

        except sqlite3.Error as e:
            print("Error updating model properties:", e)





    def update_uwi_errors(self, dataframe):
   
        # Assuming your DataFrame is named df
        for index, row in dataframe.iterrows():
            # Extract the values from the DataFrame
            uwi = row['UWI']
            sum_error_oil = row['sum_error_oil']
            sum_error_gas = row['sum_error_gas']
    
            # Update the corresponding row in the SQLite table
            self.cursor.execute("UPDATE sum_of_errors SET sum_error_oil = ?, sum_error_gas = ? WHERE UWI = ?", (sum_error_oil, sum_error_gas, uwi))

        # Commit the changes
        self.commit()



    def update_uwi_prod_rates(self, df_production_rates):
        try:

            self.connect()
 
            # Extract the UWI from the DataFrame
            uwi = df_production_rates['UWI'].iloc[0]
            print(uwi)

            # Construct and execute an SQL DELETE statement
            delete_statement = f"DELETE FROM prod_rates_all WHERE UWI = '{uwi}';"
            self.cursor.execute(delete_statement)
            print(delete_statement)
            self.connection.commit()
            df_production_rates['date'] = df_production_rates['date'].dt.strftime('%Y-%m-%d')

            for index, row in df_production_rates.iterrows():
                query = """
                INSERT INTO prod_rates_all (UWI, date, gas_volume, q_gas, error_gas, oil_volume, q_oil, error_oil, cumulative_oil_volume, cumulative_gas_volume, total_revenue, discounted_revenue, gas_revenue, oil_revenue)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """
                row = row.where(pd.notna(row), None)

                self.cursor.execute(query, (
                    row['UWI'], row['date'], row['gas_volume'], row['q_gas'],
                    row['error_gas'], row['oil_volume'], row['q_oil'], row['error_oil'],
                    row['cumulative_oil_volume'], row['cumulative_gas_volume'],
                    row['total_revenue'], row['discounted_revenue'], row['gas_revenue'], row['oil_revenue']
                ))

            # Commit the transaction
            self.connection.commit()
            print(f"Data updated successfully in prod_rates_all for UWI {uwi}")
        except Exception as e:
            # Rollback the transaction in case of an error
            self.connection.rollback()
            print(f"Error updating data in prod_rates_all: {e}")




    def retrieve_prod_rates_by_uwi(self, current_uwi=None):
        try:
            # Get column names
            self.cursor.execute("PRAGMA table_info(prod_rates_all)")
            columns = [column[1] for column in self.cursor.fetchall()]

            if current_uwi:
                # Select data for the specified UWI
                query = "SELECT * FROM prod_rates_all WHERE UWI = ?"
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


    def get_model_status(self, current_uwi, model_type):
        # Query the database to get the model status for the specified type and UWI
        try:
            query = f"SELECT {model_type}_model_status FROM model_properties WHERE UWI = ?"
            self.cursor.execute(query, (current_uwi,))
            result = self.cursor.fetchone()
            if result:
                return result[0]  # Assuming the model status is the first column in the result
            else:
                return None
        except sqlite3.Error as e:
            print(f"Error retrieving {model_type} model status:", e)
            return None


    def update_model_status(self, current_uwi, new_status, model_type):
        # Update the model status in the database for the specified type and UWI
        try:
            query = f"UPDATE model_properties SET {model_type}_model_status = ? WHERE UWI = ?"
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
            # SQL query that deletes rows where the UWI matches the given uwi
            query = f"DELETE FROM {table} WHERE UWI = ?"
            self.cursor.execute(query, (uwi,))  # Execute the query with the UWI parameter

            # Commit the changes to the database
        self.connection.commit()
