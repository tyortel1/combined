import pandas as pd
import os
from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QSizePolicy, QFrame, QGraphicsDropShadowEffect, QMessageBox, QDialog, QSlider, QVBoxLayout, QHBoxLayout, QSizePolicy, QLabel, QComboBox, QFormLayout, QSpacerItem, QSizePolicy
import math
from PySide6.QtCore import Qt, QPointF, Signal, Slot
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtGui import QIcon, QColor, QPainter, QPixmap, QBrush, QLinearGradient
import plotly.graph_objects as go
import plotly.offline as py_offline
import numpy as np
from scipy.spatial import KDTree
from StyledDropdown import StyledDropdown, StyledInputBox, StyledBaseWidget
from StyledButton import StyledButton
from StyledColorbar import StyledColorBar 

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
        self.labels = [
            "Zone",
            "Attribute",
            "Color Bar",
            "Dot Size"
        ]
        StyledDropdown.calculate_label_width(self.labels)

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

        def create_colorbar():
            colorbar = StyledColorBar("Color Bar")
            colorbar.colorbar_dropdown.label.setFixedWidth(StyledDropdown.label_width)
            colorbar.setStyleSheet("""
                QLabel {
                    background-color: transparent;
                    border: none;
                    padding: 0;
                    margin: 0;
                }
            """)
            return colorbar

        # Create plot widget
        self.plot_widget = QWebEngineView()
        self.plot_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # Zone and Attribute Section with Colorbar
        zoneAttrFrame, zoneAttrLayout = create_section("Zone and Attribute", fixed_height=170)
    
        # Well Zone Dropdown
        self.WellZoneDropdown = create_dropdown("Zone")
        self.WellZoneDropdown.combo.addItem("Select Well Zone")
        self.WellZoneDropdown.combo.currentIndexChanged.connect(self.well_zone_selected)
    
        # Well Attribute Dropdown
        self.WellAttributeDropdown = create_dropdown("Attribute")
        self.WellAttributeDropdown.combo.addItem("Select Well Attribute")
        self.WellAttributeDropdown.combo.currentIndexChanged.connect(self.well_attribute_selected)
        self.WellAttributeDropdown.setEnabled(False)
    
        # Color Bar
        self.colorbar = create_colorbar()
        self.colorbar.colorbar_dropdown.combo.currentIndexChanged.connect(self.on_colorbar_palette_changed)

    
        # Add widgets to zone attribute layout
        zoneAttrLayout.addWidget(self.WellZoneDropdown)
        zoneAttrLayout.addWidget(self.WellAttributeDropdown)
        zoneAttrLayout.addWidget(self.colorbar)

        # Dot Size Section
        dotSizeFrame, dotSizeLayout = create_section("Dot Size", fixed_height=70)
    
        # Dot size slider with label
        sliderLabel = QLabel("Dot Size:")
        sliderLabel.setStyleSheet("""
            QLabel {
                background-color: transparent;
                border: none;
                padding: 0;
                margin: 0;
            }
        """)

        self.dotSizeSlider = QSlider(Qt.Horizontal)
        self.dotSizeSlider.setMinimum(1)
        self.dotSizeSlider.setMaximum(30)
        self.dotSizeSlider.setValue(16)
        self.dotSizeSlider.setFixedWidth(192)
        self.dotSizeSlider.valueChanged.connect(self.on_dot_size_changed)

        # Add widgets to dot size layout
        dotSizeLayout.addWidget(sliderLabel)
        dotSizeLayout.addWidget(self.dotSizeSlider)

        # Create main layout
        main_layout = QHBoxLayout()
    
        # Left side - controls
        left_layout = QVBoxLayout()
        left_layout.addWidget(zoneAttrFrame)
        left_layout.addWidget(dotSizeFrame)
        left_layout.addStretch()
    
        left_frame = QFrame()
        left_frame.setStyleSheet("""
            QFrame {
                background-color: white;
                border: none;
            }
        """)
        left_frame.setLayout(left_layout)

        # Add left frame and plot widget to main layout
        main_layout.addWidget(left_frame, stretch=1)
        main_layout.addWidget(self.plot_widget, stretch=7)
    
        self.setLayout(main_layout)

        # Set window properties
        self.setWindowTitle("Gun Barrel Plot")
        self.setGeometry(100, 100, 1500, 800)
        self.setWindowFlags(Qt.Window | Qt.WindowCloseButtonHint | Qt.WindowMinimizeButtonHint | Qt.WindowMaximizeButtonHint)
        self.setWindowIcon(QIcon("icons/gunb.ico"))

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

            valid_grids = [grid for grid in self.kd_tree_depth_grids.keys() if grid in set(self.grid_info_df['Grid']) & set(self.depth_grid_data_df['Grid'])]
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
                entry = [x, y, combined_distance] + [closest_z_values[grid] for grid in valid_grids]

                gun_barrel_data.append(entry)
            
            # Define column names
            columns = ['x', 'y', 'combined_distance'] + valid_grids

                        # Add this right after calculating valid_grids
            print(f"Valid grids: {valid_grids}")
            print(f"Number of valid grids: {len(valid_grids)}")
            print(f"All kd_tree_depth_grids keys: {list(self.kd_tree_depth_grids.keys())}")
            print(f"Number of kd_tree_depth_grids: {len(self.kd_tree_depth_grids)}")
            print(f"Grid columns in depth_grid_data_df: {self.depth_grid_data_df['Grid'].unique().tolist()}")
            print(f"Number of grids in depth_grid_data_df: {len(self.depth_grid_data_df['Grid'].unique())}")
            print(f"Grid columns in grid_info_df: {self.grid_info_df['Grid'].unique().tolist()}")
            print(f"Number of grids in grid_info_df: {len(self.grid_info_df['Grid'].unique())}")

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
        # Clear the dropdown and set a default option
        self.WellZoneDropdown.combo.blockSignals(True)  # Changed
        self.WellZoneDropdown.combo.clear()  # Changed
        self.WellZoneDropdown.combo.addItem("Select Well Zone")  # Changed
    
        zone_names = self.db_manager.fetch_zone_names_by_type("Well")
        if zone_names:
            zone_names = [name[0] for name in zone_names if name[0].strip()]
            self.well_zone_names = sorted(zone_names)
            self.WellZoneDropdown.combo.addItems(self.well_zone_names)  # Changed

        self.WellZoneDropdown.combo.blockSignals(False)  # Changed


    def well_zone_selected(self):
        print("Selected Zone:", self.WellZoneDropdown.combo.currentText())
        self.selected_zone = self.WellZoneDropdown.combo.currentText()
 
        if self.selected_zone == "Select Well Zone":
            print("No zone selected, disabling attribute dropdown")
            # Clear attribute dropdown
            self.WellAttributeDropdown.combo.clear()
            self.WellAttributeDropdown.combo.addItem("Select Well Attribute")
            self.WellAttributeDropdown.combo.setEnabled(False)
        
            # Reset all intersection points to black
            try:
                fig = self.current_figure
                # Find the trace corresponding to the intersection points
                intersection_trace = next(
                    (trace for trace in fig.data if trace.name == 'Intersection Points'), 
                    None
                )
            
                if intersection_trace is not None:
                    # Update to set all points to black
                    fig.update_traces(
                        selector=dict(name='Intersection Points'),
                        marker=dict(color='black', size=self.current_dot_size)
                    )
                
                    # Update the plot without redrawing everything
                    self.plot_widget.page().runJavaScript(f"""
                        Plotly.restyle(document.getElementsByClassName('plotly-graph-div')[0], 
                                       {{marker: {{color: 'black', size: {self.current_dot_size}}}}}, 
                                       {fig.data.index(intersection_trace)});
                    """)
            
                # Clear the color range display
                self.colorbar.display_color_range(0, 1)  # Reset to default range
            
            except Exception as e:
                print(f"Error resetting intersection colors: {e}")
            
            return

        print("Preparing to populate attribute dropdown")
        self.WellAttributeDropdown.combo.blockSignals(True)
        self.WellAttributeDropdown.combo.clear()
        self.populate_well_attribute_dropdown()
        self.WellAttributeDropdown.combo.blockSignals(False)

        # Debug prints
        print("Attribute Dropdown Item Count:", self.WellAttributeDropdown.combo.count())
        print("Is Attribute Dropdown Enabled?", self.WellAttributeDropdown.isEnabled())
        print("Is Attribute Dropdown Combo Enabled?", self.WellAttributeDropdown.combo.isEnabled())

        # Explicitly set to "Select Well Attribute"
        self.WellAttributeDropdown.combo.setCurrentIndex(0)
        self.WellAttributeDropdown.setEnabled(True)
        self.WellAttributeDropdown.combo.setEnabled(True)


    def on_colorbar_palette_changed(self):
        print("Colorbar palette changed")
        # If an attribute is already selected, reapply the color mapping
        if self.selected_attribute and self.selected_attribute != "Select Well Attribute":
            self.well_attribute_selected()

    def populate_well_attribute_dropdown(self):
        selected_well_zone = self.WellZoneDropdown.combo.currentText()  # Changed
    
        self.WellAttributeDropdown.combo.blockSignals(True)  # Changed
        self.WellAttributeDropdown.combo.clear()  # Changed
        self.WellAttributeDropdown.combo.addItem("Select Well Attribute")  # Changed

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
                    self.WellAttributeDropdown.combo.addItems(non_null_columns)  # Changed
                    self.WellAttributeDropdown.combo.setEnabled(True)  # Changed
                else:
                    self.WellAttributeDropdown.combo.addItem("No Attributes Available")  # Changed
                    self.WellAttributeDropdown.combo.setEnabled(False)  # Changed
                    
            except Exception as e:
                print(f"Error populating well attributes: {e}")
                self.WellAttributeDropdown.combo.addItem("Error Loading Attributes")
                self.WellAttributeDropdown.combo.setEnabled(False)
    
        self.WellAttributeDropdown.combo.blockSignals(False) 

    def well_attribute_selected(self):
        """Handle the event when a well attribute is selected."""
        self.selected_attribute = self.WellAttributeDropdown.combo.currentText() 
    
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

            # Update the color bar display
            self.colorbar.display_color_range(min_value, max_value)
    
            # Get the color palette from StyledColorBar
            color_palette = self.colorbar.selected_color_palette
    
            # Create color map for each UWI
            UWI_color_map = {}
            for UWI in valid_intersection_UWIs:
                UWI_values = filtered_df[filtered_df['UWI'] == UWI][self.selected_attribute]
                if not UWI_values.empty:
                    value = UWI_values.iloc[0]
                    if pd.notnull(value):
                        color = self.colorbar.map_value_to_color(value, min_value, max_value, color_palette)
                        UWI_color_map[UWI] = color

            # Update the plot
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
