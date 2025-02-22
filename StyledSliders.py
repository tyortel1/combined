from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSlider
from PySide6.QtCore import Qt
from superqt import QRangeSlider
from StyledDropdown import StyledBaseWidget

class StyledSlider(StyledBaseWidget):
    def __init__(self, label_text, orientation=Qt.Horizontal, parent=None):
        self.slider = QSlider(orientation)
        self.value_label = QLabel("0")  # Add value label
        
        # Create a container widget for slider and value
        container = QWidget()
        container_layout = QHBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.addWidget(self.slider)
        container_layout.addWidget(self.value_label)
        
        self.slider.setStyleSheet("""
            QSlider::groove:horizontal {
                border: 1px solid #bdc3c7;
                background: white;
                height: 10px;
                border-radius: 4px;
            }

            QSlider::sub-page:horizontal {
                background: #3498db;
                border: 1px solid #bdc3c7;
                height: 10px;
                border-radius: 4px;
            }

            QSlider::add-page:horizontal {
                background: white;
                border: 1px solid #bdc3c7;
                height: 10px;
                border-radius: 4px;
            }

            QSlider::handle:horizontal {
                background: white;
                border: 1px solid #bdc3c7;
                width: 18px;
                height: 18px;
                margin-top: -5px;
                margin-bottom: -5px;
                border-radius: 9px;
            }

            QSlider::handle:horizontal:hover {
                border: 1px solid #3498db;
            }
        """)
        
        super().__init__(label_text, container, parent)
        self.label.setFixedWidth(StyledBaseWidget.label_width)
        
        # Connect value change to update label
        self.slider.valueChanged.connect(self._update_value_label)

    def _update_value_label(self, value):
        self.value_label.setText(str(value))

    def setValue(self, value):
        self.slider.setValue(value)
        self._update_value_label(value)

    def value(self):
        return self.slider.value()

    def setRange(self, minimum, maximum):
        self.slider.setRange(minimum, maximum)

    def setMinimum(self, value):
        self.slider.setMinimum(value)

    def setMaximum(self, value):
        self.slider.setMaximum(value)

    def valueChanged(self):
        return self.slider.valueChanged()




class StyledRangeSlider(StyledBaseWidget):
    def __init__(self, label_text, orientation=Qt.Horizontal, parent=None):
        self.slider = QRangeSlider(orientation)
        
        # Create value labels
        self.min_label = QLabel("0")
        self.max_label = QLabel("100")
        
        # Create container widget
        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        
        # Add slider
        container_layout.addWidget(self.slider)
        
        # Add value labels in horizontal layout
        values_layout = QHBoxLayout()
        values_layout.addWidget(self.min_label)
        values_layout.addStretch()
        values_layout.addWidget(self.max_label)
        container_layout.addLayout(values_layout)
        
        self.slider.setStyleSheet("""
            QRangeSlider {
                border: none;
                padding: 0px;
            }
            
            QRangeSlider::groove:horizontal {
                border: 1px solid #bdc3c7;
                background: white;
                height: 10px;
                border-radius: 4px;
            }

            QRangeSlider::sub-page:horizontal {
                background: #3498db;
                border: 1px solid #bdc3c7;
                height: 10px;
                border-radius: 4px;
            }

            QRangeSlider::add-page:horizontal {
                background: white;
                border: 1px solid #bdc3c7;
                height: 10px;
                border-radius: 4px;
            }

            QRangeSlider::handle:horizontal {
                background: white;
                border: 1px solid #bdc3c7;
                width: 18px;
                height: 18px;
                margin-top: -5px;
                margin-bottom: -5px;
                border-radius: 9px;
            }

            QRangeSlider::handle:horizontal:hover {
                border: 1px solid #3498db;
            }
        """)
        
        super().__init__(label_text, container, parent)
        self.label.setFixedWidth(StyledBaseWidget.label_width)
        
        # Connect value change to update labels
        self.slider.valueChanged.connect(self._update_value_labels)

    def _update_value_labels(self, values):
        self.min_label.setText(f"{values[0]:.1f}")
        self.max_label.setText(f"{values[1]:.1f}")

    def setValue(self, values):
        self.slider.setValue(values)
        self._update_value_labels(values)

    def value(self):
        return self.slider.value()

    def setRange(self, minimum, maximum):
        self.slider.setMinimum(minimum)
        self.slider.setMaximum(maximum)
        self._update_value_labels(self.slider.value())

    def valueChanged(self):
        return self.slider.valueChanged()

    def rangeChanged(self):
        return self.slider.rangeChanged()



    @staticmethod
    def calculate_label_width(labels):
        StyledBaseWidget.calculate_label_width(labels)


if __name__ == "__main__":
    from PySide6.QtWidgets import QApplication
    import sys

    app = QApplication(sys.argv)

    labels = ["Well", "Zone", "Attribute", "Color Bar", "Range", "Heat"]
    StyledRangeSlider.calculate_label_width(labels)

    test_widget = QWidget()
    layout = QVBoxLayout(test_widget)

    slider = StyledSlider("Heat")
    slider.setRange(0, 100)
    slider.setValue(50)
    layout.addWidget(slider)

    range_slider = StyledRangeSlider("Range")
    range_slider.setRange(0, 100)
    range_slider.setValue([30, 70])
    layout.addWidget(range_slider)

    test_widget.show()
    sys.exit(app.exec())