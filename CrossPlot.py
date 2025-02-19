import sys
from typing import Self
import numpy as np
import pandas as pd
import plotly.graph_objs as go
import plotly.offline as py_offline
from sklearn.linear_model import LinearRegression
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                              QCheckBox, QApplication, QFrame, QFormLayout)
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtGui import QColor
from PySide6.QtCore import Qt
from StyledDropdown import DarkStyledDropdown


class CrossPlot3D(QDialog):
    # Dark mode color constants
    DARK_BG = "#1e1e1e"
    DARK_WIDGET_BG = "#2d2d2d"
    DARK_BORDER = "#3d3d3d"
    DARK_TEXT = "#ffffff"
    DARK_ACCENT = "#0f84d8"
    DARK_DISABLED = "#404040"

    def __init__(self, db_manager, parent=None):
        super(CrossPlot3D, self).__init__(parent)
        self.db_manager = db_manager
        self.master_df = None  # Store merged data
        self.filtered_attributes = []
        
        # Apply dark mode styling to the entire window
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {self.DARK_BG};
                color: {self.DARK_TEXT};
            }}
            QLabel {{
                color: {self.DARK_TEXT};
            }}
            QCheckBox {{
                color: {self.DARK_TEXT};
            }}
            QCheckBox::indicator {{
                width: 18px;
                height: 18px;
                border: 1px solid {self.DARK_BORDER};
                border-radius: 4px;
                background-color: {self.DARK_WIDGET_BG};
            }}
            QCheckBox::indicator:checked {{
                background-color: {self.DARK_ACCENT};
                image: url(path/to/checkmark/icon) /* You may want to add a white checkmark image */
            }}
            QFrame {{
                background-color: {self.DARK_BG};
                border: 1px solid {self.DARK_BORDER};
                border-radius: 4px;
            }}
        """)
        
        self.setWindowFlags(self.windowFlags() | Qt.WindowMinMaxButtonsHint)
        self.init_ui()
        self.load_zone_data()
        self.populate_attribute_dropdowns()# Load and process data

    def init_ui(self):
        main_layout = QHBoxLayout(self)

        # Controls layout
        controls_layout = QVBoxLayout()
        controls_layout.setSpacing(10)
        controls_layout.setContentsMargins(10, 10, 10, 10)

        # Calculate label width for all dropdowns
        labels = ["Filter by Zone", "X Attribute", "Y Attribute", "Z Attribute"]
        DarkStyledDropdown.calculate_label_width(labels)

        # Create form layout for aligned inputs
        form_layout = QFormLayout()
        form_layout.setSpacing(10)


        # Create Zone Name Dropdown (Consistent with Others)
        self.zone_name_dropdown = DarkStyledDropdown("Filter by Zone")
        form_layout.addRow(self.zone_name_dropdown.label, self.zone_name_dropdown.combo)

        # Clear and add default value
        self.zone_name_dropdown.combo.clear()
        self.zone_name_dropdown.combo.addItem("All")

        # X Attribute Dropdown
        self.x_attr_dropdown = DarkStyledDropdown("X Attribute")
        form_layout.addRow(self.x_attr_dropdown.label, self.x_attr_dropdown.combo)

        # Y Attribute Dropdown
        self.y_attr_dropdown = DarkStyledDropdown("Y Attribute")
        form_layout.addRow(self.y_attr_dropdown.label, self.y_attr_dropdown.combo)

        # Z Attribute Dropdown
        self.z_attr_dropdown = DarkStyledDropdown("Z Attribute")
        form_layout.addRow(self.z_attr_dropdown.label, self.z_attr_dropdown.combo)

        controls_layout.addLayout(form_layout)

        # Add some spacing before checkboxes
        controls_layout.addSpacing(10)

        # Checkbox layout
        checkbox_layout = QVBoxLayout()
        checkbox_layout.setSpacing(5)

        # Checkbox to ignore zeros
        self.ignore_zeros_checkbox = QCheckBox("Ignore Zeros")
        self.ignore_zeros_checkbox.setChecked(False)
        checkbox_layout.addWidget(self.ignore_zeros_checkbox)

        # Checkbox to add regression plane
        self.add_regression_checkbox = QCheckBox("Add Regression Plane")
        self.add_regression_checkbox.setChecked(True)
        checkbox_layout.addWidget(self.add_regression_checkbox)

        controls_layout.addLayout(checkbox_layout)

        # Add a stretch to push all elements to the top
        controls_layout.addStretch()

        # Add the controls layout to the main layout on the left
        left_controls_frame = QFrame()
        left_controls_frame.setLayout(controls_layout)
        main_layout.addWidget(left_controls_frame, stretch=1)

        # Plot area on the right
        self.plot_widget = QWebEngineView()
        self.plot_widget.setStyleSheet(f"""
            QWebEngineView {{
                background-color: {self.DARK_BG} !important;
                border: none;
                border-radius: 4px;
            }}
        """)

        # Ensure the page itself starts with a dark background
        self.plot_widget.page().setBackgroundColor(QColor(self.DARK_BG))

        # Set initial dark background HTML
        initial_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ 
                    background-color: {self.DARK_BG}; 
                    margin: 0; 
                    padding: 0; 
                    display: flex; 
                    justify-content: center; 
                    align-items: center; 
                    height: 100vh; 
                    color: white; 
                    font-family: Arial, sans-serif; 
                }}
                .message {{ 
                    text-align: center; 
                    opacity: 0.7; 
                    }}
                </style>
            </head>
            <body>
                <div class="message">
                    <p>Select X, Y, and Z attributes to generate a 3D CrossPlot</p>
                </div>
            </body>
            </html>
            """
        self.plot_widget.setHtml(initial_html)
        main_layout.addWidget(self.plot_widget, stretch=5)

        # Set window properties
        self.setWindowTitle("3D CrossPlot Viewer")
        self.resize(1200, 800)

        # Connect attribute dropdowns to plot update
        self.zone_name_dropdown.combo.currentIndexChanged.connect(self.on_zone_changed)
        self.x_attr_dropdown.combo.currentIndexChanged.connect(self.plot_3d_crossplot)
        self.y_attr_dropdown.combo.currentIndexChanged.connect(self.plot_3d_crossplot)
        self.z_attr_dropdown.combo.currentIndexChanged.connect(self.plot_3d_crossplot)
        self.ignore_zeros_checkbox.stateChanged.connect(self.plot_3d_crossplot)
        self.add_regression_checkbox.stateChanged.connect(self.plot_3d_crossplot)


    def on_zone_changed(self):
        """Handle zone selection change and update attribute dropdowns"""
        zone_name = self.zone_name_dropdown.combo.currentText()
        self.update_attribute_dropdowns(zone_name) 



    def update_attribute_dropdowns(self, zone_name=None):
        
            
            if zone_name and zone_name != "All":
                self.filtered_attributes = [col for col in self.filtered_attributes if col.startswith(f"{zone_name}_")]
                print(f"Found {len(self.filtered_attributes)} columns for zone {zone_name}")
            else:
                self.filtered_attributes = list(self.iltered_attributes)
                print(f"Found {len(self.filtered_attributes)} numeric columns for all zones")
            # Clear and populate each dropdown
            for dropdown in [self.x_attr_dropdown, self.y_attr_dropdown, self.z_attr_dropdown]:
                dropdown.combo.clear()
                dropdown.combo.addItem("")  # Empty default option
                for attr in sorted(self.filtered_attributes):
                    dropdown.combo.addItem(attr)
                
            print("Available attributes:", ", ".join(self.filtered_attributes))



    def populate_attribute_dropdowns(self):
        """Populate dropdowns with all attributes but keep them blank initially."""
        try:
            if self.master_df is None or self.master_df.empty:
                print("No data available for populating dropdowns")
                return

            # Find numeric columns
            numeric_cols = self.master_df.select_dtypes(include=['float64', 'int64']).columns
            self.filtered_attributes = [col for col in numeric_cols 
                                 if col.lower() != "uwi" and col != "Zone Name"]
        
            print("\nPopulating attribute dropdowns:")
            print(f"Found {len(self.filtered_attributes)} numeric attributes")
        
            # Clear and populate each dropdown
            for dropdown in [self.x_attr_dropdown, self.y_attr_dropdown, self.z_attr_dropdown]:
                dropdown.combo.clear()
                dropdown.combo.addItem("")  # Empty default option
                for attr in sorted(self.filtered_attributes):
                    dropdown.combo.addItem(attr)
                
            print("Available attributes:", ", ".join(self.filtered_attributes))

        except Exception as e:
            print(f"Error populating attribute dropdowns: {e}")
            import traceback
            traceback.print_exc()

    def update_attribute_dropdowns(self, zone_name=None):
        print("""Update attribute dropdowns based on selected zone.""")
        try:
            if self.master_df is None or self.master_df.empty:
                print("No data available for populating dropdowns")
                return

            df = self.master_df.copy()

            # Find numeric columns correctly
            if zone_name and zone_name != "All":
                zone_columns = [col for col in df.columns if col.startswith(f"{zone_name}_")]
            else:
                zone_columns = df.select_dtypes(include=['float64', 'int64']).columns

            # Filter out 'UWI' and 'Zone Name'
            filtered_attributes = [col for col in zone_columns if col.lower() != "uwi" and col != "Zone Name"]
        
            print(f"\nUpdating dropdowns for zone: {zone_name if zone_name else 'All'}")
            print(f"Found {len(filtered_attributes)} available attributes: {filtered_attributes}")

            # Block signals before modifying dropdowns
            self.x_attr_dropdown.combo.blockSignals(True)
            self.y_attr_dropdown.combo.blockSignals(True)
            self.z_attr_dropdown.combo.blockSignals(True)

            # Clear and update each dropdown
            for dropdown in [self.x_attr_dropdown, self.y_attr_dropdown, self.z_attr_dropdown]:
                dropdown.combo.clear()
                dropdown.combo.addItem("")  # Empty default option
                dropdown.combo.addItems(sorted(filtered_attributes))

            # Re-enable signals after updating
            self.x_attr_dropdown.combo.blockSignals(False)
            self.y_attr_dropdown.combo.blockSignals(False)
            self.z_attr_dropdown.combo.blockSignals(False)

        except Exception as e:
            print(f"Error updating attribute dropdowns: {e}")
            import traceback
            traceback.print_exc()


    def load_zone_data(self):
        """
        Load zone data, remove string columns, convert numeric columns to float, 
        and merge all data based on 'UWI'.
        """
        try:
            all_zone_data = []
            well_zones = self.db_manager.fetch_zone_names_by_type("Well")
            print(f"Loading zones: {well_zones}")

            for zone_tuple in well_zones:
                zone_name = zone_tuple[0]
                print(f"\nProcessing zone: {zone_name}")

                # Fetch zone data
                data, columns = self.db_manager.fetch_zone_table_data(zone_name)

                # Convert to DataFrame
                df = pd.DataFrame(data, columns=columns)

                # Skip if no data
                if df.empty:
                    print(f"No data found for zone {zone_name}, skipping...")
                    continue

                # Standardize UWI column name and convert to string
                df.rename(columns={col: "UWI" for col in df.columns if col.lower() == "uwi"}, inplace=True)
                df["UWI"] = df["UWI"].astype(str).str.strip()

                # Ensure 'UWI' is always present
                if "UWI" not in df.columns:
                    print(f"Skipping zone {zone_name} - missing 'UWI' column")
                    continue

                # Add zone name column
                df['Zone Name'] = zone_name

                # Identify numeric columns (convert to float, remove string columns)
                numeric_cols = []
                for col in df.columns:
                    if col in ['UWI', 'Zone Name']:  # Keep these as they are
                        continue
                
                    try:
                        # Convert column to numeric (float), coerce errors to NaN
                        df[col] = pd.to_numeric(df[col], errors='coerce')

                        # If the column is not entirely NaN, keep it
                        if not df[col].isna().all():
                            new_col_name = f"{zone_name}_{col}"  # Prefix to avoid conflicts
                            df.rename(columns={col: new_col_name}, inplace=True)
                            numeric_cols.append(new_col_name)
                        else:
                            print(f"Dropping column {col} (non-numeric) from {zone_name}")

                    except Exception as e:
                        print(f"Error converting {col} in {zone_name} to float: {e}")

                # Keep only UWI, Zone Name, and numeric columns
                keep_cols = ['UWI', 'Zone Name'] + numeric_cols
                df = df[keep_cols]

                # Only add if we have valid numeric data
                if len(numeric_cols) > 0:
                    all_zone_data.append(df)
                    print(f"Added {len(numeric_cols)} numeric columns for zone {zone_name}")

            if not all_zone_data:
                print("No valid zone data to load")
                return

            # Merge all zone data by UWI
            self.master_df = pd.concat(all_zone_data, ignore_index=True)

            # Remove rows with null UWI
            self.master_df.dropna(subset=['UWI'], inplace=True)

            # Print final dataframe info
            print("\nFinal merged dataframe analysis:")
            print(f"Total rows: {len(self.master_df)}")
            print(f"Numeric columns: {self.master_df.select_dtypes(include=['float64']).columns.tolist()}")

            # Update zone dropdown
            unique_zones = sorted(self.master_df["Zone Name"].unique())

            # Block signals before modifying the dropdown
            self.zone_name_dropdown.combo.blockSignals(True)

            self.zone_name_dropdown.combo.clear()
            self.zone_name_dropdown.combo.addItem("All")

            for zone in unique_zones:
                if pd.notna(zone) and zone != "Unknown":
                    self.zone_name_dropdown.combo.addItem(str(zone))

            # Re-enable signals after updating
            self.zone_name_dropdown.combo.blockSignals(False)

        except Exception as e:
            print(f"Error loading zone data: {e}")
            import traceback
            traceback.print_exc()



    def plot_3d_crossplot(self):
        """Plot either 2D or 3D scatter plot based on selected attributes."""
        try:
            if self.master_df is None or self.master_df.empty:
                print("No data available for plotting.")
                return

            # Get current values from dropdowns
            zone_name = self.zone_name_dropdown.combo.currentText()
            x_attr = self.x_attr_dropdown.combo.currentText()
            y_attr = self.y_attr_dropdown.combo.currentText()
            z_attr = self.z_attr_dropdown.combo.currentText()

            print("\nPlot update triggered:")
            print(f"Zone: {zone_name}")
            print(f"X: {x_attr}")
            print(f"Y: {y_attr}")
            print(f"Z: {z_attr}")

            # Check if we have enough attributes for at least a 2D plot
            if not x_attr or not y_attr:
                print("Select at least X and Y attributes before plotting.")
                return

            # Start with a copy of the master dataframe
            df = self.master_df.copy()
            print(f"Initial data size: {len(df)} rows")

            # Apply zone filter
            if zone_name != "All":
                df = df[df["Zone Name"] == zone_name]
                print(f"After zone filter: {len(df)} rows")

            # Select required columns
            required_cols = ['UWI', x_attr, y_attr]
            if z_attr:  # Add Z attribute if selected
                required_cols.append(z_attr)
    
            df = df[required_cols]

            # Remove rows with NaN in selected attributes
            df_clean = df.dropna(subset=required_cols[1:])  # Exclude UWI from NaN check
            print(f"Rows after removing NaN: {len(df_clean)}")

            if df_clean.empty:
                print("No valid data available for plotting.")
                return

            # Handle zeros visibility for plotting (but keep data for regression)
            if self.ignore_zeros_checkbox.isChecked():
                nonzero_mask = (df_clean[x_attr].abs() > 1e-10) & (df_clean[y_attr].abs() > 1e-10)
                if z_attr:
                    nonzero_mask &= (df_clean[z_attr].abs() > 1e-10)
                plot_x = df_clean[x_attr][nonzero_mask]
                plot_y = df_clean[y_attr][nonzero_mask]
                plot_uwi = df_clean["UWI"][nonzero_mask]
                if z_attr:
                    plot_z = df_clean[z_attr][nonzero_mask]
            else:
                plot_x = df_clean[x_attr]
                plot_y = df_clean[y_attr]
                plot_uwi = df_clean["UWI"]
                if z_attr:
                    plot_z = df_clean[z_attr]

            # Create the plot
            fig = go.Figure()

            if z_attr:  # 3D plot
                # Add 3D scatter points
                fig.add_trace(go.Scatter3d(
                    x=plot_x,
                    y=plot_y,
                    z=plot_z,
                    mode='markers',
                    text=plot_uwi,
                    name="Data Points",
                    hoverinfo='text',
                    marker=dict(
                        size=5,
                        opacity=0.8,
                        colorscale='Viridis',
                    )
                ))

                # Add 3D regression plane if requested (using full dataset)
                if self.add_regression_checkbox.isChecked() and len(df_clean) > 3:
                    try:
                        X = df_clean[[x_attr, y_attr]].values
                        y = df_clean[z_attr].values
                        model = LinearRegression()
                        model.fit(X, y)

                        x_range = np.linspace(df_clean[x_attr].min(), df_clean[x_attr].max(), 30)
                        y_range = np.linspace(df_clean[y_attr].min(), df_clean[y_attr].max(), 30)
                        xx, yy = np.meshgrid(x_range, y_range)
                        z_pred = model.predict(np.column_stack([xx.ravel(), yy.ravel()])).reshape(xx.shape)

                        fig.add_trace(go.Surface(
                            x=x_range,
                            y=y_range,
                            z=z_pred,
                            name='Regression Plane',
                            colorscale='Viridis',
                            opacity=0.5,
                            showscale=False
                        ))
                    except Exception as e:
                        print(f"Error adding 3D regression plane: {e}")

                # 3D layout updates
                fig.update_layout(
                    scene=dict(
                        xaxis_title=x_attr,
                        yaxis_title=y_attr,
                        zaxis_title=z_attr,
                        camera=dict(
                            eye=dict(x=1.5, y=1.5, z=1.5)
                        )
                    )
                )

            else:  # 2D plot
                # Add 2D scatter points
                fig.add_trace(go.Scatter(
                    x=plot_x,
                    y=plot_y,
                    mode='markers',
                    text=plot_uwi,
                    name="Data Points",
                    hoverinfo='text',
                    marker=dict(
                        size=8,
                        opacity=0.8,
                        color='#1f77b4',
                    )
                ))

                # Add 2D regression line if requested (using full dataset)
                if self.add_regression_checkbox.isChecked() and len(df_clean) > 2:
                    try:
                        X = df_clean[x_attr].values.reshape(-1, 1)
                        y = df_clean[y_attr].values
                        model = LinearRegression()
                        model.fit(X, y)

                        x_range = np.linspace(df_clean[x_attr].min(), df_clean[x_attr].max(), 100)
                        y_pred = model.predict(x_range.reshape(-1, 1))

                        fig.add_trace(go.Scatter(
                            x=x_range,
                            y=y_pred,
                            mode='lines',
                            name='Regression Line',
                            line=dict(color='red', width=2)
                        ))
                    except Exception as e:
                        print(f"Error adding 2D regression line: {e}")

                # 2D layout updates
                fig.update_layout(
                    xaxis_title=x_attr,
                    yaxis_title=y_attr,
                )

            # Common layout updates
            fig.update_layout(
                title="CrossPlot" if not z_attr else "3D CrossPlot",
                template='plotly_dark',
                margin=dict(l=0, r=0, t=30, b=0),
                showlegend=True
            )

            html_content = py_offline.plot(fig, include_plotlyjs='cdn', output_type='div')
            self.plot_widget.setHtml(html_content)
            print("Plot updated successfully")

        except Exception as e:
            print(f"Error plotting crossplot: {e}")
            import traceback
            traceback.print_exc()