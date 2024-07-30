import sys
import plotly.graph_objs as go
from PySide2.QtGui import QIcon
import plotly.offline as py_offline
from PySide2.QtWidgets import QApplication, QVBoxLayout, QHBoxLayout, QPushButton, QWidget, QComboBox, QDialog, QSizePolicy, QDesktopWidget
from PySide2.QtWebEngineWidgets import QWebEngineView
import pandas as pd

class Plot(QDialog):
    def __init__(self, grid_well_data_df, zone_color_df, total_zone_number, parent=None):
        super().__init__(parent)
        self.main_app = parent
        self.grid_well_data_df = grid_well_data_df
        self.zone_color_df = zone_color_df
        self.total_zone_number = int(total_zone_number)
        self.uwi_list = self.grid_well_data_df['UWI'].unique().tolist()
        self.current_index = 0
        self.init_ui()

        # Set initial size and position
        self.resize(1200, 800)  # Set initial size (width, height)

        # Move to second screen if available
        screen = QDesktopWidget().screenGeometry(1)  # Get geometry of screen 2
        self.move(screen.left(), screen.top())  

    def init_ui(self):
        # Create the dropdown for well selection
        self.well_selector = QComboBox()
        self.well_selector.addItems(self.uwi_list)
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
            print(f"Plotting well at index: {self.current_index}")

            # Extract data for the current well
            current_uwi = self.uwi_list[self.current_index]
            print(f"Current UWI: {current_uwi}")
            current_well_data = self.grid_well_data_df[self.grid_well_data_df['UWI'] == current_uwi]

            if current_well_data.empty:
                print(f"No data found for UWI: {current_uwi}")
                return

            combined_distances = current_well_data['Combined Distance'].tolist()  # Extract combined distances
            tvd_values = current_well_data['TVD'].tolist()  # Extract TVD values

            zone_values = [[] for _ in range(self.total_zone_number + 2)]  # Initialize lists for zones, including top and bottom
            zone_in_values = current_well_data['ZoneIn'].tolist()

            # Extract top, zones, and bottom values
            for i in range(len(current_well_data)):
                zone_values[0].append(current_well_data.iloc[i, 6])  # Top zone
                for j in range(1, self.total_zone_number + 1):
                    zone_values[j].append(current_well_data.iloc[i, 6 + j])
                zone_values[-1].append(current_well_data.iloc[i, -2])  # Bottom zone

            # Plotting the data as lines
            zone_colors_rgb = self.zone_color_df['Zone Color (RGB)'].tolist()
            zone_colors_rgb_str = ', '.join([f"({r}, {g}, {b}, .3)" for r, g, b in zone_colors_rgb])
            print(zone_colors_rgb_str)
            # Create Plotly figure
            fig = go.Figure()

            # Plot and fill zones
            for j in range(self.total_zone_number - 1):
                print(j)
                r, g, b = zone_colors_rgb[j]
                zone_color_rgb = f'{r}, {g}, {b}'
                zone_color_rgba = f'rgba({r}, {g}, {b}, 0.3)'  # Correct indexing
                
                fig.add_trace(go.Scatter(x=combined_distances, y=zone_values[j], mode='lines', name=f'Zone {j}', line=dict(color=f'rgb({zone_color_rgb})')))
                if j > 0:
                    fig.add_trace(go.Scatter(x=combined_distances, y=zone_values[j - 1], fill='tonexty', fillcolor=f'{zone_color_rgba}', mode='none', showlegend=False))

            x_points = []
            y_points = []
            for i in range(len(tvd_values)):
                x_points.append(combined_distances[i])
                y_points.append(tvd_values[i])

            # Add a single trace with lines+markers
            fig.add_trace(go.Scatter(
                x=x_points, 
                y=y_points, 
                mode='lines', 
                line=dict(color='black', width=3),  # Make line bolder
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
            print("Next button clicked")
            self.current_index = (self.current_index + 1) % len(self.uwi_list)
            self.plot_current_well()
        except Exception as e:
            print(f"Error in on_next: {e}")

    def on_prev(self):
        try:
            print("Previous button clicked")
            self.current_index = (self.current_index - 1) % len(self.uwi_list)
            self.plot_current_well()
        except Exception as e:
            print(f"Error in on_prev: {e}")


    def receive_uwi(self):

        uwi = self.uwi_list[self.current_index]
        print(uwi)
        self.main_app.handle_hover_event(uwi)


    def on_well_selected(self, index):
        try:
            print(f"Well selected: {index}")
            self.current_index = index
            self.plot_current_well()
        except Exception as e:
            print(f"Error in on_well_selected: {e}")

if __name__ == '__main__':
    app = QApplication(sys.argv)

    # Sample grid_well_data_df for testing
    data = {
        'UWI': ['well1', 'well1', 'well2', 'well2', 'well3', 'well3'],
        'MD': [0, 0, 0, 0, 0, 0],
        'TVD': [200, 250, 250, 300, 300, 350],
        'X Offset': [0, 0, 0, 0, 0, 0],
        'Y Offset': [0, 0, 0, 0, 0, 0],
        'Combined Distance': [100, 150, 150, 200, 200, 250],
        'Zone 0': [150, 180, 180, 220, 220, 250],
        'Zone 1': [180, 200, 200, 250, 250, 300],
        'ZoneIn': [1, 2, 2, 3, 3, 4],
        'ZoneIn_Name': ['Zone 1', 'Zone 2', 'Zone 2', 'Zone 3', 'Zone 3', 'Zone 4']
    }
    grid_well_data_df = pd.DataFrame(data)

    # Sample zone
