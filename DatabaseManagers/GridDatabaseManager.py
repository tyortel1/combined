import sqlite3
import pandas as pd
import logging
import numpy as np
import os

class GridDatabaseManager:
    """
    A database manager class for handling grid data, including storage and retrieval of
    grid information such as name, color, type (depth or attribute), and units.
    """
    def __init__(self, db_path):
        """
        Initialize the GridDatabaseManager with a database path.
        
        Args:
            db_path (str): Path to the SQLite database file
        """
        self.db_path = db_path
        self.connection = None
        self.cursor = None
        
        # Create database directory if it doesn't exist
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        # Initialize database tables
        self.connect()
        self.create_grid_tables()
        self.disconnect()

    def connect(self):
        """Establish a connection to the SQLite database."""
        try:
            self.connection = sqlite3.connect(self.db_path)
            self.cursor = self.connection.cursor()
            return True
        except sqlite3.Error as e:
            print(f"Error connecting to database: {e}")
            return False

    def disconnect(self):
        """Close the database connection if it exists."""
        if self.connection:
            self.connection.close()
            self.connection = None
            self.cursor = None

    def create_grid_tables(self):
        """Create the necessary tables for storing grid information if they don't exist."""
        # Ensure connection is established
        if not self.connect():
            print("Failed to connect to database")
            return False
    
        try:
            # Main grid information table
            create_grids_table_sql = """
            CREATE TABLE IF NOT EXISTS grids (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                type TEXT NOT NULL CHECK(type IN ('Depth', 'Attribute')),
                unit TEXT NOT NULL CHECK(unit IN ('Meters', 'Feet')),
                color_hex TEXT,
                min_x REAL,
                max_x REAL,
                min_y REAL,
                max_y REAL,
                min_z REAL,
                max_z REAL,
                bin_size_x REAL,
                bin_size_y REAL,
                hdf5_location TEXT,
                date_created TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
    
            # Execute table creation
            self.cursor.execute(create_grids_table_sql)
    
            self.connection.commit()
           
            return True
    
        except sqlite3.Error as e:
            print(f"Error creating grid tables: {e}")
            self.connection.rollback()
            return False
    
        finally:
            # Always disconnect
            self.disconnect()

    def add_grid(self, name, grid_type, unit, color_hex=None, grid_info=None, hdf5_location=None):
        """
        Add a new grid to the database.
    
        Args:
            name (str): Name of the grid
            grid_type (str): Type of grid ('Depth' or 'Attribute')
            unit (str): Unit of measurement ('Meters' or 'Feet')
            color_hex (str, optional): Hex color code for the grid
            grid_info (dict, optional): Dictionary containing grid metadata like min_x, max_x, etc.
            hdf5_location (str, optional): Path to the HDF5 file storing the grid data
    
        Returns:
            int: ID of the newly added grid, or None if the operation failed
        """
        self.connect()
        try:
            # Validate inputs
            if grid_type not in ('Depth', 'Attribute'):
                raise ValueError("Grid type must be 'Depth' or 'Attribute'")
        
            if unit not in ('Meters', 'Feet'):
                raise ValueError("Unit must be 'Meters' or 'Feet'")
        
            # Prepare grid info values
            grid_info = grid_info or {}
            min_x = grid_info.get('min_x')
            max_x = grid_info.get('max_x')
            min_y = grid_info.get('min_y')
            max_y = grid_info.get('max_y')
            min_z = grid_info.get('min_z')
            max_z = grid_info.get('max_z')
            bin_size_x = grid_info.get('bin_size_x')
            bin_size_y = grid_info.get('bin_size_y')
        
            # Insert grid into database
            insert_sql = """
            INSERT INTO grids (name, type, unit, color_hex, min_x, max_x, min_y, max_y, min_z, max_z, bin_size_x, bin_size_y, hdf5_location)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
        
            self.cursor.execute(insert_sql, (
                name, grid_type, unit, color_hex,
                min_x, max_x, min_y, max_y, min_z, max_z,
                bin_size_x, bin_size_y, hdf5_location
            ))
        
            self.connection.commit()
            grid_id = self.cursor.lastrowid
            print(f"Grid '{name}' added successfully with ID {grid_id} and HDF5 location {hdf5_location}.")
            return grid_id
        
        except sqlite3.IntegrityError:
            print(f"Grid with name '{name}' already exists.")
            self.connection.rollback()
            return None
        
        except Exception as e:
            print(f"Error adding grid: {e}")
            self.connection.rollback()
            return None
        
        finally:
            self.disconnect()


    def delete_grid(self, grid_id=None, grid_name=None):
        """
        Delete a grid and its associated data.
    
        Args:
            grid_id (int, optional): ID of the grid to delete
            grid_name (str, optional): Name of the grid to delete
        
        Note: Either grid_id or grid_name must be provided
        
        Returns:
            bool: True if successful, False otherwise
        """
        if grid_id is None and grid_name is None:
            print("Either grid_id or grid_name must be provided.")
            return False
        
        self.connect()
        try:
            # If grid_name is provided, get the corresponding grid_id
            if grid_id is None:
                self.cursor.execute("SELECT id FROM grids WHERE name = ?", (grid_name,))
                result = self.cursor.fetchone()
                if result:
                    grid_id = result[0]
                else:
                    print(f"Grid with name '{grid_name}' not found.")
                    return False
        
            # Delete the grid
            self.cursor.execute("DELETE FROM grids WHERE id = ?", (grid_id,))
        
            self.connection.commit()
        
            if self.cursor.rowcount > 0:
                print(f"Grid with ID {grid_id} deleted successfully.")
                return True
            else:
                print(f"Grid with ID {grid_id} not found.")
                return False
            
        except Exception as e:
            print(f"Error deleting grid: {e}")
            self.connection.rollback()
            return False
        
        finally:
            self.disconnect()

    def update_grid_hdf5_location(self, grid_id=None, grid_name=None, hdf5_location=None):
        """
        Update the HDF5 location of a grid.
    
        Args:
            grid_id (int, optional): ID of the grid
            grid_name (str, optional): Name of the grid
            hdf5_location (str): Path to the HDF5 file
        
        Note: Either grid_id or grid_name must be provided
        
        Returns:
            bool: True if successful, False otherwise
        """
        if grid_id is None and grid_name is None:
            print("Either grid_id or grid_name must be provided.")
            return False
        
        if hdf5_location is None:
            print("HDF5 location must be provided.")
            return False
        
        self.connect()
        try:
            # If grid_name is provided, get the corresponding grid_id
            if grid_id is None:
                self.cursor.execute("SELECT id FROM grids WHERE name = ?", (grid_name,))
                result = self.cursor.fetchone()
                if result:
                    grid_id = result[0]
                else:
                    print(f"Grid with name '{grid_name}' not found.")
                    return False
        
            # Update the HDF5 location
            self.cursor.execute(
                "UPDATE grids SET hdf5_location = ? WHERE id = ?",
                (hdf5_location, grid_id)
            )
        
            self.connection.commit()
        
            if self.cursor.rowcount > 0:
                print(f"Updated HDF5 location for grid ID {grid_id} to {hdf5_location}.")
                return True
            else:
                print(f"Grid with ID {grid_id} not found.")
                return False
            
        except Exception as e:
            print(f"Error updating grid HDF5 location: {e}")
            self.connection.rollback()
            return False
        
        finally:
            self.disconnect()

    def _update_grid_metadata(self, grid_id, data_points):
        """
        Update grid metadata based on the data points.
        
        Args:
            grid_id (int): ID of the grid to update
            data_points (list): List of (x, y, z) tuples
        """
        try:
            # Extract x, y, z values
            x_values = [point[0] for point in data_points]
            y_values = [point[1] for point in data_points]
            z_values = [point[2] for point in data_points]
            
            # Calculate min/max values
            min_x = min(x_values)
            max_x = max(x_values)
            min_y = min(y_values)
            max_y = max(y_values)
            min_z = min(z_values)
            max_z = max(z_values)
            
            # Try to calculate bin size (assuming regular grid)
            unique_x = sorted(set(x_values))
            unique_y = sorted(set(y_values))
            
            bin_size_x = None
            bin_size_y = None
            
            if len(unique_x) > 1:
                x_diffs = [unique_x[i+1] - unique_x[i] for i in range(len(unique_x)-1)]
                bin_size_x = min(x_diffs)
                
            if len(unique_y) > 1:
                y_diffs = [unique_y[i+1] - unique_y[i] for i in range(len(unique_y)-1)]
                bin_size_y = min(y_diffs)
            
            # Update grid metadata
            update_sql = """
            UPDATE grids
            SET min_x = ?, max_x = ?, min_y = ?, max_y = ?, min_z = ?, max_z = ?,
                bin_size_x = ?, bin_size_y = ?
            WHERE id = ?
            """
            
            self.cursor.execute(update_sql, (
                min_x, max_x, min_y, max_y, min_z, max_z,
                bin_size_x, bin_size_y, grid_id
            ))
            
        except Exception as e:
            print(f"Error updating grid metadata: {e}")
            raise

    def get_grid_by_id(self, grid_id):
        """
        Get grid information by ID.
        
        Args:
            grid_id (int): ID of the grid to retrieve
            
        Returns:
            dict: Grid information as a dictionary, or None if not found
        """
        self.connect()
        try:
            self.cursor.execute("SELECT * FROM grids WHERE id = ?", (grid_id,))
            result = self.cursor.fetchone()
            
            if result:
                columns = [column[0] for column in self.cursor.description]
                return dict(zip(columns, result))
            else:
                print(f"Grid with ID {grid_id} not found.")
                return None
                
        except Exception as e:
            print(f"Error retrieving grid: {e}")
            return None
            
        finally:
            self.disconnect()

    def get_grid_by_name(self, grid_name):
        """
        Get grid information by name.
        
        Args:
            grid_name (str): Name of the grid to retrieve
            
        Returns:
            dict: Grid information as a dictionary, or None if not found
        """
        self.connect()
        try:
            self.cursor.execute("SELECT * FROM grids WHERE name = ?", (grid_name,))
            result = self.cursor.fetchone()
            
            if result:
                columns = [column[0] for column in self.cursor.description]
                return dict(zip(columns, result))
            else:
                print(f"Grid with name '{grid_name}' not found.")
                return None
                
        except Exception as e:
            print(f"Error retrieving grid: {e}")
            return None
            
        finally:
            self.disconnect()

    def get_all_grids(self, grid_type=None):
        """
        Get all grids, optionally filtered by type.
        
        Args:
            grid_type (str, optional): Filter by grid type ('Depth' or 'Attribute')
            
        Returns:
            list: List of dictionaries containing grid information
        """
        self.connect()
        try:
            if grid_type:
                query = "SELECT * FROM grids WHERE type = ?"
                self.cursor.execute(query, (grid_type,))
            else:
                query = "SELECT * FROM grids"
                self.cursor.execute(query)
                
            results = self.cursor.fetchall()
            
            if not results:
                return []
                
            columns = [column[0] for column in self.cursor.description]
            return [dict(zip(columns, row)) for row in results]
                
        except Exception as e:
            print(f"Error retrieving grids: {e}")
            return []
            
        finally:
            self.disconnect()


    def update_grid_color(self, grid_id=None, grid_name=None, color_hex=None):
        """
        Update the color of a grid.
        
        Args:
            grid_id (int, optional): ID of the grid
            grid_name (str, optional): Name of the grid
            color_hex (str): Hex color code
            
        Note: Either grid_id or grid_name must be provided
            
        Returns:
            bool: True if successful, False otherwise
        """
        if grid_id is None and grid_name is None:
            print("Either grid_id or grid_name must be provided.")
            return False
            
        if color_hex is None:
            print("Color hex value must be provided.")
            return False
            
        self.connect()
        try:
            # If grid_name is provided, get the corresponding grid_id
            if grid_id is None:
                self.cursor.execute("SELECT id FROM grids WHERE name = ?", (grid_name,))
                result = self.cursor.fetchone()
                if result:
                    grid_id = result[0]
                else:
                    print(f"Grid with name '{grid_name}' not found.")
                    return False
            
            # Update the color
            self.cursor.execute(
                "UPDATE grids SET color_hex = ? WHERE id = ?",
                (color_hex, grid_id)
            )
            
            self.connection.commit()
            
            if self.cursor.rowcount > 0:
                print(f"Updated color for grid ID {grid_id} to {color_hex}.")
                return True
            else:
                print(f"Grid with ID {grid_id} not found.")
                return False
                
        except Exception as e:
            print(f"Error updating grid color: {e}")
            self.connection.rollback()
            return False
            
        finally:
            self.disconnect()

    def update_grid_unit(self, grid_id=None, grid_name=None, unit=None):
        """
        Update the unit of a grid.
        
        Args:
            grid_id (int, optional): ID of the grid
            grid_name (str, optional): Name of the grid
            unit (str): New unit ('Meters' or 'Feet')
            
        Note: Either grid_id or grid_name must be provided
            
        Returns:
            bool: True if successful, False otherwise
        """
        if grid_id is None and grid_name is None:
            print("Either grid_id or grid_name must be provided.")
            return False
            
        if unit not in ('Meters', 'Feet'):
            print("Unit must be 'Meters' or 'Feet'.")
            return False
            
        self.connect()
        try:
            # If grid_name is provided, get the corresponding grid_id
            if grid_id is None:
                self.cursor.execute("SELECT id FROM grids WHERE name = ?", (grid_name,))
                result = self.cursor.fetchone()
                if result:
                    grid_id = result[0]
                else:
                    print(f"Grid with name '{grid_name}' not found.")
                    return False
            
            # Update the unit
            self.cursor.execute(
                "UPDATE grids SET unit = ? WHERE id = ?",
                (unit, grid_id)
            )
            
            self.connection.commit()
            
            if self.cursor.rowcount > 0:
                print(f"Updated unit for grid ID {grid_id} to {unit}.")
                return True
            else:
                print(f"Grid with ID {grid_id} not found.")
                return False
                
        except Exception as e:
            print(f"Error updating grid unit: {e}")
            self.connection.rollback()
            return False
            
        finally:
            self.disconnect()

    def get_grid_info_dataframe(self, grid_type=None):
        """
        Get all grids as a pandas DataFrame formatted for display and visualization.
    
        Args:
            grid_type (str, optional): Filter by grid type ('Depth' or 'Attribute')
            
        Returns:
            pandas.DataFrame: DataFrame containing grid information with properly formatted columns
        """
        self.connect()
        try:
            # Get all grids from the database
            grids = self.get_all_grids(grid_type=grid_type)
        
            if not grids:
                return pd.DataFrame()
            
            # Convert to the expected DataFrame format
            grid_info = []
            for grid in grids:
                # Convert hex color to RGB tuple
                color_rgb = self.hex_to_rgb(grid['color_hex']) if grid['color_hex'] else (0, 0, 0)
            
                grid_info.append({
                    'Grid': grid['name'],
                    'Type': grid['type'],
                    'min_x': grid['min_x'],
                    'max_x': grid['max_x'],
                    'min_y': grid['min_y'],
                    'max_y': grid['max_y'],
                    'min_z': grid['min_z'],
                    'max_z': grid['max_z'],
                    'bin_size_x': grid['bin_size_x'],
                    'bin_size_y': grid['bin_size_y'],
                    'Color (RGB)': color_rgb
                })
        
            return pd.DataFrame(grid_info)
                
        except Exception as e:
            print(f"Error creating grid info DataFrame: {e}")
            return pd.DataFrame()
        
        finally:
            self.disconnect()
        
    def hex_to_rgb(self, hex_color):
        """Convert hex color string to RGB tuple"""
        if not hex_color:
            return (0, 0, 0)
        # Remove '#' if present
        hex_color = hex_color.lstrip('#')
        # Convert hex to RGB
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))


 
