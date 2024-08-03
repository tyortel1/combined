# main.py
import sys
import os
import json
import pandas as pd
import math
import numpy as np
from scipy.spatial import KDTree
from PySide2.QtWidgets import QApplication, QFileDialog, QMainWindow, QSpinBox, QSpacerItem, QToolBar, QCheckBox, QSlider, QLabel
from PySide2.QtWidgets import QSizePolicy, QAction, QMessageBox, QErrorMessage, QDialog, QWidget, QSystemTrayIcon, QVBoxLayout, QHBoxLayout, QMenu, QMenuBar, QPushButton, QListWidget, QComboBox, QLineEdit, QScrollArea
from PySide2.QtGui import QIcon, QColor, QPainter, QPen, QFont
from PySide2.QtCore import Qt, QPointF, QCoreApplication, QMetaObject
from shapely.geometry import LineString
import SeisWare
from Exporting import ExportDialog
from DataLoader import DataLoaderDialog
from ZoneViewer import ZoneViewerDialog
from SwPropertiesEdit import SWPropertiesEdit
from DataLoadWellZone import DataLoadWellZonesDialog
from GunBarrel import PlotGB
from Plot import Plot
from pystray import Icon, Menu, MenuItem
import threading
from PIL import Image
from shapely.geometry import LineString, Point, MultiPoint, GeometryCollection
from ColorEdit import ColorEditor
import time
import ujson as json 
from DrawingArea import DrawingArea  # Import the DrawingArea class


