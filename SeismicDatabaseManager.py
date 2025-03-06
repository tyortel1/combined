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
        # Main seismic files table - removed original_segy_path
        create_seismic_table_sql = """
        CREATE TABLE IF NOT EXISTS seismic_files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,                      -- Name of the seismic file/project
            hdf5_path TEXT NOT NULL,                 -- Path to HDF5 file
            format TEXT NOT NULL,                    -- SEG-Y format
            datum REAL NOT NULL,                     -- Seismic datum
            sample_rate REAL NOT NULL,               -- Sample rate in seconds
            num_samples INTEGER NOT NULL,            -- Number of time samples
            vertical_unit TEXT DEFAULT 'Meters',     -- Vertical unit (Feet or Meters)
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
    
        # Attributes table
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
            self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_format ON seismic_files(format)")
            self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_multi_attribute ON seismic_files(is_multi_attribute)")
            self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_attribute_seismic_id ON seismic_attributes(seismic_id)")
            self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_attribute_name ON seismic_attributes(attribute_name)")
            self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_segy_path ON seismic_attributes(original_segy_path)")
    
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
                - hdf5_path (str): Path to HDF5 file
                - format (str): SEG-Y format type
                - datum (float): Seismic datum
                - sample_rate (float): Sample rate in ms
                - num_samples (int): Number of samples per trace
                - vertical_unit (str): Vertical unit (Feet or Meters)
                - geometry (dict): Optional dictionary containing:
                    - inline_min/max (int): Inline range
                    - xline_min/max (int): Crossline range
                    - x_min/max (float): X coordinate range
                    - y_min/max (float): Y coordinate range

        Returns:
            int: ID of the inserted record, or None on failure
        """
        self.connect()
    
        try:
            # Insert main seismic file info
            insert_file_sql = """
            INSERT INTO seismic_files (
                name, hdf5_path, format, datum,
                sample_rate, num_samples, vertical_unit, is_multi_attribute, creation_date, last_modified
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 0, datetime('now'), datetime('now'))
            """

            # Add vertical_unit to the values list
            file_values = [
                file_info['name'],
                file_info['hdf5_path'],
                file_info['format'],
                file_info['datum'],
                file_info['sample_rate'],
                file_info['num_samples'],
                file_info.get('vertical_unit', 'Meters')  # Default to Meters if not provided
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
            self.logger.info(f"Seismic file info saved successfully for {file_info['name']}")
            return seismic_id
        
        except sqlite3.Error as e:
            self.logger.error(f"Error saving seismic file info: {e}")
            self.connection.rollback()
            return None
        finally:
            self.disconnect()

    def get_seismic_file_info(self, id=None, name=None, hdf5_path=None):
        """Retrieve seismic file information including geometry
    
        Args:
            id (int, optional): ID of the seismic file
            name (str, optional): Name of the seismic file
            hdf5_path (str, optional): Path to the HDF5 file
        
        Returns:
            dict: Dictionary with seismic file information, or None if not found
        """
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
    
            if id:
                query += "f.id = ?"
                param = id
            elif name:
                query += "f.name = ?"
                param = name
            elif hdf5_path:
                query += "f.hdf5_path = ?"
                param = hdf5_path
            else:
                raise ValueError("Must provide either id, name, or hdf5_path")
            
            self.cursor.execute(query, (param,))
            result = self.cursor.fetchone()
        
            if result:
                # Convert to dictionary
                columns = [description[0] for description in self.cursor.description]
                file_info = dict(zip(columns, result))
            
                # Get attributes for this seismic file
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
            include_attributes (bool): Whether to include attribute information 
        
        Returns:
            list: List of dictionaries containing seismic file information.
        """
        self.connect()

        try:
            query = """
            SELECT 
                f.id,
                f.name,
                f.hdf5_path,
                f.format,
                f.datum,
                f.sample_rate,
                f.num_samples,
                f.vertical_unit, 
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
                    
                    # Get attributes
                    if include_attributes:
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

    def update_seismic_file(self, update_info):
        """
        Update seismic file information
    
        Args:
            update_info (dict): Dictionary containing:
                - id (int): ID of the seismic file to update
                - Other fields to update (name, hdf5_path, etc.)
            
        Returns:
            bool: True if successful, False otherwise
        """
        if 'id' not in update_info:
            self.logger.error("No ID provided for update")
            return False
        
        self.connect()
    
        try:
            # Build update SQL dynamically based on provided fields
            update_fields = []
            params = []
        
            # Fields that can be updated in the main table
            valid_fields = [
                'name', 'hdf5_path', 'format', 'datum', 
                'sample_rate', 'num_samples', 'vertical_unit', 'is_multi_attribute'
            ]
        
            for field in valid_fields:
                if field in update_info:
                    update_fields.append(f"{field} = ?")
                    params.append(update_info[field])
                
            # Add last_modified timestamp
            update_fields.append("last_modified = datetime('now')")
        
            if not update_fields:
                self.logger.warning("No valid fields provided for update")
                return False
            
            # Build the SQL query
            update_sql = f"""
            UPDATE seismic_files 
            SET {', '.join(update_fields)}
            WHERE id = ?
            """
        
            # Add the ID as the last parameter
            params.append(update_info['id'])
        
            # Execute the update
            self.cursor.execute(update_sql, params)
        
            # Handle attribute names update if provided
            if 'attribute_names' in update_info:
                # This requires more complex handling
                # For now, we'll just log that attributes were also updated
                self.logger.info(f"Updated attribute list for seismic file ID {update_info['id']}")
        
            self.connection.commit()
        
            return True
        
        except sqlite3.Error as e:
            self.logger.error(f"Error updating seismic file: {e}")
            self.connection.rollback()
            return False
        finally:
            self.disconnect()

    def save_attribute_info(self, seismic_id, attribute_name, segy_path):
        """Save attribute information to the database

        Args:
            seismic_id (int): ID of the seismic file
            attribute_name (str): Name of the attribute
            segy_path (str): Path to the original SEG-Y file

        Returns:
            bool: True if successful, False otherwise
        """
        self.connect()

        try:
            # First check if attribute already exists
            self.cursor.execute("""
                SELECT id FROM seismic_attributes 
                WHERE seismic_id = ? AND attribute_name = ?
            """, (seismic_id, attribute_name))
        
            existing = self.cursor.fetchone()
        
            if existing:
                # Update existing attribute
                update_sql = """
                UPDATE seismic_attributes 
                SET original_segy_path = ?
                WHERE seismic_id = ? AND attribute_name = ?
                """
                self.cursor.execute(update_sql, [segy_path, seismic_id, attribute_name])
                self.logger.info(f"Updated existing attribute '{attribute_name}' for seismic ID {seismic_id}")
            else:
                # Insert new attribute
                insert_sql = """
                INSERT INTO seismic_attributes (
                    seismic_id, attribute_name, original_segy_path, creation_date
                ) VALUES (?, ?, ?, datetime('now'))
                """
                self.cursor.execute(insert_sql, [seismic_id, attribute_name, segy_path])
                self.logger.info(f"Added new attribute '{attribute_name}' for seismic ID {seismic_id}")
        
            self.connection.commit()
            return True
        except sqlite3.Error as e:
            self.logger.error(f"Error saving attribute info: {e}")
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
                    print(f"ID: {row[0]}, Name: {row[1]}, HDF5 Path: {row[2]}, Single Volume, Attributes: {row[4]}")
    
            return results

        except sqlite3.Error as e:
            print(f"Error listing seismic files: {e}")
            return []
        finally:
            self.disconnect()