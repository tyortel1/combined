import sys
import segyio
import numpy as np
import struct
import h5py
import os
import datetime
from scipy.spatial import KDTree
from PySide6.QtWidgets import (QApplication, QDialog, QVBoxLayout, QHBoxLayout, 
                               QWidget, QFileDialog, QMessageBox, QProgressDialog, QLineEdit, QLabel,
                               QInputDialog, QComboBox, QGroupBox, QTabWidget, QTextEdit, QPushButton)
from PySide6.QtGui import QDoubleValidator, QTextOption
from PySide6.QtCore import Qt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import matplotlib.pyplot as plt
from StyledDropdown import StyledDropdown, StyledInputBox
from StyledButton import StyledButton 
from SeismicDatabaseManager import SeismicDatabaseManager



class SEGYQCWidget(QWidget):
    def __init__(self, seismic_data, parent=None):
        super().__init__(parent)
        self.seismic_data = seismic_data  # Pre-processed seismic data

        # Main layout
        main_layout = QVBoxLayout(self)

        # Create tabs for different QC views
        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)

        # Add tabs
        self.add_header_info_tab()
        self.add_trace_geometry_tab()
        self.add_statistical_tab()

    def add_header_info_tab(self):
        """Display basic SEG-Y file header information from processed data"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Create text area for header info
        header_text = QTextEdit()
        header_text.setReadOnly(True)

        # Collect header information
        info_lines = [
            f"Number of Traces: {self.seismic_data['trace_data'].shape[0]}",
            f"Number of Samples per Trace: {self.seismic_data['trace_data'].shape[1]}",
            f"Sample Rate: {self.seismic_data.get('sample_rate', 'Unknown')} sec",
            f"Inline Min: {int(np.min(self.seismic_data['inlines'])) if 'inlines' in self.seismic_data else 'N/A'}",
            f"Inline Max: {int(np.max(self.seismic_data['inlines'])) if 'inlines' in self.seismic_data else 'N/A'}",
            f"Crossline Min: {int(np.min(self.seismic_data['crosslines'])) if 'crosslines' in self.seismic_data else 'N/A'}",
            f"Crossline Max: {int(np.max(self.seismic_data['crosslines'])) if 'crosslines' in self.seismic_data else 'N/A'}",
            f"Bounding Box: X [{self.seismic_data['x_coords'].min()} to {self.seismic_data['x_coords'].max()}], "
            f"Y [{self.seismic_data['y_coords'].min()} to {self.seismic_data['y_coords'].max()}]",
        ]

        header_text.setText("\n".join(info_lines))
        layout.addWidget(header_text)

        self.tab_widget.addTab(tab, "File Header")

    def add_trace_geometry_tab(self):
        """Create a tab showing trace geometry visualization from processed data"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        try:
            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 5))

            # Extract inline and crossline numbers
            inlines = self.seismic_data.get('inlines', [])
            crosslines = self.seismic_data.get('crosslines', [])

            if len(inlines) > 0 and len(crosslines) > 0:
                ax1.scatter(inlines, crosslines, alpha=0.5)
                ax1.set_title('Inline vs Crossline')
                ax1.set_xlabel('Inline')
                ax1.set_ylabel('Crossline')

                ax2.hist2d(inlines, crosslines, bins=50, cmap='viridis')
                ax2.set_title('Inline-Crossline Distribution')
                ax2.set_xlabel('Inline')
                ax2.set_ylabel('Crossline')
            else:
                ax1.text(0.5, 0.5, "No trace geometry data available",
                         horizontalalignment='center', verticalalignment='center')

            plt.tight_layout()
            canvas = FigureCanvas(fig)
            layout.addWidget(canvas)

        except Exception as e:
            layout.addWidget(QLabel(f"Error visualizing trace geometry: {str(e)}"))

        self.tab_widget.addTab(tab, "Trace Geometry")

    def add_statistical_tab(self):
        """Create a tab showing statistical analysis of traces"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        try:
            traces = self.seismic_data['trace_data']
            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 5))

            # Trace amplitude distribution
            ax1.hist(traces.flatten(), bins=50, density=True)
            ax1.set_title('Trace Amplitude Distribution')
            ax1.set_xlabel('Amplitude')
            ax1.set_ylabel('Density')

            # Trace energy plot
            trace_energy = np.sum(traces**2, axis=1)
            ax2.plot(trace_energy)
            ax2.set_title('Trace Energy')
            ax2.set_xlabel('Trace Number')
            ax2.set_ylabel('Energy')

            plt.tight_layout()
            canvas = FigureCanvas(fig)
            layout.addWidget(canvas)

            # Text area for statistical summary
            stats_text = QTextEdit()
            stats_text.setReadOnly(True)

            stats_lines = [
                f"Total Traces: {traces.shape[0]}",
                f"Samples per Trace: {traces.shape[1]}",
                f"Mean Amplitude: {np.mean(traces):.4f}",
                f"Std Deviation: {np.std(traces):.4f}",
                f"Min Amplitude: {np.min(traces):.4f}",
                f"Max Amplitude: {np.max(traces):.4f}"
            ]

            stats_text.setText("\n".join(stats_lines))
            layout.addWidget(stats_text)

        except Exception as e:
            layout.addWidget(QLabel(f"Error performing statistical analysis: {str(e)}"))

        self.tab_widget.addTab(tab, "Trace Statistics")


class SEGYViewer(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.figure, self.ax = plt.subplots()
        self.canvas = FigureCanvas(self.figure)
        layout = QVBoxLayout(self)
        layout.addWidget(self.canvas)

    def plot_segy_slice(self, trace_data, time_axis, slice_index=0, title_suffix=None):
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

        title = f"Slice {slice_index}: First {num_traces_to_plot} traces"
        if title_suffix:
            title = f"{title} - {title_suffix}"

        self.ax.set_title(title)
        self.ax.set_xlabel("Trace Number")
        self.ax.set_ylabel("Time (ms)")
        self.figure.colorbar(im, ax=self.ax, label="Amplitude")
        self.canvas.draw()


class DataLoadSegy(QDialog):
    def __init__(self, parent=None, db_path=None):
        super().__init__(parent)
        self.setWindowTitle("SEG-Y Loader")
        self.setGeometry(100, 100, 800, 700)
        self.segy_files = []  # List of SEGY files to process
        self.seismic_data = None
        self.bounding_box = None
        self.kdtree = None
        self.db_path = db_path
        self.sample_rate = None
        self.qc_widget = None
        
        # Mode selection flags
        self.mode = "new_volume"  # Options: "new_volume", "add_attribute"

        # Create the database manager if we have a path
        if self.db_path:
            self.seismic_db = SeismicDatabaseManager(self.db_path)
            # Create tables if they don't exist
            self.seismic_db.create_tables()
        else:
            self.seismic_db = None
        
        self.setupUi()
  
    def setupUi(self):
        # Define labels for alignment
        labels = ["Mode:", "Seismic Volume:", "Name", "SEG-Y Format:", "Seismic Datum:"]
        StyledDropdown.calculate_label_width(labels)
    
        # Main layout
        main_layout = QVBoxLayout(self)
    
        # Helper functions for creating consistent UI components
        def create_dropdown(label, items=None, parent=None):
            dropdown = StyledDropdown(label, parent=parent or self)
            if items:
                dropdown.setItems(items)
            return dropdown
    
        def create_input(label, default_value="", validator=None):
            input_box = StyledInputBox(label, default_value, validator=validator)
            input_box.label.setFixedWidth(StyledDropdown.label_width)
            return input_box
    
        # Load button layout - moved to the very top
        load_button_layout = QHBoxLayout()
        self.load_button = StyledButton("Select SEG-Y File(s)", "function")
        self.load_button.clicked.connect(self.select_segy_files)
        load_button_layout.addWidget(self.load_button)
    
        # Label to show selected files
        self.files_label = QLabel("No files selected")
        load_button_layout.addWidget(self.files_label)
    
        load_button_layout.addStretch()
        main_layout.addLayout(load_button_layout)
    
        # Mode selection
        self.mode_dropdown = create_dropdown("Mode:", ["New Volume", "New Attribute"])
        self.mode_dropdown.combo.currentTextChanged.connect(self.on_mode_changed)
        main_layout.addWidget(self.mode_dropdown)
    
        # Existing Project selection (for Add Attribute mode)
        self.project_group = QGroupBox("Select Existing Seismic Volume")
        project_layout = QHBoxLayout()
        self.project_dropdown = create_dropdown("Seismic Volume:")
        self.populate_seismic_dropdown()  # Load volumes initially
        project_layout.addWidget(self.project_dropdown)
        self.project_group.setLayout(project_layout)
        self.project_group.setVisible(False)  # Hidden by default
        main_layout.addWidget(self.project_group)
    
        # Format dropdown
        self.format_dropdown = create_dropdown("SEG-Y Format:", ["SEG-Y Native Format", "SeisWare"])
        main_layout.addWidget(self.format_dropdown)
    
        # Name input after format
        self.name_input = create_input("Name", "Enter seismic data name")
        main_layout.addWidget(self.name_input)
    
        # Datum input box
        double_validator = QDoubleValidator()
        double_validator.setBottom(0.0)  # No negative values
        self.datum_input = create_input("Seismic Datum:", "2000", validator=double_validator)
        main_layout.addWidget(self.datum_input)

        self.vertical_unit_dropdown = create_dropdown("Vertical Unit:", ["Meters", "Feet"])
        main_layout.addWidget(self.vertical_unit_dropdown)

        self.process_button = StyledButton("Process First File", "function")
        self.process_button.clicked.connect(self.process_first_file)
        self.process_button.setEnabled(False)  # Disabled until files are selected
        main_layout.addWidget(self.process_button)

        max_width = max(self.load_button.sizeHint().width(), 
        self.process_button.sizeHint().width())
        self.load_button.setFixedWidth(max_width)
        self.process_button.setFixedWidth(max_width)

        # **✅ Add Statistics Display (Middle Section)**
        self.statistics_group = QGroupBox("Processed SEG-Y Statistics")
        stats_layout = QVBoxLayout()

        # **Add Statistics Display (Expands to Fill Remaining Space)**
        self.statistics_group = QGroupBox("Processed SEG-Y Statistics")
        self.qc_layout = QVBoxLayout()  # Layout for QC content
        self.statistics_group.setLayout(self.qc_layout)

        # ✅ Make the statistics section expand
        main_layout.addWidget(self.statistics_group, 1)  # 👈 Adding "stretch factor" to make it expand

        # Bottom buttons (Save & Close)
        bottom_layout = QHBoxLayout()
        bottom_layout.addStretch()
    
        self.save_button = StyledButton("Save", "save")
        self.save_button.clicked.connect(self.save_data)
        self.save_button.setEnabled(False)  # Disable until data is loaded
        bottom_layout.addWidget(self.save_button)
    
        self.close_button = StyledButton("Close", "close")
        self.close_button.clicked.connect(self.close)
        bottom_layout.addWidget(self.close_button)
    
        main_layout.addLayout(bottom_layout)
    
    def on_mode_changed(self, mode_text):
        """Handle mode change"""
        if mode_text == "New Volume":
            self.mode = "new_volume"
            self.project_group.setVisible(False)
            self.name_input.setEnabled(True)
    
        elif mode_text == "New Attribute":
            self.mode = "add_attribute"
            self.project_group.setVisible(True)
            # Disable name field (use project name)
            self.name_input.setEnabled(False)
    
            # Make sure project dropdown is populated
            self.populate_seismic_dropdown()
            
            # If no projects, show warning
            if self.project_dropdown.combo.count() == 0 or self.project_dropdown.currentText() == "No seismic volumes found":
                QMessageBox.warning(self, "Warning", "No existing projects found in database. Please create a new volume first.")
                self.mode_dropdown.setCurrentText("New Volume")

    def populate_seismic_dropdown(self):
        """Populate the dropdown with seismic volumes from the database"""
        if not self.seismic_db:
            return
        
        # Create a list of volume names
        items = []
    
        try:
            # Get all seismic files
            all_files = self.seismic_db.get_all_seismic_files(include_attributes=False)
        
            for file_info in all_files:
                # Add seismic volume name to items list
                items.append(file_info['name'])
                
            if not items:
                items = ["No seismic volumes found"]
            
            # Set items to the dropdown
            self.project_dropdown.setItems(items)
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to retrieve seismic volumes: {str(e)}")
    
    def select_segy_files(self):
        """Select one or more SEG-Y files"""
        file_paths, _ = QFileDialog.getOpenFileNames(
            self, "Select SEGY File(s)", "", "SEGY Files (*.segy *.sgy)"
        )
        if not file_paths:
            return
    
        self.segy_files = file_paths
    
        # Display number of selected files
        if len(file_paths) == 1:
            self.files_label.setText(f"1 file selected: {os.path.basename(file_paths[0])}")
        else:
            self.files_label.setText(f"{len(file_paths)} files selected")
    
        # Auto-fill name if in new_volume mode and name field is empty or has default text
        if self.mode == "new_volume":
            current_name = self.name_input.text()
            if current_name == "Enter seismic data name" or current_name.strip() == "":
                basename = os.path.basename(file_paths[0])
                # Extract the part before the first dot
                volume_name = basename.split('.')[0]
                self.name_input.setText(volume_name)
    
        # Enable the process button now that files are selected
        self.process_button.setEnabled(True)

    def process_first_file(self):
        """Process the first selected file and update the QC display."""
        if not self.segy_files:
            QMessageBox.warning(self, "Warning", "No files selected.")
            return

        # Process the first file using the existing method
        traces_processed = self.process_segy_file(self.segy_files[0])

        if traces_processed > 0:
            # Remove existing QC widget if one exists
            if self.qc_widget:
                self.qc_widget.setParent(None)
                self.qc_widget.deleteLater()

            # Create a new QC widget with updated data
            self.qc_widget = SEGYQCWidget(self.seismic_data)

            # Add the widget to the QC layout
            self.qc_layout.addWidget(self.qc_widget)

            # Enable save button
            self.save_button.setEnabled(True)

        else:
            QMessageBox.warning(self, "Error", "Could not process the SEG-Y file.")



    def get_default_attribute_name(self, file_path):
        """Extract attribute name from SeisWare file if possible, otherwise use basename"""
        basename = os.path.basename(file_path)
    
        # For SeisWare format (SeismicName.AttributeName.version.segy)
        if self.format_dropdown.currentText() == "SeisWare":
            parts = basename.split('.')
            # If we have at least 3 parts (SeismicName.AttributeName.version.segy)
            if len(parts) >= 3:
                # Return the attribute name part
                return parts[1]
    
        # Default to filename without extension for non-SeisWare or unrecognized format
        return os.path.splitext(basename)[0]


    def process_segy_file(self, file_path):
        """Process a SEG-Y file"""
        segy_format = self.format_dropdown.currentText()
    
        # Get datum from the input box
        try:
            datum = float(self.datum_input.text()) if self.datum_input.text().strip() else 2000.0  # Default to 2000 if empty
        except ValueError:
            # Handle invalid input
            QMessageBox.warning(self, "Warning", "Invalid datum value. Using default value of 2000.")
            datum = 2000.0

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
                
                    # Set up progress dialog
                    progress = QProgressDialog("Processing SEG-Y file...", "Cancel", 0, 100, self)
                    progress.setWindowModality(Qt.WindowModal)
                    progress.show()
                
                    trace_size = 240 + num_samples * 4  # Header + data
                    total_traces = (file_size - 3600) // trace_size
                
                    traces_processed = 0
                    while f.tell() < file_size:
                        try:
                            # Update progress every 100 traces
                            if traces_processed % 100 == 0:
                                progress_value = min(99, int(100 * traces_processed / total_traces))
                                progress.setValue(progress_value)
                                if progress.wasCanceled():
                                    break
                        
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
                        
                            traces_processed += 1

                        except Exception as e:
                            print(f"Unexpected error processing trace: {e}")
                            break

                    # Convert lists to numpy arrays
                    trace_data = np.array(trace_data)
                    inlines = np.array(inlines)
                    crosslines = np.array(crosslines)
                    x_coords = np.array(x_coords)
                    y_coords = np.array(y_coords)
                
                    progress.close()

            else:  # Native SEG-Y format
                with segyio.open(file_path, "r", ignore_geometry=True) as segyfile:
                    total_traces = segyfile.tracecount
                    if total_traces == 0:
                        raise Exception("The SEGY file contains no traces.")

                    # Set up progress dialog
                    progress = QProgressDialog("Processing SEG-Y file...", "Cancel", 0, 100, self)
                    progress.setWindowModality(Qt.WindowModal)
                    progress.show()

                    # Load all traces into memory
                    trace_data = np.zeros((total_traces, segyfile.samples.size))
                    inlines = np.zeros(total_traces)
                    crosslines = np.zeros(total_traces)
                    x_coords = np.zeros(total_traces)
                    y_coords = np.zeros(total_traces)
                    time_axis = segyfile.samples

                    print("Reading headers for all traces:")

                    with open(file_path, "rb") as f:
                        # Read binary header first to get sample interval
                        f.seek(3200)  # Move to binary header
                        bin_header = f.read(400)
                        sample_interval = struct.unpack(">H", bin_header[16:18])[0]
                        num_samples = struct.unpack(">H", bin_header[20:22])[0]
                        data_format = struct.unpack(">H", bin_header[24:26])[0]

                        # Convert sample interval to seconds
                        self.sample_rate = sample_interval / 1000.0  # Convert milliseconds to seconds

                        print(f"Global Sample Interval: {sample_interval} ms")
                        print(f"Number of Samples: {num_samples}")
                        print(f"Data Format: {data_format}")

                        time_axis = np.arange(0, num_samples * sample_interval / 1000, sample_interval / 1000)

                        for i in range(total_traces):
                            # Update progress
                            if i % 100 == 0:
                                progress_value = min(99, int(100 * i / total_traces))
                                progress.setValue(progress_value)
                                if progress.wasCanceled():
                                    break
                            
                            trace_data[i, :] = segyfile.trace[i]  # Read trace data

                            # Move to the trace header of the current trace
                            header_offset = 3600 + i * (240 + segyfile.samples.size * 4)  # 3600 = textual + binary headers
                            f.seek(header_offset)

                            # Read the 240-byte trace header
                            trace_header = f.read(240)

                            # Extract inline and crossline using segyio (for convenience)
                            header = segyfile.header[i]
                            inlines[i] = header[segyio.TraceField.INLINE_3D]
                            crosslines[i] = header[segyio.TraceField.CROSSLINE_3D]

                            # Manually extract X and Y from byte 181 and byte 185 (4-byte integers)
                            x_bytes = struct.unpack(">i", trace_header[180:184])[0]  # 181st byte
                            y_bytes = struct.unpack(">i", trace_header[184:188])[0]  # 185th byte

                            x_coords[i] = x_bytes
                            y_coords[i] = y_bytes

                    progress.close()

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

            # Store seismic data
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
            title_suffix = None
            if self.mode == "add_attribute":
                title_suffix = f"Attribute: {os.path.basename(file_path)}"
            
            self.open_segy_viewer(self.seismic_data, title_suffix)

            # Build KD-tree for all modes
            if self.seismic_data and self.bounding_box:
                self.build_kdtree()

            return len(trace_data) if "trace_data" in self.seismic_data and self.seismic_data["trace_data"] is not None else 0

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to process SEG-Y file: {str(e)}")
            return 0

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


            
    

    def save_data(self):
        """Save data based on current mode"""
        if not self.seismic_data or not self.bounding_box or not self.segy_files:
            QMessageBox.warning(self, "Warning", "No data to save.")
            return

        try:
            # Set up progress dialog
            progress = QProgressDialog("Processing seismic data...", "Cancel", 0, 100, self)
            progress.setWindowModality(Qt.WindowModal)
            progress.show()

            # Variables to store project info
            project_id = None
            hdf5_path = None
        
            if self.mode == "new_volume":
                # Get name for new volume
                name = self.name_input.text()
                if not name or name == "Enter seismic data name":
                    QMessageBox.warning(self, "Warning", "Please enter a name for the seismic data.")
                    progress.close()
                    return
            
                # Create HDF5 path based on the name input

            
                if self.db_path:
                    project_dir = os.path.dirname(self.db_path)
                else:
                    project_dir = os.path.dirname(self.segy_files[0])

                hdf5_path = os.path.join(project_dir, f"{name}.h5")

                # Check if file already exists
                if os.path.exists(hdf5_path):
                    response = QMessageBox.question(
                        self, "File Exists", 
                        f"HDF5 file '{os.path.basename(hdf5_path)}' already exists. Replace it?",
                        QMessageBox.Yes | QMessageBox.No
                    )
                    if response == QMessageBox.No:
                        progress.close()
                        return
            
                # Step 1: Create HDF5 file structure from first SEGY file
                progress.setValue(10)
                progress.setLabelText("Creating HDF5 file structure...")
            
                # Get datum from input box
                try:
                    datum_value = float(self.datum_input.text()) if self.datum_input.text().strip() else 2000.0
                except ValueError:
                    datum_value = 2000.0
            
                with h5py.File(hdf5_path, 'w') as f:
                    # Store metadata
                    f.attrs['format'] = self.format_dropdown.currentText()
                    f.attrs['datum'] = datum_value
                    f.attrs['sample_rate'] = self.sample_rate
                    f.attrs['vertical_unit'] = self.vertical_unit_dropdown.combo.currentText()  # Add this line
                    f.attrs['creation_date'] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    f.attrs['attribute_names'] = ""
                    f.attrs['num_attributes'] = 0
    
                
                    # Create geometry group and store geometry data
                    geometry_group = f.create_group('geometry')
                    for key in ['x_coords', 'y_coords', 'inlines', 'crosslines', 'time_axis']:
                        if key in self.seismic_data:
                            geometry_group.create_dataset(
                                key,
                                data=self.seismic_data[key],
                                compression='gzip',
                                compression_opts=4,
                                chunks=True
                            )
                
                    # Store KD-tree
                    if self.kdtree is not None:
                        kdtree_group = geometry_group.create_group('kdtree')
                        kdtree_group.create_dataset('data', data=self.kdtree.data)
                        kdtree_group.attrs['leafsize'] = self.kdtree.leafsize
                
                    # Store bounding box
                    if self.bounding_box:
                        bbox_group = geometry_group.create_group('bounding_box')
                        for key, value in self.bounding_box.items():
                            bbox_group.attrs[key] = value
                
                    # Create attributes group
                    f.create_group('attributes')
            
                # Step 2: Save to database - create new entry
                progress.setValue(20)
                progress.setLabelText("Saving to database...")
            
                # Create file info dictionary - no original_segy_path
                file_info = {
                    'name': name,
                    'hdf5_path': hdf5_path,
                    'format': self.format_dropdown.currentText(),
                    'datum': datum_value,
                    'sample_rate': self.sample_rate,
                    'num_samples': len(self.seismic_data['time_axis']),
                    'vertical_unit': self.vertical_unit_dropdown.combo.currentText(),  # Add this line
                    'attribute_names': [],
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
                        'inline_min': int(np.min(self.seismic_data['inlines'])),
                        'inline_max': int(np.max(self.seismic_data['inlines'])),
                        'xline_min': int(np.min(self.seismic_data['crosslines'])),
                        'xline_max': int(np.max(self.seismic_data['crosslines']))
                    })
            
                # Save to database and get project ID
                if self.seismic_db:
                    project_id = self.seismic_db.save_seismic_file(file_info)
                    if not project_id:
                        QMessageBox.critical(self, "Error", "Failed to save project information to database.")
                        progress.close()
                        return
            
            else:  # add_attribute mode
                # Get project name
                project_name = self.project_dropdown.currentText()
                if project_name == "No seismic volumes found":
                    QMessageBox.warning(self, "Warning", "No project selected.")
                    progress.close()
                    return
            
                # Get project info from database
                project_info = self.seismic_db.get_seismic_file_info(name=project_name)
                if not project_info:
                    QMessageBox.warning(self, "Warning", f"Could not find project '{project_name}' in database.")
                    progress.close()
                    return
            
                # Get project ID and HDF5 path
                project_id = project_info.get('id')
                hdf5_path = project_info.get('hdf5_path')
            
                # Check if HDF5 file exists
                if not hdf5_path or not os.path.exists(hdf5_path):
                    QMessageBox.warning(self, "Warning", "HDF5 file not found for the selected project.")
                    progress.close()
                    return
        
            # Step 3: Process all SEGY files and add them as attributes
            # The rest of the code is identical for both modes
            progress.setValue(30)
            progress.setLabelText("Processing attributes...")
        
            # Track attribute names
            attr_names = []
        
            # Process each SEGY file
            total_files = len(self.segy_files)
            for i, segy_file in enumerate(self.segy_files):
                # Update progress
                progress_value = 30 + int((i * 60) / total_files)
                progress.setValue(progress_value)
                progress.setLabelText(f"Processing file {i+1} of {total_files}: {os.path.basename(segy_file)}")
            
                # Get default attribute name (parse SeisWare format if applicable)
                default_name = self.get_default_attribute_name(segy_file)
            
                # Always ask for attribute name (even for first file)
                attr_name, ok = QInputDialog.getText(
                    self, "Attribute Name", 
                    f"Enter name for attribute from {os.path.basename(segy_file)}:",
                    text=default_name
                )
            
                if not ok:
                    continue  # Skip this file if user cancels
            
                # Use default if empty
                if not attr_name:
                    attr_name = default_name
            
                # If not the first file or not in new_volume mode, process the SEGY file
                saved_data = None
                if i > 0 or self.mode == "add_attribute":
                    # Save current data
                    saved_data = self.seismic_data.copy()
                
                    # Process new file
                    self.process_segy_file(segy_file)
                
                    # Verify geometry matches HDF5 file
                    if not self.verify_geometry_with_hdf5(hdf5_path):
                        QMessageBox.warning(
                            self, "Warning", 
                            f"File '{os.path.basename(segy_file)}' geometry doesn't match. Skipping."
                        )
                    
                        # Restore previous data
                        self.seismic_data = saved_data
                        continue
            
                # Add attribute to HDF5 file
                with h5py.File(hdf5_path, 'r+') as f:
                    attributes_group = f['attributes']
                
                    # Check if attribute already exists
                    if attr_name in attributes_group:
                        # Ask if user wants to replace
                        response = QMessageBox.question(
                            self, "Attribute Exists", 
                            f"Attribute '{attr_name}' already exists. Replace it?",
                            QMessageBox.Yes | QMessageBox.No
                        )
                    
                        if response == QMessageBox.No:
                            # Skip this file if user cancels
                            if saved_data:
                                self.seismic_data = saved_data
                            continue
                    
                        # Delete existing attribute
                        del attributes_group[attr_name]
                
                    # Create attribute group
                    attr_group = attributes_group.create_group(attr_name)
                
                    # Store trace data
                    attr_group.create_dataset(
                        'trace_data',
                        data=self.seismic_data['trace_data'],
                        compression='gzip',
                        compression_opts=4,
                        chunks=True
                    )
                
                    # Store original file path
                    attr_group.attrs['original_file'] = segy_file
                
                    # Add to attribute names
                    attr_names.append(attr_name)
                
                    # Update HDF5 metadata
                    f.attrs['attribute_names'] = ",".join(attr_names)
                    f.attrs['num_attributes'] = len(attr_names)
            
                # Save attribute info to database
                if project_id and self.seismic_db:
                    self.seismic_db.save_attribute_info(project_id, attr_name, segy_file)
            
                # Restore data if needed
                if saved_data:
                    self.seismic_data = saved_data
        
            # Step 4: Update database with final attribute list
            if project_id and self.seismic_db:
                progress.setValue(95)
                progress.setLabelText("Updating database...")
            
                update_info = {
                    'id': project_id,
                    'attribute_names': attr_names
                }
            
                self.seismic_db.update_seismic_file(update_info)
        
            # Complete
            progress.setValue(100)
            progress.setLabelText("Save completed!")
            progress.close()
        
            # Reset UI
            self.reset_ui_after_save()
        
            # Show success message
            if self.mode == "new_volume":
                QMessageBox.information(self, "Success", "Volume created successfully with attributes.")
            else:
                QMessageBox.information(self, "Success", "Attributes added successfully.")
        
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save data: {str(e)}")
            if 'progress' in locals():
                progress.close()
           
    def verify_geometry_with_hdf5(self, hdf5_path):
        """Verify that current data geometry matches the HDF5 file"""
        if not self.seismic_data:
            return False
            
        try:
            with h5py.File(hdf5_path, 'r') as f:
                geometry = f.get('geometry')
                if geometry is None:
                    return False
                    
                # Compare number of traces
                hdf5_coords = geometry.get('x_coords')
                if hdf5_coords is None or len(hdf5_coords) != len(self.seismic_data['x_coords']):
                    return False
                    
                # Compare number of samples
                hdf5_time = geometry.get('time_axis')
                if hdf5_time is None or len(hdf5_time) != len(self.seismic_data['time_axis']):
                    return False
                    
                # Sample a subset of coordinates for comparison
                sample_size = min(100, len(hdf5_coords))
                sample_indices = np.linspace(0, len(hdf5_coords)-1, sample_size, dtype=int)
                
                x_diff = np.max(np.abs(hdf5_coords[sample_indices] - self.seismic_data['x_coords'][sample_indices]))
                
                hdf5_y_coords = geometry.get('y_coords')
                y_diff = np.max(np.abs(hdf5_y_coords[sample_indices] - self.seismic_data['y_coords'][sample_indices]))
                
                tolerance = 1.0  # Tolerance for coordinate differences
                
                return x_diff <= tolerance and y_diff <= tolerance
                
        except Exception as e:
            print(f"Error verifying geometry: {e}")
            return False
            
    def open_segy_viewer(self, seismic_data, title_suffix=None):
        """Open SEGYViewer in a new window"""
        self.viewer_window = QDialog(self)
        self.viewer_window.setWindowTitle("SEGY Viewer")
        self.viewer_window.setGeometry(150, 150, 900, 600)

        layout = QVBoxLayout(self.viewer_window)
        self.viewer = SEGYViewer()  # Create a new SEGYViewer instance
        layout.addWidget(self.viewer)

        # Plot the SEG-Y data in the new viewer
        self.viewer.plot_segy_slice(
            seismic_data["trace_data"], 
            seismic_data["time_axis"], 
            slice_index=0, 
            title_suffix=title_suffix
        )

        self.viewer_window.exec()  # Show as a new modal dialog

            
    def reset_ui_after_save(self):
        """Reset UI state after successful save"""
        # Reset data
        self.seismic_data = None
        self.bounding_box = None
        self.kdtree = None
        self.segy_files = []
        
        # Reset UI elements
        self.name_input.setText("Enter seismic data name")
        self.files_label.setText("No files selected")
        
        # Refresh project dropdown if in add_attribute mode
        if self.mode == "add_attribute":
            self.populate_seismic_dropdown()
        
        # Disable save button
        self.save_button.setEnabled(False)
        
        # Clear viewer



if __name__ == "__main__":
    app = QApplication(sys.argv)
    dialog = DataLoadSegy()
    result = dialog.exec()
    sys.exit(app.exec())

