from PySide2.QtWidgets import QApplication, QDialog, QFileDialog, QVBoxLayout, QLabel, QPushButton, QMessageBox, QLineEdit
import segyio
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import struct
import os


class DataLoadSegy(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("SEGY Viewer")
        self.setGeometry(200, 100, 1000, 800)

        self.layout = QVBoxLayout(self)
        self.file_label = QLabel("No SEGY file selected.")
        self.layout.addWidget(self.file_label)

        # Add a LineEdit for the datum input
        self.datum_label = QLabel("Enter seismic datum (default 2000):")
        self.layout.addWidget(self.datum_label)
        self.datum_input = QLineEdit()
        self.datum_input.setText("2000")  # Set a default value of 2000
        self.layout.addWidget(self.datum_input)

        self.load_button = QPushButton("Select SEGY File")
        self.load_button.clicked.connect(self.load_segy_file)
        self.layout.addWidget(self.load_button)

        self.view_button = QPushButton("View SEGY Sample")
        self.view_button.clicked.connect(self.view_segy_sample)
        self.view_button.setEnabled(False)
        self.layout.addWidget(self.view_button)

        self.ok_button = QPushButton("OK")
        self.ok_button.clicked.connect(self.confirm_and_return_data)
        self.ok_button.setEnabled(False)
        self.layout.addWidget(self.ok_button)

        self.figure = plt.figure()
        self.canvas = FigureCanvas(self.figure)
        self.layout.addWidget(self.canvas)

        self.segy_file = None
        self.trace_data = None
        self.inlines = None
        self.crosslines = None
        self.x_coords = None
        self.y_coords = None
        self.time_axis = None
        self.bounding_box = None

    def load_segy_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select SEGY File", "", "SEGY Files (*.segy *.sgy)")
        if file_path:
            self.file_label.setText(file_path)
            self.segy_file = file_path
            self.view_button.setEnabled(True)

    def view_segy_sample(self):
        try:
            if not self.segy_file:
                raise Exception("No SEGY file selected.")

            with segyio.open(self.segy_file, "r", ignore_geometry=True) as segyfile:
                total_traces = segyfile.tracecount
                if total_traces == 0:
                    raise Exception("The SEGY file contains no traces.")

                # Load all traces into memory
                self.trace_data = np.zeros((total_traces, segyfile.samples.size))
                self.inlines = np.zeros(total_traces)
                self.crosslines = np.zeros(total_traces)
                self.x_coords = np.zeros(total_traces)
                self.y_coords = np.zeros(total_traces)

                # Manually read headers from the SEGY file to get X and Y values from specific byte positions
                print("Reading headers for all traces:")

                with open(self.segy_file, "rb") as f:
                    for i in range(total_traces):
                        self.trace_data[i, :] = segyfile.trace[i]  # Read trace data

                        # Move to the trace header of the current trace
                        header_offset = 3600 + i * (240 + segyfile.samples.size * 4)  # 3600 = textual + binary headers
                        f.seek(header_offset)

                        # Read the 240-byte trace header
                        trace_header = f.read(240)

                        # Extract inline and crossline using segyio (for convenience)
                        header = segyfile.header[i]
                        self.inlines[i] = header[segyio.TraceField.INLINE_3D]
                        self.crosslines[i] = header[segyio.TraceField.CROSSLINE_3D]

                        # Manually extract X and Y from byte 181 and byte 185 (4-byte integers)
                        x_bytes = struct.unpack(">i", trace_header[180:184])[0]  # 181st byte
                        y_bytes = struct.unpack(">i", trace_header[184:188])[0]  # 185th byte

                        self.x_coords[i] = x_bytes
                        self.y_coords[i] = y_bytes

                        print(f"Trace {i}: Inline={self.inlines[i]}, Crossline={self.crosslines[i]}, X={self.x_coords[i]}, Y={self.y_coords[i]}")

                self.time_axis = segyfile.samples

                # Apply datum shift to the time axis
                self.apply_datum_shift()

                self.bounding_box = self.calculate_bounding_box()

                # Only plot the first 100 traces
                num_traces_to_plot = min(100, total_traces)
                self.figure.clear()
                ax = self.figure.add_subplot(111)

                # Plot the first 100 traces as a seismic image
                im = ax.imshow(self.trace_data[:num_traces_to_plot, :].T, cmap='seismic', aspect='auto',
                               extent=[0, num_traces_to_plot, self.time_axis[-1], self.time_axis[0]])

                ax.set_title(f"First {num_traces_to_plot} SEGY Traces (Seismic Image)")
                ax.set_xlabel("Trace Number")
                ax.set_ylabel("Time (ms)")
                plt.colorbar(im, ax=ax, label="Amplitude")
                self.canvas.draw()

                self.ok_button.setEnabled(True)

        except Exception as e:
            QMessageBox.warning(self, "Error", f"An error occurred: {str(e)}")
            print(f"Exception occurred: {str(e)}")

    def apply_datum_shift(self):
        try:
            # Get the datum value from the input field
            datum_value = float(self.datum_input.text())

            # Shift the time axis to start from the datum value and decrease
            self.time_axis = datum_value - self.time_axis

            print(f"Time axis after datum shift: {self.time_axis}")
        except ValueError:
            QMessageBox.warning(self, "Error", "Invalid datum value. Please enter a valid number.")

    def confirm_and_return_data(self):
        if self.trace_data is None:
            QMessageBox.warning(self, "Error", "No seismic data loaded.")
        else:
            print("Returning seismic data and bounding box...")
            self.accept()

    def calculate_bounding_box(self):
        min_x = np.min(self.x_coords)
        max_x = np.max(self.x_coords)
        min_y = np.min(self.y_coords)
        max_y = np.max(self.y_coords)
        return {"min_x": min_x, "max_x": max_x, "min_y": min_y, "max_y": max_y}

    def get_seismic_data(self):
        return {
            "trace_data": self.trace_data,
            "inlines": self.inlines,
            "crosslines": self.crosslines,
            "x_coords": self.x_coords,
            "y_coords": self.y_coords,
            "time_axis": self.time_axis
        }

    def get_bounding_box(self):
        return self.bounding_box


if __name__ == "__main__":
    app = QApplication([])
    dialog = DataLoadSegy()
    if dialog.exec_() == QDialog.Accepted:
        seismic_data = dialog.get_seismic_data()
        bounding_box = dialog.get_bounding_box()

        print("Seismic data shape (traces x samples):", seismic_data["trace_data"].shape)
        print("Bounding Box:", bounding_box)

    app.exec_()
