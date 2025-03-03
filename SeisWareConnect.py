from PySide6.QtWidgets import (
    QApplication, QDialog, QVBoxLayout, QHBoxLayout, 
    QMessageBox
)
import os
from PySide6.QtCore import Qt, QSignalBlocker
import numpy as np
import pandas as pd
import sys
import datetime
from StyledTwoListSelector import TwoListSelector
from StyledDropdown import StyledDropdown
from StyledButton import StyledButton

import SeisWare

class SeisWareConnectDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
     
        # Set dialog properties
        self.setWindowTitle("SeisWare Connect")
        self.setGeometry(590, 257, 800, 700)
        
        # Initialize class attributes
        self.project_list = []
        self.connection = SeisWare.Connection()
        self.login_instance = SeisWare.LoginInstance()
        self.well_list = []
        self.project_names = []
        self.projects = []
        self.filter_name = None
        self.grid_xyz_top = []
        self.filtered_well_filter = []
        self.directional_survey_values = []
        self.Grid_intersec_top = []
        self.Grid_intersec_bottom = []
        self.selected_item = None
        self.well_data_df = pd.DataFrame()
        self.UWIs_and_offsets = []
        self.UWI_to_well_dict = {}
        self.UWI_list = []
        self.filter_selection = None
        self.project_selection = None
        self.selected_UWIs = None

        # Initialize UI
        self.initUI()

        # Connect to SeisWare
        self.connect_to_seisware()

    def initUI(self):
        # Main layout
        main_layout = QVBoxLayout(self)

        # Top section for dropdowns
        top_layout = QVBoxLayout()
        
        # Project dropdown
        self.project_dropdown = StyledDropdown("Project:")
        self.project_dropdown.combo.currentIndexChanged.connect(self.on_project_select)
        top_layout.addWidget(self.project_dropdown)

        # Well filter dropdown
        self.filter_dropdown = StyledDropdown("Well Filter:")
        self.filter_dropdown.combo.setEnabled(False)
        self.filter_dropdown.combo.currentIndexChanged.connect(self.on_filter_select)
        top_layout.addWidget(self.filter_dropdown)

        main_layout.addLayout(top_layout)

        # Two-list selector for UWIs
        self.uwi_selector = TwoListSelector("Available UWIs", "Selected UWIs")
        self.uwi_selector.setFullHeight(True)  # Set full height as requested
        main_layout.addWidget(self.uwi_selector)

        # Button layout
        button_layout = QHBoxLayout()
        button_layout.addStretch()  # This pushes the button to the right

        # Okay button with styled green function button
        self.okay_button = StyledButton("Load Data", "function")
        self.okay_button.clicked.connect(self.okay_clicked)
        button_layout.addWidget(self.okay_button)

        main_layout.addLayout(button_layout)

        # Set the main layout
        self.setLayout(main_layout)

    def connect_to_seisware(self):
        """Connect to SeisWare with detailed debugging information."""
        print("\n=== Attempting to connect to SeisWare API ===")
    
        # Show the current working directory
        print(f"Current directory: {os.getcwd()}")
    
        # Debug where CreateServer is looking for the API executables
        print("\n=== DEBUGGING API SERVER SEARCH ===")
    
        # Get the executable directory
        exe_dir = os.path.dirname(sys.executable)
        print(f"Executable directory: {exe_dir}")
    
        # Check common locations for the API server executables
        search_dirs = [
            os.getcwd(),  # Current working directory
            exe_dir,  # Executable directory
            os.path.join(os.getcwd(), 'SeisWare'),  # SeisWare subdirectory
            os.path.join(exe_dir, 'SeisWare'),  # SeisWare subdirectory in exe dir
            os.path.join(os.environ.get('PROGRAMFILES', 'C:\\Program Files'), 'SeisWare'),
            os.path.join(os.environ.get('PROGRAMFILES(X86)', 'C:\\Program Files (x86)'), 'SeisWare'),
        ]
    
        # Files to check for
        api_files = ['SWAPIServer.exe', 'SWAPIService.exe', 'APIServer.exe']
    
        # Check each directory for the files
        print("\nChecking for API Server executables:")
        found_files = []
    
        for directory in search_dirs:
            if not os.path.exists(directory):
                continue
            
            print(f"\nSearching in: {directory}")
            for file in api_files:
                file_path = os.path.join(directory, file)
                if os.path.exists(file_path):
                    print(f"  FOUND: {file_path}")
                    found_files.append(file_path)
                else:
                    print(f"  Not found: {file_path}")
    
        if found_files:
            print(f"\nFound {len(found_files)} API Server executables:")
            for file in found_files:
                print(f"  {file}")
        else:
            print("\nNo API Server executables found in common locations!")
    
        print("=== END DEBUGGING INFO ===\n")
    
        try:
            print("1. Creating SeisWare.Connection object...")
            self.connection = SeisWare.Connection()
            print("   ✓ Connection object created successfully")
    
            print("2. Calling SeisWare.Connection.CreateServer()...")
        
            # Try to get source code information about CreateServer (this is speculative)
            try:
                import inspect
                createserver_source = inspect.getsource(SeisWare.Connection.CreateServer)
                print(f"CreateServer source code:\n{createserver_source}")
            except Exception as e:
                print(f"Could not retrieve CreateServer source: {e}")
        
            serverInfo = SeisWare.Connection.CreateServer()
            print(f"   ✓ Server info created: Endpoint={serverInfo.Endpoint()}")
    
            print(f"3. Connecting to server at {serverInfo.Endpoint()}:50000...")
            self.connection.Connect(serverInfo.Endpoint(), 50000)
            print("   ✓ Connection successful!")
    
            print("4. Getting project list...")
            self.project_list = SeisWare.ProjectList()
            self.connection.ProjectManager().GetAll(self.project_list)
            print(f"   ✓ Retrieved {len(self.project_list)} projects")
    
            # Show project names
            self.project_names = [project.Name() for project in self.project_list]
            print(f"   Project names: {', '.join(self.project_names)}")
    
            # Populate project dropdown
            with QSignalBlocker(self.project_dropdown.combo):
                self.project_dropdown.setItems(self.project_names)
                self.project_dropdown.setCurrentIndex(-1)
        
        except RuntimeError as err:
            print(f"❌ SeisWare API Error: {err}")
            print(f"   Error type: {type(err)}")
        
            # Additional debug info for this specific error
            if "APIServer executable could not be located" in str(err):
                print("\n=== API SERVER LOCATION DEBUG ===")
                print("The error indicates the SeisWare API cannot find its server executable.")
                print("This file needs to be included in your packaged application.")
            
                # Print PATH environment variable
                print("\nPATH environment variable:")
                path_dirs = os.environ.get('PATH', '').split(os.pathsep)
                for i, path in enumerate(path_dirs):
                    print(f"  [{i}] {path}")
                
                # Search Python module directory
                try:
                    import SeisWare
                    if hasattr(SeisWare, '__file__'):
                        seisware_dir = os.path.dirname(SeisWare.__file__)
                        print(f"\nSeisWare module directory: {seisware_dir}")
                        print("Files in SeisWare module directory:")
                        for file in os.listdir(seisware_dir):
                            print(f"  - {file}")
                except Exception as e:
                    print(f"Error listing SeisWare directory: {e}")
                
                print("=== END API SERVER LOCATION DEBUG ===\n")
        
            QMessageBox.critical(self,"Connection Error", f"Failed to connect to the server: {err}")
            return
        except Exception as e:
            print(f"❌ Unexpected Error: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self,"Connection Error", f"Unexpected error: {e}")
            return

    def on_project_select(self, index):
        # Enable filter dropdown
        self.filter_dropdown.combo.setEnabled(True)
      
        # Clear the content of the list selectors
        self.clear_widgets()
            
        self.login_instance = SeisWare.LoginInstance()

        project_name = self.project_dropdown.currentText()
        self.projects = [project for project in self.project_list if project.Name() == project_name]
        if not self.projects:
            QMessageBox.critical(self,"Error", "No project was found")
            sys.exit(1)

        try:
            self.login_instance.Open(self.connection, self.projects[0])
        except RuntimeError as err:
            QMessageBox.critical(self,"Error", f"Failed to open project: {err}")
            return

        self.well_filter = SeisWare.FilterList()
        try:
            self.login_instance.FilterManager().GetAll(self.well_filter)
        except RuntimeError as err:
            QMessageBox.critical(self,"Error", f"Failed to get filters: {err}")
            return

        # Filter for well filters (type 2)
        filter_list = []
        for filter in self.well_filter:
            filter_type = filter.FilterType()
            if filter_type == 2:
                filter_name = filter.Name()
                filter_list.append(filter_name)

        # Populate filter dropdown
        with QSignalBlocker(self.filter_dropdown.combo):
            self.filter_dropdown.setItems(filter_list)
            self.filter_dropdown.setCurrentIndex(-1)

    def on_filter_select(self, index):
        selected_filter = self.filter_dropdown.currentText()
        print(f"Selected filter: {selected_filter}")

        # Retrieve and apply the well filter
        well_filter = SeisWare.FilterList()
        self.login_instance.FilterManager().GetAll(well_filter)
        self.filtered_well_filter = [f for f in well_filter if f.Name() == selected_filter]

        # Retrieve well information
        well_keys = SeisWare.IDSet()
        self.well_list = SeisWare.WellList()
        try:
            # Get well keys for the selected filter
            self.login_instance.WellManager().GetKeysByFilter(self.filtered_well_filter[0], well_keys)

            # Retrieve well data 
            self.login_instance.WellManager().GetByKeys(well_keys, self.well_list, True)

            if not self.well_list:
                QMessageBox.warning(self, "No Wells Found", "No wells were found for the provided filter.")
                return

            # Clear and populate UWI list
            self.uwi_selector.set_left_items([well.UWI() for well in self.well_list])

            # Map UWIs to Well objects
            self.UWI_to_well_dict = {well.UWI(): well for well in self.well_list}

        except RuntimeError as err:
            QMessageBox.critical(self, "Failed to get wells", str(err))
    
    def okay_clicked(self):
        UWI_list = self.uwi_selector.get_right_items()
        
        if not UWI_list:
            QMessageBox.information(self, "Info", "No wells selected.")
            return
        production_keys = SeisWare.IDSet()
        failed_production_keys = SeisWare.IDSet()
        productions = SeisWare.ProductionList()
        self.login_instance.ProductionManager().GetKeysByFilter(self.filtered_well_filter[0], production_keys)
        self.login_instance.ProductionManager().GetByKeys(production_keys, productions, True)
  
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

                    # Create a set of WellKey objects for the current well_key
                    well_keys = SeisWare.IDSet([well_key])
                    failed_well_keys = SeisWare.IDSet()

                    # Create a WellList object to hold the results
                    well_list = SeisWare.WellList()

                    try:
                        # Retrieve well objects based on the well_keys
                        self.login_instance.WellManager().GetByKeys(well_keys, well_list, True)  # True to populate

                        # Iterate through the retrieved wells
                        for well in well_list:
                            # Assuming UWI is a method of the Well class
                            UWI_str = well.UWI()  
                            print(f"UWI: {UWI_str}")  

                            if UWI_str in UWI_list:
                                print(f"UWI {UWI_str} found in list.")

                                # Now, retrieve production volume data for this well
                                for volume in volume_list:
                                    # Format the volume date
                                    volume_date = volume.VolumeDate()
                                    formatted_date = f"{volume_date.year}-{str(volume_date.month).zfill(2)}-{str(volume_date.day).zfill(2)}"
                    
                                    # Append the production data to your list
                                    production_volume_data.append({
                                        "UWI": UWI_str,
                                        "date": formatted_date,
                                        "oil_volume": volume.OilVolume(),
                                        "gas_volume": volume.GasVolume()
                                    })
                            else:
                                print(f"{UWI_str} is not in the list.")
                    except Exception as e:
                        print(f"Failed to process production wells: {e}")
            
                all_production_volume_data.extend(production_volume_data)
            except Exception as e:
                print(f"Failed to process production wells: {e}")
      
        sorted_data = sorted(
            all_production_volume_data,
            key=lambda x: (x["UWI"], x["date"], x["oil_volume"] + x["gas_volume"]),
            reverse=True
        )
        
        # Create a dictionary to store the best row for each (UWI, date)
        seen = {}
        for row in sorted_data:
            key = (row["UWI"], row["date"])
            if key not in seen:
                seen[key] = row  # Keep the first occurrence (highest volumes due to sorting)

        self.production_data = list(seen.values())
        self.directional_surveys()
        self.accept()
        print('swdone')

        return self.production_data, self.directional_survey_values, self.well_data_df, self.selected_UWIs

    def directional_surveys(self):
        selected_UWIs = self.uwi_selector.get_right_items()
        self.selected_UWIs = selected_UWIs

        if not selected_UWIs:
            QMessageBox.information(self, "Info", "No wells selected for export.")
            return

        survey_data = []
        total_lat_data = []

        for UWI in selected_UWIs:
            well = self.UWI_to_well_dict.get(UWI)
            print(well)
            if well:
                depth_unit = SeisWare.Unit.Meter
                surfaceX = well.TopHole().x.Value(depth_unit)
                surfaceY = well.TopHole().y.Value(depth_unit)
                surfaceDatum = well.DatumElevation().Value(depth_unit)
                print(f"Well ID: {well.ID()}")

                spud_date_struct = well.SpudDate()
                print(f"Spud Date Struct - Year: {spud_date_struct.year}, Month: {spud_date_struct.month}, Day: {spud_date_struct.day}")

                # Validate spud date
                if spud_date_struct.year and spud_date_struct.month and spud_date_struct.day:
                    try:
                        spud_date = datetime.date(
                            spud_date_struct.year,
                            spud_date_struct.month,
                            spud_date_struct.day
                        )
                        print(f"Extracted Spud Date: {spud_date}")
                    except ValueError as e:
                        print(f"Error creating date from attributes: {e}")
                        spud_date = None
                else:
                    print("Spud date is not available or incomplete.")
                    spud_date = None

                dirsrvylist = SeisWare.DirectionalSurveyList()
                self.login_instance.DirectionalSurveyManager().GetAllForWell(well.ID(), dirsrvylist)
                dirsrvy = [i for i in dirsrvylist if i.OffsetNorthType() > 0]

                if dirsrvy:
                    self.login_instance.DirectionalSurveyManager().PopulateValues(dirsrvy[0])
                    srvypoints = SeisWare.DirectionalSurveyPointList()
                    dirsrvy[0].Values(srvypoints)

                    previous_md = None
                    previous_tvd = None
                    previous_x = None
                    previous_y = None
                    start_lat = None
                    heel_x, heel_y = None, None
                    toe_x, toe_y = None, None
                    cumulative_distance = 0
                    tvd_sum = 0
                    tvd_count = 0

                    for point in srvypoints:
                        well_UWI = well.UWI()
                        x_offset = surfaceX + point.xOffset.Value(depth_unit)
                        y_offset = surfaceY + point.yOffset.Value(depth_unit)
                        tvd = surfaceDatum - point.tvd.Value(depth_unit)
                        md = point.md.Value(depth_unit)

                        # Update TVD sum and count for average TVD calculation
                        tvd_sum += tvd
                        tvd_count += 1

                        # Calculate cumulative distance
                        if previous_x is not None and previous_y is not None:
                            distance = np.sqrt((x_offset - previous_x)**2 + (y_offset - previous_y)**2)
                            cumulative_distance += distance

                        # Calculate inclination for heel detection
                        if previous_md is not None and previous_tvd is not None:
                            delta_md = md - previous_md
                            delta_tvd = tvd - previous_tvd
                            inclination = np.degrees(np.arccos(delta_tvd / delta_md)) if delta_md != 0 else 0.0

                            # Capture heel point
                            if start_lat is None and inclination < 95:
                                start_lat = md
                                heel_x, heel_y = x_offset, y_offset
                                heel_md = md
                        else:
                            inclination = 0.0

                        # Store survey point data
                        survey_data.append([well_UWI, x_offset, y_offset, md, tvd, cumulative_distance])

                        # Update toe point (last valid point)
                        toe_x, toe_y = x_offset, y_offset

                        # Update previous values
                        previous_md = md
                        previous_tvd = tvd
                        previous_x = x_offset
                        previous_y = y_offset

                    # Calculate total lateral distance and average TVD
                    end_lat = md
                    avg_tvd = tvd_sum / tvd_count if tvd_count > 0 else None

                    if start_lat is not None:
                        total_lat = end_lat - start_lat
                        total_lat_data.append((well_UWI, 'Active', surfaceX, surfaceY, total_lat, heel_x, heel_y, toe_x, toe_y, heel_md, end_lat, avg_tvd, end_lat, spud_date))
                    else:
                        total_lat_data.append((well_UWI, 'Active', surfaceX, surfaceY, None, None, None, None, None, None, None, None, None, spud_date))

                else:
                    QMessageBox.warning(self, "Warning", f"No directional survey found for well {UWI}.")

        # Create directional survey DataFrame
        self.directional_survey_values = pd.DataFrame(
            survey_data,
            columns=['UWI', 'X Offset', 'Y Offset', 'MD', 'TVD', 'Cumulative Distance']
        )
        print("Directional Survey Data:")
        print(self.directional_survey_values)

        # Create well data DataFrame with proper column order
        self.well_data_df = pd.DataFrame(
            total_lat_data,
            columns=['UWI', 'status', 'surface_x', 'surface_y', 'lateral', 
                     'heel_x', 'heel_y', 'toe_x', 'toe_y', 'heel_md', 
                     'toe_md', 'average_tvd', 'total_length', 'spud_date']
        )
        print("Well Data:")
        print(self.well_data_df)
        self.well_data_df['spud_date'] = self.well_data_df['spud_date'].apply(lambda x: x if pd.notnull(x) else None)


    def clear_widgets(self):
        # Clear UWI selector
        self.uwi_selector.set_left_items([])
        self.uwi_selector.set_right_items([])
    
# Main application logic

if __name__ == "__main__":
    import sys
    print("Starting application...")
    app = QApplication.instance() or QApplication(sys.argv)
    print("QApplication initialized:", QApplication.instance())
    dialog = SeisWareConnectDialog()
    dialog.exec_()
    print("Dialog execution completed.")
    sys.exit(app.exec_())