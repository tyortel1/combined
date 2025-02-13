import pandas as pd
import os
from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QSizePolicy, QMessageBox, QDialog, QSlider, QVBoxLayout, QHBoxLayout, QSizePolicy, QLabel, QComboBox, QFormLayout, QSpacerItem, QSizePolicy
import math
from PySide6.QtCore import Qt, QPointF, Signal, Slot
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtGui import QIcon, QColor, QPainter, QPixmap, QBrush, QLinearGradient
import plotly.graph_objects as go
import plotly.offline as py_offline
import numpy as np
from scipy.spatial import KDTree

class PlotGB(QDialog):
    hoverEvent = Signal(str)
    closed = Signal()

    def __init__(self, db_manager, depth_grid_data_df, grid_info_df, currentLine, kd_tree_depth_grids, depth_grid_data_dict, intersections=None, zone_names=None, master_df=None, seismic_data=None, parent=None, main_app=None):
        super(PlotGB, self).__init__(parent)
        self.main_app = main_app
        self.db_manager = db_manager
        self.depth_grid_data_df = depth_grid_data_df
        self.grid_info_df = grid_info_df
        self.current_line = currentLine
        self.zone_names = zone_names
        self.master_df = master_df
        self.selected_zone = None
        self.selected_attribute = None
        self.kd_tree_depth_grids = kd_tree_depth_grids
        self.depth_grid_data_dict = depth_grid_data_dict
        self.intersections = intersections or []
        self.seismic_data = seismic_data
        self.setWindowTitle("Gun Barrel Plot")
        self.setGeometry(100, 100, 1500, 800)
        self.default_dot_size = 16
        self.current_dot_size = self.default_dot_size
        self.setWindowFlags(Qt.Window | Qt.WindowCloseButtonHint | Qt.WindowMinimizeButtonHint | Qt.WindowMaximizeButtonHint)
        self.current_figure = go.Figure()
        self.setupUi()


    def closeEvent(self, event):
        self.closed.emit()
        event.accept()

    def setupUi(self):
        # Create plot widget
        self.plot_widget = QWebEngineView()
        self.plot_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # Create controls layout
        self.controls_layout = QVBoxLayout()
        self.controls_layout.addSpacing(5)
        self.controls_layout.setContentsMargins(5, 5, 5, 5)

        # Dropdown to select Well Zone
        self.WellZoneLabel = QLabel("Select Well Zone:", self)
        self.controls_layout.addWidget(self.WellZoneLabel)
        self.WellZoneDropdown = QComboBox(self)
        self.WellZoneDropdown.addItem("Select Well Zone")
        self.WellZoneDropdown.currentIndexChanged.connect(self.well_zone_selected)
        self.controls_layout.addWidget(self.WellZoneDropdown)

        # Dropdown to select Well Attribute
        self.WellAttributeLabel = QLabel("Select Well Attribute:", self)
        self.controls_layout.addWidget(self.WellAttributeLabel)
        self.WellAttributeDropdown = QComboBox(self)
        self.WellAttributeDropdown.addItem("Select Well Attribute")
        self.WellAttributeDropdown.currentIndexChanged.connect(self.well_attribute_selected)
        self.WellAttributeDropdown.setEnabled(False)
        self.controls_layout.addWidget(self.WellAttributeDropdown)

        # Color range display for Well Attribute
        self.WellAttributeColorRangeDisplay = QLabel(self)
        self.WellAttributeColorRangeDisplay.setFixedHeight(50)
        self.WellAttributeColorRangeDisplay.setFixedWidth(220)
        self.WellAttributeColorRangeDisplay.setStyleSheet("background-color: white; border: 1px solid black;")
        self.controls_layout.addWidget(self.WellAttributeColorRangeDisplay)

        # Dropdown to select Well Color Bar
        self.WellAttributeColorBarLabel = QLabel("Select Well Color Bar:", self)
        self.controls_layout.addWidget(self.WellAttributeColorBarLabel)
        self.WellAttributeColorBarDropdown = QComboBox(self)
        self.WellAttributeColorBarDropdown.addItem("Rainbow")
        self.WellAttributeColorBarDropdown.currentIndexChanged.connect(self.well_attribute_selected)
        self.controls_layout.addWidget(self.WellAttributeColorBarDropdown)


    # Dot size slider
        self.dotSizeSlider = QSlider(Qt.Horizontal)
        self.dotSizeSlider.setMinimum(1)
        self.dotSizeSlider.setMaximum(30)
        self.dotSizeSlider.setValue(16)  # Default size
        self.dotSizeSlider.setFixedWidth(192)  # Set width to 2 inches (approximately 192 pixels)
        self.dotSizeSlider.valueChanged.connect(self.on_dot_size_changed)
        self.controls_layout.addWidget(QLabel("Dot Size:"))
        self.controls_layout.addWidget(self.dotSizeSlider)
        self.controls_layout.addStretch()

        # Create main layout and add widgets
        main_layout = QHBoxLayout()
        main_layout.addLayout(self.controls_layout)
        main_layout.addWidget(self.plot_widget)
        self.setLayout(main_layout)
        self.setWindowIcon(QIcon("icons/gunb.ico"))

        # Set up QWebChannel
        self.channel = QWebChannel()
        self.channel.registerObject('pyqtConnector', self)
        self.plot_widget.page().setWebChannel(self.channel)

        # Initial plot
        self.populate_color_bar_dropdown()
        self.populate_well_zone_dropdown()
        self.plot_intersection_line()

    def plot_intersection_line(self):
        try:
            print("Plotting intersection line")

            # Extract the X and Y coordinates of the line
            if isinstance(self.current_line[0], QPointF):
                line_coords = [(point.x(), point.y()) for point in self.current_line]
            else:
                line_coords = [(point[0], point[1]) for point in self.current_line]

            # Generate intermediate points along the line
            num_samples = 200  # Number of points to sample along the line
            sampled_line_coords = self.sample_points_along_line(line_coords, num_samples)

            gun_barrel_data = []
            combined_distance = 0

            for i, (x, y) in enumerate(sampled_line_coords):
                # Initialize closest Z values for each grid
                closest_z_values = {grid: None for grid in self.kd_tree_depth_grids}

                # Query each KD-Tree
                for grid, kdtree in self.kd_tree_depth_grids.items():
                    if kdtree.data.size > 0:
                        distances, indices = kdtree.query((x, y))
                        if isinstance(indices, np.ndarray):  # Handle multiple indices
                            indices = indices[0]
                        if 0 <= indices < len(self.depth_grid_data_dict[grid]):
                            z_value = self.depth_grid_data_dict[grid][indices]
                            closest_z_values[grid] = z_value if pd.notnull(z_value) else float('nan')
                            # print(f"Grid: {grid}, Point: ({x}, {y}), Z Value: {z_value}, Index: {indices}, Distances: {distances}")
                        else:
                            print(f"Invalid index for KDTree query: {indices}")

                # Calculate the combined distance
                if i > 0:
                    prev_x, prev_y = sampled_line_coords[i - 1]
                    segment_length = np.sqrt((x - prev_x) ** 2 + (y - prev_y) ** 2)
                    combined_distance += segment_length
                    if np.isinf(combined_distance) or np.isnan(combined_distance):
                        print(f"Invalid combined distance calculation at index {i}: segment_length={segment_length}, combined_distance={combined_distance}")
                else:
                    combined_distance = 0  # First point has distance 0

                # Prepare the entry data
                entry = [x, y, combined_distance] + [closest_z_values[grid] for grid in self.kd_tree_depth_grids]
                gun_barrel_data.append(entry)
            valid_grids = [grid for grid in self.kd_tree_depth_grids.keys() if grid in set(self.grid_info_df['Grid']) & set(self.depth_grid_data_df['Grid'])]
            # Define column names
            columns = ['x', 'y', 'combined_distance'] + valid_grids

            # Create DataFrame with defined columns
            df = pd.DataFrame(gun_barrel_data, columns=columns)
            pd.set_option('display.max_columns', None)
            pd.set_option('display.width', None)
      

            # Extract combined distances and grid values
            combined_distances = df['combined_distance'].tolist()
            grid_values = {grid_name: df[grid_name].tolist() for grid_name in valid_grids}
            sorted_grids = sorted(grid_values.keys(), key=lambda grid: min(grid_values[grid]))
            fig = self.current_figure

            # Plot and fill grids
            for i, grid_name in enumerate(sorted_grids):
                try:
                    # Ensure the grid name exists in the DataFrame
                    grid_row = self.grid_info_df.loc[self.grid_info_df['Grid'] == grid_name]
                    if grid_row.empty:
                        print(f"Grid {grid_name} not found in grid_info_df")
                        continue

                    r, g, b = grid_row['Color (RGB)'].values[0]
                    grid_color_rgb = f'{r}, {g}, {b}'
                    grid_color_rgba = f'rgba({r}, {g}, {b}, 0.3)'


                    
                    r, g, b = grid_row['Color (RGB)'].values[0]
                    grid_color_rgb = f'{r}, {g}, {b}'
                    grid_color_rgba = f'rgba({r}, {g}, {b}, 0.3)'

                                        # Determine the color of the previous grid if it exists
                    if i + 1 < len(sorted_grids):
                        next_grid_name = sorted_grids[i + 1]
                        next_grid_row = self.grid_info_df.loc[self.grid_info_df['Grid'] == next_grid_name]
                        if not next_grid_row.empty:
                            next_r, next_g, next_b = next_grid_row['Color (RGB)'].values[0]
                            next_grid_rgba = f'rgba({next_r}, {next_g}, {next_b}, 0.3)'
                        else:
                            next_grid_rgba = 'rgba(0, 0, 0, 0.3)'  # Fallback if the next grid is not found
                    else:
                        next_grid_rgba = 'rgba(0, 0, 0, 0.3)'  # Fallback for the last grid

                    # Ensure the grid values are available
                    if grid_name not in grid_values:
                        print(f"Grid values for {grid_name} not found")
                        continue

                    # Plot the grid line with the grid's color
                    fig.add_trace(go.Scatter(
                        x=combined_distances,
                        y=grid_values[grid_name],
                        mode='lines',
                        name=grid_name,
                        line=dict(color=f'rgb({grid_color_rgb})')
                    ))

                    # Only fill between the current grid and the grid directly below it
                    if i < len(sorted_grids) - 1:
                        next_grid_name = sorted_grids[i + 1]
                        if next_grid_name not in grid_values:
                            print(f"Next grid values for {next_grid_name} not found")
                            continue

                        next_grid_values = grid_values[next_grid_name]
                        fig.add_trace(go.Scatter(
                            x=combined_distances,
                            y=next_grid_values,
                            fill='tonexty',
                            fillcolor=next_grid_rgba,
                            mode='none',
                            showlegend=False
                        ))

                except IndexError as e:
                    print(f"Error accessing data for grid {grid_name}: {e}")
                    continue
                except Exception as e:
                    print(f"Unexpected error for grid {grid_name}: {e}")
                    continue

            # Extracting intersection information and filtering invalid TVDs
            intersection_distances = [item[4] for item in self.intersections]
            intersection_tvds = [item[3] for item in self.intersections]
            intersection_UWIs = [item[0] for item in self.intersections]

            # Filter out invalid TVDs (like inf or NaN)
            valid_intersections = [(dist, tvd, UWI) for dist, tvd, UWI in zip(intersection_distances, intersection_tvds, intersection_UWIs) if np.isfinite(tvd)]
            intersection_distances, intersection_tvds, intersection_UWIs = zip(*valid_intersections) if valid_intersections else ([], [], [])


            fig.add_trace(go.Scatter(
                x=intersection_distances,
                y=intersection_tvds,
                mode='markers',
                name='Intersection Points',
                marker=dict(color='black', size=self.default_dot_size),
                text=intersection_UWIs,  # Add UWI as hover text
                hoverinfo='text'  # Display the hover text
            ))

            # Add annotations for each UWI label
            annotations = []
            for i, UWI in enumerate(intersection_UWIs):
                annotations.append(
                    dict(
                        x=intersection_distances[i],
                        y=intersection_tvds[i],
                        text=UWI,
                        showarrow=False,
                        textangle=-45,  # Rotate text by 45 degrees
                        xanchor='left',
                        yanchor='bottom',
                    )
                )

            # Update layout with annotations
            fig.update_layout(
                annotations=annotations
            )
            fig.update_layout(
                title='',  # Remove the title
                xaxis=dict(
                    showline=True,
                    showgrid=False,
                    ticks='inside',  # Keep ticks inside the plot
                    tickcolor='black',
                    showticklabels=True,  # Show the tick numbers
                    title='',  # Remove x-axis title
                    ticklabelposition="inside",  # Move labels inside the plot
                ),
                yaxis=dict(
                    showline=True,
                    showgrid=False,
                    ticks='inside',  # Keep ticks inside the plot
                    tickcolor='black',
                    showticklabels=True,  # Show the tick numbers
                    title='',  # Remove y-axis title
                    ticklabelposition="inside",  # Move labels inside the plot
                ),
                font=dict(color='black'),  # Keep default text color
                margin=dict(l=0, r=0, t=0, b=0),  # Remove all margins
                plot_bgcolor='rgba(0,0,0,0)',  # Transparent plot background
                paper_bgcolor='rgba(0,0,0,0)',  # Transparent paper background
                legend=dict(
                    font=dict(color='black'),
                    bgcolor='rgba(255,255,255,0.5)',  # Transparent white background for the legend
                    orientation="v",  # Vertical legend
                    x=0.95,  # Right aligned
                    xanchor='right',
                    y=0.05,  # Bottom aligned
                    yanchor='bottom',
                ),
                autosize=True,  # Automatically size the plot to fill the available space
            )
            # Render Plotly figure as HTML and display it in the QWebEngineView
            html_content = py_offline.plot(fig, include_plotlyjs='cdn', output_type='div')

            # Inject JavaScript for handling hover events
            html_content += """
            <script src="qrc:///qtwebchannel/qwebchannel.js"></script>
            <script>
            new QWebChannel(qt.webChannelTransport, function (channel) {
                window.pyqtConnector = channel.objects.pyqtConnector;
                // Initialize hover events after QWebChannel is set up
                initializeHoverEvents();
            });

            function initializeHoverEvents() {
                console.log('Initializing hover events');
                var plotElement = document.getElementsByClassName('plotly-graph-div')[0];
                if (!plotElement) {
                    console.error('Plot element not found');
                    return;
                }
                var hoverTimeout;
                plotElement.on('plotly_hover', function(data){
                    console.log('Hover event detected');
                    var infotext = data.points.map(function(d){ return (d.text); });
                    hoverTimeout = setTimeout(function() {
                        if (window.pyqtConnector) {
                            console.log('Sending hover event to PyQt with UWI:', infotext[0]);
                            window.pyqtConnector.receiveHoverEvent(infotext[0]);
                        } else {
                            console.error('pyqtConnector not found');
                        }
                    }, 500);
                });
                plotElement.on('plotly_unhover', function(data){
                    console.log('Unhover event detected');
                    clearTimeout(hoverTimeout);
                });
            }
            </script>
            """

            self.plot_widget.setHtml(html_content)

        except IndexError as e:
            print(f"IndexError: {e}")
        except Exception as e:
            print(f"Error plotting intersection line: {e}")

    def sample_points_along_line(self, line_coords, num_samples):
        sampled_points = []
        total_length = sum(np.sqrt((line_coords[i][0] - line_coords[i-1][0])**2 + (line_coords[i][1] - line_coords[i-1][1])**2) for i in range(1, len(line_coords)))
        step = total_length / (num_samples - 1)
        accumulated_length = 0
        sampled_points.append(line_coords[0])

        for i in range(1, len(line_coords)):
            segment_length = np.sqrt((line_coords[i][0] - line_coords[i-1][0])**2 + (line_coords[i][1] - line_coords[i-1][1])**2)
            while accumulated_length + segment_length >= step:
                t = (step - accumulated_length) / segment_length
                new_x = line_coords[i-1][0] + t * (line_coords[i][0] - line_coords[i-1][0])
                new_y = line_coords[i-1][1] + t * (line_coords[i][1] - line_coords[i-1][1])
                sampled_points.append((new_x, new_y))
                accumulated_length -= step
            accumulated_length += segment_length
    
        sampled_points.append(line_coords[-1])
        return sampled_points

    def update_data(self,grid_info_df):
        self.grid_info_df = grid_info_df
        self.update_plot(self.grid_info_df) 

    def update_plot(self, grid_info_df):
        self.grid_info_df = grid_info_df
        self.plot_intersection_line() 

    @Slot(str)
    def receiveHoverEvent(self, UWI):
        print(f'Hover event received for UWI: {UWI}')
        self.hoverEvent.emit(UWI)
        self.main_app.handle_hover_event(UWI)

    def populate_well_zone_dropdown(self):
        """Populates the dropdown with unique zone names where the Attribute Type is 'Well'."""

        # Clear the dropdown and set a default option
        self.WellZoneDropdown.blockSignals(True)
        self.WellZoneDropdown.clear()
        self.WellZoneDropdown.addItem("Select Well Zone")
    
        zone_names = self.db_manager.fetch_zone_names_by_type("Well")
        if zone_names:
            # Extract first element from each tuple and sort
            zone_names = [name[0] for name in zone_names if name[0].strip()]  # Also strip whitespace
            self.well_zone_names = sorted(zone_names)
            self.WellZoneDropdown.addItems(self.well_zone_names)

        self.WellZoneDropdown.blockSignals(False)
    def populate_color_bar_dropdown(self):
        """Populate the color bar dropdown with file names from the Palettes directory."""
        palettes_path = os.path.join(os.path.dirname(__file__), 'Palettes')
        try:
            color_bar_files = [f.split('.')[0] for f in os.listdir(palettes_path) if f.endswith('.pal')]
            self.WellAttributeColorBarDropdown.addItems(color_bar_files)
        except FileNotFoundError:
            print(f"Directory not found: {palettes_path}")
        except Exception as e:
            print(f"Error populating color bar dropdown: {e}")

    def well_zone_selected(self):
        """Handles the selection of a zone from the dropdown."""
        self.selected_zone = self.WellZoneDropdown.currentText()
 
        if self.selected_zone == "Select Well Zone":
            self.WellAttributeDropdown.setEnabled(False)
            self.WellAttributeDropdown.clear()
            return

        self.WellAttributeDropdown.blockSignals(True)
        self.WellAttributeDropdown.clear()
        self.populate_well_attribute_dropdown()
        self.WellAttributeDropdown.blockSignals(False)
        self.WellAttributeDropdown.setEnabled(True)

    def populate_well_attribute_dropdown(self):
        """Populate the well attribute dropdown with numeric attributes for the selected well zone."""
    
        # Get the selected well zone from the well zone dropdown
        selected_well_zone = self.WellZoneDropdown.currentText()
    
        # Clear the dropdown before populating
        self.WellAttributeDropdown.blockSignals(True)
        self.WellAttributeDropdown.clear()
        self.WellAttributeDropdown.addItem("Select Well Attribute")

        if selected_well_zone != "Select Well Zone":
            # Fetch the data for the selected zone
            try:
                well_zone_df = self.db_manager.fetch_table_data(selected_well_zone)
                self.cached_well_zone_df = well_zone_df  # Cache the data
            
                if well_zone_df is not None and not well_zone_df.empty:
                    # Drop fixed columns that are not relevant for selection
                    columns_to_exclude = [
                        'Zone_Name', 'Zone_Type', 'Attribute_Type',
                        'Top_Depth', 'Base_Depth', 'UWI',
                        'Top_X_Offset', 'Base_X_Offset', 'Top_Y_Offset', 'Base_Y_Offset',
                        'Angle_Top', 'Angle_Base'
                    ]
                    remaining_df = well_zone_df.drop(columns=columns_to_exclude, errors='ignore')
                
                    # Process numeric and date columns
                    numeric_columns = remaining_df.select_dtypes(include=[np.number]).columns.tolist()
                    numeric_columns = [col for col in numeric_columns if remaining_df[col].max() - remaining_df[col].min() > 0]
                
                    date_columns = remaining_df.select_dtypes(include=['datetime64[ns]', 'datetime64']).columns.tolist()
                
                    combined_columns = numeric_columns + date_columns
                    non_null_columns = [col for col in combined_columns if remaining_df[col].notnull().any()]
                    non_null_columns.sort()
                
                    if non_null_columns:
                        self.WellAttributeDropdown.addItems(non_null_columns)
                        self.WellAttributeDropdown.setEnabled(True)
                    else:
                        self.WellAttributeDropdown.addItem("No Attributes Available")
                        self.WellAttributeDropdown.setEnabled(False)
                    
            except Exception as e:
                print(f"Error populating well attributes: {e}")
                self.WellAttributeDropdown.addItem("Error Loading Attributes")
                self.WellAttributeDropdown.setEnabled(False)
    
        self.WellAttributeDropdown.blockSignals(False)

    def well_attribute_selected(self):
        """Handle the event when a well attribute is selected."""
        self.selected_attribute = self.WellAttributeDropdown.currentText()
    
        if self.selected_attribute == "Select Well Attribute" or not self.selected_attribute:
            return
        if self.selected_zone is None:
            print("No zone selected.")
            return
        
        try:
            # Use cached zone data instead of master_df
            if not hasattr(self, 'cached_well_zone_df') or self.cached_well_zone_df is None:
                print("No zone data cached.")
                return
            
            # Extract valid UWIs from intersections
            valid_intersection_UWIs = [item[0] for item in self.intersections if np.isfinite(item[3])]
            print("Valid UWIs:", valid_intersection_UWIs)
        
            # Filter the cached zone data
            filtered_df = self.cached_well_zone_df[
                self.cached_well_zone_df['UWI'].isin(valid_intersection_UWIs)
            ][['UWI', self.selected_attribute]]
        
            if filtered_df.empty:
                print("No matching data found for the selected UWIs and attribute")
                return
            
            # Calculate the min and max values for the selected attribute
            min_value = filtered_df[self.selected_attribute].min()
            max_value = filtered_df[self.selected_attribute].max()
        
            # Load color palette
            color_bar_name = self.WellAttributeColorBarDropdown.currentText()
            palettes_dir = os.path.join(os.path.dirname(__file__), 'Palettes')
            file_path = os.path.join(palettes_dir, f"{color_bar_name}.pal")  # Add .pal extension
        
            color_palette = self.load_color_palette(file_path)
        
            # Create color map for each UWI
            UWI_color_map = {}
            for UWI in valid_intersection_UWIs:
                UWI_values = filtered_df[filtered_df['UWI'] == UWI][self.selected_attribute]
                if not UWI_values.empty:
                    value = UWI_values.iloc[0]  # Take first value instead of mean
                    print(f"UWI: {UWI}, Value: {value}")
                    if pd.notnull(value):  # Check for null values
                        color = self.map_value_to_color(value, min_value, max_value, color_palette)
                        UWI_color_map[UWI] = color
        
            print("Final UWI Color Map:", UWI_color_map)
        
            # Update displays
            self.display_color_range(self.WellAttributeColorRangeDisplay, color_palette, min_value, max_value)
            self.update_intersection_plot(UWI_color_map)
        
        except Exception as e:
            print(f"Error in well_attribute_selected: {str(e)}")
            import traceback
            traceback.print_exc()


    def on_dot_size_changed(self):
        new_size = self.dotSizeSlider.value()
        self.update_dot_size(new_size)


    def update_intersection_plot(self, UWI_color_map):
        """Updates the colors of the intersection points without altering existing grid lines or size."""
        try:
            fig = self.current_figure

            # Find the trace corresponding to the intersection points
            intersection_trace = next(
                (trace for trace in fig.data if trace.name == 'Intersection Points'), 
                None
            )

            if intersection_trace is not None:
                intersection_UWIs = intersection_trace.text
                # Update the colors of the dots based on the new UWI_color_map
                new_colors = [self.map_qcolor_to_hex(UWI_color_map.get(UWI, 'black')) for UWI in intersection_UWIs]
            
                # Update both color and maintain current size
                fig.update_traces(
                    selector=dict(name='Intersection Points'),
                    marker=dict(color=new_colors, size=self.current_dot_size)
                )
            
                # Update the plot without redrawing everything
                self.plot_widget.page().runJavaScript(f"""
                    Plotly.restyle(document.getElementsByClassName('plotly-graph-div')[0], 
                                   {{marker: {{color: {new_colors}, size: {self.current_dot_size}}}}}, 
                                   {fig.data.index(intersection_trace)});
                """)
            else:
                print("Intersection points trace not found.")
        except Exception as e:
            print(f"Error updating intersection plot: {e}")

    def update_dot_size(self, point_size=16):
        """Updates the size of the intersection points without altering colors or existing grid lines."""
        try:
            fig = self.current_figure

            # Find the trace corresponding to the intersection points
            intersection_trace = next(
                (trace for trace in fig.data if trace.name == 'Intersection Points'), 
                None
            )

            if intersection_trace is not None:
                # Update only the size of the markers
                fig.update_traces(
                    selector=dict(name='Intersection Points'),
                    marker=dict(size=point_size)
                )

                # Update the plot without redrawing everything
                self.plot_widget.page().runJavaScript(f"""
                    Plotly.restyle(document.getElementsByClassName('plotly-graph-div')[0], 
                                   {{'marker.size': {point_size}}}, 
                                   {fig.data.index(intersection_trace)});
                """)
                print(f"Updated dot size to {point_size}")
            else:
                print("Intersection points trace not found.")
        except Exception as e:
            print(f"Error updating dot size: {e}")


    def map_qcolor_to_hex(self, qcolor):
        """Convert a QColor or RGB tuple to a hex string."""
        if isinstance(qcolor, QColor):
            return qcolor.name()  # Returns '#RRGGBB'
        elif isinstance(qcolor, tuple) and len(qcolor) >= 3:
            # Handle RGB tuple
            r, g, b = qcolor[:3]
            return f"#{r:02x}{g:02x}{b:02x}"
        return "#000000"  # Default black

    def load_color_palette(self, file_path):
        """Load color palette and return list of QColors."""
        base_path = file_path.replace('.pal.pal', '.pal')
        color_palette = []
    
        try:
            with open(base_path, 'r') as file:
                lines = file.readlines()
                for line in lines:
                    if line.strip() and not line.strip().startswith(('struct', 'Name', 'Colors', '}', 'ColorPalette')):
                        try:
                            r, g, b = map(int, line.strip().split())
                            color_palette.append(QColor(r, g, b))
                        except ValueError:
                            continue
        except Exception as e:
            print(f"Error loading color palette from {base_path}: {e}")
            return [QColor(0, 0, 0)]  # Return default black QColor
    
        return color_palette if color_palette else [QColor(0, 0, 0)]

    def map_value_to_color(self, value, min_value, max_value, color_palette):
        """Map a value to a QColor using the provided color palette."""
        if not color_palette:
            return QColor(0, 0, 0)
        
        if math.isnan(value) or math.isnan(min_value) or math.isnan(max_value):
            return QColor(0, 0, 0)  # Return black for NaN values
        
        if max_value == min_value:
            return color_palette[0]
        
        try:
            normalized_value = (value - min_value) / (max_value - min_value)
            normalized_value = max(0.0, min(1.0, normalized_value))  # Clamp between 0 and 1
        
            index = int(normalized_value * (len(color_palette) - 1))
            index = max(0, min(index, len(color_palette) - 1))  # Ensure index is in bounds
        
            return color_palette[index]
        except Exception as e:
            print(f"Error in map_value_to_color: {e}")
            return QColor(0, 0, 0)  # Return black on error

    def display_color_range(self, color_range_display, color_palette, min_attr, max_attr):
        if not color_palette or min_attr is None or max_attr is None:
            print("Unable to display color range.")
            color_range_display.setPixmap(QPixmap(color_range_display.size()))
            return

        pixmap = QPixmap(color_range_display.size())
        pixmap.fill(Qt.white)

        painter = QPainter(pixmap)
        margin = 5
        dash_height = 5
        text_height = 10
        color_bar_height = 20
        total_height = margin + text_height + dash_height + color_bar_height + margin
        color_bar_y = total_height - color_bar_height - margin
        edge_padding = 10

        gradient = QLinearGradient(edge_padding, color_bar_y, 
                                   color_range_display.width() - edge_padding, color_bar_y)
        for i, color in enumerate(color_palette):
            gradient.setColorAt(i / (len(color_palette) - 1), color)

        painter.setBrush(QBrush(gradient))
        painter.drawRect(edge_padding, color_bar_y, 
                         color_range_display.width() - 2 * edge_padding, color_bar_height)

        painter.setPen(Qt.black)
        font = painter.font()
        font.setPointSize(5)
        painter.setFont(font)

        num_intervals = 4
        interval = (max_attr - min_attr) / num_intervals
        values = [round(min_attr + i * interval) for i in range(num_intervals + 1)]

        for i, value in enumerate(values):
            x = int(i * (color_range_display.width() - 2 * edge_padding) / num_intervals) + edge_padding

            painter.drawLine(x, color_bar_y - dash_height, x, color_bar_y)

            text = f"{value}"
            text_width = painter.fontMetrics().horizontalAdvance(text)

            if i == 0:
                text_x = edge_padding
            elif i == num_intervals:
                text_x = color_range_display.width() - text_width - edge_padding
            else:
                text_x = x - text_width / 2

            painter.drawText(text_x, margin + text_height, text)

        painter.end()
        color_range_display.setPixmap(pixmap)






