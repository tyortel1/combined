import sys
import pandas as pd
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QSlider, QApplication, QDialogButtonBox, QGridLayout, QLineEdit
)
from PySide6.QtGui import QColor
from PySide6.QtCore import Qt, Signal
from functools import partial

class ColorEditor(QDialog):
    color_changed = Signal(pd.DataFrame)

    def __init__(self, grid_color_df, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Color Editor")
        self.grid_color_df = grid_color_df.copy()
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()
        self.color_labels = {}

        for index, row in self.grid_color_df.iterrows():
            if row['Type'] != 'Depth':
                continue
            color = QColor(*row['Color (RGB)'])
            label = QLabel(f"Grid {row['Grid']}")
            label.setStyleSheet(f"background-color: rgb{tuple(row['Color (RGB)']):}; color: white; padding: 5px;")
            button = QPushButton("Change Color")
            button.clicked.connect(partial(self.open_color_dialog, index))
            h_layout = QHBoxLayout()
            h_layout.addWidget(label)
            h_layout.addWidget(button)
            layout.addLayout(h_layout)
            self.color_labels[index] = label

        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)

        self.setLayout(layout)
        self.setMinimumSize(300, 400)

    def open_color_dialog(self, index):
        current_color = QColor(*self.grid_color_df.loc[index, 'Color (RGB)'])
        color_dialog = CustomColorDialog(current_color, self)
        color_dialog.color_selected.connect(lambda color: self.update_color(index, color))
        color_dialog.exec_()

    def update_color(self, index, color):
        rgb = (color.red(), color.green(), color.blue())
        self.grid_color_df.at[index, 'Color (RGB)'] = rgb
        self.color_labels[index].setStyleSheet(f"background-color: rgb{rgb}; color: white; padding: 5px;")
        print(f"Changed color for Grid {self.grid_color_df.loc[index, 'Grid']} to rgb{rgb}")

    def accept(self):
        self.color_changed.emit(self.grid_color_df)
        super().accept()


