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

        # Create widgets
        self.zone_name_label = QLabel("Zone Name:", self)
        self.zone_name_edit = QLineEdit(self)
  # Make the combo box editable



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
        """Create a DataFrame for each well with X, Y offsets, TVD, and closest Z values for each grid."""
        data = []

        for uwi, group in self.directional_surveys_df.groupby('UWI'):
            print(f"Processing UWI: {uwi}")
            for i, row in group.iterrows():
                x = row['X Offset']
                y = row['Y Offset']
                tvd = row['TVD']
                md = row['MD']

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
                    'MD' : md
                }
                # Add the closest Z values for each grid to the row data
                for grid in self.kd_tree_depth_grids.keys():
                    row_data[f'{grid} Closest Z'] = closest_z_values.get(grid)

                data.append(row_data)

        df = pd.DataFrame(data)
        print(df)
        
        # Assuming df is already sorted by UWI and TVD
        selected_grids = [self.selected_grids_list.item(i).text() for i in range(self.selected_grids_list.count())]
        intersections = self.find_tvd_grid_intersections(df, selected_grids)
        print(intersections)
        self.update_master_df(intersections)
     



    def calculate(self):
        grid_df = self.create_grid_dataframe()
        if not grid_df.empty:
            print(grid_df)
            # You can do additional processing here if needed
        else:
            print("No intersections to process")


    def find_tvd_grid_intersections(self, df, selected_grids):
        intersections_dict = {}

        # Process each well individually
        for uwi in df['UWI'].unique():
            well_df = df[df['UWI'] == uwi]

            # Get the last row's values for the well
            last_row = well_df.iloc[-1]
            last_x_offset = last_row['X Offset']
            last_y_offset = last_row['Y Offset']
            last_md = last_row['MD']
            last_tvd = last_row['TVD']

            for grid in selected_grids:
                z_values = well_df[f'{grid} Closest Z'].values

                for i in range(1, len(well_df) - 1):
                    tvd1 = well_df['TVD'].iloc[i-1]
                    tvd2 = well_df['TVD'].iloc[i]
                    tvd3 = well_df['TVD'].iloc[i+1]
                    z1 = z_values[i]

                    # Check for intersection based on the specified conditions
                    if tvd3 <= z1 <= tvd2:
                        t = (z1 - tvd3) / (tvd2 - tvd3) if (tvd2 - tvd3) != 0 else 0
                    elif tvd2 >= z1 >= tvd1:
                        t = (z1 - tvd2) / (tvd1 - tvd2) if (tvd1 - tvd2) != 0 else 0
                    else:
                        continue  # Z1 is not within the TVD range we are interested in

                    # Calculate intersection coordinates
                    x_intersect = well_df['X Offset'].iloc[i] + t * (well_df['X Offset'].iloc[i+1] - well_df['X Offset'].iloc[i])
                    y_intersect = well_df['Y Offset'].iloc[i] + t * (well_df['Y Offset'].iloc[i+1] - well_df['Y Offset'].iloc[i])
                    md_intersect = well_df['MD'].iloc[i] + t * (well_df['MD'].iloc[i+1] - well_df['MD'].iloc[i])

                    # Create intersection entry
                    intersection = {
                        'UWI': uwi,
                        'Grid Name': grid,
                        'Top X Offset': x_intersect,
                        'Top Y Offset': y_intersect,
                        'Top Depth': md_intersect,
                        'Top TVD': z1,
                        'Base X Offset': np.nan,
                        'Base Y Offset': np.nan,
                        'Base Depth': np.nan,
                        'Base TVD': np.nan
                    }

                    key = (uwi, grid)
                    if key in intersections_dict:
                        existing = intersections_dict[key]
                        if pd.isna(existing.get('Base X Offset')):
                            existing.update({
                                'Base X Offset': intersection['Top X Offset'],
                                'Base Y Offset': intersection['Top Y Offset'],
                                'Base Depth': intersection['Top Depth'],
                                'Base TVD': intersection['Top TVD']
                            })
                        elif pd.isna(existing.get('Top X Offset')):
                            intersections_dict[key] = {
                                'UWI': intersection['UWI'],
                                'Grid Name': grid,
                                'Top X Offset': intersection['Top X Offset'],
                                'Top Y Offset': intersection['Top Y Offset'],
                                'Base X Offset': np.nan,
                                'Base Y Offset': np.nan,
                                'Top Depth': intersection['Top Depth'],
                                'Base Depth': np.nan,
                                'Top TVD': intersection['Top TVD'],
                                'Base TVD': np.nan
                            }
                    else:
                        intersections_dict[key] = intersection

                    print(f"Intersection found for {grid}:")
                    print(f"TVD1: {tvd1}, TVD2: {tvd2}, Z1: {z1}")
                    print(f"Intersection Coordinates: X={x_intersect}, Y={y_intersect}, MD={md_intersect}")

            # Fill missing base values with the last point in the directional survey
            for key, value in intersections_dict.items():
                if pd.isna(value.get('Base X Offset')):
                    value.update({
                        'Base X Offset': last_x_offset,
                        'Base Y Offset': last_y_offset,
                        'Base Depth': last_md,
                        'Base TVD': last_tvd
                    })

        df = pd.DataFrame(list(intersections_dict.values()))
        zone_name = self.zone_name_edit.text()
        # Add 'Zone Type', 'Attribute Type', and 'Zone Name' columns

        df['Zone Type'] = 'Intersections'
        df['Attribute Type'] = 'Zone'
        df['Zone Name'] = zone_name
        if zone_name not in self.zone_names:
            self.zone_names.append(zone_name)

        return df


    def update_master_df(self, valid_df):
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

            # Calculate angles
            angle_top = self.calculate_angle(row['Top X Offset'], row['Top Y Offset'], row['Base X Offset'], row['Base Y Offset'])
            angle_base = self.calculate_angle(row['Base X Offset'], row['Base Y Offset'], row['Top X Offset'], row['Top Y Offset'])

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
                    'Top Depth': row.get('Top Depth', pd.NA),
                    'Base Depth': row.get('Base Depth', pd.NA),
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

    def calculate_angle(self, x1, y1, x2, y2):
        """Calculate the angle between two points."""
        dx = x2 - x1
        dy = y2 - y1
        angle = np.arctan2(dy, dx)  # Returns the angle in radians
        return np.degrees(angle)  # Convert radians to degrees (optional)