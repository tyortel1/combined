import sys
import os
import plotly.graph_objs as go
import json

import plotly.offline as py_offline
from PySide6.QtGui import QIcon, QIntValidator, QColor, QPainter, QBrush, QPixmap, QLinearGradient, QGuiApplication
from PySide6.QtWidgets import (
    QApplication, QVBoxLayout,QSpacerItem,QSizePolicy, QHBoxLayout,QGraphicsDropShadowEffect, QPushButton, QSlider, QSpinBox, 
    QLineEdit, QComboBox, QDialog, QSizePolicy, QLabel, QFrame, QMessageBox
)
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebEngineCore import QWebEngineSettings, QWebEnginePage

import pandas as pd
import numpy as np
from scipy.spatial import KDTree
from PySide6.QtCore import Signal, QtMsgType, Qt
from scipy import interpolate
from PySide6.QtCore import QUrl
from scipy.ndimage import gaussian_filter
from StyledDropdown import StyledDropdown, StyledInputBox, StyledBaseWidget
from StyledButton import StyledButton
from StyledColorbar import StyledColorBar 





class Plot(QDialog):
    closed = Signal()
    
    def __init__(self, UWI_list, directional_surveys_df, depth_grid_data_df, grid_info_df, kd_tree_depth_grids, current_UWI, depth_grid_data_dict, master_df,seismic_data,seismic_kdtree,db_manager, parent=None):
        super().__init__(parent)
        self.setWindowFlags(self.windowFlags() | Qt.WindowMinMaxButtonsHint | Qt.Window)

        self.main_app = parent
        self.UWI_list = UWI_list
        self.directional_surveys_df = directional_surveys_df
        self.depth_grid_data_df = depth_grid_data_df
        self.grid_info_df = grid_info_df
        self.kd_tree_depth_grids = kd_tree_depth_grids
        self.current_index = self.UWI_list.index(current_UWI)
        self.current_UWI = current_UWI
        self.depth_grid_data_dict = depth_grid_data_dict
        self.seismic_data = seismic_data
        self.master_df = master_df
        self.seismic_kdtree = seismic_kdtree
        self.zones =[]
        self.combined_distances = []
        self.tick_traces = [] 
        self.tvd_values = []
        self.attributes_names = []
        self.UWI_att_data = pd.DataFrame()
        self.selected_zone_df = pd.DataFrame()
        self.current_well_data = pd.DataFrame()
        self.selected_attribute = None
        self.min_attr = 0
        self.max_attr = 1
        self.selected_zone = None
        self.tick_size_value = 50
        self.fig = go.Figure()

        self.next_well = False
        self.db_manager = db_manager
     
        

        self.palettes_folder = '/Palettes'  # Replace with your actual palette folder path
        self.init_ui()
        
        # Set initial size and position
        self.resize(1200, 1400)  # Set initial size (width, height)

        # Check if there are multiple screens
        app = QGuiApplication.instance() or QGuiApplication([])
        screens = app.screens()

        if len(screens) > 1:
            # Get the geometry of the second screen
            screen = screens[1]  # Screen index 1 corresponds to the second screen
            screen_geometry = screen.geometry()

            # Move the window to the top-left corner of the second screen
            self.move(screen_geometry.left(), screen_geometry.top())

    def closeEvent(self, event):
        self.closed.emit()
        event.accept()

    def init_ui(self):

        labels = [
            "Well",
            "Zone",
            "Attribute",
            "Color Bar",  # Add this
            "Tick Size",
            "Max TVD",
            "Min TVD"
        ]
        StyledDropdown.calculate_label_width(labels)



        self.setStyleSheet("""
                QDialog {
                    background-color: white;
                }
                QLabel {
                    color: black;
                }
                QPushButton {
                    background-color: white;
                    border: none;
                }
            """)



        def create_dropdown(label):
            dropdown = StyledDropdown(label)
            dropdown.setStyleSheet("""
                QLabel, QComboBox {
                    background-color: transparent;
                    border: none;
                    padding: 0;
                    margin: 0;
                }
            """)
            return dropdown

        def create_section(frame_name, fixed_height=None):
            frame = QFrame()
            frame.setFrameStyle(QFrame.Panel | QFrame.Raised)
            frame.setStyleSheet("""
                QFrame {
                    background-color: white;
                    border: 2px solid #A0A0A0;
                    border-radius: 6px;
                    padding: 4px;
                }
            """)
            if fixed_height:
                frame.setFixedHeight(fixed_height)
                frame.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)

            shadow = QGraphicsDropShadowEffect()
            shadow.setBlurRadius(10)
            shadow.setXOffset(3)
            shadow.setYOffset(3)
            shadow.setColor(QColor(0, 0, 0, 100))
            frame.setGraphicsEffect(shadow)

            layout = QVBoxLayout(frame)
            layout.setSpacing(1)
            layout.setContentsMargins(5, 5, 5, 5)
            layout.setAlignment(Qt.AlignTop)
            return frame, layout

        def create_input(label, default_value='', validator=None):
            input_box = StyledInputBox(label, default_value, validator)
            input_box.label.setFixedWidth(StyledDropdown.label_width)  # Use the same width
            input_box.setStyleSheet("""
                QLabel {
                    background-color: transparent;
                    border: none;
                    padding: 0;
                    margin: 0;
                }
            """)
            return input_box

        def create_colorbar():
            colorbar = StyledColorBar("Color Bar")  # Make sure to pass the label text
            colorbar.colorbar_dropdown.label.setFixedWidth(StyledDropdown.label_width)  # Use the calculated width
    
            # Apply consistent styling
            colorbar.setStyleSheet("""
                QLabel {
                    background-color: transparent;
                    border: none;
                    padding: 0;
                    margin: 0;
                }
            """)
            return colorbar




        # Well and Navigation Section
        wellFrame, wellLayout = create_section("Well Navigation", fixed_height=90)
    
        # Well Selector
        self.well_selector = create_dropdown("Well")
        self.well_selector.addItems(self.UWI_list)
        current_index = self.UWI_list.index(self.current_UWI)
        self.well_selector.setCurrentIndex(current_index)
        self.well_selector.combo.currentIndexChanged.connect(self.on_well_selected)
        # Navigation Buttons Layout

        self.prev_button = QPushButton()
        self.next_button = QPushButton()

        # Load icons
        prev_icon = QIcon(os.path.join(os.path.dirname(__file__), 'Icons', 'arrow_left.ico'))
        next_icon = QIcon(os.path.join(os.path.dirname(__file__), 'Icons', 'arrow_right.ico'))

        self.prev_button.setIcon(prev_icon)
        self.next_button.setIcon(next_icon)

        self.prev_button.setFixedSize(40, 40)
        self.next_button.setFixedSize(40, 40)

        self.prev_button.setText('')
        self.next_button.setText('')

        # Connect existing methods
        self.prev_button.clicked.connect(self.on_prev)
        self.next_button.clicked.connect(self.on_next)

        # Create a horizontal layout for buttons
      # Create a horizontal layout for buttons
        button_layout = QHBoxLayout()

        # Add spacer before the first button (20 units)
        spacer_20 = QSpacerItem(0, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)
        button_layout.addItem(spacer_20)  # Add the 20-unit spacer first

        # Add the first button
        button_layout.addWidget(self.prev_button)

        # Add spacer before the second button (40 units)
        spacer_40 = QSpacerItem(0, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)
        button_layout.addItem(spacer_40)  # Add the 40-unit spacer before the second button

        # Add the second button
        button_layout.addWidget(self.next_button)

        button_layout.addStretch()  # This ensures buttons are centered or aligned as needed

        # Add to layout under the well dropdown
        wellLayout.addWidget(self.well_selector)
        wellLayout.addLayout(button_layout)




        # Zone and Attribute Section
        zoneFrame, zoneLayout = create_section("Zone and Attribute", fixed_height=170)
    
        # Zone Selector
        self.zone_selector = create_dropdown("Zone")
        self.zone_attribute_selector = create_dropdown("Attribute")
        self.color_colorbar = create_colorbar()


        # Add widgets to zone frame
        zoneLayout.addWidget(self.zone_selector)
        zoneLayout.addWidget(self.zone_attribute_selector)
        zoneLayout.addWidget(self.color_colorbar)
       
        # Tick Settings Section

        tickFrame, tickLayout = create_section("Tick Settings", fixed_height=110)

        # Tick Size Input
        self.tick_size_input = create_input("Tick Size", default_value='50')
        self.tick_size_input.editingFinished.connect(self.change_tick_size_from_input)

        # TVD Range Inputs
        tvd_validator = QIntValidator()

        # TVD Range Inputs with integer validation
        self.max_tvd_input = create_input("Max TVD", default_value='0', validator=tvd_validator)
        self.min_tvd_input = create_input("Min TVD", default_value='0', validator=tvd_validator)

        # Connect inputs to update plot
        self.min_tvd_input.editingFinished.connect(self.plot_current_well)
        self.max_tvd_input.editingFinished.connect(self.plot_current_well)

        # Add widgets to tick frame
        tickLayout.addWidget(self.tick_size_input)
        tickLayout.addWidget(self.max_tvd_input)
        tickLayout.addWidget(self.min_tvd_input)

        # Control Layout
        control_layout = QVBoxLayout()
        control_layout.addWidget(wellFrame)
        control_layout.addWidget(zoneFrame)
        control_layout.addWidget(tickFrame)
        control_layout.addStretch()

        # Plot Layout
        self.plot_widget = QWebEngineView()
        self.plot_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.plot_layout = QVBoxLayout()
        self.plot_layout.addWidget(self.plot_widget)
        self.plot_widget.settings().setAttribute(QWebEngineSettings.JavascriptEnabled, True)

        # Main layout
        main_layout = QHBoxLayout()
        main_layout.addLayout(control_layout, stretch=1)
        main_layout.addLayout(self.plot_layout, stretch=7)
        self.setLayout(main_layout)

        self.zone_selector.combo.currentIndexChanged.connect(self.zone_selected)
        self.zone_attribute_selector.combo.currentIndexChanged.connect(self.attribute_selected)
        self.color_colorbar.colorbar_dropdown.combo.currentIndexChanged.connect(self.palette_selected)
        self.zone_attribute_selector.combo.setEnabled(False)

        self.populate_zone_names()
  
        self.plot_current_well()


    def palette_selected(self):
        if self.next_well == False:
            self.plot_current_well()

    def attribute_selected(self):
        if self.next_well == False:
            self.plot_current_well()

    def change_tick_size_from_input(self):
     
        new_size = int(self.tick_size_input.text())
         
        self.tick_size_value = new_size
        if self.next_well == False:
            self.plot_current_well()

    def populate_zone_names(self):

        
        self.zone_selector.blockSignals(True)
        # Clear existing items
        self.zone_selector.clear()

        # Add default option
        self.zone_selector.addItem("Select Zone")

        try:
            # Fetch unique zone names from the database where type is 'Well'
            zones = self.db_manager.fetch_zone_names_by_type("Zone")

            if zones:
                # Sort zones alphabetically
                zones = [zone[0] for zone in zones if zone[0].strip()] 
                zones = sorted(zones)
                print(zones)

                # Populate the dropdown with sorted zone names
                self.zone_selector.addItems(zones)
            else:
                print("No zones of type 'Well' found.")

        except Exception as e:
            print(f"Error populating Well Zone dropdown: {e}")

        finally:
            # Unblock signals after populating the dropdown
            self.zone_selector.blockSignals(False)
            self.zone_attribute_selector.combo.setEnabled(True)



    def populate_zone_attribute(self):
        """Update the zone attribute selector based on the selected zone filter and add a default 'Select Zone Attribute' option."""
        self.zone_attribute_selector.blockSignals(True)
        self.zone_attribute_selector.setEnabled(True)

        zone_df = self.selected_zone_df
        print(zone_df)
        columns = self.selected_zone_df.columns.tolist() 

        # Columns to exclude
        columns_to_exclude = [
            'id', 'Zone_Name', 'Zone_Type', 'Attribute_Type',
            'Top_Depth', 'Base_Depth', 'UWI', 'Top_X_Offset',
            'Base_X_Offset', 'Top_Y_Offset', 'Base_Y_Offset',
            'Angle_Top', 'Angle_Base', 'Base_TVD', 'Top_TVD'
        ]

        # Drop fixed columns and find columns with at least one non-null value
        zone_df = zone_df.drop(columns=columns_to_exclude, errors='ignore')
        self.attributes_names = sorted(zone_df.columns[zone_df.notna().any()].tolist())
        print(self.attributes_names)
        # Find attributes (columns with at least one non-null value)
 
    
        # Clear and populate the attribute selector
        self.zone_attribute_selector.clear()
        self.zone_attribute_selector.addItem("Select Zone Attribute")
        self.zone_attribute_selector.addItems(self.attributes_names)
    
        # Set default selection to the first item (e.g., "Select Zone Attribute")
        self.zone_attribute_selector.setCurrentIndex(0)
        self.zone_attribute_selector.blockSignals(False)


    
    def zone_selected(self):
        # Get the selected zone name from the zone selector
        selected_text = self.zone_selector.currentText()
        if not selected_text:  # Handle empty selection
            print("Empty zone selection")
            return
        
        self.selected_zone = selected_text.replace(" ", "_")
        print(f"Selected zone: {self.selected_zone}")
    
        # Clear attributes selector
        self.zone_attribute_selector.clear()
        self.zone_attribute_selector.addItem("Select Zone Attribute")
    
        if self.selected_zone == "Select_Zone":
            # Clear the zone data
            self.selected_zone_df = None
            self.attributes_names = []
        
            # Remove existing tick traces and zone fills
            if hasattr(self, 'fig'):
                # Filter out tick traces and zone fills
                new_data = []
                for trace in self.fig.data:
                    # Check trace properties using proper Plotly attribute access
                    if hasattr(trace, 'line'):
                        line_color = trace.line.color if hasattr(trace.line, 'color') else None
                        if line_color not in ['red', 'blue']:  # not a tick mark or zone boundary
                            new_data.append(trace)
                    else:
                        new_data.append(trace)
            
                self.fig.data = tuple(new_data)  # Update figure data
            
                # Update the plot
                if not self.next_well:
                    file_path = os.path.join(os.getcwd(), "plot.html")
                    py_offline.plot(self.fig, filename=file_path, auto_open=False)
                    self.plot_widget.load(QUrl.fromLocalFile(file_path))
        else:
            try:
                # Filter the master_df to grab the relevant UWI and Zone data
                self.selected_zone_df = self.db_manager.fetch_table_data(self.selected_zone)
            
                # Trigger replot with the new selected zone data
                if not self.next_well:
                    self.plot_current_well()
            except Exception as e:
                print(f"Error fetching zone data: {str(e)}")
                self.selected_zone_df = None

        # Update the attribute selector
        self.populate_zone_attribute()




    def update_color_range(self):
        """Update the color range display and refresh the plot based on the selected palette from StyledColorBar."""
        self.palette_name = self.color_colorbar.colorbar_dropdown.currentText()
    
        # Update the color range display
        self.color_colorbar.display_color_range(self.min_attr, self.max_attr)

        # Force a replot to apply new colors
        self.plot_current_well()






    def plot_current_well(self):
        fig = go.Figure()
        try:
            # Extract data for the selected well
            self.current_well_data = self.directional_surveys_df[self.directional_surveys_df['UWI'] == self.current_UWI]
            self.current_well_data = self.current_well_data.reset_index(drop=True)

            if self.current_well_data.empty:
                print(f"No data found for UWI: {self.current_UWI}")
                return

            self.tvd_values = self.current_well_data['TVD'].tolist()
            self.combined_distances = self.current_well_data['Cumulative Distance'].tolist()

            if not self.seismic_data:
                print("No seismic data available, skipping plotting.")
            else:
                # ADD THE DEBUG PRINTS RIGHT HERE
                print("Seismic data shape:", self.seismic_data['trace_data'].shape if 'trace_data' in self.seismic_data else "No trace_data found")
                print("Time axis length:", len(self.seismic_data['time_axis']) if 'time_axis' in self.seismic_data else "No time_axis found")

                # Batch query for all well path points to find nearest seismic traces
                well_coords = np.column_stack((self.current_well_data['X Offset'], self.current_well_data['Y Offset']))
                print("Well coordinates shape:", well_coords.shape)
                print("Well X range:", well_coords[:, 0].min(), "to", well_coords[:, 0].max())
                print("Well Y range:", well_coords[:, 1].min(), "to", well_coords[:, 1].max())
                print("First few seismic coordinates from KDTree:")
                print(self.seismic_kdtree.data[:5])
                print("\nSeismic coordinate ranges:")
                print("X range:", self.seismic_kdtree.data[:, 0].min(), "to", self.seismic_kdtree.data[:, 0].max())
                print("Y range:", self.seismic_kdtree.data[:, 1].min(), "to", self.seismic_kdtree.data[:, 1].max())

                distances, indices = self.seismic_kdtree.query(well_coords)
                print("KDTree indices range:", indices.min(), "to", indices.max())

                                # Add distance-based filtering
                max_distance = 100  # Maximum distance in same units as your coordinates
                valid_traces = distances <= max_distance
                indices = indices[valid_traces]
                filtered_distances = distances[valid_traces]

                seismic_trace_amplitudes = self.seismic_data['trace_data'][indices, :]
                cumulative_distances = np.array(self.combined_distances)

                # Vectorized construction of seismic data
                seismic_time_axis = np.tile(self.seismic_data['time_axis'], len(cumulative_distances))
                seismic_amplitude_flattened = seismic_trace_amplitudes.flatten()

                UWI_seismic_data = np.column_stack((
                    np.repeat(well_coords[:, 0], len(self.seismic_data['time_axis'])),
                    np.repeat(well_coords[:, 1], len(self.seismic_data['time_axis'])),
                    np.repeat(cumulative_distances, len(self.seismic_data['time_axis'])),
                    seismic_time_axis,
                    seismic_amplitude_flattened
                ))

                seismic_df = pd.DataFrame(UWI_seismic_data, columns=['x', 'y', 'cumulative_distance', 'time', 'amplitude'])
                seismic_df = seismic_df.drop_duplicates(subset=['time', 'cumulative_distance'])
                seismic_df = seismic_df.sort_values(['cumulative_distance', 'time'])

                # Create a regular grid for interpolation
                unique_distances = np.linspace(seismic_df['cumulative_distance'].min(),
                                               seismic_df['cumulative_distance'].max(),
                                               num=500)
                unique_times = np.sort(seismic_df['time'].unique())
                grid_distances, grid_times = np.meshgrid(unique_distances, unique_times)

                # Perform 2D interpolation
                points = seismic_df[['cumulative_distance', 'time']].values
                values = seismic_df['amplitude'].values
                interpolated_data = interpolate.griddata(points, values, (grid_distances, grid_times), method='cubic', fill_value=0)

                # Apply Gaussian smoothing
                smoothed_data = gaussian_filter(interpolated_data, sigma=(5, 2))  # Adjust sigma as needed

                # Create a new DataFrame with the smoothed data
                smoothed_df = pd.DataFrame({
                    'cumulative_distance': grid_distances.flatten(),
                    'time': grid_times.flatten(),
                    'amplitude': smoothed_data.flatten()
                })

                seismic_data = smoothed_df.pivot(index='time', columns='cumulative_distance', values='amplitude').values
                seismic_distances = unique_distances
                seismic_time_axis = unique_times[::-1]  # Reverse the time axis if needed

                max_amplitude = np.max(np.abs(seismic_data))

                # Create the heatmap figure for seismic data
                fig = go.Figure()

                fig.add_trace(go.Heatmap(
                    z=seismic_data,
                    x=seismic_distances,
                    y=seismic_time_axis,
                    colorscale='RdBu',
                    zmin=-max_amplitude,
                    zmax=max_amplitude,
                    showscale=False  # Keep colorbar
                    #colorbar=dict(
                    #    len=0.3,  # ⬅️ 30% of default height
                    #    thickness=10,  # ⬅️ Make it thinner
                    #    x=1.02,  # ⬅️ Slightly move to the right
                    #    y=0.5,  # ⬅️ Center it vertically
                    #    title="Amplitude",  # Optional: Label for colorbar
                    #    titleside="right"
                    #)
                ))


            # Now plot the grid data over the seismic data (optimized with vectorization)
            well_coords_grid = np.column_stack((self.current_well_data['X Offset'], self.current_well_data['Y Offset']))
            UWI_grid_data = []

            for i, (x2, y2) in enumerate(well_coords_grid):
                # Batch query for grid data using KDTree
                closest_z_values = {grid: None for grid in self.kd_tree_depth_grids.keys()}
                for grid, kdtree in self.kd_tree_depth_grids.items():
                    if kdtree.data.size > 0:
                        distances, indices = kdtree.query((x2, y2))
                        if indices < len(self.depth_grid_data_dict[grid]):
                            closest_z_values[grid] = self.depth_grid_data_dict[grid][indices]

                entry = [x2, y2, self.combined_distances[i]] + [closest_z_values[grid] for grid in self.kd_tree_depth_grids.keys()]
                UWI_grid_data.append(entry)

            valid_grids = [grid for grid in self.kd_tree_depth_grids.keys() if grid in set(self.grid_info_df['Grid']) & set(self.depth_grid_data_df['Grid'])]
            columns = ['x', 'y', 'combined_distance'] + valid_grids

            if all(len(entry) == len(columns) for entry in UWI_grid_data):
                df = pd.DataFrame(UWI_grid_data, columns=columns)
            else:
                print("Error: Length of entries in UWI_grid_data does not match the length of columns")
                return

            grid_values = {grid_name: df[grid_name].tolist() for grid_name in valid_grids}
            sorted_grids = sorted(grid_values.keys(), key=lambda grid: min(grid_values[grid]))

            all_z_values = []
            for grid_name in sorted_grids:
                all_z_values.extend(grid_values[grid_name])
            
            if all_z_values:
                min_z = min(all_z_values)
                max_z = max(all_z_values)
                
                # Add padding (2% of range)
                z_range = max_z - min_z
                padding = z_range * 0.02
                
                final_min = min_z - padding
                final_max = max_z + padding
                
                print(f"Grid Z range: {round(min_z)} to {round(max_z)}")
                print(f"Final TVD range: {round(final_min)} to {round(final_max)}")
                
                self.min_tvd_input.setText(f"{round(final_min)}")
                self.max_tvd_input.setText(f"{round(final_max)}")
                
                # Update plot's y-axis range
                fig.update_yaxes(range=[round(final_min), round(final_max)])




            # Overlay grids on the seismic plot and fill between them
            for i, grid_name in enumerate(sorted_grids):
                try:
                    # Get the color for the current grid
                    grid_row = self.grid_info_df.loc[self.grid_info_df['Grid'] == grid_name]
                    if grid_row.empty:
                        print(f"Grid {grid_name} not found in grid_info_df")
                        continue

                    r, g, b = grid_row['Color (RGB)'].values[0]
                    grid_color_rgb = f'rgb({r}, {g}, {b})'
                    grid_color_rgba = f'rgba({r}, {g}, {b}, 0.3)'

                    if i + 1 < len(sorted_grids):
                        next_grid_name = sorted_grids[i + 1]
                        next_grid_row = self.grid_info_df.loc[self.grid_info_df['Grid'] == next_grid_name]
                        if not next_grid_row.empty:
                            next_r, next_g, next_b = next_grid_row['Color (RGB)'].values[0]
                            next_grid_rgba = f'rgba({next_r}, {next_g}, {next_b}, 0.3)'
                        else:
                            next_grid_rgba = 'rgba(0, 0, 0, 0.3)'
                    else:
                        next_grid_rgba = 'rgba(0, 0, 0, 0.3)'

                    fig.add_trace(go.Scatter(
                        x=self.combined_distances,
                        y=grid_values[grid_name],
                        mode='lines',
                        name=grid_name,
                        line=dict(color=grid_color_rgb),
                        fill=None,  # Added missing comma
                        showlegend=False  # Turn off legend for this trace
                    ))

                    if i < len(sorted_grids) - 1:
                        next_grid_values = grid_values[next_grid_name]
                        fig.add_trace(go.Scatter(
                            x=self.combined_distances,
                            y=next_grid_values,
                            fill='tonexty',
                            fillcolor=next_grid_rgba,
                            mode='none',
                            showlegend=False
                        ))

                except Exception as e:
                    print(f"Error processing grid {grid_name}: {e}")

            # Plot well path as black lines
            fig.update_yaxes(range=[float(self.min_tvd_input.text()), float(self.max_tvd_input.text())])

            # Store the figure object as an instance variable
            self.fig = fig


            self.update_zone_ticks()  # Call a new method to add/update zone ticks



            fig.add_trace(go.Scatter(
                x=self.combined_distances,
                y=self.tvd_values,
                mode='lines',
                line=dict(color='black', width=3),
                showlegend=False,
                hoverinfo='skip'

            ))




            # Update layout to improve plot appearance
            fig.update_layout(
                title='Seismic Trace and Grid Overlay',
                xaxis_title='Cumulative Distance',
                yaxis_title='Time (ms) / Depth',
                margin=dict(l=0, r=0, t=50, b=50),
                xaxis=dict(showline=True, showgrid=False, showticklabels=True, ticks='inside'),
                yaxis=dict(showline=True, showgrid=False, showticklabels=True, ticks='inside'),
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                showlegend=True
            )

            # Save Plotly figure to an HTML file for testing
            file_path = os.path.join(os.getcwd(), "plot.html")
            py_offline.plot(fig, filename=file_path, auto_open=False)
          
            url = QUrl.fromLocalFile(file_path)
            self.plot_widget.load(url)

        except Exception as e:
            print(f"Error plotting seismic and grid data: {e}")



        


    def interpolate_value(self, md, column):
        # Check if MD is within the range of our data
        if md < self.current_well_data['MD'].min():
            print(f"MD {md} is below the range of the well data. Using minimum value.")
            return self.current_well_data[column].iloc[0]
        elif md > self.current_well_data['MD'].max():
            print(f"MD {md} is above the range of the well data. Using maximum value.")
            return self.current_well_data[column].iloc[-1]

        # Find the indices where MD falls between
        idx = np.searchsorted(self.current_well_data['MD'].values, md)

        # Handle the case where md exactly matches the last MD in the data
        if idx == len(self.current_well_data):
            return self.current_well_data[column].iloc[-1]

        # Get the bounding values
        md_lower = self.current_well_data['MD'].iloc[idx-1]
        md_upper = self.current_well_data['MD'].iloc[idx]
        val_lower = self.current_well_data[column].iloc[idx-1]
        val_upper = self.current_well_data[column].iloc[idx]

        # Interpolate
        fraction = (md - md_lower) / (md_upper - md_lower)
        interpolated_val = val_lower + fraction * (val_upper - val_lower)

        return interpolated_val



    def zone_selected(self):
        # Get the selected zone name from the zone selector
        selected_text = self.zone_selector.currentText()
        if not selected_text:  # Handle empty selection
            print("Empty zone selection")
            return
        
        self.selected_zone = selected_text.replace(" ", "_")
        print(f"Selected zone: {self.selected_zone}")
    
        # Clear attributes selector
        self.zone_attribute_selector.clear()
        self.zone_attribute_selector.addItem("Select Zone Attribute")
    
        if self.selected_zone == "Select_Zone":
            # Clear the zone data
            self.selected_zone_df = None
            self.attributes_names = []
        
            # Remove existing tick traces and zone fills
            if hasattr(self, 'fig'):
                # Filter out tick traces and zone fills
                new_data = []
                for trace in self.fig.data:
                    # Check trace properties using proper Plotly attribute access
                    if hasattr(trace, 'line'):
                        line_color = trace.line.color if hasattr(trace.line, 'color') else None
                        if line_color not in ['red', 'blue']:  # not a tick mark or zone boundary
                            new_data.append(trace)
                    else:
                        new_data.append(trace)
            
                self.fig.data = tuple(new_data)  # Update figure data
            
                # Update the plot
                if not self.next_well:
                    file_path = os.path.join(os.getcwd(), "plot.html")
                    py_offline.plot(self.fig, filename=file_path, auto_open=False)
                    self.plot_widget.load(QUrl.fromLocalFile(file_path))
        else:
            try:
                # Filter the master_df to grab the relevant UWI and Zone data
                self.selected_zone_df = self.db_manager.fetch_table_data(self.selected_zone)
            
                # Trigger replot with the new selected zone data
                if not self.next_well:
                    self.plot_current_well()
            except Exception as e:
                print(f"Error fetching zone data: {str(e)}")
                self.selected_zone_df = None

        # Update the attribute selector
        self.populate_zone_attribute()

    def update_zone_ticks(self):
        # Early return if no zone is selected or if "Select Zone" is chosen
        if self.selected_zone is None or self.selected_zone == "Select_Zone":
            print("No valid zone selected, skipping tick update.")
            return

        try:
            tick_traces = []
            zone_fills = []

            # Safety check for selected_zone_df
            if self.selected_zone_df is None:
                print("No zone data available")
                return

            attribute = self.zone_attribute_selector.currentText()
            color_zones = attribute != "Select Zone Attribute"

            # Filter the master_df for the current UWI and selected zone
            zone_data = self.selected_zone_df[self.selected_zone_df['UWI'] == self.current_UWI].copy()
    
            if zone_data.empty:
                print(f"No data found for UWI {self.current_UWI} and zone {self.selected_zone}")
                return

            if color_zones:
                if attribute not in zone_data.columns:
                    print(f"Selected attribute '{attribute}' not found in the data.")
                    color_zones = False  # Prevent it from blocking tick drawing
                else:
                    self.min_attr = zone_data[attribute].min()
                    self.max_attr = zone_data[attribute].max()
                    self.color_colorbar.display_color_range(self.min_attr, self.max_attr)

            for _, zone_row in zone_data.iterrows():
                try:
                    top_md = zone_row['Top_Depth']
                    base_md = zone_row['Base_Depth']

                    top_cum_dist = self.interpolate_value(top_md, 'Cumulative Distance')
                    base_cum_dist = self.interpolate_value(base_md, 'Cumulative Distance')
                    top_tvd = self.interpolate_value(top_md, 'TVD')
                    base_tvd = self.interpolate_value(base_md, 'TVD')

                    if all(v is not None for v in [top_cum_dist, base_cum_dist, top_tvd, base_tvd]):
                        # Only add tick marks if a valid zone is selected
                        for cum_dist, tvd, name in [(top_cum_dist, top_tvd, 'Top'), (base_cum_dist, base_tvd, 'Base')]:
                            tick_traces.append(go.Scatter(
                                x=[cum_dist, cum_dist],
                                y=[tvd - self.tick_size_value/2, tvd + self.tick_size_value/2],
                                mode='lines',
                                line=dict(color='red', width=2),
                                showlegend=False,
                                hoverinfo='skip'
                            ))

                        if color_zones and attribute in zone_row:
                            attribute_value = zone_row[attribute]
                            color = self.color_colorbar.map_value_to_color(attribute_value, self.min_attr, self.max_attr, self.color_colorbar.selected_color_palette)

                            zone_fills.append(go.Scatter(
                                x=[top_cum_dist, base_cum_dist],
                                y=[top_tvd, base_tvd],
                                mode='lines',
                                line=dict(color=f'rgb({color.red()}, {color.green()}, {color.blue()})', width=(self.tick_size_value/3)),
                                name=f'{self.selected_zone}: {attribute} = {attribute_value:.2f}',
                                showlegend=False,
                                hoverinfo='text',
                                text=f'{self.selected_zone}: {attribute} = {attribute_value:.2f}'
                            ))
                        else:
                            # Add zone boundary
                            tick_traces.append(go.Scatter(
                                x=[top_cum_dist, base_cum_dist],
                                y=[top_tvd, base_tvd],
                                mode='lines',
                                line=dict(color='blue', width=2, dash='dash'),
                                name=f'{self.selected_zone} Boundary'
                            ))

                except Exception as e:
                    print(f"Error processing zone row: {str(e)}")
                    continue

            if tick_traces or zone_fills:
                # Add all traces at once
                self.fig.add_traces(zone_fills + tick_traces)

                file_path = os.path.join(os.getcwd(), "plot.html")
                py_offline.plot(self.fig, filename=file_path, auto_open=False)
                self.plot_widget.load(QUrl.fromLocalFile(file_path))

        except Exception as e:
            print(f"Error updating zone ticks and fills: {str(e)}")
            print("Zone data columns:", zone_data.columns.tolist() if 'zone_data' in locals() else "No zone data available")
            import traceback
            traceback.print_exc()


    def on_well_selected(self, index):
        try:
            selected_UWI = self.well_selector.currentText()  # Get UWI directly from the selector
            if selected_UWI in self.UWI_list:
                self.current_UWI = selected_UWI
                self.current_index = index  # Add this line
                self.plot_current_well()  # Update the plot for the selected UWI
            else:
                print(f"Selected UWI {selected_UWI} not found in UWI list.")
        except Exception as e:
            print(f"Error in on_well_selected: {e}")

    def on_next(self):
        """Navigate to the next well in alphabetical order."""
        try:
            current_index = self.UWI_list.index(self.current_UWI)
            next_index = (current_index + 1) % len(self.UWI_list)  # Ensure it wraps around
            self.current_UWI = self.UWI_list[next_index]
            self.update_well_selector_to_current_UWI()
            self.plot_current_well()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"An error occurred while processing the next well: {str(e)}")

    def on_prev(self):
        """Navigate to the previous well in alphabetical order."""
        try:
            current_index = self.UWI_list.index(self.current_UWI)
            prev_index = (current_index - 1) % len(self.UWI_list)  # Ensure it wraps around
            self.current_UWI = self.UWI_list[prev_index]
            self.update_well_selector_to_current_UWI()
            self.plot_current_well()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"An error occurred while processing the previous well: {str(e)}")
    def update_well_selector_to_current_UWI(self):
        """Set the dropdown to the current UWI."""
        try:
            current_index = self.UWI_list.index(self.current_UWI)
            self.well_selector.blockSignals(True)
            self.well_selector.setCurrentIndex(current_index)
            self.well_selector.blockSignals(False)
        except ValueError:
            QMessageBox.critical(self, "Error", f"UWI '{self.current_UWI}' not found in the list.")


    def update_well_selector_to_current_UWI(self):
        """Set the dropdown to the current UWI."""
        try:
            current_index = self.UWI_list.index(self.current_UWI)
            self.well_selector.blockSignals(True)
            self.well_selector.setCurrentIndex(current_index)
            self.well_selector.blockSignals(False)
        except ValueError:
            QMessageBox.critical(self, "Error", f"UWI '{self.current_UWI}' not found in the list.")

    def update_well_related_data(self):
        # Re-populate dropdowns and plots based on the newly selected UWI
        self.populate_zone_names()
        self.zone_selected()  # This triggers zone filtering and replotting based on the new UWI

        # Update the plot
        self.plot_current_well()

    def update_plot(self, grid_info_df):
        self.grid_info_df = grid_info_df
        self.plot_current_well()

    def receive_UWI(self):
      
        self.main_app.handle_hover_event(self.current_UWI)




    def show_error_message(self, message):
        """Display an error message box."""
        QMessageBox.critical(self, "Error", message)


