import pandas as pd
from PySide2.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QSizePolicy, QMessageBox
from PySide2.QtCore import Qt, QPointF, Signal, Slot
from PySide2.QtWebEngineWidgets import QWebEngineView
from PySide2.QtWebChannel import QWebChannel
from PySide2.QtGui import QIcon
import plotly.graph_objects as go
import plotly.offline as py_offline
import numpy as np
from scipy.spatial import KDTree

class PlotGB(QDialog):
    hoverEvent = Signal(str)
    closed = Signal()

    def __init__(self, depth_grid_data_df, grid_info_df, currentLine, kd_tree_depth_grids, depth_grid_data_dict, intersections=None, main_app=None, parent=None):
        super(PlotGB, self).__init__(parent)
        self.main_app = main_app
        self.depth_grid_data_df = depth_grid_data_df
        self.grid_info_df = grid_info_df
        self.current_line = currentLine
        self.kd_tree_depth_grids = kd_tree_depth_grids
        self.depth_grid_data_dict = depth_grid_data_dict  # Depth grid dictionary
        self.intersections = intersections or []
        self.setWindowTitle("Gun Barrel Plot")
        self.setGeometry(100, 100, 1200, 800)
        self.setupUi()

    def closeEvent(self, event):
        self.closed.emit()
        event.accept()

    def setupUi(self):
        # Create the plot layout
        self.plot_widget = QWebEngineView()
        self.plot_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.plot_layout = QVBoxLayout()
        self.plot_layout.addWidget(self.plot_widget)

        # Set up QWebChannel
        self.channel = QWebChannel()
        self.channel.registerObject('pyqtConnector', self)
        self.plot_widget.page().setWebChannel(self.channel)

        # Main layout
        main_layout = QHBoxLayout()
        main_layout.addLayout(self.plot_layout)
        self.setLayout(main_layout)
        self.setWindowTitle("Gun Barrel")
        self.setWindowIcon(QIcon("icons/gunb.ico"))

        # Initial plot
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
            print(f"DataFrame:\n{df}")

            # Extract combined distances and grid values
            combined_distances = df['combined_distance'].tolist()
            grid_values = {grid_name: df[grid_name].tolist() for grid_name in valid_grids}
            sorted_grids = sorted(grid_values.keys(), key=lambda grid: min(grid_values[grid]))
            fig = go.Figure()

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
                            fillcolor=grid_color_rgba,
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
            intersection_uwis = [item[0] for item in self.intersections]

            # Filter out invalid TVDs (like inf or NaN)
            valid_intersections = [(dist, tvd, uwi) for dist, tvd, uwi in zip(intersection_distances, intersection_tvds, intersection_uwis) if np.isfinite(tvd)]
            intersection_distances, intersection_tvds, intersection_uwis = zip(*valid_intersections) if valid_intersections else ([], [], [])

            # Print debug information for intersections
            print(f"Intersection Distances: {intersection_distances}")
            print(f"Intersection TVDs: {intersection_tvds}")
            print(f"Intersection UWIs: {intersection_uwis}")

            fig.add_trace(go.Scatter(
                x=intersection_distances,
                y=intersection_tvds,
                mode='markers',
                name='Intersection Points',
                marker=dict(color='black', size=8),
                text=intersection_uwis,  # Add UWI as hover text
                hoverinfo='text'  # Display the hover text
            ))

            # Add annotations for each UWI label
            annotations = []
            for i, uwi in enumerate(intersection_uwis):
                annotations.append(
                    dict(
                        x=intersection_distances[i],
                        y=intersection_tvds[i],
                        text=uwi,
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

            x_axis_title = "Combined Distances"
            fig.update_layout(
                title='Gun Barrel Plot', 
                xaxis_title=x_axis_title,  
                yaxis_title='TVD',
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
    def receiveHoverEvent(self, uwi):
        print(f'Hover event received for UWI: {uwi}')
        self.hoverEvent.emit(uwi)
        self.main_app.handle_hover_event(uwi)

if __name__ == "__main__":
    import sys
    from PySide2.QtWidgets import QApplication

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
