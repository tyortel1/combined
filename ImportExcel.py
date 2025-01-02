from PyQt5.QtWidgets import (QApplication, QDialog, QLabel, QPushButton, QVBoxLayout, QHBoxLayout, QComboBox, 
                             QFileDialog, QWidget, QTableWidget, QTableWidgetItem, QSizePolicy, QSpacerItem)
import pandas as pd
from PyQt5.QtWidgets import QMessageBox


import sys

class ImportExcelDialog(QDialog):
    def __init__(self):
        super().__init__()
        
        self.setWindowTitle("Import Data - SeisWare Connect")
        self.setGeometry(100, 100, 800, 600)
        self.df = None
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()
        self.columnSelectors = {}
        self.production_data = []# Keep track of the column selection dropdowns

        # For selecting the specific columns
        self.columnMappingLayout = QHBoxLayout()
        layout.addLayout(self.columnMappingLayout)
        # File selection button and label
        self.btnSelectFile = QPushButton("Select File")
        self.btnSelectFile.clicked.connect(self.selectFile)
        layout.addWidget(self.btnSelectFile)

        self.lblFilePath = QLabel("No file selected")
        layout.addWidget(self.lblFilePath)

        # Table for file preview
        self.tablePreview = QTableWidget()
        self.tablePreview.setRowCount(5)  # Set to how many rows you want to preview
        self.tablePreview.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout.addWidget(self.tablePreview)

        # Button layout for "Okay" button
        buttonLayout = QHBoxLayout()
        spacer = QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)
        buttonLayout.addItem(spacer)  # Pushes the button to the right

        self.btnOkay = QPushButton("Okay")
        self.btnOkay.clicked.connect(self.onOkayClicked)
        buttonLayout.addWidget(self.btnOkay)

        layout.addLayout(buttonLayout)
        self.setLayout(layout)

    def selectFile(self):
        options = QFileDialog.Options()
        filePath, _ = QFileDialog.getOpenFileName(self, "Select File", "", "Excel Files (*.xlsx);;CSV Files (*.csv)", options=options)
        if filePath:
            self.lblFilePath.setText(filePath)
            self.loadDataForPreview(filePath)

    def loadDataForPreview(self, filePath):
        try:
            if filePath.endswith('.xlsx'):
                self.df = pd.read_excel(filePath, engine='openpyxl')  # Change here
            elif filePath.endswith('.csv'):
                self.df = pd.read_csv(filePath)  # Change here
            else:
                QMessageBox.warning(self, "Unsupported File", "Please select a valid Excel or CSV file.")
                return
            preview_df = self.df.head(5)  # Use self.df here for preview
            self.populatePreviewTable(preview_df)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to load file: {e}")
            self.df = None  # Ensure df is set to None if loading fails


    def populatePreviewTable(self, df):
        self.tablePreview.setColumnCount(len(df.columns))
        self.tablePreview.setHorizontalHeaderLabels(df.columns)
        for row in range(df.shape[0]):
            for col in range(df.shape[1]):
                self.tablePreview.setItem(row, col, QTableWidgetItem(str(df.iat[row, col])))
        self.tablePreview.resizeColumnsToContents()

     # Clear existing column selectors
        for i in reversed(range(self.columnMappingLayout.count())):
            widget = self.columnMappingLayout.itemAt(i).widget()
            if widget is not None:
                widget.setParent(None)

        # Assuming df is your DataFrame loaded from the selected file
        columns = df.columns.tolist()

        # Create a dropdown for each required field
        requiredFields = ["uwi", "Date", "Gas Volume", "Oil Volume"]
        for field in requiredFields:
            label = QLabel(f"{field}:")
            comboBox = QComboBox()
            comboBox.addItems(['Select Column'] + columns)  # Add a prompt item
            self.columnSelectors[field] = comboBox  # Store the comboBox to read selected value later
            self.columnMappingLayout.addWidget(label)
            self.columnMappingLayout.addWidget(comboBox)

    def onOkayClicked(self):
        # Ensure a DataFrame is loaded
        if not hasattr(self, 'df') or self.df is None:
            QMessageBox.warning(self, "No File Loaded", "Please load a file first.")
            return

        # Fetch column selections from the dropdowns
        selecteduwiColumn = self.columnSelectors["uwi"].currentText()
        selectedDateColumn = self.columnSelectors["Date"].currentText()
        selectedGasVolumeColumn = self.columnSelectors["Gas Volume"].currentText()
        selectedOilVolumeColumn = self.columnSelectors["Oil Volume"].currentText()

        ## Validate the column selections
        #if 'Select Column' in [selecteduwiColumn, selectedDateColumn]:
        #    QMessageBox.warning(self, "Selection Required", "Please select a column for uwi and Date fields.")
        #    return
        #if 'Select Column' in [selectedGasVolumeColumn, selectedOilVolumeColumn]:
        #    QMessageBox.warning(self, "Selection Required", "Please select at least one volume column (Gas or Oil).")
        #    return

        # Process the DataFrame using the selected columns
        try:
            self.production_data = []
            for _, row in self.df.iterrows():
                uwi = row[selecteduwiColumn]
                try:
                    # Convert and format the date column once
                    formatted_date = pd.to_datetime(row[selectedDateColumn]).strftime('%Y-%m-%d')
                except ValueError:
                    QMessageBox.warning(self, "Invalid Date", f"The date {row[selectedDateColumn]} is not in a recognizable format.")
                    return

                gas_volume = float(row[selectedGasVolumeColumn]) if selectedGasVolumeColumn != 'Select Column' else None
                oil_volume = float(row[selectedOilVolumeColumn]) if selectedOilVolumeColumn != 'Select Column' else None

                # Ensure at least one volume is provided
                if gas_volume is None and oil_volume is None:
                    QMessageBox.warning(self, "Volume Error", "Both Gas and Oil volumes cannot be empty. Please provide at least one.")
                    return

                self.production_data.append({
                    'uwi': uwi,
                    'date': formatted_date,
                    'gas_volume': gas_volume,
                    'oil_volume': oil_volume
                })
        except IndexError as e:
            QMessageBox.critical(self, "Error", "An error occurred: No entries found for selected uwi. Please check your selections and try again.")
            return
        except Exception as e:
            QMessageBox.critical(self, "Error Processing File", f"An unexpected error occurred: {str(e)}")
            return


        self.accept()
        return self.production_data


      

# Run the application
if __name__ == "__main__":
    app = QApplication(sys.argv)
    dialog = ImportExcelDialog()
    dialog.show()
    sys.exit(app.exec_())