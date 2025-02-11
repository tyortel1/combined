import os
import sys
import pandas as pd
from PySide6.QtWidgets import QApplication,QMessageBox, QLineEdit, QDialog, QVBoxLayout, QTableView, QFileDialog, QAbstractItemView, QHBoxLayout, QPushButton, QLabel, QComboBox, QToolBar, QSlider, QWidget, QListWidget, QFormLayout
from PySide6.QtCore import QSize, Qt, Signal, QSettings
from PySide6.QtGui import QStandardItemModel, QStandardItem, QIcon, QFont, QColor, QAction
from ColumnSelectDialog import ColumnSelectionDialog
from PySide6.QtCore import Signal
from HighlightCriteriaDialog import HighlightCriteriaDialog
from CriteriaToZone import CriteriaToZoneDialog
from DecisionTreeDialog import DecisionTreeDialog
from DeleteZone import DeleteZone
from CalculateCorrelations import CalculateCorrelations
import json



class ZoneViewerDialog(QDialog):
    settingsClosed = Signal(dict)
    dataUpdated = Signal(pd.DataFrame)
    newAttributeAdded = Signal(str) 
    zoneNamesUpdated = Signal(list) 

    def __init__(self, db_manager):

        super(ZoneViewerDialog, self).__init__()
        self.setWindowTitle("Zone Properties")
        self.resize(1500, 1200)
         # Set window flags to include the maximize button
        self.setWindowFlags(self.windowFlags() | Qt.WindowMaximizeButtonHint | Qt.WindowMinimizeButtonHint)
        self.db_manager = db_manager

        self.zone_names = []
        self.df = pd.DataFrame()
        self.filtered_df = pd.DataFrame()
        self.selected_UWIs = None
        self.saved_sort_column = None



          # Initially select all columns



    
        self.page_size = 1000  # Number of rows per page
        self.current_page = 0
        self.column_filters = {}
        self.current_config_name = None
        self.settings = False


        self.df_criteria = pd.DataFrame()
        self.highlight_criteria = pd.DataFrame()  

        # Create main vertical layout
        self.main_vertical_layout = QVBoxLayout(self)
        self.setLayout(self.main_vertical_layout)

        # Create and set up the toolbar
        self.toolbar = QToolBar(self)
        self.main_vertical_layout.addWidget(self.toolbar)

        # Load icons
        icon_path = "icons"  # Folder where your icons are stored
        columns_icon = QIcon(os.path.join(icon_path, "Filter-Icon.ico"))
        highlight_icon = QIcon(os.path.join(icon_path, "ListManager_ list properties.ico"))
        criteria_to_zone_icon = QIcon(os.path.join(icon_path, "SavePicks.ico"))
        decision_tree_icon = QIcon(os.path.join(icon_path, "view_tree.ico"))
        correlation_icon = QIcon(os.path.join(icon_path, "Trends.ico"))
        export_icon = QIcon(os.path.join(icon_path, "Save to List_Icon_.ico"))
        delete_zone_icon = QIcon(os.path.join(icon_path, "Delete.ico"))
        next_icon = QIcon(os.path.join(icon_path, "arrow_right.ico"))  # Replace with the path to your next icon
        prev_icon = QIcon(os.path.join(icon_path, "arrow_left.ico"))  # Replace with the path to your previous icon

        # Create actions
        self.column_action = QAction(columns_icon, "Select Column Filter", self)
        self.column_action.triggered.connect(self.open_column_selection_dialog)
        self.highlight_action = QAction(highlight_icon, "Highlight", self)
        self.highlight_action.triggered.connect(self.highlight)
        self.criteria_to_zone_action = QAction(criteria_to_zone_icon, "Save To Zone", self)
        self.criteria_to_zone_action.triggered.connect(self.open_criteria_to_zone_dialog)
        self.decision_tree_action = QAction(decision_tree_icon, "Decision Tree", self)
        self.decision_tree_action.triggered.connect(self.open_decision_tree_dialog)
        self.correlation_action = QAction(correlation_icon, "Correlations", self)
        self.correlation_action.triggered.connect(self.correlation_dialog)
        self.export_action = QAction(export_icon, "Export", self)
        self.export_action.triggered.connect(self.export_current_view)
        self.delete_zone_action = QAction(delete_zone_icon, "Delete Zone", self)
        self.delete_zone_action.triggered.connect(self.delete_zone)
        self.next_action = QAction(next_icon, "Next Page", self)
        self.next_action.triggered.connect(self.next_page)
        self.prev_action = QAction(prev_icon, "Previous Page", self)
        self.prev_action.triggered.connect(self.prev_page)

                # Add a label and combo box for rows per page selection
        rows_per_page_label = QLabel("Rows per page:", self)
        self.rows_per_page_combo = QComboBox(self)
        self.rows_per_page_combo.addItems(["100", "500", "1000", "2000", "5000"])
        self.rows_per_page_combo.setCurrentText("1000")
        self.rows_per_page_combo.currentIndexChanged.connect(self.change_rows_per_page)

                # Pagination layout

       
        self.page_label = QLabel(self)

  

        # Add actions to the toolbar
        self.toolbar.addAction(self.column_action)
        self.toolbar.addAction(self.highlight_action)
        self.toolbar.addAction(self.criteria_to_zone_action)
        self.toolbar.addAction(self.decision_tree_action)
        self.toolbar.addAction(self.correlation_action)
        self.toolbar.addAction(self.export_action)
        self.toolbar.addAction(self.delete_zone_action)
        self.toolbar.addWidget(self.page_label)
        self.toolbar.addAction(self.prev_action)
        self.toolbar.addAction(self.next_action)
        
        self.toolbar.addWidget(self.rows_per_page_combo)
        self.toolbar.addWidget(rows_per_page_label)

        # Create horizontal layout for filters and table
        self.main_layout = QHBoxLayout()
        self.main_vertical_layout.addLayout(self.main_layout)

        # Left widget for filters, criteria dropdowns, and column dimensions
        self.left_widget = QWidget()
        self.left_widget.setFixedWidth(200)
        self.left_layout = QVBoxLayout(self.left_widget)
        self.left_layout.setContentsMargins(10, 10, 10, 10)
        self.left_layout.setSpacing(5)
        self.main_layout.addWidget(self.left_widget)



        # Filter layout
        self.filter_layout = QVBoxLayout()
        self.filter_layout.setSpacing(5)

        self.filter_layout.addWidget(QLabel("Saved Conifurations:"))
        self.column_filter_dropdown = QComboBox(self)
        self.column_filter_dropdown.addItem("Select Saved Configuration") 
        self.column_filter_dropdown.addItems(self.column_filters.keys())
        self.column_filter_dropdown.currentIndexChanged.connect(self.apply_column_filter)
        
        self.filter_layout.addWidget(self.column_filter_dropdown)


                # Zone Type Filter
        self.zone_type_filter_label = QLabel("Filter by Zone Type")
        self.zone_type_filter = QComboBox(self)
        self.zone_type_filter.setFixedSize(QSize(180, 25))
        self.zone_type_filter.addItem("All")
        sorted_zone_types = sorted(["Well", "Zone", "Intersections"])
        self.zone_type_filter.addItems(sorted_zone_types)
        self.zone_type_filter.setCurrentText("All")  # Set initial value
        self.zone_type_filter.currentTextChanged.connect(self.on_zone_type_selected)
        self.filter_layout.addWidget(self.zone_type_filter_label)
        self.filter_layout.addWidget(self.zone_type_filter)

                # Zone Name Filter
        self.zone_name_filter_label = QLabel("Filter by Zone Name")
        self.zone_name_filter = QComboBox(self)
        self.zone_name_filter.setFixedSize(QSize(180, 25))
        self.zone_name_filter.addItem("Select Zone")
        sorted_zone_names = sorted(self.zone_names)
        self.zone_name_filter.addItems(sorted_zone_names)
        self.zone_name_filter.setCurrentText("Select Zone")  # Set initial value
        self.zone_name_filter.currentTextChanged.connect(self.on_zone_selected)
        self.filter_layout.addWidget(self.zone_name_filter_label)
        self.filter_layout.addWidget(self.zone_name_filter)




        # Search bar with label
        self.filter_layout.addWidget(QLabel("Search:"))
        self.search_bar = QLineEdit(self)
        self.search_bar.setPlaceholderText("Search...")
        self.search_bar.returnPressed.connect(self.apply_search_filter)
        self.filter_layout.addWidget(self.search_bar)

                # UWI Filter
        self.UWI_filter_label = QLabel("Filter by UWI")
        self.UWI_filter = QComboBox(self)
        self.UWI_filter.setFixedSize(QSize(180, 25))
        self.UWI_filter.addItem("All")
      

        self.UWI_filter.setCurrentText("All")  # Set initial value
        self.UWI_filter.currentTextChanged.connect(self.apply_filters)
        self.filter_layout.addWidget(self.UWI_filter_label)
        self.filter_layout.addWidget(self.UWI_filter)

        # Criteria dropdowns
        self.filter_criteria_dropdown = QComboBox(self)
        self.filter_criteria_dropdown.addItem("None")
        self.filter_criteria_dropdown.currentIndexChanged.connect(self.apply_filters)

        self.highlight_criteria_dropdown = QComboBox(self)
        self.highlight_criteria_dropdown.addItem("None")
        self.highlight_criteria_dropdown.currentIndexChanged.connect(self.apply_filters)


     










        self.filter_layout.addWidget(QLabel("Filter by Criteria:"))
        self.filter_layout.addWidget(self.filter_criteria_dropdown)
        self.filter_layout.addWidget(QLabel("Highlight by Criteria:"))
        self.filter_layout.addWidget(self.highlight_criteria_dropdown)

        self.left_layout.addLayout(self.filter_layout)

        # Add column width, height, and font size sliders
        self.dimensions_layout = QFormLayout()
        self.column_width_slider = QSlider(Qt.Horizontal)
        self.column_width_slider.setRange(20, 200)
        self.column_width_slider.setValue(100)
        self.column_width_slider.valueChanged.connect(self.apply_column_dimensions)

        self.row_height_slider = QSlider(Qt.Horizontal)
        self.row_height_slider.setRange(10, 50)
        self.row_height_slider.setValue(20)
        self.row_height_slider.valueChanged.connect(self.apply_column_dimensions)

        self.font_size_slider = QSlider(Qt.Horizontal)
        self.font_size_slider.setRange(3, 16)
        self.font_size_slider.setValue(8)
        self.font_size_slider.valueChanged.connect(self.apply_column_dimensions)

        self.dimensions_layout.addRow("Width", self.column_width_slider)
        self.dimensions_layout.addRow("Height", self.row_height_slider)
        self.dimensions_layout.addRow("Font", self.font_size_slider)
        self.left_layout.addLayout(self.dimensions_layout)

        # Add a stretch at the bottom to push everything up
        self.left_layout.addStretch()

        # Right layout for table view and pagination
        self.right_layout = QVBoxLayout()
        self.main_layout.addLayout(self.right_layout)
        # Create and set up the table view


        self.table_view = QTableView(self)
       
    
        
        # Set a smaller font for the table view
        font = QFont()
        font.setPointSize(8)  # Adjust the font size as needed
        self.table_view.setFont(font)
        self.table_view.setSortingEnabled(True)

        # Connect the sort indicator changed signal to the custom handler
        self.table_view.horizontalHeader().sortIndicatorChanged.connect(self.handle_sort_indicator_changed)

        # Add the table view to the layout
        self.right_layout.addWidget(self.table_view)

        self.load_saved_configurations()
        self.load_settings()

        






    def initialize_viewer(self, zone_type=None):
        """
        Initialize the ZoneViewer with the selected zone type and load data.
        """
        try:
            # Fetch initial zone names
            print(zone_type)


            results = self.db_manager.fetch_zone_names_by_type(zone_type)
            if self.settings:
                # Block signals before setting the text
                self.zone_type_filter.blockSignals(True)
                self.zone_type_filter.setCurrentText(self.zone_type)
                # Unblock signals after setting the text
                self.zone_type_filter.blockSignals(False)

            print(results)
            self.zone_names = [row[0] for row in results]  # Extract ZoneName from tuples
        except Exception as e:
            print(f"Error fetching zone names: {e}")
            self.zone_names = []

        # Call populate_zone_names method if UI is already set up
        if hasattr(self, 'zone_name_filter'):
            self.populate_zone_names(zone_type)

    def on_zone_type_selected(self):
        """
        Clear zone names and repopulate them when a zone type is selected.
        """
        selected_zone_type = self.zone_type_filter.currentText()
        print(f"Selected zone type: {selected_zone_type}")
        self.populate_zone_names(selected_zone_type)
       


    def populate_zone_names(self, zone_type=None):
        """
        Populate zone names in the UI based on the selected type.
        Parameters:
            zone_type (str): The type of zones to fetch (e.g., 'Zones', 'Intersections', 'Well').
        """
        try:
            # Block signals to avoid triggering connected methods
            self.zone_name_filter.blockSignals(True)

            # Fetch zone names from the database based on the zone type
            results = self.db_manager.fetch_zone_names_by_type(zone_type)
            self.zone_names = [row[0] for row in results]  # Extract ZoneName from tuples

            # Populate zone names in the dropdown
            self.zone_name_filter.clear()
            self.zone_name_filter.addItem("Select Zone")  # Default option
            self.zone_name_filter.addItems(sorted(self.zone_names))

        
            # Optional: Set a default selection
            if self.settings:
                self.zone_name_filter.setCurrentText(self.zone_name_filter_text)
                self.on_zone_selected()
            else:
                self.zone_name_filter.setCurrentText("Select Zone")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load zone names: {str(e)}")
            print(f"Error in populate_zone_names: {e}")
        finally:
            # Unblock signals after changes are done
            self.zone_name_filter.blockSignals(False)



    def on_zone_selected(self):
        """
        Load data and update UI elements when a zone is selected.
        """
        selected_zone = self.zone_name_filter.currentText().strip()
        print(f"Selected zone: {selected_zone}")
    
        # If "All" or "Select Zone" is selected, clear data
        if selected_zone in ["Select Zone", None, ""]:
            print("No valid zone selected. Clearing data.")
            self.df = pd.DataFrame()
            self.selected_UWIs = []
            self.selected_columns = []
            self.UWI_filter.clear()
            self.UWI_filter.addItem("All")# Reset pagination
            self.load_data()  # Clear the table view
            self.update_page_label() 

            return
    
        try:
            print(selected_zone)
            normalized_zone_name = selected_zone.replace(' ', '_')
            # Fetch entire table data for the selected zone
            data, columns = self.db_manager.fetch_zone_table_data(normalized_zone_name)
        
            # Create DataFrame
            self.df = pd.DataFrame(data, columns=columns)
            print("Loaded DataFrame:")
            print(self.df)
        
            # Validate DataFrame
            if self.df.empty:
                QMessageBox.warning(self, "No Data", f"No data found for zone '{selected_zone}'")
                return
        
            # Update UI elements
            self.selected_UWIs = self.get_unique_UWIs_from_dataframe()
            self.selected_columns = self.df.columns.tolist()
                        # Update UWI filter
            self.UWI_filter.blockSignals(True)
            self.UWI_filter.clear()
            self.UWI_filter.addItem("All")
            if "UWI" in self.df.columns:
                unique_UWIs = sorted(self.df["UWI"].unique().tolist())
                self.UWI_filter.addItems([str(UWI) for UWI in unique_UWIs])
            self.UWI_filter.blockSignals(False)
        

            self.apply_filters()
            self.load_data()
        
        except Exception as e:
            QMessageBox.critical(
                self, 
                "Error", 
                f"Failed to load data for zone '{selected_zone}': {str(e)}"
            )
            # Optional: log the full traceback
            import traceback
            traceback.print_exc()
    def get_unique_UWIs_from_dataframe(self):
        """
        Fetch unique UWIs from the initial DataFrame.

        Returns:
            list: A sorted list of unique UWIs.
        """
        if 'UWI' in self.df.columns:
            return sorted(self.df['UWI'].unique().tolist())
        else:
            QMessageBox.warning(self, "Warning", "The UWI column is missing in the data.")
            return []      
        
        
 

    def update_zone_data(self):
        """Update zone data when the zone type changes."""
        self.load_zone_data()
        self.update_filtered_data()

    def update_filtered_data(self):
        """Apply filters and reload the table data."""
        zone_name = self.zone_name_filter.currentText()
        zone_type = self.zone_type_filter.currentText()

        if zone_name == "Select Zone":
            self.filtered_df = pd.DataFrame()
            return

        # Apply filters based on selected zone name and type
        if zone_name != "Select Zone":
            self.filtered_df = self.df[(self.df["Zone Name"] == zone_name) & 
                                       (self.df["Zone Type"] == zone_type)]
        else:
            self.filtered_df = []

        # Update the table view
        self.load_data()       
        
    def handle_sort_indicator_changed(self, logicalIndex, order):
        # Get the column name based on the logical index
        sort_column = self.table_view.horizontalHeader().model().headerData(logicalIndex, Qt.Horizontal)

        # Save the current sort column and order
        self.saved_sort_column = sort_column
        self.saved_sort_order = Qt.AscendingOrder if order == Qt.AscendingOrder else Qt.DescendingOrder

        # Determine if the column is numeric and sort accordingly
        if pd.api.types.is_numeric_dtype(self.filtered_df[sort_column]):
            self.filtered_df.sort_values(
                by=sort_column,
                ascending=order == Qt.AscendingOrder,
                inplace=True,
                key=pd.to_numeric
            )
        else:
            self.filtered_df.sort_values(
                by=sort_column,
                ascending=order == Qt.AscendingOrder,
                inplace=True
            )

        # Reset the current page and reload the data
        self.current_page = 0
        self.update_page_label()
        self.load_data()
        




    def change_rows_per_page(self):
        self.page_size = int(self.rows_per_page_combo.currentText())
        self.current_page = 0  # Reset to the first page
        self.update_page_label()
        self.load_data()   
        
    def apply_search_filter(self):
        search_text = self.search_bar.text().strip().lower()

        if search_text:
            # Check each row if any of the column values contain the search text
            search_condition = self.filtered_df.apply(
                lambda row: row.astype(str).str.lower().str.contains(search_text).any(), axis=1
            )
            self.filtered_df = self.filtered_df[search_condition]
        else:
            # If search text is cleared, reapply filters without the search condition
            self.filtered_df = self.df.copy()  # Reset to the original DataFrame
            self.apply_filters()  # Reapply any saved filters and sorting

        # Reset the current page and update the view
        self.current_page = 0
        self.update_page_label()
        self.load_data()

    def apply_column_filter(self):
        selected_filter = self.column_filter_dropdown.currentText()

        if selected_filter == "Select Saved Configuration":
            # Default to all columns if "Select Saved Configuration" is selected
            self.selected_columns = self.df.columns.tolist()
            print("Defaulting to all columns")  # Debugging statement
        elif selected_filter in self.column_filters:
            # Apply the filter based on the selected configuration
            self.selected_columns = self.column_filters[selected_filter]
            print(f"Selected columns for filter: {self.selected_columns}")  # Debugging statement
        else:
            # If the filter is not found, log or handle this case if necessary
            print(f"Filter '{selected_filter}' not found in column_filters")  # Debugging statement

        # Reload the data to apply the selected columns
        self.load_data()


    def apply_columns(self, columns):
        """Method to show or hide columns based on the selected filter."""
        self.selected_columns = columns
        self.load_data() 


        
    def apply_filters(self):
        # Clear search bar
        self.search_bar.setText("")

        # Block signals to prevent multiple updates
        filters_to_block = [
            self.UWI_filter, 
 
            self.zone_name_filter, 
            self.zone_type_filter, 
            self.filter_criteria_dropdown, 
            self.highlight_criteria_dropdown, 
     
        ]
    
        for filter_widget in filters_to_block:
            filter_widget.blockSignals(True)

        try:
            # Get the selected zone name

            filtered_df = self.df.copy()

            # Extract filter texts
            UWI_filter_text = self.UWI_filter.currentText().strip().lower()
           
            zone_type_filter_text = self.zone_type_filter.currentText().strip().lower()

            # Apply UWI filter
            if UWI_filter_text != "all":
                filtered_df = filtered_df[
                    filtered_df['UWI'].astype(str).str.lower().str.contains(UWI_filter_text)
                ]



            # Update filtered DataFrame
            self.filtered_df = filtered_df

            # Apply additional filters
            self.apply_saved_filter()
            self.apply_saved_highlight()

            # Sorting
            # Use saved sorting column and order
            if hasattr(self, 'saved_sort_column') and self.saved_sort_column:
                ascending = self.saved_sort_order == Qt.AscendingOrder
                if pd.api.types.is_numeric_dtype(self.filtered_df[self.saved_sort_column]):
                    self.filtered_df.sort_values(
                        by=self.saved_sort_column,
                        ascending=ascending,
                        inplace=True,
                        key=pd.to_numeric
                    )
                else:
                    self.filtered_df.sort_values(
                        by=self.saved_sort_column,
                        ascending=ascending,
                        inplace=True)

        finally:
            # Unblock signals 
            for filter_widget in filters_to_block:
                filter_widget.blockSignals(False)
    
        # Reset pagination and load data
        self.current_page = 0
        self.update_page_label()
        self.load_data()

    def load_data(self):
        model = QStandardItemModel()

        # Ensure 'HighlightColor' is included in the DataFrame if it exists
        if 'HighlightColor' in self.filtered_df.columns:
            columns_to_include = self.selected_columns + ['HighlightColor'] if 'HighlightColor' not in self.selected_columns else self.selected_columns
        else:
            columns_to_include = self.selected_columns
        # Filter columns based on selection and available columns in the filtered DataFrame
        available_columns = [col for col in columns_to_include if col in self.filtered_df.columns]
        filtered_df = self.filtered_df[available_columns]

        # Set headers (excluding 'HighlightColor' if it should not be displayed)
        model.setHorizontalHeaderLabels([col for col in filtered_df.columns if col != 'HighlightColor'])

        # Calculate the start and end indices for the current page
        start_idx = self.current_page * self.page_size
        end_idx = min(start_idx + self.page_size, len(filtered_df))
        page_data = filtered_df.iloc[start_idx:end_idx]
        page_data = page_data.map(lambda x: f"{x:.2f}" if isinstance(x, (int, float)) else x)
        # Add rows to the model
        for _, row in page_data.iterrows():
            items = [QStandardItem(str(field)) for field in row if field != row.get('HighlightColor')]

            # Apply highlight color
            color = row.get('HighlightColor', None)
       
            if pd.notna(color):  # Check if the color is not NaN
                qcolor = QColor(color)
                for item in items:
                    item.setBackground(qcolor)

            model.appendRow(items)

        # Set the model to the table view
        self.table_view.setModel(model)
        self.apply_column_dimensions()


    def open_decision_tree_dialog(self):
        dialog = DecisionTreeDialog(self.df, self)
    
        # Remove or comment out the line trying to connect to dataUpdated
        # dialog.dataUpdated.connect(self.update_dataframe)  # Remove this line
    
        # Connect only the criteriaGenerated signal
        dialog.criteriaGenerated.connect(self.handle_new_criteria)
    
        dialog.show()



    def highlight(self):
        dialog = HighlightCriteriaDialog(
            columns=self.df.columns.tolist(), 
            existing_criteria_df=self.df_criteria,
            parent=self
        )

        if dialog.exec_() == QDialog.Accepted:
            self.df_criteria = dialog.criteria_df
        
            criteria_name = dialog.criteria_name
    
            
            # Ensure the criteria name is in the dropdowns if not already present
            highlight_names = [self.highlight_criteria_dropdown.itemText(i) for i in range(self.highlight_criteria_dropdown.count())]
            filter_names = [self.filter_criteria_dropdown.itemText(i) for i in range(self.filter_criteria_dropdown.count())]
            
            if criteria_name not in highlight_names:
                self.highlight_criteria_dropdown.addItem(criteria_name)
                
            if criteria_name not in filter_names:
                self.filter_criteria_dropdown.addItem(criteria_name)
    
            # Reload data if the current text matches the criteria_name
            if self.highlight_criteria_dropdown.currentText() == criteria_name or \
                self.filter_criteria_dropdown.currentText() == criteria_name:
                self.load_data()

      
        self.apply_filters()



    def apply_saved_filter(self):
        selected_filter = self.filter_criteria_dropdown.currentText()

        if selected_filter != "None":
            if not self.df_criteria.empty:
                criteria = self.df_criteria[self.df_criteria['Name'] == selected_filter]
                if not criteria.empty:
                    self.filtered_df = self.apply_criteria_to_df(self.filtered_df, criteria)
                else:
                    print(f"No valid filter found for selection: '{selected_filter}'")
            else:
                print(f"No criteria data available")
                self.apply_other_filters()


        # Reset to the first page after applying filters
        self.current_page = 0
        self.update_page_label()

        # Reload the data to reflect the applied filters
   

    def apply_criteria_to_df(self, df, criteria):
        """Apply a set of criteria to filter the DataFrame."""
        result_df = df.copy()
        temp_df = pd.DataFrame()
    
        for i, criterion in criteria.iterrows():
            column = criterion['Column']
            operator = criterion['Operator']
            value = criterion['Value']
            logical_op = criterion['Logical Operator']

            # Apply the filter condition based on the operator
            if operator == '=':
                mask = result_df[column] == value
            elif operator == '>':
                mask = result_df[column] > float(value)
            elif operator == '<':
                mask = result_df[column] < float(value)
            elif operator == '>=':
                mask = result_df[column] >= float(value)
            elif operator == '<=':
                mask = result_df[column] <= float(value)
            elif operator == '!=':
                mask = result_df[column] != value

            if i == 0 or logical_op == 'AND':
                result_df = result_df[mask]
            elif logical_op == 'OR':
                temp_df = pd.concat([temp_df, result_df[mask]])
            
        # Combine the results of OR operations
        result_df = pd.concat([result_df, temp_df]).drop_duplicates()
        print(result_df)
        return result_df


    def apply_saved_highlight(self):
        selected_highlight = self.highlight_criteria_dropdown.currentText()

        if selected_highlight == "None":
            # Remove the 'HighlightColor' column if it exists
            if 'HighlightColor' in self.filtered_df.columns:
                self.filtered_df = self.filtered_df.drop(columns=['HighlightColor'])
            self.highlight_criteria = pd.DataFrame()
        elif not self.df_criteria.empty:
            self.highlight_criteria = self.df_criteria[self.df_criteria['Name'] == selected_highlight]
            if self.highlight_criteria.empty:
                print(f"No valid highlight found for selection: '{selected_highlight}'")
                # Remove the 'HighlightColor' column if no valid criteria found
                if 'HighlightColor' in self.filtered_df.columns:
                    self.filtered_df = self.filtered_df.drop(columns=['HighlightColor'])
            else:
                print(f"Applying highlight criteria: {self.highlight_criteria.to_dict('records')}")
                self.apply_criteria_to_data()  # Apply the criteria to the data
        else:
            print("No criteria data available")
            # Remove the 'HighlightColor' column if no criteria data available
            if 'HighlightColor' in self.filtered_df.columns:
                self.filtered_df = self.filtered_df.drop(columns=['HighlightColor'])


    def apply_criteria_to_data(self):
        if self.highlight_criteria.empty:
            return

        # Ensure 'HighlightColor' column is reset or created
        self.filtered_df['HighlightColor'] = None

        # Start with a mask that is all True, then narrow it down
        final_mask = pd.Series(True, index=self.filtered_df.index)

        # Iterate over each criterion in the highlight criteria DataFrame
        for i, criterion in self.highlight_criteria.iterrows():
            column = criterion['Column']
            operator = criterion['Operator']
            value = criterion['Value']
            color = criterion['Color']
            logical_operator = criterion.get('Logical Operator', 'AND')

            # Apply the condition based on the operator
            if operator == '=':
                mask = self.filtered_df[column] == value
            elif operator == '>':
                mask = self.filtered_df[column] > float(value)
            elif operator == '<':
                mask = self.filtered_df[column] < float(value)
            elif operator == '>=':
                mask = self.filtered_df[column] >= float(value)
            elif operator == '<=':
                mask = self.filtered_df[column] <= float(value)
            elif operator == '!=':
                mask = self.filtered_df[column] != value
            else:
                mask = pd.Series(False, index=self.filtered_df.index)  # If unknown operator, default to False

            # Combine masks using the logical operator
            if i == 0 or logical_operator == 'AND':
                final_mask &= mask
            elif logical_operator == 'OR':
                final_mask |= mask

        # Apply the color to rows that match the final mask
        self.filtered_df.loc[final_mask, 'HighlightColor'] = color


    def update_page_label(self):




        total_pages = (len(self.filtered_df) + self.page_size - 1) // self.page_size
        self.page_label.setText(f"Page {self.current_page + 1} of {total_pages}")

    def next_page(self):
        if (self.current_page + 1) * self.page_size < len(self.filtered_df):
            self.current_page += 1
            self.update_page_label()
            self.load_data()

    def prev_page(self):
        if self.current_page > 0:
            self.current_page -= 1
            self.update_page_label()
            self.load_data()

    def open_column_selection_dialog(self):
        self.current_config_name = self.column_filter_dropdown.currentText()
    
        dialog = ColumnSelectionDialog(
            all_columns=self.df.columns.tolist(),
            selected_columns=self.selected_columns,
            column_filters=self.column_filters,
            current_config_name=self.current_config_name,
            parent=self
        )
    
        if dialog.exec_() == QDialog.Accepted:
            # Update column filters
            self.column_filters = dialog.column_filters
            self.current_config_name = dialog.current_config_name
        
            # Save settings after update
            self.save_settings()

            # Refresh dropdown
            self.column_filter_dropdown.clear()
            self.column_filter_dropdown.addItem("Select Saved Configuration")
            self.column_filter_dropdown.addItems(self.column_filters.keys())
        
            if self.current_config_name and self.current_config_name in self.column_filters:
                self.column_filter_dropdown.setCurrentText(self.current_config_name)
                self.selected_columns = self.column_filters[self.current_config_name]
            else:
                self.column_filter_dropdown.setCurrentText("Select Saved Configuration")
                self.selected_columns = dialog.get_selected_columns()
        
            self.load_data()

    def apply_column_dimensions(self):
        column_width = self.column_width_slider.value()
        row_height = self.row_height_slider.value()
        font_size = self.font_size_slider.value()

        # Check if model exists before trying to access it
        if self.table_view.model() is not None:
            for column in range(self.table_view.model().columnCount()):
                self.table_view.setColumnWidth(column, column_width)
    
        self.table_view.verticalHeader().setDefaultSectionSize(row_height)

        # Set the font size for the table view
        font = QFont()
        font.setPointSize(font_size)
        self.table_view.setFont(font)

    def export_current_view(self):
        # Open a file dialog to choose the export file path
        file_path, _ = QFileDialog.getSaveFileName(self, "Export Current View", "", "CSV Files (*.csv);;All Files (*)")

        if file_path:  # If the user did not cancel
            start_idx = self.current_page * self.page_size
            end_idx = min(start_idx + self.page_size, len(self.filtered_df))
            page_data = self.filtered_df.iloc[start_idx:end_idx]

            page_data.to_csv(file_path, index=False)

    def save_settings(self):
        if not self.current_config_name or self.current_config_name == "Select Saved Configuration":
            return
    
        settings = QSettings('ZoneApp', 'ZoneViewer')
        settings.beginGroup(self.current_config_name)
    
        # Save column filters and configuration
        settings.setValue('column_filters', json.dumps(self.column_filters))
        settings.setValue('selected_columns', json.dumps(self.selected_columns))
        settings.setValue('current_config', self.current_config_name)
    
        # Save dropdown states
        settings.setValue('zone_type_filter', self.zone_type_filter.currentText())
        settings.setValue('zone_name_filter', self.zone_name_filter.currentText())
        settings.setValue('UWI_filter', self.UWI_filter.currentText())
        settings.setValue('rows_per_page', self.rows_per_page_combo.currentText())
        settings.setValue('filter_criteria', self.filter_criteria_dropdown.currentText())
        settings.setValue('highlight_criteria', self.highlight_criteria_dropdown.currentText())
    
        # Save slider values
        settings.setValue('column_width', self.column_width_slider.value())
        settings.setValue('row_height', self.row_height_slider.value())
        settings.setValue('font_size', self.font_size_slider.value())
    
        # Save criteria
        if not self.df_criteria.empty:
            settings.setValue('df_criteria', self.df_criteria.to_json())
    
        settings.endGroup()
    
        # Save the name of the last used configuration
        settings.setValue('last_config', self.current_config_name)
        settings.sync()
        
    def load_settings(self):
        self.settings = True
        settings = QSettings('ZoneApp', 'ZoneViewer')
        last_config_name = settings.value('last_config')
        print(f"Loading settings, last config: {last_config_name}")

        # If no last config, initialize the viewer
        if not last_config_name:
            print("No last config found")
            self.initialize_viewer()
            return

        # Initialize all variables with defaults
        self.current_config_name = last_config_name or "DefaultConfig"
        self.column_filters = {}
        self.selected_columns = []
        self.zone_type_filter_text = "All"
        self.zone_name_filter_text = "Select Zone"
        self.UWI_filter_text = "All"
        self.rows_per_page = "1000"
        self.filter_criteria_text = "None"
        self.highlight_criteria_text = "None"
        self.column_width = 100
        self.row_height = 20
        self.font_size = 8
        self.df_criteria = pd.DataFrame()

        if last_config_name:
            settings.beginGroup(last_config_name)

            # Block signals for UI components
            widgets_to_block = [
                self.UWI_filter,
                self.zone_name_filter,
                self.zone_type_filter,
                self.filter_criteria_dropdown,
                self.highlight_criteria_dropdown,
                self.column_width_slider,
                self.row_height_slider,
                self.font_size_slider
            ]
            for widget in widgets_to_block:
                widget.blockSignals(True)

            try:
                # Load settings with defaults if keys are missing
                self.column_filters = json.loads(settings.value('column_filters', '{}'))
                self.selected_columns = json.loads(settings.value('selected_columns', '[]'))
                self.zone_type_filter_text = settings.value('zone_type_filter', 'All')
                self.zone_name_filter_text = settings.value('zone_name_filter', 'Select Zone')
                self.UWI_filter_text = settings.value('UWI_filter', 'All')
                self.rows_per_page = settings.value('rows_per_page', '1000')
                self.filter_criteria_text = settings.value('filter_criteria', 'None')
                self.highlight_criteria_text = settings.value('highlight_criteria', 'None')
                self.column_width = int(settings.value('column_width', 100))
                self.row_height = int(settings.value('row_height', 20))
                self.font_size = int(settings.value('font_size', 8))
                criteria_json = settings.value('df_criteria', '{}')
                if criteria_json:
                    self.df_criteria = pd.read_json(criteria_json)
            except Exception as e:
                print(f"Error loading settings: {e}")
            finally:
                # Unblock signals
                for widget in widgets_to_block:
                    widget.blockSignals(False)
                settings.endGroup()

        self.initialize_viewer(self.zone_type_filter_text)

        # Apply loaded settings to the UI
        self.zone_type_filter.setCurrentText(self.zone_type_filter_text)
        self.zone_name_filter.setCurrentText(self.zone_name_filter_text)
        self.UWI_filter.setCurrentText(self.UWI_filter_text)
        self.rows_per_page_combo.setCurrentText(self.rows_per_page)
        self.filter_criteria_dropdown.setCurrentText(self.filter_criteria_text)
        self.highlight_criteria_dropdown.setCurrentText(self.highlight_criteria_text)
        self.column_width_slider.setValue(self.column_width)
        self.row_height_slider.setValue(self.row_height)
        self.font_size_slider.setValue(self.font_size)

        self.apply_column_dimensions()
        self.apply_filters()
        self.load_data()
        self.settings = False

    def load_saved_configurations(self):
        settings = QSettings('ZoneApp', 'ZoneViewer')
        saved_configs = []
    
        # Get all groups except special keys
        for key in settings.childGroups():
            if key != 'last_config':
                saved_configs.append(key)
            
        self.column_filter_dropdown.clear()
        self.column_filter_dropdown.addItem("Select Saved Configuration")
        self.column_filter_dropdown.addItems(saved_configs)
    
        last_config = settings.value('last_config')
        if last_config and last_config in saved_configs:
            self.column_filter_dropdown.setCurrentText(last_config)
            self.current_config_name = last_config

    def open_criteria_to_zone_dialog(self):
        if self.df_criteria.empty:
            QMessageBox.information(self, "No Criteria", "No criteria available to save. Please define criteria before proceeding.")
            return

        dialog = CriteriaToZoneDialog(self.df, self.df_criteria, self)
        if dialog.exec_() == QDialog.Accepted:
            self.df = dialog.df
            # Emit the updated DataFrame and new attribute name
            self.dataUpdated.emit(self.df)
            self.newAttributeAdded.emit(dialog.attribute_name)

            # Update the local view
            self.apply_filters()

    # Usage within your main application
        # Usage within your main application
    def open_decision_tree_dialog(self):
        dialog = DecisionTreeDialog(self.df, self)
    
        # Remove or comment out the line trying to connect to dataUpdated
        # dialog.dataUpdated.connect(self.update_dataframe)  # Remove this line
    
        # Connect only the criteriaGenerated signal
        dialog.criteriaGenerated.connect(self.handle_new_criteria)
    
        dialog.show()

    def apply_saved_filter(self):
        selected_filter = self.filter_criteria_dropdown.currentText()
        print(f"Applying filter: '{selected_filter}'")
        print(f"Criteria DataFrame: {self.df_criteria}")

        if selected_filter == "None" or selected_filter == "":
            # If no filter is selected, return the original filtered DataFrame
            return

        if not self.df_criteria.empty:
            criteria = self.df_criteria[self.df_criteria['Name'] == selected_filter]
        
            if criteria.empty:
                print(f"No criteria found for name: '{selected_filter}'")
                print("Available criteria names:", self.df_criteria['Name'].unique())
                return

            self.filtered_df = self.apply_criteria_to_df(self.filtered_df, criteria)
        else:
            print("Criteria DataFrame is empty")

    def apply_saved_highlight(self):
        selected_highlight = self.highlight_criteria_dropdown.currentText()
        print(f"Applying highlight: '{selected_highlight}'")
        print(f"Criteria DataFrame: {self.df_criteria}")

        if selected_highlight == "None" or selected_highlight == "":
            # Remove highlight color if no criteria is selected
            if 'HighlightColor' in self.filtered_df.columns:
                self.filtered_df = self.filtered_df.drop(columns=['HighlightColor'])
            return

        if not self.df_criteria.empty:
            highlight_criteria = self.df_criteria[self.df_criteria['Name'] == selected_highlight]
        
            if highlight_criteria.empty:
                print(f"No highlight criteria found for name: '{selected_highlight}'")
                print("Available criteria names:", self.df_criteria['Name'].unique())
            
                # Remove highlight color if no criteria found
                if 'HighlightColor' in self.filtered_df.columns:
                    self.filtered_df = self.filtered_df.drop(columns=['HighlightColor'])
                return

            self.highlight_criteria = highlight_criteria
            self.apply_criteria_to_data()
        else:
            print("Criteria DataFrame is empty")
            # Remove highlight color if no criteria available
            if 'HighlightColor' in self.filtered_df.columns:
                self.filtered_df = self.filtered_df.drop(columns=['HighlightColor'])

    def handle_new_criteria(self, criteria_df):
        print("Received new criteria:")
        print(criteria_df)

        # Ensure the DataFrame has the required columns
        required_columns = ['Name', 'Column', 'Operator', 'Value', 'Color']
        for col in required_columns:
            if col not in criteria_df.columns:
                print(f"Warning: Missing column '{col}' in criteria DataFrame")
                return

        # Merge the new criteria with existing criteria
        if self.df_criteria is None or self.df_criteria.empty:
            self.df_criteria = criteria_df
        else:
            # Append and drop duplicates based on specific columns
            self.df_criteria = pd.concat([self.df_criteria, criteria_df]).drop_duplicates(
                subset=['Name', 'Column', 'Operator', 'Value']
            )
    
        # Update the criteria dropdowns
        self.update_criteria_dropdowns()
    
        # Automatically apply the new criteria
        self.apply_filters()

    def update_criteria_dropdowns(self):
        # Block signals to prevent multiple updates
        self.filter_criteria_dropdown.blockSignals(True)
        self.highlight_criteria_dropdown.blockSignals(True)

        # Clear existing items
        self.filter_criteria_dropdown.clear()
        self.highlight_criteria_dropdown.clear()
    
        # Add "None" as default
        self.filter_criteria_dropdown.addItem("None")
        self.highlight_criteria_dropdown.addItem("None")
    
        # Add unique criteria names
        if self.df_criteria is not None and not self.df_criteria.empty and 'Name' in self.df_criteria.columns:
            unique_names = self.df_criteria['Name'].unique()
            print("Unique criteria names:", unique_names)
        
            for name in unique_names:
                if pd.notna(name) and name != '':
                    self.filter_criteria_dropdown.addItem(name)
                    self.highlight_criteria_dropdown.addItem(name)
        else:
            print("No valid criteria names found")

        # Unblock signals
        self.filter_criteria_dropdown.blockSignals(False)
        self.highlight_criteria_dropdown.blockSignals(False)


    def correlation_dialog(self):
        dialog = CalculateCorrelations(self.df, self)
        dialog.show()

    def delete_zone(self):
        # Launch the DeleteZone dialog, passing self as the parent
        dialog = DeleteZone(self.df, self.zone_names, self)
        dialog.show()

        # Update the parent class attributes after the dialog has closed
        self.zone_names = dialog.zone_names
        self.df = dialog.df

        # Optional: Trigger any additional UI updates or actions
        self.update_after_deletion()

    def update_after_deletion(self):
        # Example: Updating a dropdown list with the new zone names
        self.zone_dropdown.clear()
        self.zone_dropdown.addItems(self.zone_names)

        # Update other UI elements as needed

    def update_after_deletion(self):
        # Step 1: Update zone-related dropdowns and lists
        self.zone_name_filter.clear()
        self.zone_name_filter.addItem("Select Zone")
        self.zone_name_filter.addItems(sorted(self.zone_names))

        # Step 2: Reapply filters since the data has changed
        self.apply_filters()

        # Step 3: Reset pagination
        self.current_page = 0
        self.update_page_label()

        # Step 4: Refresh the table view with updated data
        self.load_data()

        # Step 5: If there are other UI elements that depend on the zone list, update them here
        # For example, updating a zone dropdown elsewhere in the UI
        if hasattr(self, 'zone_dropdown'):
            self.zone_dropdown.clear()
            self.zone_dropdown.addItems(self.zone_names)

        self.dataUpdated.emit(self.df)
        self.zoneNamesUpdated.emit(self.zone_names)



def main():
    app = QApplication(sys.argv)
    
    # Create a sample DataFrame
    data = {
        'UWI': ['001', '002', '003', '004', '005'],
        'Attribute Type': ['Well', 'Zone', 'Well', 'Zone', 'Well'],
        'Zone Name': ['Zone1', 'Zone2', 'Zone3', 'Zone4', 'Zone5'],
        'Zone Type': ['Completions', 'Tests', 'Production', 'Injection', 'Completions']
    }
    df = pd.DataFrame(data)
    zone_names = ['Zone1', 'Zone2', 'Zone3', 'Zone4', 'Zone5']
    selected_UWIs = ['001', '002', '003', '004', '005']

    dialog = ZoneViewerDialog(df, zone_names, selected_UWIs)
    dialog.show()

    sys.exit(app.exec_())

if __name__ == "__main__":
    main()