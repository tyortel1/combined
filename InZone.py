from PySide6.QtWidgets import (QDialog, QLabel, QComboBox, QMessageBox, 
                               QPushButton, QVBoxLayout, QWidget, QVBoxLayout, QHBoxLayout, QFormLayout)
from PySide6.QtGui import QIcon
from PySide6.QtCore import Qt
import pandas as pd
from shapely.geometry import LineString
import numpy as np
from PySide6.QtWidgets import QProgressDialog
from StyledTwoListSelector import TwoListSelector
from StyledDropdown import StyledDropdown
from StyledButton import StyledButton

class InZoneDialog(QDialog):
    def __init__(self, db_manager, directional_surveys_df, grid_info_df, kd_tree_depth_grids,
                 kd_tree_att_grids, zone_names, depth_grid_data_dict, attribute_grid_data_dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Find Wells in Zone")
        self.db_manager = db_manager
        self.directional_surveys_df = directional_surveys_df
        self.grid_info_df = grid_info_df
        self.kd_tree_depth_grids = kd_tree_depth_grids
        self.kd_tree_att_grids = kd_tree_att_grids
        self.zone_names = zone_names
        self.depth_grid_data_dict = depth_grid_data_dict
        self.attribute_grid_data_dict = attribute_grid_data_dict
        self.sorted_grid_order = []
        self.total_laterals = []
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(10)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Calculate label width for consistency
        labels = ["Zone Name"]
        StyledDropdown.calculate_label_width(labels)
        
        # Create form layout for the zone name dropdown
        form_layout = QFormLayout()
        form_layout.setContentsMargins(10, 0, 10, 0)
        
        # Zone Name Selection using StyledDropdown
        self.zone_name_dropdown = StyledDropdown("Zone Name", parent=self)
        self.zone_name_dropdown.combo.setEditable(True)
        self.zone_name_dropdown.setItems(self.zone_names)
        form_layout.addRow(self.zone_name_dropdown.label, self.zone_name_dropdown.combo)
        
        layout.addLayout(form_layout)
        
        # Create the grid selector
        self.grid_selector = TwoListSelector(
            left_title="Available Grids",
            right_title="Selected Grids"
        )
        self.grid_selector.setFullHeight(True)
        layout.addWidget(self.grid_selector)
        
        # Button layout - horizontal with right alignment
        button_layout = QHBoxLayout()
        button_layout.addStretch()  # This pushes buttons to the right
        
        self.calculate_button = StyledButton("Calculate", "function")
        self.calculate_button.clicked.connect(self.create_grid_dataframe)
        button_layout.addWidget(self.calculate_button)
        
        self.close_button = StyledButton("Close", "close")
        self.close_button.clicked.connect(self.accept)
        button_layout.addWidget(self.close_button)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
        
        self.update_grid_selection()


    def update_grid_selection(self):
        """Update the available grids list with depth grids."""
        grid_names = self.grid_info_df[self.grid_info_df['Type'] == 'Depth']['Grid'].tolist()
        self.grid_selector.set_left_items(grid_names)

    def create_grid_dataframe(self):
        """Create and process the grid data."""
        zone_name = self.zone_name_dropdown.combo.currentText().strip()

        if not zone_name:
            QMessageBox.warning(self, "Error", "Zone name cannot be empty. Please enter a valid zone name.")
            return

        # Create DataFrame with well and grid data
        data = []
        for UWI, group in self.directional_surveys_df.groupby('UWI'):
            for i, row in group.iterrows():
                x = row['X Offset']
                y = row['Y Offset']
                tvd = row['TVD']
                md = row['MD']
                cum_distance = row['Cumulative Distance']

                closest_z_values = {}
                for grid, kdtree in self.kd_tree_depth_grids.items():
                    if kdtree.data.size > 0:
                        distances, indices = kdtree.query([x, y])
                        if indices < len(self.depth_grid_data_dict[grid]):
                            closest_z_values[grid] = self.depth_grid_data_dict[grid][indices]
                        else:
                            closest_z_values[grid] = None
                    else:
                        closest_z_values[grid] = None

                # Prepare row data
                row_data = {
                    'UWI': UWI,
                    'X Offset': x,
                    'Y Offset': y,
                    'TVD': tvd,
                    'MD': md,
                    'Cumulative Distance': cum_distance
                }
                
                # Add closest Z values
                for grid in self.kd_tree_depth_grids.keys():
                    row_data[f'{grid} Closest Z'] = closest_z_values.get(grid)

                data.append(row_data)

        # Create main DataFrame
        df = pd.DataFrame(data)
        
        # Get selected grids from the TwoListSelector
        selected_grids = self.grid_selector.get_right_items()
        
        self.sorted_grid_order = self.get_sorted_grid_order(selected_grids)
        
        try:
            # Find intersections
            intersections = self.find_tvd_grid_intersections(df, selected_grids)
            
            # Create percentage data
            percentage_data = self.create_percentage_dataframe(intersections)
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to process and save zone data: {str(e)}")

    def get_sorted_grid_order(self, selected_grids):
        """Sort grids by average TVD."""
        grid_tvd_averages = {}
        
        for grid in selected_grids:
            z_values = self.depth_grid_data_dict.get(grid, [])
            if len(z_values) > 0:
                grid_tvd_averages[grid] = np.mean(z_values)
                
        return sorted(grid_tvd_averages, key=grid_tvd_averages.get)

    def find_tvd_grid_intersections(self, df, selected_grids):
        """Find intersections between well paths and grid surfaces."""
        sorted_grids = self.get_sorted_grid_order(selected_grids)[::-1]
        intersections_list = []
        self.total_laterals = []

        # Process each well
        for UWI in df['UWI'].unique():
            well_df = df[df['UWI'] == UWI].sort_values(by='MD').reset_index(drop=True)
            well_df['Inclination'] = np.nan

            # Calculate inclination
            for i in range(1, len(well_df)):
                current_row = well_df.iloc[i]
                previous_row = well_df.iloc[i - 1]
                delta_md = current_row['MD'] - previous_row['MD']
                delta_tvd = current_row['TVD'] - previous_row['TVD']
                if delta_md != 0:
                    inclination = np.degrees(np.arccos(delta_tvd / delta_md))
                    well_df.at[i, 'Inclination'] = inclination

            # Filter to horizontal sections
            well_df = well_df[well_df['Inclination'] < 91].reset_index(drop=True)

            # Calculate total lateral length
            total_lateral = well_df['MD'].max() - well_df['MD'].min()
            self.total_laterals.append({
                'UWI': UWI,
                'Total Lateral Length': total_lateral
            })

            if well_df.empty:
                continue

            # Process intersection points
            first_row = well_df.iloc[0]
            first_x_offset = first_row['X Offset']
            first_y_offset = first_row['Y Offset']
            first_md = first_row['MD']
            first_tvd = first_row['TVD']

            last_row = well_df.iloc[-1]
            last_x_offset = last_row['X Offset']
            last_y_offset = last_row['Y Offset']
            last_md = last_row['MD']
            last_tvd = last_row['TVD']

            # Get initial grid
            grid_z_values = {}
            for grid in sorted_grids:
                grid_z_values[grid] = well_df[f'{grid} Closest Z'].iloc[0]

            initial_grid = "Above All"
            for i in range(1, len(sorted_grids)):
                grid_below = sorted_grids[i - 1]
                grid_above = sorted_grids[i]
                z_below = grid_z_values[grid_below]
                z_above = grid_z_values[grid_above]

                if z_below >= first_tvd >= z_above:
                    initial_grid = grid_below
                    break

            # Calculate well angle
            general_angle = self.calculate_angle(first_x_offset, first_y_offset, 
                                              last_x_offset, last_y_offset)

            # Process intersections
            current_intersection = {
                'UWI': UWI,
                'Grid Name': initial_grid,
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

                well_line = LineString([(tvd1, cum_distance1), (tvd2, cum_distance2)])

                for grid in sorted_grids:
                    z1 = well_df[f'{grid} Closest Z'].iloc[i-1]
                    z2 = well_df[f'{grid} Closest Z'].iloc[i]

                    grid_line = LineString([(z1, cum_distance1), (z2, cum_distance2)])

                    # Calculate slopes
                    well_slope = (tvd2 - tvd1) / (cum_distance2 - cum_distance1) if (cum_distance2 - cum_distance1) != 0 else 0
                    grid_slope = (z2 - z1) / (cum_distance2 - cum_distance1) if (cum_distance2 - cum_distance1) != 0 else 0

                    if well_line.intersects(grid_line):
                        intersection_point = well_line.intersection(grid_line)
                        
                        if intersection_point.geom_type == 'Point':
                            x_intersect, y_intersect = intersection_point.x, intersection_point.y

                            # Determine intersection grid
                            if well_slope > grid_slope:
                                grid_index = sorted_grids.index(grid)
                                intersection_grid = sorted_grids[grid_index - 1] if grid_index > 0 else "Above All"
                            else:
                                intersection_grid = grid

                            # Calculate intersection location
                            t = (y_intersect - cum_distance1) / (cum_distance2 - cum_distance1) if (cum_distance2 - cum_distance1) != 0 else 0
                            x_offset_intersect = well_df['X Offset'].iloc[i-1] + t * (well_df['X Offset'].iloc[i] - well_df['X Offset'].iloc[i-1])
                            y_offset_intersect = well_df['Y Offset'].iloc[i-1] + t * (well_df['Y Offset'].iloc[i] - well_df['Y Offset'].iloc[i-1])
                            md_intersect = well_df['MD'].iloc[i-1] + t * (well_df['MD'].iloc[i] - well_df['MD'].iloc[i-1])

                            # Complete current intersection
                            if current_intersection:
                                current_intersection.update({
                                    'Base X Offset': x_offset_intersect,
                                    'Base Y Offset': y_offset_intersect,
                                    'Base Depth': md_intersect,
                                    'Base TVD': z1
                                })
                                intersections_list.append(current_intersection)

                            # Start new intersection
                            current_intersection = {
                                'UWI': UWI,
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

            # Complete final intersection
            if current_intersection:
                current_intersection.update({
                    'Base X Offset': last_x_offset,
                    'Base Y Offset': last_y_offset,
                    'Base Depth': last_md,
                    'Base TVD': last_tvd
                })
                intersections_list.append(current_intersection)

        # Create final DataFrame
        df_intersections = pd.DataFrame(intersections_list)
        
        # Add required columns
        zone_name = self.zone_name_dropdown.combo.currentText().strip()
        zone_type = 'Intersections'



        # Save the zone name and type
        self.db_manager.add_zone_names(zone_name, zone_type)



        # Save the percentage data into a new table in the database
        self.db_manager.create_table_from_df(zone_name, df_intersections)

        return df_intersections

    def create_percentage_dataframe(self, df_intersections):
        """
        Create a DataFrame with percentage data for each well, ensuring zone name includes both name and type.
        """
        percentage_data = []
        # Construct the zone name and type
        base_zone_name = self.zone_name_dropdown.combo.currentText().strip()
        if not base_zone_name:
            raise ValueError("Zone name cannot be empty.")
        zone_name = f"{base_zone_name}_Percentages"
        zone_type = "Well"  # Zone type fixed to 'Well'
        all_grids = df_intersections['Grid Name'].unique()
    
        for UWI in df_intersections['UWI'].unique():
            # Get the total lateral length
            total_lateral = next(
                (item['Total Lateral Length'] for item in self.total_laterals if item['UWI'] == UWI),
                None
            )
            if total_lateral is None or total_lateral == 0:
                continue  # Skip wells with no lateral length
            
            # Calculate grid percentages
            UWI_df = df_intersections[df_intersections['UWI'] == UWI]
            grid_lengths = {grid: 0.0 for grid in all_grids}
        
            for _, row in UWI_df.iterrows():
                grid = row['Grid Name']
                length = row['Base Depth'] - row['Top Depth']
                grid_lengths[grid] += length
            
            grid_percentages = {grid: (length / total_lateral) * 100 for grid, length in grid_lengths.items()}
        
            # Get well location data
            first_survey = self.directional_surveys_df[self.directional_surveys_df['UWI'] == UWI].iloc[0]
        
            # Create percentage row
            percentage_row = {
                'UWI': UWI,
                'Zone Name': base_zone_name,
                'Zone Type': zone_type,
                'Total Lateral Length': total_lateral,
                'Top X Offset': first_survey['X Offset'],
                'Top Y Offset': first_survey['Y Offset'],
                'Base X Offset': first_survey['X Offset'],
                'Base Y Offset': first_survey['Y Offset']
            }
            percentage_row.update(grid_percentages)
            percentage_data.append(percentage_row)
        
        # Convert percentage data into a DataFrame
        percentage_df = pd.DataFrame(percentage_data)
    
        # Save the zone name and type
        self.db_manager.add_zone_names(zone_name, zone_type)
    

    
        # Save the percentage data into a new table in the database
        self.db_manager.create_table_from_df(zone_name, percentage_df)


        # Show completion message
        QMessageBox.information(self, "Success", "Zone calculation completed successfully!")
        
        # Close the dialog
        self.accept()
    
        return percentage_df
    
 


    def calculate_angle(self, x1, y1, x2, y2):
        """Calculate angle between two points."""
        dx = x2 - x1
        dy = y1 - y2  # Invert dy for y-axis

        angle = np.arctan2(dy, dx)
        if angle < 0:
            angle += 2 * np.pi

        target_angles = [0, np.pi/2, np.pi, 3*np.pi/2, 2*np.pi]
        rounded_angle = min(target_angles, key=lambda x: abs(x - angle))
        rotated_angle = rounded_angle + np.pi/2

        if rotated_angle >= 2 * np.pi:
            rotated_angle -= 2 * np.pi

        return rotated_angle