class Map(QMainWindow):
    def __init__(self):
        super(Map, self).__init__()
        self.grid_well_data = []
        self.grid_well_data_df = pd.DataFrame()
        self.depth_grid_color_df = pd.DataFrame()
        self.well_info_df = pd.DataFrame()
        self.top_grid_df = pd.DataFrame()
        self.bottom_grid_df = pd.DataFrame()
        self.total_zone_number = 0
        self.export_options = pd.DataFrame()
        self.import_options_df = pd.DataFrame()
        self.master_df = pd.DataFrame()
        self.depth_grid_data_df = pd.DataFrame()
        self.attribute_grid_data_df = pd.DataFrame()
        self.grid_info_df = pd.DataFrame()
        self.grid_xyz_bottom = []
        self.grid_xyz_top = []
        self.intersections = []
        self.originalIntersectionPoints = []
        self.grid_scaled_min_x = None
        self.grid_scaled_max_x = None
        self.grid_scaled_min_y = None
        self.grid_scaled_max_y = None

        self.drawing = False
        self.lastPoint = None
        self.data = []
        self.current_line = []
        self.originalCurrentLine = []
        self.scale = 1.0
        self.zoom_center = QPointF(0, 0)
        self.offset_x = 0
        self.offset_y = 0
        self.line_width = 6
        self.line_opacity = .5
        self.uwi_width = 6
        self.uwi_opacity = .5
        self.min_x = None
        self.max_x = None
        self.min_y = None
        self.max_y = None
        self.project_file_name = None
        self.scaled_data = {}
        self.intersectionPoints = []
        self.project_list = []
        self.zone_names = []
        self.uwi_list = []  # List to store UWI
        
        self.connection = SeisWare.Connection()

        self.setupUi()
        self.set_interactive_elements_enabled(False) 
 
    def closeEvent(self, event):
        # Perform any cleanup here
        self.cleanup()
        event.accept()

    def cleanup(self):
        # Ensure all connections and resources are properly closed
        if self.connection:
            self.connection.Disconnect()
            self.connection = None
        QCoreApplication.quit()

    def setupUi(self):
        self.setObjectName("MainWindow")
        self.resize(1200, 900)
        self.centralWidget = QWidget(self)
        self.setCentralWidget(self.centralWidget)

        # Main layout
        self.mainLayout = QHBoxLayout(self.centralWidget)

        # Options layout
        self.optionsLayout = QVBoxLayout()
        self.optionsLayout.setSpacing(5)  # Minimal spacing

        # Dropdown to select grid
        self.gridDropdown = QComboBox(self)
        self.gridDropdown.addItem("Select Grid")
        #self.gridDropdown.currentIndexChanged.connect(self.grid_selected)
        self.optionsLayout.addWidget(self.gridDropdown)

        # Checkbox to show/hide UWI labels
        self.uwiCheckbox = QCheckBox("Show UWI Labels", self)
        self.uwiCheckbox.setChecked(True)
        self.uwiCheckbox.stateChanged.connect(self.toggle_uwi_labels)
        self.optionsLayout.addWidget(self.uwiCheckbox)
    
        self.uwiWidthLabel = QLabel("UWI Size:", self)
        self.optionsLayout.addWidget(self.uwiWidthLabel)

        # Slider to change the width of the lines
        self.uwiWidthSlider = QSlider(Qt.Horizontal, self)
        self.uwiWidthSlider.setMinimum(1)
        self.uwiWidthSlider.setMaximum(20)
        self.uwiWidthSlider.setValue(self.line_width)
        self.uwiWidthSlider.valueChanged.connect(self.change_uwi_width)
        self.optionsLayout.addWidget(self.uwiWidthSlider)

        # Label for the opacity slider
        self.opacityLabel = QLabel("UWI Label Opacity:", self)
        self.optionsLayout.addWidget(self.opacityLabel)
    
        # Slider to change the opacity of UWI labels
        self.opacitySlider = QSlider(Qt.Horizontal, self)
        self.opacitySlider.setMinimum(0)
        self.opacitySlider.setMaximum(100)
        self.opacitySlider.setValue(50)
        self.opacitySlider.valueChanged.connect(self.change_opacity)
        self.optionsLayout.addWidget(self.opacitySlider)

        # Label for the line width slider
        self.lineWidthSliderLabel = QLabel("Line Width:", self)
        self.optionsLayout.addWidget(self.lineWidthSliderLabel)

        # Slider to change the width of the lines
        self.lineWidthSlider = QSlider(Qt.Horizontal, self)
        self.lineWidthSlider.setMinimum(1)
        self.lineWidthSlider.setMaximum(50)
        self.lineWidthSlider.setValue(self.line_width)
        self.lineWidthSlider.valueChanged.connect(self.change_line_width)
        self.optionsLayout.addWidget(self.lineWidthSlider)

        self.lineLabel = QLabel("Line Opacity", self)
        self.optionsLayout.addWidget(self.lineLabel)
    
        # Slider to change the line of UWI labels
        self.lineOpacitySlider = QSlider(Qt.Horizontal, self)
        self.lineOpacitySlider.setMinimum(0)
        self.lineOpacitySlider.setMaximum(100)
        self.lineOpacitySlider.setValue(50)
        self.lineOpacitySlider.valueChanged.connect(self.change_line_opacity)
        self.optionsLayout.addWidget(self.lineOpacitySlider)

        # Adding a spacer to push everything to the top
        self.optionsLayout.addStretch()

        self.mainLayout.addLayout(self.optionsLayout, 1)  # Occupy 1/8th of the window

        # Scroll area for the drawing area
        self.scrollArea = QScrollArea(self.centralWidget)
        self.scrollArea.setObjectName("scrollArea")
        self.scrollArea.setWidgetResizable(True)
        self.drawingArea = DrawingArea(self, fixed_width=2000, fixed_height=1500)
        self.drawingArea.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.scrollArea.setWidget(self.drawingArea)
        self.mainLayout.addWidget(self.scrollArea, 7)  # Occupy remaining 7/8ths of the window
        self.scrollArea.horizontalScrollBar().valueChanged.connect(self.updateOffset)
        self.scrollArea.verticalScrollBar().valueChanged.connect(self.updateOffset)
        self.scrollArea.setWidgetResizable(False) 

        # Menu bar
        self.menu_bar = QMenuBar(self)
        self.setMenuBar(self.menu_bar)
    
        file_menu = self.menu_bar.addMenu("Project")

        new_project_action = file_menu.addAction("Create")
        new_project_action.triggered.connect(self.create_new_project)

        open_action = file_menu.addAction("Open")
        open_action.triggered.connect(self.open_from_file)
    
        # Launch menu
        self.launch_menu = self.menu_bar.addMenu("Launch")
        self.launch_menu.setEnabled(False)
        self.plot_action = self.launch_menu.addAction("Zone Viewer")
        self.plot_action.triggered.connect(self.plot_data)
        self.color_action = self.launch_menu.addAction("Color Editor")
        self.color_action.triggered.connect(self.open_color_editor)
        self.zone_viewer_action = self.launch_menu.addAction("Zone Properties")
        self.zone_viewer_action.triggered.connect(self.launch_zone_viewer)

        self.import_menu = self.menu_bar.addMenu("Import")
        self.import_menu.setEnabled(False)
        self.data_loader_menu = self.import_menu.addAction("SeisWare Grid and Wells")
        self.data_loader_menu.triggered.connect(self.dataloader)
        self.data_loader_menu = self.import_menu.addAction("CSV Well Zones and Attributes")
        self.data_loader_menu.triggered.connect(self.dataload_well_zones)

        self.export_menu = self.menu_bar.addMenu("Export")
        self.export_menu.setEnabled(False)

        self.export_action = self.export_menu.addAction("Export Results")
        self.export_action.triggered.connect(self.export)
        self.export_properties = self.export_menu.addAction("Export SWMap Properties")
        self.export_properties.triggered.connect(self.mapproperties)
        self.zone_to_sw = self.export_menu.addAction("Send Zones to SeisWare")
        self.zone_to_sw.triggered.connect(self.export_to_sw)

        self.toolbar = QToolBar("Main Toolbar")
        self.addToolBar(self.toolbar)

        self.setWindowIcon(QIcon("icons/ZoneAnalyzer.png"))
        self.plot_icon = QIcon("icons/plot.ico")
        self.gun_barrel_icon = QIcon("icons/gunb.ico")
        self.zoom_in_icon = QIcon("icons/Zoom_in.ico")
        self.zoom_out_icon = QIcon("icons/Zoom_out.ico")
        self.exportSw_icon = QIcon("icons/export.ico")
        self.color_editor_icon = QIcon("icons/color_editor.ico")

        self.plot_tool_action = self.toolbar.addAction(self.plot_icon, "QC Zones")
        self.plot_tool_action.triggered.connect(self.plot_data)

        self.gun_barrel_action = self.toolbar.addAction(self.gun_barrel_icon, "Create Gun Barrel")
        self.gun_barrel_action.triggered.connect(self.toggleDrawing)
    
        self.color_editor_action = self.toolbar.addAction(self.color_editor_icon, "Create Gun Barrel")
        self.color_editor_action.triggered.connect(self.open_color_editor)
       
        # Zoom controls
        self.zoomOut = self.toolbar.addAction(self.zoom_out_icon, "Zoom Out")
        self.zoomOut.triggered.connect(self.zoom_out)

        self.zoomIn = self.toolbar.addAction(self.zoom_in_icon, "Zoom Out")
        self.zoomIn.triggered.connect(self.zoom_in)
  
        self.exportSw = self.toolbar.addAction(self.exportSw_icon, "Send to SeisWare")
        self.exportSw.triggered.connect(self.export_to_sw)

        self.retranslateUi()
        QMetaObject.connectSlotsByName(self)







    def grid_selected(self, index):
        if index == 0:  # "Select Grid" is selected
            return

        grid_name = self.gridDropdown.currentText()
        if grid_name in self.depth_grid_data_df['Grid'].unique():
            selected_grid_df = self.depth_grid_data_df[self.depth_grid_data_df['Grid'] == grid_name]
        else:
            selected_grid_df = self.attribute_grid_data_df[self.attribute_grid_data_df['Grid'] == grid_name]



    def retranslateUi(self):
        self.setWindowTitle(QCoreApplication.translate("MainWindow", "Zone Analyzer", None))

    def set_interactive_elements_enabled(self, enabled):
        self.plot_action.setEnabled(enabled)
        self.export_action.setEnabled(enabled)
        self.export_properties.setEnabled(enabled)
        for action in self.toolbar.actions():
            action.setEnabled(enabled)

    def setData(self, direction_survey_df):
        if direction_survey_df.empty:
            return

        pd.set_option('display.max_columns', None)  # Show all columns
        pd.set_option('display.max_colwidth', None)  # Show full column width
        print(direction_survey_df)

        uwis_and_offsets = []
        for uwi in direction_survey_df['UWI'].unique():
            df_uwi = direction_survey_df[direction_survey_df['UWI'] == uwi]
            x_offsets = df_uwi['X Offset'].tolist()
            y_offsets = df_uwi['Y Offset'].tolist()
            tvds = df_uwi['TVD'].tolist()
            uwis_and_offsets.append((uwi, x_offsets, y_offsets, tvds))

        self.data = uwis_and_offsets

        # Min/max calculations for original data
        self.min_x = min(min(x_offsets) for _, x_offsets, _, _ in self.data)
        self.max_x = max(max(x_offsets) for _, x_offsets, _, _ in self.data)
        self.min_y = min(min(y_offsets) for _, _, y_offsets, _ in self.data)
        self.max_y = max(max(y_offsets) for _, _, y_offsets, _ in self.data)

        for uwi, x_offsets, y_offsets, tvds in self.data:
            points = [(QPointF(x, y), tvd) for x, y, tvd in zip(x_offsets, y_offsets, tvds)]
            self.scaled_data[uwi] = points

        print(self.scaled_data)
        self.drawingArea.setScaledData(self.scaled_data, self.min_x, self.max_x, self.min_y, self.max_y)
        self.set_interactive_elements_enabled(True)


    def draw_grid_on_map(self, grid_df):
        # Clear current drawing
       
        self.drawingArea.clearCurrentLineAndIntersections()

        if grid_df.empty:
            return

        # Collect points and their values, prepare them for drawing
        points_with_values = []
        for index, row in grid_df.iterrows():
            x = row['X']
            y = row['Y']
            value = row['Z']  # Assuming the grid values are stored in a column named 'Value'
            # Convert to scaled coordinates
            scaled_x = (x - self.min_x) * self.scale + self.offset_x
            scaled_y = (self.max_y - y) * self.scale + self.offset_y
            points_with_values.append((QPointF(scaled_x, scaled_y), value))

        # Draw the points on the map
        print("Setting grid points:", points_with_values)  # Debugging information
        self.drawingArea.setGridPoints(points_with_values)

    def zoom_in(self):
        self.zoom(1.2)

    def zoom_out(self):
        self.zoom(1/1.2)

    def zoom(self, factor):
        old_pos = self.scrollArea.viewport().mapToGlobal(self.scrollArea.viewport().rect().center())
        old_scene_pos = self.drawingArea.mapFromGlobal(old_pos)

        new_scale = self.drawingArea.scale * factor
        self.drawingArea.setScale(new_scale)

        new_pos = self.drawingArea.mapToGlobal(old_scene_pos)
        delta = new_pos - old_pos
        self.scrollArea.horizontalScrollBar().setValue(self.scrollArea.horizontalScrollBar().value() + delta.x())
        self.scrollArea.verticalScrollBar().setValue(self.scrollArea.verticalScrollBar().value() + delta.y())

        self.updateScrollBars()

    def updateScrollBars(self):
        scaled_width = self.drawingArea.width() * self.drawingArea.scale
        scaled_height = self.drawingArea.height() * self.drawingArea.scale

        self.scrollArea.horizontalScrollBar().setRange(0, max(0, scaled_width - self.scrollArea.viewport().width()))
        self.scrollArea.verticalScrollBar().setRange(0, max(0, scaled_height - self.scrollArea.viewport().height()))

        self.scrollArea.horizontalScrollBar().setVisible(scaled_width > self.scrollArea.viewport().width())
        self.scrollArea.verticalScrollBar().setVisible(scaled_height > self.scrollArea.viewport().height())

    def updateOffset(self):
        x = self.scrollArea.horizontalScrollBar().value()
        y = self.scrollArea.verticalScrollBar().value()
        self.drawingArea.setOffset(QPointF(-x, -y))

    def toggle_uwi_labels(self, state):
        self.drawingArea.show_uwis = (state == Qt.Checked)
        self.drawingArea.update()

    def change_uwi_width(self, value):
        self.uwi_width = value 
        self.drawingArea.update()

    def change_opacity(self, value):
        self.uwi_opacity = value / 100.0
        self.drawingArea.update()

    def change_line_width(self, value):
        self.line_width = value 
        self.drawingArea.update()

    def change_line_opacity(self, value):
        self.line_opacity = value / 100.0
        self.drawingArea.update()

    def create_new_project(self):
        self.project_data = {
            'project_name': '',
            'filter_name': '',
            'selected_uwis': [],
            'top_grid': '',
            'bottom_grid': '',
            'number_of_zones': 0,
            'export_options': {}
        }

        options = QFileDialog.Options()
        file_name, _ = QFileDialog.getSaveFileName(self, "Create New Project", "", "JSON Files (*.json);;All Files (*)", options=options)
        if file_name:
            self.project_file_name = file_name
            with open(file_name, 'w') as file:
                json.dump(self.project_data, file, indent=4)

            self.set_interactive_elements_enabled(False)
            self.import_menu.setEnabled(True)
            self.data_loader_menu.setEnabled(True)

            self.grid_well_data_df = pd.DataFrame()
            self.well_info_df = pd.DataFrame()
            self.zonein_info_df = pd.DataFrame()
            self.top_grid_df = pd.DataFrame()
            self.bottom_grid_df = pd.DataFrame()
            self.total_zone_number = 0
            self.export_options = pd.DataFrame()
            self.zone_color_df = pd.DataFrame()
        
        file_basename = os.path.basename(file_name)
        self.setWindowTitle(QCoreApplication.translate("MainWindow", f"Zone Analyzer - {file_basename}", None))

    def dataloader(self):
        
        dialog = DataLoaderDialog(self.import_options_df)
        if dialog.exec_() == QDialog.Accepted:
            self.directional_surveys_df = dialog.directional_surveys_df
            self.depth_grid_data_df = dialog.depth_grid_data_df
            self.attribute_grid_data_df = dialog.attribute_grid_data_df
            self.import_options_df = dialog.import_options_df
            self.selected_uwis = dialog.selected_uwis
            self.depth_grid_color_df = dialog.depth_grid_color_df
            self.grid_info_df = dialog.grid_info_df
     


            self.populate_grid_dropdown()
            self.setData(self.directional_surveys_df)

            # Enable menus and interactive elements
            self.export_menu.setEnabled(True)
            self.launch_menu.setEnabled(True)
            self.set_interactive_elements_enabled(True)

            if hasattr(self, 'project_file_name') and self.project_file_name:
                self.project_data = {
                    'directional_surveys': self.directional_surveys_df.to_dict(orient='list') if isinstance(self.directional_surveys_df, pd.DataFrame) else {},
                    'depth_grid_data': self.depth_grid_data_df.to_dict(orient='list') if isinstance(self.depth_grid_data_df, pd.DataFrame) else {},
                    'attribute_grid_data': self.attribute_grid_data_df.to_dict(orient='list') if isinstance(self.attribute_grid_data_df, pd.DataFrame) else {},
                    'import_options': self.import_options_df.to_dict(orient='list') if isinstance(self.import_options_df, pd.DataFrame) else {},
                    'selected_uwis': self.selected_uwis,
                    'depth_grid_colors': self.depth_grid_color_df.to_dict(orient='list') if isinstance(self.depth_grid_color_df, pd.DataFrame) else {},
                    'grid_info': self.grid_info_df.to_dict(orient='list') if isinstance(self.grid_info_df, pd.DataFrame) else {},
                }
                with open(self.project_file_name, 'w') as file:
                    json.dump(self.project_data, file, indent=4)
                self.export_menu.setEnabled(True)
                self.launch_menu.setEnabled(True)




    def dataload_well_zones(self):
        dialog = DataLoadWellZonesDialog(self.selected_uwis)
        if dialog.exec_() == QDialog.Accepted:
            result = dialog.import_data()
            if result:
                df, attribute_type, zone_name, zone_type, uwi_header, top_depth_header, base_depth_header = result

                # Append the new data to the existing DataFrame
                if not self.master_df.empty:
                    self.master_df = pd.concat([self.master_df, df], ignore_index=True)
                else:
                    self.master_df = df

                # Update zone names
                self.zone_names.extend(zone_name)
                self.zone_names = list(set(self.zone_names))

                # Set display options to print all columns and rows
                pd.set_option('display.max_columns', None)
                pd.set_option('display.max_rows', None)

                # Print the updated DataFrame to verify the contents
                print(self.master_df)

                # Load existing project data
                if os.path.exists(self.project_file_name):
                    with open(self.project_file_name, 'r') as file:
                        self.project_data = json.load(file)
                else:
                    self.project_data = {}

                # Update project data with the new export options
                self.project_data['master_df'] = self.master_df.to_dict()

                # Save the updated project data to the JSON file
                with open(self.project_file_name, 'w') as file:
                    json.dump(self.project_data, file, indent=4)

                self.export_menu.setEnabled(True)
                self.launch_menu.setEnabled(True)



    def populate_grid_dropdown(self):
        if not hasattr(self, 'grid_info_df'):
            self.get_grid_names_and_store_info()  # Ensure grid_info_df is populated

        self.gridDropdown.clear()
        self.gridDropdown.addItem("Select Grid")

        # Get grid names from the grid_info_df
        grid_names = self.grid_info_df['Grid'].tolist()
        self.gridDropdown.addItems(grid_names)


    def launch_zone_viewer(self):
        print(self.master_df)
        if not self.master_df.empty:
            dialog = ZoneViewerDialog(self.master_df, self.zone_names, self.selected_uwis, self)

            dialog.exec_()


    def handle_well_attributes(self, df, uwi_header):
        # Implement logic to handle well attributes
        pass

    def handle_zone_attributes(self, df, uwi_header, top_depth_header, base_depth_header, zone_name, zone_type):
        # Implement logic to handle zone attributes
        pass




    def open_from_file(self):
        self.open = True

        options = QFileDialog.Options()
        file_name, _ = QFileDialog.getOpenFileName(self, "Open File", "", "JSON Files (*.json);;All Files (*)", options=options)
        if file_name:
            self.project_file_name = file_name
            with open(file_name, 'r') as file:
                data_loaded = json.load(file)

            # Load DataFrames from JSON if they exist
            self.directional_surveys_df = pd.DataFrame(data_loaded.get('directional_surveys', {}))
            self.depth_grid_data_df = pd.DataFrame(data_loaded.get('depth_grid_data', {}))
            self.attribute_grid_data_df = pd.DataFrame(data_loaded.get('attribute_grid_data', {}))
            self.import_options_df = pd.DataFrame(data_loaded.get('import_options', {}))
            self.selected_uwis = data_loaded.get('selected_uwis', [])
            self.depth_grid_color_df = pd.DataFrame(data_loaded.get('depth_grid_colors', {}))
            self.grid_info_df = pd.DataFrame(data_loaded.get('grid_info', {}))
           
            # Populate the grid dropdown with grid names
            self.populate_grid_dropdown()

            # Enable menus and update window title
            self.import_menu.setEnabled(True)
            self.launch_menu.setEnabled(True)
            file_basename = os.path.basename(file_name)
            self.setWindowTitle(f"Zone Analyzer - {file_basename}")

            # Update data in the application
            self.setData(self.directional_surveys_df)
            self.set_interactive_elements_enabled(True)
            self.populate_grid_dropdown()

            self.open = False  

    def plot_data(self, uwi=None):
        if not self.depth_grid_data_df.empty:
            try:
                if uwi:
                    selected_data = self.depth_grid_data_df[self.grid_well_data_df['UWI'] == uwi]
                    navigator = Plot(selected_data, self.depth_grid_color_df, parent=self)
                else:
                    navigator = Plot(self.grid_well_data_df, self.depth_grid_color_df,  parent=self)
                navigator.show()
            except Exception as e:
                print(f"Error initializing Plot: {e}")
                self.show_info_message("Error", f"Failed to initialize plot navigator: {e}")
        else:
            self.show_info_message("Info", "No grid well data available to plot.")



    def export(self):
        app = QApplication.instance()
        if app is None:
            app = QApplication([])

        if self.export_options is not None and not self.export_options.empty:
            dialog = ExportDialog(self.grid_well_data_df, self.well_info_df, self.zonein_info_df, self.top_grid_df, self.bottom_grid_df, self.total_zone_number, self.export_options)
        else:
            dialog = ExportDialog(self.grid_well_data_df, self.well_info_df, self.zonein_info_df, self.top_grid_df, self.bottom_grid_df, self.total_zone_number)

        dialog.exec_()

        if hasattr(dialog, 'export_options') and dialog.export_options is not None:
            self.export_options = dialog.export_options

            # Profile start time
            start_time = time.time()

            # Load existing project data
            if os.path.exists(self.project_file_name):
                with open(self.project_file_name, 'r') as file:
                    self.project_data = json.load(file)
        
            print("Time to load project data: {:.2f} seconds".format(time.time() - start_time))

            # Update project data with the new export options
            self.project_data['export_options'] = self.export_options.to_dict() if isinstance(self.export_options, pd.DataFrame) else {}

            # Profile update time
            update_time = time.time()
        
            # Save the updated project data to the same file
            with open(self.project_file_name, 'w') as file:
                json.dump(self.project_data, file)  # Reduced or no indentation
        
            print("Time to save project data: {:.2f} seconds".format(time.time() - update_time))
            print("Export options saved to file:", self.project_file_name)
            print(self.export_options)
        
            # Total time
            print("Total export time: {:.2f} seconds".format(time.time() - start_time))

    def mapproperties(self):
        # Create a copy of the DataFrame
        zone_color_df_copy = self.zone_color_df.copy()
        # Pass the copy to the dialog
        dialog = SWPropertiesEdit(zone_color_df_copy)
        dialog.exec_()

    def export_to_sw(self):
        self.connection = SeisWare.Connection()
        try:
            serverInfo = SeisWare.Connection.CreateServer()
            self.connection.Connect(serverInfo.Endpoint(), 50000)
        except RuntimeError as err:
            self.show_error_message("Connection Error", f"Failed to connect to the server: {err}")
            return

        self.project_list = SeisWare.ProjectList()
        try:
            self.connection.ProjectManager().GetAll(self.project_list)
        except RuntimeError as err:
            self.show_error_message("Error", f"Failed to get the project list from the server: {err}")
            return

        project_name = self.import_options_df.get('Project', [''])[0]

        self.projects = [project for project in self.project_list if project.Name() == project_name]
      
        if not self.projects:
            self.show_error_message("Error", "No project was found")
            return

        self.login_instance = SeisWare.LoginInstance()
        try:
            self.login_instance.Open(self.connection, self.projects[0])
        except RuntimeError as err:
            self.show_error_message("Error", "Failed to connect to the project: " + str(err))
            return

        well_manager = self.login_instance.WellManager()
        zone_manager = self.login_instance.ZoneManager()
        zone_type_manager = self.login_instance.ZoneTypeManager()
        well_zone_manager = self.login_instance.WellZoneManager()

        well_list = SeisWare.WellList()
        zone_list = SeisWare.ZoneList()
        zone_type_list = SeisWare.ZoneTypeList()

        try:
            well_manager.GetAll(well_list)
            zone_manager.GetAll(zone_list)
            zone_type_manager.GetAll(zone_type_list)
        except SeisWare.SDKException as e:
            print("Failed to get necessary data.")
            print(e)
            return 1

        zone_type_name = "DrilledZone"
        zone_type_exists = any(zone_type.Name() == zone_type_name for zone_type in zone_type_list)

        if not zone_type_exists:
            new_zone_type = SeisWare.ZoneType()
            new_zone_type.Name(zone_type_name)
            try:
                zone_type_manager.Add(new_zone_type)
                zone_type_manager.GetAll(zone_type_list)
                print(f"Successfully added new zone type: {zone_type_name}")
            except SeisWare.SDKException as e:
                print(f"Failed to add the new zone type: {zone_type_name}")
                print(e)
                return 1
        else:
            print(f"Zone type '{zone_type_name}' already exists.")

        drilled_zone_type_id = next((zone_type.ID() for zone_type in zone_type_list if zone_type.Name() == zone_type_name), None)
        if drilled_zone_type_id is None:
            print(f"Failed to retrieve the ID for zone type: {zone_type_name}")
            return 1

        for index, row in self.zonein_info_df.iterrows():
            zone_name = row['Zone Name']
            if not any(zone.Name() == zone_name for zone in zone_list):
                new_zone = SeisWare.Zone()
                new_zone.Name(zone_name)
                try:
                    zone_manager.Add(new_zone)
                    zone_manager.GetAll(zone_list)
                    print(f"Successfully added new zone: {zone_name}")
                except SeisWare.SDKException as e:
                    print(f"Failed to add the new zone: {zone_name}")
                    print(e)
                    return 1
            else:
                print(f"Zone '{zone_name}' already exists.")

        well_map = {well.UWI(): well for well in well_list}
        zone_map = {zone.Name(): zone for zone in zone_list}

        for index, row in self.zonein_info_df.iterrows():
            well_uwi = row['UWI']
            if well_uwi not in well_map:
                print(f"No well was found for UWI {well_uwi} in row {index}")
                continue

            well = well_map[well_uwi]
            well_id = well.ID()

            zone_name = row['Zone Name']
            if zone_name not in zone_map:
                print(f"No zone was found for name {zone_name} in row {index}")
                continue

            zone = zone_map[zone_name]

            new_well_zone = SeisWare.WellZone()

            try:
                new_well_zone.WellID(well_id)
                new_well_zone.Zone(zone)
                new_well_zone.ZoneTypeID(drilled_zone_type_id)
                new_well_zone.TopMD(SeisWare.Measurement(row['MD Top Depth Meters'], SeisWare.Unit.Meter))
                new_well_zone.BaseMD(SeisWare.Measurement(row['MD Base Depth Meters'], SeisWare.Unit.Meter))
            except KeyError as e:
                print(f"Invalid data for well zone in row {index}: {e}")
                continue
            print(new_well_zone)
            try:
                well_zone_manager.Add(new_well_zone)
                print(f"Successfully added well zone for UWI {well_uwi}")
            except SeisWare.SDKException as e:
                print(f"Failed to add well zone for UWI {well_uwi}")
                print(e)
                continue

        return 0

    def mousePressEvent(self, event):
        if self.drawing:
            if event.button() == Qt.LeftButton:
                self.handle_left_click(event)
            elif event.button() == Qt.RightButton:
                self.handle_right_click()
            return

        if event.button() == Qt.RightButton:
            canvas_height = self.drawingArea.height()
            point = self.scrollArea.widget().mapFromGlobal(event.globalPos())
            adjusted_x = (point.x() + self.scrollArea.horizontalScrollBar().value()) / self.drawingArea.scale
            adjusted_y = canvas_height - ((point.y() + self.scrollArea.verticalScrollBar().value()) / self.drawingArea.scale)
            adjusted_point = QPointF(adjusted_x, adjusted_y)

            if adjusted_point.x() < 0 or adjusted_point.y() < 0:
                print(f"Warning: Adjusted point is out of bounds: {adjusted_point}")

            closest_uwi = self.find_closest_uwi(adjusted_point)
            if closest_uwi:
                self.plot_data(closest_uwi)
                self.drawingArea.hovered_uwi = closest_uwi  
                self.drawingArea.update()

    def handle_left_click(self, event):
        # Get the click position within the scroll area
        point = self.scrollArea.widget().mapFromGlobal(event.globalPos())

        # Adjust the point for the current zoom level and scroll position
        adjusted_x = point.x() + self.scrollArea.horizontalScrollBar().value()
        adjusted_y = point.y() + self.scrollArea.verticalScrollBar().value()

        # Convert the adjusted point to the drawing area's coordinate system
        scaled_x = adjusted_x / self.drawingArea.scale
        scaled_y = adjusted_y / self.drawingArea.scale

        print(f"Click at: ({scaled_x}, {scaled_y})")  # Debugging statement

        # Update the current line and click points
        self.currentLine.append(QPointF(scaled_x, scaled_y))
        self.originalCurrentLine.append((scaled_x, scaled_y))
        self.drawingArea.setCurrentLine(self.currentLine)
        print(self.currentLine)
        self.drawingArea.addClickPoint(QPointF(scaled_x, scaled_y))
        # Add this line to add a node
        self.lastPoint = QPointF(scaled_x, scaled_y)
        self.scaled_points.append((scaled_x, scaled_y))
        self.drawingArea.update()

    def handle_right_click(self):
        canvas_height = self.drawingArea.height()
        self.drawing = False

        self.drawingArea.setCurrentLine(self.currentLine)
        self.lastPoint = None

        self.intersections = []
        self.intersectionPoints = []
        self.originalIntersectionPoints = []

        if len(self.currentLine) > 1:
            # Convert current line points to the scaled_data coordinate system
            new_line_coords = [self.map_to_data_coords(point) for point in self.currentLine]

            segment_lengths = []
            for i in range(len(new_line_coords) - 1):
                first_x, first_y = new_line_coords[i]
                last_x, last_y = new_line_coords[i + 1]

                segment_length = math.sqrt((last_x - first_x) ** 2 + (last_y - first_y) ** 2)
                segment_lengths.append(segment_length)

            segment_number = 0
            total_cumulative_distance = 0

            for i in range(len(new_line_coords) - 1):
                first_x, first_y = new_line_coords[i]
                last_x, last_y = new_line_coords[i + 1]
                segment = LineString([(first_x, first_y), (last_x, last_y)])

                for uwi, scaled_offsets in self.scaled_data.items():
                    well_line_points = [(point.x(), point.y(), tvd) for point, tvd in scaled_offsets]
                    well_line_coords = [(x, y) for x, y, tvd in well_line_points]
                    well_line = LineString(well_line_coords)

                    if segment.intersects(well_line):
                        intersection = segment.intersection(well_line)

                        if isinstance(intersection, Point):
                            points = [intersection]
                        elif isinstance(intersection, MultiPoint):
                            points = list(intersection.geoms)
                        elif isinstance(intersection, GeometryCollection):
                            points = [geom for geom in intersection.geoms if isinstance(geom, Point)]
                        else:
                            points = []

                        for point in points:
                            intersection_qpoint = self.data_to_map_coords(QPointF(point.x, point.y))
                            self.originalIntersectionPoints.append(intersection_qpoint)
                            tvd_value = self.calculate_interpolated_tvd(point, well_line_points)
                            cumulative_distance = total_cumulative_distance + math.sqrt((point.x - first_x) ** 2 + (point.y - first_y) ** 2)
                            self.intersections.append((uwi, point.x, point.y, tvd_value, cumulative_distance))

                total_cumulative_distance += segment_lengths[i]
                segment_number += 1

        actions_to_toggle = [self.plot_tool_action, self.gun_barrel_action, self.data_loader_menu]
        self.set_interactive_elements_enabled(True)
        for action in actions_to_toggle:
            action.setEnabled(True)
        self.drawingArea.setIntersectionPoints(self.originalIntersectionPoints)
        self.plot_gun_barrel()

    def map_to_data_coords(self, point):
        """Convert point from map coordinates to data coordinates."""
        scale_x = self.drawingArea.width() / (self.drawingArea.max_x - self.drawingArea.min_x)
        scale_y = self.drawingArea.height() / (self.drawingArea.max_y - self.drawingArea.min_y)
        data_x = point.x() / scale_x + self.drawingArea.min_x
        data_y = self.drawingArea.max_y - point.y() / scale_y
        return data_x, data_y

    def data_to_map_coords(self, point):
        """Convert point from data coordinates to map coordinates."""
        scale_x = self.drawingArea.width() / (self.drawingArea.max_x - self.drawingArea.min_x)
        scale_y = self.drawingArea.height() / (self.drawingArea.max_y - self.drawingArea.min_y)
        map_x = (point.x() - self.drawingArea.min_x) * scale_x
        map_y = (self.drawingArea.max_y - point.y()) * scale_y
        return QPointF(map_x, map_y)

    def calculate_interpolated_tvd(self, intersection, well_line_points):
        intersection_coords = (intersection.x, intersection.y)
        for i in range(len(well_line_points) - 1):
            x1, y1, tvd1 = well_line_points[i]
            x2, y2, tvd2 = well_line_points[i + 1]

            if self.is_between(intersection_coords, (x1, y1), (x2, y2)):
                dist_total = ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5
                dist_to_intersection = ((intersection.x - x1) ** 2 + (intersection.y - y1) ** 2) ** 0.5
                weight = dist_to_intersection / dist_total
                tvd_value = tvd1 + weight * (tvd2 - tvd1)
                return tvd_value
        return None

    def is_between(self, point, point1, point2):
        cross_product = (point[1] - point1[1]) * (point2[0] - point1[0]) - (point[0] - point1[0]) * (point2[1] - point1[1])
        if abs(cross_product) > 1e-6:
            return False

        dot_product = (point[0] - point1[0]) * (point2[0] - point1[0]) + (point[1] - point1[1]) * (point2[1] - point1[1])
        if dot_product < 0:
            return False

        squared_length = (point2[0] - point1[0]) ** 2 + (point2[1] - point1[1]) ** 2
        if dot_product > squared_length:
            return False

        return True

    def find_closest_uwi(self, point):
        min_distance = float('inf')
        closest_uwi = None
        point_array = np.array([point.x(), point.y()])

        for uwi, scaled_offsets in self.scaled_data.items():
            scaled_points = np.array([[p.x(), p.y()] for p, tvd in scaled_offsets])
            distances = np.linalg.norm(scaled_points - point_array, axis=1)
            min_idx = np.argmin(distances)
            distance = distances[min_idx]

            if distance < min_distance:
                min_distance = distance
                closest_uwi = uwi
                print(f"New closest UWI: {closest_uwi}, Distance: {min_distance}")

        print(f"Found closest UWI: {closest_uwi} with distance: {min_distance}")
        return closest_uwi

    def toggleDrawing(self):
        self.drawing = not self.drawing
        self.intersectionPoints = []
        self.currentLine = []
        self.scaled_points = []

        actions_to_toggle = [self.plot_tool_action, self.export_action, self.data_loader_menu]
        if self.drawing:
            print("Drawing mode is ON")
            self.gun_barrel_action.setChecked(True)
            self.drawingArea.clearCurrentLineAndIntersections()
            actions_to_toggle = [self.plot_tool_action, self.gun_barrel_action, self.data_loader_menu]
            self.set_interactive_elements_enabled(False) 
            for action in actions_to_toggle:
                action.setEnabled(False)
        else:
            print("Drawing mode is OFF")
            for action in actions_to_toggle:
                action.setEnabled(True)
        self.update()

    def plot_gun_barrel(self):
        new_line_coords = [self.map_to_data_coords(point) for point in self.currentLine]
        print(new_line_coords)
        if len(new_line_coords) < 2:
            QMessageBox.warning(self, "Warning", "You need to draw a line first.")
            return

        self.plot_gb = PlotGB(self.depth_grid_data_df, self.depth_grid_color_df, new_line_coords, self.intersections, main_app=self)
        self.plot_gb.show()

    def open_color_editor(self):
        editor = ColorEditor(self.zone_color_df, self)
        editor.color_changed.connect(self.update_zone_colors)
        editor.exec_()

    def update_zone_colors(self, updated_df):
        self.zone_color_df = updated_df
        self.drawingArea.setScaledData(self.scaled_data, self.zone_color_df)

    def handle_hover_event(self, uwi):
        self.drawingArea.hovered_uwi = uwi  
        self.drawingArea.update()

    def show_error_message(self, title, message):
        msg_box = QMessageBox(self)
        msg_box.setIcon(QMessageBox.Critical)
        msg_box.setWindowTitle(title)
        msg_box.setText(message)
        msg_box.exec_()

    def show_info_message(self, title, message):
        msg_box = QMessageBox(self)
        msg_box.setIcon(QMessageBox.Information)
        msg_box.setWindowTitle(title)
        msg_box.setText(message)
        msg_box.exec_()


if __name__ == "__main__":
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
    app = QApplication(sys.argv)
    window = Map()
    window.show()
    sys.exit(app.exec_())
