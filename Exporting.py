import os
import pandas as pd
from PySide6.QtWidgets import QApplication, QDialog, QFileDialog, QLabel, QLineEdit, QPushButton, QVBoxLayout, QHBoxLayout, QCheckBox, QMessageBox
from PySide6.QtCore import Qt
from PySide6.QtCore import Signal
import numpy as np



class ExportDialog(QDialog):
    def __init__(self, grid_well_data, well_info_df, zone_info_df, top_grid, bottom_grid, number_of_zones, export_options=None, parent=None):
        super().__init__(parent=parent)
        self.grid_well_data = grid_well_data
        self.well_info_df = well_info_df
        self.zone_info_df = zone_info_df
        self.number_of_zones = number_of_zones
        self.top_grid = top_grid
        self.bottom_grid = bottom_grid
        self.export_options = pd.DataFrame()
        self.name_ext = None
        self.output_directory = None
        
        self.export_options = export_options
        self.setup_ui()

    def setup_ui(self):
        self.setWindowTitle("Export Options")
        layout = QVBoxLayout()

        self.checkboxes = {}
        for export_type in ["Directional Surveys", "Lateral Lengths", "Zones", "Grids"]:
            checkbox = QCheckBox(export_type)
            layout.addWidget(checkbox)
            self.checkboxes[export_type] = checkbox

        self.name_entry = QLineEdit()
        layout.addWidget(QLabel("Name Ext:"))
        layout.addWidget(self.name_entry)

        self.directory_entry = QLineEdit()
        self.directory_entry.setText(r'')
        layout.addWidget(QLabel("Output Directory:"))
        directory_layout = QHBoxLayout()
        directory_layout.addWidget(self.directory_entry)
        directory_layout.addWidget(QPushButton("...", clicked=self.browse_directory))
        layout.addLayout(directory_layout)

        if self.export_options is not None and not self.export_options.empty:
            self.fill_options_from_dataframe()


        submit_button = QPushButton("Export")
        submit_button.clicked.connect(self.on_submit)
        layout.addWidget(submit_button)

        self.setLayout(layout)


    def fill_options_from_dataframe(self):
        # Fill the options from the dataframe
        options = self.export_options.set_index('Parameter').to_dict()['Value']
    
        self.name_entry.setText(options.get('name_ext', ''))
        self.directory_entry.setText(options.get('output_directory', r'C:\SeisWare'))
    
        for export_type, checkbox in self.checkboxes.items():
            if export_type in options:
                value = options[export_type]
                checkbox.setChecked(value in [True, 'True', 'true', 'TRUE'])




    def browse_directory(self):
        selected_dir = QFileDialog.getExistingDirectory(self, "Select Output Directory", self.directory_entry.text())
        if selected_dir:
            self.directory_entry.setText(selected_dir)

    def on_submit(self):
        self.name_ext = self.name_entry.text()
        self.output_directory = self.directory_entry.text()
                # Extracting the selected parameters


        export_parameters = self.get_selected_parameters()

        self.export_options = self.parameters_to_dataframe(export_parameters)
        self.accept()



        if not self.name_ext or not self.output_directory:
            QMessageBox.information(self, "Info", "Please fill in all fields.")
            return
        self.show_export_menu()
        if self.checkboxes["Directional Surveys"].isChecked():
            self.export_directional_surveys()
        if self.checkboxes["Lateral Lengths"].isChecked():
            self.export_lateral_lengths()
        if self.checkboxes["Zones"].isChecked():
            self.export_zones()
        if self.checkboxes["Grids"].isChecked():
            self.export_grids()

        self.update_export_window()
    
    def get_selected_parameters(self):
        selected_exports = {key: checkbox.isChecked() for key, checkbox in self.checkboxes.items()}
        return {
            'name_ext': self.name_ext,
            'output_directory': self.output_directory,
            'selected_exports': selected_exports
        }

    def parameters_to_dataframe(self, parameters):
        data = {
            'Parameter': ['name_ext', 'output_directory'] + list(parameters['selected_exports'].keys()),
            'Value': [parameters['name_ext'], parameters['output_directory']] + list(parameters['selected_exports'].values())
        }
        return pd.DataFrame(data)

    def get_selected_parameters(self):
        selected_exports = {key: checkbox.isChecked() for key, checkbox in self.checkboxes.items()}
        return {
            'name_ext': self.name_ext,
            'output_directory': self.output_directory,
            'selected_exports': selected_exports
        }

    def export_directional_surveys(self):
        try:
            df = pd.DataFrame(self.grid_well_data)
            excel_file_path = os.path.join(self.output_directory, f'{self.name_ext}_directional_surveys.xlsx')
            with pd.ExcelWriter(excel_file_path, engine='openpyxl') as writer:
                for UWI in df['UWI'].unique():
                    df_UWI = df[df['UWI'] == UWI]
                    df_UWI.to_excel(writer, sheet_name=UWI, index=False)
            print(f"Directional surveys data written to {excel_file_path}")
        except Exception as e:
            self.update_export_window()
            print(f"Failed to write directional surveys data: {e}")
  

    def export_lateral_lengths(self):
   
            try:
                # Add new columns

                print(self.well_info_df)
                self.well_info_df['Zone Type'] = 'ZonePercentage'
                self.well_info_df['Top Depth'] = '0'
                self.well_info_df['Base Depth'] = '0'

                # Rename columns that start with 'Zone'
                new_columns = {col: f"{self.name_ext} {col}" for col in self.well_info_df.columns if col.startswith('Zone')}
                
                self.well_info_df.rename(columns=new_columns, inplace=True)

                # Create CSV file path
                csv_file_path = os.path.join(self.output_directory, f'{self.name_ext}_lateral_and_zone.csv')

                # Write DataFrame to CSV
                self.well_info_df.to_csv(csv_file_path, index=False)

                print(f"Lateral lengths and zone data written to {csv_file_path}")
            except PermissionError:
                self.show_error_popup(f"Failed to write lateral lengths data: The file '{csv_file_path}' is already open.")
            except Exception as e:
                self.update_export_window()
                print(f"Failed to write lateral lengths data: {e}")


    def export_zones(self):
        csv_file_path = os.path.join(self.output_directory, f'{self.name_ext}_zones.csv')

        try:
            with open(csv_file_path, 'a') as f:
                pass
        except PermissionError:
            self.show_error_popup(f"Failed to write zone data: The file '{csv_file_path}' is already open. Please close it and try again.")
            return
        except Exception as e:
            self.update_export_window()
            self.show_error_popup(f"Failed to check zone data file due to an unexpected error: {e}")
            return

        try:
            self.zone_info_df['Zone Name'] = self.zone_info_df['Zone Name'].apply(lambda x: f"{self.name_ext} {x}")
            self.zone_info_df['Zone Type'] = 'DrilledZone'

            self.zone_info_df.to_csv(csv_file_path, index=False)
            print(f"Zones data written to {csv_file_path}")
        except PermissionError:
            self.show_error_popup(f"Failed to write zone data: The file '{csv_file_path}' is already open. Please close it and try again.")
        except Exception as e:
            self.update_export_window()
            self.show_error_popup(f"Failed to write zone data due to an unexpected error: {e}")













    def write_photon_grid(self, filename, grid_df, top_grid_column, grid_name):
        min_x = grid_df['X'].min()
        max_x = grid_df['X'].max()
        min_y = grid_df['Y'].min()
        max_y = grid_df['Y'].max()

        increment_x = (max_x - min_x) / (grid_df['X'].nunique() - 1)
        increment_y = (max_y - min_y) / (grid_df['Y'].nunique() - 1)

        n_rows = grid_df["Y"].nunique()
        n_cols = grid_df["X"].nunique()

        grid_df['Row'] = np.repeat(np.arange(n_rows), n_cols)
        grid_df['Column'] = np.tile(np.arange(n_cols), n_rows)

        data_lines = [f'{row[top_grid_column]} {row["Row"]} {row["Column"]}\n' for idx, row in grid_df.iterrows()]

        with open(filename, 'w') as f:
            f.write('#<SeisWare Grid Export - Photon ASCII Compatible>\n\n')
            f.write('struct Grid {\n')
            f.write('    Name\n')
            f.write('    MinX IncrementX\n')
            f.write('    MinY IncrementY\n')
            f.write('    RMSError NullValue\n')
            f.write('    Rows Columns\n')
            f.write('    Points[ N ] {\n')
            f.write('        Value Row Column\n')
            f.write('    }\n')
            f.write('}\n\n')
            f.write(f'Grid "{grid_name}"\n')
            f.write(f'{min_x} {increment_x}\n')
            f.write(f'{min_y} {increment_y}\n')
            f.write(f'0.000000 1.701410e+38\n')
            f.write(f'{n_rows} {n_cols}\n')
            f.write(f'{len(grid_df)}\n')
            f.writelines(data_lines)

    def export_grids(self):
   
        export_directory = self.output_directory
        if not os.path.exists(export_directory):
            os.makedirs(export_directory)

        top_grid_column = self.top_grid.columns[2]
        bottom_grid_column = self.bottom_grid.columns[2]
        print(self.top_grid)

        if top_grid_column not in self.top_grid.columns or bottom_grid_column not in self.bottom_grid.columns:
            print(f"Error: Missing '{top_grid_column}' or '{bottom_grid_column}' column in top_grid or bottom_grid.")
            return

        if not (self.top_grid[['X', 'Y']] == self.bottom_grid[['X', 'Y']]).all().all():
            print("Mismatch in grid coordinates.")
            return

        if self.number_of_zones is None:
            print("Error: number_of_zones is not set.")
            return

        try:
            number_of_zones = int(self.number_of_zones)
        except ValueError:
            print("Error: number_of_zones should be an integer.")
            return
                # Set extreme values to 0
        self.top_grid.loc[
            (self.top_grid[top_grid_column] > 1_000_000) | (self.top_grid[top_grid_column] < -1_000_000), 
            top_grid_column
        ] = 0

        self.bottom_grid.loc[
            (self.bottom_grid[bottom_grid_column] > 1_000_000) | (self.bottom_grid[bottom_grid_column] < -1_000_000), 
            bottom_grid_column
        ] = 0


        dif_df = pd.DataFrame()
        dif_df['z_diff'] = self.bottom_grid[bottom_grid_column] - self.top_grid[top_grid_column]

        zone_interval_df = pd.DataFrame()
        zone_interval_df['zone_interval'] = dif_df['z_diff'] / (number_of_zones - 1)

        zone_grids = []
        for i in range(number_of_zones - 2):
            intermediate_grid = self.top_grid.copy()
            intermediate_grid[top_grid_column] += zone_interval_df['zone_interval'] * (i + 1)


            zone_grids.append(intermediate_grid)

            grid_filename = os.path.join(export_directory, f'{self.name_ext}_zone_{i + 1}.grd')
            grid_name = f'{self.name_ext} Zone {i + 1} Grid'
            self.write_photon_grid(grid_filename, intermediate_grid, top_grid_column, grid_name)
            print(f"Grid {i + 1} exported as {grid_filename}")

        print("Export complete.")
  
        
    def show_error_popup(self, message):
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Critical)
        msg.setText(message)
        msg.setWindowTitle("Error")
        msg.setStandardButtons(QMessageBox.Ok)
        msg.exec_()
    
    def show_export_menu(self):
        self.exporting_msg = QMessageBox(self)
        self.exporting_msg.setText("Exporting data, please wait...")
        self.exporting_msg.setWindowTitle("Exporting")
        self.exporting_msg.setStandardButtons(QMessageBox.NoButton)
        self.exporting_msg.show()
        QApplication.processEvents()

    def update_export_window(self):
        self.exporting_msg.setText("Exporting done. Click OK to close.")
        self.exporting_msg.setStandardButtons(QMessageBox.Ok)
        QApplication.processEvents()

if __name__ == '__main__':
    import sys
    app = QApplication(sys.argv)
    ex = ExportDialog(None, None, None, None, None, None)
    ex.show()
    sys.exit(app.exec_())