class CustomColorDialog(QDialog):
    color_selected = Signal(QColor)

    def __init__(self, initial_color, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select Color")
        self.initial_color = initial_color
        self.color = initial_color
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()

        color_palette_label = QLabel("Basic colors:")
        layout.addWidget(color_palette_label)

        self.color_display = QLabel()
        self.color_display.setFixedHeight(50)
        self.update_color_display()
        layout.addWidget(self.color_display)

        self.create_color_grid(layout)

        self.sliders = {
            'Red': QSlider(Qt.Horizontal),
            'Green': QSlider(Qt.Horizontal),
            'Blue': QSlider(Qt.Horizontal)
        }

        self.value_labels = {
            'Red': QLineEdit(),
            'Green': QLineEdit(),
            'Blue': QLineEdit()
        }

        for color, slider in self.sliders.items():
            slider.setRange(0, 255)
            slider.setValue(getattr(self.initial_color, color.lower())())
            slider.valueChanged.connect(self.update_color)
            slider_layout = QHBoxLayout()
            value_label = self.value_labels[color]
            value_label.setFixedWidth(40)
            value_label.setReadOnly(True)
            value_label.setText(str(slider.value()))
            slider_layout.addWidget(QLabel(f"Pick a {color}"))
            slider_layout.addWidget(value_label)
            slider_layout.addWidget(slider)
            layout.addLayout(slider_layout)

        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)

        self.setLayout(layout)
        self.setMinimumSize(400, 300)

    def create_color_grid(self, layout):
        color_palette = [
            # Red shades
            [(255, 204, 204), (255, 153, 153), (255, 102, 102), (255, 51, 51), (255, 0, 0), (204, 0, 0), (153, 0, 0), (102, 0, 0), (51, 0, 0)],
            # Orange shades
            [(255, 229, 204), (255, 204, 153), (255, 178, 102), (255, 153, 51), (255, 128, 0), (204, 102, 0), (153, 76, 0), (102, 51, 0), (51, 25, 0)],
            # Yellow shades
            [(255, 255, 204), (255, 255, 153), (255, 255, 102), (255, 255, 51), (255, 255, 0), (204, 204, 0), (153, 153, 0), (102, 102, 0), (51, 51, 0)],
            # Light green shades
            [(229, 255, 204), (204, 255, 153), (178, 255, 102), (153, 255, 51), (128, 255, 0), (102, 204, 0), (76, 153, 0), (51, 102, 0), (25, 51, 0)],
            # Green shades
            [(204, 255, 204), (153, 255, 153), (102, 255, 102), (51, 255, 51), (0, 255, 0), (0, 204, 0), (0, 153, 0), (0, 102, 0), (0, 51, 0)],
            # Cyan-green shades
            [(204, 255, 229), (153, 255, 204), (102, 255, 178), (51, 255, 153), (0, 255, 128), (0, 204, 102), (0, 153, 76), (0, 102, 51), (0, 51, 25)],
                        # Cyan shades
            [(204, 255, 255), (153, 255, 255), (102, 255, 255), (51, 255, 255), (0, 255, 255), (0, 204, 204), (0, 153, 153), (0, 102, 102), (0, 51, 51)],
            # Light blue shades
            [(204, 229, 255), (153, 204, 255), (102, 178, 255), (51, 153, 255), (0, 128, 255), (0, 102, 204), (0, 76, 153), (0, 51, 102), (0, 25, 51)],
            # Blue shades
            [(204, 204, 255), (153, 153, 255), (102, 102, 255), (51, 51, 255), (0, 0, 255), (0, 0, 204), (0, 0, 153), (0, 0, 102), (0, 0, 51)],
            # Purple shades
            [(229, 204, 255), (204, 153, 255), (178, 102, 255), (153, 51, 255), (128, 0, 255), (102, 0, 204), (76, 0, 153), (51, 0, 102), (25, 0, 51)],
            # Magenta shades
            [(255, 204, 255), (255, 153, 255), (255, 102, 255), (255, 51, 255), (255, 0, 255), (204, 0, 204), (153, 0, 153), (102, 0, 102), (51, 0, 51)],
            # Pink shades
            [(255, 204, 229), (255, 153, 204), (255, 102, 178), (255, 51, 153), (255, 0, 128), (204, 0, 102), (153, 0, 76), (102, 0, 51), (51, 0, 25)],
            # Gray shades
            [(255, 255, 255), (224, 224, 224), (192, 192, 192), (160, 160, 160), (128, 128, 128), (96, 96, 96), (64, 64, 64), (32, 32, 32), (0, 0, 0)],
            # Color column
            [(255, 0, 0), (255, 128, 0), (255, 255, 0), (128, 255, 0), (0, 255, 0), (0, 255, 128), (0, 255, 255), (0, 128, 255), (0, 0, 255)]
        ]

        grid_layout = QGridLayout()
        for col, column in enumerate(color_palette):
            for row, rgb in enumerate(column):
                color_button = QPushButton()
                color_button.setStyleSheet(f"background-color: rgb{rgb}; border: 1px solid black;")
                color_button.setFixedSize(20, 20)
                color_button.clicked.connect(partial(self.select_color, rgb))  # Pass rgb directly
                grid_layout.addWidget(color_button, row, col)

        layout.addLayout(grid_layout)

    def select_color(self, rgb):
        print(f"Selected color: rgb{rgb}")
        self.color = QColor(*rgb)
        self.update_color_display()
        self.update_sliders()
        self.color_selected.emit(self.color)

    def update_color_display(self):
        rgb = (self.color.red(), self.color.green(), self.color.blue())
        self.color_display.setStyleSheet(f"background-color: rgb{rgb}; border: 1px solid black;")
        self.color_display.setText(f"RGB: {rgb}")

    def update_sliders(self):
        for slider in self.sliders.values():
            slider.blockSignals(True)
    
        self.sliders['Red'].setValue(self.color.red())
        self.sliders['Green'].setValue(self.color.green())
        self.sliders['Blue'].setValue(self.color.blue())
    
        for slider in self.sliders.values():
            slider.blockSignals(False)
    
        self.update_value_labels()

    def update_value_labels(self):
        self.value_labels['Red'].setText(str(self.color.red()))
        self.value_labels['Green'].setText(str(self.color.green()))
        self.value_labels['Blue'].setText(str(self.color.blue()))

    def update_color(self):
        self.color.setRed(self.sliders['Red'].value())
        self.color.setGreen(self.sliders['Green'].value())
        self.color.setBlue(self.sliders['Blue'].value())
        self.update_color_display()
        self.update_value_labels()

    def accept(self):
        self.color_selected.emit(self.color)
        super().accept()

# You might want to add a main function to test the dialog:
def main():
    app = QApplication(sys.argv)
    # Create a sample DataFrame
    df = pd.DataFrame({
        'Grid': ['Grid1', 'Grid2', 'Grid3'],
        'Type': ['Depth', 'Depth', 'Depth'],
        'Color (RGB)': [(255, 0, 0), (0, 255, 0), (0, 0, 255)]
    })
    editor = ColorEditor(df)
    editor.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
