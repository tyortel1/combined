import os
import sys
import pandas as pd
from PySide6.QtWidgets import QApplication,QMessageBox, QLineEdit, QDialog, QVBoxLayout, QTableView, QFileDialog, QAbstractItemView, QHBoxLayout, QPushButton, QLabel, QComboBox, QToolBar, QSlider, QWidget, QListWidget, QFormLayout
from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QStandardItemModel, QStandardItem, QIcon, QFont, QColor, QAction
from ColumnSelectDialog import ColumnSelectionDialog
from PySide6.QtCore import Signal
from HighlightCriteriaDialog import HighlightCriteriaDialog
from CriteriaToZone import CriteriaToZoneDialog
from DecisionTreeDialog import DecisionTreeDialog
from DeleteZone import DeleteZone
from CalculateCorrelations import CalculateCorrelations



class ZoneViewerDialog(QDialog):
    settingsClosed = Signal(dict)
    dataUpdated = Signal(pd.DataFrame)
    newAttributeAdded = Signal(str) 
    zoneNamesUpdated = Signal(list) 

    def __init__(self, df, zone_names, selected_uwis, save_zone_viewer_settings=None,zone_criteria_df=None, column_filters=None):
        super(ZoneViewerDialog, self).__init__()
        self.setWindowTitle("Zone Properties")
        self.resize(1500, 1200)
         # Set window flags to include the maximize button
        self.setWindowFlags(self.windowFlags() | Qt.WindowMaximizeButtonHint | Qt.WindowMinimizeButtonHint)

        self.df = df
       
        self.zone_names = zone_names
        self.selected_uwis = selected_uwis
        self.selected_columns = df.columns.tolist()  # Initially select all columns
        self.settings_dict = save_zone_viewer_settings
        self.page_size = 1000  # Number of rows per page
        self.current_page = 0
        self.column_filters = column_filters if column_filters is not None else {}
        self.current_config_name = None

        self.df_criteria = zone_criteria_df if zone_criteria_df is not None else pd.DataFrame()
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

        self.filter_layout.addWidget(QLabel("Column Filters:"))
        self.column_filter_dropdown = QComboBox(self)
        self.column_filter_dropdown.addItem("Select Saved Configuration") 
        self.column_filter_dropdown.addItems(self.column_filters.keys())
        self.column_filter_dropdown.currentIndexChanged.connect(self.apply_column_filter)
        
        self.filter_layout.addWidget(self.column_filter_dropdown)


                # Sort dropdown with label
        self.filter_layout.addWidget(QLabel("Sort By:"))
        self.sort_dropdown = QComboBox(self)
        self.sort_dropdown.addItem("Sort by...")  # Default text

        # Sort the columns alphabetically before adding them to the dropdown
        sorted_columns = sorted(self.df.columns.tolist())
        self.sort_dropdown.addItems(sorted_columns)

        self.sort_dropdown.currentIndexChanged.connect(self.sort_data)
        self.filter_layout.addWidget(self.sort_dropdown)


        # Search bar with label
        self.filter_layout.addWidget(QLabel("Search:"))
        self.search_bar = QLineEdit(self)
        self.search_bar.setPlaceholderText("Search...")
        self.search_bar.returnPressed.connect(self.apply_search_filter)
        self.filter_layout.addWidget(self.search_bar)



        # Criteria dropdowns
        self.filter_criteria_dropdown = QComboBox(self)
        self.filter_criteria_dropdown.addItem("None")
        self.filter_criteria_dropdown.currentIndexChanged.connect(self.apply_filters)

        self.highlight_criteria_dropdown = QComboBox(self)
        self.highlight_criteria_dropdown.addItem("None")
        self.highlight_criteria_dropdown.currentIndexChanged.connect(self.apply_filters)

        # UWI Filter
        # Sort the columns alphabetically before adding them to the dropdown
        sorted_columns = sorted(self.df.columns.tolist())
        self.sort_dropdown.addItems(sorted_columns)

        # UWI Filter
        self.uwi_filter_label = QLabel("Filter by UWI")
        self.uwi_filter = QComboBox(self)
        self.uwi_filter.setFixedSize(QSize(180, 25))
        self.uwi_filter.addItem("All")
        sorted_uwis = sorted(self.selected_uwis)
        self.uwi_filter.addItems(sorted_uwis)
        self.uwi_filter.setCurrentText("All")  # Set initial value
        self.uwi_filter.currentTextChanged.connect(self.apply_filters)
        self.filter_layout.addWidget(self.uwi_filter_label)
        self.filter_layout.addWidget(self.uwi_filter)

        # Attribute Filter
        self.attribute_filter_label = QLabel("Filter by Attribute")
        self.attribute_filter = QComboBox(self)
        self.attribute_filter.setFixedSize(QSize(180, 25))
        self.attribute_filter.addItem("All")
        sorted_attributes = sorted(["Well", "Zone"])
        self.attribute_filter.addItems(sorted_attributes)
        self.attribute_filter.setCurrentText("All")  # Set initial value
        self.attribute_filter.currentTextChanged.connect(self.apply_filters)
        self.filter_layout.addWidget(self.attribute_filter_label)
        self.filter_layout.addWidget(self.attribute_filter)

        # Zone Name Filter
        self.zone_name_filter_label = QLabel("Filter by Zone Name")
        self.zone_name_filter = QComboBox(self)
        self.zone_name_filter.setFixedSize(QSize(180, 25))
        self.zone_name_filter.addItem("All")
        sorted_zone_names = sorted(self.zone_names)
        self.zone_name_filter.addItems(sorted_zone_names)
        self.zone_name_filter.setCurrentText("All")  # Set initial value
        self.zone_name_filter.currentTextChanged.connect(self.apply_filters)
        self.filter_layout.addWidget(self.zone_name_filter_label)
        self.filter_layout.addWidget(self.zone_name_filter)

        # Zone Type Filter
        self.zone_type_filter_label = QLabel("Filter by Zone Type")
        self.zone_type_filter = QComboBox(self)
        self.zone_type_filter.setFixedSize(QSize(180, 25))
        self.zone_type_filter.addItem("All")
        sorted_zone_types = sorted(["Completions", "Tests", "Production", "Injection"])
        self.zone_type_filter.addItems(sorted_zone_types)
        self.zone_type_filter.setCurrentText("All")  # Set initial value
        self.zone_type_filter.currentTextChanged.connect(self.apply_filters)
        self.filter_layout.addWidget(self.zone_type_filter_label)
        self.filter_layout.addWidget(self.zone_type_filter)



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


        self.filtered_df = self.df.copy()
        self.update_page_label()
        self.load_settings()


        # Connect signals to update settings
        self.uwi_filter.currentTextChanged.connect(self.update_settings_dict)
        self.attribute_filter.currentTextChanged.connect(self.update_settings_dict)
        self.zone_name_filter.currentTextChanged.connect(self.update_settings_dict)
        self.zone_type_filter.currentTextChanged.connect(self.update_settings_dict)
        self.column_width_slider.valueChanged.connect(self.update_settings_dict)
        self.row_height_slider.valueChanged.connect(self.update_settings_dict)
        self.font_size_slider.valueChanged.connect(self.update_settings_dict)

    
        
        
    def handle_sort_indicator_changed(self, logicalIndex, order):
        # Get the column name based on the logical index
        sort_column = self.table_view.horizontalHeader().model().headerData(logicalIndex, Qt.Horizontal)

        # Determine if the column is numeric and sort accordingly
        if pd.api.types.is_numeric_dtype(self.filtered_df[sort_column]):
            self.filtered_df.sort_values(by=sort_column, ascending=order == Qt.AscendingOrder, inplace=True, key=pd.to_numeric)
        else:
            self.filtered_df.sort_values(by=sort_column, ascending=order == Qt.AscendingOrder, inplace=True)

        # Reset the current page and reload the data
        self.current_page = 0
        self.update_page_label()
        self.load_data()
        
        
    def sort_data(self):
        sort_column = self.sort_dropdown.currentText()
    
        if sort_column != "Sort by...":  # Ignore if the user hasn't selected a valid column
            if not self.filtered_df.empty:  # Check if filtered_df exists and is not empty
                df_to_sort = self.filtered_df
            else:
                df_to_sort = self.df

            df_to_sort.sort_values(by=sort_column, ascending=True, inplace=True)  # Sort the DataFrame


            if pd.api.types.is_numeric_dtype(df_to_sort[sort_column]):
                df_to_sort.sort_values(by=sort_column, ascending=True, inplace=True, key=pd.to_numeric)

            # If filtering was applied previously, update filtered_df, otherwise set it as the sorted DataFrame
            if not self.filtered_df.empty:
                self.filtered_df = df_to_sort
            else:
                self.filtered_df = df_to_sort.copy()

            # Reset to the first page and reload the data
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
            # If search text is cleared, reapply the existing filters without the search condition
            self.apply_saved_filter()

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
        self.search_bar.setText("")

        self.uwi_filter.blockSignals(True)
        self.attribute_filter.blockSignals(True)
        self.zone_name_filter.blockSignals(True)
        self.zone_type_filter.blockSignals(True)
        self.filter_criteria_dropdown.blockSignals(True)
        self.highlight_criteria_dropdown.blockSignals(True)
        self.sort_dropdown.blockSignals(True)

        uwi_filter_text = self.uwi_filter.currentText().strip().lower()
        attribute_filter_text = self.attribute_filter.currentText().strip().lower()
        zone_name_filter_text = self.zone_name_filter.currentText().strip().lower()
        zone_type_filter_text = self.zone_type_filter.currentText().strip().lower()

        # Initialize filter conditions
        uwi_filter_condition = pd.Series([True] * len(self.df), index=self.df.index)
        attribute_filter_condition = pd.Series([True] * len(self.df), index=self.df.index)
        zone_name_filter_condition = pd.Series([True] * len(self.df), index=self.df.index)
        zone_type_filter_condition = pd.Series([True] * len(self.df), index=self.df.index)

        # Apply UWI filter if not "All"
        if uwi_filter_text != "all":
            uwi_filter_condition = self.df['UWI'].astype(str).str.lower().str.contains(uwi_filter_text)

        # Apply Attribute filter if not "All"
        if attribute_filter_text != "all":
            attribute_filter_condition = self.df['Attribute Type'].astype(str).str.lower() == attribute_filter_text

        # Apply Zone Name filter if not "All"
        if zone_name_filter_text != "all":
            zone_name_filter_condition = self.df['Zone Name'].astype(str).str.lower() == zone_name_filter_text

        # Apply Zone Type filter if not "All"
        if zone_type_filter_text != "all":
            zone_type_filter_condition = self.df['Zone Type'].astype(str).str.lower() == zone_type_filter_text

        # Ensure all boolean series are aligned with the DataFrame's index
        uwi_filter_condition = uwi_filter_condition.reindex(self.df.index, fill_value=False)
        attribute_filter_condition = attribute_filter_condition.reindex(self.df.index, fill_value=False)
        zone_name_filter_condition = zone_name_filter_condition.reindex(self.df.index, fill_value=False)
        zone_type_filter_condition = zone_type_filter_condition.reindex(self.df.index, fill_value=False)

        # Apply all filter conditions to the DataFrame
        self.filtered_df = self.df[
            uwi_filter_condition &
            attribute_filter_condition &
            zone_name_filter_condition &
            zone_type_filter_condition
        ]



        self.apply_saved_filter()
        self.apply_saved_highlight()


        sort_column = self.sort_dropdown.currentText()
    
        if sort_column != "Sort by...":  # Ignore if the user hasn't selected a valid column
            if not self.filtered_df.empty:  # Check if filtered_df exists and is not empty
                df_to_sort = self.filtered_df
            else:
                df_to_sort = self.df

            df_to_sort.sort_values(by=sort_column, ascending=True, inplace=True)  # Sort the DataFrame

            # If filtering was applied previously, update filtered_df, otherwise set it as the sorted DataFrame
            if not self.filtered_df.empty:
                self.filtered_df = df_to_sort
            else:
                self.filtered_df = df_to_sort.copy()

        # Unblock signals after all operations are completed
        self.uwi_filter.blockSignals(False)
        self.attribute_filter.blockSignals(False)
        self.zone_name_filter.blockSignals(False)
        self.zone_type_filter.blockSignals(False)
        self.filter_criteria_dropdown.blockSignals(False)
        self.highlight_criteria_dropdown.blockSignals(False)
        self.sort_dropdown.blockSignals(False)
    
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
        page_data = page_data.applymap(lambda x: f"{x:.2f}" if isinstance(x, (int, float)) else x)
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
        # Retrieve the currently selected configuration name from the dropdown
        self.current_config_name = self.column_filter_dropdown.currentText()

        # Open the dialog with the current columns, selected columns, column filters, and the current configuration name
        dialog = ColumnSelectionDialog(
            all_columns=self.df.columns.tolist(),
            selected_columns=self.selected_columns,
            column_filters=self.column_filters,
            current_config_name=self.current_config_name,
            parent=self
        )


        if dialog.exec_() == QDialog.Accepted:
            # Get the updated column filters from the dialog
            self.column_filters = dialog.column_filters
            self.current_config_name = dialog.current_config_name
       

            # Update the column_filter_dropdown with the new saved column sets
            self.column_filter_dropdown.clear()
            self.column_filter_dropdown.addItem("Select Saved Configuration")  # Add a default item
            self.column_filter_dropdown.addItems(self.column_filters.keys())

            # Set the dropdown to the current configuration name if it exists
            if self.current_config_name and self.current_config_name in self.column_filters:
                self.column_filter_dropdown.setCurrentText(self.current_config_name)
                self.selected_columns = self.column_filters[self.current_config_name]
            else:
                # If the current configuration name is not found, use the default selected columns from the dialog
                self.column_filter_dropdown.setCurrentText("Select Saved Configuration")
                self.selected_columns = dialog.get_selected_columns()

            # Load the data based on the selected columns
            self.load_data()

            # Save the current configuration name to settings
            self.update_settings_dict()

    def apply_column_dimensions(self):
        column_width = self.column_width_slider.value()
        row_height = self.row_height_slider.value()
        font_size = self.font_size_slider.value()

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

    def update_settings_dict(self):
        self.current_config_name = self.column_filter_dropdown.currentText()
        """Update the settings dictionary with current values"""
        self.settings_dict = {
            "column_width": self.column_width_slider.value(),
            "row_height": self.row_height_slider.value(),
            "font_size": self.font_size_slider.value(),
            "selected_columns": self.selected_columns,
            "uwi_filter": self.uwi_filter.currentText(),
            "attribute_filter": self.attribute_filter.currentText(),
            "zone_name_filter": self.zone_name_filter.currentText(),
            "zone_type_filter": self.zone_type_filter.currentText(),
            "filter_criteria": self.filter_criteria_dropdown.currentText(),  # Save current filter criteria selection
            "highlight_criteria": self.highlight_criteria_dropdown.currentText(),  # Save current highlight criteria selection
            "current_column_filter": self.column_filter_dropdown.currentText()
        }

    def load_settings(self):
        if self.settings_dict is None:
            # If no settings are provided, do nothing and return
            return

        settings = self.settings_dict
   
        # Block signals for sliders and dropdowns to prevent triggering their connected methods
        self.column_width_slider.blockSignals(True)
        self.row_height_slider.blockSignals(True)
        self.font_size_slider.blockSignals(True)
        self.uwi_filter.blockSignals(True)
        self.attribute_filter.blockSignals(True)
        self.zone_name_filter.blockSignals(True)
        self.zone_type_filter.blockSignals(True)
        self.filter_criteria_dropdown.blockSignals(True)
        self.highlight_criteria_dropdown.blockSignals(True)

        try:
            # Load settings into the sliders and filters
            self.column_width_slider.setValue(settings.get("column_width", 100))
            self.row_height_slider.setValue(settings.get("row_height", 20))
            self.font_size_slider.setValue(settings.get("font_size", 8))
            self.selected_columns = settings.get("selected_columns", self.df.columns.tolist())
            self.uwi_filter.setCurrentText(settings.get("uwi_filter", "All"))
            self.attribute_filter.setCurrentText(settings.get("attribute_filter", "All"))
            self.zone_name_filter.setCurrentText(settings.get("zone_name_filter", "All"))
            self.zone_type_filter.setCurrentText(settings.get("zone_type_filter", "All"))
            self.column_filter_dropdown.setCurrentText(settings.get("current_column_filter", "All"))
            self.current_config_name = self.column_filter_dropdown.currentText()


            # Clear existing items in the dropdowns
            self.filter_criteria_dropdown.clear()
            self.highlight_criteria_dropdown.clear()

            # Add "None" as the default option
            self.filter_criteria_dropdown.addItem("None")
            self.highlight_criteria_dropdown.addItem("None")

            if hasattr(self, 'df_criteria') and self.df_criteria is not None and not self.df_criteria.empty:
                if 'Name' in self.df_criteria.columns:
                    for criteria_name in self.df_criteria['Name'].unique():
                        self.filter_criteria_dropdown.addItem(criteria_name)
                        self.highlight_criteria_dropdown.addItem(criteria_name)
                else:
                    print("The df_criteria DataFrame does not have the 'Name' column.")
            else:
                print("df_criteria is either not defined, None, or empty.")

            # Restore the selected criteria from settings
            saved_filter_criteria = settings.get("filter_criteria", "None")
            saved_highlight_criteria = settings.get("highlight_criteria", "None")

            if saved_filter_criteria in [self.filter_criteria_dropdown.itemText(i) for i in range(self.filter_criteria_dropdown.count())]:
                self.filter_criteria_dropdown.setCurrentText(saved_filter_criteria)

            if saved_highlight_criteria in [self.highlight_criteria_dropdown.itemText(i) for i in range(self.highlight_criteria_dropdown.count())]:
                self.highlight_criteria_dropdown.setCurrentText(saved_highlight_criteria)
        finally:
            # Re-enable signals after the settings have been loaded
            self.column_width_slider.blockSignals(False)
            self.row_height_slider.blockSignals(False)
            self.font_size_slider.blockSignals(False)
            self.uwi_filter.blockSignals(False)
            self.attribute_filter.blockSignals(False)
            self.zone_name_filter.blockSignals(False)
            self.zone_type_filter.blockSignals(False)
            self.filter_criteria_dropdown.blockSignals(False)
            self.highlight_criteria_dropdown.blockSignals(False)

        # Apply filters and column dimensions after loading settings
        self.apply_filters()
        self.apply_column_dimensions()

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
        dialog.show()


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
        self.zone_name_filter.addItem("All")
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

    def closeEvent(self, event):
        self.update_settings_dict()

        # Emit the settings and criteria DataFrame back to the main application
        self.settingsClosed.emit({
            "settings": self.settings_dict,
            "criteria": self.df_criteria,
            "columns" : self.column_filters
        })

        super().closeEvent(event)

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
    selected_uwis = ['001', '002', '003', '004', '005']

    dialog = ZoneViewerDialog(df, zone_names, selected_uwis)
    dialog.show()

    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
