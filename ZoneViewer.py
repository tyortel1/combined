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
import traceback



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
        self.filter_criteria = None



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

        # Saved Configurations
        self.filter_layout.addWidget(QLabel("Saved Configurations:"))
        self.column_filter_dropdown = QComboBox(self)
        self.column_filter_dropdown.addItem("Select Saved Configuration") 
        self.column_filter_dropdown.addItems(self.column_filters.keys())
        self.column_filter_dropdown.currentIndexChanged.connect(self.apply_column_filter)
        self.filter_layout.addWidget(self.column_filter_dropdown)

        # Zone Type Filter
        self.zone_type_filter_label = QLabel("Filter by Zone Type", self)
        self.zone_type_filter = QComboBox(self)
        self.zone_type_filter.setFixedSize(QSize(180, 25))
        self.zone_type_filter.addItem("All")
        self.zone_type_filter.addItems(sorted(["Well", "Zone", "Intersections"]))
        self.zone_type_filter.setCurrentText("All")

        # Add to layout
        self.filter_layout.addWidget(self.zone_type_filter_label)
        self.filter_layout.addWidget(self.zone_type_filter)

        # Debug logging
        print("DEBUG: Zone Type Filter Creation")
        print(f"Zone Type Filter Items: {[self.zone_type_filter.itemText(i) for i in range(self.zone_type_filter.count())]}")

        # Signal connections
        self.zone_type_filter.currentTextChanged.connect(self.on_zone_type_selected)
        print("DEBUG: Connected signal for zone_type_filter")

        # Create a label for the Zone Name filter
        self.zone_name_filter_label = QLabel("Filter by Zone Name", self)
        self.filter_layout.addWidget(self.zone_name_filter_label)

        # Initialize the zone name filter with proper connection
        self.zone_name_filter = QComboBox(self)
        self.zone_name_filter.setFixedSize(QSize(180, 25))
        self.zone_name_filter.addItem("Select Zone")
        self.zone_name_filter.currentTextChanged.connect(self.on_zone_selected)  # Add this line
        self.filter_layout.addWidget(self.zone_name_filter)

        # Initial population of zones
        self.populate_zone_names()




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

        self.populate_criteria_dropdowns()
        self.on_zone_selected()
        #self.load_settings()

    def populate_criteria_dropdowns(self):
        """Load criteria names from the database into the dropdowns."""
        print("\n=== Populating Criteria Dropdowns ===")  # Debugging
        criteria_names = self.db_manager.load_criteria_names()

        if not criteria_names:
            print("No criteria found in the database.")
            return

        print(f"Loaded criteria: {criteria_names}")

        # Clear existing items (except "None")
        self.filter_criteria_dropdown.clear()
        self.highlight_criteria_dropdown.clear()

        # Re-add "None" option
        self.filter_criteria_dropdown.addItem("None")
        self.highlight_criteria_dropdown.addItem("None")

        # Add criteria names
        self.filter_criteria_dropdown.addItems(criteria_names)
        self.highlight_criteria_dropdown.addItems(criteria_names)


    def on_zone_type_text_changed(self, text):
        print("=== Zone Type Text Changed ===")
        print(f"New Text: {text}")
        print(f"Current Index: {self.zone_type_filter.currentIndex()}")      



    def on_zone_type_selected(self):
        """
        Handles the selection of a zone type from the dropdown.
        """
        print("yes")
        try:
            selected_type = self.zone_type_filter.currentText()
            print(f"Zone type selected: {selected_type}")
        
            # Update the UI and populate zones
            self.update_zone_filter()
        
        except Exception as e:
            print(f"Error in on_zone_type_selected: {str(e)}")
         

    def update_zone_filter(self):
        """
        Updates the zone filter UI based on the selected zone type.
        """
        try:
            selected_zone_type = self.zone_type_filter.currentText().strip()
            print(f"Updating zone filter for type: {selected_zone_type}")

            # Store currently selected zones
            current_selections = []
            if isinstance(self.zone_name_filter, QComboBox):
                if self.zone_name_filter.currentText() != "Select Zone":
                    current_selections = [self.zone_name_filter.currentText()]
            elif isinstance(self.zone_name_filter, QListWidget):
                current_selections = [item.text() for item in self.zone_name_filter.selectedItems()]

            # Find the index of the zone name filter in the layout
            old_index = -1
            for i in range(self.filter_layout.count()):
                if self.filter_layout.itemAt(i).widget() == self.zone_name_filter:
                    old_index = i
                    break

            # Remove existing widget
            if hasattr(self, 'zone_name_filter'):
                self.filter_layout.removeWidget(self.zone_name_filter)
                self.zone_name_filter.deleteLater()

            # Create appropriate widget
            if selected_zone_type == "Well":
                self.zone_name_filter = QListWidget(self)
                self.zone_name_filter.setFixedSize(QSize(180, 200))
                self.zone_name_filter.setSelectionMode(QAbstractItemView.MultiSelection)
                self.zone_name_filter.itemSelectionChanged.connect(self.handle_zone_selection_changed)
            else:
                self.zone_name_filter = QComboBox(self)
                self.zone_name_filter.setFixedSize(QSize(180, 25))
                self.zone_name_filter.addItem("Select Zone")
                self.zone_name_filter.currentTextChanged.connect(self.on_zone_selected)

            # Insert widget back in the same spot
            if old_index != -1:
                self.filter_layout.insertWidget(old_index, self.zone_name_filter)
            else:
                # Fallback: insert after the zone name filter label
                label_index = -1
                for i in range(self.filter_layout.count()):
                    widget = self.filter_layout.itemAt(i).widget()
                    if isinstance(widget, QLabel) and widget.text() == "Filter by Zone Name":
                        label_index = i
                        break
                if label_index != -1:
                    self.filter_layout.insertWidget(label_index + 1, self.zone_name_filter)
                else:
                    # Last resort: just add to layout
                    self.filter_layout.addWidget(self.zone_name_filter)

            # Populate zones
            self.populate_zone_names()

            # Restore selections if possible
            if isinstance(self.zone_name_filter, QListWidget):
                for i in range(self.zone_name_filter.count()):
                    item = self.zone_name_filter.item(i)
                    if item.text() in current_selections:
                        item.setSelected(True)
            elif isinstance(self.zone_name_filter, QComboBox) and current_selections:
                self.zone_name_filter.setCurrentText(current_selections[0])

        except Exception as e:
            print(f"Error updating zone filter: {str(e)}")
            traceback.print_exc()

    def handle_zone_selection_changed(self):
        """
        Handles the selection change event for the QListWidget.
        Merges multiple zone dataframes by UWI, keeping only one row per UWI in each table.
        """
        try:
            print("\n=== Zone Selection Changed ===")
            selected_items = self.zone_name_filter.selectedItems()
            selected_zones = [item.text() for item in selected_items]
            print(f"Selected zones: {selected_zones}")
    
            if not selected_zones:
                print("No zones selected")
                self.df = pd.DataFrame()
                self.filtered_df = pd.DataFrame()
                self.load_data()
                return
        
            # Load data for all selected zones
            zone_dataframes = {}
            for zone in selected_zones:
                try:
                    print(f"Loading data for zone: {zone}")
                    normalized_zone_name = zone.replace(' ', '_')
                    data = self.db_manager.fetch_table_data(normalized_zone_name)
                
                    if data is not None and len(data) > 0:
                        zone_df = pd.DataFrame(data)
                        print(f"Loaded {len(zone_df)} rows for zone {zone}")
                    
                        # Keep only the first occurrence of each UWI
                        zone_df = zone_df.drop_duplicates(subset='UWI', keep='first')

                        # Add zone name column for tracking
                        zone_df['Zone Name'] = zone
                    
                        # Store the dataframe
                        zone_dataframes[zone] = zone_df
                    else:
                        print(f"No data found for zone: {zone}")
                
                except Exception as e:
                    print(f"Error loading zone {zone}: {str(e)}")
                    import traceback
                    traceback.print_exc()
        
            # If no dataframes were loaded
            if not zone_dataframes:
                print("No data to display")
                self.df = pd.DataFrame()
                self.filtered_df = pd.DataFrame()
                self.load_data()
                return

            # Merge dataframes by UWI, keeping all unique columns
            merged_df = None
            for zone, df in zone_dataframes.items():
                if merged_df is None:
                    merged_df = df.copy()
                else:
                    # Merge with existing data on UWI, adding suffix to avoid column overwrites
                    merged_df = pd.merge(
                        merged_df, 
                        df, 
                        on='UWI', 
                        how='outer', 
                        suffixes=('', f'_{zone}')
                    )

            # Remove completely empty columns
            merged_df = merged_df.dropna(axis=1, how='all')

            print(f"Final merged data shape: {merged_df.shape}")
            print("Columns in merged dataframe:")
            for col in merged_df.columns:
                print(f"  - {col}")
        
            self.df = merged_df
            self.filtered_df = merged_df.copy()
        
            # Update UWI filter
            if 'UWI' in self.df.columns:
                unique_UWIs = sorted(self.df['UWI'].unique())
                self.UWI_filter.blockSignals(True)
                self.UWI_filter.clear()
                self.UWI_filter.addItem("All")
                self.UWI_filter.addItems([str(uwi) for uwi in unique_UWIs])
                self.UWI_filter.blockSignals(False)
        
            # Apply filters and load data
            self.apply_filters()
            self.load_data()
        
        except Exception as e:
            print(f"Error in handle_zone_selection_changed: {str(e)}")
            import traceback
            traceback.print_exc()




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




    def populate_zone_names(self, zone_type=None):
        """
        Populate the zone filter with available zones based on the selected type.
        """
        try:
            print("\nPopulating zone names...")
            # Use the provided zone_type or get the current selection
            if zone_type is None:
                zone_type = self.zone_type_filter.currentText().strip()
        
            print(f"Fetching zones for type: {zone_type}")
        
            # Initialize empty list for zone names
            self.zone_names = []
        
            # Fetch zone names based on type
            if zone_type == "All":
                # Fetch both Well and Zone types
                well_results = self.db_manager.fetch_zone_names_by_type("Well")
                zone_results = self.db_manager.fetch_zone_names_by_type("Zone")
            
                # Combine results
                if well_results:
                    self.zone_names.extend([row[0] for row in well_results])
                if zone_results:
                    self.zone_names.extend([row[0] for row in zone_results])
            else:
                # Fetch single type as before
                results = self.db_manager.fetch_zone_names_by_type("Well" if zone_type == "Well" else zone_type)
                if results:
                    self.zone_names = [row[0] for row in results]

            print(f"Found {len(self.zone_names)} zones")
            if not self.zone_names:
                print("No zones found")

            # Handle different widget types
            if isinstance(self.zone_name_filter, QListWidget):
                print("Populating QListWidget for multi-selection")
                self.zone_name_filter.clear()
                self.zone_name_filter.addItems(sorted(self.zone_names))
        
                # Ensure the widget is enabled and visible
                self.zone_name_filter.setEnabled(True)
                self.zone_name_filter.show()
        
                # Make first item visible
                if self.zone_names:
                    self.zone_name_filter.scrollToItem(self.zone_name_filter.item(0))
            
            elif isinstance(self.zone_name_filter, QComboBox):
                print("Populating QComboBox for single selection")
                self.zone_name_filter.clear()
                self.zone_name_filter.addItem("Select Zone")
                self.zone_name_filter.addItems(sorted(self.zone_names))
        
                # Restore previous selection if applicable
                if hasattr(self, 'zone_name_filter_text') and self.zone_name_filter_text in self.zone_names:
                    self.zone_name_filter.setCurrentText(self.zone_name_filter_text)
                else:
                    self.zone_name_filter.setCurrentText("Select Zone")
                
        except Exception as e:
            print(f"Error in populate_zone_names: {str(e)}")
            traceback.print_exc()



    def on_zone_selected(self):
        """
        Handles selection of zones and loads data accordingly.
        """
        try:
            print("\n=== Zone Selection Debug ===")
            selected_zone_type = self.zone_type_filter.currentText().strip()
            print(f"Selected Zone Type: {selected_zone_type}")
        
            # Get selected zones based on widget type
            if selected_zone_type == "Well" and isinstance(self.zone_name_filter, QListWidget):
                selected_zones = [item.text().strip() for item in self.zone_name_filter.selectedItems()]
            else:
                selected_zone = self.zone_name_filter.currentText().strip()
                selected_zones = [selected_zone] if selected_zone not in ["Select Zone", ""] else []

            print(f"Selected zones: {selected_zones}")

            # Clear existing data if no zones selected
            if not selected_zones:
                print("No zones selected, clearing data")
                self.df = pd.DataFrame()
                self.filtered_df = pd.DataFrame()
                self.selected_columns = []  # Clear selected columns
                self.load_data()
                return

            # Load and merge data for selected zones
            merged_df = None
            for zone in selected_zones:
                try:
                    print(f"Loading data for zone: {zone}")
                    # Normalize zone name by replacing spaces with underscores
                    normalized_zone_name = zone.replace(' ', '_')
                
                    # Fetch data for the zone
                    data = self.db_manager.fetch_table_data(normalized_zone_name)
                    print(f"Fetched data for zone {zone}: {len(data) if data is not None else 'None'}")

                    if data is not None and len(data) > 0:
                        zone_df = pd.DataFrame(data)
                        print(f"Loaded {len(zone_df)} rows for zone {zone}")
                
                        # Add zone name column
                        zone_df['Zone Name'] = zone
                
                        # Merge with existing data
                        if merged_df is None:
                            merged_df = zone_df
                        else:
                            # Merge on common columns
                            common_cols = list(set(merged_df.columns) & set(zone_df.columns))
                            merged_df = pd.merge(merged_df, zone_df, how='outer', on=common_cols)
                
                except Exception as e:
                    print(f"Error loading zone {zone}: {str(e)}")
                    import traceback
                    traceback.print_exc()

            # Update the main and filtered DataFrames
            if merged_df is not None and not merged_df.empty:
                print(f"Final merged data shape: {merged_df.shape}")
                self.df = merged_df
                self.filtered_df = merged_df.copy()
        
                # Initialize selected columns if not already set
                if not hasattr(self, 'selected_columns') or not self.selected_columns:
                    self.selected_columns = [col for col in self.df.columns if col != 'HighlightColor']
        
                # Update UWI filter
                if 'UWI' in self.df.columns:
                    unique_UWIs = sorted(self.df['UWI'].unique())
                    self.UWI_filter.blockSignals(True)
                    self.UWI_filter.clear()
                    self.UWI_filter.addItem("All")
                    self.UWI_filter.addItems([str(uwi) for uwi in unique_UWIs])
                    self.UWI_filter.blockSignals(False)
            else:
                print("No data to display")
                self.df = pd.DataFrame()
                self.filtered_df = pd.DataFrame()

            # Apply any existing filters and load the data
            print("Applying filters and loading data...")
            self.apply_filters()
            self.load_data()

        except Exception as e:
            print(f"Error in on_zone_selected: {str(e)}")
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
        
        
    def update_zone_filter(self):
        """
        Updates the zone filter UI based on the selected zone type.
        """
        try:
            selected_zone_type = self.zone_type_filter.currentText().strip()
            print(f"Updating zone filter for type: {selected_zone_type}")

            # Find the label position first
            label_index = -1
            for i in range(self.filter_layout.count()):
                widget = self.filter_layout.itemAt(i).widget()
                if isinstance(widget, QLabel) and widget.text() == "Filter by Zone Name":
                    label_index = i
                    break

            # Remove existing widget
            if hasattr(self, 'zone_name_filter'):
                self.filter_layout.removeWidget(self.zone_name_filter)
                self.zone_name_filter.deleteLater()

            # Create appropriate widget
            if selected_zone_type == "Well":
                self.zone_name_filter = QListWidget(self)
                self.zone_name_filter.setFixedSize(QSize(180, 200))
                self.zone_name_filter.setSelectionMode(QAbstractItemView.MultiSelection)
                self.zone_name_filter.itemSelectionChanged.connect(self.handle_zone_selection_changed)
            else:
                self.zone_name_filter = QComboBox(self)
                self.zone_name_filter.setFixedSize(QSize(180, 25))
                self.zone_name_filter.addItem("Select Zone")
                self.zone_name_filter.currentTextChanged.connect(self.on_zone_selected)

            # Always insert right after the label
            if label_index != -1:
                self.filter_layout.insertWidget(label_index + 1, self.zone_name_filter)
            else:
                # Fallback in case label isn't found
                self.filter_layout.addWidget(self.zone_name_filter)

            # Populate zones
            self.populate_zone_names()

        except Exception as e:
            print(f"Error updating zone filter: {str(e)}")
            traceback.print_exc()

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
        print("\nApplying filters...")
        print(f"Original DataFrame shape: {self.df.shape}")

        # Start with a copy of the main DataFrame
        self.filtered_df = self.df.copy()

        # Get filter values
        UWI_filter = self.UWI_filter.currentText().strip()
        filter_criteria = self.filter_criteria_dropdown.currentText()
        highlight_criteria = self.highlight_criteria_dropdown.currentText()
        search_text = self.search_bar.text().strip().lower()

        print(f"Active filters - UWI: {UWI_filter}")
        print(f"Criteria - Filter: {filter_criteria}, Highlight: {highlight_criteria}")

        # Apply UWI filter
        if UWI_filter != "All" and "UWI" in self.filtered_df.columns:
            self.filtered_df = self.filtered_df[self.filtered_df['UWI'].astype(str).str.contains(UWI_filter, na=False)]
            print(f"After UWI filter: {self.filtered_df.shape}")

        # Apply search filter
        if search_text:
            search_mask = self.filtered_df.astype(str).apply(lambda x: x.str.lower().str.contains(search_text, na=False)).any(axis=1)
            self.filtered_df = self.filtered_df[search_mask]
            print(f"After search filter: {self.filtered_df.shape}")

        # Apply saved filter criteria
        if filter_criteria != "None":
            self.apply_saved_filter()

        #   Apply highlighting criteria here
        if highlight_criteria != "None":
            self.apply_highlight_criteria()

        # Reset pagination
        self.current_page = 0
        self.update_page_label()

        # Reload the data view
        self.load_data()


    def load_data(self):
        """
        Load and display data in the table view with proper debugging.
        """
        try:
            print("\nStarting load_data...")
            print(f"DataFrame shape: {self.df.shape}")
            print(f"Filtered DataFrame shape: {self.filtered_df.shape if hasattr(self, 'filtered_df') else 'No filtered_df'}")

            # Initialize model
            model = QStandardItemModel()

            # Check if we have data to display
            if self.df.empty:
                print("Main DataFrame is empty")
                self.table_view.setModel(model)
                return

            # Ensure filtered_df exists
            if not hasattr(self, 'filtered_df') or self.filtered_df is None:
                print("Initializing filtered_df with main DataFrame")
                self.filtered_df = self.df.copy()

            # Determine columns to display
            if hasattr(self, 'selected_columns') and self.selected_columns:
                columns_to_display = [col for col in self.selected_columns if col in self.filtered_df.columns]
                print(f"Using selected columns: {columns_to_display}")
            else:
                columns_to_display = [col for col in self.filtered_df.columns if col != 'HighlightColor']
                print(f"Using all columns except HighlightColor: {len(columns_to_display)} columns")

            # Set headers
            model.setHorizontalHeaderLabels(columns_to_display)

            # Calculate pagination
            start_idx = self.current_page * self.page_size
            end_idx = min(start_idx + self.page_size, len(self.filtered_df))
            print(f"Pagination: {start_idx} to {end_idx} of {len(self.filtered_df)} rows")

            # Get the data for the current page
            page_data = self.filtered_df.iloc[start_idx:end_idx]
            print(f"Page data shape: {page_data.shape}")

            # Add rows to the model
            for idx, row in page_data.iterrows():
                items = []
                for col in columns_to_display:
                    value = row.get(col, '')
                
                    # Format numeric values
                    if isinstance(value, (int, float)):
                        if pd.notnull(value):
                            formatted_value = f"{value:.2f}" if isinstance(value, float) else str(value)
                        else:
                            formatted_value = ""
                    else:
                        formatted_value = str(value) if pd.notnull(value) else ""

                    item = QStandardItem(formatted_value)
                
                    # Apply highlighting if available
                    if 'HighlightColor' in row.index and pd.notnull(row['HighlightColor']):
                        item.setBackground(QColor(row['HighlightColor']))
                
                    items.append(item)
            
                model.appendRow(items)

            # Set the model to the table view
            self.table_view.setModel(model)
        
            # Apply column dimensions
            if hasattr(self, 'apply_column_dimensions'):
                self.apply_column_dimensions()
        
            # Update the page label
            if hasattr(self, 'update_page_label'):
                self.update_page_label()

            # Enable sorting
            self.table_view.setSortingEnabled(True)

            print(f"Successfully loaded {model.rowCount()} rows with {model.columnCount()} columns")

        except Exception as e:
            print(f"Error in load_data: {str(e)}")
            import traceback
            traceback.print_exc()


    def open_decision_tree_dialog(self):
        try:
            print("Opening Decision Tree Dialog...")

                        # Check if DataFrame is valid
            if self.df is None or self.df.empty:
                print("Warning: Empty or None DataFrame passed")
                QMessageBox.warning(self, "Error", "No data available")
                return
        
            # Check if database manager is valid
            if self.db_manager is None:
                print("Warning: No database manager provided")
                QMessageBox.warning(self, "Error", "Database manager not initialized")
                return


            dialog = DecisionTreeDialog(
                master_df=self.df,
                db_manager=self.db_manager,
                parent=self
            )

            if dialog.exec_() == QDialog.Accepted:
                criteria_name = dialog.criteria_name

                # Fetch updated criteria names from the database
                highlight_names = [self.highlight_criteria_dropdown.itemText(i) for i in range(self.highlight_criteria_dropdown.count())]
                filter_names = [self.filter_criteria_dropdown.itemText(i) for i in range(self.filter_criteria_dropdown.count())]

                # Ensure dropdowns contain the new criteria name
                if criteria_name not in highlight_names:
                    self.highlight_criteria_dropdown.addItem(criteria_name)

                if criteria_name not in filter_names:
                    self.filter_criteria_dropdown.addItem(criteria_name)

                # Reload data if the selected criteria matches the newly added one
                if self.highlight_criteria_dropdown.currentText() == criteria_name or \
                   self.filter_criteria_dropdown.currentText() == criteria_name:
                    self.load_data()
        
        
        except Exception as e:
            print(f"Error in decision tree dialog: {e}")



    def highlight(self):
        """Open the highlight criteria dialog and save selections to the database."""
        dialog = HighlightCriteriaDialog(
            db_manager=self.db_manager,  # Use database manager instead of DataFrame
            columns=self.df.columns.tolist(), 
            parent=self
        )

        if dialog.exec_() == QDialog.Accepted:
            criteria_name = dialog.criteria_name

            # Fetch updated criteria names from the database
            highlight_names = [self.highlight_criteria_dropdown.itemText(i) for i in range(self.highlight_criteria_dropdown.count())]
            filter_names = [self.filter_criteria_dropdown.itemText(i) for i in range(self.filter_criteria_dropdown.count())]

            # Ensure dropdowns contain the new criteria name
            if criteria_name not in highlight_names:
                self.highlight_criteria_dropdown.addItem(criteria_name)

            if criteria_name not in filter_names:
                self.filter_criteria_dropdown.addItem(criteria_name)

            # Reload data if the selected criteria matches the newly added one
            if self.highlight_criteria_dropdown.currentText() == criteria_name or \
               self.filter_criteria_dropdown.currentText() == criteria_name:
                self.load_data()
      
        self.apply_filters()

    def handle_new_criteria(self, criteria_df):
        """Save new criteria from DecisionTreeDialog to the database."""
        print("Received new criteria:")
        print(criteria_df)

        if criteria_df.empty:
            print("No criteria to save")
            return

        for _, row in criteria_df.iterrows():
            self.db_manager.save_criterion(
                name=row['Name'],
                column=row['Column'],
                operator=row['Operator'],
                value=row['Value'],
                color=row.get('Color', None)
            )

        # Update the criteria dropdowns from the database
        self.update_criteria_dropdowns()
        self.apply_filters()


    def apply_saved_filter(self):
        """Apply a saved filter criteria from the database."""
        selected_filter = self.filter_criteria_dropdown.currentText()
        print(f"Applying filter: '{selected_filter}'")

        if selected_filter == "None" or not selected_filter:
            return

        # Fetch criteria from the database instead of using self.df_criteria
        self.filter_criteria = self.db_manager.load_criteria_by_name(selected_filter)

        if not self.filter_criteria:
            print(f"No criteria found for name: '{selected_filter}'")
            return

        self.filtered_df = self.apply_criteria_to_df()

        # Reset to the first page after applying filters
        self.current_page = 0
        self.update_page_label()
        self.load_data()

        # Reload the data to reflect the applied filters
   

    def apply_criteria_to_df(self):
        """
        Fetch and apply filtering criteria from the database.
        """
        print("\n=== Fetching and Applying Filter Criteria ===")
        selected_filter = self.filter_criteria_dropdown.currentText()
        if selected_filter == "None":
            print("No filter criteria selected, showing all data.")
            return self.df.copy()

        #   Fetch filter name and conditions separately
        _, conditions = self.db_manager.load_criteria_by_name(selected_filter)
        if not conditions:
            print(f"⚠️ No conditions found for: '{selected_filter}'")
            return self.df.copy()
        print(f"  Applying filter criteria: {conditions}")

        # Start with a mask of all True values (AND logic)
        group_mask = pd.Series(True, index=self.df.index)
        for column, operator, value, logical_op in conditions:
            print(f"Applying condition: {column} {operator} {value} (Logical: {logical_op})")
        
            try:
                numeric_col = pd.to_numeric(self.df[column], errors='coerce')
                if operator == '=':
                    mask = numeric_col == float(value)
                elif operator == '>':
                    mask = numeric_col > float(value)
                elif operator == '<':
                    mask = numeric_col < float(value)
                elif operator == '>=':
                    mask = numeric_col >= float(value)
                elif operator == '<=':
                    mask = numeric_col <= float(value)
                elif operator == '!=':
                    mask = numeric_col != float(value)
                else:
                    print(f"❌ Unsupported operator: {operator}")
                    continue
                #   Apply AND/OR logic
                if logical_op == 'OR':
                    group_mask |= mask  # OR logic
                else:
                    group_mask &= mask  # AND logic (default)
            except Exception as e:
                print(f"❌ Error processing filter criteria: {e}")

        #   Apply filter to get matching rows
        filtered_df = self.df[group_mask].copy()
        print(f"🟢 Filtered to {len(filtered_df)} rows from {len(self.df)} total rows")
        return filtered_df


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


    def open_zone_to_attribute_dialog(self):
        """Open the dialog to save zone selection as an attribute."""
        selected_zone = self.zone_name_filter.currentText().strip()
    
        if selected_zone == "Select Zone":
            QMessageBox.warning(self, "No Zone Selected", "Please select a zone first before creating an attribute.")
            return

        dialog = CriteriaToZoneDialog(self.df, self.db_manager, selected_zone, self)
        if dialog.exec_() == QDialog.Accepted:
            self.df = dialog.df
            new_attribute = dialog.attribute_name
            self.dataUpdated.emit(self.df)
            self.newAttributeAdded.emit(new_attribute)
            self.apply_filters()
            self.load_data()



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
            #self.save_settings()

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

    #def save_settings(self):
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
        
    #def load_settings(self):
    #    self.settings = True
    #    settings = QSettings('ZoneApp', 'ZoneViewer')
    #    last_config_name = settings.value('last_config')
    #    print(f"Loading settings, last config: {last_config_name}")

    #    # If no last config, initialize the viewer
    #    if not last_config_name:
    #        print("No last config found")
    #        self.initialize_viewer()
    #        return

    #    # Initialize all variables with defaults
    #    self.current_config_name = last_config_name or "DefaultConfig"
    #    self.column_filters = {}
    #    self.selected_columns = []
    #    self.zone_type_filter_text = "All"
    #    self.zone_name_filter_text = "Select Zone"
    #    self.UWI_filter_text = "All"
    #    self.rows_per_page = "1000"
    #    self.filter_criteria_text = "None"
    #    self.highlight_criteria_text = "None"
    #    self.column_width = 100
    #    self.row_height = 20
    #    self.font_size = 8
    #    self.df_criteria = pd.DataFrame()

    #    if last_config_name:
    #        settings.beginGroup(last_config_name)

    #        # Block signals for UI components
    #        widgets_to_block = [
    #            self.UWI_filter,
    #            self.zone_name_filter,
    #            self.zone_type_filter,
    #            self.filter_criteria_dropdown,
    #            self.highlight_criteria_dropdown,
    #            self.column_width_slider,
    #            self.row_height_slider,
    #            self.font_size_slider
    #        ]
    #        for widget in widgets_to_block:
    #            widget.blockSignals(True)

    #        try:
    #            # Load settings with defaults if keys are missing
    #            self.column_filters = json.loads(settings.value('column_filters', '{}'))
    #            self.selected_columns = json.loads(settings.value('selected_columns', '[]'))
    #            self.zone_type_filter_text = settings.value('zone_type_filter', 'All')
    #            self.zone_name_filter_text = settings.value('zone_name_filter', 'Select Zone')
    #            self.UWI_filter_text = settings.value('UWI_filter', 'All')
    #            self.rows_per_page = settings.value('rows_per_page', '1000')
    #            self.filter_criteria_text = settings.value('filter_criteria', 'None')
    #            self.highlight_criteria_text = settings.value('highlight_criteria', 'None')
    #            self.column_width = int(settings.value('column_width', 100))
    #            self.row_height = int(settings.value('row_height', 20))
    #            self.font_size = int(settings.value('font_size', 8))
    #            criteria_json = settings.value('df_criteria', '{}')
    #            if criteria_json:
    #                self.df_criteria = pd.read_json(criteria_json)
    #        except Exception as e:
    #            print(f"Error loading settings: {e}")
    #        finally:
    #            # Unblock signals
    #            for widget in widgets_to_block:
    #                widget.blockSignals(False)
    #            settings.endGroup()

    #    self.initialize_viewer(self.zone_type_filter.currentText()) 

    #    # Apply loaded settings to the UI
    #    self.zone_type_filter.setCurrentText(self.zone_type_filter_text)
    #    self.zone_name_filter.setCurrentText(self.zone_name_filter_text)
    #    self.UWI_filter.setCurrentText(self.UWI_filter_text)
    #    self.rows_per_page_combo.setCurrentText(self.rows_per_page)
    #    self.filter_criteria_dropdown.setCurrentText(self.filter_criteria_text)
    #    self.highlight_criteria_dropdown.setCurrentText(self.highlight_criteria_text)
    #    self.column_width_slider.setValue(self.column_width)
    #    self.row_height_slider.setValue(self.row_height)
    #    self.font_size_slider.setValue(self.font_size)

    #    self.apply_column_dimensions()
    #    self.apply_filters()
    #    self.load_data()
    #    self.settings = False

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

        selected_zone = self.zone_name_filter.currentText().strip()
        print(selected_zone)
        if selected_zone == "Select Zone" or not selected_zone:
            QMessageBox.warning(self, "No Zone Selected", "Please select a zone to apply the criteria.")
            return

        # Pass db_manager into the dialog
        dialog = CriteriaToZoneDialog(self.df, self.db_manager, selected_zone, self)

        if dialog.exec_() == QDialog.Accepted:
            self.df = dialog.df
            new_attribute = dialog.attribute_name

            # **Ensure the UI updates after applying the new attribute**
            self.dataUpdated.emit(self.df)
            self.newAttributeAdded.emit(new_attribute)
            self.apply_filters()
            self.load_data()




    #def apply_saved_filter(self):
    #    selected_filter = self.filter_criteria_dropdown.currentText()
    #    print(f"Applying filter: '{selected_filter}'")
    #    print(f"Criteria DataFrame: {self.df_criteria}")

    #    if selected_filter == "None" or selected_filter == "":
    #        # If no filter is selected, return the original filtered DataFrame
    #        return

    #    if not self.df_criteria.empty:
    #        criteria = self.df_criteria[self.df_criteria['Name'] == selected_filter]
        
    #        if criteria.empty:
    #            print(f"No criteria found for name: '{selected_filter}'")
    #            print("Available criteria names:", self.df_criteria['Name'].unique())
    #            return

    #        self.filtered_df = self.apply_criteria_to_df(self.filtered_df, criteria)
    #    else:
    #        print("Criteria DataFrame is empty")

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


    def apply_highlight_criteria(self):
        """
        Fetch and apply highlighting criteria from the database.
        """
        print("\n=== Fetching and Applying Highlight Criteria ===")

        selected_highlight = self.highlight_criteria_dropdown.currentText()
        if selected_highlight == "None":
            print("No highlight criteria selected, resetting highlight column.")
            if 'HighlightColor' in self.filtered_df.columns:
                self.filtered_df['HighlightColor'] = None
            return

        #   Fetch highlight color and conditions separately
        highlight_color, conditions = self.db_manager.load_criteria_by_name(selected_highlight)

        if not conditions:
            print(f"⚠️ No conditions found for: '{selected_highlight}'")
            if 'HighlightColor' in self.filtered_df.columns:
                self.filtered_df['HighlightColor'] = None
            return

        print(f"  Applying highlight criteria: {conditions}")
    
        # Reset Highlight column
        self.filtered_df['HighlightColor'] = None

        # Start with a mask of all True values (AND logic)
        group_mask = pd.Series(True, index=self.filtered_df.index)

        for column, operator, value, logical_op in conditions:
            print(f"Applying condition: {column} {operator} {value} (Logical: {logical_op})")
        
            try:
                numeric_col = pd.to_numeric(self.filtered_df[column], errors='coerce')

                if operator == '=':
                    mask = numeric_col == float(value)
                elif operator == '>':
                    mask = numeric_col > float(value)
                elif operator == '<':
                    mask = numeric_col < float(value)
                elif operator == '>=':
                    mask = numeric_col >= float(value)
                elif operator == '<=':
                    mask = numeric_col <= float(value)
                elif operator == '!=':
                    mask = numeric_col != float(value)
                else:
                    print(f"❌ Unsupported operator: {operator}")
                    continue

                #   Apply AND/OR logic
                if logical_op == 'OR':
                    group_mask |= mask  # OR logic
                else:
                    group_mask &= mask  # AND logic (default)

            except Exception as e:
                print(f"❌ Error processing highlight criteria: {e}")

        #   Apply highlight color to matching rows
        self.filtered_df.loc[group_mask, 'HighlightColor'] = highlight_color
        print(f"🟢 Applied {highlight_color} to {group_mask.sum()} rows")

        # Debugging: Check highlighted rows
        highlighted_rows = self.filtered_df[self.filtered_df['HighlightColor'].notna()]
        print(f"\n  Final highlighted rows: {len(highlighted_rows)}")





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
        """Update dropdowns with unique criteria names from the database."""
        self.filter_criteria_dropdown.blockSignals(True)
        self.highlight_criteria_dropdown.blockSignals(True)

        self.filter_criteria_dropdown.clear()
        self.highlight_criteria_dropdown.clear()

        self.filter_criteria_dropdown.addItem("None")
        self.highlight_criteria_dropdown.addItem("None")

        # Fetch criteria names from the database
        criteria_names = self.db_manager.get_all_criteria_names()

        if criteria_names:
            self.filter_criteria_dropdown.addItems(criteria_names)
            self.highlight_criteria_dropdown.addItems(criteria_names)

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

    def print_debug_info(self):
        """
        Print debug information about the current state.
        """
        print("\nDEBUG INFORMATION:")
        print(f"Main DataFrame shape: {self.df.shape if hasattr(self, 'df') else 'No df'}")
        print(f"Filtered DataFrame shape: {self.filtered_df.shape if hasattr(self, 'filtered_df') else 'No filtered_df'}")
        print(f"Selected columns: {self.selected_columns if hasattr(self, 'selected_columns') else 'No selected_columns'}")
    
        if hasattr(self, 'df') and not self.df.empty:
            print("\nAvailable columns:")
            for col in self.df.columns:
                print(f"  - {col}")
        
            print("\nSample data (first 5 rows):")
            print(self.df.head())
    
        if hasattr(self, 'filtered_df') and not self.filtered_df.empty:
            print("\nFiltered data info:")
            print(f"Number of rows: {len(self.filtered_df)}")
            print(f"Current page: {self.current_page}")
            print(f"Rows per page: {self.page_size}")


    def debug_well_zones(self):
        """
        Print debug information about the current state of well zones.
        """
        print("\n=== Well Zones Debug Info ===")
        print(f"Current zone type: {self.zone_type_filter.currentText()}")
        print(f"Widget type: {type(self.zone_name_filter).__name__}")
    
        if isinstance(self.zone_name_filter, QListWidget):
            print("\nList Widget State:")
            print(f"Total items: {self.zone_name_filter.count()}")
            print(f"Selected items: {[item.text() for item in self.zone_name_filter.selectedItems()]}")
            print("\nAll available items:")
            for i in range(self.zone_name_filter.count()):
                item = self.zone_name_filter.item(i)
                print(f"  - {item.text()} {'(selected)' if item.isSelected() else ''}")
        else:
            print("\nComboBox State:")
            print(f"Current text: {self.zone_name_filter.currentText()}")
            print(f"All items: {[self.zone_name_filter.itemText(i) for i in range(self.zone_name_filter.count())]}")
    
        print("\nData State:")
        print(f"Main DataFrame shape: {self.df.shape}")
        print(f"Filtered DataFrame shape: {self.filtered_df.shape}")
        print("===========================\n")
    def debug_zone_type_filter(self, index):
        print(f"Zone Type Filter - Index Changed: {index}")
        print(f"Current Text: {self.zone_type_filter.currentText()}")

    def debug_zone_type_text(self, text):
        print(f"Zone Type Filter - Text Changed: {text}")

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