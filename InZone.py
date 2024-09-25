from http.client import PARTIAL_CONTENT
from PySide2.QtWidgets import QDialog, QLabel, QComboBox,QLineEdit, QMessageBox, QPushButton, QAbstractItemView, QListWidget, QListWidgetItem, QVBoxLayout, QHBoxLayout, QSpacerItem, QSizePolicy
from PySide2.QtGui import QIcon
import pandas as pd
from shapely.geometry import LineString, Point, MultiPoint
import numpy as np

class InZoneDialog(QDialog):
    def __init__(self, master_df, directional_surveys_df, grid_info_df, kd_tree_depth_grids, kd_tree_att_grids, zone_names, depth_grid_data_dict, attribute_grid_data_dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Find Wells in Zone")
        self.master_df = master_df
        self.directional_surveys_df = directional_surveys_df
        self.grid_info_df = grid_info_df
        self.kd_tree_depth_grids = kd_tree_depth_grids
        self.kd_tree_att_grids = kd_tree_att_grids
        self.zone_names = zone_names
        self.depth_grid_data_dict = depth_grid_data_dict
        self.attribute_grid_data_dict = attribute_grid_data_dict
        self.sorted_grid_order  = []
        self.total_laterals = []


        # Create widgets
        self.zone_name_label = QLabel("New Zone Name (In-Zone):", self)
        self.zone_name_edit = QLineEdit(self)

        self.existing_zone_name_label = QLabel("Select Zone Name (Percentages):", self)
        self.existing_zone_name_combo = QComboBox(self)
        self.existing_zone_name_combo.addItems(self.zone_names) 


        # Two-list selector layout for grids
        grid_list_layout = QHBoxLayout()

        self.available_grids_list = QListWidget()
        self.available_grids_list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        grid_list_layout.addWidget(self.available_grids_list)

        grid_arrow_layout = QVBoxLayout()
        grid_arrow_layout.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding))

        self.move_all_grids_right_button = QPushButton()
        self.move_all_grids_right_button.setIcon(QIcon("icons/arrow_double_right.png"))
        self.move_all_grids_right_button.clicked.connect(self.move_all_grids_right)
        grid_arrow_layout.addWidget(self.move_all_grids_right_button)

        self.move_grids_right_button = QPushButton()
        self.move_grids_right_button.setIcon(QIcon("icons/arrow_right.ico"))
        self.move_grids_right_button.clicked.connect(self.move_selected_grids_right)
        grid_arrow_layout.addWidget(self.move_grids_right_button)

        self.move_grids_left_button = QPushButton()
        self.move_grids_left_button.setIcon(QIcon("icons/arrow_left.ico"))
        self.move_grids_left_button.clicked.connect(self.move_selected_grids_left)
        grid_arrow_layout.addWidget(self.move_grids_left_button)

        self.move_all_grids_left_button = QPushButton()
        self.move_all_grids_left_button.setIcon(QIcon("icons/arrow_double_left.png"))
        self.move_all_grids_left_button.clicked.connect(self.move_all_grids_left)
        grid_arrow_layout.addWidget(self.move_all_grids_left_button)

        grid_arrow_layout.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding))
        grid_list_layout.addLayout(grid_arrow_layout)

        self.selected_grids_list = QListWidget()
        self.selected_grids_list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        grid_list_layout.addWidget(self.selected_grids_list)

        # Set layout
        layout = QVBoxLayout()
        layout.addWidget(self.zone_name_label)
        layout.addWidget(self.zone_name_edit)
        layout.addWidget(self.existing_zone_name_label)
        layout.addWidget(self.existing_zone_name_combo)
        layout.addLayout(grid_list_layout)

        # Calculate Button
        self.calculate_button = QPushButton("Calculate", self)
        self.calculate_button.clicked.connect(self.create_grid_dataframe)
        layout.addWidget(self.calculate_button)

        # Close Button
        self.close_button = QPushButton("Close", self)
        self.close_button.clicked.connect(self.accept)
        layout.addWidget(self.close_button)

        self.setLayout(layout)
        self.update_grid_selection()

    def update_grid_selection(self):
        # Only select depth grids
        grid_names = self.grid_info_df[self.grid_info_df['Type'] == 'Depth']['Grid'].tolist()

        self.available_grids_list.clear()
        for grid_name in grid_names:
            item = QListWidgetItem(grid_name)
            self.available_grids_list.addItem(item)

    def move_all_grids_right(self):
        while self.available_grids_list.count() > 0:
            item = self.available_grids_list.takeItem(0)
            self.selected_grids_list.addItem(item)

    def move_selected_grids_right(self):
        for item in self.available_grids_list.selectedItems():
            self.selected_grids_list.addItem(self.available_grids_list.takeItem(self.available_grids_list.row(item)))

    def move_selected_grids_left(self):
        for item in self.selected_grids_list.selectedItems():
            self.available_grids_list.addItem(self.selected_grids_list.takeItem(self.selected_grids_list.row(item)))

    def move_all_grids_left(self):
        while self.selected_grids_list.count() > 0:
            item = self.selected_grids_list.takeItem(0)
            self.available_grids_list.addItem(item)

    def create_well_lines(self):
        """Create well path lines from directional surveys."""
        well_lines = []
        for uwi, group in self.directional_surveys_df.groupby('UWI'):
            coords = list(zip(group['X Offset'], group['Y Offset'], group['TVD']))
            well_path = LineString(coords)
            well_lines.append((uwi, well_path))

        return well_lines

    def create_grid_dataframe(self):

        #Grab the name they want to call this
        zone_name = self.zone_name_edit.text().strip()

        if not zone_name:
            QMessageBox.warning(self, "Error", "Zone name cannot be empty. Please enter a valid zone name.")
            return

        #Create a DataFrame for each well with X, Y offsets, TVD, and closest Z values for each grid
        data = []

        for uwi, group in self.directional_surveys_df.groupby('UWI'):
          
            for i, row in group.iterrows():
                x = row['X Offset']
                y = row['Y Offset']
                tvd = row['TVD']
                md = row['MD']
                cum_distance = row['Cumulative Distance']

                # Initialize a dictionary to store the closest Z values for each grid
                closest_z_values = {}

                # Query each KD-Tree to find the closest Z value for each grid
                for grid, kdtree in self.kd_tree_depth_grids.items():
                    if kdtree.data.size > 0:
                        distances, indices = kdtree.query([x, y])
                        if indices < len(self.depth_grid_data_dict[grid]):
                            closest_z_values[grid] = self.depth_grid_data_dict[grid][indices]
                        else:
                            closest_z_values[grid] = None  # Handle cases where the index is out of range
                    else:
                        closest_z_values[grid] = None  # Handle cases where the KD-Tree is empty

                # Prepare the row for the DataFrame
                row_data = {
                    'UWI': uwi,
                    'X Offset': x,
                    'Y Offset': y,
                    'TVD': tvd,
                    'MD' : md,
                    'Cumulative Distance' : cum_distance
                }
                # Add the closest Z values for each grid to the row data
                for grid in self.kd_tree_depth_grids.keys():
                    row_data[f'{grid} Closest Z'] = closest_z_values.get(grid)

                data.append(row_data)


        # Have a dataframe of basically all the well lines along with grid lines
        df = pd.DataFrame(data)
      
        
        # Assuming df is already sorted by UWI and TVD as it should be something to keep in mind 
        selected_grids = [self.selected_grids_list.item(i).text() for i in range(self.selected_grids_list.count())]

        #Sort the grids by average tvd so we can understand if we are entering or exiting zone
        self.sorted_grid_order = self.get_sorted_grid_order(selected_grids)


        #Find interections for each line if they exist
        intersections = self.find_tvd_grid_intersections(df, selected_grids)
        
  
        self.update_master_df(intersections)
     
    def get_sorted_grid_order(self, selected_grids):
        # Dictionary to store average TVD for each grid
        grid_tvd_averages = {}

        # Calculate the average TVD for each grid using the depth_grid_data_dict
        for grid in selected_grids:
            z_values = self.depth_grid_data_dict.get(grid, [])
        
            if len(z_values) > 0:
                average_tvd = np.mean(z_values)
                grid_tvd_averages[grid] = average_tvd

        # Sort the grids based on the average TVD in ascending order (lowest to highest)
        sorted_grids = sorted(grid_tvd_averages, key=grid_tvd_averages.get)
    
        return sorted_grids
        

    #What is this who knows maybe its magic thats making it work so im leaving it alone
    def calculate(self):
        grid_df = self.create_grid_dataframe()



    def find_tvd_grid_intersections(self, df, selected_grids):
        sorted_grids = self.get_sorted_grid_order(selected_grids)[::-1]
        intersections_list = []
        self.total_laterals = []
        for uwi in df['UWI'].unique():
            well_df = df[df['UWI'] == uwi].sort_values(by='MD').reset_index(drop=True)
            well_df['Inclination'] = np.nan

            # Calculate inclination for each row
            for i in range(1, len(well_df)):
                current_row = well_df.iloc[i]
                previous_row = well_df.iloc[i - 1]
                delta_md = current_row['MD'] - previous_row['MD']
                delta_tvd = current_row['TVD'] - previous_row['TVD']
                if delta_md != 0:
                    inclination = np.degrees(np.arccos(delta_tvd / delta_md))
                    well_df.at[i, 'Inclination'] = inclination

            # Filter to only the horizontal portions of the well (Inclination < 91 degrees)
            well_df = well_df[well_df['Inclination'] < 91].reset_index(drop=True)

            # Calculate the total lateral length
            total_lateral = well_df['MD'].max() - well_df['MD'].min()
            self.total_laterals.append({
                'UWI': uwi,
                'Total Lateral Length': total_lateral
            })
        
            if well_df.empty:
                continue  # Skip to the next UWI if this one has no horizontal portions
            
            # OKay so i am trying to create zones here so i will assume the first zone is like the begging of the well
            first_row = well_df.iloc[0]
            first_x_offset = first_row['X Offset']
            first_y_offset = first_row['Y Offset']
            first_md = first_row['MD']
            first_tvd = first_row['TVD']

            # The last depth of the well will be the very end of the last zone
            last_row = well_df.iloc[-1]
            last_x_offset = last_row['X Offset']
            last_y_offset = last_row['Y Offset']
            last_md = last_row['MD']
            last_tvd = last_row['TVD']

            grid_z_values = {}

            # Collect Z values for each grid at the first MD
            for grid in sorted_grids:
                z_value = well_df[f'{grid} Closest Z'].iloc[0]
                grid_z_values[grid] = z_value

            # Determine which grid is directly above the first TVD
            initial_grid = "Above All"
            for i in range(1, len(sorted_grids)):
                grid_below = sorted_grids[i - 1]
                grid_above = sorted_grids[i]

                z_below = grid_z_values[grid_below]
                z_above = grid_z_values[grid_above]

                if z_below >= first_tvd >= z_above:
                    initial_grid = grid_below
                   
                    break
    


            #I need thse angles to draw sticks on the map that are perpedicularish to the overall direction fo the line so im doing it here
            general_angle = self.calculate_angle(first_x_offset, first_y_offset, last_x_offset, last_y_offset)

            # Initialize the first intersection using the first row
            current_intersection = {
                'UWI': uwi,
                'Grid Name': initial_grid,  # Will be filled in when the first grid intersection is found
                'Top X Offset': first_x_offset,
                'Top Y Offset': first_y_offset,
                'Top Depth': first_md,
                'Top TVD': first_tvd,
                'Base X Offset': np.nan,
                'Base Y Offset': np.nan,
                'Base Depth': np.nan,
                'Base TVD': np.nan,
                'Angle Top': general_angle,
                'Angle Base': general_angle
            }


 
            for i in range(1, len(well_df) - 1):

                cum_distance1 = well_df['Cumulative Distance'].iloc[i-1]
                tvd1 = well_df['TVD'].iloc[i-1]
                cum_distance2 = well_df['Cumulative Distance'].iloc[i]
                tvd2 = well_df['TVD'].iloc[i]
                md = well_df['MD'].iloc[i]
                    

                # Create the well path line segment between two tvd points
                well_line = LineString([(tvd1, cum_distance1), (tvd2, cum_distance2)])

                for grid in sorted_grids:
                    z1 = well_df[f'{grid} Closest Z'].iloc[i-1]


                    z2 = well_df[f'{grid} Closest Z'].iloc[i]
                    #print (md)

                    # Create the grid line segment for the same point as we iterate through grid lines
                    grid_line = LineString([(z1, cum_distance1), (z2, cum_distance2)])

                    #This is to tell if its going into or out of a zone depending on slopes its either entering a zone or exiting
                    well_slope = (tvd2 - tvd1) / (cum_distance2 - cum_distance1) if (cum_distance2 - cum_distance1) != 0 else 0
                    grid_slope = (z2 - z1) / (cum_distance2 - cum_distance1) if (cum_distance2 - cum_distance1) != 0 else 0
                    #print (grid_line)
                    #print (well_line)

                    # Calculate the intersection between the well line and the grid line
                    if well_line.intersects(grid_line):
                        intersection_point = well_line.intersection(grid_line)
                
                        if intersection_point.geom_type == 'Point':
                            print('intersection found')
                            x_intersect, y_intersect = intersection_point.x, intersection_point.y
                            

                            # Determine the correct grid based on the slope
                            if well_slope > grid_slope:
                                # Use the grid above (higher in sorted list)
                                grid_index = sorted_grids.index(grid)
                                if grid_index > 0:
                                    intersection_grid = sorted_grids[grid_index - 1]
                                else:
                                    intersection_grid = "Above All"
                            else:
                                # Use the current grid
                                intersection_grid = grid

                            # Use the intersect of cum distance to figure out where the approximate offsets are
                            t = (y_intersect - cum_distance1) / (cum_distance2 - cum_distance1) if (cum_distance2 - cum_distance1) != 0 else 0
                            x_offset_intersect = well_df['X Offset'].iloc[i-1] + t * (well_df['X Offset'].iloc[i] - well_df['X Offset'].iloc[i-1])
                            y_offset_intersect = well_df['Y Offset'].iloc[i-1] + t * (well_df['Y Offset'].iloc[i] - well_df['Y Offset'].iloc[i-1])
                            md_intersect = well_df['MD'].iloc[i-1] + t * (well_df['MD'].iloc[i] - well_df['MD'].iloc[i-1])

                            #Finish off the current zone base
                            if current_intersection:
                                # Complete the current intersection with Base values
                                current_intersection.update({
                                    'Base X Offset': x_offset_intersect,
                                    'Base Y Offset': y_offset_intersect,
                                    'Base Depth': md_intersect,
                                    'Base TVD': z1
                                })
                                intersections_list.append(current_intersection)
                            
                            # Start a new zone as the Top
                            current_intersection = {
                                'UWI': uwi,
                                'Grid Name': intersection_grid,
                                'Top X Offset': x_offset_intersect,
                                'Top Y Offset': y_offset_intersect,
                                'Top Depth': md_intersect,
                                'Top TVD': z1,
                                'Base X Offset': np.nan,
                                'Base Y Offset': np.nan,
                                'Base Depth': np.nan,
                                'Base TVD': np.nan,
                                'Angle Top': general_angle,
                                'Angle Base': general_angle
                            }
                     
            #Finish the last zone with the last point in the directional survey
            if current_intersection:
                current_intersection.update({
                    'Base X Offset': last_x_offset,
                    'Base Y Offset': last_y_offset,
                    'Base Depth': last_md,
                    'Base TVD': last_tvd
                })
                intersections_list.append(current_intersection)
       
        # Convert the list of intersections to a DataFrame
        df_intersections = pd.DataFrame(intersections_list)

        # Add 'Zone Type', 'Attribute Type', and 'Zone Name' columns
        zone_name = self.zone_name_edit.text()
        df_intersections['Zone Type'] = 'Intersections'
        df_intersections['Attribute Type'] = 'Zone'
        df_intersections['Zone Name'] = zone_name

        self.calculate_lateral_length_percentages(df_intersections)
    
        if zone_name not in self.zone_names:
            self.zone_names.append(zone_name)
      
        return df_intersections
    

    def calculate_lateral_length_percentages(self, df_intersections):
        # Create a DataFrame to store the results
        lateral_length_df = pd.DataFrame()

        # Get a list of all unique grids in the intersections
        all_grids = df_intersections['Grid Name'].unique()

        # Ensure all grid columns exist in master_df
        for grid in all_grids:
            if grid not in self.master_df.columns:
                self.master_df[grid] = 0.0  # Initialize missing grid columns with 0%

        # Ensure the 'Total Lateral Length' column exists in master_df
        if 'Total Lateral Length' not in self.master_df.columns:
            self.master_df['Total Lateral Length'] = 0.0

        zone_name = self.existing_zone_name_combo.currentText().strip()

        # Iterate through the unique UWIs in the df_intersections
        for uwi in df_intersections['UWI'].unique():
            # Filter the intersection DataFrame by UWI
            uwi_df = df_intersections[df_intersections['UWI'] == uwi].sort_values(by='Top Depth').reset_index(drop=True)

            # Retrieve the total lateral length for this UWI from self.total_laterals
            total_lateral_length = next(item['Total Lateral Length'] for item in self.total_laterals if item['UWI'] == uwi)

            # Initialize dictionary for storing lengths per grid
            grid_lengths = {grid: 0.0 for grid in all_grids}

            # Iterate through the intersection points to calculate the length in each grid
            for i in range(len(uwi_df)):
                current_grid = uwi_df.iloc[i]['Grid Name']

                # Calculate the MD range between the intersection points
                top_md = uwi_df.iloc[i]['Top Depth']
                base_md = uwi_df.iloc[i]['Base Depth']

                # Calculate the MD difference for the current segment
                segment_length = base_md - top_md

                # Update the length for the current grid
                grid_lengths[current_grid] += segment_length

            # Calculate the percentage of the total lateral length for each grid
            grid_percentages = {grid: (length / total_lateral_length) * 100 for grid, length in grid_lengths.items()}

            # Find the first X and Y offsets from the directional survey data
            first_survey = self.directional_surveys_df[self.directional_surveys_df['UWI'] == uwi].iloc[0]
            first_x_offset = first_survey['X Offset']
            first_y_offset = first_survey['Y Offset']

            # Prepare the row data for master_df
            new_row = {
                'UWI': uwi,
                'Zone Name': zone_name,  # Add the zone name here
                'Attribute Type': 'Well',
                'Zone Type': 'Stages',
                'Total Lateral Length': total_lateral_length,
                'Top X Offset': first_x_offset,
                'Base X Offset': first_x_offset,
                'Top Y Offset': first_y_offset,
                'Base Y Offset': first_y_offset
            }
            new_row.update(grid_percentages)
          

            # Check if this combination of UWI and Zone Name already exists
            existing_row = self.master_df[
                (self.master_df['UWI'] == uwi) & 
                (self.master_df['Zone Name'] == zone_name)
            ]

            if not existing_row.empty:
                # If the row exists, update the existing row for all columns in new_row
                for key, value in new_row.items():
                    # Check if the column exists in master_df
                    if key not in self.master_df.columns:
                        # Add the column to master_df with default values (NaN)
                        self.master_df[key] = pd.NA

                    # Update the value for the existing row
                    self.master_df.loc[
                        (self.master_df['UWI'] == uwi) & 
                        (self.master_df['Zone Name'] == zone_name), key
                    ] = value
            else:
                # If the row does not exist, append the new row
                self.master_df = self.master_df.append(new_row, ignore_index=True)

        # Ensure the zone name is added to the list if it's new
        if zone_name not in self.zone_names:
            self.zone_names.append(zone_name)


    #Update the Master with this new data feels clunky here
    def update_master_df(self, valid_df):
        print('updating')
        # Ensure the master_df has the required columns
        required_columns = [
            'UWI', 'Attribute Type', 'Zone Name', 'Top Depth', 'Base Depth',
            'Top Depth', 'Base Depth', 'Top X Offset', 'Top Y Offset',
            'Base X Offset', 'Base Y Offset', 'Grid Name', 'Zone Type',
            'Angle Top', 'Angle Base'  # Include the angle columns
        ]

        for col in required_columns:
            if col not in self.master_df.columns:
                self.master_df[col] = pd.NA

        for _, row in valid_df.iterrows():
            uwi = row['UWI']
            attribute_type = row['Attribute Type']
            zone_name = row['Zone Name']
            top_md = row['Top Depth']
            base_md = row['Base Depth']
            zone_type = row.get('Zone Type', pd.NA)
            angle_top = row.get('Angle Top')
            angle_base = row.get('Angle Base')


            # Check for matching rows
            matching_rows = self.master_df[
                (self.master_df['UWI'] == uwi) &
                (self.master_df['Attribute Type'] == attribute_type) &
                (self.master_df['Zone Name'] == zone_name) &
                (self.master_df['Top Depth'] == top_md) &
                (self.master_df['Base Depth'] == base_md) &
                (self.master_df['Zone Type'] == zone_type)
            ]

            if not matching_rows.empty:
                # Update existing rows
                for col in valid_df.columns:
                    if col not in ['UWI', 'Attribute Type', 'Zone Name', 'Top Depth', 'Base Depth', 'Zone Type']:
                        if col in self.master_df.columns:
                            self.master_df.loc[
                                (self.master_df['UWI'] == uwi) &
                                (self.master_df['Attribute Type'] == attribute_type) &
                                (self.master_df['Zone Name'] == zone_name) &
                                (self.master_df['Top Depth'] == top_md) &
                                (self.master_df['Base Depth'] == base_md) &
                                (self.master_df['Zone Type'] == zone_type), col
                            ] = row[col]
            
                # Also update the angles
                self.master_df.loc[
                    (self.master_df['UWI'] == uwi) &
                    (self.master_df['Attribute Type'] == attribute_type) &
                    (self.master_df['Zone Name'] == zone_name) &
                    (self.master_df['Top Depth'] == top_md) &
                    (self.master_df['Base Depth'] == base_md) &
                    (self.master_df['Zone Type'] == zone_type), 'Angle Top'
                ] = angle_top
            
                self.master_df.loc[
                    (self.master_df['UWI'] == uwi) &
                    (self.master_df['Attribute Type'] == attribute_type) &
                    (self.master_df['Zone Name'] == zone_name) &
                    (self.master_df['Top Depth'] == top_md) &
                    (self.master_df['Base Depth'] == base_md) &
                    (self.master_df['Zone Type'] == zone_type), 'Angle Base'
                ] = angle_base
            else:
                # Append new rows
                new_row = {
                    'UWI': uwi,
                    'Attribute Type': attribute_type,
                    'Zone Name': zone_name,
                    'Top Depth': top_md,
                    'Base Depth': base_md,
                    'Top X Offset': row.get('Top X Offset', pd.NA),
                    'Top Y Offset': row.get('Top Y Offset', pd.NA),
                    'Base X Offset': row.get('Base X Offset', pd.NA),
                    'Base Y Offset': row.get('Base Y Offset', pd.NA),
                    'Grid Name': row.get('Grid Name', pd.NA),
                    'Zone Type': zone_type,
                    'Angle Top': angle_top,
                    'Angle Base': angle_base
                }
                self.master_df = self.master_df.append(new_row, ignore_index=True)

        print('done')



        #Draw a line from Top hole to Bottom hole figure out its orientation 90 from that is the tick Angle.
    def calculate_angle(self, x1, y1, x2, y2):
        """Calculate the angle between two points in radians, accounting for inverted y-axis, round to the nearest 0, π/2, π, 3π/2, or 2π, and rotate by 90 degrees."""
        dx = x2 - x1
        dy = y1 - y2  # Invert dy to account for the y-axis being inverted

        angle = np.arctan2(dy, dx)  # Calculate the angle in radians

        # Normalize the angle to the range [0, 2π)
        if angle < 0:
            angle += 2 * np.pi

        # Define the target angles (0, π/2, π, 3π/2, 2π) in radians
        target_angles = [0, np.pi/2, np.pi, 3*np.pi/2, 2*np.pi]

        # Round to the nearest target angle
        rounded_angle = min(target_angles, key=lambda x: abs(x - angle))

        # Rotate the angle by 90 degrees (π/2 radians)
        rotated_angle = rounded_angle + np.pi/2

        # Normalize the rotated angle to the range [0, 2π)
        if rotated_angle >= 2 * np.pi:
            rotated_angle -= 2 * np.pi

        print(f"Original angle (radians): {angle}, Rounded angle (radians): {rounded_angle}, Rotated angle (radians): {rotated_angle}")
    
        return rotated_angle