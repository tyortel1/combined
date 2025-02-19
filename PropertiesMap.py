from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QCheckBox, QSpinBox, 
    QSlider, QPushButton
)
from PySide6.QtCore import Qt


class MapPropertiesDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Properties")
        self.setMinimumWidth(300)

        layout = QVBoxLayout(self)

        # Checkbox: Show UWI Labels
        self.UWICheckbox = QCheckBox("Show UWI Labels")
        layout.addWidget(self.UWICheckbox)

        # Checkbox: Show Ticks
        self.ticksCheckbox = QCheckBox("Show Ticks")
        layout.addWidget(self.ticksCheckbox)

        # Checkbox: Show Drainage
        self.gradientCheckbox = QCheckBox("Show Drainage")

        # Gradient size spinbox
        self.gradientSizeSpinBox = QSpinBox()
        self.gradientSizeSpinBox.setMinimum(1)
        self.gradientSizeSpinBox.setMaximum(1000)
        self.gradientSizeSpinBox.setSingleStep(10)

        # Gradient layout (Checkbox + Spinbox)
        gradientLayout = QHBoxLayout()
        gradientLayout.addWidget(self.gradientCheckbox)
        gradientLayout.addWidget(QLabel("Size:"))
        gradientLayout.addWidget(self.gradientSizeSpinBox)
        layout.addLayout(gradientLayout)

        # UWI Size slider
        self.UWIWidthSlider = QSlider(Qt.Horizontal)
        self.UWIWidthSlider.setMinimum(1)
        self.UWIWidthSlider.setMaximum(100)
        layout.addWidget(QLabel("UWI Size:"))
        layout.addWidget(self.UWIWidthSlider)

        # UWI Label Opacity slider
        self.opacitySlider = QSlider(Qt.Horizontal)
        self.opacitySlider.setMinimum(0)
        self.opacitySlider.setMaximum(100)
        layout.addWidget(QLabel("UWI Label Opacity:"))
        layout.addWidget(self.opacitySlider)

        # Line Width slider
        self.lineWidthSlider = QSlider(Qt.Horizontal)
        self.lineWidthSlider.setMinimum(1)
        self.lineWidthSlider.setMaximum(200)
        layout.addWidget(QLabel("Line Width:"))
        layout.addWidget(self.lineWidthSlider)

        # Line Opacity slider
        self.lineOpacitySlider = QSlider(Qt.Horizontal)
        self.lineOpacitySlider.setMinimum(0)
        self.lineOpacitySlider.setMaximum(100)
        layout.addWidget(QLabel("Line Opacity:"))
        layout.addWidget(self.lineOpacitySlider)

        # Apply & Cancel buttons
        buttonLayout = QHBoxLayout()
        self.applyButton = QPushButton("Apply")
        self.cancelButton = QPushButton("Cancel")
        buttonLayout.addWidget(self.applyButton)
        buttonLayout.addWidget(self.cancelButton)
        layout.addLayout(buttonLayout)

        # Connect buttons
        self.cancelButton.clicked.connect(self.reject)
        self.applyButton.clicked.connect(self.accept)
