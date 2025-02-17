from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QHBoxLayout
from PySide6.QtGui import QPixmap, QPainter, QLinearGradient, QBrush, QColor, QPen
from PySide6.QtCore import Qt
import os
import pandas as pd
from StyledDropdown import StyledDropdown

class StyledColorBar(QWidget):
    def __init__(self, label_text="Color Bar", items=None, parent=None):
        super().__init__(parent)
        
        # Create main vertical layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        # Initialize selected color palette
        available_palettes = self.scan_palette_directory()
        palette_options = items if items is not None else available_palettes

        # Dropdown for color bar selection
        self.colorbar_dropdown = StyledDropdown(label_text, palette_options, self)

        # Create container for color bar
        colorbar_container = QWidget(self)
        colorbar_layout = QHBoxLayout(colorbar_container)
        colorbar_layout.setContentsMargins(StyledDropdown.label_width + 5, 0, 0, 0)
        colorbar_layout.setSpacing(0)

        # Color display (gradient box)
        self.color_display = QLabel(self)
        self.color_display.setFixedSize(200, 30)
        self.color_display.setStyleSheet("background: white; border: 1px solid #999;")
        colorbar_layout.addWidget(self.color_display)

        # Min and Max labels
        min_max_layout = QHBoxLayout()
        min_max_layout.setContentsMargins(StyledDropdown.label_width, 0, 0, 0)

        self.min_value_label = QLabel("", self)
        self.max_value_label = QLabel("", self)
        self.min_value_label.setAlignment(Qt.AlignLeft)
        self.max_value_label.setAlignment(Qt.AlignRight)

        min_max_layout.addWidget(self.min_value_label)
        min_max_layout.addStretch()
        min_max_layout.addWidget(self.max_value_label)

        # Add widgets to the main layout
        layout.addWidget(self.colorbar_dropdown)
        layout.addWidget(colorbar_container)
        layout.addLayout(min_max_layout)

        # Connect color selection
        self.colorbar_dropdown.combo.currentIndexChanged.connect(self.color_selected)
        
        # Initialize with first palette if available
        if palette_options:
            self.selected_color_palette = self.load_color_palette(palette_options[0])

    def scan_palette_directory(self):
        """Scan the Palettes directory for .pal files and return their names without extension."""
        palette_dir = os.path.join(os.path.dirname(__file__), 'Palettes')
        print(f"Looking for palettes in: {palette_dir}")  # Debug print
        
        palette_options = []
        try:
            if not os.path.exists(palette_dir):
                print(f"Warning: Palettes directory not found at {palette_dir}")
                return []
                
            files = os.listdir(palette_dir)
            print(f"Files found in directory: {files}")  # Debug print
            
            for file in files:
                if file.endswith('.pal'):
                    palette_name = os.path.splitext(file)[0]
                    palette_options.append(palette_name)
                    print(f"Added palette: {palette_name}")  # Debug print
                    
            return sorted(palette_options)
        except Exception as e:
            print(f"Error scanning palette directory: {e}")
            return []

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
        
        self.selected_color_palette = color_palette
        return color_palette

    def color_selected(self):
        """Triggered when a color bar is selected."""
        selected_palette_name = self.colorbar_dropdown.currentText().strip()
        if not selected_palette_name:
            print("Error: No color palette selected.")
            return
    
        print(f"📂 Loading Palette: {selected_palette_name}")
        self.selected_color_palette = self.load_color_palette(selected_palette_name)
    
        if hasattr(self, 'min_value') and hasattr(self, 'max_value'):
            self.display_color_range(self.min_value, self.max_value)

    def display_color_range(self, min_attr, max_attr):
        """Display the color range gradient with correctly aligned min/max labels."""
        if not self.selected_color_palette or min_attr is None or max_attr is None:
            print("Unable to display color range.")
            self.color_display.clear()
            self.min_value_label.clear()
            self.max_value_label.clear()
            return

        try:
            min_value = float(min_attr)
            max_value = float(max_attr)
            self.min_value_label.setText(f"{min_value:.2f}")
            self.max_value_label.setText(f"{max_value:.2f}")
        except ValueError:
            print("Could not convert min/max to float")
            return

        # Create and draw gradient
        pixmap = QPixmap(self.color_display.width(), self.color_display.height())
        pixmap.fill(Qt.white)
        painter = QPainter(pixmap)

        gradient = QLinearGradient(0, 0, self.color_display.width(), 0)
        for i, color in enumerate(self.selected_color_palette):
            gradient.setColorAt(i / (len(self.selected_color_palette) - 1), color)

        painter.setBrush(QBrush(gradient))
        painter.drawRect(0, 0, self.color_display.width(), self.color_display.height())

        # Draw ticks
        painter.setPen(QPen(Qt.black, 2))
        num_ticks = 5
        tick_positions = []

        for i in range(num_ticks):
            x = int(i * (self.color_display.width() / (num_ticks - 1)))
            tick_positions.append(x)
            painter.drawLine(x, self.color_display.height(), x, self.color_display.height() - 8)

        painter.end()
        self.color_display.setPixmap(pixmap)

        # Adjust label positions
        self.min_value_label.setFixedWidth(50)
        self.max_value_label.setFixedWidth(50)
        self.min_value_label.setStyleSheet(f"margin-left: {tick_positions[0]}px;")
        self.max_value_label.setStyleSheet(f"margin-right: {self.color_display.width() - tick_positions[-1]}px;")

    def map_value_to_color(self, value, min_value, max_value, color_palette):
        """Map a value to a color based on the min and max range."""
        if not color_palette:
            return QColor(0, 0, 0)

        if max_value == min_value:
            return color_palette[0] if color_palette else QColor(0, 0, 0)

        normalized_value = (value - min_value) / (max_value - min_value)
        index = int(normalized_value * (len(color_palette) - 1)) if not pd.isna(normalized_value) else 0
        index = max(0, min(index, len(color_palette) - 1))

        return color_palette[index]


    # Convenience methods for accessing dropdown text
    def currentText(self):
        return self.colorbar_dropdown.currentText()

    def setCurrentText(self, text):
        self.colorbar_dropdown.setCurrentText(text)

    def currentColorBar(self):
        return self.colorbar_dropdown.combo.currentText()