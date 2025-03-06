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
            name TEXT NOT NULL,                      -- Name of the seismic file/project
            original_segy_path TEXT,                 -- Path to original SEGY (can be NULL for multi-attribute projects)
            hdf5_path TEXT NOT NULL,                 -- Path to HDF5 file
            format TEXT NOT NULL,                    -- SEG-Y format
            datum REAL NOT NULL,                     -- Seismic datum
            sample_rate REAL NOT NULL,               -- Sample rate in seconds
            num_samples INTEGER NOT NULL,            -- Number of time samples
            is_multi_attribute INTEGER DEFAULT 0,    -- Flag for multi-attribute datasets
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
        
        # New attributes table
        create_attributes_table_sql = """
        CREATE TABLE IF NOT EXISTS seismic_attributes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            seismic_id INTEGER NOT NULL,             -- Reference to parent seismic file
            attribute_name TEXT NOT NULL,            -- Name of the attribute
            original_segy_path TEXT,                 -- Original SEGY file for this attribute
            description TEXT,                        -- Optional description of the attribute
            creation_date TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (seismic_id) REFERENCES seismic_files (id)
                ON DELETE CASCADE,
            UNIQUE (seismic_id, attribute_name)      -- Each attribute name must be unique within a project
        )
        """

        try:
            # Create tables
            self.cursor.execute(create_seismic_table_sql)
            self.cursor.execute(create_geometry_table_sql)
            self.cursor.execute(create_attributes_table_sql)
        
            # Create indices for faster lookups
            self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_name ON seismic_files(name)")
            self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_hdf5_path ON seismic_files(hdf5_path)")
            self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_segy_path ON seismic_files(original_segy_path)")
            self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_format ON seismic_files(format)")
            self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_multi_attribute ON seismic_files(is_multi_attribute)")
            self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_attribute_seismic_id ON seismic_attributes(seismic_id)")
            self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_attribute_name ON seismic_attributes(attribute_name)")
        
            self.connection.commit()
            self.logger.info("Seismic database tables created successfully")
        
        except sqlite3.Error as e:
            self.logger.error(f"Error creating tables: {e}")
            self.connection.rollback()
        finally:
            self.disconnect()

    def save_seismic_file(self, file_info):
        """
        Save single seismic file information to database
    
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
                sample_rate, num_samples, is_multi_attribute, creation_date, last_modified
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 0, datetime('now'), datetime('now'))
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
            
    def save_multi_attribute_seismic(self, file_info):
        """
        Save multi-attribute seismic volume information to database
        
        Args:
            file_info (dict): Dictionary containing:
                - name (str): Project name for the multi-attribute volume
                - hdf5_path (str): Path to HDF5 file
                - format (str): SEG-Y format type
                - datum (float): Seismic datum
                - sample_rate (float): Sample rate in ms
                - num_samples (int): Number of samples per trace
                - attribute_names (list): List of attribute names
                - geometry (dict): Dictionary containing:
                    - inline_min/max (int): Inline range
                    - xline_min/max (int): Crossline range
                    - x_min/max (float): X coordinate range
                    - y_min/max (float): Y coordinate range
        """
        self.connect()
        
        try:
            # Create a transaction
            self.connection.isolation_level = None
            self.cursor.execute("BEGIN TRANSACTION")
            
            # Insert main seismic file info (project entry)
            insert_file_sql = """
            INSERT INTO seismic_files (
                name, hdf5_path, format, datum,
                sample_rate, num_samples, is_multi_attribute,
                creation_date, last_modified
            ) VALUES (?, ?, ?, ?, ?, ?, 1, datetime('now'), datetime('now'))
            """
            
            file_values = [
                file_info['name'],
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
            
            # Insert attributes
            if 'attribute_names' in file_info:
                insert_attr_sql = """
                INSERT INTO seismic_attributes (
                    seismic_id, attribute_name, original_segy_path
                ) VALUES (?, ?, ?)
                """
                
                for attr_name in file_info['attribute_names']:
                    # Get original SEGY path if we have it
                    original_segy = None
                    if 'original_files' in file_info and attr_name in file_info['original_files']:
                        original_segy = file_info['original_files'][attr_name]
                    
                    attr_values = [
                        seismic_id,
                        attr_name,
                        original_segy
                    ]
                    
                    self.cursor.execute(insert_attr_sql, attr_values)
            
            # Commit the transaction
            self.cursor.execute("COMMIT")
            self.logger.info(f"Multi-attribute volume '{file_info['name']}' saved successfully with {len(file_info.get('attribute_names', []))} attributes")
            
        except sqlite3.Error as e:
            self.cursor.execute("ROLLBACK")
            self.logger.error(f"Error saving multi-attribute volume: {e}")
        finally:
            self.connection.isolation_level = ''  # Reset to default
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
                file_info = dict(zip(columns, result))
                
                # If multi-attribute, get attributes
                if file_info.get('is_multi_attribute') == 1:
                    self.cursor.execute("""
                        SELECT attribute_name, original_segy_path, description
                        FROM seismic_attributes
                        WHERE seismic_id = ?
                    """, (file_info['id'],))
                    
                    attributes = []
                    for attr_row in self.cursor.fetchall():
                        attributes.append({
                            'name': attr_row[0],
                            'original_segy_path': attr_row[1],
                            'description': attr_row[2]
                        })
                    
                    file_info['attributes'] = attributes
                
                return file_info
            return None
            
        except sqlite3.Error as e:
            self.logger.error(f"Error retrieving seismic file info: {e}")
            return None
        finally:
            self.disconnect()

    def get_all_seismic_files(self, include_attributes=True):
        """
        Retrieve all seismic file information including geometry
    
        Args:
            include_attributes (bool): Whether to include attribute information for multi-attribute volumes
            
        Returns:
            list: List of dictionaries containing seismic file information.
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
                f.is_multi_attribute,
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
                        
                    # Get attributes for multi-attribute files
                    if include_attributes and file_info.get('is_multi_attribute') == 1:
                        self.cursor.execute("""
                            SELECT attribute_name, original_segy_path, description
                            FROM seismic_attributes
                            WHERE seismic_id = ?
                        """, (file_info['id'],))
                        
                        attributes = []
                        for attr_row in self.cursor.fetchall():
                            attributes.append({
                                'name': attr_row[0],
                                'original_segy_path': attr_row[1],
                                'description': attr_row[2]
                            })
                        
                        file_info['attributes'] = attributes

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
            
            # Due to ON DELETE CASCADE foreign key constraints, we only need to delete
            # from the main table and related records will be automatically deleted
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
            
    def add_attribute_to_multi_volume(self, project_name, attribute_info):
        """
        Add a new attribute to an existing multi-attribute seismic volume
        
        Args:
            project_name (str): Name of the existing multi-attribute project
            attribute_info (dict): Dictionary containing:
                - name (str): Name of the attribute
                - original_segy_path (str, optional): Path to original SEG-Y file
                - description (str, optional): Description of the attribute
                
        Returns:
            bool: True if successful, False otherwise
        """
        self.connect()
        
        try:
            # First verify the project exists and is a multi-attribute volume
            self.cursor.execute("""
                SELECT id, is_multi_attribute 
                FROM seismic_files 
                WHERE name = ?
            """, (project_name,))
            
            result = self.cursor.fetchone()
            if not result:
                self.logger.warning(f"No project found with name: {project_name}")
                return False
                
            seismic_id, is_multi = result
            if is_multi != 1:
                self.logger.warning(f"Project '{project_name}' is not a multi-attribute volume")
                return False
                
            # Check if attribute already exists
            self.cursor.execute("""
                SELECT 1 FROM seismic_attributes
                WHERE seismic_id = ? AND attribute_name = ?
            """, (seismic_id, attribute_info['name']))
            
            if self.cursor.fetchone():
                self.logger.warning(f"Attribute '{attribute_info['name']}' already exists in project '{project_name}'")
                return False
                
            # Insert the new attribute
            insert_attr_sql = """
            INSERT INTO seismic_attributes (
                seismic_id, attribute_name, original_segy_path, description
            ) VALUES (?, ?, ?, ?)
            """
            
            attr_values = [
                seismic_id,
                attribute_info['name'],
                attribute_info.get('original_segy_path'),
                attribute_info.get('description')
            ]
            
            self.cursor.execute(insert_attr_sql, attr_values)
            self.connection.commit()
            
            self.logger.info(f"Added attribute '{attribute_info['name']}' to project '{project_name}'")
            return True
            
        except sqlite3.Error as e:
            self.logger.error(f"Error adding attribute to multi-attribute volume: {e}")
            self.connection.rollback()
            return False
        finally:
            self.disconnect()
            
    def remove_attribute_from_multi_volume(self, project_name, attribute_name):
        """
        Remove an attribute from an existing multi-attribute seismic volume
        
        Args:
            project_name (str): Name of the existing multi-attribute project
            attribute_name (str): Name of the attribute to remove
                
        Returns:
            bool: True if successful, False otherwise
        """
        self.connect()
        
        try:
            # First verify the project exists and is a multi-attribute volume
            self.cursor.execute("""
                SELECT id, is_multi_attribute 
                FROM seismic_files 
                WHERE name = ?
            """, (project_name,))
            
            result = self.cursor.fetchone()
            if not result:
                self.logger.warning(f"No project found with name: {project_name}")
                return False
                
            seismic_id, is_multi = result
            if is_multi != 1:
                self.logger.warning(f"Project '{project_name}' is not a multi-attribute volume")
                return False
                
            # Remove the attribute
            self.cursor.execute("""
                DELETE FROM seismic_attributes
                WHERE seismic_id = ? AND attribute_name = ?
            """, (seismic_id, attribute_name))
            
            if self.cursor.rowcount == 0:
                self.logger.warning(f"Attribute '{attribute_name}' not found in project '{project_name}'")
                return False
                
            self.connection.commit()
            self.logger.info(f"Removed attribute '{attribute_name}' from project '{project_name}'")
            return True
            
        except sqlite3.Error as e:
            self.logger.error(f"Error removing attribute from multi-attribute volume: {e}")
            self.connection.rollback()
            return False
        finally:
            self.disconnect()
    
    def list_all_seismic_files(self):
        """List all seismic files in the database for debugging"""
        self.connect()
    
        try:
            query = """
            SELECT sf.id, sf.name, sf.hdf5_path, sf.is_multi_attribute, 
                   COUNT(sa.id) as attribute_count
            FROM seismic_files sf
            LEFT JOIN seismic_attributes sa ON sf.id = sa.seismic_id
            GROUP BY sf.id
            """
            self.cursor.execute(query)
        
            results = self.cursor.fetchall()
        
            print("All Seismic Files in Database:")
            for row in results:
                if row[3] == 1:  # is_multi_attribute
                    print(f"ID: {row[0]}, Project Name: {row[1]}, HDF5 Path: {row[2]}, Multi-Attribute: Yes, Attributes: {row[4]}")
                else:
                    print(f"ID: {row[0]}, Name: {row[1]}, HDF5 Path: {row[2]}, Single Volume")
        
            return results
    
        except sqlite3.Error as e:
            print(f"Error listing seismic files: {e}")
            return []
        finally:
            self.disconnect()