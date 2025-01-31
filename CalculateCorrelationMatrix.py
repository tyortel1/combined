from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                               QTableWidget, QTableWidgetItem, QSplitter,
                               QWidget, QLineEdit, QAbstractItemView, QPushButton, QListWidget, QMessageBox, QFileDialog)
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
        uwi_widget = QWidget()
        uwi_layout = QVBoxLayout()
        uwi_layout.addWidget(QLabel("Well UWIs"))
        
        uwi_search = QLineEdit()
        uwi_search.setPlaceholderText("Search UWIs...")
        uwi_search.textChanged.connect(self.filter_uwis)
        uwi_layout.addWidget(uwi_search)
        
        uwi_lists = QHBoxLayout()
        self.available_uwis = QListWidget()
        self.available_uwis.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.selected_uwis = QListWidget()
        self.selected_uwis.setSelectionMode(QAbstractItemView.ExtendedSelection)
        
        uwi_buttons = QVBoxLayout()
        btn_select_uwi = QPushButton(">")
        btn_deselect_uwi = QPushButton("<")
        btn_select_all_uwi = QPushButton(">>")
        btn_deselect_all_uwi = QPushButton("<<")
        
        btn_select_uwi.clicked.connect(self.select_uwi)
        btn_deselect_uwi.clicked.connect(self.deselect_uwi)
        btn_select_all_uwi.clicked.connect(self.select_all_uwis)
        btn_deselect_all_uwi.clicked.connect(self.deselect_all_uwis)
        
        uwi_buttons.addWidget(btn_select_all_uwi)
        uwi_buttons.addWidget(btn_select_uwi)
        uwi_buttons.addWidget(btn_deselect_uwi)
        uwi_buttons.addWidget(btn_deselect_all_uwi)
        
        uwi_lists.addWidget(self.available_uwis)
        uwi_lists.addLayout(uwi_buttons)
        uwi_lists.addWidget(self.selected_uwis)
        uwi_layout.addLayout(uwi_lists)
        uwi_widget.setLayout(uwi_layout)
        
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
        splitter.addWidget(uwi_widget)
        splitter.addWidget(attr_widget)
        layout.addWidget(splitter)
        
        btn_run = QPushButton("Run Correlation Analysis")
        btn_run.clicked.connect(self.run_analysis)
        layout.addWidget(btn_run)
        
        self.setLayout(layout)
        self.load_data()

    def filter_uwis(self, text):
        for i in range(self.available_uwis.count()):
            item = self.available_uwis.item(i)
            item.setHidden(text.lower() not in item.text().lower())
    
    def filter_attrs(self, text):
        for i in range(self.available_attrs.count()):
            item = self.available_attrs.item(i)
            item.setHidden(text.lower() not in item.text().lower())
    
    def select_all_uwis(self):
        items = []
        # Iterate in reverse to avoid index shifting
        for i in range(self.available_uwis.count() - 1, -1, -1):
            item = self.available_uwis.item(i)
            if not item.isHidden():
                items.append(self.available_uwis.takeItem(i))
        for item in reversed(items):  # Add items in original order
            self.selected_uwis.addItem(item)
    
    def deselect_all_uwis(self):
        items = []
        for i in range(self.selected_uwis.count()-1, -1, -1):
            items.append(self.selected_uwis.takeItem(i))
        for item in reversed(items):  # Add items in original order
            self.available_uwis.addItem(item)
    
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
        
    def load_data(self):
        """Load available UWIs and attributes from the database"""
        try:
            # Load UWIs into available_uwis
            print("\nGetting UWIs...")
            uwis = self.db_manager.get_uwis()  # Fetch all UWIs
            print(f"Found UWIs: {uwis}")
            self.available_uwis.addItems(uwis)  # Add to list

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
                    # Fetch zone table data
                    data, columns = self.db_manager.fetch_zone_table_data(zone_name)
                    print(f"Columns in {zone_name}: {columns}")

                    # Find numeric columns
                    for col in columns[1:]:  # Skip UWI column
                        col_idx = columns.index(col)
                        print(f"Checking Column: {col}")

                        if self._is_numeric_column(data, col_idx):
                            numeric_columns.append(f"{zone_name}.{col}")
                        else:
                            print(f"Column {col} rejected - not numeric")

                except Exception as e:
                    print(f"Skipping zone {zone_name}: {e}")
                    continue

            print(f"\nFinal List of Numeric Attributes: {numeric_columns}")

            # Ensure attributes are correctly added to available_attrs
            self.available_attrs.addItems(numeric_columns)

        except Exception as e:
            print(f"Error loading data: {str(e)}")
            QMessageBox.critical(self, "Error", f"Error loading data: {str(e)}")

    def _is_numeric_column(self, data, col_idx):
        try:
            print(f"\nChecking if column is numeric:")
            for row_idx, row in enumerate(data):
                value = row[col_idx]
                print(f"Value {row_idx}: {value} (type: {type(value)})")

                # Skip empty values
                if value is None or value == "":
                    continue

                # If it's already a float or int, it's numeric
                if isinstance(value, (float, int)):
                    print(f"Found numeric value: {value}")
                    return True

                # Try to convert any strings
                if isinstance(value, str):
                    # Remove any spaces
                    value = value.strip()
                    try:
                        float(value)  # Just try to convert it
                        print(f"Successfully converted {value} to number")
                        return True
                    except ValueError:
                        print(f"Could not convert {value} to number")
                        return False

            return False
        except Exception as e:
            print(f"Error checking numeric: {e}")
            return False
            
    def select_uwi(self):
        items = self.available_uwis.selectedItems()
        for item in items:
            self.available_uwis.takeItem(self.available_uwis.row(item))
            self.selected_uwis.addItem(item)
            
    def deselect_uwi(self):
        items = self.selected_uwis.selectedItems()
        for item in items:
            self.selected_uwis.takeItem(self.selected_uwis.row(item))
            self.available_uwis.addItem(item)
            
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
            
    def run_analysis(self):
        """Run correlation analysis on selected items"""
        # Get selected UWIs
        uwis = [self.selected_uwis.item(i).text() for i in range(self.selected_uwis.count())]
    
        # Get selected attributes
        selected_attrs = [self.selected_attrs.item(i).text() for i in range(self.selected_attrs.count())]

        print("Selected UWIs:", uwis)
        print("Selected Attributes:", selected_attrs)

        if not uwis or not selected_attrs:
            QMessageBox.warning(self, "Invalid Selection", "Please select at least one UWI and attribute")
            return

        try:
            # Create empty DataFrame with UWI as index
            data = pd.DataFrame(index=uwis)

            # Organize attribute selection
            attr_map = {}  # Dictionary to map table names to attribute lists
            for attr in selected_attrs:
                table_name, col_name = attr.split('.')
                if table_name not in attr_map:
                    attr_map[table_name] = []
                attr_map[table_name].append(col_name)

            # Fetch data for all UWIs and attributes
            self.db_manager.connect()
            for table_name, cols in attr_map.items():
                col_str = ', '.join(cols)
                uwi_placeholders = ', '.join(['?'] * len(uwis))
            
                query = f"SELECT UWI, {col_str} FROM {table_name} WHERE UWI IN ({uwi_placeholders})"
                self.db_manager.cursor.execute(query, uwis)
                results = self.db_manager.cursor.fetchall()
            
                if results:
                    temp_df = pd.DataFrame(results, columns=['UWI'] + cols)
                    # Convert numeric strings to float more carefully
                    for col in cols:
                        # Try to convert while preserving zeros
                        try:
                            temp_df[col] = temp_df[col].astype(float)
                        except:
                            temp_df[col] = pd.to_numeric(temp_df[col], errors='coerce')
                        print(f"\nColumn {col} conversion results:")
                        print(f"Sample values: {temp_df[col].head()}")
                        print(f"Number of zeros: {(temp_df[col] == 0).sum()}")
                    temp_df = temp_df.set_index('UWI')
                    # Use suffix to avoid column name conflicts
                    data = data.join(temp_df, how='left', rsuffix=f'_{table_name}')
            
            self.db_manager.disconnect()

            # Ensure data has at least two numeric columns before correlation
            numeric_data = data.apply(pd.to_numeric, errors='coerce')  # Convert to numeric
            numeric_data = numeric_data.dropna(axis=1, how='all')  # Drop empty columns

            # Debug information
            print("\nData Analysis:")
            for col in numeric_data.columns:
                unique_vals = numeric_data[col].unique()
                n_zeros = (numeric_data[col] == 0).sum()
                n_nulls = numeric_data[col].isna().sum()
                print(f"\nColumn: {col}")
                print(f"Unique values: {unique_vals}")
                print(f"Number of zeros: {n_zeros}")
                print(f"Number of nulls: {n_nulls}")
                print(f"Column dtype: {numeric_data[col].dtype}")

            # Check for constant columns (modified to handle zeros properly)
            constant_columns = []
            for col in numeric_data.columns:
                # Get unique values, treating 0 and 0.0 as the same
                unique_vals = pd.Series(numeric_data[col].unique()).dropna()
                if len(unique_vals) == 1:
                    constant_columns.append(f"{col} (value: {unique_vals[0]})")
                elif len(unique_vals) == 0:
                    constant_columns.append(f"{col} (all null)")

            if constant_columns:
                msg = ("The following columns are constant and will show as NaN in correlations:\n" + 
                      "\n".join(constant_columns))
                QMessageBox.information(self, "Constant Columns Detected", msg)

            # Compute correlation matrix, handling zeros properly
            corr_matrix = numeric_data.corr(method='pearson')
        
            # Display the correlation matrix
            dialog = CorrelationDisplayDialog(corr_matrix, numeric_data, self)
            dialog.exec()

        except Exception as e:
            print("Error details:", str(e))
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
            
        def get_uwis(self):
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