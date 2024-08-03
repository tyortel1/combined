import os
from PySide2.QtWidgets import QWidget
from PySide2.QtGui import QPainter, QColor, QPen, QFont
from PySide2.QtCore import Qt, QPointF

class DrawingArea(QWidget):
    def __init__(self, map_instance, fixed_width, fixed_height, parent=None):
        super().__init__(parent)
        self.setFixedSize(fixed_width, fixed_height)
        self.map_instance = map_instance
        self.scale = 1.0
        self.offset = QPointF(0, 0)
        self.scaled_data = {}
        self.currentLine = []
        self.originalCurrentLine = []
        self.intersectionPoints = []
        self.originalIntersectionPoints = []
        self.clickPoints = []
        self.rectangles = []
        self.nodes = []  # List to store nodes
        self.hovered_uwi = None
        self.show_uwis = True
        self.uwi_opacity = 0.5
        self.gridPoints = []  # To store grid points and their corresponding values
        self.color_palette = self.load_color_palette('Palettes/Rainbow.pal')  # Load color palette
        self.min_x = 0
        self.max_x = 1
        self.min_y = 0
        self.max_y = 1

    def load_color_palette(self, file_path):
        color_palette = []
        with open(file_path, 'r') as file:
            lines = file.readlines()
            start_index = lines.index('ColorPalette "Rainbow" 256\n') + 2
            for line in lines[start_index:]:
                r, g, b = map(int, line.strip().split())
                color_palette.append(QColor(r, g, b))
        return color_palette

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.translate(self.offset)
        painter.scale(self.scale, self.scale)
        painter.fillRect(self.rect(), Qt.white)

        # Define the pen color and opacity
        pen_color = QColor(0, 0, 0)
        pen_color.setAlphaF(self.map_instance.line_opacity)
        pen = QPen(pen_color)
        pen.setWidth(self.map_instance.line_width)

        # Draw the scaled data lines and UWI labels
        for uwi, scaled_offsets in self.scaled_data.items():
            points = [self.scale_and_translate_point(QPointF(scaled_point.x(), scaled_point.y())) for scaled_point, _ in scaled_offsets]

            # Draw lines
            if len(points) > 1:
                painter.setPen(pen)
                for i in range(1, len(points)):
                    painter.drawLine(points[i - 1], points[i])

            # Draw UWI labels
            if self.show_uwis and points:
                painter.save()
                painter.translate(points[0])
                painter.rotate(-45)
                font = QFont()
                color = QColor(255, 0, 0) if uwi == self.hovered_uwi else QColor(0, 0, 0)
                font.setPointSize(self.map_instance.uwi_width * (2 if uwi == self.hovered_uwi else 1))
                font.setBold(uwi == self.hovered_uwi)
                color.setAlphaF(self.map_instance.uwi_opacity)
                painter.setPen(color)
                painter.setFont(font)
                painter.drawText(0, 0, uwi)
                painter.restore()

        # Draw current line
        if len(self.currentLine) > 1:
            redPen = QPen(Qt.red)
            redPen.setWidth(2)
            painter.setPen(redPen)
            for i in range(1, len(self.currentLine)):
                print(f"Drawing line from {self.currentLine[i - 1]} to {self.currentLine[i]}")  # Debugging statement
                painter.drawLine(self.currentLine[i - 1], self.currentLine[i])

        # Draw intersection points
        for point in self.intersectionPoints:
            print(f"Drawing intersection point at: {point}")  # Debugging statement
            painter.setPen(Qt.black)
            painter.setBrush(Qt.black)
            painter.drawEllipse(point, 5, 5)

        # Draw click points
        for point in self.clickPoints:
            print(f"Drawing click point at: {point}")  # Debugging statement
            painter.setPen(Qt.red)
            painter.setBrush(Qt.red)
            painter.drawRect(point.x() - 2, point.y() - 2, 4, 4)

        # Draw rectangles
        for top_left, bottom_right in self.rectangles:
            linePen = QPen(Qt.blue)
            linePen.setWidth(2)
            painter.setPen(linePen)
            painter.setBrush(Qt.NoBrush)
            top_left_scaled = QPointF(top_left.x(), top_left.y())
            bottom_right_scaled = QPointF(bottom_right.x(), bottom_right.y())
            top_right = QPointF(bottom_right_scaled.x(), top_left_scaled.y())
            bottom_left = QPointF(top_left_scaled.x(), bottom_right_scaled.y())
            painter.drawLine(top_left_scaled, top_right)
            painter.drawLine(top_right, bottom_right_scaled)
            painter.drawLine(bottom_right_scaled, bottom_left)
            painter.drawLine(bottom_left, top_left_scaled)
        # Draw nodes

        # Draw grid points with colors
        print("Drawing grid points:", self.gridPoints)  # Debugging information
        for point, value in self.gridPoints:
            color = self.map_value_to_color(value)
            gridPen = QPen(color)
            gridPen.setWidth(2)
            painter.setPen(gridPen)
            painter.setBrush(color)
            scaled_point = self.scale_and_translate_point(point)
            painter.drawEllipse(scaled_point, 3, 3)

    def scale_and_translate_point(self, point):
        # Calculate the scale factors
        scale_x = self.width() / (self.max_x - self.min_x) if self.max_x != self.min_x else 1
        scale_y = self.height() / (self.max_y - self.min_y) if self.max_y != self.min_y else 1

        # Apply scaling and translation
        translated_x = (point.x() - self.min_x) * scale_x
        translated_y = (self.max_y - point.y()) * scale_y  # Flipping the Y axis
        return QPointF(translated_x, translated_y)

    def map_value_to_color(self, value):
        # Normalize the value to the range of the color palette
        min_val, max_val = 0, 255  # Assuming the value range is 0 to 255
        index = int((value - min_val) / (max_val - min_val) * (len(self.color_palette) - 1))
        return self.color_palette[index]

    def setScaledData(self, scaled_data, min_x, max_x, min_y, max_y):
        self.scaled_data = scaled_data
        self.min_x = min_x
        self.max_x = max_x
        self.min_y = min_y
        self.max_y = max_y
        self.update()

    def setCurrentLine(self, current_line):
        self.currentLine = current_line
        self.originalCurrentLine = [(point.x(), point.y()) for point in current_line]
        self.update()

    def setIntersectionPoints(self, points):
        self.intersectionPoints = points
        self.originalIntersectionPoints = [(point.x(), point.y()) for point in points]
        self.update()

    def addRectangle(self, top_left, bottom_right):
        self.rectangles.clear()
        self.rectangles.append((top_left, bottom_right))
        self.update()

    def clearCurrentLineAndIntersections(self):
        self.currentLine = []
        self.originalCurrentLine = []
        self.intersectionPoints = []
        self.originalIntersectionPoints = []
        self.clickPoints = []
        self.gridPoints = []  # Clear grid points
        self.nodes = []  # Clear nodes
        self.update()

    def addClickPoint(self, point):
        self.clickPoints.append(point)
        self.update()

    def setScale(self, new_scale):
        self.scale = new_scale
        self.update()

    def setOffset(self, new_offset):
        self.offset = new_offset
        self.update()

    def setGridPoints(self, points_with_values):
        self.gridPoints = points_with_values
        self.update()
