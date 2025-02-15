

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QHBoxLayout
from PySide6.QtGui import QPixmap, QPainter, QLinearGradient, QBrush, QColor, QPen
from PySide6.QtCore import Qt

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QHBoxLayout
from PySide6.QtGui import QPixmap, QPainter, QLinearGradient, QBrush, QColor, QPen
from PySide6.QtCore import Qt
import os
import pandas as pd
from StyledDropdown import StyledDropdown




from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QHBoxLayout
from PySide6.QtGui import QPixmap, QPainter, QLinearGradient, QBrush, QColor, QPen
from PySide6.QtCore import Qt

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
        layout.setSpacing(5)  # Adjust spacing for better alignment

        # Dropdown for color bar selection
        self.colorbar_dropdown = StyledDropdown(label_text, items, self)

        # Create container for color bar and ensure it aligns with StyledDropdown
        colorbar_container = QWidget(self)
        colorbar_layout = QHBoxLayout(colorbar_container)
        colorbar_layout.setContentsMargins(StyledDropdown.label_width + 5, 0, 0, 0)  # Align with StyledDropdown
        colorbar_layout.setSpacing(0)

        # Color display (gradient box)
        self.color_display = QLabel(self)
        self.color_display.setFixedSize(200, 30)  # Adjust width and height
        self.color_display.setStyleSheet("background: white; border: 1px solid #999;")

        colorbar_layout.addWidget(self.color_display)

        # Min and Max labels (now positioned correctly)
        min_max_layout = QHBoxLayout()
        min_max_layout.setContentsMargins(StyledDropdown.label_width, 0, 0, 0)  # Align with dropdown label width

        self.min_value_label = QLabel("", self)
        self.min_value_label.setAlignment(Qt.AlignLeft)

        self.max_value_label = QLabel("", self)
        self.max_value_label.setAlignment(Qt.AlignRight)

        min_max_layout.addWidget(self.min_value_label)
        min_max_layout.addStretch()
        min_max_layout.addWidget(self.max_value_label)

        # Add widgets to the main layout
        layout.addWidget(self.colorbar_dropdown)
        layout.addWidget(colorbar_container)  # Ensures alignment
        layout.addLayout(min_max_layout)  # Min/max labels below

        # Connect color selection
        self.colorbar_dropdown.combo.currentIndexChanged.connect(self.color_selected)

        # Initialize selected color palette
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

            # Update label texts
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

        # Draw ticks at correct positions
        painter.setPen(QPen(Qt.black, 2))
        num_ticks = 5  # Number of ticks to display
        tick_positions = []

        for i in range(num_ticks):
            x = int(i * (self.color_display.width() / (num_ticks - 1)))
            tick_positions.append(x)  # Store positions for later label alignment
            painter.drawLine(x, self.color_display.height(), x, self.color_display.height() - 8)

        painter.end()

        self.color_display.setPixmap(pixmap)

        # --- **Fix for Label Alignment Under the Ticks** ---
        self.min_value_label.setAlignment(Qt.AlignLeft)
        self.max_value_label.setAlignment(Qt.AlignRight)

        # Adjust label positions based on tick locations
        self.min_value_label.setFixedWidth(50)
        self.max_value_label.setFixedWidth(50)
        self.min_value_label.setStyleSheet(f"margin-left: {tick_positions[0]}px;")
        self.max_value_label.setStyleSheet(f"margin-right: {self.color_display.width() - tick_positions[-1]}px;")
    def addColorBarOptions(self, options):
        """Add color bar options to the dropdown and set default to Rainbow"""
        self.colorbar_dropdown.combo.blockSignals(True)  # Block signals
        self.colorbar_dropdown.combo.clear()
        self.colorbar_dropdown.combo.addItems(options)
    
        # Set default to Rainbow if it exists in options, otherwise use the first option
        default_option = "Rainbow" if "Rainbow" in options else options[0] if options else None
        if default_option:
            self.colorbar_dropdown.combo.setCurrentText(default_option)
    
        self.colorbar_dropdown.combo.blockSignals(False)  # Unblock signals

        # Manually call color_selected to ensure the correct palette is loaded
        self.color_selected()

    def currentColorBar(self):
        """Get current selected color bar"""
        return self.colorbar_dropdown.combo.currentText()

 
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

            # Update label texts
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

        # Draw ticks at correct positions
        painter.setPen(QPen(Qt.black, 2))
        num_ticks = 5  # Number of ticks to display
        tick_positions = []

        for i in range(num_ticks):
            x = int(i * (self.color_display.width() / (num_ticks - 1)))
            tick_positions.append(x)  # Store positions for later label alignment
            painter.drawLine(x, self.color_display.height(), x, self.color_display.height() - 8)

        painter.end()

        self.color_display.setPixmap(pixmap)

        # --- **Fix for Label Alignment Under the Ticks** ---
        self.min_value_label.setAlignment(Qt.AlignLeft)
        self.max_value_label.setAlignment(Qt.AlignRight)

        # Adjust label positions based on tick locations
        self.min_value_label.setFixedWidth(50)
        self.max_value_label.setFixedWidth(50)
        self.min_value_label.setStyleSheet(f"margin-left: {tick_positions[0]}px;")
        self.max_value_label.setStyleSheet(f"margin-right: {self.color_display.width() - tick_positions[-1]}px;")
    def addColorBarOptions(self, options):
        """Add color bar options to the dropdown and set default to Rainbow"""
        self.colorbar_dropdown.combo.blockSignals(True)  # Block signals
        self.colorbar_dropdown.combo.clear()
        self.colorbar_dropdown.combo.addItems(options)
    
        # Set default to Rainbow if it exists in options, otherwise use the first option
        default_option = "Rainbow" if "Rainbow" in options else options[0] if options else None
        if default_option:
            self.colorbar_dropdown.combo.setCurrentText(default_option)
    
        self.colorbar_dropdown.combo.blockSignals(False)  # Unblock signals

        # Manually call color_selected to ensure the correct palette is loaded
        self.color_selected()

    def currentColorBar(self):
        """Get current selected color bar"""
        return self.colorbar_dropdown.combo.currentText()