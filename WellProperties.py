from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTableView, QPushButton, QStyledItemDelegate,
    QComboBox, QMenu, QToolBar
)
from PySide6.QtGui import QStandardItemModel, QStandardItem, QIcon, QAction
from PySide6.QtCore import QSortFilterProxyModel, Qt
import pandas as pd


class StatusDelegate(QStyledItemDelegate):
    def createEditor(self, parent, option, index):
        """Create a combo box editor for the 'Status' column."""
        combo_box = QComboBox(parent)
        combo_box.addItems(["Planned", "Active"])
        return combo_box

    def setEditorData(self, editor, index):
        """Set the current value of the combo box."""
        value = index.model().data(index, Qt.DisplayRole)
        editor.setCurrentText(value)

    def setModelData(self, editor, model, index):
        """Set the selected value back to the model."""
        value = editor.currentText()
        model.setData(index, value)


class WellPropertiesDialog(QDialog):
    def __init__(self, well_data_df, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Well Properties")
        self.setMinimumSize(800, 500)

        self.well_data_df = well_data_df.copy()

        # Ensure required columns exist
        if "status" not in self.well_data_df.columns:
            self.well_data_df["status"] = "Planned"
        if "spud_date" not in self.well_data_df.columns:
            self.well_data_df["spud_date"] = None

        # Reorder columns to place 'spud_date' after 'status'
        columns = self.well_data_df.columns.tolist()
        if "status" in columns and "spud_date" in columns:
            status_index = columns.index("status")
            columns.remove("spud_date")
            columns.insert(status_index + 1, "spud_date")
            self.well_data_df = self.well_data_df[columns]

        # Layout
        main_layout = QVBoxLayout(self)

        # Toolbar with icons
        toolbar = QToolBar(self)
        set_active_action = QAction(QIcon("icons/oil_on.png"), "Set Active", self)
        set_planned_action = QAction(QIcon("icons/oil_off.png"), "Set Planned", self)

        set_active_action.triggered.connect(lambda: self.set_status_for_selected("Active"))
        set_planned_action.triggered.connect(lambda: self.set_status_for_selected("Planned"))

        toolbar.addAction(set_active_action)
        toolbar.addAction(set_planned_action)
        main_layout.addWidget(toolbar)

        # Table view
        self.table_view = QTableView(self)
        self.model = QStandardItemModel(self)
        self.populate_model()

        # Use a proxy model to enable sorting
        self.proxy_model = QSortFilterProxyModel(self)
        self.proxy_model.setSourceModel(self.model)
        self.proxy_model.setSortCaseSensitivity(Qt.CaseInsensitive)

        self.table_view.setModel(self.proxy_model)
        self.table_view.setSortingEnabled(True)
        self.table_view.setSelectionBehavior(QTableView.SelectRows)
        self.table_view.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table_view.customContextMenuRequested.connect(self.show_context_menu)

        main_layout.addWidget(self.table_view)

        # Save button
        self.save_button = QPushButton("Save")
        self.save_button.setFixedWidth(150)  # 1.5 inches approximately
        self.save_button.clicked.connect(self.accept)  # Close the dialog

        button_layout = QHBoxLayout()
        button_layout.addStretch()  # Push the save button to the right
        button_layout.addWidget(self.save_button)
        main_layout.addLayout(button_layout)

    def populate_model(self):
        """Populate the table model with data from well_data_df."""
        self.model.setHorizontalHeaderLabels(self.well_data_df.columns.tolist())

        for _, row in self.well_data_df.iterrows():
            items = [QStandardItem(str(cell) if pd.notnull(cell) else "") for cell in row]
            self.model.appendRow(items)

    def show_context_menu(self, position):
        """Show context menu for setting status."""
        menu = QMenu(self)
        set_planned_action = QAction("Set to Planned", self)
        set_active_action = QAction("Set to Active", self)

        set_planned_action.triggered.connect(lambda: self.set_status_for_selected("Planned"))
        set_active_action.triggered.connect(lambda: self.set_status_for_selected("Active"))

        menu.addAction(set_planned_action)
        menu.addAction(set_active_action)
        menu.exec_(self.table_view.viewport().mapToGlobal(position))

    def set_status_for_selected(self, status):
        """Set the 'Status' column for all selected rows to the specified status."""
        selected_rows = self.table_view.selectionModel().selectedRows()
        status_column_index = self.well_data_df.columns.get_loc("status")

        for index in selected_rows:
            model_index = self.proxy_model.mapToSource(index)
            self.model.setData(self.model.index(model_index.row(), status_column_index), status)

    def get_updated_data(self):
        """Extract the updated data from the table model."""
        updated_data = []
        for row in range(self.model.rowCount()):
            row_data = [
                self.model.item(row, col).text()
                for col in range(self.model.columnCount())
            ]
            updated_data.append(row_data)

        return pd.DataFrame(updated_data, columns=self.well_data_df.columns)
