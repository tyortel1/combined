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
                font-weight: 500;
                font-size: 13px;
                color: #333333;
                border-style: solid;
                border-width: 1px;
                border-bottom-width: 3px;
            }
            QPushButton:hover {
                color: #1a1a1a;
            }
            QPushButton:pressed {
                padding-top: 6px;
                padding-bottom: 4px;
                border-bottom-width: 1px;
            }
        """
        
        button_styles = {
            "function": ("#C7E6C7", "#A8D1A8", "#95C795"),
            "close": ("#E6C3C3", "#D1A8A8", "#C79595"),
            "export": ("#C3C3E6", "#A8A8D1", "#9595C7"),
            "default": ("#E0E0E0", "#CCCCCC", "#B0B0B0")
        }

        bg_color, hover_color, border_color = button_styles.get(button_type, button_styles["default"])

        color_style = f"""
            QPushButton {{
                background-color: {bg_color};
                border-color: {border_color};
            }}
            QPushButton:hover {{
                background-color: {hover_color};
            }}
            QPushButton:pressed {{
                background-color: {border_color};
                border-bottom-color: {hover_color};
            }}
        """

        self.setStyleSheet(base_style + color_style)