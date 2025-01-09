from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QMessageBox, QComboBox, QListWidget, QPushButton,QCheckBox, QLineEdit, QHBoxLayout, QSpacerItem, QSizePolicy, QListWidgetItem, QMessageBox, QAbstractItemView
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
import numpy as np
import pandas as pd


class ZoneAttributesDialog(QDialog):
    def __init__(self, master_df, directional_surveys_df, grid_info_df, kd_tree_depth_grids, kd_tree_att_grids, zone_names, depth_grid_data_dict, attribute_grid_data_dict, parent=None):
        super(ZoneAttributesDialog, self).__init__(parent)
        self.setWindowTitle("Calculate Zone Attributes")
        self.setMinimumSize(400, 400)

        self.master_df = master_df.copy()  # Make a copy to modify
        self.directional_surveys_df = directional_surveys_df  # Directional surveys data
        self.grid_info_df = grid_info_df  # Store grid info
        self.kd_tree_depth_grids = kd_tree_depth_grids  # KDTree for depth grids
        self.kd_tree_att_grids = kd_tree_att_grids  # KDTree for attribute grids
        self.zone_names = zone_names  # List of zone names
        self.depth_grid_data_dict = depth_grid_data_dict  # Depth grid data dictionary
        self.attribute_grid_data_dict = attribute_grid_data_dict
        self.updated_master = pd.DataFrame()# Attribute grid data dictionary

        layout = QVBoxLayout()

        # Zone Name ComboBox
        self.zone_name_label = QLabel("Zone Name:", self)
        layout.addWidget(self.zone_name_label)

        self.zone_name_combo = QComboBox(self)
        self.zone_name_combo.addItems(self.zone_names)
        layout.addWidget(self.zone_name_combo)

        # Grid Type ComboBox
        self.grid_type_label = QLabel("Select Grid Type:", self)
        layout.addWidget(self.grid_type_label)

        self.grid_type_combo = QComboBox(self)
        self.grid_type_combo.addItems(['Attribute', 'Depth'])
        self.grid_type_combo.currentIndexChanged.connect(self.update_grid_selection)
        layout.addWidget(self.grid_type_combo)

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

        layout.addLayout(grid_list_layout)

        # Calculate Button
        self.calculate_button = QPushButton("Calculate", self)
        self.calculate_button.clicked.connect(self.calculate_zone_attributes)
        self.calculate_button.clicked.connect(self.accept)  #
        layout.addWidget(self.calculate_button)

        # Close Button
        self.close_button = QPushButton("Close", self)
        self.close_button.clicked.connect(self.close)  
        layout.addWidget(self.close_button)

        self.setLayout(layout)
        self.update_grid_selection()

    def update_grid_selection(self):
        grid_type = self.grid_type_combo.currentText()
        if grid_type == 'Attribute':
            grid_names = self.grid_info_df[self.grid_info_df['Type'] == 'Attribute']['Grid'].tolist()
        else:
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

    def calculate_zone_attributes(self):


        zone_name = self.zone_name_combo.currentText()
        selected_grids = [item.text() for item in self.selected_grids_list.findItems("*", Qt.MatchWildcard)]
        grid_type = self.grid_type_combo.currentText()

        # Ensure the DataFrame contains the necessary columns
        required_columns = ['Zone Name', 'Top Depth', 'Base Depth', 'UWI']
        for col in required_columns:
            if col not in self.master_df.columns:
                QMessageBox.warning(self, "Warning", f"The master DataFrame does not contain the necessary column: {col}")
                return

        if not selected_grids:
            QMessageBox.warning(self, "Warning", "No grids selected for calculation.")
            return

        # Pre-calculate grid info dictionary
        grid_info_dict = self.grid_info_df.set_index('Grid').to_dict('index')


        new_attribute_names = []
        for selected_grid in selected_grids:
            if selected_grid not in grid_info_dict:
                QMessageBox.warning(self, "Warning", f"Selected grid '{selected_grid}' is not present in the grid info DataFrame.")
                return

            # Initialize the Avg column
            avg_col_name = f'Avg {selected_grid}'
            if avg_col_name not in self.master_df.columns:
                self.master_df[avg_col_name] = np.nan
                new_attribute_names.append(avg_col_name)

            if grid_type == 'Attribute':
                kd_tree = self.kd_tree_att_grids.get(selected_grid)
                grid_data_dict = self.attribute_grid_data_dict
            else:
                kd_tree = self.kd_tree_depth_grids.get(selected_grid)
                grid_data_dict = self.depth_grid_data_dict

            if kd_tree is None:
                QMessageBox.warning(self, "Warning", f"KDTree for grid '{selected_grid}' is not available.")
                return

            # Filter master_df once
            zones = self.master_df[self.master_df['Zone Name'] == zone_name]
            if zones.empty:
                QMessageBox.warning(self, "Warning", f"No data found for zone '{zone_name}'.")
                return

            for _, zone in zones.iterrows():
                top_md = zone['Top Depth']
                base_md = zone['Base Depth']
                uwi = zone['UWI']
                print(uwi)

                uwi_surveys = self.directional_surveys_df[self.directional_surveys_df['UWI'] == uwi]

                if uwi_surveys.empty:
                    print(f"No well data found for UWI: {uwi} within MD range {top_md} to {base_md}")
                    continue

                # Fetch and process well data directly
                well_data = pd.DataFrame(columns=['MD', 'X Offset', 'Y Offset'])

                top_x, top_y, _, _, _, _ = self.interpolate_offsets(uwi_surveys, top_md)
                base_x, base_y, _, _, _, _ = self.interpolate_offsets(uwi_surveys, base_md)

                well_data = well_data.append({'MD': top_md, 'X Offset': top_x, 'Y Offset': top_y}, ignore_index=True)
                uwi_surveys_offsets = uwi_surveys[(uwi_surveys['MD'] > top_md) & (uwi_surveys['MD'] < base_md)]
                well_data = well_data.append(uwi_surveys_offsets[['MD', 'X Offset', 'Y Offset']])
                well_data = well_data.append({'MD': base_md, 'X Offset': base_x, 'Y Offset': base_y}, ignore_index=True)

                well_data_points = well_data[['X Offset', 'Y Offset']].values
                distances, indices = kd_tree.query(well_data_points)

                avg_values = []
                for index in indices:
                    try:
                        avg_values.append(grid_data_dict[selected_grid][index])
                    except IndexError:
                        # Ignore out-of-bounds index
                        continue

                if avg_values:
                    avg_value = np.mean(avg_values)
                    self.master_df.loc[
                        (self.master_df['Zone Name'] == zone_name) &
                        (self.master_df['Top Depth'] == top_md) &
                        (self.master_df['Base Depth'] == base_md) &
                        (self.master_df['UWI'] == uwi),
                        avg_col_name
                    ] = avg_value
                else:
                    print(f"No valid grid values found for zone: {zone_name}, UWI: {uwi}, MD range: {top_md}-{base_md}")

        # Print summary and check specific rows
        print("Calculation Complete")
        for selected_grid in selected_grids:
            avg_col_name = f'Avg {selected_grid}'
            try:
                print(self.master_df[self.master_df['Zone Name'] == zone_name][['Zone Name', 'Top Depth', 'Base Depth', avg_col_name]].head())
            except KeyError as e:
                print(f"Column {avg_col_name} does not exist in the master DataFrame")

        QMessageBox.information(self, "Calculation Complete", "Average values for selected grids calculated.")
        print(self.master_df)
        self.updated_master = self.master_df
        self.accept()

        return new_attribute_names


    def interpolate_offsets(self, data, md):
    # Find the two bracketing points
        below = data[data['MD'] <= md]
        above = data[data['MD'] >= md]

        if below.empty or above.empty:
            return None, None, None, None, None, None

        below = below.iloc[-1]
        above = above.iloc[0]

        if below['MD'] == above['MD']:  # Exact match
            return below['X Offset'], below['Y Offset'], below['X Offset'], below['Y Offset'], above['X Offset'], above['Y Offset']

        # Linear interpolation
        x = below['X Offset'] + (above['X Offset'] - below['X Offset']) * (md - below['MD']) / (above['MD'] - below['MD'])
        y = below['Y Offset'] + (above['Y Offset'] - below['Y Offset']) * (md - below['MD']) / (above['MD'] - below['MD'])
        return x, y, below['X Offset'], below['Y Offset'], above['X Offset'], above['Y Offset']


