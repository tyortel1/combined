import sys
import SeisWare
import pandas as pd
from PySide6.QtWidgets import QApplication, QDialog, QLabel, QComboBox, QSizePolicy, QVBoxLayout, QHBoxLayout, QPushButton, QListWidget, QAbstractItemView, QSizePolicy, QSpacerItem, QMessageBox
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QColor
import numpy as np
from scipy.spatial import KDTree
from PySide6.QtWidgets import QProgressDialog
from StyledTwoListSelector import TwoListSelector
from StyledDropdown import StyledDropdown
from StyledButton import StyledButton



class DataLoadGridDialog(QDialog):
    def __init__(self, import_options_df=None, parent=None):
        super(DataLoadGridDialog, self).__init__(parent)
        self.setWindowTitle("Load Grids")
        self.setGeometry(100, 100, 800, 600)
        self.setupUi()
        self.connect_to_seisware()
        self.import_options_df = import_options_df
        self.depth_grid_data_df = pd.DataFrame()
        self.attribute_grid_data_df = pd.DataFrame()
        self.kd_tree_depth_grids = None
        self.kd_tree_att_grids = None
        if self.import_options_df is not None:
            self.set_import_parameters(self.import_options_df)

    def setupUi(self):
        layout = QVBoxLayout(self)

        # Project
        self.project_dropdown = StyledDropdown("Project:", parent=self)
        layout.addWidget(self.project_dropdown)

        # Grid Unit
        self.grid_unit_dropdown = StyledDropdown("Grid Unit:", parent=self)
        self.grid_unit_dropdown.setItems(["Feet", "Meters"])
        layout.addWidget(self.grid_unit_dropdown)

        # Add some space
        layout.addSpacing(20)

        # Depth Grids Selector
        self.depth_grid_selector = TwoListSelector("Available Depth Grids", "Selected Depth Grids")
        self.depth_grid_selector.setFullHeight(True)  # Add this line
        layout.addWidget(self.depth_grid_selector)

        # Attribute Grids Selector
        self.attribute_grid_selector = TwoListSelector("Available Attribute Grids", "Selected Attribute Grids")
        self.attribute_grid_selector.setFullHeight(True)  # Add this line
        layout.addWidget(self.attribute_grid_selector)

        # Button layout for bottom right alignment
        button_layout = QHBoxLayout()
        button_layout.addStretch()  # This pushes the button to the right

        # Load Data button (green, bottom right)
        self.load_button = StyledButton("Load Data", "function")
        self.load_button.clicked.connect(self.load_data)
        button_layout.addWidget(self.load_button)

        layout.addLayout(button_layout)

        self.setLayout(layout)

        # Initialize other attributes
        self.connection = None
        self.project_list = []
        self.grid_objects_with_names = []
        self.import_options_df = pd.DataFrame()
        self.grid_info_df = pd.DataFrame()
        self.grid_names = []

    def set_import_parameters(self, import_options_df):
        if not import_options_df.empty:
            # Set project
            if 'Project' in import_options_df.columns:
                self.project_dropdown.setCurrentText(import_options_df['Project'].iloc[0])
            
            # Set grid unit
            if 'GridUnit' in import_options_df.columns:
                self.grid_unit_dropdown.setCurrentText(import_options_df['GridUnit'].iloc[0])
            
            # Set selected grids
            selected_depth_grids = import_options_df.get('selected_depth_grids', [[]]).iloc[0]
            selected_attribute_grids = import_options_df.get('selected_attribute_grids', [[]]).iloc[0]
            
            # Update the selectors
            if selected_depth_grids:
                self.depth_grid_selector.set_right_items(selected_depth_grids)
            if selected_attribute_grids:
                self.attribute_grid_selector.set_right_items(selected_attribute_grids)
            
            # Store the selections
            self.selected_depth_grids = selected_depth_grids
            self.selected_attribute_grids = selected_attribute_grids



    def move_selected_depth_grids_right(self):
        selected_items = self.depth_grid_listbox.selectedItems()
        for item in selected_items:
            text = item.text()
            self.selected_depth_grid_listbox.addItem(text)
            # Remove from both left lists
            self.remove_from_listbox(self.depth_grid_listbox, text)
            self.remove_from_listbox(self.attribute_grid_listbox, text)
            # Sort the selected list
            self.sort_listbox(self.selected_depth_grid_listbox)

    def move_selected_depth_grids_left(self):
        selected_items = self.selected_depth_grid_listbox.selectedItems()
        for item in selected_items:
            text = item.text()
            # Add back to both left lists
            self.depth_grid_listbox.addItem(text)
            self.attribute_grid_listbox.addItem(text)
            self.selected_depth_grid_listbox.takeItem(self.selected_depth_grid_listbox.row(item))
            # Sort both left lists
            self.sort_listbox(self.depth_grid_listbox)
            self.sort_listbox(self.attribute_grid_listbox)

    def move_selected_attribute_grids_right(self):
        selected_items = self.attribute_grid_listbox.selectedItems()
        for item in selected_items:
            text = item.text()
            self.selected_attribute_grid_listbox.addItem(text)
            # Remove from both left lists
            self.remove_from_listbox(self.depth_grid_listbox, text)
            self.remove_from_listbox(self.attribute_grid_listbox, text)
            # Sort the selected list
            self.sort_listbox(self.selected_attribute_grid_listbox)

    def move_selected_attribute_grids_left(self):
        selected_items = self.selected_attribute_grid_listbox.selectedItems()
        for item in selected_items:
            text = item.text()
            # Add back to both left lists
            self.depth_grid_listbox.addItem(text)
            self.attribute_grid_listbox.addItem(text)
            self.selected_attribute_grid_listbox.takeItem(self.selected_attribute_grid_listbox.row(item))
            # Sort both left lists
            self.sort_listbox(self.depth_grid_listbox)
            self.sort_listbox(self.attribute_grid_listbox)

    # Helper functions
    def sort_listbox(self, listbox):
        items = [listbox.item(i).text() for i in range(listbox.count())]
        items.sort()
        listbox.clear()
        listbox.addItems(items)

    def remove_from_listbox(self, listbox, text):
        for i in range(listbox.count()):
            if listbox.item(i).text() == text:
                listbox.takeItem(i)
                break

    # Also modify your on_project_select to sort initially:
    def on_project_select(self, index):
        # ... existing code ...
    
        # Add all grids to both Depth Grids and Attribute Grids lists
        for grid_name in sorted(self.grids):  # Sort the grids before adding
            self.depth_grid_listbox.addItem(grid_name)
            self.attribute_grid_listbox.addItem(grid_name)

    def move_all_depth_grids_right(self):
        items = [self.depth_grid_listbox.item(i).text() for i in range(self.depth_grid_listbox.count())]
        # Add all items to selected list
        self.selected_depth_grid_listbox.addItems(sorted(items))
        # Clear both left lists
        self.depth_grid_listbox.clear()
        self.attribute_grid_listbox.clear()

    def move_all_depth_grids_left(self):
        items = [self.selected_depth_grid_listbox.item(i).text() for i in range(self.selected_depth_grid_listbox.count())]
        # Clear selected list
        self.selected_depth_grid_listbox.clear()
        # Add items back to both left lists in sorted order
        self.depth_grid_listbox.addItems(sorted(items))
        self.attribute_grid_listbox.addItems(sorted(items))

    def move_all_attribute_grids_right(self):
        items = [self.attribute_grid_listbox.item(i).text() for i in range(self.attribute_grid_listbox.count())]
        # Add all items to selected list
        self.selected_attribute_grid_listbox.addItems(sorted(items))
        # Clear both left lists
        self.depth_grid_listbox.clear()
        self.attribute_grid_listbox.clear()

    def move_all_attribute_grids_left(self):
        items = [self.selected_attribute_grid_listbox.item(i).text() for i in range(self.selected_attribute_grid_listbox.count())]
        # Clear selected list
        self.selected_attribute_grid_listbox.clear()
        # Add items back to both left lists in sorted order
        self.depth_grid_listbox.addItems(sorted(items))
        self.attribute_grid_listbox.addItems(sorted(items))

    def sort_listbox(self, listbox):
        items = [listbox.item(i).text() for i in range(listbox.count())]
        items.sort()
        listbox.clear()
        listbox.addItems(items)

    def remove_from_listbox(self, listbox, text):
        for i in range(listbox.count()):
            if listbox.item(i).text() == text:
                listbox.takeItem(i)
                break

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
        self.project_dropdown.setItems(self.project_names)
        self.project_dropdown.combo.setCurrentIndex(-1)
        self.project_dropdown.combo.currentIndexChanged.connect(self.on_project_select)

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

        self.grid_list = SeisWare.GridList()
        try:
            self.login_instance.GridManager().GetAll(self.grid_list)
        except RuntimeError as err:
            self.show_error_message("Failed to get the grids from the project", str(err))
            return

        self.grids = [grid.Name() for grid in self.grid_list]
        self.grid_objects_with_names = [(grid, grid.Name()) for grid in self.grid_list]

        # Update the TwoListSelectors with the sorted grid names
        sorted_grids = sorted(self.grids)
        self.depth_grid_selector.set_left_items(sorted_grids)
        self.attribute_grid_selector.set_left_items(sorted_grids)



    def load_data(self):
        loading_dialog = QProgressDialog("Loading data, please wait...", None, 0, 0, self)
        loading_dialog.setWindowTitle("Loading")
        loading_dialog.setWindowModality(Qt.ApplicationModal)
        loading_dialog.setCancelButton(None)
        loading_dialog.show()

        try:
            self.selected_depth_grids = self.depth_grid_selector.get_right_items()
            self.selected_attribute_grids = self.attribute_grid_selector.get_right_items()

            if not self.selected_depth_grids and not self.selected_attribute_grids:
                self.show_info_message("Info", "No grids selected for export.")
                return

            self.store_depth_grid_data()
            self.store_attribute_grid_data()
            self.zone_color()
            self.get_grid_names_and_store_info()

            self.accept()

        finally:
            loading_dialog.close()

    def store_depth_grid_data(self):
        self.depth_grid_data = []
        conversion_factor = 0.3048
        is_feet_selected = self.grid_unit_dropdown.currentText() == "Feet"

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

                    if is_feet_selected:
                        z_value = z_value * conversion_factor



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
        self.kd_tree_depth_grids = {grid: KDTree(self.depth_grid_data_df[self.depth_grid_data_df['Grid'] == grid][['X', 'Y']].values) for grid in self.depth_grid_data_df['Grid'].unique()}
    


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
      
        self.kd_tree_att_grids = {grid: KDTree(self.attribute_grid_data_df[self.attribute_grid_data_df['Grid'] == grid][['X', 'Y']].values) for grid in self.attribute_grid_data_df['Grid'].unique()}


    def zone_color(self):
        # Get the names of the depth grids directly from the selected items
        depth_grid_names = self.selected_depth_grids  # Using the already stored selected grids

        # Generate colors for each depth grid
        num_grids = len(depth_grid_names)
        
        if num_grids == 0:
            self.depth_grid_color_df = pd.DataFrame(columns=['Depth Grid Name', 'Color (Hex)', 'Color (RGB)'])
            return

        # Generate unique colors
        grid_colors_hex = [
            QColor.fromHsv(int(i * 360 / num_grids), 255, 255).toRgb().name(QColor.HexRgb) 
            for i in range(num_grids)
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
                grid_type = "Depth"
            else:
                grid_data = self.attribute_grid_data_df[self.attribute_grid_data_df['Grid'] == grid_name]
                grid_type = "Attribute"

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
                'Type': grid_type,
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
        self.depth_grid_selector.set_left_items([])
        self.depth_grid_selector.set_right_items([])
        self.attribute_grid_selector.set_left_items([])
        self.attribute_grid_selector.set_right_items([])
        self.depth_grid_data_df = pd.DataFrame()
        self.attribute_grid_data_df = pd.DataFrame()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    dialog = DataLoaderDialog()
    dialog.show()
    sys.exit(app.exec_())
