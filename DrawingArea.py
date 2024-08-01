# drawing_area.py
import pandas as pd
from PySide2.QtWidgets import QWidget
from PySide2.QtGui import QPainter, QColor, QPen, QFont
from PySide2.QtCore import Qt,  QPointF
from shapely.geometry import LineString, Point, MultiPoint, GeometryCollection


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
        self.zone_color_df = pd.DataFrame()
        self.clickPoints = []
        self.rectangles = []
        self.hovered_uwi = None
        self.show_uwis = True
        self.uwi_opacity = 0.5

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.translate(self.offset)
        painter.scale(self.scale, self.scale)
        painter.fillRect(self.rect(), Qt.white)

        zone_colors = {index: QColor(*row['Zone Color (RGB)']) for index, row in self.zone_color_df.iterrows()} if not self.zone_color_df.empty else {}

        for uwi, scaled_offsets in self.scaled_data.items():
            points = []
            for (scaled_point, tvd, zone) in scaled_offsets:
                inverted_point = QPointF(scaled_point.x(), self.height() - scaled_point.y())
                points.append((inverted_point, zone))

            for i in range(1, len(points)):
                zone = points[i - 1][1]
                color = zone_colors.get(zone, QColor(0, 0, 0))
                pen = QPen(color)
                pen.setWidth(self.map_instance.line_width)
                color.setAlphaF(self.map_instance.line_opacity)
                painter.setPen(pen)
                painter.drawLine(points[i - 1][0], points[i][0])

            if self.show_uwis and points:
                painter.save()
                painter.translate(points[0][0])
                painter.rotate(-45)
                font = QFont()
                if uwi == self.hovered_uwi:
                    color = QColor(255, 0, 0)
                    font.setPointSize(self.map_instance.uwi_width * 2)
                    font.setBold(True)
                else:
                    color = QColor(0, 0, 0)
                    font.setPointSize(self.map_instance.uwi_width)
                    font.setBold(False)

                color.setAlphaF(self.map_instance.uwi_opacity)
                painter.setPen(color)
                painter.setFont(font)
                painter.drawText(0, 0, uwi)
                painter.restore()

        if len(self.currentLine) > 1:
            redPen = QPen(Qt.red)
            redPen.setWidth(2)
            painter.setPen(redPen)
            for i in range(1, len(self.currentLine)):
                painter.drawLine(self.currentLine[i - 1], self.currentLine[i])

        for point in self.intersectionPoints:
            painter.drawEllipse(point, 5, 5)

        for point in self.clickPoints:
            painter.setPen(Qt.red)
            painter.setBrush(Qt.red)
            painter.drawRect(point.x() - 2, point.y() - 2, 4, 4)

        for top_left, bottom_right in self.rectangles:
            try:
                linePen = QPen(Qt.blue)
                linePen.setWidth(2)
                painter.setPen(linePen)
                painter.setBrush(Qt.NoBrush)

                top_right = QPointF(bottom_right.x(), top_left.y())
                bottom_left = QPointF(top_left.x(), bottom_right.y())

                painter.drawLine(top_left, top_right)
                painter.drawLine(top_right, bottom_right)
                painter.drawLine(bottom_right, bottom_left)
                painter.drawLine(bottom_left, top_left)
            except Exception as e:
                print(f"Error drawing lines: {e}")

    def setScaledData(self, scaled_data, zone_color_df):
        self.scaled_data = scaled_data
        self.zone_color_df = zone_color_df
        self.zone_color_df['Zone Color (RGB)'] = self.zone_color_df['Zone Color (RGB)'].apply(lambda x: tuple(x))
        self.zone_color_df.index = self.zone_color_df.index.astype(int)
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