class StagesCalculationDialog(QDialog):
    def __init__(self, master_df, directional_surveys_df, zone_names, parent=None):
        super(StagesCalculationDialog, self).__init__(parent)
        self.setWindowTitle("Calculate Stages")
        self.setMinimumSize(400, 300)

        self.master_df = master_df
        self.directional_surveys_df = directional_surveys_df
        self.zone_names = zone_names  # Store zone names
        layout = QVBoxLayout()
        
        # Average Stage Length Input
        self.avg_stage_length_label = QLabel("Average Stage Length:", self)
        layout.addWidget(self.avg_stage_length_label)
        
        self.avg_stage_length_input = QLineEdit(self)
        layout.addWidget(self.avg_stage_length_input)
        
        # Zone Name Input
        self.zone_name_label = QLabel("Zone Name:", self)
        layout.addWidget(self.zone_name_label)
        
        self.zone_name_dropdown = QComboBox(self)
        self.zone_name_dropdown.setEditable(True)
        self.zone_name_dropdown.addItems(self.zone_names)  # Add zone names to the dropdown
        if self.zone_names:  # Check if zone_names is not empty
            self.zone_name_dropdown.setCurrentIndex(0)  # Set to the first zone name
        layout.addWidget(self.zone_name_dropdown)
        
        # Overwrite Existing Stages Checkbox
        self.overwrite_checkbox = QCheckBox("Overwrite existing stages for this zone", self)
        layout.addWidget(self.overwrite_checkbox)
        
        # Calculate Button
        self.calculate_button = QPushButton("Calculate", self)
        self.calculate_button.clicked.connect(self.calculate_stages)
        layout.addWidget(self.calculate_button)
        
        # Close Button
        self.close_button = QPushButton("Close", self)
        self.close_button.clicked.connect(self.accept)
        layout.addWidget(self.close_button)
        
        self.setLayout(layout)
    
    def calculate_stages(self):
        avg_stage_length = float(self.avg_stage_length_input.text())
        zone_name = self.zone_name_dropdown.currentText() or "Stages"  # Use the selected or default zone name
        
        # Check if overwrite checkbox is checked
        if self.overwrite_checkbox.isChecked():
            # Remove existing data for the selected zone
            self.master_df = self.master_df[self.master_df['Zone Name'] != zone_name]
        
        stages_list = []
        
        # Filter directional surveys based on the selected zone
        existing_uwis = set(self.master_df[self.master_df['Zone Name'] == zone_name]['UWI'])
        
        # Group by UWI
        for uwi, group_df in self.directional_surveys_df.groupby('UWI'):
            if uwi in existing_uwis and not self.overwrite_checkbox.isChecked():
                continue  # Skip wells that already have stages for this zone if not overwriting
            
            group_df = group_df.sort_values(by='MD').reset_index(drop=True)
            group_df['Inclination'] = np.nan
        
            # Calculate inclination
            for i in range(1, len(group_df)):
                current_row = group_df.iloc[i]
                previous_row = group_df.iloc[i - 1]
                delta_md = current_row['MD'] - previous_row['MD']
                delta_tvd = current_row['TVD'] - previous_row['TVD']
                if delta_md != 0:
                    inclination = np.degrees(np.arccos(delta_tvd / delta_md))
                    group_df.at[i, 'Inclination'] = inclination
        
            # Filter lateral points
            lateral_df = group_df[group_df['Inclination'] < 91]
            if lateral_df.empty:
                continue
        
            # Calculate total lateral length
            total_lateral = lateral_df['MD'].max() - lateral_df['MD'].min()
            num_stages = int(round(total_lateral / avg_stage_length))
            perfect_avg_stage_length = total_lateral / num_stages
        
            # Generate stage data
            for i in range(num_stages):
                start_md = lateral_df['MD'].min() + i * perfect_avg_stage_length
                end_md = start_md + perfect_avg_stage_length
                if i == num_stages - 1:
                    end_md = lateral_df['MD'].max()
                stages_list.append({
                    'UWI': uwi,
                    'Zone Name': zone_name,
                    'Top Depth': round(start_md, 2),
                    'Base Depth': round(end_md, 2),
                    'Attribute Type': 'Zone',
                    'Zone Type': 'Stage'
                })


        if not stages_list:
            QMessageBox.warning(self, "Warning", "No lateral points found with inclination greater than 85 degrees for any UWI.")
            return
    
        # Create DataFrame for stages
        stages_df = pd.DataFrame(stages_list)
       

        # Initialize the columns for offsets and angles
        stages_df['Top X Offset'] = None
        stages_df['Top Y Offset'] = None
        stages_df['Base X Offset'] = None
        stages_df['Base Y Offset'] = None
        stages_df['Angle Top'] = None
        stages_df['Angle Base'] = None

        for i, row in stages_df.iterrows():
            uwi = row['UWI']
            top_md = row['Top Depth']
            base_md = row['Base Depth']
            top_x, top_y, base_x, base_y = self.calculate_offsets(uwi, top_md, base_md)

            stages_df.at[i, 'Top X Offset'] = top_x
            stages_df.at[i, 'Top Y Offset'] = top_y
            stages_df.at[i, 'Base X Offset'] = base_x
            stages_df.at[i, 'Base Y Offset'] = base_y
        
        if zone_name not in self.zone_names:
            self.zone_names.append(zone_name)
    


                    # Reorder columns
        columns = ['UWI', 'Attribute Type', 'Zone Name', 'Zone Type', 'Top Depth', 'Base Depth', 'Top X Offset', 'Top Y Offset', 'Base X Offset', 'Base Y Offset', 'Angle Top', 'Angle Base'] + \
                  [col for col in stages_df.columns if col not in ['UWI', 'Attribute Type', 'Zone Name', 'Zone Type', 'Top Depth', 'Base Depth', 'Top X Offset', 'Top Y Offset', 'Base X Offset', 'Base Y Offset', 'Angle Top', 'Angle Base']]
        stages_df = stages_df[columns]
        stages_df = self.calculate_angles(stages_df)

        QMessageBox.information(self, "Calculation Complete", f"Total Stages: {len(stages_list)}")
        self.accept()

        self.master_df = self.master_df.append(stages_df, ignore_index=True)





    def calculate_offsets(self, uwi, top_md, base_md):
        well_data = self.directional_surveys_df[self.directional_surveys_df['UWI'] == uwi]
        if well_data.empty:
            return None, None, None, None

        # Interpolate for top and base MDs
        top_x, top_y, _, _, _, _ = self.interpolate(top_md, well_data)
        base_x, base_y, _, _, _, _ = self.interpolate(base_md, well_data)

        return top_x, top_y, base_x, base_y

    def interpolate(self, md, data):
        # Find the two bracketing points
        below = data[data['MD'] <= (md + .1)]
        above = data[data['MD'] >= (md - .1)]
        if below.empty or above.empty:
            return None, None, None, None, None, None

        below = below.iloc[-1]
        above = above.iloc[0]

        if below['MD'] == above['MD']:  # Exact match
            return below['X Offset'], below['Y Offset'], below['X Offset'], below['Y Offset'], above['X Offset'], above['Y Offset']

        # Linear interpolation
        x = below['X Offset'] + (above['X Offset'] - below['X Offset']) * (md - below['MD']) / (above['MD'] - below['MD'])
        y = below['Y Offset'] + (above['Y Offset'] - below['Y Offset']) * (md - below['MD']) / (above['MD'] - below['MD'])
        return x, y, below['X Offset'], below['Y Offset'], above['X Offset'], above['Y Offset']

    def calculate_angles(self, stages_df):
        # Loop over each unique UWI in the valid_df
        for uwi in stages_df['UWI'].unique():
            uwi_data = stages_df[stages_df['UWI'] == uwi]

            # Extract the first and last rows for the current UWI
            first_row = uwi_data.iloc[0]
            last_row = uwi_data.iloc[-1]

            # Extract the corresponding X and Y offsets
            x1, y1 = first_row['Top X Offset'], first_row['Top Y Offset']
            x2, y2 = last_row['Base X Offset'], last_row['Base Y Offset']

            # Calculate the angle in radians
            dx, dy = x2 - x1, y1 - y2
            angle = np.arctan2(dy, dx)

            # Normalize the angle to [0, 2π)
            if angle < 0:
                angle += 2 * np.pi

            # Define target angles for snapping
            target_angles = [0, np.pi/2, np.pi, 3*np.pi/2, 2*np.pi]

            # Round to the nearest target angle and rotate by 90 degrees
            rounded_angle = min(target_angles, key=lambda x: abs(x - angle))
            rotated_angle = (rounded_angle + np.pi/2) % (2 * np.pi)

            # Update the angle for all rows with the current UWI
            stages_df.loc[stages_df['UWI'] == uwi, 'Angle Top'] = rotated_angle
            stages_df.loc[stages_df['UWI'] == uwi, 'Angle Base'] = rotated_angle
        return stages_df

class WellAttributesDialog(QDialog):
    def __init__(self, parent=None):
        super(WellAttributesDialog, self).__init__(parent)
        self.setWindowTitle("Calculate Well Attributes")
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Well Attributes Calculation"))
        # Add widgets for well attributes calculation
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.accept)
        layout.addWidget(close_button)
        self.setLayout(layout)
