from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QComboBox, 
                              QPushButton, QLabel, QMessageBox, QCheckBox, QListWidget,
                              QAbstractItemView, QSizePolicy, QSpacerItem,QLineEdit)
from PySide6.QtCore import Qt
import numpy as np
import pandas as pd

class ZoneAttributesDialog(QDialog):
    def __init__(self, db_manager, grid_info_df, kd_tree_depth_grids, 
                 kd_tree_att_grids, depth_grid_data_dict, 
                 attribute_grid_data_dict, parent=None):
        super(ZoneAttributesDialog, self).__init__(parent)
        self.setWindowTitle("Sample Grid Values")
        self.setMinimumSize(500, 400)
        
        self.db_manager = db_manager
        self.grid_info_df = grid_info_df
        self.kd_tree_depth_grids = kd_tree_depth_grids
        self.kd_tree_att_grids = kd_tree_att_grids
        self.depth_grid_data_dict = depth_grid_data_dict
        self.attribute_grid_data_dict = attribute_grid_data_dict
        
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout()

        # Zone Selection
        zone_layout = QHBoxLayout()
        self.zone_label = QLabel("Zone:", self)
        zone_layout.addWidget(self.zone_label)
        
        self.zone_combo = QComboBox(self)
        self.populate_zone_list()
        zone_layout.addWidget(self.zone_combo)
        layout.addLayout(zone_layout)

        # Grid Type Selection
        grid_type_layout = QHBoxLayout()
        self.grid_type_label = QLabel("Grid Type:", self)
        grid_type_layout.addWidget(self.grid_type_label)
        
        self.grid_type_combo = QComboBox(self)
        self.grid_type_combo.addItems(['Attribute', 'Depth'])
        self.grid_type_combo.currentIndexChanged.connect(self.update_available_grids)
        grid_type_layout.addWidget(self.grid_type_combo)
        layout.addLayout(grid_type_layout)

        # Grid Selection Lists
        grid_list_layout = QHBoxLayout()

        # Available Grids
        available_layout = QVBoxLayout()
        available_layout.addWidget(QLabel("Available Grids:"))
        self.available_grids = QListWidget()
        self.available_grids.setSelectionMode(QAbstractItemView.ExtendedSelection)
        available_layout.addWidget(self.available_grids)
        grid_list_layout.addLayout(available_layout)

        # Arrow Buttons
        arrow_layout = QVBoxLayout()
        arrow_layout.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding))
        
        for button_info in [
            ("→", self.move_selected_right),
            ("⇉", self.move_all_right),
            ("←", self.move_selected_left),
            ("⇇", self.move_all_left)
        ]:
            btn = QPushButton(button_info[0])
            btn.clicked.connect(button_info[1])
            arrow_layout.addWidget(btn)
        
        arrow_layout.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding))
        grid_list_layout.addLayout(arrow_layout)

        # Selected Grids
        selected_layout = QVBoxLayout()
        selected_layout.addWidget(QLabel("Selected Grids:"))
        self.selected_grids = QListWidget()
        self.selected_grids.setSelectionMode(QAbstractItemView.ExtendedSelection)
        selected_layout.addWidget(self.selected_grids)
        grid_list_layout.addLayout(selected_layout)

        layout.addLayout(grid_list_layout)

        # Sampling Options
        self.use_intermediate = QCheckBox("Sample intermediate points")
        self.use_intermediate.setToolTip("Sample additional points between top and base")
        layout.addWidget(self.use_intermediate)

        # Buttons
        button_layout = QHBoxLayout()
        self.sample_button = QPushButton("Sample Grid Values", self)
        self.sample_button.clicked.connect(self.sample_grid_values)
        button_layout.addWidget(self.sample_button)

        self.close_button = QPushButton("Close", self)
        self.close_button.clicked.connect(self.reject)
        button_layout.addWidget(self.close_button)

        layout.addLayout(button_layout)
        self.setLayout(layout)
        
        # Initialize grid list
        self.update_available_grids()

    def populate_zone_list(self):
        pass


    def update_available_grids(self):
        """Update available grids based on selected type"""
        self.available_grids.clear()
        grid_type = self.grid_type_combo.currentText()
        
        # Filter grid info by type
        grids = self.grid_info_df[
            self.grid_info_df['Type'] == grid_type
        ]['Grid'].tolist()
        
        # Add to available list if not already in selected
        for grid in grids:
            if self.selected_grids.findItems(grid, Qt.MatchExactly) == []:
                self.available_grids.addItem(grid)

    def move_selected_right(self):
        for item in self.available_grids.selectedItems():
            self.selected_grids.addItem(self.available_grids.takeItem(
                self.available_grids.row(item)
            ))

    def move_all_right(self):
        while self.available_grids.count() > 0:
            self.selected_grids.addItem(
                self.available_grids.takeItem(0)
            )

    def move_selected_left(self):
        for item in self.selected_grids.selectedItems():
            self.available_grids.addItem(self.selected_grids.takeItem(
                self.selected_grids.row(item)
            ))

    def move_all_left(self):
        while self.selected_grids.count() > 0:
            self.available_grids.addItem(
                self.selected_grids.takeItem(0)
            )

    def get_intermediate_points(self, top_point, base_point, num_points=5):
        """Generate evenly spaced points between top and base"""
        points = []
        for i in range(num_points):
            fraction = i / (num_points - 1)
            x = top_point[0] + (base_point[0] - top_point[0]) * fraction
            y = top_point[1] + (base_point[1] - top_point[1]) * fraction
            points.append([x, y])
        return points

    def sample_grid_values(self):
        """Sample grid values and update zone table."""
        try:
            zone_name = self.zone_combo.currentText()
            grid_type = self.grid_type_combo.currentText()
            selected_grids = [self.selected_grids.item(i).text() for i in range(self.selected_grids.count())]

            if not selected_grids:
                return QMessageBox.warning(self, "Error", "Please select at least one grid")

            # Fetch zone data from the database (includes correct column names)
            zone_data = self.db_manager.fetch_zone_table_data(zone_name)
            zone_df = pd.DataFrame(zone_data[0], columns=zone_data[1])  # Convert to DataFrame

            if zone_df.empty:
                return QMessageBox.warning(self, "Error", f"No data found for zone '{zone_name}'")

            # Ensure the necessary columns exist with the original naming
            required_columns = ["Top_X_Offset", "Top_Y_Offset", "Base_X_Offset", "Base_Y_Offset"]
            missing_columns = [col for col in required_columns if col not in zone_df.columns]
        
            if missing_columns:
                return QMessageBox.warning(self, "Error", f"Missing required columns: {', '.join(missing_columns)}")

            # Extract Top/Base points using correct column names
            top_points = zone_df[['Top_X_Offset', 'Top_Y_Offset']].values
            base_points = zone_df[['Base_X_Offset', 'Base_Y_Offset']].values

            # Select KD-Tree and Grid Data
            kd_trees, grid_data = (
                (self.kd_tree_att_grids, self.attribute_grid_data_dict) if grid_type == 'Attribute' 
                else (self.kd_tree_depth_grids, self.depth_grid_data_dict)
            )

            # Process selected grids
            for grid_name in selected_grids:
                if grid_name not in kd_trees:
                    print(f"Skipping {grid_name} - no KD tree found")
                    continue

                avg_col_name = f'Avg_{grid_name}'
                zone_df[avg_col_name] = np.nan  # Initialize column

                # Perform sampling (vectorized)
                if self.use_intermediate.isChecked():
                    sampled_points = np.concatenate([
                        self.get_intermediate_points(top, base) for top, base in zip(top_points, base_points)
                    ])
                    _, indices = kd_trees[grid_name].query(sampled_points)
                    avg_values = np.mean([grid_data[grid_name][idx] for idx in indices.flatten()], axis=1)
                else:
                    _, top_indices = kd_trees[grid_name].query(top_points)
                    _, base_indices = kd_trees[grid_name].query(base_points)
                    avg_values = (grid_data[grid_name][top_indices] + grid_data[grid_name][base_indices]) / 2

                zone_df[avg_col_name] = avg_values

            # Bulk update zone data with original column names
            self.db_manager.update_zone_data(zone_name, zone_df)

            QMessageBox.information(self, "Success", f"Processed {len(selected_grids)} grids for zone {zone_name}")
            self.accept()

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error sampling grid values: {str(e)}")




