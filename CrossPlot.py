import sys
import numpy as np
from PySide2.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QCheckBox, QApplication, QWidget, QFrame
from PySide2.QtCore import Qt
import plotly.graph_objs as go
import plotly.offline as py_offline
import pandas as pd
from PySide2.QtWebEngineWidgets import QWebEngineView
from sklearn.linear_model import LinearRegression

class CrossPlot(QDialog):
    def __init__(self, master_df, parent=None):
        super(CrossPlot, self).__init__(parent)
        self.master_df = master_df
        self.init_ui()

    def init_ui(self):
        main_layout = QHBoxLayout(self)

        # Controls layout
        controls_layout = QVBoxLayout()

        # Zone Name Dropdown
        self.zone_name_label = QLabel("Select Zone Name:")
        self.zone_name_dropdown = QComboBox()
        self.zone_name_dropdown.addItem("All")
        zone_names = self.master_df['Zone Name'].dropna().unique()
        self.zone_name_dropdown.addItems(sorted(zone_names))
        self.zone_name_dropdown.currentIndexChanged.connect(self.update_attribute_dropdowns)
        controls_layout.addWidget(self.zone_name_label)
        controls_layout.addWidget(self.zone_name_dropdown)

        # First Attribute Dropdown
        self.first_attribute_label = QLabel("Select First Attribute:")
        self.x_attr_dropdown = QComboBox()
        controls_layout.addWidget(self.first_attribute_label)
        controls_layout.addWidget(self.x_attr_dropdown)

        # Second Attribute Dropdown
        self.second_attribute_label = QLabel("Select Second Attribute:")
        self.y_attr_dropdown = QComboBox()
        controls_layout.addWidget(self.second_attribute_label)
        controls_layout.addWidget(self.y_attr_dropdown)

        # Checkbox to ignore zeros
        self.ignore_zeros_checkbox = QCheckBox("Ignore Zeros")
        self.ignore_zeros_checkbox.setChecked(False)
        controls_layout.addWidget(self.ignore_zeros_checkbox)

        # Checkbox to add trendline
        self.add_trendline_checkbox = QCheckBox("Add Trendline")
        self.add_trendline_checkbox.setChecked(True)
        controls_layout.addWidget(self.add_trendline_checkbox)

        # Add a stretch to push all elements to the top
        controls_layout.addStretch()

        # Add the controls layout to the main layout on the left
        left_controls_frame = QFrame()
        left_controls_frame.setLayout(controls_layout)
        main_layout.addWidget(left_controls_frame, stretch=1)

        # Plot area on the right
        self.plot_widget = QWebEngineView()
        main_layout.addWidget(self.plot_widget, stretch=5)

        # Set window properties
        self.setWindowTitle("CrossPlot Viewer")
        self.resize(1200, 800)

        # Initial update of attribute dropdowns
        self.update_attribute_dropdowns()

        # Trigger initial plot
        self.plot_crossplot()

        # Connect attribute dropdowns to plot update
        self.x_attr_dropdown.currentIndexChanged.connect(self.plot_crossplot)
        self.y_attr_dropdown.currentIndexChanged.connect(self.plot_crossplot)
        self.ignore_zeros_checkbox.stateChanged.connect(self.plot_crossplot)
        self.add_trendline_checkbox.stateChanged.connect(self.plot_crossplot)

    def update_attribute_dropdowns(self):
        try:
            zone_name = self.zone_name_dropdown.currentText()

            if zone_name == "All":
                df = self.master_df
            else:
                df = self.master_df[self.master_df['Zone Name'] == zone_name]

            attributes = df.select_dtypes(include=['float64', 'int64']).columns

            self.x_attr_dropdown.clear()
            self.y_attr_dropdown.clear()

            self.x_attr_dropdown.addItems(sorted(attributes))
            self.y_attr_dropdown.addItems(sorted(attributes))
        except Exception as e:
            print(f"Error updating attribute dropdowns: {e}")

    def plot_crossplot(self):
        try:
            zone_name = self.zone_name_dropdown.currentText()
            x_attr = self.x_attr_dropdown.currentText()
            y_attr = self.y_attr_dropdown.currentText()
            ignore_zeros = self.ignore_zeros_checkbox.isChecked()
            add_trendline = self.add_trendline_checkbox.isChecked()

            if not x_attr or not y_attr:
                return  # Do nothing if attributes are not selected

            # Filter the DataFrame based on the selected zone
            if zone_name == "All":
                df = self.master_df
            else:
                df = self.master_df[self.master_df['Zone Name'] == zone_name]

            # Handle NaN, inf, and zero values
            df = df[[x_attr, y_attr, 'UWI']].replace([np.inf, -np.inf], np.nan).dropna()
            if ignore_zeros:
                df = df[(df[x_attr] != 0) & (df[y_attr] != 0)]

            if df.empty:
                print("No valid data available for plotting.")
                return

            # Initialize Plotly figure
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=df[x_attr],
                y=df[y_attr],
                mode='markers',
                text=df['UWI'],
                hoverinfo='text',
            ))

            # Add a trendline if requested
            if add_trendline:
                x_values = df[x_attr].values.reshape(-1, 1)
                y_values = df[y_attr].values
                model = LinearRegression().fit(x_values, y_values)
                trendline = model.predict(x_values)
                fig.add_trace(go.Scatter(
                    x=df[x_attr],
                    y=trendline,
                    mode='lines',
                    name='Trendline',
                    line=dict(color='red', dash='dash')
                ))

            # Update layout
            fig.update_layout(
                title=f'{x_attr} vs {y_attr}',
                xaxis_title=x_attr,
                yaxis_title=y_attr,
                template='plotly_dark'
            )

            # Display the plot
            html_content = py_offline.plot(fig, include_plotlyjs='cdn', output_type='div')
            self.plot_widget.setHtml(html_content)

        except Exception as e:
            print(f"Error plotting crossplot: {e}")


if __name__ == "__main__":
    app = QApplication(sys.argv)

    # Sample DataFrame
    data = {
        'UWI': ['well1', 'well2', 'well3', 'well4'],
        'Zone Name': ['Zone A', 'Zone B', 'Zone A', 'Zone C'],
        'Attribute 1': [10, 20, 30, 40],
        'Attribute 2': [5, 15, 25, 35],
        'Attribute 3': [7, 14, 21, 28]
    }
    master_df = pd.DataFrame(data)

    dialog = CrossPlot(master_df)
    dialog.exec_()

    sys.exit(app.exec_())
