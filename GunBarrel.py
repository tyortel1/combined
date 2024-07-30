import pandas as pd
from PySide2.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QSizePolicy
from PySide2.QtCore import Qt, QPointF, QTimer, Signal, Slot
from PySide2.QtWebEngineWidgets import QWebEngineView
from PySide2.QtWebChannel import QWebChannel  
from PySide2.QtGui import QIcon
import plotly.graph_objects as go
import plotly.offline as py_offline
import numpy as np
from scipy.spatial import KDTree

class PlotGB(QDialog):
    hoverEvent = Signal(str)
    def __init__(self, grid_xyz_top, grid_xyz_bottom, currentLine, total_zone_number, zone_color_df, intersections=None, main_app=None,  parent=None):
        super(PlotGB, self).__init__(parent)
        self.main_app = main_app
        self.grid_xyz_top = grid_xyz_top
        self.grid_xyz_bottom = grid_xyz_bottom
        self.current_line = currentLine
        self.total_zone_number = total_zone_number
        self.intersections = intersections or []
        self.zone_color_df = zone_color_df
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
            print(line_coords)
            # Create KD-Trees for top and bottom grids
            kdtree_top = KDTree([(point[1], point[0]) for point in self.grid_xyz_top]) if self.grid_xyz_top else None
            kdtree_bottom = KDTree([(point[1], point[0]) for point in self.grid_xyz_bottom]) if self.grid_xyz_bottom else None


            # Generate intermediate points along the line
            num_samples = 100  # Number of points to sample along the line
            sampled_line_coords = self.sample_points_along_line(line_coords, num_samples)

            gun_barrel_data = []
            combined_distance = 0

            for i, (x, y) in enumerate(sampled_line_coords):
                closest_z_top = 0
                closest_z_bottom = 0
                closest_z_top = self.grid_xyz_top[kdtree_top.query((x, y))[1]][2] if kdtree_top and kdtree_top.data.size > 0 else 0
                closest_z_bottom = self.grid_xyz_bottom[kdtree_bottom.query((x, y))[1]][2]  if kdtree_bottom and kdtree_bottom.data.size > 0 else 0
                if closest_z_bottom > 1000000:
                    closest_z_bottom = 0
                zones = self.calculate_zones(closest_z_top, closest_z_bottom, self.total_zone_number)

                if i > 0:
                    prev_x, prev_y = sampled_line_coords[i - 1]
                    combined_distance += np.sqrt((x - prev_x) ** 2 + (y - prev_y) ** 2)
                    print(combined_distance)
                else:
                    combined_distance = 0  # First point has distance 0

                entry = [x, y, combined_distance, closest_z_top] + zones + [closest_z_bottom]
                gun_barrel_data.append(entry)
            print(gun_barrel_data)
            # Determine the number of zones from the data
            num_columns = len(gun_barrel_data[0])
            num_zones = self.total_zone_number - 3

            # Define column names
            columns = ['x', 'y', 'combined_distance', 'closest_z_top'] + [f'zone_{i}' for i in range(1, num_zones + 1)] + ['closest_z_bottom']

            # Create DataFrame with defined columns
            df = pd.DataFrame(gun_barrel_data, columns=columns)
            pd.set_option('display.max_columns', None)
            pd.set_option('display.width', None)
            print(df)

            # Extract combined distances and zone values with x and y
            combined_distances = df['combined_distance'].tolist()
            zone_values = [[] for _ in range(self.total_zone_number-1)]

            # Populate zone_values from DataFrame
            for i, row in df.iterrows():
                x = round(row['x'], 1)
                y = round(row['y'], 1)
                cum = row['combined_distance']
                for j in range(self.total_zone_number-1):  # Use total_zone_number for zones
                    zone_values[j].append((x, y, cum, row[3 + j]))  

            print(zone_values)  # For debugging, to ensure values are correctly extracted

            fig = go.Figure()

            # Plot and fill zones
            for j in range(self.total_zone_number-1):
                r, g, b = self.zone_color_df.iloc[j]['Zone Color (RGB)']
                zone_color_rgb = f'{r}, {g}, {b}'
                zone_color_rgba = f'rgba({r}, {g}, {b}, 0.3)'

                fig.add_trace(go.Scatter(
                    x=[val[2] for val in zone_values[j]],  # cumulative distances
                    y=[val[3] for val in zone_values[j]],  # zone values
                    mode='lines',
                    name=f'Zone {j + 1}',  # Zone numbering starting from 1
                    line=dict(color=f'rgb({zone_color_rgb})')
                ))

                # Only fill if there is a next zone to fill to
                if j > 0:
                    previous_z_zone = [val[3] for val in zone_values[j - 1]]
                    fig.add_trace(go.Scatter(
                        x=[val[2] for val in zone_values[j]], 
                        y=previous_z_zone, 
                        fill='tonexty', 
                        fillcolor=f'{zone_color_rgba}', 
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

    def calculate_zones(self, closest_z_top, closest_z_bottom, number_of_zones):
        if closest_z_top is not None and closest_z_bottom is not None and number_of_zones > 2:
            zone_interval = (closest_z_bottom - closest_z_top) / (number_of_zones - 2)
            zones = [closest_z_top + i * zone_interval for i in range(1, number_of_zones - 2)]
        else:
            zones = [closest_z_top, closest_z_bottom]
        return zones

    def calculate_cumulative_distance(self, inter_x, inter_y, line_coords, combined_distances):
        # Find the closest line segment and interpolate the cumulative distance
        min_distance = float('inf')
        cumulative_distance = 0
        for i in range(1, len(line_coords)):
            x1, y1 = line_coords[i - 1]
            x2, y2 = line_coords[i]
            # Calculate the perpendicular distance to the line segment
            distance, t = self.point_to_line_segment_distance(inter_x, inter_y, x1, y1, x2, y2)
            if distance < min_distance:
                min_distance = distance
                segment_distance = combined_distances[i - 1] + t * (combined_distances[i] - combined_distances[i - 1])
                cumulative_distance = segment_distance
        return cumulative_distance

    def point_to_line_segment_distance(self, px, py, x1, y1, x2, y2):
        # Calculate the perpendicular distance from point (px, py) to the line segment (x1, y1) - (x2, y2)
        dx, dy = x2 - x1, y2 - y1
        if dx == dy == 0:  # the segment is a point
            return np.hypot(px - x1, py - y1), 0
        t = ((px - x1) * dx + (py - y1) * dy) / (dx * dx + dy * dy)
        if t < 0:
            distance = np.hypot(px - x1, py - y1)
            t = 0
        elif t > 1:
            distance = np.hypot(px - x2, py - y2)
            t = 1
        else:
            nearest_x = x1 + t * dx
            nearest_y = y1 + t * dy
            distance = np.hypot(px - nearest_x, py - nearest_y)
        return distance, t

    @Slot(str)
    def receiveHoverEvent(self, uwi):
        print(f'Hover event received for UWI: {uwi}')
        self.hoverEvent.emit(uwi)
        self.main_app.handle_hover_event(uwi)


    def on_hover_timeout(self):
        if self.current_hover_uwi:
            print(f'Hovering over UWI: {self.current_hover_uwi}')
            self.hover_timer.stop()
            self.current_hover_uwi = None
# Example usage


if __name__ == "__main__":
    import sys
    from PySide2.QtWidgets import QApplication

    app = QApplication(sys.argv)

    # Example data
    grid_xyz_top = [(1, 1, 10), (2, 2, 20), (3, 3, 30)]
    grid_xyz_bottom = [(1, 1, 5), (2, 2, 15), (3, 3, 25)]
    currentLine = [QPointF(0, 0), QPointF(1, 1), QPointF(2, 2)]
    total_zone_number = 4
    zone_color_df = pd.DataFrame({
        'Zone Color (RGB)': [(255, 0, 0), (0, 255, 0), (0, 0, 255)]
    })
    intersections = [
        ('UWI1', 1, 1, 10, 0),
        ('UWI2', 2, 2, 20, 1),
        ('UWI3', 3, 3, 30, 2)
    ]

    plot_gb = PlotGB(grid_xyz_top, grid_xyz_bottom, currentLine, total_zone_number, zone_color_df, intersections)
    plot_gb.show()

    sys.exit(app.exec_())
