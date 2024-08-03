
import SeisWare
import pandas as pd
import numpy as np
from scipy.spatial import KDTree

from Exporting import ExportDialog
from PySide2.QtWidgets import QApplication, QFileDialog, QMainWindow, QSpinBox,QSpacerItem, QToolBar
from PySide2.QtWidgets import QSizePolicy,QApplication,  QDialog, QWidget,QAbstractItemView, QVBoxLayout, QHBoxLayout,QMenu, QMenuBar, QLabel, QPushButton, QListWidget, QComboBox, QLineEdit, QScrollArea, QMenu, QMessageBox, QErrorMessage
from PySide2.QtCore import Qt
import SeisWare
from PySide2.QtGui import QIcon, QColor


class DataLoaderDialog(QDialog):
    def __init__(self, import_options_df=None, parent=None):
        super(DataLoaderDialog, self).__init__(parent)
        self.setWindowTitle("Load Data")
        self.setGeometry(100, 100, 800, 600)
        self.setupUi()
        self.connect_to_seisware()
        self.import_options_df = import_options_df
        if self.import_options_df is not None:
            self.set_import_parameters(self.import_options_df)


    def setupUi(self):
        layout = QVBoxLayout(self)

        label_width = 120
        dropdown_width = 240

        # Project
        project_layout = QHBoxLayout()
        self.project_label = QLabel("Project:")
        self.project_label.setFixedWidth(label_width)
        self.project_dropdown = QComboBox()
        self.project_dropdown.setFixedWidth(dropdown_width)
        project_layout.addWidget(self.project_label)
        project_layout.addWidget(self.project_dropdown)
        project_layout.addStretch()
        layout.addLayout(project_layout)

        # Well Filter
        filter_layout = QHBoxLayout()
        self.filter_label = QLabel("Well Filter:")
        self.filter_label.setFixedWidth(label_width)
        self.filter_dropdown = QComboBox()
        self.filter_dropdown = QComboBox()
        self.filter_dropdown.setFixedWidth(dropdown_width)
        filter_layout.addWidget(self.filter_label)
        filter_layout.addWidget(self.filter_dropdown)
        filter_layout.addStretch()
        layout.addLayout(filter_layout)

        # Layout for UWI list boxes and arrows
        list_layout = QHBoxLayout()

        self.uwi_listbox = QListWidget()
        self.uwi_listbox.setSelectionMode(QAbstractItemView.ExtendedSelection)
        list_layout.addWidget(self.uwi_listbox)

        arrow_layout = QVBoxLayout()

        arrow_layout.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding))

        self.move_all_right_button = QPushButton()
        self.move_all_right_button.setIcon(QIcon("icons/arrow_double_right.png"))
        self.move_all_right_button.clicked.connect(self.move_all_right)
        arrow_layout.addWidget(self.move_all_right_button)

        self.move_right_button = QPushButton()
        self.move_right_button.setIcon(QIcon("icons/arrow_right.ico"))
        self.move_right_button.clicked.connect(self.move_selected_right)
        arrow_layout.addWidget(self.move_right_button)

        self.move_left_button = QPushButton()
        self.move_left_button.setIcon(QIcon("icons/arrow_left.ico"))
        self.move_left_button.clicked.connect(self.move_selected_left)
        arrow_layout.addWidget(self.move_left_button)

        self.move_all_left_button = QPushButton()
        self.move_all_left_button.setIcon(QIcon("icons/arrow_double_left.png"))
        self.move_all_left_button.clicked.connect(self.move_all_left)
        arrow_layout.addWidget(self.move_all_left_button)

        arrow_layout.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding))

        list_layout.addLayout(arrow_layout)

        self.selected_uwi_listbox = QListWidget()
        self.selected_uwi_listbox.setSelectionMode(QAbstractItemView.ExtendedSelection)
        list_layout.addWidget(self.selected_uwi_listbox)

        layout.addLayout(list_layout)

        # Top Grid
        top_grid_layout = QHBoxLayout()
        self.grid_top_label = QLabel("Top Grid:")
        self.grid_top_label.setFixedWidth(label_width)
        self.grid_combobox = QComboBox()
        self.grid_combobox.setFixedWidth(dropdown_width)
        top_grid_layout.addWidget(self.grid_top_label)
        top_grid_layout.addWidget(self.grid_combobox)
        top_grid_layout.addStretch()
        layout.addLayout(top_grid_layout)

        # Bottom Grid
        bottom_grid_layout = QHBoxLayout()
        self.grid_bottom_label = QLabel("Bottom Grid:")
        self.grid_bottom_label.setFixedWidth(label_width)
        self.grid_bottom_combobox = QComboBox()
        self.grid_bottom_combobox.setFixedWidth(dropdown_width)
        bottom_grid_layout.addWidget(self.grid_bottom_label)
        bottom_grid_layout.addWidget(self.grid_bottom_combobox)
        bottom_grid_layout.addStretch()
        layout.addLayout(bottom_grid_layout)

        # Zones
        zones_layout = QHBoxLayout()
        self.number_of_zones_label = QLabel("Zones:")
        self.number_of_zones_label.setFixedWidth(label_width)
        self.number_of_zones = QSpinBox()
        self.number_of_zones.setValue(6)
        self.number_of_zones.setFixedWidth(dropdown_width)
        zones_layout.addWidget(self.number_of_zones_label)
        zones_layout.addWidget(self.number_of_zones)
        zones_layout.addStretch()
        layout.addLayout(zones_layout)

        self.calculate_button = QPushButton("Calculate")
        self.calculate_button.clicked.connect(self.calculate_grid_well_data)
        self.calculate_button.setFixedWidth(dropdown_width)
        layout.addWidget(self.calculate_button)

        self.connection = None
       
        self.project_var = ""
        self.well_list = []
        self.project_names = []
        self.project_list = []
        self.curve_calibration_dict = {}
        self.filter_name = ""
        self.grid_xyz_top = []
        self.grid_well_data = []
        self.total_zone_number = None
        self.grid_df = pd.DataFrame()
        self.directional_survey_values = []
        self.Grid_intersec_top = []
        self.Grid_intersec_bottom = []
        self.selected_item = None
        self.uwis_and_offsets = []
        self.line_segments = []
        self.x_data = []
        self.y_data = []
        self.selected_uwis = []
        self.zonein_info_df = pd.DataFrame()
        self.zone_color_df = pd.DataFrame()
        self.grid_well_data_df = pd.DataFrame()
        self.well_info_df = pd.DataFrame()
        self.export_options = pd.DataFrame
        self.closest_well = None
     



    def set_import_parameters(self, import_options_df):
        if not import_options_df.empty:
            self.project_dropdown.setCurrentText(import_options_df.get('Project', [''])[0])
            self.filter_dropdown.setCurrentText(import_options_df.get('Well Filter', [''])[0])
            self.grid_combobox.setCurrentText(import_options_df.get('Top Grid', [''])[0])
            self.grid_bottom_combobox.setCurrentText(import_options_df.get('Bottom Grid', [''])[0])
            self.number_of_zones.setValue(import_options_df.get('Number of Zones', [0])[0])
        
            selected_uwis = import_options_df.get('selected_uwis', [[]])[0]

            for i in range(self.uwi_listbox.count() - 1, -1, -1):
                if self.uwi_listbox.item(i).text() in selected_uwis:
                    self.uwi_listbox.takeItem(i)
            if isinstance(selected_uwis, list):  # Ensure selected_uwis is a list
                self.selected_uwi_listbox.clear()
                self.selected_uwi_listbox.addItems(selected_uwis)

    def move_selected_right(self):
        selected_items = self.uwi_listbox.selectedItems()
        for item in selected_items:
            self.selected_uwi_listbox.addItem(item.text())
            self.uwi_listbox.takeItem(self.uwi_listbox.row(item))

    def move_selected_left(self):
        selected_items = self.selected_uwi_listbox.selectedItems()
        for item in selected_items:
            self.uwi_listbox.addItem(item.text())
            self.selected_uwi_listbox.takeItem(self.selected_uwi_listbox.row(item))

    def move_all_right(self):
        while self.uwi_listbox.count() > 0:
            item = self.uwi_listbox.takeItem(0)
            self.selected_uwi_listbox.addItem(item)

    def move_all_left(self):
        while self.selected_uwi_listbox.count() > 0:
            item = self.selected_uwi_listbox.takeItem(0)
            self.uwi_listbox.addItem(item)

    def connect_to_seisware(self):
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

        self.project_names = [project.Name() for project in self.project_list]
        self.project_dropdown.addItems(self.project_names)
        self.project_dropdown.setCurrentIndex(-1)
        self.project_dropdown.currentIndexChanged.connect(self.on_project_select)


    def on_project_select(self, index):
       
        self.reset_ui_and_data()
      

  
        
        
        project_name = self.project_dropdown.currentText()

        self.projects = [project for project in self.project_list if project.Name() == project_name]
        if not self.projects:
            self.show_error_message("Error", "No project was found")
            return

        self.login_instance = SeisWare.LoginInstance()
        try:
            self.login_instance.Open(self.connection, self.projects[0])
            print(self.projects[0])
        except RuntimeError as err:
            self.show_error_message("Error", "Failed to connect to the project: " + str(err))
            return
        
        if self.open == False:
            self.hide_working_message()

        self.well_filter = SeisWare.FilterList()
        try:
            self.login_instance.FilterManager().GetAll(self.well_filter)
        except RuntimeError as err:
            self.show_error_message("Error", f"Failed to filters: {err}")
            return



        filter_list = []
        for filter in self.well_filter:
            filter_type = filter.FilterType()
            if filter_type == 2:
                filter_name = filter.Name()
                filter_info = f"{filter_name}"
                filter_list.append(filter_info)

        self.filter_dropdown.clear()
        self.filter_dropdown.addItems(filter_list)
        self.filter_dropdown.blockSignals(True)
        self.filter_dropdown.setCurrentIndex(-1)
        self.filter_dropdown.blockSignals(False)
        self.filter_dropdown.currentIndexChanged.connect(self.on_filter_select)
       
        self.grid_list = SeisWare.GridList()
        try:
            self.login_instance.GridManager().GetAll(self.grid_list)
        except RuntimeError as err:
            self.show_error_message("Failed to get the grids from the project", err)
        self.grids = [grid.Name() for grid in self.grid_list]
        self.grid_objects_with_names = [(grid, grid.Name()) for grid in self.grid_list]

        self.grid_combobox.clear()

        self.grid_combobox.addItems(self.grids)
        
        
        self.grid_combobox.blockSignals(True)
        self.grid_combobox.setCurrentIndex(-1)
        self.grid_bottom_combobox.clear()
        self.grid_combobox.blockSignals(False)
        self.grid_bottom_combobox.addItems(self.grids)
        self.grid_combobox.currentIndexChanged.connect(self.on_grid_select)

        self.grid_bottom_combobox.blockSignals(True)
        
        self.grid_bottom_combobox.setCurrentIndex(-1)
        self.grid_bottom_combobox.blockSignals(False)
        self.grid_bottom_combobox.currentIndexChanged.connect(self.on_grid_select_bottom)
       


    def on_filter_select(self, index):
        self.uwi_listbox.clear()
        self.selected_uwi_listbox.clear()

        selected_filter = self.filter_dropdown.currentText()
        well_filter = SeisWare.FilterList()
        self.login_instance.FilterManager().GetAll(well_filter)
        well_filter = [i for i in well_filter if i.Name() == selected_filter]

        keys = SeisWare.IDSet()
        failed_keys = SeisWare.IDSet()
        well_list = SeisWare.WellList()

        try:
            self.login_instance.WellManager().GetKeysByFilter(well_filter[0], keys)
            self.login_instance.WellManager().GetByKeys(keys, well_list, failed_keys)
        except RuntimeError as err:
            self.show_error_message("Failed to get all the wells from the project", err)
            return

        self.well_list = [well.UWI() for well in well_list]
        self.uwi_to_well_dict = {well.UWI(): well for well in well_list}
        self.load_uwi_list()

    def load_uwi_list(self):

        sorted_uwi_list = sorted(self.well_list, reverse=False)
        self.uwi_listbox.addItems(sorted_uwi_list)

    def on_grid_select(self):
        grid_name = self.grid_combobox.currentText()
        selected_grid_object = None
        for grid, name in self.grid_objects_with_names:
            if name == grid_name:
                selected_grid_object = grid
                break
       
     
        try:
            self.login_instance.GridManager().PopulateValues(selected_grid_object)
        except RuntimeError as err:
            self.show_error_message("Failed to populate the values of grid %s from the project" % (grid), err)
    
        grid_values = SeisWare.GridValues()
        grid.Values(grid_values)
        
        # Fill a DF with X, Y, Z values
        self.grid_xyz_top = []
        grid_values_list = list(grid_values.Data())
       
        counter = 0
        for i in range(grid_values.Height()):
            for j in range(grid_values.Width()):
                self.grid_xyz_top.append((grid.Definition().RangeY().start + i * grid.Definition().RangeY().delta,
                                grid.Definition().RangeX().start + j * grid.Definition().RangeX().delta,
                                grid_values_list[counter]))
                counter += 1
              
        # Create DataFrame
      
        self.top_grid_df = pd.DataFrame(self.grid_xyz_top, columns=["Y", "X", f"{grid.Name()}"])
        #print(self.grid_xyz_top)
        #print(self.top_grid_df)

    def on_grid_select_bottom(self):
        grid_name = self.grid_bottom_combobox.currentText()
        selected_grid_object = None
        for grid, name in self.grid_objects_with_names:
            if name == grid_name:
                selected_grid_object = grid
                break
    
     

        try:
            self.login_instance.GridManager().PopulateValues(selected_grid_object)
        except RuntimeError as err:
            self.show_error_message("Failed to populate the values of grid %s from the project" % (grid), err)
    
            

        grid_values = SeisWare.GridValues()
        grid.Values(grid_values)
        
        # Fill a DF with X, Y, Z values
        self.grid_xyz_bottom = []
      
        grid_values_list = list(grid_values.Data())
      
        counter = 0
        for i in range(grid_values.Height()):
            for j in range(grid_values.Width()):
                self.grid_xyz_bottom.append((grid.Definition().RangeY().start + i * grid.Definition().RangeY().delta,
                                grid.Definition().RangeX().start + j * grid.Definition().RangeX().delta,
                                grid_values_list[counter]))
                counter += 1
               
        # Create DataFrame
   
        self.bottom_grid_df = pd.DataFrame(self.grid_xyz_bottom, columns=["Y", "X", f"{grid.Name()}"])

    def store_uwis_and_offsets(self):
        self.uwis_and_offsets = []
        self.md_and_offsets = []
        self.total_lat_data = []
        self.selected_uwis = [self.selected_uwi_listbox.item(i).text() for i in range(self.selected_uwi_listbox.count())]
        if not self.selected_uwis:
            self.show_info_message("Info", "No wells selected for export.")
            return

        for uwi in self.selected_uwis:
            well = self.uwi_to_well_dict.get(uwi)
            if well:
                depth_unit = SeisWare.Unit.Meter
                x_offsets = []
                y_offsets = []
                md_values = []
                tvd_values = []

                surfaceX = well.TopHole().x.Value(depth_unit)
                surfaceY = well.TopHole().y.Value(depth_unit)
                surfaceDatum = well.DatumElevation().Value(depth_unit)

                dirsrvylist = SeisWare.DirectionalSurveyList()
                self.login_instance.DirectionalSurveyManager().GetAllForWell(well.ID(), dirsrvylist)
                dirsrvy = [i for i in dirsrvylist if i.OffsetNorthType() > 0]

                if dirsrvy:
                    self.login_instance.DirectionalSurveyManager().PopulateValues(dirsrvy[0])
                    srvypoints = SeisWare.DirectionalSurveyPointList()
                    dirsrvy[0].Values(srvypoints)

                    previous_md = None
                    previous_tvd = None
                    start_lat = None
                    total_lat = 0

                    for i in srvypoints:
                        x_offset = surfaceX + i.xOffset.Value(depth_unit)
                        y_offset = surfaceY + i.yOffset.Value(depth_unit)
                        tvd = surfaceDatum - i.tvd.Value(depth_unit)
                        md = i.md.Value(depth_unit)

                        if previous_md is not None and previous_tvd is not None:
                            delta_md = md - previous_md
                            delta_tvd = tvd - previous_tvd
                            inclination = np.degrees(np.arccos(delta_tvd / delta_md)) if delta_md != 0 else None
                        else:
                            inclination = None

                        if inclination is not None and inclination < 360:
                            x_offsets.append(x_offset)
                            y_offsets.append(y_offset)
                            md_values.append(md)
                            tvd_values.append(tvd)
                            if start_lat is None:
                                start_lat = md

                        previous_md = md
                        previous_tvd = tvd

                    end_lat = md
                    if start_lat is not None:
                        total_lat = end_lat - start_lat

                    self.uwis_and_offsets.append((uwi, x_offsets, y_offsets))
                    self.md_and_offsets.append((uwi, md_values, tvd_values, x_offsets, y_offsets))
                    print(self.md_and_offsets)
                    self.total_lat_data.append((uwi, total_lat, surfaceX, surfaceY))

                else:
                    self.show_info_message("Warning", f"No directional survey found for well {uwi}.")

    def calculate_zones(self, closest_z_top, closest_z_bottom, number_of_zones):
        if closest_z_top is not None and closest_z_bottom is not None and number_of_zones > 1:
            zone_interval = (closest_z_bottom - closest_z_top) / (number_of_zones - 2)

            zones = [closest_z_top + i * zone_interval for i in range(1, number_of_zones - 2)]
            #print(zones)
        else:
            zones = [closest_z_top, closest_z_bottom]
        return zones

    def calculate_grid_well_data(self):



        self.store_uwis_and_offsets()
        self.grid_well_data = []

        try:
            self.total_zone_number = int(self.number_of_zones.text())
        except ValueError:
            print("Invalid number of zones. Please enter a valid integer.")
            return

        kdtree_top = KDTree([(point[1], point[0]) for point in self.grid_xyz_top]) if self.grid_xyz_top else None
        kdtree_bottom = KDTree([(point[1], point[0]) for point in self.grid_xyz_bottom]) if self.grid_xyz_bottom else None

        for (uwi, total_lat, surfaceX, surfaceY) in self.total_lat_data:
            well = self.uwi_to_well_dict.get(uwi)
            if well:
                depth_unit = SeisWare.Unit.Meter
                surfaceDatum = well.DatumElevation().Value(depth_unit)
                directional_survey_values = [val for val in self.md_and_offsets if val[0] == uwi]
                if not directional_survey_values:
                    continue

                combined_distance = 0
                for survey_point in directional_survey_values:
                    md_values, tvd_values, x_offsets, y_offsets = survey_point[1:]

                    for i, (md, tvd, x_offset, y_offset) in enumerate(zip(md_values, tvd_values, x_offsets, y_offsets)):
                        closest_z_top = self.grid_xyz_top[kdtree_top.query((x_offset, y_offset))[1]][2] if kdtree_top else None
                        closest_z_bottom = self.grid_xyz_bottom[kdtree_bottom.query((x_offset, y_offset))[1]][2] if kdtree_bottom else None
                        zones = self.calculate_zones(closest_z_top, closest_z_bottom, self.total_zone_number)
                        if i > 0:
                            prev_x_offset, prev_y_offset = x_offsets[i - 1], y_offsets[i - 1]
                            combined_distance += np.sqrt((x_offset - prev_x_offset) ** 2 + (y_offset - prev_y_offset) ** 2)

                        entry = [uwi, md, tvd, x_offset, y_offset, combined_distance, closest_z_top] + zones + [closest_z_bottom]
                        self.grid_well_data.append(entry)
                     

        print(f"Grid well data prepared with {len(self.grid_well_data)} entries including zones and combined distances.")
  
        for entry in self.grid_well_data:
            tvd = entry[2]
            zones = entry[6:]
            zone_in = None
            zone_in_name = None
         
            for j in range(len(zones) - 1):

                if j == 0 and tvd > zones[j]:
                    zone_in = 0
                    zone_in_name = 'Zone 0'
                    break
                elif j == len(zones) and tvd <= zones[j]:
                    zone_in = j + 1
                    zone_in_name = f'Zone {j + 1}'
                    break
                elif zones[j] >= tvd > (zones[j + 1]):
                    zone_in = j + 1
                    zone_in_name = f'Zone {j + 1}'
                    break
         


            entry.append(zone_in)
            entry.append(zone_in_name)



        # Construct the DataFrame columns
        max_columns = max(len(entry) for entry in self.grid_well_data)
        base_columns = ['UWI', 'MD', 'TVD', 'X Offset', 'Y Offset', 'Combined Distance']
        zone_columns = [f'Zone {i}' for i in range(max_columns - len(base_columns) - 2)]
        columns = base_columns + zone_columns + ['ZoneIn'] + ['ZoneIn_Name']

        # Convert grid_well_data to DataFrame
        self.grid_well_data_df = pd.DataFrame(self.grid_well_data, columns=columns)

        self.well_info_df = pd.DataFrame(self.total_lat_data, columns=['UWI', 'Total Lateral Length', 'Surface X', 'Surface Y'])
        #print(self.well_info_df)
        project_name = self.project_dropdown.currentText()
        self.zone_color()
        self.extract_zonein_info()
        self.collect_dialog_options()
        self.accept()
        print(self.selected_uwis)
        return self.grid_well_data_df,self.grid_well_data , self.well_info_df, self.zonein_info_df, self.top_grid_df, self.bottom_grid_df, self.total_zone_number, self.zone_color_df, self.export_options, self.import_options_df, self.grid_xyz_top, self.grid_xyz_bottom, project_name, self.selected_uwis
    
    def collect_dialog_options(self):
        selected_uwis = [self.selected_uwi_listbox.item(i).text() for i in range(self.selected_uwi_listbox.count())]
    
        options = {
            'Project': [self.project_dropdown.currentText()],
            'Well Filter': [self.filter_dropdown.currentText()],
            'selected_uwis': [selected_uwis],
            'Top Grid': [self.grid_combobox.currentText()],
            'Bottom Grid': [self.grid_bottom_combobox.currentText()],
            'Number of Zones': [self.number_of_zones.value()]
        }

        self.import_options_df = pd.DataFrame(options)
        return self.import_options_df


    def hex_to_rgb(self, hex_color):
        # Convert hex color to RGB format
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

    def zone_color(self):
        # Determine the zone names from the column headers 6 through -1
        column_headers = self.grid_well_data_df.columns[6:-2]
        #print(column_headers)
        zone_names = [header for header in column_headers]
       

        # Add a new zone for the bottom
        bottom_zone_name = f'Zone {self.total_zone_number-1}'
        zone_names.append(bottom_zone_name)

        # Generate colors for each zone
        num_zones = len(zone_names)
        zone_colors_hex = [
            QColor.fromHsv(int(i * 360 / (1.25 *(num_zones))), 255, 255).toRgb().name(QColor.HexRgb) for i in range(num_zones)
        ]

        # Convert hex colors to RGB
        zone_colors_rgb = [self.hex_to_rgb(color) for color in zone_colors_hex]

        # Create a DataFrame for zone names and colors
        zone_color_df = pd.DataFrame({
            'Zone Name': zone_names,
            'Zone Color (Hex)': zone_colors_hex,
            'Zone Color (RGB)': zone_colors_rgb
        })

        self.zone_color_df = zone_color_df
       # print(self.zone_color_df)

    def extract_zonein_info(self):
    
        df = self.grid_well_data_df
        result = []

        for uwi in df['UWI'].unique():
            df_uwi = df[df['UWI'] == uwi].sort_values('MD')
            current_zonein = df_uwi['ZoneIn'].iloc[0]
            start_md = df_uwi['MD'].iloc[0]

            for i in range(1, len(df_uwi)):
                if df_uwi['ZoneIn'].iloc[i] != current_zonein:
                    end_md = df_uwi['MD'].iloc[i]
                    zone_length = round(end_md - start_md, 2)

                    total_lateral_length = self.well_info_df.loc[self.well_info_df['UWI'] == uwi, 'Total Lateral Length'].values[0]
                    zone_percentage = round((zone_length / total_lateral_length) * 100, 2)

                    result.append({
                        'UWI': uwi,
                        'Zone Name': f'Zone {current_zonein}',
                        'Zone Type': '',
                        'Source': '',
                        'MD Top Depth Meters': round(start_md, 2),
                        'MD Base Depth Meters': round(end_md, 2),
                        'Interval Zone Length Meters': zone_length,
                        'Interval Zone Percentage': zone_percentage
                    })
                    current_zonein = df_uwi['ZoneIn'].iloc[i]
                    start_md = end_md

            end_md = df_uwi['MD'].iloc[-1]
            zone_length = round(end_md - start_md, 2)
            total_lateral_length = self.well_info_df.loc[self.well_info_df['UWI'] == uwi, 'Total Lateral Length'].values[0]
            zone_percentage = round((zone_length / total_lateral_length) * 100, 2)

            result.append({
                'UWI': uwi,
                'Zone Name': f'Zone {current_zonein}',
                'Zone Type': '',
                'Source': '',
                'MD Top Depth Meters': round(start_md, 2),
                'MD Base Depth Meters': round(end_md, 2),
                'Interval Zone Length Meters': zone_length,
                'Interval Zone Percentage': zone_percentage
            })

        self.zonein_info_df = pd.DataFrame(result)

        #print(self.zonein_info_df)
        self.calculate_zone_percentages()


    def calculate_zone_percentages(self):

        df = self.grid_well_data_df
        #print(self.grid_well_data_df)
        zone_percentage_dict = {}

        for uwi in df['UWI'].unique():
            df_uwi = df[df['UWI'] == uwi]
            total_entries = len(df_uwi)
            zone_counts = df_uwi['ZoneIn'].value_counts().to_dict()
            zone_percentages = {f'Zone {zone} Percentage': (count / total_entries) * 100 for zone, count in zone_counts.items()}
            zone_percentage_dict[uwi] = zone_percentages

        zone_percentage_df = pd.DataFrame(zone_percentage_dict).transpose().reset_index().rename(columns={'index': 'UWI'})
        self.well_info_df = self.well_info_df.merge(zone_percentage_df, on='UWI', how='left').fillna(0)
        #print(self.well_info_df)


  
    def show_error_message(self, title, message):
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle(title)
        msg_box.showMessage(message)

    def reset_ui_and_data(self):
        # Reset UI components and internal data
        self.filter_dropdown.blockSignals(True)
        self.filter_dropdown.clear()
        self.filter_dropdown.blockSignals(False)

        self.uwi_listbox.clear()
        self.selected_uwi_listbox.clear()
        self.grid_combobox.blockSignals(True)
        self.grid_combobox.clear()
        self.grid_combobox.blockSignals(False)
        self.grid_bottom_combobox.blockSignals(True)
        self.grid_bottom_combobox.clear()
        self.grid_bottom_combobox.blockSignals(False)

        self.well_list.clear()
        self.curve_calibration_dict.clear()
        self.grid_xyz_top.clear()
        self.grid_well_data.clear()
        self.total_zone_number = None
        self.grid_df = pd.DataFrame()
        self.directional_survey_values.clear()
        self.Grid_intersec_top.clear()
        self.Grid_intersec_bottom.clear()
        self.selected_item = None
        self.uwis_and_offsets.clear()
        self.line_segments.clear()
        self.x_data.clear()
        self.y_data.clear()
        self.zonein_info_df = pd.DataFrame()
        self.grid_well_data_df = pd.DataFrame()
        self.well_info_df = pd.DataFrame()
