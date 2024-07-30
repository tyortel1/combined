import sys
import pandas as pd
from PySide2.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QColorDialog, QApplication, QDialogButtonBox
from PySide2.QtGui import QColor
from PySide2.QtCore import Qt, Signal
from functools import partial

class ColorEditor(QDialog):
    color_changed = Signal(pd.DataFrame)

    def __init__(self, zone_color_df, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Color Editor")
        self.zone_color_df = zone_color_df.copy()
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()
        self.color_labels = {}

        for index, row in self.zone_color_df.iterrows():
            color = QColor(*row['Zone Color (RGB)'])
            label = QLabel(f"Zone {index}")
            label.setStyleSheet(f"background-color: {color.name()}; color: white; padding: 5px;")
            button = QPushButton("Change Color")
            button.clicked.connect(partial(self.change_color, index))
            h_layout = QHBoxLayout()
            h_layout.addWidget(label)
            h_layout.addWidget(button)
            layout.addLayout(h_layout)
            self.color_labels[index] = label

        # Add OK and Cancel buttons
        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)

        self.setLayout(layout)
        self.setMinimumSize(300, 400)

    def change_color(self, index):
        current_color = QColor(*self.zone_color_df.loc[index, 'Zone Color (RGB)'])
        color = QColorDialog.getColor(current_color, self, f"Select Color for Zone {index}")

        if color.isValid():
            self.zone_color_df.at[index, 'Zone Color (RGB)'] = (color.red(), color.green(), color.blue())
            self.color_labels[index].setStyleSheet(f"background-color: {color.name()}; color: white; padding: 5px;")
            print(f"Changed color for Zone {index} to {color.name()}")

    def accept(self):
        self.color_changed.emit(self.zone_color_df)
        super().accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    # Example DataFrame for testing
    data = {
        'Zone Color (RGB)': [(255, 0, 0), (0, 255, 0), (0, 0, 255)]
    }
    df = pd.DataFrame(data)
    editor = ColorEditor(df)
    editor.color_changed.connect(lambda updated_df: print(updated_df))
    editor.exec_()
    sys.exit(app.exec_())
