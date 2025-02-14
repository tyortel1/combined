from PySide6.QtWidgets import QPushButton
from PySide6.QtCore import Qt

class StyledButton(QPushButton):
    def __init__(self, text, button_type, parent=None):
        super().__init__(text, parent)
        self.setCursor(Qt.PointingHandCursor)
        self.setButtonStyle(button_type)

    def setButtonStyle(self, button_type):
        base_style = """
            QPushButton {
                padding: 5px 15px;
                border-radius: 4px;
                font-weight: bold;
                font-size: 12px;
                color: white;
            """
        
        if button_type == "function":
            color_style = """
                background-color: #2ecc71;
            }
            QPushButton:hover {
                background-color: #27ae60;
            }
            """
        elif button_type == "close":
            color_style = """
                background-color: #e74c3c;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
            """
        elif button_type == "export":
            color_style = """
                background-color: #3498db;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
            """
        else:
            color_style = """
                background-color: #95a5a6;
            }
            QPushButton:hover {
                background-color: #7f8c8d;
            }
            """

        self.setStyleSheet(base_style + color_style)