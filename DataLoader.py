import sys
import SeisWare
import pandas as pd
from PySide2.QtWidgets import QApplication, QDialog, QLabel, QComboBox, QVBoxLayout, QHBoxLayout, QPushButton, QListWidget, QAbstractItemView, QSizePolicy, QSpacerItem, QMessageBox
from PySide2.QtCore import Qt
from PySide2.QtGui import QIcon, QColor
import numpy as np


class DataLoaderDialog(QDialog):
    def __init__(self, import_options_df=None, parent=None):
        super(DataLoaderDialog, self).__init__(parent)
        self.setWindowTitle("Load Data")
        self.setGeometry(100, 100, 800, 800)  # Adjusted height
        self.setupUi()
        self.connect_to_seisware()
        self.import_options_df = import_options_df
        self.directional_surveys_df = pd.DataFrame()
        self.depth_grid_data_df = pd.DataFrame()
        self.attribute_grid_data_df = pd.DataFrame()
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
        self.filter_dropdown.setFixedWidth(dropdown_width)
        filter_layout.addWidget(self.filter_label)
        filter_layout.addWidget(self.filter_dropdown)
        filter_layout.addStretch()
        layout.addLayout(filter_layout)


        uwi_label = QLabel("Select UWI:")
        layout.addWidget(uwi_label)  
        # Layout for UWI list boxes and arrows
        well_list_layout = QHBoxLayout()
        self.uwi_listbox = QListWidget()
        self.uwi_listbox.setSelectionMode(QAbstractItemView.ExtendedSelection)
        well_list_layout.addWidget(self.uwi_listbox)

        well_arrow_layout = QVBoxLayout()
        well_arrow_layout.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding))

        self.move_all_wells_right_button = QPushButton()
        self.move_all_wells_right_button.setIcon(QIcon("icons/arrow_double_right.png"))
        self.move_all_wells_right_button.clicked.connect(self.move_all_wells_right)
        well_arrow_layout.addWidget(self.move_all_wells_right_button)

        self.move_wells_right_button = QPushButton()
        self.move_wells_right_button.setIcon(QIcon("icons/arrow_right.ico"))
        self.move_wells_right_button.clicked.connect(self.move_selected_wells_right)
        well_arrow_layout.addWidget(self.move_wells_right_button)

        self.move_wells_left_button = QPushButton()
        self.move_wells_left_button.setIcon(QIcon("icons/arrow_left.ico"))
        self.move_wells_left_button.clicked.connect(self.move_selected_wells_left)
        well_arrow_layout.addWidget(self.move_wells_left_button)

        self.move_all_wells_left_button = QPushButton()
        self.move_all_wells_left_button.setIcon(QIcon("icons/arrow_double_left.png"))
        self.move_all_wells_left_button.clicked.connect(self.move_all_wells_left)
        well_arrow_layout.addWidget(self.move_all_wells_left_button)

        well_arrow_layout.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding))
        well_list_layout.addLayout(well_arrow_layout)

        self.selected_uwi_listbox = QListWidget()
        self.selected_uwi_listbox.setSelectionMode(QAbstractItemView.ExtendedSelection)
        well_list_layout.addWidget(self.selected_uwi_listbox)

        layout.addLayout(well_list_layout)


        depth_grids_label = QLabel("Select Depth Grids:")
        layout.addWidget(depth_grids_label)  
        # New UI elements for Depth Grids
        depth_grid_list_layout = QHBoxLayout()
        self.depth_grid_listbox = QListWidget()
        self.depth_grid_listbox.setSelectionMode(QAbstractItemView.ExtendedSelection)
        depth_grid_list_layout.addWidget(self.depth_grid_listbox)

        depth_grid_arrow_layout = QVBoxLayout()
        depth_grid_arrow_layout.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding))

        self.move_all_depth_grids_right_button = QPushButton()
        self.move_all_depth_grids_right_button.setIcon(QIcon("icons/arrow_double_right.png"))
        self.move_all_depth_grids_right_button.setIcon(QIcon("icons/arrow_double_right.png"))
        self.move_all_depth_grids_right_button.clicked.connect(self.move_all_depth_grids_right)
        depth_grid_arrow_layout.addWidget(self.move_all_depth_grids_right_button)

        self.move_depth_grids_right_button = QPushButton()
        self.move_depth_grids_right_button.setIcon(QIcon("icons/arrow_right.ico"))
        self.move_depth_grids_right_button.clicked.connect(self.move_selected_depth_grids_right)
        depth_grid_arrow_layout.addWidget(self.move_depth_grids_right_button)

        self.move_depth_grids_left_button = QPushButton()
        self.move_depth_grids_left_button.setIcon(QIcon("icons/arrow_left.ico"))
        self.move_depth_grids_left_button.clicked.connect(self.move_selected_depth_grids_left)
        depth_grid_arrow_layout.addWidget(self.move_depth_grids_left_button)

        self.move_all_depth_grids_left_button = QPushButton()
        self.move_all_depth_grids_left_button.setIcon(QIcon("icons/arrow_double_left.png"))
        self.move_all_depth_grids_left_button.clicked.connect(self.move_all_depth_grids_left)
        depth_grid_arrow_layout.addWidget(self.move_all_depth_grids_left_button)

        depth_grid_arrow_layout.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding))
        depth_grid_list_layout.addLayout(depth_grid_arrow_layout)

        self.selected_depth_grid_listbox = QListWidget()
        self.selected_depth_grid_listbox.setSelectionMode(QAbstractItemView.ExtendedSelection)
        depth_grid_list_layout.addWidget(self.selected_depth_grid_listbox)

        layout.addLayout(depth_grid_list_layout)


        attribute_grids_label = QLabel("Select Attribute Grids:")
        layout.addWidget(attribute_grids_label)  # Add this line for Attribute Grids label

        # New UI elements for Attribute Grids
        attribute_grid_list_layout = QHBoxLayout()
        self.attribute_grid_listbox = QListWidget()
        self.attribute_grid_listbox.setSelectionMode(QAbstractItemView.ExtendedSelection)
        attribute_grid_list_layout.addWidget(self.attribute_grid_listbox)

        attribute_grid_arrow_layout = QVBoxLayout()
        attribute_grid_arrow_layout.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding))

        self.move_all_attribute_grids_right_button = QPushButton()
        self.move_all_attribute_grids_right_button.setIcon(QIcon("icons/arrow_double_right.png"))
        self.move_all_attribute_grids_right_button.clicked.connect(self.move_all_attribute_grids_right)
        attribute_grid_arrow_layout.addWidget(self.move_all_attribute_grids_right_button)

        self.move_attribute_grids_right_button = QPushButton()
        self.move_attribute_grids_right_button.setIcon(QIcon("icons/arrow_right.ico"))
        self.move_attribute_grids_right_button.clicked.connect(self.move_selected_attribute_grids_right)
        attribute_grid_arrow_layout.addWidget(self.move_attribute_grids_right_button)

        self.move_attribute_grids_left_button = QPushButton()
        self.move_attribute_grids_left_button.setIcon(QIcon("icons/arrow_left.ico"))
        self.move_attribute_grids_left_button.clicked.connect(self.move_selected_attribute_grids_left)
        attribute_grid_arrow_layout.addWidget(self.move_attribute_grids_left_button)

        self.move_all_attribute_grids_left_button = QPushButton()
        self.move_all_attribute_grids_left_button.setIcon(QIcon("icons/arrow_double_left.png"))
        self.move_all_attribute_grids_left_button.clicked.connect(self.move_all_attribute_grids_left)
        attribute_grid_arrow_layout.addWidget(self.move_all_attribute_grids_left_button)

        attribute_grid_arrow_layout.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding))
        attribute_grid_list_layout.addLayout(attribute_grid_arrow_layout)

        self.selected_attribute_grid_listbox = QListWidget()
        self.selected_attribute_grid_listbox.setSelectionMode(QAbstractItemView.ExtendedSelection)
        attribute_grid_list_layout.addWidget(self.selected_attribute_grid_listbox)

        layout.addLayout(attribute_grid_list_layout)

        # Button to load data
        self.load_button = QPushButton("Load Data")
        self.load_button.clicked.connect(self.load_data)
        layout.addWidget(self.load_button)

        self.connection = None

        self.project_list = []
        self.well_list = []
        self.uwi_to_well_dict = {}
        self.selected_uwis = []
        self.depth_grid_list = []
        self.attribute_grid_list = []
        self.grid_objects_with_names = []
        self.selected_depth_grids = []
        self.selected_attribute_grids = []
        self.import_options_df = pd.DataFrame()
        self.uwis_and_offsets = []
        self.directional_surveys = []
        self.directional_surveys_df = pd.DataFrame()
        self.grid_info_df = pd.DataFrame()
        self.total_lat_data = []
        self.grid_names = []

    def set_import_parameters(self, import_options_df):
        if not import_options_df.empty:
            self.project_dropdown.setCurrentText(import_options_df.get('Project', [''])[0])
            self.filter_dropdown.setCurrentText(import_options_df.get('Well Filter', [''])[0])
            selected_uwis = import_options_df.get('selected_uwis', [[]])[0]
            selected_depth_grids = import_options_df.get('selected_depth_grids', [[]])[0]
            selected_attribute_grids = import_options_df.get('selected_attribute_grids', [[]])[0]

            for i in range(self.uwi_listbox.count() - 1, -1, -1):
                if self.uwi_listbox.item(i).text() in selected_uwis:
                    self.uwi_listbox.takeItem(i)
            if isinstance(selected_uwis, list):
                self.selected_uwi_listbox.clear()
                self.selected_uwi_listbox.addItems(selected_uwis)

            for i in range(self.depth_grid_listbox.count() - 1, -1, -1):
                if self.depth_grid_listbox.item(i).text() in selected_depth_grids:
                    self.depth_grid_listbox.takeItem(i)
            if isinstance(selected_depth_grids, list):
                self.selected_depth_grid_listbox.clear()
                self.selected_depth_grid_listbox.addItems(selected_depth_grids)

            for i in range(self.attribute_grid_listbox.count() - 1, -1, -1):
                if self.attribute_grid_listbox.item(i).text() in selected_attribute_grids:
                    self.attribute_grid_listbox.takeItem(i)
            if isinstance(selected_attribute_grids, list):
                self.selected_attribute_grid_listbox.clear()
                self.selected_attribute_grid_listbox.addItems(selected_attribute_grids)

    def move_selected_wells_right(self):
        selected_items = self.uwi_listbox.selectedItems()
        for item in selected_items:
            self.selected_uwi_listbox.addItem(item.text())
            self.uwi_listbox.takeItem(self.uwi_listbox.row(item))

    def move_selected_wells_left(self):
        selected_items = self.selected_uwi_listbox.selectedItems()
        for item in selected_items:
            self.uwi_listbox.addItem(item.text())
            self.selected_uwi_listbox.takeItem(self.selected_uwi_listbox.row(item))

    def move_all_wells_right(self):
        while self.uwi_listbox.count() > 0:
            item = self.uwi_listbox.takeItem(0)
            self.selected_uwi_listbox.addItem(item)

    def move_all_wells_left(self):
        while self.selected_uwi_listbox.count() > 0:
            item = self.selected_uwi_listbox.takeItem(0)
            self.uwi_listbox.addItem(item)

    def move_selected_depth_grids_right(self):
        selected_items = self.depth_grid_listbox.selectedItems()
        for item in selected_items:
            self.selected_depth_grid_listbox.addItem(item.text())
            self.depth_grid_listbox.takeItem(self.depth_grid_listbox.row(item))

    def move_selected_depth_grids_left(self):
        selected_items = self.selected_depth_grid_listbox.selectedItems()
        for item in selected_items:
            self.depth_grid_listbox.addItem(item.text())
            self.selected_depth_grid_listbox.takeItem(self.selected_depth_grid_listbox.row(item))

    def move_all_depth_grids_right(self):
        while self.depth_grid_listbox.count() > 0:
            item = self.depth_grid_listbox.takeItem(0)
            self.selected_depth_grid_listbox.addItem(item)

    def move_all_depth_grids_left(self):
        while self.selected_depth_grid_listbox.count() > 0:
            item = self.selected_depth_grid_listbox.takeItem(0)
            self.depth_grid_listbox.addItem(item)

    def move_selected_attribute_grids_right(self):
        selected_items = self.attribute_grid_listbox.selectedItems()
        for item in selected_items:
            self.selected_attribute_grid_listbox.addItem(item.text())
            self.attribute_grid_listbox.takeItem(self.attribute_grid_listbox.row(item))

    def move_selected_attribute_grids_left(self):
        selected_items = self.selected_attribute_grid_listbox.selectedItems()
        for item in selected_items:
            self.attribute_grid_listbox.addItem(item.text())
            self.selected_attribute_grid_listbox.takeItem(self.selected_attribute_grid_listbox.row(item))

    def move_all_attribute_grids_right(self):
        while self.attribute_grid_listbox.count() > 0:
            item = self.attribute_grid_listbox.takeItem(0)
            self.selected_attribute_grid_listbox.addItem(item)

    def move_all_attribute_grids_left(self):
        while self.selected_attribute_grid_listbox.count() > 0:
            item = self.selected_attribute_grid_listbox.takeItem(0)
            self.attribute_grid_listbox.addItem(item)

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
        except RuntimeError as err:
            self.show_error_message("Error", "Failed to connect to the project: " + str(err))
            return

        self.well_filter = SeisWare.FilterList()
        try:
            self.login_instance.FilterManager().GetAll(self.well_filter)
        except RuntimeError as err:
            self.show_error_message("Error", f"Failed to get filters: {err}")
            return

        filter_list = []
        for filter in self.well_filter:
            filter_type = filter.FilterType()
            if filter_type == 2:
                filter_name = filter.Name()
                filter_list.append(filter_name)

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
            self.show_error_message("Failed to get the grids from the project", str(err))

        self.grids = [grid.Name() for grid in self.grid_list]
        self.grid_objects_with_names = [(grid, grid.Name()) for grid in self.grid_list]

        self.depth_grid_listbox.clear()
        self.attribute_grid_listbox.clear()

        # Add all grids to both Depth Grids and Attribute Grids lists
        for grid_name in self.grids:
            self.depth_grid_listbox.addItem(grid_name)
            self.attribute_grid_listbox.addItem(grid_name)

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

    def load_data(self):
        self.selected_uwis = [self.selected_uwi_listbox.item(i).text() for i in range(self.selected_uwi_listbox.count())]
        self.selected_depth_grids = [self.selected_depth_grid_listbox.item(i).text() for i in range(self.selected_depth_grid_listbox.count())]

        self.selected_attribute_grids = [self.selected_attribute_grid_listbox.item(i).text() for i in range(self.selected_attribute_grid_listbox.count())]
        print(self.selected_attribute_grids)
        print(self.selected_depth_grids)

        if not self.selected_uwis:
            self.show_info_message("Info", "No wells selected for export.")
            return

        if not self.selected_depth_grids and not self.selected_attribute_grids:
            self.show_info_message("Info", "No grids selected for export.")
            return

        self.store_directional_surveys()
        self.store_depth_grid_data()
        self.zone_color()
        self.get_grid_names_and_store_info()

        self.accept()  # This line ensures that the dialog is accepted and returns data

    def store_directional_surveys(self):
        self.uwis_and_offsets = []
        self.directional_surveys = []
        self.total_lat_data = []

        selected_uwis = [self.selected_uwi_listbox.item(i).text() for i in range(self.selected_uwi_listbox.count())]
        if not selected_uwis:
            self.show_info_message("Info", "No wells selected for export.")
            return

        for uwi in selected_uwis:
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
                    self.directional_surveys.append((uwi, md_values, tvd_values, x_offsets, y_offsets))
                    self.total_lat_data.append((uwi, total_lat, surfaceX, surfaceY))

                    max_points = max(len(md_values) for _, md_values, _, _, _ in self.directional_surveys)
                    data_list = []
                    for uwi, md_values, tvd_values, x_offsets, y_offsets in self.directional_surveys:
                        for i in range(max_points):
                            md = md_values[i] if i < len(md_values) else None
                            tvd = tvd_values[i] if i < len(tvd_values) else None
                            x_offset = x_offsets[i] if i < len(x_offsets) else None
                            y_offset = y_offsets[i] if i < len(y_offsets) else None
                            if None not in (md, tvd, x_offset, y_offset):
                                data_list.append([uwi, md, tvd, x_offset, y_offset])
                           

                    columns = ['UWI', 'MD', 'TVD', 'X Offset', 'Y Offset']
                    self.directional_surveys_df = pd.DataFrame(data_list, columns=columns)
              

                else:
                    self.show_info_message("Warning", f"No directional survey found for well {uwi}.")

    def store_depth_grid_data(self):
        self.depth_grid_data = []
        for grid_name in self.selected_depth_grids:
            selected_grid_object = None
            for grid, name in self.grid_objects_with_names:
                if name == grid_name:
                    selected_grid_object = grid
                    break

            try:
                self.login_instance.GridManager().PopulateValues(selected_grid_object)
            except RuntimeError as err:
                self.show_error_message("Failed to populate the values of grid %s from the project" % grid_name, err)
                return

            grid_values = SeisWare.GridValues()
            selected_grid_object.Values(grid_values)

            grid_values_list = list(grid_values.Data())
            for i in range(grid_values.Height()):
                for j in range(grid_values.Width()):
                    z_value = grid_values_list[i * grid_values.Width() + j]
        
                    # Check if Z is within the desired range before appending
                    if -1000000 <= z_value <= 1000000:
                        self.depth_grid_data.append({
                            'Grid': grid_name,
                            'X': selected_grid_object.Definition().RangeX().start + j * selected_grid_object.Definition().RangeX().delta,
                            'Y': selected_grid_object.Definition().RangeY().start + i * selected_grid_object.Definition().RangeY().delta,
                            'Z': z_value
                        })
        if self.depth_grid_data:
            print("Depth Grid data sample:", self.depth_grid_data[0])
        else:
            print("No depth grid data found.")

        self.depth_grid_data_df = pd.DataFrame(self.depth_grid_data)
        print(self.depth_grid_data_df)

    def store_attribute_grid_data(self):
        self.attribute_grid_data = []
        for grid_name in self.selected_attribute_grids:
            selected_grid_object = None
            for grid, name in self.grid_objects_with_names:
                if name == grid_name:
                    selected_grid_object = grid
                    break

            try:
                self.login_instance.GridManager().PopulateValues(selected_grid_object)
            except RuntimeError as err:
                self.show_error_message("Failed to populate the values of grid %s from the project" % grid_name, err)
                return

            grid_values = SeisWare.GridValues()
            selected_grid_object.Values(grid_values)

            grid_values_list = list(grid_values.Data())
            for i in range(grid_values.Height()):
                for j in range(grid_values.Width()):
                    self.attribute_grid_data.append({
                        'Grid': grid_name,
                        'X': selected_grid_object.Definition().RangeX().start + j * selected_grid_object.Definition().RangeX().delta,
                        'Y': selected_grid_object.Definition().RangeY().start + i * selected_grid_object.Definition().RangeY().delta,
                        'Z': grid_values_list[i * grid_values.Width() + j]
                    })

        if self.attribute_grid_data:
            print("Attribute Grid data sample:", self.attribute_grid_data[0])
        else:
            print("No attribute grid data found.")

        self.attribute_grid_data_df = pd.DataFrame(self.attribute_grid_data)

    def zone_color(self):
        # Get the names of the depth grids from the list box
        depth_grid_names = [self.selected_depth_grid_listbox.item(i).text() for i in range(self.selected_depth_grid_listbox.count())]
 
        print(depth_grid_names)

        # Generate colors for each depth grid
        num_grids = len(self.selected_depth_grids )

        grid_colors_hex = [
            QColor.fromHsv(int(i * 360 / num_grids), 255, 255).toRgb().name(QColor.HexRgb) for i in range(num_grids)
        ]

        # Convert hex colors to RGB
        grid_colors_rgb = [self.hex_to_rgb(color) for color in grid_colors_hex]

        # Create a DataFrame for depth grid names and colors
        depth_grid_color_df = pd.DataFrame({
            'Depth Grid Name': depth_grid_names,
            'Color (Hex)': grid_colors_hex,
            'Color (RGB)': grid_colors_rgb
        })

        self.depth_grid_color_df = depth_grid_color_df

        # Print the DataFrame for verification
        print(self.depth_grid_color_df)

    def get_grid_names_and_store_info(self, output_file='grid_info.csv'):
        # Combine grid names from both depth and attribute grids
        depth_grid_names = self.depth_grid_data_df['Grid'].unique().tolist() if not self.depth_grid_data_df.empty else []
        attribute_grid_names = self.attribute_grid_data_df['Grid'].unique().tolist() if not self.attribute_grid_data_df.empty else []
        self.grid_names = depth_grid_names + attribute_grid_names

        grid_info_list = []

        # Calculate bin size, min, max values, and add color for each grid
        for grid_name in self.grid_names:
            if grid_name in depth_grid_names:
                grid_data = self.depth_grid_data_df[self.depth_grid_data_df['Grid'] == grid_name]
            else:
                grid_data = self.attribute_grid_data_df[self.attribute_grid_data_df['Grid'] == grid_name]

            if grid_data.empty:
                continue

            min_x = grid_data['X'].min()
            max_x = grid_data['X'].max()
            min_y = grid_data['Y'].min()
            max_y = grid_data['Y'].max()
            min_z = grid_data['Z'].min()
            max_z = grid_data['Z'].max()

            # Calculate bin size (assuming uniform spacing)
            unique_x = sorted(grid_data['X'].unique())
            unique_y = sorted(grid_data['Y'].unique())

            if len(unique_x) > 1:
                bin_size_x = unique_x[1] - unique_x[0]
            else:
                bin_size_x = None

            if len(unique_y) > 1:
                bin_size_y = unique_y[1] - unique_y[0]
            else:
                bin_size_y = None

            # Get the color for the grid if available, otherwise set a default color
            color_row = self.depth_grid_color_df[self.depth_grid_color_df['Depth Grid Name'] == grid_name]
            if not color_row.empty:
                color_rgb = color_row['Color (RGB)'].values[0]
            else:
                color_rgb = (255, 255, 255)  # Default color (white) if not found

            grid_info_list.append({
                'Grid': grid_name,
                'min_x': min_x,
                'max_x': max_x,
                'min_y': min_y,
                'max_y': max_y,
                'min_z': min_z,
                'max_z': max_z,
                'bin_size_x': bin_size_x,
                'bin_size_y': bin_size_y,
                'Color (RGB)': color_rgb
            })

        # Convert the grid info list to a DataFrame and write to a CSV file
        self.grid_info_df = pd.DataFrame(grid_info_list)

        return self.grid_info_df

    def hex_to_rgb(self, hex_color):
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

    def hex_to_rgb(self, hex_color):
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))




    def show_error_message(self, title, message):
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle(title)
        msg_box.setText(message)
        msg_box.setIcon(QMessageBox.Critical)
        msg_box.exec_()

    def show_info_message(self, title, message):
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle(title)
        msg_box.setText(message)
        msg_box.setIcon(QMessageBox.Information)
        msg_box.exec_()

    def reset_ui_and_data(self):
        self.filter_dropdown.blockSignals(True)
        self.filter_dropdown.clear()
        self.filter_dropdown.blockSignals(False)

        self.uwi_listbox.clear()
        self.selected_uwi_listbox.clear()
        self.depth_grid_listbox.clear()
        self.selected_depth_grid_listbox.clear()
        self.attribute_grid_listbox.clear()
        self.selected_attribute_grid_listbox.clear()

        self.well_list.clear()
        self.depth_grid_list.clear()
        self.attribute_grid_list.clear()
        self.uwi_to_well_dict.clear()
        self.selected_uwis.clear()

        self.directional_surveys_df = pd.DataFrame()
        self.depth_grid_data_df = pd.DataFrame()
        self.attribute_grid_data_df = pd.DataFrame()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    dialog = DataLoaderDialog()
    dialog.show()
    sys.exit(app.exec_())
