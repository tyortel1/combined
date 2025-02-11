from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                               QTableWidget, QTableWidgetItem, QSplitter,
                               QWidget, QLineEdit, QAbstractItemView, QPushButton, QListWidget, QMessageBox, QCheckBox, QFileDialog)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
import pandas as pd
import seaborn as sns
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
import openpyxl
from openpyxl.styles import PatternFill
import numpy as np
import traceback

class CrossplotDialog(QDialog):
    def __init__(self, data_matrix, x_col, y_col, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Crossplot: {x_col} vs {y_col}")
        self.setMinimumSize(800, 600)

        layout = QVBoxLayout()
        fig, ax = plt.subplots(figsize=(8, 6))
        canvas = FigureCanvasQTAgg(fig)

        sns.regplot(
            x=data_matrix[x_col], 
            y=data_matrix[y_col], 
            scatter_kws={'alpha': 0.7},
            line_kws={'color': 'red'},
            ax=ax
        )

        ax.set_xlabel(x_col)
        ax.set_ylabel(y_col)
        ax.set_title(f"Crossplot: {x_col} vs {y_col}")

        corr = data_matrix[x_col].corr(data_matrix[y_col])
        ax.annotate(f'Correlation: {corr:.2f}', 
                    xy=(0.05, 0.95), 
                    xycoords='axes fraction',
                    fontsize=10,
                    verticalalignment='top')

        fig.tight_layout()
        layout.addWidget(canvas)
        self.setLayout(layout)








class CorrelationDisplayDialog(QDialog):
    def __init__(self, correlation_matrix, data_matrix, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Correlation Matrix Results")
        self.setMinimumWidth(1400)
        self.setMinimumHeight(900)

        self.correlation_matrix = correlation_matrix
        self.data_matrix = data_matrix

        self.setWindowFlags(self.windowFlags() | Qt.WindowMaximizeButtonHint)

        splitter = QSplitter(Qt.Horizontal)
        main_layout = QHBoxLayout(self)

        # Left Panel: Heatmap
        heatmap_section = QWidget()
        heatmap_layout = QVBoxLayout(heatmap_section)

        self.heatmap_fig = Figure(figsize=(8, 6))
        self.heatmap_canvas = FigureCanvasQTAgg(self.heatmap_fig)
        self.heatmap_ax = self.heatmap_fig.add_subplot(111)

        self.draw_heatmap()
        self.heatmap_canvas.mpl_connect('button_press_event', self.on_heatmap_click)

        heatmap_layout.addWidget(self.heatmap_canvas)
        splitter.addWidget(heatmap_section)

        # Right Panel: Raw Data Table + Crossplot
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)

        # Raw Data Table
        raw_data_label = QLabel("Raw Data Matrix")
        right_layout.addWidget(raw_data_label)

        self.raw_data_table = QTableWidget()
        self.populate_raw_data_table()
        right_layout.addWidget(self.raw_data_table)

        # Crossplot
        self.crossplot_label = QLabel("Crossplot (Click Heatmap to Update)")
        right_layout.addWidget(self.crossplot_label)

        self.crossplot_fig = Figure(figsize=(6, 5))
        self.crossplot_canvas = FigureCanvasQTAgg(self.crossplot_fig)
        self.crossplot_ax = self.crossplot_fig.add_subplot(111)

        right_layout.addWidget(self.crossplot_canvas)

        # Export Button
        export_button = QPushButton("Export to Excel")
        export_button.setFixedSize(140, 40)
        export_button.clicked.connect(self.export_to_excel)
        right_layout.addWidget(export_button, alignment=Qt.AlignRight | Qt.AlignBottom)

        splitter.addWidget(right_panel)
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 3)

        main_layout.addWidget(splitter)
        self.setLayout(main_layout)

    def draw_heatmap(self):
        """Draws the heatmap with interactive click support."""
        self.heatmap_ax.clear()
        sns.heatmap(
            self.correlation_matrix, annot=True, cmap='RdYlBu', center=0, 
            fmt='.2f', vmin=-1, vmax=1, ax=self.heatmap_ax, cbar=True,
            annot_kws={"size": 8},
            xticklabels=self.correlation_matrix.columns,
            yticklabels=self.correlation_matrix.index
        )

        self.heatmap_ax.tick_params(axis='x', labelsize=6, rotation=45)
        self.heatmap_ax.tick_params(axis='y', labelsize=6)
        self.heatmap_canvas.draw()

    def on_heatmap_click(self, event):
        """Handles clicking on the heatmap and updates the crossplot."""
        if event.inaxes == self.heatmap_ax:
            try:
                col = round(event.xdata - 0.5)
                row = round(event.ydata - 0.5)

                if (0 <= row < len(self.correlation_matrix.index) and 
                    0 <= col < len(self.correlation_matrix.columns) and 
                    row != col):
                    self.update_crossplot(row, col)
            except (TypeError, ValueError):
                pass

    def update_crossplot(self, row, col):
        """Updates the crossplot with the selected variables."""
        x_col = self.correlation_matrix.columns[col]
        y_col = self.correlation_matrix.index[row]

        self.crossplot_ax.clear()
        self.crossplot_ax.set_title(f"Crossplot: {x_col} vs {y_col}")
        self.crossplot_ax.set_xlabel(x_col)
        self.crossplot_ax.set_ylabel(y_col)

        sns.regplot(
            x=self.data_matrix[x_col], 
            y=self.data_matrix[y_col], 
            scatter_kws={'alpha': 0.7},
            line_kws={'color': 'red'},
            ax=self.crossplot_ax
        )

        # Display correlation coefficient
        corr = self.data_matrix[x_col].corr(self.data_matrix[y_col])
        self.crossplot_ax.annotate(f'Correlation: {corr:.2f}', 
                                   xy=(0.05, 0.95), 
                                   xycoords='axes fraction',
                                   fontsize=10,
                                   verticalalignment='top')

        self.crossplot_canvas.draw()

    def populate_raw_data_table(self):
        """Fills the raw data table."""
        self.raw_data_table.setRowCount(len(self.data_matrix.index))
        self.raw_data_table.setColumnCount(len(self.data_matrix.columns))
        self.raw_data_table.setHorizontalHeaderLabels(self.data_matrix.columns)
        self.raw_data_table.setVerticalHeaderLabels(self.data_matrix.index)

        for i in range(len(self.data_matrix.index)):
            for j in range(len(self.data_matrix.columns)):
                value = self.data_matrix.iloc[i, j]
                item = QTableWidgetItem(f"{value:.3f}" if isinstance(value, float) else str(value))
                item.setTextAlignment(int(Qt.AlignCenter))
                self.raw_data_table.setItem(i, j, item)

        self.raw_data_table.resizeColumnsToContents()

    def export_to_excel(self):
        """Export correlation matrix to an Excel file with colors"""
        try:
            file_path, _ = QFileDialog.getSaveFileName(self, "Save File", "", "Excel Files (*.xlsx)")
            if not file_path:
                return  

            if not file_path.lower().endswith('.xlsx'):
                file_path += '.xlsx'

            workbook = openpyxl.Workbook()
            std_sheet = workbook.active
            workbook.remove(std_sheet)

            sheet = workbook.create_sheet("Correlation Matrix")

            for col_idx, col_name in enumerate(self.correlation_matrix.columns, start=2):
                sheet.cell(row=1, column=col_idx, value=col_name)

            for row_idx, row_name in enumerate(self.correlation_matrix.index, start=2):
                sheet.cell(row=row_idx, column=1, value=row_name)

                for col_idx, col_name in enumerate(self.correlation_matrix.columns, start=2):
                    value = self.correlation_matrix.loc[row_name, col_name]
                    cell = sheet.cell(row=row_idx, column=col_idx, value=value)

                    if pd.notna(value):
                        rgb = (255, 204, 204)  # Default color
                        hex_color = f"{rgb[0]:02X}{rgb[1]:02X}{rgb[2]:02X}"
                        cell.fill = PatternFill(start_color=hex_color, end_color=hex_color, fill_type="solid")

            workbook.save(file_path)
            QMessageBox.information(self, "Export Successful", f"File saved to {file_path}")

        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"An error occurred while exporting: {str(e)}")

    def get_seaborn_qcolor(self, value):
        """Convert Seaborn heatmap color to QColor for Qt tables"""
        if pd.isna(value):
            return QColor(255, 255, 255)  # White for NaN
        cmap = sns.color_palette("RdYlBu", as_cmap=True)
        norm = mcolors.Normalize(vmin=-1, vmax=1)
        rgba = cmap(norm(value))
        rgb = [int(255 * c) for c in rgba[:3]]
        return QColor(*rgb)

    def export_to_excel(self):
        """Export correlation matrix to an Excel file with colors"""
        try:
            file_path, _ = QFileDialog.getSaveFileName(self, "Save File", "", "Excel Files (*.xlsx)")
            if not file_path:
                return  # User canceled

            if not file_path.lower().endswith('.xlsx'):
                file_path += '.xlsx'

            workbook = openpyxl.Workbook()
            std_sheet = workbook.active
            workbook.remove(std_sheet)

            sheet = workbook.create_sheet("Correlation Matrix")

            for col_idx, col_name in enumerate(self.correlation_matrix.columns, start=2):
                sheet.cell(row=1, column=col_idx, value=col_name)

            for row_idx, row_name in enumerate(self.correlation_matrix.index, start=2):
                sheet.cell(row=row_idx, column=1, value=row_name)

                for col_idx, col_name in enumerate(self.correlation_matrix.columns, start=2):
                    value = self.correlation_matrix.loc[row_name, col_name]
                    cell = sheet.cell(row=row_idx, column=col_idx, value=value)

                    if pd.notna(value):
                        qcolor = self.get_seaborn_qcolor(value)
                        rgb = qcolor.getRgb()[:3]
                        hex_color = f"{rgb[0]:02X}{rgb[1]:02X}{rgb[2]:02X}"
                        cell.fill = PatternFill(start_color=hex_color, end_color=hex_color, fill_type="solid")

            workbook.save(file_path)
            QMessageBox.information(self, "Export Successful", f"File saved to {file_path}")

        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"An error occurred while exporting: {str(e)}")


