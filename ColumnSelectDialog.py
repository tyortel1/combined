from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QListWidget, QPushButton, QListWidgetItem, QLabel, QSpacerItem, QSizePolicy, QAbstractItemView, QComboBox, QLineEdit, QMessageBox
from PySide6.QtGui import QIcon
from PySide6.QtCore import QSize

class ColumnSelectionDialog(QDialog):
    def __init__(self, all_columns, selected_columns, column_filters=None, current_config_name=None, parent=None):
        super(ColumnSelectionDialog, self).__init__(parent)
        self.setWindowTitle("Select Columns")
        self.resize(800, 600)

        self.all_columns = all_columns
        self.selected_columns = selected_columns
        self.column_filters = column_filters if column_filters is not None else {}
        self.current_config_name = current_config_name if current_config_name is not None else None
        self.layout = QVBoxLayout(self)

        self.label = QLabel("Move columns between the boxes to select which ones to display.")
        self.layout.addWidget(self.label)

        # Layout for Save and Load functionality
        save_layout = QVBoxLayout()

        # Label for Load Column Display
        self.load_column_display_label = QLabel("Load Column Display", self)
        self.layout.addWidget(self.load_column_display_label)

        # Dropdown to select saved configurations
        self.config_dropdown = QComboBox(self)
        self.config_dropdown.addItem("Select Saved Configuration")
        self.config_dropdown.addItems(self.column_filters.keys())
        self.config_dropdown.currentIndexChanged.connect(self.load_saved_configuration)
        self.layout.addWidget(self.config_dropdown)

        # Layout for entering a new configuration name
        self.save_name_label = QLabel("Column Displayed Name", self)
        save_layout.addWidget(self.save_name_label)

        # Input field for entering the configuration name
        self.save_name_input = QLineEdit(self)
        if self.current_config_name is not None:
            self.save_name_input.setText(self.current_config_name)
        else:
            self.save_name_input.setPlaceholderText("Enter configuration name to save")
        save_layout.addWidget(self.save_name_input)

        self.layout.addLayout(save_layout)

        list_layout = QHBoxLayout()

        self.available_list = QListWidget(self)
        self.available_list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.selected_list = QListWidget(self)
        self.selected_list.setSelectionMode(QAbstractItemView.ExtendedSelection)

        sorted_columns = sorted(all_columns)
        for col in sorted_columns:
            item = QListWidgetItem(col)
            if col in selected_columns:
                self.selected_list.addItem(item)
            else:
                self.available_list.addItem(item)

        list_layout.addWidget(self.available_list)

        arrow_layout = QVBoxLayout()
        arrow_layout.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding))

        self.move_all_right_button = QPushButton()
        self.move_all_right_button.setIcon(QIcon("icons/arrow_double_right.png"))
        self.move_all_right_button.clicked.connect(self.move_all_right)
        arrow_layout.addWidget(self.move_all_right_button)

        self.move_right_button = QPushButton()
        self.move_right_button.setIcon(QIcon("icons/arrow_right.ico"))
        self.move_right_button.clicked.connect(self.move_selected_right)
        arrow_layout.addWidget(self.move_right_button)

        self.move_left_button = QPushButton()
        self.move_left_button.setIcon(QIcon("icons/arrow_left.ico"))
        self.move_left_button.clicked.connect(self.move_selected_left)
        arrow_layout.addWidget(self.move_left_button)

        self.move_all_left_button = QPushButton()
        self.move_all_left_button.setIcon(QIcon("icons/arrow_double_left.png"))
        self.move_all_left_button.clicked.connect(self.move_all_left)
        arrow_layout.addWidget(self.move_all_left_button)

        arrow_layout.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding))

        list_layout.addLayout(arrow_layout)
        list_layout.addWidget(self.selected_list)

        self.layout.addLayout(list_layout)

        buttons_layout = QHBoxLayout()
        buttons_layout.addSpacerItem(QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))

        self.cancel_button = QPushButton("Cancel", self)
        self.cancel_button.setFixedSize(QSize(96, 32))  # 1 inch = 96 pixels at 96 DPI
        self.cancel_button.clicked.connect(self.reject)
        buttons_layout.addWidget(self.cancel_button)

        self.save_button = QPushButton("Save", self)
        self.save_button.setFixedSize(QSize(96, 32))  # 1 inch = 96 pixels at 96 DPI
        self.save_button.clicked.connect(self.save_current_configuration)
        buttons_layout.addWidget(self.save_button)

        self.layout.addLayout(buttons_layout)

    def move_all_right(self):
        while self.available_list.count() > 0:
            item = self.available_list.takeItem(0)
            self.selected_list.addItem(item)
   

    def move_selected_right(self):
        for item in self.available_list.selectedItems():
            self.selected_list.addItem(self.available_list.takeItem(self.available_list.row(item)))
   

    def move_selected_left(self):
        for item in self.selected_list.selectedItems():
            self.available_list.addItem(self.selected_list.takeItem(self.selected_list.row(item)))
        self.sort_list(self.available_list)

    def move_all_left(self):
        while self.selected_list.count() > 0:
            item = self.selected_list.takeItem(0)
            self.available_list.addItem(item)
        self.sort_list(self.available_list)

    def sort_list(self, list_widget):
        # Define the list of columns that should always be at the top
        priority_columns = [
            'UWI', 'Attribute Type', 'Zone Name', 'Zone Type', 
            'Top Depth', 'Base Depth', 'Top X Offset', 
            'Top Y Offset', 'Base X Offset', 'Base Y Offset'
        ]

        # Extract all items from the list widget
        items = [list_widget.item(i).text() for i in range(list_widget.count())]

        # Separate the priority items and the remaining items
        priority_items = [item for item in items if item in priority_columns]
        remaining_items = [item for item in items if item not in priority_columns]

        # Sort the remaining items alphabetically
        remaining_items.sort()

        # Combine the priority items (in the given order) with the sorted remaining items
        sorted_items = priority_items + remaining_items

        # Clear the list widget and re-add the items in the sorted order
        list_widget.clear()
        for item in sorted_items:
            list_widget.addItem(item)


    def get_selected_columns(self):
        return [self.selected_list.item(i).text() for i in range(self.selected_list.count())]

    def save_current_configuration(self):
        self.current_config_name = self.save_name_input.text().strip()

        if not self.current_config_name or self.current_config_name == "Select Saved Configuration":
            QMessageBox.warning(self, "Error", "Please enter a valid name to save the configuration. The name cannot be empty or 'Select Saved Configuration'.")
            return

        # Save the configuration
        self.column_filters[self.current_config_name] = self.get_selected_columns()

        # Update the dropdown if the name isn't already in the list
        if self.current_config_name not in [self.config_dropdown.itemText(i) for i in range(self.config_dropdown.count())]:
            self.config_dropdown.addItem(self.current_config_name)

        # Close the dialog after saving
        self.accept()

    def load_saved_configuration(self):
        config_name = self.config_dropdown.currentText()
        self.available_list.clear()
        self.selected_list.clear()

        if config_name and config_name != "Select Saved Configuration":
            saved_columns = self.column_filters.get(config_name, [])
        else:
            saved_columns = []

        for col in sorted(self.all_columns):
            item = QListWidgetItem(col)
            if col in saved_columns:
                self.selected_list.addItem(item)
            else:
                self.available_list.addItem(item)

        if config_name == "Select Saved Configuration":
            # Move all columns to the available list
            self.selected_list.clear()
            for col in sorted(self.all_columns):
                item = QListWidgetItem(col)
                self.available_list.addItem(item)
