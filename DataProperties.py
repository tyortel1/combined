
from select import select
import tkinter as tk
import tkinter.ttk as ttk
from tkinter import messagebox
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np  # Import NumPy
import matplotlib.pyplot as plt
import tkinter as tk
from mpl_toolkits.axes_grid1 import make_axes_locatable
import numpy as np
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.widgets import Button
from matplotlib.lines import Line2D
import matplotlib.pyplot as plt
from PySide6.QtWidgets import QApplication, QMainWindow, QPushButton
from matplotlib.widgets import Cursor
import numpy as np
from tkinter import messagebox
import plotly.express as px
import sys
sys.path.append('C:\Program Files')
import SeisWare


def main(*args):
    '''Main entry point for the application.'''
    global root
    root = tk.Tk()

    root.protocol('WM_DELETE_WINDOW', root.destroy)
    _w1 = ImageGUI(root)
    root.mainloop()
    _w1.run()

class ImageGUI:

    # MAING DIALOG BUILDING
    def __init__(self, top=None):
        self.top = top

        self.top.geometry("700x700+590+257")
        self.top.minsize(120, 1)
        self.top.maxsize(6500, 1181)
        self.top.resizable(1, 1)

        self.top.title("Deviation Analyzer")
        self.top.configure(background="white")

        self.connection = None
        self.connection = None
        self.project_var = tk.StringVar()
        self.well_list = None
        self.project_names = None
        self.project_list = None
        self.curve_calibration_dict = {}
        self.filter_name = None
        self.grid_xyz_top = []






        self.label_config = {
            "background": "white",
            "foreground": "#000000",
            "anchor": 'w'
        }

        self.project_selection = tk.StringVar(value=None)
        self.project_dropdown = ttk.OptionMenu(self.top, self.project_selection, "", command=self.on_project_select)
        self.project_label = tk.Label(self.top, text="Project:")
        self.project_label.configure(**self.label_config)
        self.project_label.place(relx=0.01, rely=0.005, relwidth=0.09)
        
        self.filter_selection = tk.StringVar(value=None)
        self.filter_label = tk.Label(self.top, text="Well Filter:")
        self.filter_label.configure(**self.label_config)
        self.filter_dropdown = ttk.OptionMenu(self.top, self.filter_selection, "", command=self.on_filter_select)
        self.filter_label.place(relx=0.01, rely=0.035, relwidth=0.09)


        self.UWI_listbox = tk.Listbox(self.top, selectmode=tk.MULTIPLE)
        self.UWI_listbox.place(relx=0.01, rely=0.09, relwidth=0.44, relheight=0.6)
        #self.UWI_listbox.bind('<<ListboxSelect>>', self.on_UWI_select)

        self.selected_UWI_listbox = tk.Listbox(self.top, selectmode=tk.MULTIPLE)
        self.selected_UWI_listbox.place(relx=0.53, rely=0.09, relwidth=0.44, relheight=0.6)
        #self.selected_UWI_listbox.bind('<<ListboxSelect>>', self.on_selected_UWI_select)
        
        # Bind mouse events for moving items
        self.UWI_listbox.bind("<ButtonPress-1>", self.on_UWI_listbox_click)
        self.UWI_listbox.bind("<B1-Motion>", self.on_UWI_listbox_drag)
        self.selected_UWI_listbox.bind("<ButtonPress-1>", self.on_selected_UWI_listbox_click)
        self.selected_UWI_listbox.bind("<B1-Motion>", self.on_selected_UWI_listbox_drag)

        # Create a vertical scrollbar for UWI_listbox
        self.UWI_listbox_scrollbar = tk.Scrollbar(self.top, orient=tk.VERTICAL)
        self.UWI_listbox_scrollbar.place(relx=0.44, rely=0.09, relheight=0.6)
        self.UWI_listbox.config(yscrollcommand=self.UWI_listbox_scrollbar.set)
        self.UWI_listbox_scrollbar.config(command=self.UWI_listbox.yview)


        # Create a vertical scrollbar for selected_UWI_listbox
        self.selected_UWI_listbox_scrollbar = tk.Scrollbar(self.top, orient=tk.VERTICAL)
        self.selected_UWI_listbox_scrollbar.place(relx=0.96, rely=0.09, relheight=0.6)
        self.selected_UWI_listbox.config(yscrollcommand=self.selected_UWI_listbox_scrollbar.set)
        self.selected_UWI_listbox_scrollbar.config(command=self.selected_UWI_listbox.yview)

                # Create a button to move selected items from UWI_listbox to selected_UWI_listbox
        self.move_right_button = tk.Button(self.top, text=">", command=self.move_selected_right)
        self.move_right_button.place(relx=0.47, rely=0.35, relwidth=0.05)

        # Create a button to move selected items from selected_UWI_listbox to UWI_listbox
        self.move_left_button = tk.Button(self.top, text="<", command=self.move_selected_left)
        self.move_left_button.place(relx=0.47, rely=0.4, relwidth=0.05)

                # Create a button to move all items from UWI_listbox to selected_UWI_listbox
        self.move_all_right_button = tk.Button(self.top, text=">>", command=self.move_all_right)
        self.move_all_right_button.place(relx=0.47, rely=0.3, relwidth=0.05)

        # Create a button to move all items from selected_UWI_listbox to UWI_listbox
        self.move_all_left_button = tk.Button(self.top, text="<<", command=self.move_all_left)
        self.move_all_left_button.place(relx=0.47, rely=0.45, relwidth=0.05)
        # Create a context menu for listboxes
        self.context_menu = tk.Menu(self.top, tearoff=0)
        self.context_menu.add_command(label="Copy", command=self.copy_selected_item)

        # Bind the right-click event to show the context menu
        self.UWI_listbox.bind("<Button-3>", self.show_context_menu)
        self.selected_UWI_listbox.bind("<Button-3>", self.show_context_menu)

        #self.export_label = tk.Label(self.top, text="Export:")
        #self.export_label.configure(**self.label_config)
        #self.export_label.place(relx=0.01, rely=0.90, relwidth=0.1)
        #self.export_button = tk.Button(self.top, text="Export", command=self.fetch_and_process_monthly_production)
        #self.export_button.place(relx=0.15, rely=0.90, relwidth=0.2)

        # Hide the label and dropdown initially
        self.project_label.place_forget()
        self.project_dropdown.place_forget()
        self.filter_label.place_forget()
        self.filter_dropdown.place_forget()
        self.connection = SeisWare.Connection()
        self.connect_to_seisware()
        self.login_instance = SeisWare.LoginInstance()
        self.grid_df = pd.DataFrame() 
        self.directional_survey_values = []
        self.directional_survey_values = []
        self.Grid_intersec_top = []
        self.Grid_intersec_bottom = []
        self.selected_item = None
        self.UWIs_and_offsets = []
        self.line_segments = [] 
        self.drawing = False
        self.line = None
        self.x_data = []
        self.y_data = []
        self.canvas = None
        self.closest_well = None



    def show_context_menu(self, event):
        # Get the widget that triggered the event
        source_widget = event.widget

        if source_widget == self.UWI_listbox:
            # The event originated from self.UWI_listbox
            # Deselect all items in both listboxes
            self.UWI_listbox.selection_clear(0, tk.END)
            self.selected_UWI_listbox.selection_clear(0, tk.END)

            # Find the closest item to the right-click position in self.UWI_listbox
            nearest_index = self.UWI_listbox.nearest(event.y)

            # Select the closest item in self.UWI_listbox
            self.UWI_listbox.selection_set(nearest_index)
            self.selected_item = self.UWI_listbox.get(nearest_index)
        elif source_widget == self.selected_UWI_listbox:
            # The event originated from self.selected_UWI_listbox
            # Deselect all items in both listboxes
            self.UWI_listbox.selection_clear(0, tk.END)
            self.selected_UWI_listbox.selection_clear(0, tk.END)

            # Find the closest item to the right-click position in self.selected_UWI_listbox
            nearest_index = self.selected_UWI_listbox.nearest(event.y)

            # Select the closest item in self.selected_UWI_listbox
            self.selected_UWI_listbox.selection_set(nearest_index)
            self.selected_item = self.selected_UWI_listbox.get(nearest_index)  # Corrected here

        # Display the context menu at the cursor position
        self.context_menu.post(event.x_root, event.y_root)

    def copy_selected_item(self):
        if self.selected_item:
            self.top.clipboard_clear()
            self.top.clipboard_append(self.selected_item)
            self.top.update()


 
    # Create a tkinter window (app) and the listboxes, and configure the context menu





    def on_UWI_listbox_click(self, event):
        index = self.UWI_listbox.nearest(event.y)
        self.UWI_listbox.anchor = index
        self.UWI_listbox.selection_clear(0, tk.END)
        self.UWI_listbox.selection_set(index)
    def on_UWI_listbox_drag(self, event):
        if self.UWI_listbox.anchor is not None:
            index = self.UWI_listbox.nearest(event.y)
            self.UWI_listbox.selection_clear(0, tk.END)
            self.UWI_listbox.selection_set(self.UWI_listbox.anchor, index)
    def on_selected_UWI_listbox_click(self, event):
        index = self.selected_UWI_listbox.nearest(event.y)
        self.selected_UWI_listbox.anchor = index
        self.selected_UWI_listbox.selection_clear(0, tk.END)
        self.selected_UWI_listbox.selection_set(index)
    def on_selected_UWI_listbox_drag(self, event):
        if self.selected_UWI_listbox.anchor is not None:
            index = self.selected_UWI_listbox.nearest(event.y)
            self.selected_UWI_listbox.selection_clear(0, tk.END)
            self.selected_UWI_listbox.selection_set(self.selected_UWI_listbox.anchor, index)
    def move_selected_right(self):
        selected_indices = self.UWI_listbox.curselection()
        items_to_move = [self.UWI_listbox.get(index) for index in selected_indices]

        # Iterate over the items to move and delete them one by one
        for item in items_to_move:
            self.UWI_listbox.delete(self.UWI_listbox.get(0, tk.END).index(item))

        # Insert the deleted items into the selected_UWI_listbox
        for item in items_to_move:
            self.selected_UWI_listbox.insert(tk.END, item)

        self.store_UWIs_and_offsets()
    def move_selected_left(self):
        selected_indices = self.selected_UWI_listbox.curselection()
        items_to_move = [self.selected_UWI_listbox.get(index) for index in selected_indices]

        # Iterate over the items to move and delete them one by one
        for item in items_to_move:
            self.selected_UWI_listbox.delete(self.selected_UWI_listbox.get(0, tk.END).index(item))

        # Insert the deleted items into the UWI_listbox
        for item in items_to_move:
            self.UWI_listbox.insert(tk.END, item)
    def move_all_right(self):
        items_to_move = list(self.UWI_listbox.get(0, tk.END))

        # Delete all items from UWI_listbox
        self.UWI_listbox.delete(0, tk.END)

        # Insert all items into selected_UWI_listbox
        for item in items_to_move:
            self.selected_UWI_listbox.insert(tk.END, item)
        self.store_UWIs_and_offsets()
    def move_all_left(self):
        items_to_move = list(self.selected_UWI_listbox.get(0, tk.END))

        # Delete all items from selected_UWI_listbox
        self.selected_UWI_listbox.delete(0, tk.END)

        # Insert all items into UWI_listbox
        for item in items_to_move:
            self.UWI_listbox.insert(tk.END, item)

        
    def connect_to_seisware(self):
        # Connect to API
        self.connection = SeisWare.Connection()
        try:
            serverInfo = SeisWare.Connection.CreateServer()
            self.connection.Connect(serverInfo.Endpoint(), 50000)
        except RuntimeError as err:
            messagebox.showerror("Connection Error", f"Failed to connect to the server: {err}")
            return

        self.project_list = SeisWare.ProjectList()
        try:
            self.connection.ProjectManager().GetAll(self.project_list)
        except RuntimeError as err:
            messagebox.showerror("Error", f"Failed to get the project list from the server: {err}")
            return

                # Put project names in Dropdown
        self.project_names = [project.Name() for project in self.project_list]
        self.project_selection = tk.StringVar(value=None)

        # Create the OptionMenu with the updated project_names
        self.project_dropdown = ttk.OptionMenu(self.top, self.project_selection, "", *self.project_names,command=self.on_project_select)


        # Show the label and dropdown
        self.project_label.place(relx=0.01, rely=0.005, relwidth=0.1)
        self.project_dropdown.place(relx=0.15, rely=0.005, relwidth=0.2)

    def clear_widgets(self):
        # Clear the UWI listbox and selected UWI listbox
        if hasattr(self, 'UWI_listbox') and self.UWI_listbox:
            self.UWI_listbox.delete(0, 'end')

        if hasattr(self, 'selected_UWI_listbox') and self.selected_UWI_listbox:
            self.selected_UWI_listbox.delete(0, 'end')


    def on_project_select(self, event):
                # Clear the content of the list selectors
        self.clear_widgets()

        #self.connection = SeisWare.Connection()
        self.login_instance = SeisWare.LoginInstance()


        # Clear previous selections and values
        self.filter_selection.set("")  # Clear the filter selection

        # Clear the filter dropdown if it exists
        try:
            self.filter_dropdown.set("")
        except AttributeError:
            pass

        # Clear the well UWI selection if it exists
        try:
            self.planned_UWI.set("")
        except AttributeError:
            pass


        
        project_name = self.project_selection.get()
        self.projects = [project for project in self.project_list if project.Name() == project_name]
        if not self.projects:
            messagebox.showerror("Error", "No project was found")
            sys.exit(1)

        
        try:
            self.login_instance.Open(self.connection, self.projects[0])
        except RuntimeError as err:
            messagebox.showerror("Error", "Failed to connect to the project: " + str(err))

        self.well_filter = SeisWare.FilterList()
        try:
            self.login_instance.FilterManager().GetAll(self.well_filter)
        except RuntimeError as err:
            messagebox.showerror("Error", f"Failed to filters: {err}")
            print(self.well_filter)

        filter_list = []

        for filter in self.well_filter:
            filter_type = filter.FilterType()  # 
            if filter_type == 2:
                filter_name = filter.Name()  # 
                filter_info = f"{filter_name}"
                filter_list.append(filter_info)

        # Create the Well Filter dropdown using OptionMenu and populate it with filter_list
        self.filter_selection = tk.StringVar(value="")
        self.filter_dropdown = ttk.OptionMenu(self.top, self.filter_selection, "", *filter_list, command=self.on_filter_select)
        self.fiilter_label = tk.Label(self.top, text="Project:")
        self.filter_label.configure(**self.label_config)
        self.filter_label.place(relx=0.01, rely=0.035, relwidth=0.1)
        # Place the Well Filter dropdown on the interface
        self.filter_dropdown.place(relx=0.15, rely=0.035, relwidth=0.2)


        project_name = self.project_selection.get()
        self.projects = [project for project in self.project_list if project.Name() == project_name]
        if not self.projects:
            messagebox.showerror("Error", "No project was found")
            sys.exit(1)

        login_instance = SeisWare.LoginInstance()
        try:
            login_instance.Open(self.connection, self.projects[0])
        except RuntimeError as err:
            messagebox.showerror("Error", "Failed to connect to the project: " + str(err))

        # Get the wells from the project
        self.well_list = SeisWare.WellList()
        try:
            login_instance.WellManager().GetAll(self.well_list)
        except RuntimeError as err:
            messagebox.showerror("Error", "Failed to get all the wells from the project: " + str(err))


        # Retrieve UWIs from the well_list
       # Retrieve UWIs from the well_list and sort them
        UWI_list = [well.UWI() for well in self.well_list]
        self.sorted_UWI_list = sorted(UWI_list, reverse=False)

                # Get the grids from the project
        self.grid_list = SeisWare.GridList()
        try:
            self.login_instance.GridManager().GetAll(self.grid_list)
        except RuntimeError as err:
            messagebox.showerror("Failed to get the grids from the project", err)
                # Create the Well Filter dropdown using OptionMenu and populate it with filter_list
        self.grids = [grid.Name() for grid in self.grid_list]
        self.grid_objects_with_names = [(grid, grid.Name()) for grid in self.grid_list]

    def on_filter_select(self, event):
        # Initialize a structure to store all the data, sorted as per your requirements.
     
        selected_filter = self.filter_selection.get()
        print(f"Selected filter: {selected_filter}")

        # Retrieve and apply the well filter
        well_filter = SeisWare.FilterList()
        self.login_instance.FilterManager().GetAll(well_filter)
        filtered_well_filter = [f for f in well_filter if f.Name() == selected_filter]
        print(filtered_well_filter)

        ## Retrieve well information
        #well_keys = SeisWare.IDSet()
        #failed_well_keys = SeisWare.IDSet()
        #well_list = SeisWare.WellList()
        #self.login_instance.WellManager().GetKeysByFilter(filtered_well_filter[0], well_keys)
        #self.login_instance.WellManager().GetByKeys(well_keys, well_list, failed_well_keys)
    
        ## Map UWIs to Well IDs
        #UWI_to_well_id = {well.UWI(): well.ID() for well in well_list}
        #print(UWI_to_well_id)

        production_keys = SeisWare.IDSet()
        failed_production_keys = SeisWare.IDSet()
        productions = SeisWare.ProductionList()
        self.login_instance.ProductionManager().GetKeysByFilter(filtered_well_filter[0], production_keys)
        self.login_instance.ProductionManager().GetByKeys(production_keys, productions, failed_production_keys)
        print(productions)


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
                    UWI = {well.UWI() for well in well_list}
                    print(UWI)
                 
                    for volume in volume_list:
                        volume_date = volume.VolumeDate()
                        formatted_date = f"{volume_date.year}-{str(volume_date.month).zfill(2)}-{str(volume_date.day).zfill(2)}"
                    

                        production_volume_data.append({
                            "prod name": production.Name(),
                            "UWI": UWI,
                            "date": formatted_date,
                            "oil_volume": volume.OilVolume(),
                            "gas_volume": volume.GasVolume()
                        })
                       
                all_production_volume_data.extend(production_volume_data)

            except Exception as e:
                print(f"Failed to process production wells: {e}")
        df = pd.DataFrame(all_production_volume_data)

        # Define the order of columns in the DataFrame
        columns_order = ["prod name", "UWI", "date", "oil_volume", "gas_volume"]

        # Reorder columns in the DataFrame
        df = df[columns_order]

        # Write the DataFrame to an Excel file
        excel_file = "production_volume_data.xlsx"
        df.to_excel(excel_file, index=False)

        print("Production volume data has been written to", excel_file)
        #print("success")







    def load_UWI_list(self):
        # Assuming UWI_list contains your data
        UWI_list = self.well_list
        sorted_UWI_list = sorted(UWI_list, reverse=False)

        for UWI in sorted_UWI_list:
            self.UWI_listbox.insert(tk.END, UWI)
    def on_UWI_select(self, event):
        selected_indices = self.UWI_listbox.curselection()
        selected_UWIs = [self.UWI_listbox.get(idx) for idx in selected_indices]
        # Add the selected UWIs to the selected listbox
        for UWI in selected_UWIs:
            self.selected_UWI_listbox.insert(tk.END, UWI)
        # Remove the selected UWIs from the original listbox
        for idx in reversed(selected_indices):
            self.UWI_listbox.delete(idx)

        self.store_UWIs_and_offsets()
    def on_selected_UWI_select(self, event):
        selected_indices = self.selected_UWI_listbox.curselection()
        self.selected_UWIs = [self.selected_UWI_listbox.get(idx) for idx in selected_indices]
        # Add the selected UWIs back to the original listbox
        for UWI in self.selected_UWIs:
            self.UWI_listbox.insert(tk.END, UWI)
        # Remove the selected UWIs from the selected listbox
        for idx in reversed(selected_indices):
            self.selected_UWI_listbox.delete(idx)

        self.store_UWIs_and_offsets()
    def on_grid_select(self,event):
        
        grid_name = self.grid_combobox.get()
        selected_grid_object = None
        for grid, name in self.grid_objects_with_names:
            if name == grid_name:
                selected_grid_object = grid
                break
        print(selected_grid_object)
     
        try:
            self.login_instance.GridManager().PopulateValues(selected_grid_object)
        except RuntimeError as err:
            messagebox.showerror("Failed to populate the values of grid %s from the project" % (grid), err)
    
        grid_values = SeisWare.GridValues()
        grid.Values(grid_values)
        
        # Fill a DF with X, Y, Z values
        self.grid_xyz_top = []
        grid_values_list = list(grid_values.Data())
        print(grid_values_list)
        counter = 0
        for i in range(grid_values.Height()):
            for j in range(grid_values.Width()):
                self.grid_xyz_top.append((grid.Definition().RangeY().start + i * grid.Definition().RangeY().delta,
                                grid.Definition().RangeX().start + j * grid.Definition().RangeX().delta,
                                grid_values_list[counter]))
                counter += 1
                print(counter)
        # Create DataFrame
        print(self.grid_xyz_top)
        self.grid_df = pd.DataFrame(self.grid_xyz_top, columns=["Y", "X", f"{grid.Name()}"])
    def on_grid_select_bottom(self,event):
        
        grid_name = self.grid_bottom_combobox.get()
        selected_grid_object = None
        for grid, name in self.grid_objects_with_names:
            if name == grid_name:
                selected_grid_object = grid
                break
        print(selected_grid_object)
     

        try:
            self.login_instance.GridManager().PopulateValues(selected_grid_object)
        except RuntimeError as err:
            messagebox.showerror("Failed to populate the values of grid %s from the project" % (grid), err)
    
            

        grid_values = SeisWare.GridValues()
        grid.Values(grid_values)
        
        # Fill a DF with X, Y, Z values
        self.grid_xyz_bottom = []
        grid_values_list = list(grid_values.Data())
        print(grid_values_list)
        counter = 0
        for i in range(grid_values.Height()):
            for j in range(grid_values.Width()):
                self.grid_xyz_bottom.append((grid.Definition().RangeY().start + i * grid.Definition().RangeY().delta,
                                grid.Definition().RangeX().start + j * grid.Definition().RangeX().delta,
                                grid_values_list[counter]))
                counter += 1
                print(counter)
        # Create DataFrame
        print(self.grid_xyz_bottom)
        self.grid_df = pd.DataFrame(self.grid_xyz_bottom, columns=["Y", "X", f"{grid.Name()}"])
        


 
        


    def filter_UWI_values(self, event):
        typed_text = event.widget.get().lower()
        
        # Filter the values based on the typed text
        matching_items = [item for item in self.sorted_UWI_list if typed_text in item.lower()]

        # Update the Combobox values to show the filtered items
        event.widget['values'] = matching_items
if __name__ == '__main__':
    root = tk.Tk()
    app = ImageGUI(root)
    root.mainloop()