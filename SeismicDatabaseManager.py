import sqlite3
import logging
from datetime import datetime

class SeismicDatabaseManager:
    def __init__(self, db_path):
        self.db_path = db_path
        self.connection = None
        self.cursor = None
        
        # Set up logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

    def connect(self):
        """Establish database connection"""
        self.connection = sqlite3.connect(self.db_path)
        self.cursor = self.connection.cursor()

    def disconnect(self):
        """Close database connection"""
        if self.connection:
            self.connection.close()

    def create_tables(self):
        """Create necessary tables for seismic data management"""
        self.connect()
    
        # Main seismic files table
        create_seismic_table_sql = """
        CREATE TABLE IF NOT EXISTS seismic_files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,                      -- Added name field
            original_segy_path TEXT UNIQUE NOT NULL,
            hdf5_path TEXT UNIQUE NOT NULL,
            format TEXT NOT NULL,
            datum REAL NOT NULL,
            sample_rate REAL NOT NULL,
            num_samples INTEGER NOT NULL,
            creation_date TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            last_modified TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            CHECK (sample_rate > 0),
            CHECK (num_samples > 0)
        )
        """
    
        # Geometry information table
        create_geometry_table_sql = """
        CREATE TABLE IF NOT EXISTS seismic_geometry (
            seismic_id INTEGER PRIMARY KEY,
            inline_min INTEGER NOT NULL,
            inline_max INTEGER NOT NULL,
            xline_min INTEGER NOT NULL,
            xline_max INTEGER NOT NULL,
            x_min REAL NOT NULL,
            x_max REAL NOT NULL,
            y_min REAL NOT NULL,
            y_max REAL NOT NULL,
            CHECK (inline_max > inline_min),
            CHECK (xline_max > xline_min),
            CHECK (x_max > x_min),
            CHECK (y_max > y_min),
            FOREIGN KEY (seismic_id) REFERENCES seismic_files (id)
                ON DELETE CASCADE
        )
        """

        try:
            # Create tables
            self.cursor.execute(create_seismic_table_sql)
            self.cursor.execute(create_geometry_table_sql)
        
            # Create indices for faster lookups
            self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_name ON seismic_files(name)")  # Added index for name
            self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_hdf5_path ON seismic_files(hdf5_path)")
            self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_segy_path ON seismic_files(original_segy_path)")
            self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_format ON seismic_files(format)")
        
            self.connection.commit()
            self.logger.info("Seismic database tables created successfully")
        
        except sqlite3.Error as e:
            self.logger.error(f"Error creating tables: {e}")
            self.connection.rollback()
        finally:
            self.disconnect()

    def save_seismic_file(self, file_info):
        """
        Save seismic file information to database
    
        Args:
            file_info (dict): Dictionary containing:
                - name (str): Name of the seismic file
                - original_segy_path (str): Path to original SEG-Y file
                - hdf5_path (str): Path to HDF5 file
                - format (str): SEG-Y format type
                - datum (float): Seismic datum
                - sample_rate (float): Sample rate in ms
                - num_samples (int): Number of samples per trace
                - geometry (dict): Optional dictionary containing:
                    - inline_min/max (int): Inline range
                    - xline_min/max (int): Crossline range
                    - x_min/max (float): X coordinate range
                    - y_min/max (float): Y coordinate range
        """
        self.connect()
    
        try:
            # Insert main seismic file info
            insert_file_sql = """
            INSERT INTO seismic_files (
                name, original_segy_path, hdf5_path, format, datum,
                sample_rate, num_samples, creation_date, last_modified
            ) VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))
            """
        
            file_values = [
                file_info['name'],
                file_info['original_segy_path'],
                file_info['hdf5_path'],
                file_info['format'],
                file_info['datum'],
                file_info['sample_rate'],
                file_info['num_samples']
            ]
            
            self.cursor.execute(insert_file_sql, file_values)
            seismic_id = self.cursor.lastrowid
            
            # Insert geometry info if provided
            if 'geometry' in file_info:
                geom = file_info['geometry']
                insert_geom_sql = """
                INSERT INTO seismic_geometry (
                    seismic_id, inline_min, inline_max, xline_min, xline_max,
                    x_min, x_max, y_min, y_max
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """
                
                geom_values = [
                    seismic_id,
                    geom.get('inline_min'),
                    geom.get('inline_max'),
                    geom.get('xline_min'),
                    geom.get('xline_max'),
                    geom.get('x_min'),
                    geom.get('x_max'),
                    geom.get('y_min'),
                    geom.get('y_max')
                ]
                
                self.cursor.execute(insert_geom_sql, geom_values)
            
            self.connection.commit()
            self.logger.info(f"Seismic file info saved successfully for {file_info['original_segy_path']}")
            
        except sqlite3.Error as e:
            self.logger.error(f"Error saving seismic file info: {e}")
            self.connection.rollback()
        finally:
            self.disconnect()

    def get_seismic_file_info(self, name=None, hdf5_path=None, segy_path=None):
        """Retrieve seismic file information including geometry"""
        self.connect()
    
        try:
            query = """
            SELECT 
                f.*, 
                g.inline_min, g.inline_max, g.xline_min, g.xline_max,
                g.x_min, g.x_max, g.y_min, g.y_max
            FROM seismic_files f
            LEFT JOIN seismic_geometry g ON f.id = g.seismic_id
            WHERE """
        
            if name:
                query += "f.name = ?"
                param = name
            elif hdf5_path:
                query += "f.hdf5_path = ?"
                param = hdf5_path
            elif segy_path:
                query += "f.original_segy_path = ?"
                param = segy_path
            else:
                raise ValueError("Must provide either name, hdf5_path or segy_path")
                
            self.cursor.execute(query, (param,))
            result = self.cursor.fetchone()
            
            if result:
                # Convert to dictionary
                columns = [description[0] for description in self.cursor.description]
                return dict(zip(columns, result))
            return None
            
        except sqlite3.Error as e:
            self.logger.error(f"Error retrieving seismic file info: {e}")
            return None
        finally:
            self.disconnect()

    def list_all_seismic_files(self):
        """List all seismic files in the database for debugging"""
        self.connect()
    
        try:
            query = "SELECT id, name, hdf5_path, original_segy_path FROM seismic_files"
            self.cursor.execute(query)
        
            results = self.cursor.fetchall()
        
            print("All Seismic Files in Database:")
            for row in results:
                print(f"ID: {row[0]}, Name: {row[1]}, HDF5 Path: {row[2]}, SEG-Y Path: {row[3]}")
        
            return results
    
        except sqlite3.Error as e:
            print(f"Error listing seismic files: {e}")
            return []
        finally:
            self.disconnect()


    def delete_seismic_file(self, name=None, hdf5_path=None):
        """
        Delete seismic file entry and associated geometry
    
        Args:
            name (str, optional): Name of the seismic file to delete
            hdf5_path (str, optional): HDF5 path of the seismic file to delete
        
        Note:
            Must provide either name or hdf5_path
        """
        self.connect()
    
        try:
            if not name and not hdf5_path:
                raise ValueError("Must provide either name or hdf5_path")
            
            where_clause = "name = ?" if name else "hdf5_path = ?"
            param = name if name else hdf5_path
            
            # First delete geometry (due to foreign key constraint)
            self.cursor.execute(f"""
                DELETE FROM seismic_geometry 
                WHERE seismic_id = (
                    SELECT id FROM seismic_files WHERE {where_clause}
                )
            """, (param,))
        
            # Then delete main file entry
            self.cursor.execute(f"""
                DELETE FROM seismic_files 
                WHERE {where_clause}
            """, (param,))
        
            self.connection.commit()
        
            if self.cursor.rowcount == 0:
                self.logger.warning(f"No seismic file found with {'name' if name else 'HDF5 path'}: {param}")
            else:
                self.logger.info(f"Successfully deleted seismic file info for {'name' if name else 'HDF5 path'}: {param}")
                
        except sqlite3.Error as e:
            self.logger.error(f"Error deleting seismic file info: {e}")
            self.connection.rollback()
        finally:
            self.disconnect()

    #def update_seismic_file(self, name=None, hdf5_path=None, updates):
    #    """
    #    Update seismic file information
    
    #    Args:
    #        name (str, optional): Name of the seismic file to update
    #        hdf5_path (str, optional): HDF5 path of the seismic file to update
    #        updates (dict): Dictionary containing fields to update. Can include:
    #            - name: New name for the file
    #            - original_segy_path: New SEG-Y file path
    #            - hdf5_path: New HDF5 file path
    #            - format: New format type
    #            - datum: New datum value
    #            - sample_rate: New sample rate
    #            - num_samples: New number of samples
    #            - geometry updates:
    #                - inline_min/max: New inline range
    #                - xline_min/max: New crossline range
    #                - x_min/max: New X coordinate range
    #                - y_min/max: New Y coordinate range
                
    #    Note:
    #        Must provide either name or hdf5_path
    #    """
    #    self.connect()

    #    if not name and not hdf5_path:
    #        raise ValueError("Must provide either name or hdf5_path")
    
    #    try:
    #        # First verify the file exists
    #        where_clause = "name = ?" if name else "hdf5_path = ?"
    #        param = name if name else hdf5_path
        
    #        self.cursor.execute(f"""
    #            SELECT id FROM seismic_files WHERE {where_clause}
    #        """, (param,))
        
    #        result = self.cursor.fetchone()
    #        if not result:
    #            self.logger.warning(f"No seismic file found with {'name' if name else 'HDF5 path'}: {param}")
    #            return
            
    #        seismic_id = result[0]
        
    #        # Separate geometry updates from main file updates
    #        geom_updates = {}
    #        file_updates = {}
        
    #        for key, value in updates.items():
    #            if key in ['inline_min', 'inline_max', 'xline_min', 'xline_max',
    #                      'x_min', 'x_max', 'y_min', 'y_max']:
    #                geom_updates[key] = value
    #            else:
    #                file_updates[key] = value

    #        # Update main file info if needed
    #        if file_updates:
    #            set_clause = ", ".join([f"{key} = ?" for key in file_updates.keys()])
    #            set_clause += ", last_modified = datetime('now')"
            
    #            sql = f"""
    #            UPDATE seismic_files 
    #            SET {set_clause}
    #            WHERE id = ?
    #            """
            
    #            values = list(file_updates.values()) + [seismic_id]
    #            self.cursor.execute(sql, values)

    #        # Update geometry if needed
    #        if geom_updates:
    #            # Check if geometry record exists
    #            self.cursor.execute("""
    #                SELECT 1 FROM seismic_geometry WHERE seismic_id = ?
    #            """, (seismic_id,))
            
    #            if self.cursor.fetchone():
    #                # Update existing geometry
    #                set_clause = ", ".join([f"{key} = ?" for key in geom_updates.keys()])
    #                sql = f"""
    #                UPDATE seismic_geometry 
    #                SET {set_clause}
    #                WHERE seismic_id = ?
    #                """
    #                values = list(geom_updates.values()) + [seismic_id]
    #                self.cursor.execute(sql, values)
    #            else:
    #                # Get all geometry columns
    #                self.cursor.execute("PRAGMA table_info(seismic_geometry)")
    #                columns = [row[1] for row in self.cursor.fetchall()]
    #                columns.remove('seismic_id')  # Handle seismic_id separately
                
    #                # Prepare insert with all columns and appropriate values
    #                fields = ['seismic_id'] + columns
    #                values = [seismic_id]
                
    #                # Add values for each column, using updates if provided or 0 as default
    #                for col in columns:
    #                    values.append(geom_updates.get(col, 0))
                
    #                placeholders = ','.join(['?' for _ in range(len(fields))])
    #                sql = f"""
    #                INSERT INTO seismic_geometry 
    #                ({','.join(fields)})
    #                VALUES ({placeholders})
    #                """
    #                self.cursor.execute(sql, values)

    #        self.connection.commit()
    #        self.logger.info(f"Successfully updated seismic file info for {'name' if name else 'HDF5 path'}: {param}")
                
    #    except sqlite3.Error as e:
    #        self.logger.error(f"Error updating seismic file info: {e}")
    #        self.connection.rollback()
    #    finally:
    #        self.disconnect()


    def get_all_seismic_files(self):
        """
        Retrieve all seismic file information including geometry
    
        Returns:
            list: List of dictionaries containing seismic file information.
                 Each dictionary contains:
                    - id (int): Database ID
                    - name (str): Seismic file name
                    - original_segy_path (str): Path to original SEG-Y file
                    - hdf5_path (str): Path to HDF5 file
                    - format (str): SEG-Y format type
                    - datum (float): Seismic datum
                    - sample_rate (float): Sample rate in ms
                    - num_samples (int): Number of samples per trace
                    - creation_date (str): Creation timestamp
                    - last_modified (str): Last modification timestamp
                    - geometry (dict): Dictionary containing:
                        - inline_min/max (int): Inline range
                        - xline_min/max (int): Crossline range
                        - x_min/max (float): X coordinate range
                        - y_min/max (float): Y coordinate range
        
            Empty list is returned if no files found or in case of error.
        """
        self.connect()

        try:
            query = """
            SELECT 
                f.id,
                f.name,
                f.original_segy_path,
                f.hdf5_path,
                f.format,
                f.datum,
                f.sample_rate,
                f.num_samples,
                f.creation_date,
                f.last_modified,
                g.inline_min,
                g.inline_max,
                g.xline_min,
                g.xline_max,
                g.x_min,
                g.x_max,
                g.y_min,
                g.y_max
            FROM seismic_files f
            LEFT JOIN seismic_geometry g ON f.id = g.seismic_id
            ORDER BY f.name, f.creation_date
            """

            self.cursor.execute(query)
            results = self.cursor.fetchall()

            seismic_files = []
            if results:
                # Get column names
                columns = [description[0] for description in self.cursor.description]

                # Convert each row to a dictionary
                for row in results:
                    file_info = dict(zip(columns, row))
                
                    # Extract geometry fields into a nested dictionary
                    geometry_fields = ['inline_min', 'inline_max', 'xline_min', 'xline_max',
                                     'x_min', 'x_max', 'y_min', 'y_max']
                
                    # Only include geometry if at least one field is not None
                    if any(file_info.get(field) is not None for field in geometry_fields):
                        file_info['geometry'] = {
                            field: file_info.pop(field)
                            for field in geometry_fields
                        }
                    else:
                        # Remove None geometry fields and set geometry to None
                        for field in geometry_fields:
                            file_info.pop(field)
                        file_info['geometry'] = None

                    seismic_files.append(file_info)

                self.logger.info(f"Successfully retrieved {len(seismic_files)} seismic files")
            else:
                self.logger.info("No seismic files found in database")

            return seismic_files

        except sqlite3.Error as e:
            self.logger.error(f"Error retrieving seismic files: {e}")
            return []
        finally:
            self.disconnect()