class GenerateCorrelationMatrix(QDialog):
    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.setWindowTitle("Well Zone Correlation Analysis")
        self.setMinimumWidth(1000)
        self.setMinimumHeight(800)
        
        layout = QVBoxLayout()
        
        # Create UWI selector
        UWI_widget = QWidget()
        UWI_layout = QVBoxLayout()
        UWI_layout.addWidget(QLabel("Well UWIs"))
        
        UWI_search = QLineEdit()
        UWI_search.setPlaceholderText("Search UWIs...")
        UWI_search.textChanged.connect(self.filter_UWIs)
        UWI_layout.addWidget(UWI_search)
        
        UWI_lists = QHBoxLayout()
        self.available_UWIs = QListWidget()
        self.available_UWIs.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.selected_UWIs = QListWidget()
        self.selected_UWIs.setSelectionMode(QAbstractItemView.ExtendedSelection)
        
        UWI_buttons = QVBoxLayout()
        btn_select_UWI = QPushButton(">")
        btn_deselect_UWI = QPushButton("<")
        btn_select_all_UWI = QPushButton(">>")
        btn_deselect_all_UWI = QPushButton("<<")
        
        btn_select_UWI.clicked.connect(self.select_UWI)
        btn_deselect_UWI.clicked.connect(self.deselect_UWI)
        btn_select_all_UWI.clicked.connect(self.select_all_UWIs)
        btn_deselect_all_UWI.clicked.connect(self.deselect_all_UWIs)
        
        UWI_buttons.addWidget(btn_select_all_UWI)
        UWI_buttons.addWidget(btn_select_UWI)
        UWI_buttons.addWidget(btn_deselect_UWI)
        UWI_buttons.addWidget(btn_deselect_all_UWI)
        
        UWI_lists.addWidget(self.available_UWIs)
        UWI_lists.addLayout(UWI_buttons)
        UWI_lists.addWidget(self.selected_UWIs)
        UWI_layout.addLayout(UWI_lists)
        UWI_widget.setLayout(UWI_layout)
        
        # Create attribute selector
        attr_widget = QWidget()
        attr_layout = QVBoxLayout()
        attr_layout.addWidget(QLabel("Attributes"))
        
        attr_search = QLineEdit()
        attr_search.setPlaceholderText("Search attributes...")
        attr_search.textChanged.connect(self.filter_attrs)
        attr_layout.addWidget(attr_search)
        
        attr_lists = QHBoxLayout()
        self.available_attrs = QListWidget()
        self.available_attrs.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.selected_attrs = QListWidget()
        self.selected_attrs.setSelectionMode(QAbstractItemView.ExtendedSelection)
        
        attr_buttons = QVBoxLayout()
        btn_select_attr = QPushButton(">")
        btn_deselect_attr = QPushButton("<")
        btn_select_all_attr = QPushButton(">>")
        btn_deselect_all_attr = QPushButton("<<")
        
        btn_select_attr.clicked.connect(self.select_attr)
        btn_deselect_attr.clicked.connect(self.deselect_attr)
        btn_select_all_attr.clicked.connect(self.select_all_attrs)
        btn_deselect_all_attr.clicked.connect(self.deselect_all_attrs)
        
        attr_buttons.addWidget(btn_select_all_attr)
        attr_buttons.addWidget(btn_select_attr)
        attr_buttons.addWidget(btn_deselect_attr)
        attr_buttons.addWidget(btn_deselect_all_attr)
        
        attr_lists.addWidget(self.available_attrs)
        attr_lists.addLayout(attr_buttons)
        attr_lists.addWidget(self.selected_attrs)
        attr_layout.addLayout(attr_lists)
        attr_widget.setLayout(attr_layout)
        
        splitter = QSplitter(Qt.Vertical)
        splitter.addWidget(UWI_widget)
        splitter.addWidget(attr_widget)
        layout.addWidget(splitter)
        
        # Add checkbox for ignoring zeros
        self.ignore_zeros_checkbox = QCheckBox("Ignore Zeros in Correlation")
        layout.addWidget(self.ignore_zeros_checkbox)
        
        btn_run = QPushButton("Run Correlation Analysis")
        btn_run.clicked.connect(self.run_analysis)
        layout.addWidget(btn_run)
        
        self.setLayout(layout)
        self.load_data()

    def filter_UWIs(self, text):
        for i in range(self.available_UWIs.count()):
            item = self.available_UWIs.item(i)
            item.setHidden(text.lower() not in item.text().lower())
    
    def filter_attrs(self, text):
        for i in range(self.available_attrs.count()):
            item = self.available_attrs.item(i)
            item.setHidden(text.lower() not in item.text().lower())
    
    def select_all_UWIs(self):
        items = []
        # Iterate in reverse to avoid index shifting
        for i in range(self.available_UWIs.count() - 1, -1, -1):
            item = self.available_UWIs.item(i)
            if not item.isHidden():
                items.append(self.available_UWIs.takeItem(i))
        for item in reversed(items):  # Add items in original order
            self.selected_UWIs.addItem(item)
    
    def deselect_all_UWIs(self):
        items = []
        for i in range(self.selected_UWIs.count()-1, -1, -1):
            items.append(self.selected_UWIs.takeItem(i))
        for item in reversed(items):  # Add items in original order
            self.available_UWIs.addItem(item)
    
    def select_all_attrs(self):
        items = []
        for i in range(self.available_attrs.count()-1, -1, -1):
            item = self.available_attrs.item(i)
            if not item.isHidden():
                items.append(self.available_attrs.takeItem(i))
        for item in reversed(items):  # Add items in original order
            self.selected_attrs.addItem(item)
    
    def deselect_all_attrs(self):
        items = []
        for i in range(self.selected_attrs.count()-1, -1, -1):
            items.append(self.selected_attrs.takeItem(i))
        for item in reversed(items):  # Add items in original order
            self.available_attrs.addItem(item)
        
    def _is_numeric_column(self, data, col_idx):
        try:
            print(f"\nChecking if column is numeric:")
            for row_idx, row in enumerate(data):
                value = row[col_idx]
            
                # Skip empty values
                if value is None or value == "":
                    continue

                # If it's already a float or int, it's numeric
                if isinstance(value, (float, int)):
                    return True

                # Try to convert any strings
                if isinstance(value, str):
                    value = value.strip()
                    try:
                        float(value)
                        return True
                    except ValueError:
                        return False

            return False
        except Exception as e:
            print(f"Error checking numeric: {e}")
            return False


    def load_data(self):
        """Load available UWIs and attributes from the database"""
        try:
            # Define columns to exclude
            columns_to_exclude = [
                'Zone_Name', 'Zone_Type', 'Attribute_Type',
                'Top_Depth', 'Base_Depth', 'UWI',
                'Top_X_Offset', 'Base_X_Offset', 'Top_Y_Offset', 'Base_Y_Offset',
                'Angle_Top', 'Angle_Base', 'Total_Lateral_Length'
            ]
        
            # Load UWIs into available_UWIs
            print("\nGetting UWIs...")
            UWIs = self.db_manager.get_UWIs()
            print(f"Found UWIs: {UWIs}")
            self.available_UWIs.addItems(UWIs)

            # Fetch well zones
            print("\nFetching Well Zones...")
            well_zones = self.db_manager.fetch_zone_names_by_type("Well")
            print(f"Found Well Zones: {[zone[0] for zone in well_zones]}")

            numeric_columns = []

            # Process each well zone
            for zone_tuple in well_zones:
                zone_name = zone_tuple[0]
                print(f"\nProcessing Zone: {zone_name}")

                try:
                    # Get the table name using the database manager method
                    zone_table_name = self.db_manager.get_table_name_from_zone(zone_name)
                    print(f"Using table: {zone_table_name}")

                    # Fetch zone table data
                    data, columns = self.db_manager.fetch_zone_table_data(zone_table_name)
                    print(f"Columns in {zone_table_name}: {columns}")

                    # Find numeric columns
                    for col in columns:  # Process all columns
                        # Skip excluded columns and UWI
                        if col.upper() == 'UWI' or any(exclude.lower() in col.lower() for exclude in columns_to_exclude):
                            print(f"Skipping excluded column: {col}")
                            continue
                        
                        col_idx = columns.index(col)
                        print(f"Checking Column: {col}")

                        if self._is_numeric_column(data, col_idx):
                            # Add the column with the full table name
                            numeric_columns.append(f"{zone_table_name}.{col}")
                            print(f"Added numeric column: {zone_table_name}.{col}")
                        else:
                            print(f"Column {col} rejected - not numeric")

                except Exception as e:
                    print(f"Error processing zone {zone_name}: {str(e)}")
                    continue

            print(f"\nFinal List of Numeric Attributes: {numeric_columns}")
            self.available_attrs.clear()  # Clear any existing items
            self.available_attrs.addItems(numeric_columns)

        except Exception as e:
            print(f"Error loading data: {str(e)}")
            QMessageBox.critical(self, "Error", f"Error loading data: {str(e)}")

            
    def select_UWI(self):
        items = self.available_UWIs.selectedItems()
        for item in items:
            self.available_UWIs.takeItem(self.available_UWIs.row(item))
            self.selected_UWIs.addItem(item)
            
    def deselect_UWI(self):
        items = self.selected_UWIs.selectedItems()
        for item in items:
            self.selected_UWIs.takeItem(self.selected_UWIs.row(item))
            self.available_UWIs.addItem(item)
            
    def select_attr(self):
        items = self.available_attrs.selectedItems()
        for item in items:
            self.available_attrs.takeItem(self.available_attrs.row(item))
            self.selected_attrs.addItem(item)
            
    def deselect_attr(self):
        items = self.selected_attrs.selectedItems()
        for item in items:
            self.selected_attrs.takeItem(self.selected_attrs.row(item))
            self.available_attrs.addItem(item)

    def validate_numeric_data(self, data):
        """Ensure all data is in correct format for correlation"""
        valid_data = pd.DataFrame()
        
        for column in data.columns:
            # Convert to numeric, forcing errors to NaN
            series = pd.to_numeric(data[column], errors='coerce')
            
            # Only include columns with actual numeric data
            if not series.isna().all():
                valid_data[column] = series
                
            # Print debugging info
            print(f"\nValidating column: {column}")
            print(f"Original dtype: {data[column].dtype}")
            print(f"Converted dtype: {series.dtype}")
            print(f"Number of valid values: {series.count()}")
        
        return valid_data




    def debug_data(self, numeric_data):
        """Debug data issues before correlation"""
        print("\nData Debug Information:")
        for col in numeric_data.columns:
            print(f"\nColumn: {col}")
            print(f"Type: {type(numeric_data[col])}")
            print(f"Shape: {numeric_data[col].shape}")
            print(f"Sample: {numeric_data[col].head()}")
            
            # Check if column is valid for correlation
            if not isinstance(numeric_data[col], (pd.Series, np.ndarray)):
                print(f"WARNING: Column {col} is not in correct format")
                # Convert to proper format
                numeric_data[col] = pd.Series(numeric_data[col])
        
        return numeric_data

            
    def run_analysis(self):
        """Run correlation analysis on selected items"""
        try:
            # Get selected UWIs and attributes
            UWIs = [self.selected_UWIs.item(i).text() for i in range(self.selected_UWIs.count())]
            selected_attrs = [self.selected_attrs.item(i).text() for i in range(self.selected_attrs.count())]

            print("Selected UWIs:", UWIs)
            print("Selected Attributes:", selected_attrs)

            if len(UWIs) == 0 or len(selected_attrs) == 0:
                QMessageBox.warning(self, "Invalid Selection", "Please select at least one UWI and attribute")
                return

            # Build query parts
            attr_selects = []
            tables = set()
            for attr in selected_attrs:
                table_name, col_name = attr.split('.')
                tables.add(table_name)
                # Case insensitive check for UWI columns
                if col_name.upper() == 'UWI':
                    continue  # Skip UWI columns in attribute selection
                attr_selects.append(f'"{table_name}"."{col_name}"')  # Double Quotes

            # Create the JOIN query
            base_table = list(tables)[0]
            joins = []
            for table in tables:
                if table != base_table:
                    joins.append(f"""
                        LEFT JOIN {table} ON 
                        CASE 
                            WHEN EXISTS (SELECT 1 FROM pragma_table_info('{table}') WHERE name = 'UWI')
                            THEN {base_table}.UWI = {table}.UWI
                            ELSE {base_table}.UWI = {table}.UWI
                        END
                    """)

            # Build the complete query
            UWI_placeholders = ', '.join(['?'] * len(UWIs))
            query = f"""
            SELECT 
                CASE 
                    WHEN EXISTS (SELECT 1 FROM pragma_table_info('{base_table}') WHERE name = 'UWI')
                    THEN {base_table}.UWI
                    ELSE {base_table}.UWI
                END as UWI,
                {', '.join(attr_selects)}
            FROM {base_table}
            {' '.join(joins)}
            WHERE {base_table}.UWI IN ({UWI_placeholders})
               OR {base_table}.UWI IN ({UWI_placeholders})
            """

            print("\nExecuting query:")
            print(query)
            query_params = UWIs + UWIs

            # Execute the query
            self.db_manager.connect()
            self.db_manager.cursor.execute(query, query_params)
            results = self.db_manager.cursor.fetchall()
            self.db_manager.disconnect()

            if not results:
                QMessageBox.warning(self, "No Data", "No data found for the selected combinations")
                return

            # Create DataFrame with all data
            columns = ['UWI'] + [attr for attr in selected_attrs if attr.split('.')[1].upper() != 'UWI']
            df = pd.DataFrame(results, columns=columns)
            df = df.set_index('UWI')

            # Convert to numeric, handling errors
            numeric_df = df.apply(pd.to_numeric, errors='coerce')

            # Handle zero values if checkbox is checked
            if self.ignore_zeros_checkbox.isChecked():
                print("Ignoring zero values in correlation calculation")
                # Replace zeros with NaN
                numeric_df = numeric_df.replace(0, np.nan)

            print("\nFinal numeric data:")
            print(f"Shape: {numeric_df.shape}")
            print(f"Columns: {numeric_df.columns.tolist()}")

            # Calculate correlation matrix
            corr_matrix = numeric_df.corr(method='pearson')
        
            # Display results
            dialog = CorrelationDisplayDialog(corr_matrix, numeric_df, self)
            dialog.exec()

        except Exception as e:
            import traceback
            print("Error details:", str(e))
            print("Full traceback:", traceback.format_exc())
            QMessageBox.critical(self, "Error", f"Error running analysis: {str(e)}")

# Example usage and testing:
if __name__ == '__main__':
    import sys
    from PySide6.QtWidgets import QApplication
    
    class MockDBManager:
        def connect(self):
            pass
            
        def disconnect(self):
            pass
            
        def get_UWIs(self):
            return ['UWI1', 'UWI2', 'UWI3', 'UWI4', 'UWI5']
            
        def fetch_zone_names_by_type(self, zone_type):
            return [('Zone1',), ('Zone2',)]
            
        def fetch_zone_table_data(self, zone_name):
            # Mock data
            data = [
                ['UWI1', 100.0, 200.0, 300.0],
                ['UWI2', 150.0, 250.0, 350.0],
                ['UWI3', 175.0, 225.0, 375.0],
                ['UWI4', 125.0, 275.0, 325.0],
                ['UWI5', 160.0, 240.0, 360.0]
            ]
            columns = ['UWI', 'Value1', 'Value2', 'Value3']
            return data, columns

    app = QApplication(sys.argv)
    db_manager = MockDBManager()
    dialog = GenerateCorrelationMatrix(db_manager)
    dialog.show()
    sys.exit(app.exec())