class StagesCalculationDialog(QDialog):
    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Calculate Stages")
        self.setMinimumSize(400, 200)
        self.setStyleSheet(self.get_dark_style())

        self.db_manager = db_manager
        self.zone_names = [zone[0] for zone in self.db_manager.fetch_zone_names_by_type('Zone')]

        # Standardize directional survey DataFrame
        self.directional_surveys_df = pd.DataFrame(self.db_manager.get_directional_surveys_dataframe())
        self.directional_surveys_df.columns = self.directional_surveys_df.columns.str.lower().str.strip()

        # Rename columns
        column_mapping = {
            "uwi": "UWI", "md": "MD", "tvd": "TVD",
            "x offset": "X Offset", "y offset": "Y Offset"
        }
        self.directional_surveys_df.rename(columns=column_mapping, inplace=True)

        layout = QVBoxLayout(self)

        # Average Stage Length
        layout.addWidget(QLabel("Average Stage Length:", self))
        self.avg_stage_length_input = QLineEdit(self)
        layout.addWidget(self.avg_stage_length_input)

        # Zone Name
        layout.addWidget(QLabel("Zone Name:", self))
        self.zone_name_dropdown = QComboBox(self)
        self.zone_name_dropdown.setEditable(True)
        self.zone_name_dropdown.addItem("Select Zone") if not self.zone_names else self.zone_name_dropdown.addItems(self.zone_names)
        layout.addWidget(self.zone_name_dropdown)

        # Button Layout (Side-by-Side on the Right)
        button_layout = QHBoxLayout()
        button_layout.addStretch()  # Push buttons to the right

        self.calculate_button = QPushButton("Calculate", self)
        self.close_button = QPushButton("Close", self)

        # Set button size
        self.calculate_button.setFixedWidth(100)
        self.close_button.setFixedWidth(100)

        button_layout.addWidget(self.calculate_button)
        button_layout.addWidget(self.close_button)

        layout.addLayout(button_layout)

        # Connect buttons
        self.calculate_button.clicked.connect(self.calculate_stages)
        self.close_button.clicked.connect(self.accept)

        self.setLayout(layout)


    def get_dark_style(self):
        """Returns dark theme styles"""
        return """
            QDialog { background-color: #222; color: white; }
            QLabel { color: white; }
            QLineEdit, QComboBox, QPushButton {
                background-color: #333; color: white;
                border: 1px solid white; padding: 5px;
            }
            QPushButton:hover { background-color: #444; }
            QPushButton:pressed { background-color: #555; }
        """

    def calculate_stages(self):
        try:
            avg_stage_length = float(self.avg_stage_length_input.text())
            if avg_stage_length <= 0:
                raise ValueError
        except ValueError:
            QMessageBox.warning(self, "Invalid Input", "Please enter a valid positive number for average stage length.")
            return

        # Get selected zone name
        zone_name = self.zone_name_dropdown.currentText().strip()
        zone_table_name = self.db_manager.get_table_name_from_zone(zone_name)
        # Validate zone name
        if not zone_name:
            QMessageBox.warning(self, "No Zone Name", "Please enter or select a valid zone name.")
            return

        # Get existing UWIs for the selected zone
        zone_depth_df = self.db_manager.fetch_zone_depth_data(zone_table_name)
        
        # Make sure we're working with strings for UWI comparison
        existing_UWIs = set(str(uwi) for uwi in zone_depth_df['UWI']) if not zone_depth_df.empty else set()
        
        # Convert all UWIs in directional surveys to strings for consistent comparison
        self.directional_surveys_df['UWI'] = self.directional_surveys_df['UWI'].astype(str)
        
        # Filter out any UWIs that already exist in the zone
        new_surveys_df = self.directional_surveys_df[~self.directional_surveys_df['UWI'].isin(existing_UWIs)]
        
        if new_surveys_df.empty:
            QMessageBox.warning(self, "No New Wells", 
                              "All wells in the directional survey already have stages calculated for this zone.")
            return
        
        stages_list = []

        for UWI, group_df in new_surveys_df.groupby('UWI'):
            group_df = group_df.sort_values(by='MD').reset_index(drop=True)
            group_df['Inclination'] = np.nan

            # Calculate inclination
            for i in range(1, len(group_df)):
                delta_md = group_df.at[i, 'MD'] - group_df.at[i - 1, 'MD']
                delta_tvd = group_df.at[i, 'TVD'] - group_df.at[i - 1, 'TVD']
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
                    'UWI': UWI,
                    'Zone Name': zone_name,
                    'Top Depth': round(start_md, 2),
                    'Base Depth': round(end_md, 2),
                })

        if not stages_list:
            QMessageBox.warning(self, "Warning", "No valid stages could be calculated for the new wells.")
            return

        # Create DataFrame for new stages
        new_stages_df = pd.DataFrame(stages_list)

        # Initialize the columns for offsets and angles
        for col in ['Top X Offset', 'Top Y Offset', 'Base X Offset', 'Base Y Offset', 'Angle Top', 'Angle Base']:
            new_stages_df[col] = None

        # Calculate offsets and angles
        for i, row in new_stages_df.iterrows():
            UWI = row['UWI']
            top_md = row['Top Depth']
            base_md = row['Base Depth']
            top_x, top_y, base_x, base_y = self.calculate_offsets(UWI, top_md, base_md)

            new_stages_df.at[i, 'Top X Offset'] = top_x
            new_stages_df.at[i, 'Top Y Offset'] = top_y
            new_stages_df.at[i, 'Base X Offset'] = base_x
            new_stages_df.at[i, 'Base Y Offset'] = base_y

        # Calculate angles for the new stages
        new_stages_df = self.calculate_angles(new_stages_df)

        # Add zone name to list if it's new
        if zone_name not in self.zone_names:
            self.zone_names.append(zone_name)

        # Save the new stages to the database
        success = self.db_manager.append_zone_data(zone_table_name, new_stages_df)

        if success:
            QMessageBox.information(self, "Calculation Complete",
                                  f"Added stages for  new wells")
        else:
            QMessageBox.warning(self, "Save Error",
                              "There was an error saving the new stages to the database.")

        self.accept()
        return self.zone_names

    def calculate_offsets(self, UWI, top_md, base_md):
        well_data = self.directional_surveys_df[self.directional_surveys_df['UWI'] == UWI]
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
        for UWI in stages_df['UWI'].unique():
            UWI_data = stages_df[stages_df['UWI'] == UWI]

            # Extract the first and last rows for the current UWI
            first_row = UWI_data.iloc[0]
            last_row = UWI_data.iloc[-1]

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
            stages_df.loc[stages_df['UWI'] == UWI, 'Angle Top'] = rotated_angle
            stages_df.loc[stages_df['UWI'] == UWI, 'Angle Base'] = rotated_angle

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
