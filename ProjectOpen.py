import json
import pandas as pd
from PySide6.QtWidgets import QFileDialog
from PySide6.QtWidgets import QMessageBox
from scipy.spatial import KDTree
import os
import pickle
import numpy as np
from DatabaseManager import DatabaseManager
from PySide6.QtWidgets import QTableWidgetItem, QMessageBox

class ProjectLoader:
    def __init__(self, parent):
        self.parent = parent
        self.db_path = None
        self.scenario_id = 1

    def open_from_file(self):
        self.parent.open = True

        options = QFileDialog.Options()
        file_name, _ = QFileDialog.getOpenFileName(self.parent, "Open File", "", "JSON Files (*.json);;All Files (*)", options=options)
        if file_name:
            self.parent.set_project_file_name(file_name)
            with open(file_name, 'r') as file:
                data_loaded = json.load(file)

            # Load DataFrames from JSON if they exist
            self.parent.depth_grid_data_df = pd.DataFrame(data_loaded.get('depth_grid_data', {}))
            self.parent.attribute_grid_data_df = pd.DataFrame(data_loaded.get('attribute_grid_data', {}))
            self.parent.import_options_df = pd.DataFrame(data_loaded.get('import_options', {}))
            self.parent.selected_UWIs = data_loaded.get('selected_UWIs', [])
            self.parent.grid_info_df = pd.DataFrame(data_loaded.get('grid_info', {}))
            self.parent.well_list = data_loaded.get('well_list', [])
            self.parent.master_df = pd.DataFrame(data_loaded.get('master_df', {}))
                    # Load SEGY data and bounding box
            # Load seismic data back into a DataFrame

            seismic_data_dict = data_loaded.get('seismic_data_df', None)
            if seismic_data_dict:
                seismic_metadata_df = pd.DataFrame(seismic_data_dict)
            else:
                seismic_metadata_df = None

            # Load the trace data and time axis
            trace_data = np.array(data_loaded.get('seismic_trace_data', []))
            time_axis = np.array(data_loaded.get('seismic_time_axis', []))

            # Recombine everything back into self.parent.seismic_data
            if seismic_metadata_df is not None:
                self.parent.seismic_data = {
                    'trace_data': trace_data,
                    'time_axis': time_axis,
                    'inlines': seismic_metadata_df['Inline'].values,
                    'crosslines': seismic_metadata_df['Crossline'].values,
                    'x_coords': seismic_metadata_df['X'].values,
                    'y_coords': seismic_metadata_df['Y'].values
                }
            else:
                self.parent.seismic_data = None  # Handle missing metadata case
            try:
                with open(file_name.replace('.json', '_kdtree.pkl'), 'rb') as kdtree_file:
                    self.parent.seismic_kdtree = pickle.load(kdtree_file)
                    print("Seismic KDTree loaded successfully.")
            except FileNotFoundError:
                print("KDTree file not found.")
                self.parent.seismic_kdtree = None  # Handle missing KDTree case
            except Exception as e:
                print(f"Error loading seismic KDTree: {e}")
                self.parent.seismic_kdtree = None


            # Load the bounding box, if it exists
            self.parent.bounding_box = data_loaded.get('bounding_box', None)



            self.parent.line_width = data_loaded.get('line_width', 2)
            self.parent.line_opacity = data_loaded.get('line_opacity', 0.8)
            self.parent.UWI_width = data_loaded.get('UWI_width', 80)
            self.parent.UWI_opacity = data_loaded.get('UWI_opacity', 1.0)
    


            self.parent.gridDropdown.combo.blockSignals(True)
            self.parent.zoneDropdown.combo.blockSignals(True)
            self.parent.zoneAttributeDropdown.combo.blockSignals(True)
            self.parent.wellZoneDropdown.combo.blockSignals(True)
            self.parent.wellAttributeDropdown.combo.blockSignals(True)
            self.parent.grid_colorbar.colorbar_dropdown.combo.blockSignals(True)
            self.parent.zone_colorbar.colorbar_dropdown.combo.blockSignals(True)
            self.parent.well_colorbar.colorbar_dropdown.combo.blockSignals(True)


         
            self.parent.gridDropdown.combo.setCurrentText("Select Grid")
            self.parent.wellZoneDropdown.combo.setCurrentText("Select Well Zone")
            self.parent.zoneDropdown.combo.setCurrentText("Select Zone")


            self.parent.gridDropdown.combo.blockSignals(False)
            self.parent.zoneDropdown.combo.blockSignals(False)
            self.parent.zoneAttributeDropdown.combo.blockSignals(False)
            self.parent.wellZoneDropdown.combo.blockSignals(False)
            self.parent.wellAttributeDropdown.combo.blockSignals(False)
            self.parent.grid_colorbar.colorbar_dropdown.combo.blockSignals(False)
            self.parent.zone_colorbar.colorbar_dropdown.combo.blockSignals(False)
            self.parent.well_colorbar.colorbar_dropdown.combo.blockSignals(False)
            # Load zone viewer settings if they exist
            if 'zone_viewer_settings' in data_loaded:
                self.parent.save_zone_viewer_settings = data_loaded['zone_viewer_settings']

            # Load zone criteria if they exist
            if 'zone_criteria' in data_loaded:
                self.load_zone_criteria_df(data_loaded)

            # Load the saved column filters if they exist
            if 'column_filters' in data_loaded:
                self.parent.column_filters = data_loaded['column_filters']
                # Apply the loaded column filters as needed, possibly refreshing UI elements or data
     

            # Load selected grid and zone
            grid_selected = data_loaded.get('selected_grid', 'Select Grids')
            selected_zone = data_loaded.get('selected_zone', 'Select Zones')



            # Check if 'Grid' column exists and DataFrame is not empty before constructing KDTree
            if not self.parent.depth_grid_data_df.empty and 'Grid' in self.parent.depth_grid_data_df.columns:
                self.parent.kd_tree_depth_grids = {
                    grid: KDTree(self.parent.depth_grid_data_df[self.parent.depth_grid_data_df['Grid'] == grid][['X', 'Y']].values) 
                    for grid in self.parent.depth_grid_data_df['Grid'].unique()
                }
                print("KD-Trees for depth grids constructed.")
            else:
                print("Depth grid data is empty or 'Grid' column not found.")

            if not self.parent.attribute_grid_data_df.empty and 'Grid' in self.parent.attribute_grid_data_df.columns:
                self.parent.kd_tree_att_grids = {
                    grid: KDTree(self.parent.attribute_grid_data_df[self.parent.attribute_grid_data_df['Grid'] == grid][['X', 'Y']].values) 
                    for grid in self.parent.attribute_grid_data_df['Grid'].unique()
                }
                print("KD-Trees for attribute grids constructed.")
            else:
                print("Attribute grid data is empty or 'Grid' column not found.")

            if self.parent.depth_grid_data_df is not None and self.parent.kd_tree_depth_grids is not None:
                self.parent.depth_grid_data_dict = {
                    grid: self.parent.depth_grid_data_df[self.parent.depth_grid_data_df['Grid'] == grid]['Z'].values
                    for grid in self.parent.kd_tree_depth_grids
                }

            # Check if 'attribute_grid_data_df' and 'kd_tree_att_grids' are not None
            if self.parent.attribute_grid_data_df is not None and self.parent.kd_tree_att_grids is not None:
                self.parent.attribute_grid_data_dict = {
                    grid: self.parent.attribute_grid_data_df[self.parent.attribute_grid_data_df['Grid'] == grid]['Z'].values
                    for grid in self.parent.kd_tree_att_grids
                }


            

            db_file_path = file_name.replace('.json', '.db')
            self.load_db_file(db_file_path)
          
            # Populate dropdowns
            self.parent.populate_well_zone_dropdown()
            self.parent.populate_grid_dropdown(grid_selected)
            self.parent.populate_zone_dropdown()




            # Enable menus and update window title
            self.parent.import_menu.setEnabled(True)
            self.parent.prepare_attributes_menu.setEnabled(True)  # Renamed from calculate_menu
            self.parent.regression_menu.setEnabled(True)  # New menu
            self.parent.production_menu.setEnabled(True)  # New menu
            self.parent.properties_menu.setEnabled(True)  # Keep as is

            # Update window title
            file_basename = os.path.basename(file_name)
            self.parent.setWindowTitle(f"Zone Analyzer - {file_basename}")



            
            

    def load_zone_criteria_df(self, data_loaded):
        """Load the zone criteria DataFrame from the project data."""
        # Load the data into a DataFrame
        zone_criteria_df = pd.DataFrame(data_loaded.get('zone_criteria', {}))

        # Retrieve and apply the column order
        column_order = data_loaded.get('zone_criteria_columns', None)
        if column_order:
            zone_criteria_df = zone_criteria_df[column_order]
    
        self.parent.zone_criteria_df = zone_criteria_df

        
    
    def load_db_file(self, db_file_path):
        if os.path.exists(db_file_path):
            try:

                self.parent.db_manager = DatabaseManager(db_file_path)
                self.parent.db_manager.connect()
                self.parent.db_path = db_file_path 
                print(f"Database loaded successfully from: {db_file_path}")
                self.load_directional_surveys_from_db()
                self.parent.selected_UWIs = self.parent.db_manager.get_UWIs()
                self.parent.well_data_df = self.parent.db_manager.get_all_UWIs()
                print(self.parent.well_data_df)
                self.parent.well_list = self.parent.well_data_df['UWI'].tolist()
                self.scneario_id = 1
                self.parent.model_data = self.parent.db_manager.retrieve_model_data_by_scenario(self.scenario_id)

            except Exception as e:
                QMessageBox.critical(
                    self.parent,
                    "Database Load Error",
                    f"Failed to load database: {str(e)}",
                    QMessageBox.Ok
                )
        else:
            QMessageBox.warning(self.parent, "Database Not Found", "No corresponding database file found at: {db_file_path}", QMessageBox.Ok)



    def load_directional_surveys_from_db(self):
        try:
            # Query the database for directional surveys
            directional_surveys_data = self.parent.db_manager.get_directional_surveys()

            # Check if data is returned
            if directional_surveys_data:
                # Convert the result into a DataFrame and drop the first column
                self.parent.directional_surveys_df = pd.DataFrame(directional_surveys_data).iloc[:, 1:]
            
                # Rename the columns to match your expected structure
                self.parent.directional_surveys_df.columns = ['UWI', 'MD', 'TVD', 'X Offset', 'Y Offset', 'Cumulative Distance']
            
                print(f"Directional surveys data loaded: {self.parent.directional_surveys_df}")
            else:
                print("No directional surveys data found in the database.")
                self.parent.directional_surveys_df = pd.DataFrame()
              # Ensure it's initialized as an empty DataFrame

        except Exception as e:
            # Handle errors gracefully
            print(f"Error occurred while loading directional surveys: {str(e)}")
            QMessageBox.critical(self.parent, "Error", f"Failed to load directional surveys from DB: {str(e)}")

