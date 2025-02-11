import sys
import numpy as np
import pandas as pd
import plotly.graph_objs as go
import plotly.offline as py_offline
from sklearn.linear_model import LinearRegression
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                               QComboBox, QCheckBox, QApplication, QFrame)
from PySide6.QtWebEngineWidgets import QWebEngineView


class CrossPlot3D(QDialog):
    def __init__(self, db_manager, parent=None):
        super(CrossPlot3D, self).__init__(parent)
        self.db_manager = db_manager
        self.master_df = None  # Store merged data
        self.init_ui()
        self.load_zone_data()  # Load and process data

    def init_ui(self):
        main_layout = QHBoxLayout(self)

        # Controls layout
        controls_layout = QVBoxLayout()

        # Zone Filter Dropdown
        self.zone_name_label = QLabel("Filter by Zone:")
        self.zone_name_dropdown = QComboBox()
        self.zone_name_dropdown.addItem("All")  # Default to all zones
        self.zone_name_dropdown.currentIndexChanged.connect(self.plot_3d_crossplot)
        controls_layout.addWidget(self.zone_name_label)
        controls_layout.addWidget(self.zone_name_dropdown)

        # X Attribute Dropdown
        self.x_attr_label = QLabel("Select X Attribute:")
        self.x_attr_dropdown = QComboBox()
        controls_layout.addWidget(self.x_attr_label)
        controls_layout.addWidget(self.x_attr_dropdown)

        # Y Attribute Dropdown
        self.y_attr_label = QLabel("Select Y Attribute:")
        self.y_attr_dropdown = QComboBox()
        controls_layout.addWidget(self.y_attr_label)
        controls_layout.addWidget(self.y_attr_dropdown)

        # Z Attribute Dropdown
        self.z_attr_label = QLabel("Select Z Attribute:")
        self.z_attr_dropdown = QComboBox()
        controls_layout.addWidget(self.z_attr_label)
        controls_layout.addWidget(self.z_attr_dropdown)

        # Checkbox to ignore zeros
        self.ignore_zeros_checkbox = QCheckBox("Ignore Zeros")
        self.ignore_zeros_checkbox.setChecked(False)
        controls_layout.addWidget(self.ignore_zeros_checkbox)

        # Checkbox to add regression plane
        self.add_regression_checkbox = QCheckBox("Add Regression Plane")
        self.add_regression_checkbox.setChecked(True)
        controls_layout.addWidget(self.add_regression_checkbox)

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
        self.setWindowTitle("3D CrossPlot Viewer")
        self.resize(1200, 800)

        # Connect attribute dropdowns to plot update
        self.x_attr_dropdown.currentIndexChanged.connect(self.plot_3d_crossplot)
        self.y_attr_dropdown.currentIndexChanged.connect(self.plot_3d_crossplot)
        self.z_attr_dropdown.currentIndexChanged.connect(self.plot_3d_crossplot)
        self.ignore_zeros_checkbox.stateChanged.connect(self.plot_3d_crossplot)
        self.add_regression_checkbox.stateChanged.connect(self.plot_3d_crossplot)

    def load_zone_data(self):
        """Load data for all zones, merge attributes by UWI, and standardize column names."""
        try:
            all_zone_data = []
            well_zones = self.db_manager.fetch_zone_names_by_type("Well")

            for zone_tuple in well_zones:
                zone_name = zone_tuple[0]
                data, columns = self.db_manager.fetch_zone_table_data(zone_name)

                # Convert to DataFrame
                df = pd.DataFrame(data, columns=columns)

                # Standardize UWI column name
                df.rename(columns={col: "UWI" for col in df.columns if col.lower() == "UWI"}, inplace=True)

                # Prefix attributes to avoid conflicts (e.g., Value1 -> ZoneA_Value1)
                df = df.add_prefix(f"{zone_name}_")
                df.rename(columns={f"{zone_name}_UWI": "UWI"}, inplace=True)  # Keep UWI standard
                df["Zone Name"] = zone_name  # Track which zone it came from

                all_zone_data.append(df)

            if all_zone_data:
                # Merge all zones by UWI
                self.master_df = all_zone_data[0]
                for df in all_zone_data[1:]:
                    self.master_df = pd.merge(self.master_df, df, on="UWI", how="outer")

                # Populate attribute dropdowns
                self.populate_attribute_dropdowns()

                # Initial empty plot
                self.plot_3d_crossplot()

        except Exception as e:
            print(f"Error loading zone data: {e}")

    def populate_attribute_dropdowns(self):
        """Populate dropdowns with all attributes but keep them blank initially."""
        try:
            if self.master_df is None or self.master_df.empty:
                return

            # Find numeric attributes
            attributes = self.master_df.select_dtypes(include=['float64', 'int64']).columns.tolist()
            filtered_attributes = [col for col in attributes if col.lower() != "UWI"]

            # Clear dropdowns & keep them blank
            self.x_attr_dropdown.clear()
            self.y_attr_dropdown.clear()
            self.z_attr_dropdown.clear()

            self.x_attr_dropdown.addItem("")  # Empty default option
            self.y_attr_dropdown.addItem("")
            self.z_attr_dropdown.addItem("")
            self.x_attr_dropdown.addItems(sorted(filtered_attributes))
            self.y_attr_dropdown.addItems(sorted(filtered_attributes))
            self.z_attr_dropdown.addItems(sorted(filtered_attributes))

        except Exception as e:
            print(f"Error populating attribute dropdowns: {e}")

    def plot_3d_crossplot(self):
        """Plot the 3D scatter plot with merged UWI data and optional regression plane."""
        try:
            if self.master_df is None or self.master_df.empty:
                print("No data available for plotting.")
                return

            zone_name = self.zone_name_dropdown.currentText()
            x_attr = self.x_attr_dropdown.currentText().strip()
            y_attr = self.y_attr_dropdown.currentText().strip()
            z_attr = self.z_attr_dropdown.currentText().strip()

            if not x_attr or not y_attr or not z_attr:
                print("Select X, Y, and Z attributes before plotting.")
                return

            df = self.master_df.copy()
            if zone_name != "All":
                df = df[df["Zone Name"] == zone_name]

            df = df[['UWI', x_attr, y_attr, z_attr]].replace([np.inf, -np.inf], np.nan).dropna()
            if self.ignore_zeros_checkbox.isChecked():
                df = df[(df[x_attr] != 0) & (df[y_attr] != 0) & (df[z_attr] != 0)]

            if df.empty:
                print("No valid data available for plotting.")
                return

            fig = go.Figure()
            fig.add_trace(go.Scatter3d(
                x=df[x_attr],
                y=df[y_attr],
                z=df[z_attr],
                mode='markers',
                text=df["UWI"],
                name="All Data",
                hoverinfo='text',
                marker=dict(size=5, opacity=0.8)
            ))

            # Add regression plane if enabled
            if self.add_regression_checkbox.isChecked():
                try:
                    # Extract data for regression
                    X = df[[x_attr, y_attr]].values
                    y = df[z_attr].values

                    if X.shape[1] != 2:
                        print(f"Regression Error: Expected 2 features in X, got {X.shape[1]}")
                        return

                    # Fit Linear Regression
                    model = LinearRegression()
                    model.fit(X, y)

                    # Generate mesh grid
                    x_range = np.linspace(df[x_attr].min(), df[x_attr].max(), 30)
                    y_range = np.linspace(df[y_attr].min(), df[y_attr].max(), 30)
                    xx, yy = np.meshgrid(x_range, y_range)

                    # Predict Z values
                    z_pred = model.predict(np.column_stack([xx.ravel(), yy.ravel()])).reshape(xx.shape)

                    # Add regression plane
                    fig.add_trace(go.Surface(
                        x=x_range, y=y_range, z=z_pred,
                        name='Regression Plane', colorscale='Viridis', opacity=0.5, showscale=False
                    ))

                except Exception as e:
                    print(f"Error adding regression plane: {e}")

            fig.update_layout(title="3D CrossPlot", template='plotly_dark')
            html_content = py_offline.plot(fig, include_plotlyjs='cdn', output_type='div')
            self.plot_widget.setHtml(html_content)

        except Exception as e:
            print(f"Error plotting 3D crossplot: {e}")

