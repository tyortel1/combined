import ujson as json
import pandas as pd
from concurrent.futures import ThreadPoolExecutor
import threading

class ProjectSaver:
    def __init__(self, project_file_name):
        self.project_file_name = project_file_name
        self.project_data = self.load_project_data()
        self.executor = ThreadPoolExecutor(max_workers=1)  # Thread pool for background saving
        self.lock = threading.Lock()  # Lock for thread safety

    def load_project_data(self):
        try:
            with open(self.project_file_name, 'r') as file:
                return json.load(file)
        except FileNotFoundError:
            return {}
        except Exception as e:
            print(f"Error loading project data: {e}")
            return {}

    def save_project_data(self):
        with self.lock:
            try:
                with open(self.project_file_name, 'w') as file:
                    json.dump(self.project_data, file)
                print(f"Project saved to {self.project_file_name}")
            except Exception as e:
                print(f"Error saving project data: {e}")

    def save_directional_surveys(self, directional_surveys_df):
        with self.lock:
            self.project_data['directional_surveys'] = directional_surveys_df.to_dict(orient='list')
        self.executor.submit(self.save_project_data)

    def save_depth_grid_data(self, depth_grid_data_df):
        with self.lock:
            self.project_data['depth_grid_data'] = depth_grid_data_df.to_dict(orient='list')
        self.executor.submit(self.save_project_data)

    def save_attribute_grid_data(self, attribute_grid_data_df):
        with self.lock:
            self.project_data['attribute_grid_data'] = attribute_grid_data_df.to_dict(orient='list')
        self.executor.submit(self.save_project_data)

    def save_import_options(self, import_options_df):
        with self.lock:
            self.project_data['import_options'] = import_options_df.to_dict(orient='list')
        self.executor.submit(self.save_project_data)

    def save_selected_uwis(self, selected_uwis):
        with self.lock:
            self.project_data['selected_uwis'] = selected_uwis
        self.executor.submit(self.save_project_data)

    def save_depth_grid_colors(self, depth_grid_color_df):
        with self.lock:
            self.project_data['depth_grid_colors'] = depth_grid_color_df.to_dict(orient='list')
        self.executor.submit(self.save_project_data)

    def save_grid_info(self, grid_info_df):
        with self.lock:
            self.project_data['grid_info'] = grid_info_df.to_dict(orient='list')
        self.executor.submit(self.save_project_data)

    def save_well_list(self, well_list):
        with self.lock:
            self.project_data['well_list'] = well_list
        self.executor.submit(self.save_project_data)

    def save_master_df(self, master_df):
        with self.lock:
            self.project_data['master_df'] = master_df.to_dict(orient='list')
        self.executor.submit(self.save_project_data)

    def shutdown(self):
        self.executor.shutdown(wait=True)
