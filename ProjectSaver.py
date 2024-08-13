import ujson as json
import pandas as pd
from concurrent.futures import ThreadPoolExecutor
import threading

class ProjectSaver:
    def __init__(self, project_file_name):
        self.project_file_name = project_file_name
        self.project_data = self.load_project_data()
        self.executor = ThreadPoolExecutor(max_workers=1)  # Thread pool for background saving
        self.executor_shutdown = False  # Executor shutdown flag
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

    def submit_save_task(self):
        if not self.executor_shutdown:
            future = self.executor.submit(self.save_project_data)
            return future
        else:
            print("Executor has been shut down. Cannot submit new tasks.")
            return None

    def save_directional_surveys(self, directional_surveys_df):
        with self.lock:
            self.project_data['directional_surveys'] = directional_surveys_df.to_dict(orient='list')
        self.submit_save_task()

    def save_depth_grid_data(self, depth_grid_data_df):
        with self.lock:
            self.project_data['depth_grid_data'] = depth_grid_data_df.to_dict(orient='list')
        self.submit_save_task()

    def save_attribute_grid_data(self, attribute_grid_data_df):
        with self.lock:
            self.project_data['attribute_grid_data'] = attribute_grid_data_df.to_dict(orient='list')
        self.submit_save_task()

    def save_import_options(self, import_options_df):
        with self.lock:
            self.project_data['import_options'] = import_options_df.to_dict(orient='list')
        self.submit_save_task()

    def save_selected_uwis(self, selected_uwis):
        with self.lock:
            self.project_data['selected_uwis'] = selected_uwis
        self.submit_save_task()

    def save_depth_grid_colors(self, depth_grid_color_df):
        with self.lock:
            self.project_data['depth_grid_colors'] = depth_grid_color_df.to_dict(orient='list')
        self.submit_save_task()

    def save_grid_info(self, grid_info_df):
        with self.lock:
            self.project_data['grid_info'] = grid_info_df.to_dict(orient='list')
        self.submit_save_task()

    def save_well_list(self, well_list):
        with self.lock:
            self.project_data['well_list'] = well_list
        self.submit_save_task()

    def save_master_df(self, master_df):
       
        
        with self.lock:
            self.project_data['master_df'] = master_df.to_dict(orient='list')
        print("Saving master DataFrame.")
        print(f"Before submit_save_task. executor_shutdown: {self.executor_shutdown}")
        self.submit_save_task()
        print(f"After submit_save_task. executor_shutdown: {self.executor_shutdown}")

    def save_zone_names(self, zone_names):
        with self.lock:
            self.project_data['zone_names'] = zone_names
        self.submit_save_task()


    def save_zone_viewer_settings(self, settings):
        with self.lock:
            self.project_data['zone_viewer_settings'] = settings
        self.submit_save_task()

    def save_zone_criteria_df(self, zone_criteria_df):
        """Save the zone criteria DataFrame to the project data."""
        print(zone_criteria_df)
        with self.lock:
            # Store the DataFrame as a dictionary
            self.project_data['zone_criteria'] = zone_criteria_df.to_dict(orient='list')
        
            # Store the column order explicitly
            self.project_data['zone_criteria_columns'] = list(zone_criteria_df.columns)
            print(self.project_data)
            
        self.submit_save_task()

    def shutdown(self, line_width, line_opacity, uwi_width, uwi_opacity, selected_grid, selected_zone):
        with self.lock:
            self.project_data['line_width'] = line_width
            self.project_data['line_opacity'] = line_opacity
            self.project_data['uwi_width'] = uwi_width
            self.project_data['uwi_opacity'] = uwi_opacity
            self.project_data['selected_grid'] = selected_grid
            self.project_data['selected_zone'] = selected_zone
        
        print("Submitting final save task before shutdown.")
        future = self.submit_save_task()
        if future:
            future.result()  # Wait for the final save task to complete

        print("Setting executor_shutdown to True and shutting down executor.")
        self.executor_shutdown = True
        self.executor.shutdown(wait=True)
        print("Executor has been shut down.")
