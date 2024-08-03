from PySide2.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QListWidget, QPushButton, QListWidgetItem, QLabel, QSpacerItem, QSizePolicy, QAbstractItemView
from PySide2.QtGui import QIcon

class ColumnSelectionDialog(QDialog):
    def __init__(self, all_columns, selected_columns, parent=None):
        super(ColumnSelectionDialog, self).__init__(parent)
        self.setWindowTitle("Select Columns")
        self.resize(400, 300)

        self.all_columns = all_columns
        self.selected_columns = selected_columns

        self.layout = QVBoxLayout(self)

        self.label = QLabel("Move columns between the boxes to select which ones to display.")
        self.layout.addWidget(self.label)

        list_layout = QHBoxLayout()

        self.available_list = QListWidget(self)
        self.available_list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.selected_list = QListWidget(self)
        self.selected_list.setSelectionMode(QAbstractItemView.ExtendedSelection)

        for col in all_columns:
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
        self.ok_button = QPushButton("OK", self)
        self.ok_button.clicked.connect(self.accept)
        self.cancel_button = QPushButton("Cancel", self)
        self.cancel_button.clicked.connect(self.reject)
        buttons_layout.addWidget(self.ok_button)
        buttons_layout.addWidget(self.cancel_button)

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

    def move_all_left(self):
        while self.selected_list.count() > 0:
            item = self.selected_list.takeItem(0)
            self.available_list.addItem(item)

    def get_selected_columns(self):
        return [self.selected_list.item(i).text() for i in range(self.selected_list.count())]
