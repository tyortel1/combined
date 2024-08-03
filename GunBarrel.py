import pandas as pd
from PySide2.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QSizePolicy
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

    def __init__(self, depth_grid_data_df, depth_grid_color_df, currentLine, intersections=None, main_app=None, parent=None):
        super(PlotGB, self).__init__(parent)
        self.main_app = main_app
        self.depth_grid_data_df = depth_grid_data_df
        self.depth_grid_color_df = depth_grid_color_df
        self.current_line = currentLine
        self.intersections = intersections or []
        self.setWindowTitle("Gun Barrel Plot")
        self.setGeometry(100, 100, 1200, 800)
        self.setupUi()

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
            print(f"Line coordinates: {line_coords}")

            # Generate intermediate points along the line
            num_samples = 200  # Number of points to sample along the line
            sampled_line_coords = self.sample_points_along_line(line_coords, num_samples)

            gun_barrel_data = []
            combined_distance = 0

            # Create KD-Trees for each grid
            kdtrees = {grid: KDTree(self.depth_grid_data_df[self.depth_grid_data_df['Grid'] == grid][['X', 'Y']].values) for grid in self.depth_grid_data_df['Grid'].unique()}

            for i, (x, y) in enumerate(sampled_line_coords):
                # Initialize closest Z values for each grid
                closest_z_values = {grid: 0 for grid in kdtrees}

                # Query each KD-Tree
                for grid, kdtree in kdtrees.items():
                    if kdtree.data.size > 0:
                        distances, indices = kdtree.query((x, y))
                        if indices < len(self.depth_grid_data_df):
                            closest_z_values[grid] = self.depth_grid_data_df[self.depth_grid_data_df['Grid'] == grid].iloc[indices]['Z']

                # Calculate the combined distance
                if i > 0:
                    prev_x, prev_y = sampled_line_coords[i - 1]
                    combined_distance += np.sqrt((x - prev_x) ** 2 + (y - prev_y) ** 2)
                    print(combined_distance)
                else:
                    combined_distance = 0  # First point has distance 0

                # Prepare the entry data
                entry = [x, y, combined_distance] + [closest_z_values[grid] for grid in kdtrees]
                gun_barrel_data.append(entry)
            print(gun_barrel_data)
            
            # Define column names
            columns = ['x', 'y', 'combined_distance'] + list(self.depth_grid_color_df['Depth Grid Name'])

            # Create DataFrame with defined columns
            df = pd.DataFrame(gun_barrel_data, columns=columns)
            pd.set_option('display.max_columns', None)
            pd.set_option('display.width', None)
            print(f"DataFrame:\n{df}")

            # Extract combined distances and grid values
            combined_distances = df['combined_distance'].tolist()
            grid_values = {grid_name: df[grid_name].tolist() for grid_name in self.depth_grid_color_df['Depth Grid Name']}

            fig = go.Figure()

            # Plot and fill grids
            for grid_name in self.depth_grid_color_df['Depth Grid Name']:
                r, g, b = self.depth_grid_color_df.loc[self.depth_grid_color_df['Depth Grid Name'] == grid_name, 'Color (RGB)'].values[0]
                grid_color_rgb = f'{r}, {g}, {b}'
                grid_color_rgba = f'rgba({r}, {g}, {b}, 0.3)'

                fig.add_trace(go.Scatter(
                    x=combined_distances,
                    y=grid_values[grid_name],
                    mode='lines',
                    name=grid_name,
                    line=dict(color=f'rgb({grid_color_rgb})')
                ))

                # Only fill if there is a next grid to fill to
                if grid_name != self.depth_grid_color_df['Depth Grid Name'].iloc[0]:
                    previous_grid_name = self.depth_grid_color_df['Depth Grid Name'].iloc[self.depth_grid_color_df['Depth Grid Name'].tolist().index(grid_name) - 1]
                    previous_grid_values = grid_values[previous_grid_name]
                    fig.add_trace(go.Scatter(
                        x=combined_distances, 
                        y=previous_grid_values, 
                        fill='tonexty', 
                        fillcolor=f'{grid_color_rgba}', 
                        mode='none', 
                        showlegend=False
                    ))

            # Plot intersection points as black dots
            intersection_distances = [item[4] for item in self.intersections]
            intersection_tvds = [item[3] for item in self.intersections]
            intersection_uwis = [item[0] for item in self.intersections] 
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
                        yanchor='bottom'
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

    app = QApplication(sys.argv)
    window = PlotGB(depth_grid_data_df, depth_grid_color_df, currentLine, intersections)
    window.show()
    sys.exit(app.exec_())
