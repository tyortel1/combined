from select import select
from PyQt5.QtWidgets import (
    QApplication, QDialog, QLabel, QPushButton, QVBoxLayout, QHBoxLayout, 
    QComboBox, QListWidget, QGridLayout, QMessageBox, QScrollBar, 
)
from PyQt5.QtCore import Qt, QSignalBlocker
import pandas as pd
import sys
import LoadProductions

sys.path.append('C:\Program Files')
import SeisWare

class SeisWareConnectDialog(QDialog):
    def __init__(self):
        super().__init__()
        
        # Set dialog properties
        self.setWindowTitle("SeisWare Connect")
        self.setGeometry(590, 257, 700, 700)
        self.setMinimumSize(120, 1)
        
        # Initialize UI components
        self.initUI()

        self.project_list = []
        self.connection = SeisWare.Connection()
        self.login_instance = SeisWare.LoginInstance()

        self.connect_to_seisware()
        # Your connection code or setup here
        # self.connect_to_seisware()
        self.well_list = []
        self.project_names = []
        self.projects =[]
        #self.curve_calibration_dict = {}
        self.filter_name = None
        self.grid_xyz_top = []
        self.filtered_well_filter =[]
        
        self.login_instance = SeisWare.LoginInstance()
        self.directional_survey_values = []
        self.Grid_intersec_top = []
        self.Grid_intersec_bottom = []
        self.selected_item = None
        self.uwis_and_offsets = []
        self.filter_selection = None
        self.project_selection = None
  



    def initUI(self):
        # Project label and dropdown
        self.project_label = QLabel("Project:", self)
        self.project_label.setGeometry(20, 20, 60, 20)  # x, y, width, height

        self.project_dropdown = QComboBox(self)
        self.project_dropdown.setGeometry(90, 20, 150, 20)  # x, y, width, height
        self.project_dropdown.currentIndexChanged.connect(self.on_project_select)

        # Well filter label and dropdown
        self.filter_label = QLabel("Well Filter:", self)
        self.filter_label.setGeometry(20, 50, 60, 20)  # x, y, width, height

        self.filter_dropdown = QComboBox(self)
        self.filter_dropdown.setGeometry(90, 50, 150, 20)  # x, y, width, height
        self.filter_dropdown.setEnabled(False)
        self.filter_dropdown.currentIndexChanged.connect(self.on_filter_select)

        # Listboxes for UWIs
        self.uwi_listbox = QListWidget(self)
        self.uwi_listbox.setGeometry(20, 100, 280, 500)  # x, y, width, height

        self.selected_uwi_listbox = QListWidget(self)
        self.selected_uwi_listbox.setGeometry(400, 100, 280, 500)  # x, y, width, height

        self.uwi_listbox.setSelectionMode(QListWidget.MultiSelection)
        self.selected_uwi_listbox.setSelectionMode(QListWidget.MultiSelection)

        # Buttons for moving items between listboxes
        button_width = 50
        self.move_right_button = QPushButton(">", self)
        self.move_right_button.setGeometry(320, 250, button_width, 30)  # x, y, width, height
        self.move_right_button.clicked.connect(self.move_selected_right)

        self.move_left_button = QPushButton("<", self)
        self.move_left_button.setGeometry(320, 290, button_width, 30)  # x, y, width, height
        self.move_left_button.clicked.connect(self.move_selected_left)

        self.move_all_right_button = QPushButton(">>", self)
        self.move_all_right_button.setGeometry(320, 330, button_width, 30)  # x, y, width, height
        self.move_all_right_button.clicked.connect(self.move_all_right)

        self.move_all_left_button = QPushButton("<<", self)
        self.move_all_left_button.setGeometry(320, 370, button_width, 30)  # x, y, width, height
        self.move_all_left_button.clicked.connect(self.move_all_left)

        # Okay button
        self.okay_button = QPushButton("Okay", self)
        self.okay_button.setGeometry(580, 630, 100, 30)  # x, y, width, height
        self.okay_button.clicked.connect(self.okay_clicked) 
        

    def connect_to_seisware(self):
        # Connect to API
        self.connection = SeisWare.Connection()
        try:
            serverInfo = SeisWare.Connection.CreateServer()
            self.connection.Connect(serverInfo.Endpoint(), 50000)
        except RuntimeError as err:
            QMessageBox.critical(self,"Connection Error", f"Failed to connect to the server: {err}")
            return

        self.project_list = SeisWare.ProjectList()
        try:
            self.connection.ProjectManager().GetAll(self.project_list)
        except RuntimeError as err:
            QMessageBox.critical(self,"Error", f"Failed to get the project list from the server: {err}")
            return

                # Put project names in Dropdown
            # Populate project_dropdown with project_names
        self.project_names = [project.Name() for project in self.project_list]
        with QSignalBlocker(self.project_dropdown):
            self.project_dropdown.addItems([project.Name() for project in self.project_list])
            self.project_dropdown.setCurrentIndex(-1)


        # Add more connections as needed
    def on_project_select(self, event):
        self.filter_dropdown.setEnabled(True)
      
    # Clear the content of the list selectors
        self.clear_widgets()
            
        self.login_instance = SeisWare.LoginInstance()

        project_name = self.project_dropdown.currentText()
        self.projects = [project for project in self.project_list if project.Name() == project_name]
        if not self.projects:
            QMessageBox.critical(self,"Error", "No project was found")
            sys.exit(1)

            
        print("enabled")
        print(self.projects)
        print(self.connection)
        try:
            self.login_instance.Open(self.connection, self.projects[0])
        except RuntimeError as err:
            
            QMessageBox.critical(self,"Error", f"Failed to filters: {err}")
          



        self.well_filter = SeisWare.FilterList()
        try:
            self.login_instance.FilterManager().GetAll(self.well_filter)
        except RuntimeError as err:
            QMessageBox.critical(self,"Error", f"Failed to filters: {err}")
            print(self.well_filter)

        filter_list = []
        for filter in self.well_filter:
            filter_type = filter.FilterType()
            if filter_type == 2:
                filter_name = filter.Name()
                filter_list.append(filter_name)

        with QSignalBlocker(self.filter_dropdown):
            self.filter_dropdown.clear() 
            self.filter_dropdown.addItems(filter_list)
            self.filter_dropdown.setCurrentIndex(-1)


        #project_name = self.project_selection.get()
        #self.projects = [project for project in self.project_list if project.Name() == project_name]
        #if not self.projects:
        #    QMessageBox.critical(self,"Error", "No project was found")
        #    sys.exit(1)

        #login_instance = SeisWare.LoginInstance()
        #try:
        #    login_instance.Open(self.connection, self.projects[0])
        #except RuntimeError as err:
        #    QMessageBox.critical(self,"Error", "Failed to connect to the project: " + str(err))

        ## Get the wells from the project
        #self.well_list = SeisWare.WellList()
        #try:
        #    login_instance.WellManager().GetAll(self.well_list)
        #except RuntimeError as err:
        #    QMessageBox.critical(self,"Error", "Failed to get all the wells from the project: " + str(err))


        ## Retrieve UWIs from the well_list
        ## Retrieve UWIs from the well_list and sort them
        #uwi_list = [well.UWI() for well in self.well_list]
        #self.sorted_uwi_list = sorted(uwi_list, reverse=False)

        #        # Get the grids from the project
        #self.grid_list = SeisWare.GridList()
        #try:
        #    self.login_instance.GridManager().GetAll(self.grid_list)
        #except RuntimeError as err:
        #    QMessageBox.critical(self,"Failed to get the grids from the project", err)
        #        # Create the Well Filter dropdown using OptionMenu and populate it with filter_list
        #self.grids = [grid.Name() for grid in self.grid_list]
        #self.grid_objects_with_names = [(grid, grid.Name()) for grid in self.grid_list]

    def on_filter_select(self, event):
        # Initialize a structure to store all the data, sorted as per your requirements.
   
        selected_filter = self.filter_dropdown.currentText()
        print(f"Selected filter: {selected_filter}")

        # Retrieve and apply the well filter
        well_filter = SeisWare.FilterList()
        self.login_instance.FilterManager().GetAll(well_filter)
        self.filtered_well_filter = [f for f in well_filter if f.Name() == selected_filter]
        print(self.filtered_well_filter)

        # Retrieve well information
        well_keys = SeisWare.IDSet()
        failed_well_keys = SeisWare.IDSet()
        well_list = SeisWare.WellList()
        self.login_instance.WellManager().GetKeysByFilter(self.filtered_well_filter[0], well_keys)
        self.login_instance.WellManager().GetByKeys(well_keys, well_list, failed_well_keys)
    
        # Map UWIs to Well IDs
        uwi_to_well_id = {well.UWI(): well.ID() for well in well_list}
        print(uwi_to_well_id)

        self.uwi_listbox.clear()
        for uwi in uwi_to_well_id.keys():
            self.uwi_listbox.addItem(uwi)

    
    def okay_clicked(self):
        uwi_list = []
        for index in range(self.selected_uwi_listbox.count()):
            item = self.selected_uwi_listbox.item(index)
            if item is not None:
                uwi_list.append(item.text())
        print(uwi_list)
        production_keys = SeisWare.IDSet()
        failed_production_keys = SeisWare.IDSet()
        productions = SeisWare.ProductionList()
        self.login_instance.ProductionManager().GetKeysByFilter(self.filtered_well_filter[0], production_keys)
        self.login_instance.ProductionManager().GetByKeys(production_keys, productions, failed_production_keys)
  
        # Process and return or display your productions data as needed
        print(productions)  # Placeholder for actual data handling


        all_production_volume_data = []

        # Initialize a set to collect unique Well IDs from all productions
        all_well_ids = set()

        for production in productions:


            try:
                
                self.login_instance.ProductionManager().PopulateWells(production)
                production_wells = SeisWare.ProductionWellList()
                production.Wells(production_wells)
                            # Populate Volumes for the Production
                self.login_instance.ProductionManager().PopulateVolumes(production)
                volume_list = SeisWare.ProductionVolumeList()
                production.Volumes(volume_list)

                production_volume_data = []
                print(production_wells)
        
                            # Collect data for each well in the production
                for well in production_wells:
                    well_key = well.WellID()
                    print("Well Key:", well_key)
                    all_well_ids.add(well_key)  
                
                    well_keys = SeisWare.IDSet([well_key]) 
                    failed_well_keys = SeisWare.IDSet()
                    well_list = SeisWare.WellList()
                    self.login_instance.WellManager().GetByKeys(well_keys, well_list, failed_well_keys)
                    # Map UWIs to Well IDs
                    uwi = {well.UWI() for well in well_list}
                    uwi_str = uwi.pop()
                           
                    if uwi_str in uwi_list: 
                        print(uwi_str)
                        for volume in volume_list:
                            volume_date = volume.VolumeDate()
                            formatted_date = f"{volume_date.year}-{str(volume_date.month).zfill(2)}-{str(volume_date.day).zfill(2)}"
                    

                            production_volume_data.append({
                                "uwi": uwi_str,
                                "date": formatted_date,
                                "oil_volume": volume.OilVolume(),
                                "gas_volume": volume.GasVolume()
                            })
                    else:    
                        print(uwi_str , "is not in list")
            
                all_production_volume_data.extend(production_volume_data)
            except Exception as e:
                print(f"Failed to process production wells: {e}")
      
        self.production_data = all_production_volume_data
        self.accept()
        print('swdone')
        return self.production_data


    # Event handlers and methods to replicate the functionality of your original class
    def move_selected_right(self):
        selected_items = self.uwi_listbox.selectedItems()
        for item in selected_items:
            self.uwi_listbox.takeItem(self.uwi_listbox.row(item))
            self.selected_uwi_listbox.addItem(item.text())
            

    def move_selected_left(self):
        selected_items = self.selected_uwi_listbox.selectedItems()
        for item in selected_items:
            self.selected_uwi_listbox.takeItem(self.selected_uwi_listbox.row(item))
            self.uwi_listbox.addItem(item.text())

    def move_all_right(self):
        for index in range(self.uwi_listbox.count()):
            item = self.uwi_listbox.item(index)
            self.selected_uwi_listbox.addItem(item.text())
        self.uwi_listbox.clear()

    def move_all_left(self):
        for index in range(self.selected_uwi_listbox.count()):
            item = self.selected_uwi_listbox.item(index)
            self.uwi_listbox.addItem(item.text())
        self.selected_uwi_listbox.clear()
    def clear_widgets(self):
        self.selected_uwi_listbox.clear()
        with QSignalBlocker(self.filter_dropdown):
            self.filter_dropdown.clear() 
            self.filter_dropdown.setCurrentIndex(-1)
        # Clear the selected_uwi_listbox
        self.uwi_listbox.clear()
    
# Main application logic

if __name__ == "__main__":
    app = QApplication(sys.argv)
    dialog = SeisWareConnectDialog()
    dialog.show()
    sys.exit(app.exec_())