if __name__ == "__main__":
    import sys
    from PySide6.QtWidgets import QApplication

    # Mock data for testing
    depth_grid_data = {
        'Grid': ['Grid1', 'Grid1', 'Grid2', 'Grid2'],
        'X': [0, 1, 0, 1],
        'Y': [0, 0, 1, 1],
        'Z': [10, 20, 30, 40]
    }
    depth_grid_data_df = pd.DataFrame(depth_grid_data)

    depth_grid_color_data = {
        'Depth Grid Name': ['Grid1', 'Grid2'],
        'Color (RGB)': [(255, 0, 0), (0, 255, 0)]
    }
    depth_grid_color_df = pd.DataFrame(depth_grid_color_data)

    currentLine = [QPointF(0, 0), QPointF(1, 1)]
    intersections = [(1, 2, 3, 4, 5)]

    # Create KD-Trees for testing
    kd_tree_depth_grids = {grid: KDTree(depth_grid_data_df[depth_grid_data_df['Grid'] == grid][['X', 'Y']].values) for grid in depth_grid_data_df['Grid'].unique()}

    # Create Depth Grid Data Dictionary for testing
    depth_grid_data_dict = {grid: depth_grid_data_df[depth_grid_data_df['Grid'] == grid]['Z'].values for grid in depth_grid_data_df['Grid'].unique()}

    app = QApplication(sys.argv)
    window = PlotGB(depth_grid_data_df, depth_grid_color_df, currentLine, kd_tree_depth_grids, depth_grid_data_dict, intersections)
    window.show()
    sys.exit(app.exec_())