class WebEngineView(QWebEngineView):
    def __init__(self, html_content):
        super().__init__()
        # Enable Developer Tools
        # Enable JavaScript settings if needed
        settings = self.settings()
        settings.setAttribute(QWebEngineSettings.JavascriptEnabled, True)
        settings.setAttribute(QWebEngineSettings.JavascriptCanOpenWindows, True)
        settings.setAttribute(QWebEngineSettings.JavascriptCanAccessClipboard, True)
        
        # Inject the HTML content
        self.setHtml(html_content)


if __name__ == '__main__':
    app = QApplication(sys.argv)

    # Sample directional_surveys_df
    data = {
        'UWI': ['well1', 'well1', 'well2', 'well2', 'well3', 'well3'],
        'MD': [0, 0, 0, 0, 0, 0],
        'TVD': [200, 250, 250, 300, 300, 350],
        'X Offset': [0, 0, 0, 0, 0, 0],
        'Y Offset': [0, 0, 0, 0, 0, 0],
        'Cumulative Distance': [100, 150, 150, 200, 200, 250],
        'Grid1': [150, 180, 180, 220, 220, 250],
        'Grid2': [180, 200, 200, 250, 250, 300],
        'ZoneIn': [1, 2, 2, 3, 3, 4],
        'ZoneIn_Name': ['Zone 1', 'Zone 2', 'Zone 2', 'Zone 3', 'Zone 3', 'Zone 4']
    }
    directional_surveys_df = pd.DataFrame(data)

    # Sample depth_grid_data_df for testing
    depth_grid_data = {
        'Grid': ['Grid1', 'Grid1', 'Grid2', 'Grid2'],
        'X': [0, 1, 0, 1],
        'Y': [0, 0, 1, 1],
        'Z': [10, 20, 30, 40]
    }
    depth_grid_data_df = pd.DataFrame(depth_grid_data)

    # Sample grid_info_df for testing
    grid_info_data = {
        'Grid': ['Grid1', 'Grid2', 'Grid3'],  # Assume Grid3 is not in depth_grid_data_df
        'Type': ['Depth', 'Depth', 'Depth'],
        'min_x': [0, 0, 0],
        'max_x': [1, 1, 1],
        'min_y': [0, 0, 0],
        'max_y': [1, 1, 1],
        'min_z': [10, 30, 0],
        'max_z': [20, 40, 1],
        'bin_size_x': [0.1, 0.1, 0.1],
        'bin_size_y': [0.1, 0.1, 0.1],
        'Color (RGB)': [(255, 0, 0), (0, 255, 0), (0, 0, 255)]
    }
    grid_info_df = pd.DataFrame(grid_info_data)

    # Sample KD-Trees for testing
    kd_tree_depth_grids = {grid: KDTree(depth_grid_data_df[depth_grid_data_df['Grid'] == grid][['X', 'Y']].values) for grid in depth_grid_data_df['Grid'].unique()}

    window = Plot(['well1', 'well2', 'well3'], directional_surveys_df, depth_grid_data_df, grid_info_df, kd_tree_depth_grids, 'well1', depth_grid_data_dict={})
    window.show()
    sys.exit(app.exec_())