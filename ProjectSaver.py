import ujson as json
import pandas as pd
from concurrent.futures import ThreadPoolExecutor
import threading
import pickle
import numpy as np

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

    def save_selected_UWIs(self, selected_UWIs):
        with self.lock:
            self.project_data['selected_UWIs'] = selected_UWIs
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
        master_df = master_df.fillna(0)
        
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
     
        with self.lock:
            # Store the DataFrame as a dictionary
            self.project_data['zone_criteria'] = zone_criteria_df.to_dict(orient='list')
        
            # Store the column order explicitly
            self.project_data['zone_criteria_columns'] = list(zone_criteria_df.columns)
         
            
        self.submit_save_task()



    def save_column_filters(self, column_filters ):
        with self.lock:  # Assuming self.lock is defined as a threading.Lock() elsewhere in your class
            self.project_data['column_filters'] = column_filters  # Store the filters in your project data
        self.submit_save_task()  # Assuming this handles the actual saving process asynchronously

    def save_seismic_data(self, seismic_data, bounding_box, seismic_kdtree=None):
        with self.lock:
            # Convert seismic metadata (Inline, Crossline, X, Y) to DataFrame
            seismic_df = pd.DataFrame({
                'Inline': seismic_data['inlines'],
                'Crossline': seismic_data['crosslines'],
                'X': seismic_data['x_coords'],
                'Y': seismic_data['y_coords']
            })

            # Get the time_axis and trace_data from seismic_data
            time_data = seismic_data['time_axis']
            trace_data = seismic_data['trace_data']

            # Save seismic metadata as a dictionary
            self.project_data['seismic_data_df'] = seismic_df.to_dict(orient='list')

            # Save the time_axis and trace_data separately as lists
            self.project_data['seismic_time_axis'] = time_data.tolist()
            self.project_data['seismic_trace_data'] = trace_data.tolist()

            # Save the bounding box if applicable
            self.project_data['bounding_box'] = bounding_box

            # Save the KDTree for seismic data if provided
            if seismic_kdtree:
                try:
                    # Save the KDTree using pickle
                    with open(self.project_file_name.replace('.json', '_kdtree.pkl'), 'wb') as kdtree_file:
                        pickle.dump(seismic_kdtree, kdtree_file)
                    print("Seismic KDTree saved successfully.")
                except Exception as e:
                    print(f"Error saving seismic KDTree: {e}")

        # Submit the save task asynchronously
        self.submit_save_task()



    def shutdown(self, line_width, line_opacity, UWI_width, UWI_opacity, selected_grid, selected_zone, selected_zone_attribute, selected_well_zone, selected_well_attribute, gridColorBarDropdown, zoneAttributeColorBarDropdown, WellAttributeColorBarDropdown):
        with self.lock:
            # Store the existing parameters
            self.project_data['line_width'] = line_width
            self.project_data['line_opacity'] = line_opacity
            self.project_data['UWI_width'] = UWI_width
            self.project_data['UWI_opacity'] = UWI_opacity
            self.project_data['selected_grid'] = selected_grid
            self.project_data['selected_zone'] = selected_zone
        
            # Store the additional parameters
            self.project_data['selected_zone_attribute'] = selected_zone_attribute
            self.project_data['selected_well_zone'] = selected_well_zone
            self.project_data['selected_well_attribute'] = selected_well_attribute
            self.project_data['grid_color_bar_dropdown'] = gridColorBarDropdown
            self.project_data['zone_attribute_color_bar_dropdown'] = zoneAttributeColorBarDropdown
            self.project_data['well_attribute_color_bar_dropdown'] = WellAttributeColorBarDropdown

        print("Submitting final save task before shutdown.")
        future = self.submit_save_task()
        if future:
            future.result()  # Wait for the final save task to complete

        print("Setting executor_shutdown to True and shutting down executor.")
        self.executor_shutdown = True
        self.executor.shutdown(wait=True)
        print("Executor has been shut down.")