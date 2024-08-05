import sys
import plotly.graph_objs as go
from PySide2.QtGui import QIcon
import plotly.offline as py_offline
from PySide2.QtWidgets import QApplication, QVBoxLayout, QHBoxLayout, QPushButton, QComboBox, QDialog, QSizePolicy, QDesktopWidget
from PySide2.QtWebEngineWidgets import QWebEngineView
import pandas as pd
import numpy as np
from scipy.spatial import KDTree
from PySide2.QtCore import Signal

class Plot(QDialog):
    closed = Signal()
    def __init__(self, uwi_list, directional_surveys_df, depth_grid_data_df, grid_info_df, kd_tree_depth_grids, current_uwi, depth_grid_data_dict, parent=None):
        super().__init__(parent)
        self.main_app = parent
        self.uwi_list = uwi_list
        self.directional_surveys_df = directional_surveys_df
        self.depth_grid_data_df = depth_grid_data_df
        print(self.depth_grid_data_df)
        self.grid_info_df = grid_info_df
        self.kd_tree_depth_grids = kd_tree_depth_grids
        self.current_index = self.uwi_list.index(current_uwi)
        self.depth_grid_data_dict = depth_grid_data_dict
        self.init_ui()
        
        # Set initial size and position
        self.resize(1200, 800)  # Set initial size (width, height)

        # Move to second screen if available
        if QDesktopWidget().screenCount() > 1:
            screen = QDesktopWidget().screenGeometry(1)  # Get geometry of screen 2
            self.move(screen.left(), screen.top())  


    def closeEvent(self, event):
        self.closed.emit()
        event.accept()

    def init_ui(self):
        # Create the dropdown for well selection
        self.well_selector = QComboBox()
        self.well_selector.addItems(self.uwi_list)
        self.well_selector.setCurrentIndex(self.current_index)
        self.well_selector.currentIndexChanged.connect(self.on_well_selected)

        # Create navigation buttons
        self.next_button = QPushButton('Next')
        self.prev_button = QPushButton('Previous')
        self.next_button.clicked.connect(self.on_next)
        self.prev_button.clicked.connect(self.on_prev)

        # Layout for well selector
        well_selector_layout = QVBoxLayout()
        well_selector_layout.addWidget(self.well_selector)

        # Layout for Previous and Next buttons side by side
        nav_buttons_layout = QHBoxLayout()
        nav_buttons_layout.addWidget(self.prev_button)
        nav_buttons_layout.addWidget(self.next_button)

        # Layout for controls (well selector and navigation buttons)
        control_layout = QVBoxLayout()
        control_layout.addLayout(well_selector_layout)
        control_layout.addLayout(nav_buttons_layout)
        control_layout.addStretch()  # Add stretch at the bottom to push controls to the top

        # Create the plot layout
        self.plot_widget = QWebEngineView()
        self.plot_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.plot_layout = QVBoxLayout()
        self.plot_layout.addWidget(self.plot_widget)

        # Main layout
        main_layout = QHBoxLayout()
        main_layout.addLayout(control_layout)
        main_layout.addLayout(self.plot_layout)
        self.setLayout(main_layout)
        self.setWindowTitle("Zone Viewer")

        self.setWindowIcon(QIcon("icons/ZoneAnalyzer.png"))
        # Initial plot
        self.plot_current_well()

    def plot_current_well(self):
        try:
            # Extract data for the current well
            current_uwi = self.uwi_list[self.current_index]
            current_well_data = self.directional_surveys_df[self.directional_surveys_df['UWI'] == current_uwi]
            current_well_data = current_well_data.reset_index(drop=True)
            
            if current_well_data.empty:
                print(f"No data found for UWI: {current_uwi}")
                return

            combined_distances = current_well_data['Cumulative Distance'].tolist()  # Extract combined distances
            tvd_values = current_well_data['TVD'].tolist()  # Extract TVD values

            if len(combined_distances) != len(current_well_data):
                print(f"Warning: Length mismatch between combined distances and well data for UWI: {current_uwi}")

            uwi_grid_data = []
            print('first')

            for i, row in current_well_data.iterrows():
                x = row['X Offset']
                y = row['Y Offset']

                # Initialize a dictionary to store the closest Z values for each grid
                closest_z_values = {grid: None for grid in self.kd_tree_depth_grids.keys()}

                # Query each KD-Tree to find the closest Z value for each grid
                for grid, kdtree in self.kd_tree_depth_grids.items():
                    if kdtree.data.size > 0:
                        distances, indices = kdtree.query((x, y))
                        if indices < len(self.depth_grid_data_dict[grid]):
                            closest_z_values[grid] = self.depth_grid_data_dict[grid][indices]

                # Prepare the entry data for the DataFrame
                entry = [x, y, combined_distances[i]] + [closest_z_values[grid] for grid in self.kd_tree_depth_grids.keys()]
                uwi_grid_data.append(entry)

            # Define valid grids present in both depth_grid_data_df and grid_info_df
            valid_grids = [grid for grid in self.kd_tree_depth_grids.keys() if grid in set(self.grid_info_df['Grid']) & set(self.depth_grid_data_df['Grid'])]
            print(valid_grids)
            columns = ['x', 'y', 'combined_distance'] + valid_grids

            # Check if the length of each entry matches the length of columns
            if all(len(entry) == len(columns) for entry in uwi_grid_data):
                # Create DataFrame with the defined columns
                df = pd.DataFrame(uwi_grid_data, columns=columns)
                print(df)
            else:
                print("Error: Length of entries in uwi_grid_data does not match the length of columns")
                return

            pd.set_option('display.max_columns', None)
            pd.set_option('display.width', None)

            if df.empty:
                print(f"No data to plot for UWI: {current_uwi}")
                return

            # Extract combined distances and grid values
            combined_distances = df['combined_distance'].tolist()
            grid_values = {grid_name: df[grid_name].tolist() for grid_name in valid_grids}
            print(grid_values)
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


            # Plot well path as black lines
            fig.add_trace(go.Scatter(
                x=combined_distances,
                y=tvd_values,
                mode='lines',
                line=dict(color='black', width=3),
                showlegend=False
            ))

            fig.update_layout(title=f'Well {current_uwi} TVD vs Combined Distances', xaxis_title='Combined Distances (X and Y)', yaxis_title='TVD')

            # Render Plotly figure as HTML and display it in the QWebEngineView
            html_content = py_offline.plot(fig, include_plotlyjs='cdn', output_type='div')
            
            self.plot_widget.setHtml(html_content)
            self.receive_uwi()

        except Exception as e:
            print(f"Error plotting well: {e}")

    def on_next(self):
        try:
            self.current_index = (self.current_index + 1) % len(self.uwi_list)
            self.plot_current_well()
        except Exception as e:
            print(f"Error in on_next: {e}")

    def on_prev(self):
        try:
            self.current_index = (self.current_index - 1) % len(self.uwi_list)
            self.plot_current_well()
        except Exception as e:
            print(f"Error in on_prev: {e}")

    def update_plot(self, grid_info_df):
        self.grid_info_df = grid_info_df
        self.plot_current_well()
    def receive_uwi(self):
        uwi = self.uwi_list[self.current_index]
        self.main_app.handle_hover_event(uwi)

    def on_well_selected(self, index):
        try:
            self.current_index = index
            self.plot_current_well()
        except Exception as e:
            print(f"Error in on_well_selected: {e}")

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
