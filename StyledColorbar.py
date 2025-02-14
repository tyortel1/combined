from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PySide6.QtGui import QPixmap, QPainter, QLinearGradient, QBrush, QColor
from PySide6.QtCore import Qt
from StyledDropdown import StyledDropdown
import os
import pandas as pd

#   Import StyledDropdown

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QHBoxLayout
from PySide6.QtGui import QPixmap, QPainter, QLinearGradient, QBrush, QColor, QPen
from PySide6.QtCore import Qt

class StyledColorBar(QWidget):
    def __init__(self, items=None, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Dropdown for selecting color bars
        self.colorbar_dropdown = StyledDropdown("SColor Bar", items, self)
        self.colorbar_dropdown.combo.currentIndexChanged.connect(self.color_selected)

        # Create a horizontal layout for color bar and labels
        color_bar_layout = QHBoxLayout()

        # Min value label
        self.min_value_label = QLabel()
        self.min_value_label.setFixedWidth(60)
        self.min_value_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        # Display widget for the color gradient
        self.color_display = QLabel(self)
        self.color_display.setFixedSize(200, 30)  # Set a fixed size for visibility
        self.color_display.setStyleSheet("background: white; border: 1px solid #999;")

        # Max value label
        self.max_value_label = QLabel()
        self.max_value_label.setFixedWidth(60)
        self.max_value_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        # Add widgets to horizontal layout
        color_bar_layout.addWidget(self.min_value_label)
        color_bar_layout.addWidget(self.color_display)
        color_bar_layout.addWidget(self.max_value_label)

        # Add dropdown and color bar layout to main layout
        layout.addWidget(self.colorbar_dropdown)
        layout.addLayout(color_bar_layout)
        layout.addStretch()

        # Initialize selected_color_palette
        self.selected_color_palette = self.load_color_palette("Rainbow")

 
    def color_selected(self):
        """Triggered when a color bar is selected."""
        selected_palette_name = self.colorbar_dropdown.currentText().strip()

        if not selected_palette_name:  # Check if empty
            print("Error: No color palette selected.")
            return
    
        print(f"📂 Loading Palette: {selected_palette_name}")  # Debug print
        self.selected_color_palette = self.load_color_palette(selected_palette_name)
    
        # Attempt to display color range if min and max values are available
        # You might need to adjust this part based on how min and max are tracked in your application
        if hasattr(self, 'min_value') and hasattr(self, 'max_value'):
            self.display_color_range(self.min_value, self.max_value)


    def currentText(self):
        return self.colorbar_dropdown.currentText()

    def setCurrentText(self, text):
        self.colorbar_dropdown.setCurrentText(text)

    def map_value_to_color(self, value, min_value, max_value, color_palette):
        """Map a value to a color based on the min and max range."""
        if not color_palette:  #   Prevents accessing an empty list
            return QColor(0, 0, 0)  # Default black color if no palette is available

        if max_value == min_value:
            return color_palette[0] if color_palette else QColor(0, 0, 0)

        # Normalize value
        normalized_value = (value - min_value) / (max_value - min_value)

        #   Ensure `index` is within bounds
        index = int(normalized_value * (len(color_palette) - 1)) if not pd.isna(normalized_value) else 0
        index = max(0, min(index, len(color_palette) - 1))  #   Clamping within bounds

        return color_palette[index]


    def load_color_palette(self, palette_name):
        """Load a color palette from the Palettes directory."""
        color_palette = []
        file_path = os.path.join(os.path.dirname(__file__), 'Palettes', palette_name + ".pal")
        try:
            with open(file_path, 'r') as file:
                lines = file.readlines()
                start_index = 2  # Assuming the first two lines are metadata
                for line in lines[start_index:]:
                    if line.strip():  # Ignore empty lines
                        try:
                            r, g, b = map(int, line.strip().split())
                            color_palette.append(QColor(r, g, b))
                        except ValueError:
                            continue  # Skip invalid lines
        except FileNotFoundError:
            print(f"Error: The file '{file_path}' was not found.")
        except IOError:
            print(f"Error: An IOError occurred while trying to read '{file_path}'.")
        
        #   Update the stored color palette
        self.selected_color_palette = color_palette
        return color_palette

    def display_color_range(self, min_attr, max_attr):
        """Display the color range gradient with ticks."""
        if not self.selected_color_palette or min_attr is None or max_attr is None:
            print("Unable to display color range.")
            self.color_display.clear()
            self.min_value_label.clear()
            self.max_value_label.clear()
            return

        # Convert to float and format labels
        try:
            min_value = float(min_attr)
            max_value = float(max_attr)
        
            # Format labels with appropriate precision
            self.min_value_label.setText(f"{min_value:.2f}")
            self.max_value_label.setText(f"{max_value:.2f}")
        except ValueError:
            print("Could not convert min/max to float")
            return

        # Create color gradient pixmap
        pixmap = QPixmap(self.color_display.width(), self.color_display.height())
        pixmap.fill(Qt.white)
        painter = QPainter(pixmap)

        # Draw color gradient
        gradient = QLinearGradient(0, 0, self.color_display.width(), 0)
        for i, color in enumerate(self.selected_color_palette):
            gradient.setColorAt(i / (len(self.selected_color_palette) - 1), color)

        painter.setBrush(QBrush(gradient))
        painter.drawRect(0, 0, self.color_display.width(), self.color_display.height())

        # Add ticks
        painter.setPen(QPen(Qt.black, 2))  # Slightly thicker tick lines
        num_ticks = 5  # Number of ticks to display
        for i in range(num_ticks):
            # Calculate x position for each tick
            x = int(i * (self.color_display.width() / (num_ticks - 1)))
        
            # Draw tick line
            tick_height = 8  # Tick height in pixels
            painter.drawLine(
                x, 
                self.color_display.height(), 
                x, 
                self.color_display.height() - tick_height
            )

        painter.end()

        self.color_display.setPixmap(pixmap)

    def addColorBarOptions(self, options):
        """Add color bar options to the dropdown"""
        self.colorbar_dropdown.combo.clear()
        self.colorbar_dropdown.combo.addItems(options)

    def currentColorBar(self):
        """Get current selected color bar"""
        return self.colorbar_dropdown.combo.currentText()