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
            
            # Load master_df from JSON if it exists
            self.parent.master_df = pd.DataFrame(data_loaded.get('master_df', {}))

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

            self.parent.depth_grid_data_dict = {
                grid: self.parent.depth_grid_data_df[self.parent.depth_grid_data_df['Grid'] == grid]['Z'].values
                for grid in self.parent.kd_tree_depth_grids
            }

            self.parent.attribute_grid_data_dict = {
                grid: self.parent.attribute_grid_data_df[self.parent.attribute_grid_data_df['Grid'] == grid]['Z'].values
                for grid in self.parent.kd_tree_att_grids
            }

            # Populate the grid dropdown with grid names
            self.parent.populate_grid_dropdown()
            self.parent.setData(self.parent.directional_surveys_df)

            # Enable menus and update window title
            self.parent.import_menu.setEnabled(True)
            self.parent.launch_menu.setEnabled(True)
            file_basename = os.path.basename(file_name)
            self.parent.setWindowTitle(f"Zone Analyzer - {file_basename}")
