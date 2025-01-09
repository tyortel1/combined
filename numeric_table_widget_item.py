from PySide6.QtWidgets import QTableWidgetItem
from PySide6.QtCore import Qt

class NumericTableWidgetItem(QTableWidgetItem):
    def __init__(self, value):
        # Format the numeric value to 2 decimal places or use string representation
        super().__init__(f"{value:.2f}" if isinstance(value, (int, float)) else str(value))
        self.value = value  # Store the raw numeric value
        # Align the text to the right for better numeric formatting
        self.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)

    def __lt__(self, other):
        # Ensure that sorting works correctly for numeric values
        if isinstance(other, NumericTableWidgetItem):
            return self.value < other.value
        return super().__lt__(other)
