from PySide6.QtWidgets import (QDialog, QListWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
                               QTableWidget, QTableWidgetItem, QMessageBox, QSpacerItem, QWidget, QSizePolicy, 
                               QListWidgetItem, QComboBox, QCheckBox)
from PySide6.QtGui import QIcon
from PySide6.QtCore import Qt, QSize
import pandas as pd
import numpy as np
import sys
import seaborn as sns
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from StyledTwoListSelector import TwoListSelector
from StyledDropdown import StyledDropdown, StyledInputBox, StyledBaseWidget
from StyledButton import StyledButton
from scipy.stats import linregress
#

class CalculateCorrelations(QDialog):
    def __init__(self, master_df, parent=None):
        super().__init__(parent)
        self.master_df = master_df
        self.initUI()



    def initUI(self):
        self.setWindowTitle("Correlation Analysis")
        self.setGeometry(100, 100, 1200, 800)  # Initial window size

        # Enable Minimize and Maximize buttons
        self.setWindowFlags(self.windowFlags() | Qt.WindowMinMaxButtonsHint)
    
        # Main layout
        main_layout = QHBoxLayout(self)

        # Left side container for controls and table
        left_container = QWidget()
        left_layout = QVBoxLayout(left_container)

        # Threshold Dropdown
        self.threshold_dropdown = StyledDropdown("Threshold:", parent=self)
        self.threshold_dropdown.addItems(["0", "0.1", "0.2", "0.3", "0.4", "0.5", "0.6", "0.7", "0.8", "0.9"])
        left_layout.addWidget(self.threshold_dropdown)

        # Checkbox for excluding zeros
        self.exclude_zeros_checkbox = QCheckBox("Exclude zeros in calculation")
        left_layout.addWidget(self.exclude_zeros_checkbox)

        # Attribute Selector
        available_columns = sorted([col for col in self.master_df.columns])
        self.attribute_selector = TwoListSelector("Available Attributes", "Selected Attributes")
        self.attribute_selector.set_left_items(available_columns)
        left_layout.addWidget(self.attribute_selector)

        # Dropdown for attribute filtering
        self.filter_dropdown = StyledDropdown("Filter Results:", parent=self)
        self.filter_dropdown.setVisible(False)
        self.filter_dropdown.combo.addItem("Show All")
        left_layout.addWidget(self.filter_dropdown)
        self.filter_dropdown.combo.currentIndexChanged.connect(self.filter_results_by_attribute)

        # Results Table
        self.results_table = QTableWidget(self)
        self.results_table.setColumnCount(5)
        self.results_table.setHorizontalHeaderLabels(
            ["Attribute 1", "Attribute 2", "Correlation Type", "Correlation Coefficient", "Standard Error"])
        self.results_table.setSortingEnabled(True)
        left_layout.addWidget(self.results_table)

        # Action Buttons
        button_layout = QHBoxLayout()
        button_size = (80, 25)
    
        self.run_button = StyledButton("Run", "function")
        self.close_button = StyledButton("Close", "close")
    
        self.run_button.setFixedSize(*button_size)
        self.close_button.setFixedSize(*button_size)
    
        self.run_button.clicked.connect(self.calculate_and_display_correlation)
        self.close_button.clicked.connect(self.reject)
    
        button_layout.addStretch()
        button_layout.addWidget(self.run_button)
        button_layout.addWidget(self.close_button)
    
        left_layout.addLayout(button_layout)

            # Heatmap Widget (on the right side)
        self.heatmap_widget = QWidget()
        self.heatmap_widget.setStyleSheet("""
            QWidget {
                background-color: black;
            }
        """)
        heatmap_layout = QVBoxLayout(self.heatmap_widget)

    
        # Matplotlib Figure for Heatmap
        self.heatmap_figure = plt.figure(figsize=(10, 8), dpi=100, facecolor='black')
        self.heatmap_canvas = FigureCanvas(self.heatmap_figure)
        heatmap_layout.addWidget(self.heatmap_canvas)

        # Add left container and heatmap to main layout
        main_layout.addWidget(left_container, 1)  # Left side takes less space
        main_layout.addWidget(self.heatmap_widget, 2)  # Heatmap can expand more

        # Set the layout for the dialog
        self.setLayout(main_layout)



    def create_crossplot(self, attr1, attr2):
        # Clear previous crossplot
        self.ax_crossplot.clear()

        # Get data for selected attributes
        x = self.last_correlation_df[attr1].to_numpy()
        y = self.last_correlation_df[attr2].to_numpy()

        # If "Exclude Zeros" is checked, remove rows with zeros
        if self.exclude_zeros_checkbox.isChecked():
            mask = (x != 0) & (y != 0)
            x = x[mask]
            y = y[mask]

        # Remove any NaN values
        valid_mask = ~np.isnan(x) & ~np.isnan(y)
        x_clean = x[valid_mask]
        y_clean = y[valid_mask]


        # Check for sufficient valid data points
        if len(x_clean) < 2:  # Need at least 2 points for regression
            self.ax_crossplot.set_title("Insufficient valid data for regression", fontsize=8, color='red')
            self.heatmap_canvas.draw()
            return

        # Set dark background
        self.ax_crossplot.set_facecolor('#1E1E1E')

        # Create scatter plot
        self.ax_crossplot.scatter(
            x_clean, y_clean,
            alpha=0.7,
            edgecolors='cyan',
            linewidth=1.5
        )

        # Compute trendline using `linregress` with error handling
        try:
            # Ensure data is finite
            finite_mask = np.isfinite(x_clean) & np.isfinite(y_clean)
            if not np.any(finite_mask):
                raise ValueError("No finite values available for regression")

            x_finite = x_clean[finite_mask]
            y_finite = y_clean[finite_mask]

            if len(x_finite) < 2:
                raise ValueError("Need at least two finite points for regression")

            slope, intercept, r_value, p_value, std_err = linregress(x_finite, y_finite)

            # Check if regression results are valid
            if np.isfinite(slope) and np.isfinite(intercept):
                # Create line of best fit
                line_x = np.array([np.min(x_finite), np.max(x_finite)])
                line_y = slope * line_x + intercept

                # Plot the trendline
                self.ax_crossplot.plot(
                    line_x, line_y, 
                    color='magenta', 
                    linestyle='--', 
                    linewidth=2,
                    label=f'y = {slope:.2f}x + {intercept:.2f}\nR² = {r_value**2:.2f}'
                )

                # Add legend
                self.ax_crossplot.legend(fontsize=6, facecolor='#2C2C2C', edgecolor='magenta', labelcolor='white')
            else:
                print("Invalid regression results:", slope, intercept)
                raise ValueError("Invalid regression coefficients")

        except Exception as e:
            print(f"Trendline error: {e}")
            self.ax_crossplot.text(
                0.5, 0.5, 
                f"Could not calculate trendline:\n{str(e)}", 
                ha='center', 
                va='center',
                color='red',
                fontsize=8,
                transform=self.ax_crossplot.transAxes
            )

        # Compute correlation for valid data
        correlation = np.corrcoef(x_finite, y_finite)[0, 1] if len(x_finite) > 1 else np.nan

        # Set title color based on correlation
        title_color = 'red' if correlation > 0 else 'blue' if correlation < 0 else 'white'

        # Set title and labels
        self.ax_crossplot.set_title(
            f'Scatter Plot: {attr1} vs {attr2}\nCorrelation: {correlation:.2f}', 
            fontsize=8, 
            color=title_color
        )
        self.ax_crossplot.set_xlabel(attr1, fontsize=6, color='cyan')
        self.ax_crossplot.set_ylabel(attr2, fontsize=6, color='cyan')

        # Style axes
        for spine in ['bottom', 'top', 'left', 'right']:
            self.ax_crossplot.spines[spine].set_color('cyan')

        # Tick colors
        self.ax_crossplot.tick_params(colors='white', which='both')

        # Grid with subtle neon effect
        self.ax_crossplot.grid(color='cyan', linestyle='--', linewidth=0.5, alpha=0.3)

        # Redraw the canvas
        self.heatmap_canvas.draw()

    def calculate_and_display_correlation(self):
        # Get selected attributes
        selected_attributes = self.attribute_selector.get_right_items()
    
        if len(selected_attributes) < 2:
            QMessageBox.warning(self, "Selection Error", "Please select at least two attributes.")
            return

        # Filter DataFrame
        df_filtered = self.master_df[selected_attributes]
    
        # Store the filtered dataframe for later use
        self.last_correlation_df = df_filtered
    
        # Calculate correlations
        results_df = self.calculate_correlation_analysis(df_filtered)

        # Populate the filter dropdown with selected attributes
        self.populate_filter_dropdown(selected_attributes)

        # Display results in the table
        self.display_results_in_table(results_df)

        # Create and display heatmap
        self.display_correlation_heatmap(df_filtered)

    def calculate_correlation_analysis(self, df):
        self.reset_state()

        # ✅ Filter only numeric columns
        numeric_df = df.select_dtypes(include=[np.number])  # Keeps only numeric columns

        if numeric_df.empty:
            QMessageBox.warning(self, "Error", "No numeric columns available for correlation analysis.")
            return pd.DataFrame()  # Return an empty DataFrame to prevent crashes

        # ✅ If the user selects "Exclude Zeros", replace them with NaN (but don’t remove rows!)
        if self.exclude_zeros_checkbox.isChecked():
            numeric_df = numeric_df.replace(0, np.nan)  # ✅ Keeps rows but excludes zeros in correlation calculation

        # ✅ Compute correlation only on numeric columns
        corr_matrix = numeric_df.corr()

        # Prepare a DataFrame to store results
        results = []

        # Calculate correlation and standard error
        for i in range(len(corr_matrix.columns)):
            for j in range(i + 1, len(corr_matrix.columns)):  # Avoid duplicate pairs
                attr1 = corr_matrix.columns[i]
                attr2 = corr_matrix.columns[j]
                r = corr_matrix.iloc[i, j]

                # Get valid sample size (excluding NaN values from the correlation calculation)
                n = numeric_df[[attr1, attr2]].dropna().shape[0]  # ✅ Drops NaN only when counting valid samples

                # Compute standard error (avoid division by zero)
                # Compute standard error (avoid division by zero)
                if n > 2:
                    se = np.sqrt((1 - r**2) / max(n - 2, 1))  # Ensure denominator is at least 1
                else:
                    se = np.nan  # If not enough data, set to NaN


                # Determine correlation type
                corr_type = "Positive" if r > 0 else "Negative" if r < 0 else "Flat"

                results.append({
                    "Attribute 1": attr1,
                    "Attribute 2": attr2,
                    "Correlation Type": corr_type,
                    "Correlation Coefficient": r,
                    "Standard Error": se
                })

        # Convert the results into a DataFrame and return
        results_df = pd.DataFrame(results)
        return results_df

    def display_results_in_table(self, results_df):
        # Clear the table first
        self.results_table.setRowCount(0)

        # Get the threshold value selected by the user
        threshold = float(self.threshold_dropdown.currentText())

        # Populate the table with the results, filtering by the threshold (absolute value)
        for row_idx, row in results_df.iterrows():
            if abs(row["Correlation Coefficient"]) >= threshold:
                self.results_table.insertRow(row_idx)
                self.results_table.setItem(row_idx, 0, QTableWidgetItem(str(row["Attribute 1"])))
                self.results_table.setItem(row_idx, 1, QTableWidgetItem(str(row["Attribute 2"])))
                self.results_table.setItem(row_idx, 2, QTableWidgetItem(row["Correlation Type"]))
                self.results_table.setItem(row_idx, 3, QTableWidgetItem(f"{row['Correlation Coefficient']:.4f}"))
                self.results_table.setItem(row_idx, 4, QTableWidgetItem(f"{row['Standard Error']:.4f}"))

    def populate_filter_dropdown(self, attributes):
        # Remove any empty strings
        attributes = [attr for attr in attributes if attr and attr.strip()]

        # Show the filter dropdown and populate it with selected attributes
        self.filter_dropdown.setVisible(True)
        self.filter_dropdown.combo.clear()  # Clear existing items
        self.filter_dropdown.combo.addItem("Show All")  # Add the "Show All" option
    
        # Add non-empty attributes
        if attributes:
            self.filter_dropdown.combo.addItems(attributes)

    def filter_results_by_attribute(self):
        selected_attribute = self.filter_dropdown.combo.currentText()
    
        print("Debug - Filter Dropdown Items:")
        for i in range(self.filter_dropdown.combo.count()):
            print(f"Item {i}: '{self.filter_dropdown.combo.itemText(i)}'")

        print(f"Selected attribute: '{selected_attribute}'")
        print(f"Type of selected attribute: {type(selected_attribute)}")

        # If "Show All" is selected, revert to full heatmap
        if selected_attribute == "Show All":
            # Reuse the existing figure if possible
            self.display_correlation_heatmap(self.last_correlation_df)
    
            # Show all rows in the table
            for row in range(self.results_table.rowCount()):
                self.results_table.setRowHidden(row, False)
        
            return

        # If a specific attribute is selected, update the heatmap
        try:
            self.update_filtered_heatmap(selected_attribute)
        except Exception as e:
            print(f"Error updating filtered heatmap: {e}")
            # Fallback to full heatmap
            self.display_correlation_heatmap(self.last_correlation_df)

        # Filter the table
        for row in range(self.results_table.rowCount()):
            self.results_table.setRowHidden(row, False)  # First, show all rows
    
            attr1 = self.results_table.item(row, 0).text()
            attr2 = self.results_table.item(row, 1).text()
    
            # Hide rows that don't contain the selected attribute
            if selected_attribute not in [attr1, attr2]:
                self.results_table.setRowHidden(row, True)

    def display_correlation_heatmap(self, df):
        # Check if figure already exists and is valid
        if not hasattr(self, 'heatmap_figure') or not plt.fignum_exists(self.heatmap_figure.number):
            # Clear previous plot
            self.heatmap_figure = plt.figure(figsize=(10, 8), dpi=100, facecolor='black')
        else:
            # Clear existing axes
            for ax in self.heatmap_figure.get_axes():
                ax.clear()

        # Create a grid of subplots
        gs = self.heatmap_figure.add_gridspec(2, 1, height_ratios=[2, 1], hspace=.8)

        # Heatmap subplot
        ax_heatmap = self.heatmap_figure.add_subplot(gs[0])
        ax_heatmap.set_facecolor('black')

        # Calculate correlation matrix
        corr_matrix = df.corr()

        # Create heatmap with seaborn
        heatmap = sns.heatmap(
            corr_matrix, 
            annot=True,          # Show correlation values
            cmap='coolwarm_r',   # Reversed Red-Blue color map (blue for positive, red for negative)
            center=0,            # Center color map at 0
            vmin=-1, 
            vmax=1,
            square=False,         # Allow non-square cells
            ax=ax_heatmap,
            fmt='.2f',            # Format to 2 decimal places
            cbar=False,           # Remove color bar
            annot_kws={"size": 6, "color": "white"},  # White annotations
            linewidths=0.5,       # Add grid lines
            linecolor='cyan'      # Cyan grid lines
        )

        ax_heatmap.tick_params(axis='both', colors='white', labelsize=5)  # Smaller font
        ax_heatmap.set_xticklabels(ax_heatmap.get_xticklabels(), rotation=75, ha='right', fontsize=5, color='white')
        ax_heatmap.set_yticklabels(ax_heatmap.get_yticklabels(), fontsize=5, color='white')

        # Adjust spacing to maximize horizontal space
        plt.subplots_adjust(left=0.1, right=0.95, bottom=0.2, top=0.95)

        # Cyan borders
        for spine in ax_heatmap.spines.values():
            spine.set_edgecolor('cyan')

        # Remove x and y labels
        ax_heatmap.set_xlabel('')
        ax_heatmap.set_ylabel('')

        # Remove title
        ax_heatmap.set_title('')

        # Cross-plot subplot (initially empty)
        self.ax_crossplot = self.heatmap_figure.add_subplot(gs[1])
        self.ax_crossplot.clear()
        self.ax_crossplot.set_facecolor('black')

        # Styled initial title
        self.ax_crossplot.set_title('Click heatmap to show scatter plot', 
                                     fontsize=8, 
                                     color='cyan')
        self.ax_crossplot.set_xlabel('')
        self.ax_crossplot.set_ylabel('')

        # Connect click event
        def on_cell_click(event):
            if event.inaxes == ax_heatmap:
                # Get the column and row indices
                col_index = int(event.xdata)
                row_index = int(event.ydata)
        
                # Get the column names
                col_name = corr_matrix.columns[col_index]
                row_name = corr_matrix.index[row_index]
        
                # Create cross-plot
                self.create_crossplot(col_name, row_name)

        # Add click event
        self.heatmap_figure.canvas.mpl_connect('button_press_event', on_cell_click)

        # Replace the canvas safely
        if hasattr(self, 'heatmap_canvas'):
            try:
                self.heatmap_widget.layout().removeWidget(self.heatmap_canvas)
                self.heatmap_canvas.setParent(None)  # Fully detach widget before deletion
                self.heatmap_canvas.deleteLater()
            except RuntimeError as e:
                print(f"Canvas deletion error: {e}")

        # Now create the new canvas
        self.heatmap_canvas = FigureCanvas(self.heatmap_figure)
        self.heatmap_widget.layout().addWidget(self.heatmap_canvas)



        self.heatmap_canvas.draw()


    def reset_state(self):
        self.results_table.clearContents()  # Clear previous results
        self.results_table.setRowCount(0)   # Reset row count

    # Filter the table to show correlations involving these attributes
    def filter_table_by_attributes(self, attr1, attr2):
        # Show all rows first
        for row in range(self.results_table.rowCount()):
            self.results_table.setRowHidden(row, False)
    
        # Filter rows
        for row in range(self.results_table.rowCount()):
            table_attr1 = self.results_table.item(row, 0).text()
            table_attr2 = self.results_table.item(row, 1).text()
        
            # Hide rows that don't match the selected attributes
            if not ((table_attr1 == attr1 and table_attr2 == attr2) or 
                    (table_attr1 == attr2 and table_attr2 == attr1)):
                self.results_table.setRowHidden(row, True)
    
        # Update filter dropdown to reflect the selection
        index = self.filter_dropdown.combo.findText(attr1)
        if index != -1:
            self.filter_dropdown.combo.setCurrentIndex(index)

    def update_filtered_heatmap(self, selected_attribute):
        # Early return if "Show All" is passed
        if selected_attribute == "Show All":
            return

        try:
            # Close any existing figure to prevent memory leaks
            plt.close(self.heatmap_figure) if hasattr(self, 'heatmap_figure') else None
        
            # Create new figure
            self.heatmap_figure = plt.figure(figsize=(8, 8), dpi=100, facecolor='black')
    
            # Create a grid of subplots
            gs = self.heatmap_figure.add_gridspec(2, 1, height_ratios=[2, 1], hspace=0.8)
    
            # Bar graph subplot
            ax_bargraph = self.heatmap_figure.add_subplot(gs[0])
            ax_bargraph.set_facecolor('black')

            # Get the full correlation matrix
            corr_matrix = self.last_correlation_df.corr()

            # Safety check for the selected attribute
            if selected_attribute not in corr_matrix.columns:
                print(f"Attribute {selected_attribute} not found in correlation matrix")
                return

            # Get correlations for the selected attribute
            attr_correlations = corr_matrix.loc[selected_attribute].drop(selected_attribute)
    
            # Sort correlations by absolute value
            attr_correlations_sorted = attr_correlations.reindex(
                attr_correlations.abs().sort_values(ascending=False).index
            )

            # Create bar plot with neon styling
            bars = ax_bargraph.bar(
                attr_correlations_sorted.index, 
                attr_correlations_sorted.values, 
                color=[plt.cm.coolwarm(0.5 + 0.5 * val) for val in attr_correlations_sorted.values],
                edgecolor='cyan'
            )

            # Style the bar graph
            ax_bargraph.set_facecolor('black')
            ax_bargraph.spines['bottom'].set_color('cyan')
            ax_bargraph.spines['top'].set_color('cyan')
            ax_bargraph.spines['left'].set_color('cyan')
            ax_bargraph.spines['right'].set_color('cyan')

            # Rotate x-axis labels
            plt.sca(ax_bargraph)
            plt.xticks(rotation=45, ha='right', fontsize=6, color='white')
            plt.yticks(color='white')

            # Add value labels on top of each bar
            for bar in bars:
                height = bar.get_height()
                ax_bargraph.text(
                    bar.get_x() + bar.get_width()/2., 
                    height,
                    f'{height:.2f}',
                    ha='center', 
                    va='bottom', 
                    fontsize=6,
                    color='white'
                )

            # Set title and labels
            ax_bargraph.set_title(f'Correlations with {selected_attribute}', fontsize=8, color='cyan')
            ax_bargraph.set_xlabel('Attributes', fontsize=6, color='cyan')
            ax_bargraph.set_ylabel('Correlation Coefficient', fontsize=6, color='cyan')

            # Add a horizontal line at y=0
            ax_bargraph.axhline(y=0, color='cyan', linestyle='--', linewidth=0.5)

            # Cross-plot subplot (initially empty)
            self.ax_crossplot = self.heatmap_figure.add_subplot(gs[1])
            self.ax_crossplot.clear()
            self.ax_crossplot.set_facecolor('black')
            self.ax_crossplot.set_title(f'Click bar to show scatter plot for {selected_attribute}', 
                                         fontsize=8, 
                                         color='cyan')

            # Connect click event for bar graph
            def on_bar_click(event):
                if event.inaxes == ax_bargraph:
                    # Get the x-index of the clicked bar
                    x_index = int(event.xdata)
            
                    # Get the attribute name
                    clicked_attr = attr_correlations_sorted.index[x_index]
            
                    # Create cross-plot
                    self.create_crossplot(selected_attribute, clicked_attr)

            # Add click event
            self.heatmap_figure.canvas.mpl_connect('button_press_event', on_bar_click)

            # Replace the canvas
            if hasattr(self, 'heatmap_canvas'):
                try:
                    self.heatmap_widget.layout().removeWidget(self.heatmap_canvas)
                    self.heatmap_canvas.deleteLater()
                except Exception as e:
                    print(f"Error removing previous canvas: {e}")

            self.heatmap_canvas = FigureCanvas(self.heatmap_figure)
            self.heatmap_widget.layout().addWidget(self.heatmap_canvas)

            # Adjust layout and redraw
            plt.tight_layout(pad=1.0)
            self.heatmap_canvas.draw()

        except Exception as e:
            print(f"Comprehensive error in update_filtered_heatmap: {e}")
            import traceback
            traceback.print_exc()


# Example usage
if __name__ == "__main__":
    from PySide6.QtWidgets import QApplication

    # Example DataFrame
    data = {
        'Pressure': [300, 400, 500, 600, 300, 200, 250],
        'Fluid_Pressure': [50, 30, 80, 20, 70, 10, 60],
        'Attribute1': [1, 2, 1, 3, 2, 1, 2],
        'Attribute2': [5, 3, 6, 2, 5, 4, 6],
        'Attribute3': [1.5, 2.3, 3.1, 4.2, 2.5, 1.9, 2.8],
    }
    master_df = pd.DataFrame(data)

    app = QApplication(sys.argv)
    dialog = CalculateCorrelations(master_df)
    dialog.show()
    sys.exit(app.exec())