import os
import sys
import pandas as pd
from PySide2.QtWidgets import QApplication, QDialog, QVBoxLayout, QTableView, QAbstractItemView, QHBoxLayout, QLabel, QComboBox, QToolBar, QAction, QSlider, QWidget, QFormLayout
from PySide2.QtCore import QSize, Qt
from PySide2.QtGui import QStandardItemModel, QStandardItem, QIcon, QFont
from ColumnSelectDialog import ColumnSelectionDialog

class ZoneViewerDialog(QDialog):



    def __init__(self, df, zone_names, selected_uwis, parent=None):
        super(ZoneViewerDialog, self).__init__(parent)
        self.setWindowTitle("Zone Viewer")
        self.resize(800, 600)

        # Set window flags to include the maximize button
        self.setWindowFlags(self.windowFlags() | Qt.WindowMaximizeButtonHint)

        self.df = df
        self.zone_names = zone_names
        self.selected_uwis = selected_uwis
        self.selected_columns = df.columns.tolist()  # Initially select all columns
        self.page_size = 1000  # Number of rows per page
        self.current_page = 0

        # Create main vertical layout
        self.main_vertical_layout = QVBoxLayout(self)
        self.setLayout(self.main_vertical_layout)

        # Create and set up the toolbar
        self.toolbar = QToolBar(self)
        self.main_vertical_layout.addWidget(self.toolbar)

        # Load icons
        icon_path = "icons"  # Folder where your icons are stored
        prev_icon = QIcon(os.path.join(icon_path, "arrow_left.ico"))
        next_icon = QIcon(os.path.join(icon_path, "arrow_right.ico"))
        filter_icon = QIcon(os.path.join(icon_path, "color_editor.ico"))

        # Create actions
        self.prev_action = QAction(prev_icon, "Previous", self)
        self.prev_action.triggered.connect(self.prev_page)
        self.next_action = QAction(next_icon, "Next", self)
        self.next_action.triggered.connect(self.next_page)
        self.filter_action = QAction(filter_icon, "Set Attribute Filter", self)
        self.filter_action.triggered.connect(self.open_column_selection_dialog)
        self.column_action = QAction("Select Columns", self)
        self.column_action.triggered.connect(self.open_column_selection_dialog)

        # Add actions to the toolbar
        self.toolbar.addAction(self.prev_action)
        self.toolbar.addAction(self.next_action)
        self.toolbar.addAction(self.filter_action)
        self.toolbar.addAction(self.column_action)

        # Create horizontal layout for filters and table
        self.main_layout = QHBoxLayout()
        self.main_vertical_layout.addLayout(self.main_layout)

        # Left widget for filters and column dimensions
        self.left_widget = QWidget()
        self.left_widget.setFixedWidth(200)
        self.left_layout = QVBoxLayout(self.left_widget)
        self.left_layout.setContentsMargins(10, 10, 10, 10)
        self.left_layout.setSpacing(5)
        self.main_layout.addWidget(self.left_widget)

        # Filter layout
        self.filter_layout = QVBoxLayout()
        self.filter_layout.setSpacing(5)

        # UWI Filter
        self.uwi_filter_label = QLabel("Filter by UWI")
        self.uwi_filter = QComboBox(self)
        self.uwi_filter.setFixedSize(QSize(180, 25))
        self.uwi_filter.addItem("All")
        self.uwi_filter.addItems(self.selected_uwis)
        self.uwi_filter.setCurrentText("All")  # Set initial value
        self.uwi_filter.currentTextChanged.connect(self.apply_filters)
        self.filter_layout.addWidget(self.uwi_filter_label)
        self.filter_layout.addWidget(self.uwi_filter)

        # Attribute Filter
        self.attribute_filter_label = QLabel("Filter by Attribute")
        self.attribute_filter = QComboBox(self)
        self.attribute_filter.setFixedSize(QSize(180, 25))
        self.attribute_filter.addItem("All")
        self.attribute_filter.addItems(["Well", "Zone"])
        self.attribute_filter.setCurrentText("All")  # Set initial value
        self.attribute_filter.currentTextChanged.connect(self.apply_filters)
        self.filter_layout.addWidget(self.attribute_filter_label)
        self.filter_layout.addWidget(self.attribute_filter)

        # Zone Name Filter
        self.zone_name_filter_label = QLabel("Filter by Zone Name")
        self.zone_name_filter = QComboBox(self)
        self.zone_name_filter.setFixedSize(QSize(180, 25))
        self.zone_name_filter.addItem("All")
        self.zone_name_filter.addItems(self.zone_names)
        self.zone_name_filter.setCurrentText("All")  # Set initial value
        self.zone_name_filter.currentTextChanged.connect(self.apply_filters)
        self.filter_layout.addWidget(self.zone_name_filter_label)
        self.filter_layout.addWidget(self.zone_name_filter)

        # Zone Type Filter
        self.zone_type_filter_label = QLabel("Filter by Zone Type")
        self.zone_type_filter = QComboBox(self)
        self.zone_type_filter.setFixedSize(QSize(180, 25))
        self.zone_type_filter.addItem("All")
        self.zone_type_filter.addItems(["Completions", "Tests", "Production", "Injection"])
        self.zone_type_filter.setCurrentText("All")  # Set initial value
        self.zone_type_filter.currentTextChanged.connect(self.apply_filters)
        self.filter_layout.addWidget(self.zone_type_filter_label)
        self.filter_layout.addWidget(self.zone_type_filter)

        self.left_layout.addLayout(self.filter_layout)

        # Add column width, height, and font size sliders
        self.dimensions_layout = QFormLayout()
        self.column_width_slider = QSlider(Qt.Horizontal)
        self.column_width_slider.setRange(20, 200)
        self.column_width_slider.setValue(100)
        self.column_width_slider.valueChanged.connect(self.apply_column_dimensions)
        
        self.row_height_slider = QSlider(Qt.Horizontal)
        self.row_height_slider.setRange(10, 50)
        self.row_height_slider.setValue(20)
        self.row_height_slider.valueChanged.connect(self.apply_column_dimensions)
        
        self.font_size_slider = QSlider(Qt.Horizontal)
        self.font_size_slider.setRange(3, 16)
        self.font_size_slider.setValue(8)
        self.font_size_slider.valueChanged.connect(self.apply_column_dimensions)
        
        self.dimensions_layout.addRow("Width", self.column_width_slider)
        self.dimensions_layout.addRow("Height", self.row_height_slider)
        self.dimensions_layout.addRow("Font", self.font_size_slider)
        self.left_layout.addLayout(self.dimensions_layout)

        # Add a stretch at the bottom to push everything up
        self.left_layout.addStretch()

        # Right layout for table view
        self.right_layout = QVBoxLayout()
        self.main_layout.addLayout(self.right_layout)

        self.table_view = QTableView(self)
        
        # Set a smaller font for the table view
        font = QFont()
        font.setPointSize(8)  # Adjust the font size as needed
        self.table_view.setFont(font)
        self.table_view.setSortingEnabled(True)
        
        self.right_layout.addWidget(self.table_view)

        self.pagination_layout = QHBoxLayout()
        self.page_label = QLabel(self)
        self.pagination_layout.addWidget(self.page_label)
        self.right_layout.addLayout(self.pagination_layout)

        self.filtered_df = self.df.copy()
        self.update_page_label()
        self.load_data()

    def apply_filters(self):
        uwi_filter_text = self.uwi_filter.currentText().strip().lower()
        attribute_filter_text = self.attribute_filter.currentText().strip().lower()
        zone_name_filter_text = self.zone_name_filter.currentText().strip().lower()
        zone_type_filter_text = self.zone_type_filter.currentText().strip().lower()

        # Initialize filter conditions
        uwi_filter_condition = pd.Series([True] * len(self.df), index=self.df.index)
        attribute_filter_condition = pd.Series([True] * len(self.df), index=self.df.index)
        zone_name_filter_condition = pd.Series([True] * len(self.df), index=self.df.index)
        zone_type_filter_condition = pd.Series([True] * len(self.df), index=self.df.index)

        # Apply UWI filter if not "All"
        if uwi_filter_text != "all":
            uwi_filter_condition = self.df['UWI'].astype(str).str.lower().str.contains(uwi_filter_text)

        # Apply Attribute filter if not "All"
        if attribute_filter_text != "all":
            attribute_filter_condition = self.df['Attribute Type'].astype(str).str.lower() == attribute_filter_text

        # Apply Zone Name filter if not "All"
        if zone_name_filter_text != "all":
            zone_name_filter_condition = self.df['Zone Name'].astype(str).str.lower() == zone_name_filter_text

        # Apply Zone Type filter if not "All"
        if zone_type_filter_text != "all":
            zone_type_filter_condition = self.df['Zone Type'].astype(str).str.lower() == zone_type_filter_text

        # Ensure all boolean series are aligned with the DataFrame's index
        uwi_filter_condition = uwi_filter_condition.reindex(self.df.index, fill_value=False)
        attribute_filter_condition = attribute_filter_condition.reindex(self.df.index, fill_value=False)
        zone_name_filter_condition = zone_name_filter_condition.reindex(self.df.index, fill_value=False)
        zone_type_filter_condition = zone_type_filter_condition.reindex(self.df.index, fill_value=False)

        # Apply all filter conditions to the DataFrame
        self.filtered_df = self.df[
            uwi_filter_condition &
            attribute_filter_condition &
            zone_name_filter_condition &
            zone_type_filter_condition
        ]

        self.current_page = 0
        self.update_page_label()
        self.load_data()

    def load_data(self):
        model = QStandardItemModel()

        # Filter columns based on selection
        filtered_df = self.filtered_df[self.selected_columns]

        # Set headers
        model.setHorizontalHeaderLabels(filtered_df.columns.tolist())

        # Calculate the start and end indices for the current page
        start_idx = self.current_page * self.page_size
        end_idx = min(start_idx + self.page_size, len(filtered_df))
        page_data = filtered_df.iloc[start_idx:end_idx]

        # Add rows
        for row in page_data.itertuples(index=False):
            items = [QStandardItem(str(field)) for field in row]
            model.appendRow(items)

        self.table_view.setModel(model)
        self.table_view.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table_view.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table_view.setEditTriggers(QAbstractItemView.NoEditTriggers)

    def update_page_label(self):
        total_pages = (len(self.filtered_df) + self.page_size - 1) // self.page_size
        self.page_label.setText(f"Page {self.current_page + 1} of {total_pages}")

    def next_page(self):
        if (self.current_page + 1) * self.page_size < len(self.filtered_df):
            self.current_page += 1
            self.update_page_label()
           
            self.load_data()

    def prev_page(self):
        if self.current_page > 0:
            self.current_page -= 1
            self.update_page_label()
            self.load_data()

    def open_filter_dialog(self):
        # Logic to open a dialog to set attribute filters
        pass

    def open_column_selection_dialog(self):
        dialog = ColumnSelectionDialog(self.df.columns.tolist(), self.selected_columns, self)
        if dialog.exec_() == QDialog.Accepted:
            self.selected_columns = dialog.get_selected_columns()
            self.load_data()
            print('okay')

    def apply_column_dimensions(self):
        column_width = self.column_width_slider.value()
        row_height = self.row_height_slider.value()
        font_size = self.font_size_slider.value()
        
        for column in range(self.table_view.model().columnCount()):
            self.table_view.setColumnWidth(column, column_width)
        self.table_view.verticalHeader().setDefaultSectionSize(row_height)
        
        # Set the font size for the table view
        font = QFont()
        font.setPointSize(font_size)
        self.table_view.setFont(font)

def main():
    app = QApplication(sys.argv)
    
    # Create a sample DataFrame
    data = {
        'UWI': ['001', '002', '003', '004', '005'],
        'Attribute Type': ['Well', 'Zone', 'Well', 'Zone', 'Well'],
        'Zone Name': ['Zone1', 'Zone2', 'Zone3', 'Zone4', 'Zone5'],
        'Zone Type': ['Completions', 'Tests', 'Production', 'Injection', 'Completions']
    }
    df = pd.DataFrame(data)
    zone_names = ['Zone1', 'Zone2', 'Zone3', 'Zone4', 'Zone5']
    selected_uwis = ['001', '002', '003', '004', '005']

    dialog = ZoneViewerDialog(df, zone_names, selected_uwis)
    dialog.show()

    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
