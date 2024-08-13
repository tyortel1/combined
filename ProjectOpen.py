import json
import pandas as pd
from PySide2.QtWidgets import QFileDialog
from scipy.spatial import KDTree
import os

class ProjectLoader:
    def __init__(self, parent):
        self.parent = parent

    def open_from_file(self):
        self.parent.open = True

        options = QFileDialog.Options()
        file_name, _ = QFileDialog.getOpenFileName(self.parent, "Open File", "", "JSON Files (*.json);;All Files (*)", options=options)
        if file_name:
            self.parent.set_project_file_name(file_name)
            with open(file_name, 'r') as file:
                data_loaded = json.load(file)

            # Load DataFrames from JSON if they exist
            self.parent.directional_surveys_df = pd.DataFrame(data_loaded.get('directional_surveys', {}))
            self.parent.depth_grid_data_df = pd.DataFrame(data_loaded.get('depth_grid_data', {}))
            self.parent.attribute_grid_data_df = pd.DataFrame(data_loaded.get('attribute_grid_data', {}))
            self.parent.import_options_df = pd.DataFrame(data_loaded.get('import_options', {}))
            self.parent.selected_uwis = data_loaded.get('selected_uwis', [])
            self.parent.grid_info_df = pd.DataFrame(data_loaded.get('grid_info', {}))
            self.parent.well_list = data_loaded.get('well_list', [])
            self.parent.master_df = pd.DataFrame(data_loaded.get('master_df', {}))

            # Load zone names
            self.parent.zone_names = data_loaded.get('zone_names', [])

            # Load map parameters
            self.parent.line_width = data_loaded.get('line_width', 2)
            self.parent.line_opacity = data_loaded.get('line_opacity', 0.8)
            self.parent.uwi_width = data_loaded.get('uwi_width', 80)
            self.parent.uwi_opacity = data_loaded.get('uwi_opacity', 1.0)


            if 'zone_viewer_settings' in data_loaded:
                self.parent.save_zone_viewer_settings = data_loaded['zone_viewer_settings']
               
            if 'zone_criteria' in data_loaded:
                print(data_loaded)
                self.load_zone_criteria_df(data_loaded)
            grid_selected = data_loaded.get('selected_grid', 'Select Grids')
            selected_zone = data_loaded.get('selected_zone', 'Select Zones')
            print(selected_zone)

            self.parent.populate_grid_dropdown(grid_selected)
            self.parent.populate_zone_dropdown(selected_zone)

            # Debugging: Print DataFrame columns and head to verify loading
            print("Depth Grid DataFrame Columns:", self.parent.depth_grid_data_df.columns)
            print("Depth Grid DataFrame Head:\n", self.parent.depth_grid_data_df.head())
            print("Attribute Grid DataFrame Columns:", self.parent.attribute_grid_data_df.columns)
            print("Attribute Grid DataFrame Head:\n", self.parent.attribute_grid_data_df.head())
            print("Master DataFrame Columns:", self.parent.master_df.columns)
            print("Master DataFrame Head:\n", self.parent.master_df.head())

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


            self.parent.setData()


            self.parent.populate_grid_dropdown(grid_selected)
            self.parent.populate_zone_dropdown(selected_zone)
            if selected_zone is not None and selected_zone != "Select Zone":
                self.parent.populate_zone_attributes()


            self.parent.zoneDropdown.currentText()

            # Enable menus and update window title
            self.parent.import_menu.setEnabled(True)
            self.parent.launch_menu.setEnabled(True)
            self.parent.calculate_menu.setEnabled(True)
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
        print(self.parent.zone_criteria_df)