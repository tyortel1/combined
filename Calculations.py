from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QComboBox, QListWidget, QPushButton, QLineEdit, QHBoxLayout, QSpacerItem, QSizePolicy, QListWidgetItem, QMessageBox, QAbstractItemView
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon
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
        layout.addWidget(self.calculate_button)

        # Close Button
        self.close_button = QPushButton("Close", self)
        self.close_button.clicked.connect(self.accept)
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
        import numpy as np
        import pandas as pd
        from PyQt5.QtWidgets import QMessageBox

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
        self.setMinimumSize(400, 250)

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
        self.zone_name_label = QLabel("Zone Name (Default: Stages):", self)
        layout.addWidget(self.zone_name_label)
        
        self.zone_name_input = QLineEdit(self)
        self.zone_name_input.setPlaceholderText("Stages")
        layout.addWidget(self.zone_name_input)
        
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
        zone_name = self.zone_name_input.text() or "Stages"  # Use "Stages" if no input
        
        # Ensure the DataFrame contains the necessary columns
        if 'MD' not in self.directional_surveys_df.columns or 'TVD' not in self.directional_surveys_df.columns or 'UWI' not in self.directional_surveys_df.columns:
            QMessageBox.warning(self, "Warning", "Directional surveys data does not contain necessary columns.")
            return

        stages_list = []

        # Group by UWI
        for uwi, group_df in self.directional_surveys_df.groupby('UWI'):
            # Sort DataFrame by MD
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
            lateral_df = group_df[group_df['Inclination'] < 92]
           
            if lateral_df.empty:
                continue
        
            # Calculate total lateral length
            total_lateral = lateral_df['MD'].max() - lateral_df['MD'].min()

        
            # Calculate number of stages
            num_stages = int(round(total_lateral / avg_stage_length))
            perfect_avg_stage_length = total_lateral / num_stages
        
            # Generate stage data
            for i in range(num_stages):
                start_md = lateral_df['MD'].min() + i * perfect_avg_stage_length
                end_md = start_md + perfect_avg_stage_length

                if i == num_stages - 1:  # Ensure the very last stage's base depth is equal to the last MD value
                    end_md = lateral_df['MD'].max()
                top_depth = round(start_md, 2)
                bottom_depth = round(end_md, 2)

            
                stages_list.append({
                    'UWI': uwi,
                    'Zone Name': zone_name,  # Use the provided or default stage name
                    'Top Depth': top_depth,
                    'Base Depth': bottom_depth,
                    'Attribute Type': 'Zone',
                    'Zone Type': 'Stage'
                })
    
        if not stages_list:
            QMessageBox.warning(self, "Warning", "No lateral points found with inclination greater than 85 degrees for any UWI.")
            return
    
        # Create DataFrame for stages
        stages_df = pd.DataFrame(stages_list)
    
        # Optionally, update master_df or save results
        self.master_df = self.master_df.append(stages_df, ignore_index=True)
        
        # Update self.zone_names with the new zone name
        if zone_name not in self.zone_names:
            self.zone_names.append(zone_name)
    
        QMessageBox.information(self, "Calculation Complete", f"Total Stages: {len(stages_list)}")
        self.accept()




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
