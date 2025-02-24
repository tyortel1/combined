import sys
import segyio
import numpy as np
import struct
import h5py
from scipy.spatial import KDTree
from PySide6.QtWidgets import (QApplication, QDialog, QVBoxLayout, QHBoxLayout, 
                               QWidget, QFileDialog, QMessageBox, QProgressDialog, QLineEdit, QLabel)
from PySide6.QtCore import Qt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import matplotlib.pyplot as plt
from StyledDropdown import StyledDropdown, StyledInputBox
from StyledButton import StyledButton 
from SeismicDatabaseManager import SeismicDatabaseManager

class SEGYViewer(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.figure, self.ax = plt.subplots()
        self.canvas = FigureCanvas(self.figure)
        layout = QVBoxLayout(self)
        layout.addWidget(self.canvas)

    def plot_segy_slice(self, trace_data, time_axis, slice_index=0):
        self.ax.clear()
    
        if len(trace_data.shape) == 3:
            slice_to_plot = trace_data[slice_index]
        elif len(trace_data.shape) == 2:
            slice_to_plot = trace_data
        else:
            raise ValueError(f"Unexpected data shape: {trace_data.shape}")

        num_traces_to_plot = min(100, slice_to_plot.shape[0])
        im = self.ax.imshow(slice_to_plot[:num_traces_to_plot, :].T, cmap='seismic', aspect='auto',
                            extent=[0, num_traces_to_plot, time_axis[-1], time_axis[0]])
    
        self.ax.set_title(f"Slice {slice_index}: First {num_traces_to_plot} traces")
        self.ax.set_xlabel("Trace Number")
        self.ax.set_ylabel("Time (ms)")
        self.figure.colorbar(im, ax=self.ax, label="Amplitude")
        self.canvas.draw()

class DataLoadSegy(QDialog):
    def __init__(self, parent=None, db_path=None):
        super().__init__(parent)
        self.setWindowTitle("SEG-Y Loader")
        self.setGeometry(100, 100, 800, 600)
        self.segy_file = None
        self.seismic_data = None
        self.bounding_box = None
        self.kdtree = None
        self.db_path = db_path
        self.sample_rate = None


                # Create the database manager if we have a path
        # Create the seismic database manager if we have a path
        if self.db_path:
            from SeismicDatabaseManager import SeismicDatabaseManager
            self.seismic_db = SeismicDatabaseManager(self.db_path)

        else:
            self.seismic_db = None
        
        self.setupUi()
  

    def setupUi(self):
        main_layout = QVBoxLayout(self)


        self.name_input = StyledInputBox("Name", "Enter seismic data name")
        main_layout.addWidget(self.name_input)

        self.format_dropdown = StyledDropdown("SEG-Y Format:", parent=self)
        self.format_dropdown.setItems(["SEG-Y Native Format", "SeisWare"])
        main_layout.addWidget(self.format_dropdown)

        self.datum_dropdown = StyledDropdown("Seismic Datum:", parent=self)
        self.datum_dropdown.setItems(["2000", "1500", "Custom"])
        main_layout.addWidget(self.datum_dropdown)

        load_button_layout = QHBoxLayout()
        self.load_button = StyledButton("Select SEG-Y File", "function")
        self.load_button.clicked.connect(self.select_segy_file)
        load_button_layout.addWidget(self.load_button)
        load_button_layout.addStretch()
        main_layout.addLayout(load_button_layout)

        self.segy_viewer = SEGYViewer()
        main_layout.addWidget(self.segy_viewer)

        bottom_layout = QHBoxLayout()
        bottom_layout.addStretch()
        self.close_button = StyledButton("Close", "close")
        self.close_button.clicked.connect(self.close)
        bottom_layout.addWidget(self.close_button)
        main_layout.addLayout(bottom_layout)

    def select_segy_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select SEGY File", "", "SEGY Files (*.segy *.sgy)")
        if file_path:
            self.segy_file = file_path
            self.process_segy_file(self.segy_file)





    def process_segy_file(self, file_path):
        segy_format = self.format_dropdown.currentText()
        datum = float(self.datum_dropdown.currentText()) if self.datum_dropdown.currentText() != "Custom" else None

        try:
            if segy_format == "SeisWare":
                with open(file_path, "rb") as f:
                    # Skip textual header
                    f.seek(3200)
                    bin_header = f.read(400)

                    sample_interval = struct.unpack("<H", bin_header[16:18])[0]
                    num_samples = struct.unpack("<H", bin_header[20:22])[0]
                    data_format = struct.unpack("<H", bin_header[24:26])[0]

                    # Convert sample interval to seconds
                    self.sample_rate = sample_interval / 1000.0  # Convert milliseconds to seconds

                    print("\n--- Binary Header Information ---")
                    print(f"Sample Interval: {sample_interval} ms")
                    print(f"Number of Samples: {num_samples}")
                    print(f"Data Format: {data_format}")

                    time_axis = np.arange(0, num_samples * sample_interval / 1000, sample_interval / 1000)

                    trace_data, inlines, crosslines, x_coords, y_coords = [], [], [], [], []

                    f.seek(3600)  # Move to first trace
                    file_size = f.seek(0, 2)  # Get file size
                    f.seek(3600)  # Reset to first trace

                    while f.tell() < file_size:
                        try:
                            trace_header = f.read(240)
                            if len(trace_header) < 240:
                                break

                            inline = struct.unpack("<i", trace_header[8:12])[0]
                            crossline = struct.unpack("<i", trace_header[12:16])[0]
                            x_coord = struct.unpack("<f", trace_header[80:84])[0]
                            y_coord = struct.unpack("<f", trace_header[84:88])[0]

                            trace_bytes = f.read(num_samples * 4)
                            if len(trace_bytes) < num_samples * 4:
                                break

                            trace = np.frombuffer(trace_bytes, dtype='<f4')
                            trace_data.append(trace)
                            inlines.append(inline)
                            crosslines.append(crossline)
                            x_coords.append(x_coord)
                            y_coords.append(y_coord)

                        except Exception as e:
                            print(f"Unexpected error processing trace: {e}")
                            break

                    # Convert lists to numpy arrays
                    trace_data = np.array(trace_data)
                    inlines = np.array(inlines)
                    crosslines = np.array(crosslines)
                    x_coords = np.array(x_coords)
                    y_coords = np.array(y_coords)

                    # Compute Bounding Box
                    self.bounding_box = None
                    if len(x_coords) > 1 and len(y_coords) > 1:
                        self.bounding_box = {
                            'min_x': np.min(x_coords),
                            'max_x': np.max(x_coords),
                            'min_y': np.min(y_coords),
                            'max_y': np.max(y_coords)
                        }

                        print("\n--- Computed Bounding Box (SeisWare) ---")
                        print(f"X Min: {self.bounding_box['min_x']}, X Max: {self.bounding_box['max_x']}")
                        print(f"Y Min: {self.bounding_box['min_y']}, Y Max: {self.bounding_box['max_y']}")

                        if self.bounding_box['max_x'] <= self.bounding_box['min_x'] or self.bounding_box['max_y'] <= self.bounding_box['min_y']:
                            print("ERROR: Invalid bounding box! Resetting.")
                            self.bounding_box = None

                    self.seismic_data = {
                        'trace_data': trace_data,
                        'time_axis': time_axis,
                        'x_coords': x_coords,
                        'y_coords': y_coords,
                        'inlines': inlines,
                        'crosslines': crosslines
                    }

            else:
                with segyio.open(file_path, "r", ignore_geometry=True) as segyfile:
                    total_traces = segyfile.tracecount
                    if total_traces == 0:
                        raise Exception("The SEG-Y file contains no traces.")

                    trace_data = segyfile.trace.raw[:]
                    time_axis = segyfile.samples

                    x_coords = segyfile.attributes(segyio.TraceField.SourceX)[:]
                    y_coords = segyfile.attributes(segyio.TraceField.SourceY)[:]
                    inlines = segyfile.attributes(segyio.TraceField.INLINE_3D)[:]
                    crosslines = segyfile.attributes(segyio.TraceField.CROSSLINE_3D)[:]

                    if len(time_axis) > 1:
                        self.sample_rate = time_axis[1] - time_axis[0]

                    print(f"\n--- SEG-Y (segyio) Information ---")
                    print(f"Sample Rate: {self.sample_rate} sec")
                    print(f"Time Axis Length: {len(time_axis)}")
                    print(f"Trace Data Shape: {trace_data.shape}")

                    # Compute Bounding Box
                    self.bounding_box = None
                    if len(x_coords) > 1 and len(y_coords) > 1:
                        self.bounding_box = {
                            'min_x': np.min(x_coords),
                            'max_x': np.max(x_coords),
                            'min_y': np.min(y_coords),
                            'max_y': np.max(y_coords)
                        }

                        print("\n--- Computed Bounding Box ---")
                        print(f"X Min: {self.bounding_box['min_x']}, X Max: {self.bounding_box['max_x']}")
                        print(f"Y Min: {self.bounding_box['min_y']}, Y Max: {self.bounding_box['max_y']}")

                        if self.bounding_box['max_x'] <= self.bounding_box['min_x'] or self.bounding_box['max_y'] <= self.bounding_box['min_y']:
                            print("ERROR: Invalid bounding box! Resetting.")
                            self.bounding_box = None

                    self.seismic_data = {
                        'trace_data': trace_data,
                        'time_axis': time_axis,
                        'x_coords': x_coords,
                        'y_coords': y_coords,
                        'inlines': inlines,
                        'crosslines': crosslines
                    }

            # Apply datum shift
            if datum is not None:
                self.seismic_data["time_axis"] = datum - self.seismic_data["time_axis"]

            # Plot the data
            self.segy_viewer.plot_segy_slice(self.seismic_data["trace_data"], self.seismic_data["time_axis"], slice_index=0)

            # --- Moved this out of the try-except ---
            if self.seismic_data and self.bounding_box:
                try:
                    progress = QProgressDialog("Building KD-tree...", None, 0, 100, self)
                    progress.setWindowModality(Qt.WindowModal)
                    progress.show()

                    progress.setValue(20)
                    self.build_kdtree()
                    progress.setValue(50)

                    progress.setLabelText("Preparing HDF5 save...")
                    hdf5_path = file_path.replace('.sgy', '.h5').replace('.segy', '.h5')

                    if self.save_to_hdf5(hdf5_path):
                        if self.seismic_db:
                            progress.setLabelText("Saving to database...")
                            progress.setValue(70)
                            self.save_to_database(file_path, hdf5_path)
                            progress.setValue(100)

                    progress.close()

                except Exception as e:
                    progress.close()
                    QMessageBox.critical(self, "Error", f"Failed to save data: {str(e)}")

            return len(trace_data) if "trace_data" in self.seismic_data and self.seismic_data["trace_data"] is not None else 0

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to process SEG-Y file: {str(e)}")
            return 0


    def get_seismic_data(self):
        return self.seismic_data

    def get_bounding_box(self):
        return self.bounding_box


    def save_to_hdf5(self, hdf5_path):
        """Save seismic data and KD-tree to HDF5 file"""
        try:
            progress = QProgressDialog("Saving seismic data to HDF5...", "Cancel", 0, 100, self)
            progress.setWindowModality(Qt.WindowModal)
            progress.show()
        
            with h5py.File(hdf5_path, 'w') as f:
                # Create main groups
                seismic_group = f.create_group('seismic_data')
            
                # Store seismic data with compression
                total_items = len(self.seismic_data)
                for i, (key, value) in enumerate(self.seismic_data.items()):
                    if isinstance(value, np.ndarray):
                        progress.setValue(int((i / total_items) * 70))  # First 70% for seismic data
                        progress.setLabelText(f"Saving seismic data: {key}")
                        if progress.wasCanceled():
                            return False
                        
                        seismic_group.create_dataset(
                            key,
                            data=value,
                            compression='gzip',
                            compression_opts=4,
                            chunks=True
                        )
            
                # Store KD-tree data if available
                if self.kdtree is not None:
                    progress.setValue(70)
                    progress.setLabelText("Saving KD-tree data...")
                    kdtree_group = f.create_group('kdtree')
                    kdtree_group.create_dataset('data', data=self.kdtree.data)
                    kdtree_group.attrs['leafsize'] = self.kdtree.leafsize
            
                # Store bounding box if available
                if self.bounding_box:
                    progress.setValue(90)
                    progress.setLabelText("Saving bounding box...")
                    bbox_group = f.create_group('bounding_box')
                    for key, value in self.bounding_box.items():
                        bbox_group.attrs[key] = value
            
                progress.setValue(100)
                progress.setLabelText("Save completed!")
            
            return True
        
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save HDF5 file: {str(e)}")
            return False
        finally:
            progress.close()
    def build_kdtree(self):
        """Build KD-tree from coordinate data"""
        if self.seismic_data and 'x_coords' in self.seismic_data and 'y_coords' in self.seismic_data:
            coords = np.column_stack((
                self.seismic_data['x_coords'],
                self.seismic_data['y_coords']
            ))
            self.kdtree = KDTree(coords, leafsize=16)
            return True
        return False

    def get_kdtree(self):
        """Return the constructed KD-tree"""
        return self.kdtree

    def save_to_database(self, original_path, hdf5_path):
        """Save seismic metadata to database"""
        if not self.seismic_db:
            print("No database path provided!")
            return False
        
        try:
            # Get the name from the input box
            seismic_name = self.name_input.text()
        
            # Check if name is empty
            if not seismic_name or seismic_name.strip() == "Enter seismic data name":
                QMessageBox.warning(self, "Warning", "Please enter a name for the seismic data.")
                return False
        
            file_info = {
                'name': seismic_name,  # Add the name to the metadata
                'original_segy_path': original_path,
                'hdf5_path': hdf5_path,
                'format': self.format_dropdown.currentText(),
                'datum': float(self.datum_dropdown.currentText()) if self.datum_dropdown.currentText() != "Custom" else None,
                'sample_rate': self.sample_rate,
                'num_samples': len(self.seismic_data['time_axis']),
                'geometry': {
                    'x_min': self.bounding_box['min_x'],
                    'x_max': self.bounding_box['max_x'],
                    'y_min': self.bounding_box['min_y'],
                    'y_max': self.bounding_box['max_y']
                }
            }
    
            # Add inline/crossline info if available
            if 'inlines' in self.seismic_data and 'crosslines' in self.seismic_data:
                file_info['geometry'].update({
                    'inline_min': np.min(self.seismic_data['inlines']),
                    'inline_max': np.max(self.seismic_data['inlines']),
                    'xline_min': np.min(self.seismic_data['crosslines']),
                    'xline_max': np.max(self.seismic_data['crosslines'])
                })
    
            self.seismic_db.save_seismic_file(file_info)
            return True
    
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save to database: {str(e)}")
            return False


if __name__ == "__main__":
    app = QApplication(sys.argv)
    dialog = DataLoadSegy()
    segy_file, accepted = dialog.exec()
    if accepted and segy_file:
        print(f"Selected SEG-Y file: {segy_file}")
    else:
        print("SEG-Y file selection cancelled")
    sys.exit(app.exec())
 