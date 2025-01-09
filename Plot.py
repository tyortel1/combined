import sys
import os
import plotly.graph_objs as go
import json
from PySide6.QtGui import QIcon, QIntValidator
import plotly.offline as py_offline
from PySide6.QtGui import QIcon, QColor, QPainter, QBrush, QPixmap, QLinearGradient,QGuiApplication
from PySide6.QtWidgets import QApplication, QVBoxLayout, QHBoxLayout,  QPushButton, QSlider,QSpinBox,  QLineEdit, QComboBox, QDialog, QSizePolicy, QLabel, QFrame, QLabel ,QMessageBox
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEngineSettings, QWebEnginePage

import pandas as pd
import numpy as np
from scipy.spatial import KDTree
from PySide6.QtCore import Signal, QtMsgType, Qt
from scipy import interpolate
from PySide6.QtCore import QUrl
from scipy.ndimage import gaussian_filter





class Plot(QDialog):
    closed = Signal()
    
    def __init__(self, uwi_list, directional_surveys_df, depth_grid_data_df, grid_info_df, kd_tree_depth_grids, current_uwi, depth_grid_data_dict, master_df,seismic_data,seismic_kdtree, parent=None):
        super().__init__(parent)
        self.main_app = parent
        self.uwi_list = uwi_list
        self.directional_surveys_df = directional_surveys_df
        self.depth_grid_data_df = depth_grid_data_df
        self.grid_info_df = grid_info_df
        self.kd_tree_depth_grids = kd_tree_depth_grids
        self.current_index = self.uwi_list.index(current_uwi)
        self.current_uwi = current_uwi
        self.depth_grid_data_dict = depth_grid_data_dict
        self.seismic_data = seismic_data
        self.master_df = master_df
        self.seismic_kdtree = seismic_kdtree
        self.zones =[]
        self.combined_distances = []
        self.tick_traces = [] 
        self.tvd_values = []
        self.attributes_names = []
        self.uwi_att_data = pd.DataFrame()
        self.selected_zone_df = pd.DataFrame()
        self.current_well_data = pd.DataFrame()
        self.selected_attribute = None
        self.min_attr = 0
        self.max_attr = 1
        self.selected_zone = None
        self.tick_size_value = 50
        self.fig = go.Figure()
        self.palette_name = 'Rainbow'
        self.next_well = False
     
        

        self.palettes_folder = '/Palettes'  # Replace with your actual palette folder path
        self.init_ui()
        
        # Set initial size and position
        self.resize(1200, 800)  # Set initial size (width, height)

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

        self.uwi_list = sorted(self.uwi_list)
        # Create the dropdown for well selection
        self.well_selector = QComboBox()
        self.well_selector.addItems(self.uwi_list)

        current_index = self.uwi_list.index(self.current_uwi)
        self.well_selector.setCurrentIndex(current_index)
        self.well_selector.currentIndexChanged.connect(self.on_well_selected)

        # Create navigation buttons
        self.next_button = QPushButton('Next')
        self.prev_button = QPushButton('Previous')
        self.next_button.clicked.connect(self.on_next)
        self.prev_button.clicked.connect(self.on_prev)

        # Create dropdowns for Select Zone, Select Attribute Filter, and Select Zone Attribute
        self.zone_selector = QComboBox()
        self.zone_attribute_selector = QComboBox()

        # Color range display
        self.color_range_display = QLabel()
        self.color_range_display.setFixedHeight(50)
        self.color_range_display.setFixedWidth(220)
        self.color_range_display.setStyleSheet("background-color: white; border: 1px solid black;")

        # Create the Color Palette dropdown
        self.palette_selector = QComboBox()
        self.palette_selector.currentIndexChanged.connect(self.update_color_range)

        # Create the text box for tick size
        self.tick_size_input = QLineEdit()
        self.tick_size_input.setText('50')  # Default value
        self.tick_size_input.editingFinished.connect(self.change_tick_size_from_input)

        self.max_tvd_spinbox = QSpinBox()
        self.max_tvd_spinbox.setRange(-10000, 10000)  # Adjust based on your data range
        self.max_tvd_spinbox.setSingleStep(100)

        self.min_tvd_spinbox = QSpinBox()
        self.min_tvd_spinbox.setRange(-10000, 10000)  # Adjust based on your data range
        self.min_tvd_spinbox.setSingleStep(100)

        # Connect the spinboxes to update the plot when values change
        self.min_tvd_spinbox.editingFinished.connect(self.plot_current_well)
        self.max_tvd_spinbox.editingFinished.connect(self.plot_current_well)

        # Layout for well selector
        well_selector_layout = QVBoxLayout()
        well_selector_layout.addWidget(self.well_selector)

        # Layout for Previous and Next buttons side by side
        nav_buttons_layout = QHBoxLayout()
        nav_buttons_layout.addWidget(self.prev_button)
        nav_buttons_layout.addWidget(self.next_button)

        # Layout for dropdowns above the color palette
        dropdowns_layout = QVBoxLayout()
        dropdowns_layout.addWidget(QLabel("Select Zone:"))
        dropdowns_layout.addWidget(self.zone_selector)
        dropdowns_layout.addWidget(QLabel("Select Zone Attribute:"))
        dropdowns_layout.addWidget(self.zone_attribute_selector)
        dropdowns_layout.addWidget(QLabel("Color Range:"))
        dropdowns_layout.addWidget(self.color_range_display)

        # Layout for color palette selector and tick size
        palette_layout = QVBoxLayout()
        palette_layout.addWidget(QLabel("Select Palette:"))
        palette_layout.addWidget(self.palette_selector)
        palette_layout.addWidget(QLabel("Tick Size (TVD):"))
        palette_layout.addWidget(self.tick_size_input)

        # Layout for TVD range selectors with labels above them
        tvd_layout = QVBoxLayout()
        tvd_layout.addWidget(QLabel("Max TVD:"))  # Label for max TVD
        tvd_layout.addWidget(self.max_tvd_spinbox)
        tvd_layout.addWidget(QLabel("Min TVD:"))  # Label for min TVD
        tvd_layout.addWidget(self.min_tvd_spinbox)
        

        # Layout for controls
        control_layout = QVBoxLayout()
        control_layout.addLayout(well_selector_layout)
        control_layout.addLayout(nav_buttons_layout)
        control_layout.addLayout(dropdowns_layout)
        control_layout.addLayout(palette_layout)
        control_layout.addLayout(tvd_layout)  # Add TVD range to the control layout
        control_layout.addStretch()

        # Create the plot layout
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
        self.setWindowTitle("Zone Viewer")

        # Set window icon
        self.setWindowIcon(QIcon("icons/ZoneAnalyzer.png"))

        # Initial plot
        self.zone_selector.currentIndexChanged.connect(self.zone_selected)
        self.zone_attribute_selector.currentIndexChanged.connect(self.attribute_selected)
        self.palette_selector.currentIndexChanged.connect(self.palette_selected)

        self.zone_attribute_selector.setEnabled(False)
        self.populate_color_bar_dropdown()
        self.populate_zone_names()
        #self.change_tick_size_from_input()
        self.set_default_tvd_range()
        self.plot_current_well()
        




    def set_default_tvd_range(self):
        depth_grids = self.grid_info_df[self.grid_info_df['Type'] == 'Depth']
    
        if not depth_grids.empty:
            min_z = depth_grids['min_z'].min()
            max_z = depth_grids['max_z'].max()
        
            # Set default TVD range with +/- 50 adjustment
            self.min_tvd_spinbox.setValue(min_z - 50)
            self.max_tvd_spinbox.setValue(max_z + 100)
        else:
            # Set some sensible defaults if no depth grids are found
            self.min_tvd_spinbox.setValue(-100)
            self.max_tvd_spinbox.setValue(1000)

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

    
        if 'UWI' in self.master_df.columns:
            # Filter the master DataFrame based on the current UWI
            self.uwi_att_data = self.master_df[self.master_df['UWI'] == self.current_uwi]
        else:
            # If 'UWI' column does not exist, set self.uwi_att_data to an empty DataFrame
            self.uwi_att_data = pd.DataFrame()

        self.zone_selector.blockSignals(True)
        # Clear existing items
        self.zone_selector.clear()

        # Add default option
        self.zone_selector.addItem("Select Zone")

        if not self.uwi_att_data.empty and 'Zone Name' in self.uwi_att_data.columns:
            # Find unique zone names if data is available
            self.zones = sorted(self.uwi_att_data['Zone Name'].dropna().unique())
            self.zone_selector.addItems(self.zones)
        else:
            # Data is empty or 'Zone Name' column does not exist, add only the default option
            self.zone_selector.addItem("No Zones Available")

        # Set default selection to the first item
        self.zone_selector.setCurrentIndex(0)
        self.zone_selector.blockSignals(False)

        self.zone_attribute_selector .blockSignals(True)

                    # Add placeholder item to Select Attribute Filter
        self.zone_attribute_selector .addItem("Select Zone Attribute")
        self.zone_attribute_selector .setCurrentIndex(0)  # Set placeholder as current
        self.zone_attribute_selector .setEnabled(False)  
        self.zone_attribute_selector .blockSignals(False)


    def populate_zone_attribute(self):
        """Update the zone attribute selector based on the selected zone filter and add a default 'Select Zone Attribute' option."""
        self.zone_attribute_selector.blockSignals(True)
        self.zone_attribute_selector.setEnabled(True)

    
        if 'Zone Name' in self.master_df.columns:
            # Filter the DataFrame for the selected zone
            zone_df = self.master_df[self.master_df['Zone Name'] == self.selected_zone]
        else:
            # If 'Zone Name' column does not exist, set zone_df to an empty DataFrame
            zone_df = pd.DataFrame()

        # Columns to exclude
        columns_to_exclude = ['Zone Name', 'Zone Type', 'Attribute Type', 'Top Depth', 'Base Depth', 'UWI', 'Top X Offset', 'Base X Offset', 'Top Y Offset', 'Base Y Offset']

        # Drop fixed columns and find columns with at least one non-null value
        remaining_df = zone_df.drop(columns=columns_to_exclude, errors='ignore')
        self.attributes_names = sorted(remaining_df.columns[remaining_df.notna().any()].tolist())
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
        
        self.selected_zone = self.zone_selector.currentText()
        self.populate_zone_attribute()






  

        if self.selected_zone != "Select Zone":
            # Filter the master_df to grab the relevant UWI and Zone data
            self.selected_zone_df = self.master_df[
                (self.master_df['Zone Name'] == self.selected_zone) & 
                (self.master_df['UWI'] == self.current_uwi)
            ]

            # Extract specific attributes

            self.selected_zone_df = self.selected_zone_df[['UWI', 'Zone Name', 'Top Depth', 'Base Depth', 
                                                           'Top X Offset', 'Base X Offset', 
                                                           'Top Y Offset', 'Base Y Offset']]
        


            # Trigger replot with the new selected zone data
            if self.next_well == False:
                self.plot_current_well()
        else:
            # If "Select Zone" is selected, clear the zone data
            self.selected_zone_df = None
      
            if self.next_well == False:
                self.plot_current_well()


    def populate_color_bar_dropdown(self):
        """Populate the color bar dropdowns with file names from the Palettes directory."""
        current_dir = os.path.dirname(__file__)
        palettes_path = os.path.join(current_dir, 'Palettes')
    
        # List all .pal files in the Palettes directory
        color_bar_files = [f.split('.')[0] for f in os.listdir(palettes_path) if f.endswith('.pal')]
        self.palette_selector.blockSignals(True)
    
        try:
            # Clear existing items in the palette selector
            self.palette_selector.clear()

            # Add color bar files to the dropdown
            self.palette_selector.addItems(color_bar_files)

            # Set default selection to 'Rainbow' if available
            if 'Rainbow' in color_bar_files:
                self.palette_selector.setCurrentText('Rainbow')
                self.update_color_range()  # Ensure color range is updated for default palette

        except Exception as e:
            print(f"Error populating color bar dropdown: {e}")
          

        finally:
            # Re-enable signals
            self.palette_selector.blockSignals(False)

        self.load_color_palette()



    def load_color_palette(self):
        
        palettes_dir = os.path.join(os.path.dirname(__file__), 'Palettes')
        file_path = os.path.join(palettes_dir, f"{self.palette_name}.pal")
        color_palette = []

        try:
            with open(file_path, 'r') as file:
                lines = file.readlines()
                for line in lines:
                    if line.strip() and not line.strip().startswith(('struct', 'Name', 'Colors', '}', 'ColorPalette')):
                        try:
                            r, g, b = map(int, line.strip().split())
                            color_palette.append(QColor(r, g, b))
                        except ValueError:
                            continue
        except Exception as e:
            print(f"Error loading color palette: {e}")

        return color_palette

    def update_color_range(self):
        """Update the color range display based on the selected palette."""
        self.palette_name = self.palette_selector.currentText()
        color_palette = self.load_color_palette()
        self.display_color_range(color_palette)

    def display_color_range(self, color_palette):
        """Display the color range gradient with dashes and values above it."""
        if not color_palette or self.min_attr is None or self.max_attr is None:
            print("Unable to display color range.")
            self.color_range_display.setPixmap(QPixmap(self.color_range_display.size()))
            return

        pixmap = QPixmap(self.color_range_display.size())
        pixmap.fill(Qt.white)

        painter = QPainter(pixmap)
    
        # Calculate dimensions
        margin = 5
        dash_height = 5
        text_height = 15
        color_bar_height = 20
        total_height = margin + text_height + dash_height + color_bar_height + margin
        color_bar_y = total_height - color_bar_height - margin
        edge_padding = 10  # Increased padding

        # Draw color gradient (left to right: min to max)
        gradient = QLinearGradient(edge_padding, color_bar_y, 
                                   self.color_range_display.width() - edge_padding, color_bar_y)
        for i, color in enumerate(color_palette):
            gradient.setColorAt(i / (len(color_palette) - 1), color)

        painter.setBrush(QBrush(gradient))
        painter.drawRect(edge_padding, color_bar_y, 
                         self.color_range_display.width() - 2 * edge_padding, color_bar_height)

        # Prepare for drawing text and dashes
        painter.setPen(Qt.black)
        font = painter.font()
        font.setPointSize(8)
        painter.setFont(font)

        # Calculate intermediate values
        num_intervals = 4
        interval = (self.max_attr - self.min_attr) / num_intervals
        values = [self.min_attr + i * interval for i in range(num_intervals + 1)]

        for i, value in enumerate(values):
            x = int(i * (self.color_range_display.width() - 2 * edge_padding) / num_intervals) + edge_padding
        
            # Draw dash
            painter.drawLine(x, color_bar_y - dash_height, x, color_bar_y)
        
            # Draw value
            text = f"{value:.2f}"
            text_width = painter.fontMetrics().width(text)
        
            # Adjust text position for edge values
            if i == 0:  # Leftmost value
                text_x = edge_padding
            elif i == num_intervals:  # Rightmost value
                text_x = self.color_range_display.width() - text_width - edge_padding
            else:
                text_x = x - text_width / 2
        
            painter.drawText(text_x, margin + text_height, text)

        painter.end()
        self.color_range_display.setPixmap(pixmap)


    def plot_current_well(self):
        fig = go.Figure()
        try:
            # Extract data for the selected well
            self.current_well_data = self.directional_surveys_df[self.directional_surveys_df['UWI'] == self.current_uwi]
            self.current_well_data = self.current_well_data.reset_index(drop=True)

            if self.current_well_data.empty:
                print(f"No data found for UWI: {self.current_uwi}")
                return

            self.tvd_values = self.current_well_data['TVD'].tolist()
            self.combined_distances = self.current_well_data['Cumulative Distance'].tolist()

            if not self.seismic_data:
                print("No seismic data available, skipping plotting.")
            else:
                # Build KDTree for seismic trace locations

                # Batch query for all well path points to find nearest seismic traces
                well_coords = np.column_stack((self.current_well_data['X Offset'], self.current_well_data['Y Offset']))
                distances, indices = self.seismic_kdtree.query(well_coords)

                seismic_trace_amplitudes = self.seismic_data['trace_data'][indices, :]
                cumulative_distances = np.array(self.combined_distances)

                # Vectorized construction of seismic data
                seismic_time_axis = np.tile(self.seismic_data['time_axis'], len(cumulative_distances))
                seismic_amplitude_flattened = seismic_trace_amplitudes.flatten()

                uwi_seismic_data = np.column_stack((
                    np.repeat(well_coords[:, 0], len(self.seismic_data['time_axis'])),
                    np.repeat(well_coords[:, 1], len(self.seismic_data['time_axis'])),
                    np.repeat(cumulative_distances, len(self.seismic_data['time_axis'])),
                    seismic_time_axis,
                    seismic_amplitude_flattened
                ))

                seismic_df = pd.DataFrame(uwi_seismic_data, columns=['x', 'y', 'cumulative_distance', 'time', 'amplitude'])
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
                    showscale=True
                ))

            # Now plot the grid data over the seismic data (optimized with vectorization)
            well_coords_grid = np.column_stack((self.current_well_data['X Offset'], self.current_well_data['Y Offset']))
            uwi_grid_data = []

            for i, (x2, y2) in enumerate(well_coords_grid):
                # Batch query for grid data using KDTree
                closest_z_values = {grid: None for grid in self.kd_tree_depth_grids.keys()}
                for grid, kdtree in self.kd_tree_depth_grids.items():
                    if kdtree.data.size > 0:
                        distances, indices = kdtree.query((x2, y2))
                        if indices < len(self.depth_grid_data_dict[grid]):
                            closest_z_values[grid] = self.depth_grid_data_dict[grid][indices]

                entry = [x2, y2, self.combined_distances[i]] + [closest_z_values[grid] for grid in self.kd_tree_depth_grids.keys()]
                uwi_grid_data.append(entry)

            valid_grids = [grid for grid in self.kd_tree_depth_grids.keys() if grid in set(self.grid_info_df['Grid']) & set(self.depth_grid_data_df['Grid'])]
            columns = ['x', 'y', 'combined_distance'] + valid_grids

            if all(len(entry) == len(columns) for entry in uwi_grid_data):
                df = pd.DataFrame(uwi_grid_data, columns=columns)
            else:
                print("Error: Length of entries in uwi_grid_data does not match the length of columns")
                return

            grid_values = {grid_name: df[grid_name].tolist() for grid_name in valid_grids}
            sorted_grids = sorted(grid_values.keys(), key=lambda grid: min(grid_values[grid]))

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
                        fill=None
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
            fig.update_yaxes(range=[self.min_tvd_spinbox.value(), self.max_tvd_spinbox.value()])

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



    def get_color(self, value, min_val, max_val):
        self.palette_name = self.palette_selector.currentText()
        color_palette = self.load_color_palette()
    
        if min_val == max_val:
            normalized = 0.5
        else:
            normalized = (value - min_val) / (max_val - min_val)
    
        index = int(normalized * (len(color_palette) - 1))
        return color_palette[index]

    def update_zone_ticks(self):
        if self.selected_zone is None or self.selected_zone == 'Select Zone':
            print("No valid zone selected for tick update.")
            return

        try:
            tick_traces = []
            zone_fills = []
    
            # Get the current UWI
    

            # Get the selected attribute
            attribute = self.zone_attribute_selector.currentText()
            color_zones = attribute != "Select Zone Attribute"


            # Filter the master_df for the current UWI and selected zone
            zone_data = self.master_df[(self.master_df['UWI'] == self.current_uwi) & 
3                                       (self.master_df['Zone Name'] == self.selected_zone)]

            if zone_data.empty:
                print(f"No data found for UWI {self.current_uwi} and zone {self.selected_zone}")
                return



            if color_zones:
                if attribute not in zone_data.columns:
                    print(f"Selected attribute '{attribute}' not found in the data.")
                    return
                # Calculate min and max of the attribute for color scaling
                self.min_attr = zone_data[attribute].min()
                self.max_attr = zone_data[attribute].max()
  

            for _, zone_row in zone_data.iterrows():
                top_md = zone_row['Top Depth']
                base_md = zone_row['Base Depth']

                top_cum_dist = self.interpolate_value(top_md, 'Cumulative Distance')
                base_cum_dist = self.interpolate_value(base_md, 'Cumulative Distance')
                top_tvd = self.interpolate_value(top_md, 'TVD')
                base_tvd = self.interpolate_value(base_md, 'TVD')
        
                if all(v is not None for v in [top_cum_dist, base_cum_dist, top_tvd, base_tvd]):
                    # Add ticks
                    for cum_dist, tvd, name in [(top_cum_dist, top_tvd, 'Top'), (base_cum_dist, base_tvd, 'Base')]:
                        tick_traces.append(go.Scatter(
                            x=[cum_dist, cum_dist],
                            y=[tvd - self.tick_size_value/2, tvd + self.tick_size_value/2],
                            mode='lines',
                            line=dict(color='red', width=2),
                            showlegend=False,
                            hoverinfo='skip'
                        ))
            
                    if color_zones:
                        # Check if the attribute exists in zone_row
                        if attribute not in zone_row.index:
                            print(f"Attribute '{attribute}' not found in zone row.")
                        
                            continue

                        # Add colored fill between top and base
                        attribute_value = zone_row[attribute]
                        color = self.get_color(attribute_value, self.min_attr, self.max_attr)
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
                        # Just add a line connecting top and base without fill
                        tick_traces.append(go.Scatter(
                            x=[top_cum_dist, base_cum_dist],
                            y=[top_tvd, base_tvd],
                            mode='lines',
                            line=dict(color='blue', width=2, dash='dash'),
                            name=f'{self.selected_zone} Boundary'
                        ))
                else:
                    print(f"Unable to create visualization for {self.selected_zone} due to missing interpolated values")

            if tick_traces or zone_fills:
                self.fig.add_traces(zone_fills)
                self.fig.add_traces(tick_traces)
                html_content = py_offline.plot(self.fig, include_plotlyjs='cdn', output_type='div')
                self.plot_widget.setHtml(html_content)

            file_path = os.path.join(os.getcwd(), "plot.html")
            py_offline.plot(self.fig, filename=file_path, auto_open=False)
          
            url = QUrl.fromLocalFile(file_path)
            self.plot_widget.load(url)
          
        except Exception as e:
            print(f"Error updating zone ticks and fills: {str(e)}")
            print("Zone data columns:", zone_data.columns.tolist())
            import traceback
            traceback.print_exc()

    def on_well_selected(self, index):
        try:
            selected_uwi = self.well_selector.currentText()  # Get UWI directly from the selector
            if selected_uwi in self.uwi_list:
                self.current_uwi = selected_uwi
                self.plot_current_well()  # Update the plot for the selected UWI
            else:
                print(f"Selected UWI {selected_uwi} not found in UWI list.")
        except Exception as e:
            print(f"Error in on_well_selected: {e}")

    def on_next(self):
        """Navigate to the next well in alphabetical order."""
        try:
            current_index = self.uwi_list.index(self.current_uwi)
            next_index = (current_index + 1) % len(self.uwi_list)  # Ensure it wraps around
            self.current_uwi = self.uwi_list[next_index]
            self.update_well_selector_to_current_uwi()
            self.plot_current_well()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"An error occurred while processing the next well: {str(e)}")

    def on_prev(self):
        """Navigate to the previous well in alphabetical order."""
        try:
            current_index = self.uwi_list.index(self.current_uwi)
            prev_index = (current_index - 1) % len(self.uwi_list)  # Ensure it wraps around
            self.current_uwi = self.uwi_list[prev_index]
            self.update_well_selector_to_current_uwi()
            self.plot_current_well()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"An error occurred while processing the previous well: {str(e)}")
    def update_well_selector_to_current_uwi(self):
        """Set the dropdown to the current UWI."""
        try:
            current_index = self.uwi_list.index(self.current_uwi)
            self.well_selector.blockSignals(True)
            self.well_selector.setCurrentIndex(current_index)
            self.well_selector.blockSignals(False)
        except ValueError:
            QMessageBox.critical(self, "Error", f"UWI '{self.current_uwi}' not found in the list.")


    def update_well_selector_to_current_uwi(self):
        """Set the dropdown to the current UWI."""
        try:
            current_index = self.uwi_list.index(self.current_uwi)
            self.well_selector.blockSignals(True)
            self.well_selector.setCurrentIndex(current_index)
            self.well_selector.blockSignals(False)
        except ValueError:
            QMessageBox.critical(self, "Error", f"UWI '{self.current_uwi}' not found in the list.")

    def update_well_related_data(self):
        # Re-populate dropdowns and plots based on the newly selected UWI
        self.populate_zone_names()
        self.zone_selected()  # This triggers zone filtering and replotting based on the new UWI

        # Update the plot
        self.plot_current_well()

    def update_plot(self, grid_info_df):
        self.grid_info_df = grid_info_df
        self.plot_current_well()

    def receive_uwi(self):
      
        self.main_app.handle_hover_event(self.current_uwi)

    def on_well_selected(self, index):
        try:
            self.current_index = index
            if self.next_well ==False:
                self.plot_current_well()
        except Exception as e:
            print(f"Error in on_well_selected: {e}")


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
