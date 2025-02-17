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
    
        # Set dark background
        self.ax_crossplot.set_facecolor('#1E1E1E')  # Dark background
    
        # Create scatter plot with neon-like colors
        scatter = self.ax_crossplot.scatter(
            self.last_correlation_df[attr1], 
            self.last_correlation_df[attr2],
            alpha=0.7,
            c=self.last_correlation_df[attr1],  # Color based on first attribute
            cmap='plasma',  # Vibrant color map
            edgecolors='cyan',  # Neon cyan edge
            linewidth=1.5
        )
    
        # Add line of best fit with neon style
        x = self.last_correlation_df[attr1]
        y = self.last_correlation_df[attr2]
        m, b = np.polyfit(x, y, 1)
        self.ax_crossplot.plot(x, m*x + b, color='magenta', linestyle='--', linewidth=2, label=f'y = {m:.2f}x + {b:.2f}')
    
        # Calculate correlation
        correlation = self.last_correlation_df[attr1].corr(self.last_correlation_df[attr2])
    
        # Set title and labels with light colors
        self.ax_crossplot.set_title(f'Scatter Plot: {attr1} vs {attr2}\nCorrelation: {correlation:.2f}', 
                                     fontsize=8, 
                                     color='white')
        self.ax_crossplot.set_xlabel(attr1, fontsize=6, color='cyan')
        self.ax_crossplot.set_ylabel(attr2, fontsize=6, color='cyan')
    
        # Style axes
        self.ax_crossplot.spines['bottom'].set_color('cyan')
        self.ax_crossplot.spines['top'].set_color('cyan')
        self.ax_crossplot.spines['left'].set_color('cyan')
        self.ax_crossplot.spines['right'].set_color('cyan')
    
        # Tick colors
        self.ax_crossplot.tick_params(colors='white', which='both')
    
        # Add legend with neon style
        self.ax_crossplot.legend(fontsize=6, facecolor='#2C2C2C', edgecolor='magenta', labelcolor='white')
    
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
        # Check if the user wants to exclude zeros
        if self.exclude_zeros_checkbox.isChecked():
            df = df.replace(0, np.nan)  # Replace zeros with NaN to exclude from correlation

        # Calculate the correlation matrix
        corr_matrix = df.corr()

        # Prepare a DataFrame to store results
        results = []

        # Calculate the correlation and standard error
        for i in range(len(corr_matrix.columns)):
            for j in range(i+1, len(corr_matrix.columns)):
                attr1 = corr_matrix.columns[i]
                attr2 = corr_matrix.columns[j]
                r = corr_matrix.iloc[i, j]
                n = len(df.dropna(subset=[attr1, attr2]))  # Drop NaN rows for correct sample size
                se = np.sqrt((1 - r**2) / (n - 2)) if n > 2 else np.nan  # Avoid division by zero

                # Determine correlation type
                if r > 0:
                    corr_type = "Positive"
                elif r < 0:
                    corr_type = "Negative"
                else:
                    corr_type = "Flat"

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
        # Show the filter dropdown and populate it with selected attributes
        self.filter_dropdown.setVisible(True)
        self.filter_dropdown.combo.clear()  # Clear existing items
        self.filter_dropdown.combo.addItem("Show All")  # Add the "Show All" option
        self.filter_dropdown.combo.addItems(attributes)  # Add selected attributes

    def filter_results_by_attribute(self):
        selected_attribute = self.filter_dropdown.combo.currentText()
    
        # If only one attribute is selected, update the heatmap with bar chart
        if selected_attribute != "Show All":
            self.update_filtered_heatmap(selected_attribute)
        else:
            # Revert to full heatmap
            self.display_correlation_heatmap(self.last_correlation_df)
    
        # Filter the table
        for row in range(self.results_table.rowCount()):
            self.results_table.setRowHidden(row, False)  # First, show all rows
        
            if selected_attribute != "Show All":
                attr1 = self.results_table.item(row, 0).text()
                attr2 = self.results_table.item(row, 1).text()
            
                # Hide rows that don't contain the selected attribute
                if selected_attribute not in [attr1, attr2]:
                    self.results_table.setRowHidden(row, True)

    def display_correlation_heatmap(self, df):
        # Clear previous plot
        self.heatmap_figure = plt.figure(figsize=(10, 8), dpi=100, facecolor='black')
    
        # Create a grid of subplots
        gs = self.heatmap_figure.add_gridspec(2, 1, height_ratios=[2, 1], hspace=0.5)
    
        # Heatmap subplot
        ax_heatmap = self.heatmap_figure.add_subplot(gs[0])
        ax_heatmap.set_facecolor('black')
    
        # Calculate correlation matrix
        corr_matrix = df.corr()
    
        # Create heatmap with seaborn
        heatmap = sns.heatmap(
            corr_matrix, 
            annot=True,          # Show correlation values
            cmap='coolwarm',     # Red-Blue color map
            center=0,            # Center color map at 0
            vmin=-1, 
            vmax=1,
            square=True,          # Make squares equal
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

        # Adjust spacing so labels don’t overlap cross-plot
        plt.subplots_adjust(bottom=0.1, top=0.95)
    
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
    
        # Replace the canvas
        if hasattr(self, 'heatmap_canvas'):
            self.heatmap_widget.layout().removeWidget(self.heatmap_canvas)
            self.heatmap_canvas.deleteLater()
    
        self.heatmap_canvas = FigureCanvas(self.heatmap_figure)
        self.heatmap_widget.layout().addWidget(self.heatmap_canvas)
    
        # Adjust layout and redraw
        self.heatmap_figure.tight_layout()
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
        # Clear previous plot
        self.heatmap_figure = plt.figure(figsize=(8, 8), dpi=100, facecolor='black')
    
        # Create a grid of subplots
        gs = self.heatmap_figure.add_gridspec(2, 1, height_ratios=[2, 1], hspace=0.4)
    
        # Bar graph subplot
        ax_bargraph = self.heatmap_figure.add_subplot(gs[0])
        ax_bargraph.set_facecolor('black')

        # Get the full correlation matrix
        corr_matrix = self.last_correlation_df.corr()

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
            self.heatmap_widget.layout().removeWidget(self.heatmap_canvas)
            self.heatmap_canvas.deleteLater()

        self.heatmap_canvas = FigureCanvas(self.heatmap_figure)
        self.heatmap_widget.layout().addWidget(self.heatmap_canvas)

        # Adjust layout and redraw
        self.heatmap_figure.tight_layout()
        self.heatmap_canvas.draw()



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