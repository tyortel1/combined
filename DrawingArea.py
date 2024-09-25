import os
import numpy as np
from PySide2.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsRectItem, QGraphicsItemGroup, QGraphicsTextItem, QGraphicsEllipseItem, QGraphicsPixmapItem, QGraphicsPathItem, QGraphicsLineItem, QGraphicsItem
from PySide2.QtGui import QPainter, QColor, QPen, QFont, QPainterPath, QBrush, QTransform, QImage, QPixmap, QFontMetrics
from PySide2.QtCore import Qt, QPointF, QRectF, Signal, QLineF

class BulkZoneTicks(QGraphicsItem):
    def __init__(self, zone_ticks, line_width=1):
        super().__init__()
        self.zone_ticks = zone_ticks
        self._line_width = line_width / 10
        self.setFlag(QGraphicsItem.ItemUsesExtendedStyleOption)

    @property
    def line_width(self):
        return self._line_width

    @line_width.setter
    def line_width(self, value):
        self._line_width = value / 10
        self.update()

    def boundingRect(self):
        if not self.zone_ticks:
            return QRectF()
        x_coords, y_coords, _, _ = zip(*self.zone_ticks)
        return QRectF(min(x_coords), min(y_coords), max(x_coords) - min(x_coords), max(y_coords) - min(y_coords))

    def paint(self, painter, option, widget):
        scale = painter.transform().m11()
        visible_rect = option.exposedRect

        painter.setPen(QPen(QColor(0, 100, 0), self.line_width))

        for x, y, _, angle in self.zone_ticks:
            if not visible_rect.contains(x, y):
                continue

            start_point = (x - 100 * np.cos(angle), y - 100 * np.sin(angle))
            end_point = (x + 100 * np.cos(angle), y + 100 * np.sin(angle))
            painter.drawLine(start_point[0], start_point[1], end_point[0], end_point[1])

class WellAttributeBox(QGraphicsRectItem):
    def __init__(self, uwi, position, color, size=10):
        super().__init__(-size / 2, -size / 2, size, size)
        self.uwi = uwi  # Store the UWI associated with this box
        self.setBrush(QBrush(color))
        self.setPen(Qt.NoPen)  # No border
        self.setPos(position)
        self.setData(0, 'wellattributebox')  # Tag the item for easy identification

    def update_color(self, color):
        self.setBrush(QBrush(color))

class DrawingArea(QGraphicsView):
    leftClicked = Signal(QPointF)
    rightClicked = Signal(QPointF)

    def __init__(self, map_instance, fixed_width=2000, fixed_height=1500, parent=None):
        super().__init__(parent)
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        self.setRenderHint(QPainter.Antialiasing)
        self.setRenderHint(QPainter.SmoothPixmapTransform)
        self.setRenderHint(QPainter.HighQualityAntialiasing)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setDragMode(QGraphicsView.NoDrag)
        self.setTransform(QTransform().scale(1, -1))
        self.setAutoFillBackground(True)

        self.map_instance = map_instance
        self.scaled_data = {}
        self.currentLine = None
        self.intersectionPoints = []
        self.clickPoints = []
        self.rectangles = []
        self.hovered_uwi = None
        self.show_uwis = True
        self.uwi_opacity = 0.5
        self.gridPoints = []
        self.gridGroup = None
        self.zoneTicks = []
        self.zoneTickCache = {}
        self.lineItemPool = []
        self.pixmap_item_pool = []
        self.textItemPool = []
        self.uwi_items = {}
        self.well_attribute_boxes = {}
        self.line_items = {}
        self.view_adjusted = False
        self.initial_fit_in_view_done = False 

        self.textPixmapCache = {}
        self.color_palette = self.load_color_palette('Palettes/Rainbow.pal')
        self.reset_boundaries()
                # Set background color to very light grey
        light_grey = QColor(240, 240, 240)
        self.setBackgroundBrush(QBrush(light_grey))

    def reset_boundaries(self):
        self.min_x = self.max_x = self.min_y = self.max_y = self.min_z = self.max_z = 0
        self.bin_size_x = self.bin_size_y = 1
        self.uwi_width = 80
        self.uwi_opacity = 1
        self.line_width = 80
        self.line_opacity = 1.0
        self.scale_factor = 1.0
        self.draw_mode = False

    def load_color_palette(self, file_path):
        color_palette = []
        with open(file_path, 'r') as file:
            lines = file.readlines()
            start_index = lines.index('ColorPalette "Rainbow" 256\n') + 2
            for line in lines[start_index:]:
                r, g, b = map(int, line.strip().split())
                color_palette.append(QColor(r, g, b))
        return color_palette

    def setScaledData(self, well_data, well_attribute_values=None):
        self.clearUWILines()
        

        new_items = []

        all_x = [x for well in well_data.values() for x in well['x_offsets']]
        all_y = [y for well in well_data.values() for y in well['y_offsets']]



        self.min_x, self.max_x = min(all_x), max(all_x)
        self.min_y, self.max_y = min(all_y), max(all_y)

        for uwi, well in well_data.items():
            points = well['points']
            mds = well['mds']
            md_colors = well.get('md_colors', [QColor(Qt.black)] * len(mds))

            if len(points) > 1:
                for i in range(len(points) - 1):
                    start_point = points[i]
                    end_point = points[i + 1]
                    md = mds[i]
                    # Calculate the direction of the line
                    direction = (end_point - start_point)
                    direction = direction / direction.manhattanLength()  # Normalize the direction vector

                    # Dynamically calculate the offset based on the zoom level
                    current_scale = self.transform().m11()  # Get the current scale factor from the QGraphicsView transform
                    base_offset = 0.5  # Base offset to extend the line slightly
                    adjusted_offset = base_offset / current_scale  # Adjust offset based on zoom level

                    # Extend the start and end points slightly
                    adjusted_start_point = start_point - direction * adjusted_offset
                    adjusted_end_point = end_point + direction * adjusted_offset

                    color = md_colors[i] if i < len(md_colors) else QColor(Qt.black)
                    color.setAlphaF(self.uwi_opacity)

                    line = QGraphicsLineItem(QLineF(adjusted_start_point, adjusted_end_point))
                    pen = QPen(color)
                    pen.setWidth(self.line_width)
                    pen.setCapStyle(Qt.FlatCap)  # Keep the original cap style
                    line.setPen(pen)
                    line.setZValue(5)
                    line.setData(0, 'uwiline')
                    new_items.append(line)

                    if uwi not in self.line_items:
                        self.line_items[uwi] = {}
                    self.line_items[uwi][md] = line

                if self.show_uwis:
                    self.add_text_item(uwi, points[0])

            if well_attribute_values and uwi in well_attribute_values:
                color = well_attribute_values[uwi]['color']
                box_position = points[0] + QPointF(0, 20)

                if uwi in self.well_attribute_boxes:
                    self.well_attribute_boxes[uwi].setPos(box_position)
                    self.well_attribute_boxes[uwi].update_color(color)
                else:
                    well_attribute_box = WellAttributeBox(uwi, box_position, color, size=20)
                    self.scene.addItem(well_attribute_box)
                    self.well_attribute_boxes[uwi] = well_attribute_box

                new_items.append(self.well_attribute_boxes[uwi])

        for item in new_items:
            self.scene.addItem(item)

        
        # Only run fitInView the first time
        if not self.initial_fit_in_view_done:
            self.fitInView(self.scene.sceneRect(), Qt.KeepAspectRatio)
            self.initial_fit_in_view_done = True 

    def clearWellAttributeBoxes(self):
        for uwi, box in self.well_attribute_boxes.items():
            self.scene.removeItem(box)
        self.well_attribute_boxes.clear()

    def add_text_item(self, uwi_times, position):
        try:
            text_item = QGraphicsTextItem(uwi_times)
            text_item.setFont(QFont("Arial", self.uwi_width))
            text_item.setDefaultTextColor(QColor(0, 0, 0, int(255 * self.uwi_opacity)))
            text_item.setPos(position)

            transform = QTransform()
            transform.rotate(45)
            transform.scale(1, -1)
            text_item.setTransform(transform, True)

            text_item.setZValue(2)
            text_item.setCacheMode(QGraphicsItem.DeviceCoordinateCache)
            self.scene.addItem(text_item)
            self.uwi_items[uwi_times] = text_item
        except Exception as e:
            print(f"Error adding text item for UWI {uwi_times}: {e}")

    def is_point_in_range(self, start_point, end_point, md):
        return start_point.x() <= md <= end_point.x()

    def getLineItemFromPool(self):
        if self.lineItemPool:
            return self.lineItemPool.pop()
        return QGraphicsLineItem()

    def returnLineItemToPool(self, item):
        item.setVisible(False)
        self.scene.removeItem(item)
        self.lineItemPool.append(item)

    def returnPixmapItemToPool(self, pixmap_item):
        pixmap_item.setVisible(False)
        self.scene.removeItem(pixmap_item)
        self.pixmap_item_pool.append(pixmap_item)

    def returnTextItemToPool(self, text_item):
        text_item.setVisible(False)
        self.scene.removeItem(text_item)
        self.textItemPool.append(text_item)

    def clearScene(self):
        self.scene.clear()
        self.zoneTicks = []
        self.scene.update()



    def add_well_attribute_boxes(self, well_attribute_values):
     
        """
        Adds well attribute boxes to the map based on the provided well_attribute_values list.
        """
        for point, color in well_attribute_values:
            circle_item = QGraphicsEllipseItem(point.x() - 100, point.y() - 100, 200, 200) # Adjust size as needed
            circle_item.setBrush(QBrush(color))
            circle_item.setPen(QPen(Qt.NoPen))  # No border
            circle_item.setZValue(10)  # Ensure it appears above other items
            circle_item.setData(0, 'well_attribute_box')  # Tag for easy removal later
            self.scene.addItem(circle_item)


    def clearWellAttributeBoxes(self):
        """
        Clears all well attribute boxes from the scene.
        """
        items_to_remove = [item for item in self.scene.items() if item.data(0) == 'well_attribute_box']
        for item in items_to_remove:
            self.scene.removeItem(item)

    def setZoneTicks(self, zone_ticks):
        if not zone_ticks:
            print("No zone ticks provided.")
            return

        self.clearZones()
        self.zoneTicks = zone_ticks

        for item in self.scene.items():
            if isinstance(item, BulkZoneTicks):
                self.scene.removeItem(item)

        bulk_ticks = BulkZoneTicks(zone_ticks, line_width=self.line_width)
        bulk_ticks.setData(0, 'bulkzoneticks')
        bulk_ticks.setZValue(6)
        self.scene.addItem(bulk_ticks)

        self.scene.update()
        self.viewport().update()

    def setGridPoints(self, points_with_values, min_x, max_x, min_y, max_y, min_z, max_z, bin_size_x, bin_size_y):
        self.min_x, self.max_x, self.min_y, self.max_y = min_x, max_x, min_y, max_y
        self.min_z, self.max_z = min_z, max_z
        self.bin_size_x, self.bin_size_y = bin_size_x, bin_size_y

        if hasattr(self, 'gridGroup'):
            self.scene.removeItem(self.gridGroup)
            self.gridGroup = None

        self.gridGroup = QGraphicsItemGroup()
        overlap_factor = 100

        for point, color in points_with_values:
            rect_item = QGraphicsRectItem(
                point.x() - bin_size_x / 2 - overlap_factor,
                point.y() - bin_size_y / 2 - overlap_factor,
                bin_size_x + 2 * overlap_factor,
                bin_size_y + 2 * overlap_factor
            )
            rect_item.setBrush(QBrush(color))
            rect_item.setPen(QPen(Qt.NoPen))
            rect_item.setData(0, 'gridpoint')
            rect_item.setZValue(-10)
            self.gridGroup.addToGroup(rect_item)

        self.scene.addItem(self.gridGroup)
        self.gridPoints = self.gridGroup.childItems()
        self.calculate_scene_size()

    def calculate_scene_size(self):
        rect = self.scene.itemsBoundingRect()
        self.scene.setSceneRect(rect.adjusted(-rect.width() * 0.1, -rect.height() * 0.1, rect.width() * 0.1, rect.height() * 0.1))

    def wheelEvent(self, event):
        if event.modifiers() == Qt.ControlModifier:
            zoom_in_factor = 1.25
            zoom_out_factor = 1 / zoom_in_factor

            zoom_factor = zoom_in_factor if event.angleDelta().y() > 0 else zoom_out_factor
            self.zoom(zoom_factor, event.pos())
        else:
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - event.angleDelta().y())

    def zoom(self, zoom_factor, center_point):
        old_pos = self.mapToScene(center_point)
        self.scale(zoom_factor, zoom_factor)
        self.scale_factor *= zoom_factor
        new_pos = self.mapToScene(center_point)
        delta = new_pos - old_pos
        self.translate(delta.x(), delta.y())
        self.map_instance.updateScrollBars()

    def setCurrentLine(self, points):
        if self.currentLine:
            self.scene.removeItem(self.currentLine)

        if len(points) > 1:
            path = QPainterPath()
            path.moveTo(points[0])
            for point in points[1:]:
                path.lineTo(point)

            pen = QPen(Qt.red, 3)
            pen.setCosmetic(True)
            self.currentLine = self.scene.addPath(path, pen)
            self.currentLine.setZValue(10)

    def setIntersectionPoints(self, points):
        size = 80  # Match the size of the click points
        pen = QPen(Qt.red, 3)  # Match the pen style of the click points
        pen.setCosmetic(True)
        brush = QBrush(Qt.red)  # Match the brush style of the click points
    
        # Remove existing intersection points
        for point in self.intersectionPoints:
            self.scene.removeItem(point)
        self.intersectionPoints = []
   
    
        # Add new intersection points
        for point in points:
            item = self.scene.addEllipse(point.x() - size / 2, point.y() - size / 2, size, size, pen, brush)
            item.setZValue(10)  # Match the Z-value of the click points
            self.intersectionPoints.append(item)

    def clearCurrentLineAndIntersections(self):
        if self.currentLine:
            self.scene.removeItem(self.currentLine)
            self.currentLine = None
        for point in self.intersectionPoints:
            self.scene.removeItem(point)
        self.intersectionPoints = []
        for point in self.clickPoints:
            self.scene.removeItem(point)
        self.clickPoints = []

    def addClickPoint(self, point):
        size = 80
        pen = QPen(Qt.red, 3)
        pen.setCosmetic(True)
        brush = QBrush(Qt.red)
        item = self.scene.addEllipse(point.x() - size / 2, point.y() - size / 2, size, size, pen, brush)
        item.setZValue(10)
        self.clickPoints.append(item)

    def map_value_to_color(self, value):
        index = int((value - self.min_z) / (self.max_z - self.min_z) * (len(self.color_palette) - 1))
        index = max(0, min(index, len(self.color_palette) - 1))
        return self.color_palette[index]

    def setScale(self, new_scale):
        self.resetTransform()
        self.scale_factor = new_scale
        self.setTransform(QTransform().scale(self.scale_factor, self.scale_factor))

    def setOffset(self, new_offset):
        self.setSceneRect(self.scene.itemsBoundingRect())
        self.centerOn(new_offset)

    def updateHoveredUWI(self, uwi):
        self.hovered_uwi = uwi
        for item in self.scene.items():
            if isinstance(item, QGraphicsTextItem):
                if item.toPlainText() == uwi:
                    item.setFont(QFont("Arial", self.map_instance.uwi_width * 2, QFont.Bold))
                    item.setDefaultTextColor(QColor(255, 0, 0))
                else:
                    item.setFont(QFont("Arial", self.map_instance.uwi_width))
                    item.setDefaultTextColor(QColor(0, 0, 0, int(255 * self.map_instance.uwi_opacity)))
        self.scene.update()

    def updateUWIWidth(self, width):
        self.uwi_width = width
        for item in self.scene.items():
            if isinstance(item, QGraphicsTextItem):
                font = item.font()
                font.setPointSize(width)
                item.setFont(font)
        self.scene.update()

    def setUWIOpacity(self, opacity):
        self.uwi_opacity = opacity
        for text_item in self.uwi_items.values():
            color = text_item.defaultTextColor()
            color.setAlphaF(opacity)
            text_item.setDefaultTextColor(color)
        self.scene.update()

    def updateLineWidth(self, width):
        self.line_width = width
        for item in self.scene.items():
            if isinstance(item, QGraphicsLineItem) and item.data(0) == 'uwiline':
                pen = item.pen()
                pen.setWidth(width)
                item.setPen(pen)
            elif isinstance(item, BulkZoneTicks):
                item.line_width = width
                item.update()
        self.scene.update()

    def updateLineOpacity(self, opacity):
        self.line_opacity = opacity
        for item in self.scene.items():
            if isinstance(item, QGraphicsLineItem) and item.data(0) == 'uwiline':
                pen = item.pen()
                color = pen.color()
                color.setAlphaF(opacity)
                pen.setColor(color)
                item.setPen(pen)
        self.scene.update()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.calculate_scene_size()

    def clearAll(self):
        self.scene.clear()
        self.currentLine = None
        self.intersectionPoints = []
        self.clickPoints = []
        self.rectangles = []
        self.gridPoints = []
        self.zoneTicks = []

    def exportScene(self, file_path):
        image = QImage(self.scene.sceneRect().size().toSize(), QImage.Format_ARGB32)
        image.fill(Qt.white)

        painter = QPainter(image)
        self.scene.render(painter)
        painter.end()

        image.save(file_path)

    def fitSceneInView(self):
        self.fitInView(self.scene.sceneRect(), Qt.KeepAspectRatio)

    def mousePressEvent(self, event):
        scene_pos = self.mapToScene(event.pos())
        x = scene_pos.x()
        y = scene_pos.y()

        if event.button() == Qt.LeftButton:
            self.leftClicked.emit(scene_pos)
            print(f"Left Button Clicked at: ({x}, {y})")
        elif event.button() == Qt.RightButton:
            self.rightClicked.emit(scene_pos)
            print(f"Right Button Clicked at: ({x}, {y})")

        super().mousePressEvent(event)

    def clearGrid(self):
        if hasattr(self, 'gridGroup') and self.gridGroup is not None:
            self.scene.removeItem(self.gridGroup)
            self.gridGroup = None
        self.gridPoints = []
  

    def clearZones(self):
        print("Clearing 'uwiline', tick data, and 'BulkZoneTicks' items from the scene.")

        # Remove 'uwiline' items
        uwilines_to_remove = [item for item in self.scene.items() if item.data(0) == 'uwiline']
        for item in uwilines_to_remove:
            if item.scene() is not None:
                self.scene.removeItem(item)

        # Remove tick data (assuming tick data is associated with BulkZoneTicks or similar)
        ticks_to_remove = [item for item in self.scene.items() if isinstance(item, BulkZoneTicks)]
        for item in ticks_to_remove:
            if item.scene() is not None:
                self.scene.removeItem(item)

        # Clear related data structures
        self.zoneTicks.clear()
        self.zoneTickCache.clear()



    def updateScene(self):
        self.scene.update()
        self.setUpdatesEnabled(True)

    def set_processed_data(self, processed_data):
        self.processed_data = processed_data
        self.update_colored_segments()

    #def update_colored_segments(self):
    #    for item in self.scene.items():
    #        if isinstance(item, QGraphicsPathItem) and item.data(0) == 'colored_segment':
    #            self.scene.removeItem(item)

    #    for uwi, points in self.processed_data.items():
    #        if len(points) > 1:
    #            for i in range(len(points) - 1):
    #                segment_path = QPainterPath()
    #                segment_path.moveTo(QPointF(points[i]['x'], points[i]['y']))
    #                segment_path.lineTo(QPointF(points[i + 1]['x'], points[i + 1]['y']))

    #                path_item = QGraphicsPathItem(segment_path)
    #                pen = QPen(points[i]['color'])
    #                pen.setWidth(self.line_width)
    #                path_item.setPen(pen)
    #                path_item.setCacheMode(QGraphicsItem.DeviceCoordinateCache)
    #                path_item.setData(0, 'colored_segment')
    #                path_item.setZValue(4)
    #                self.scene.addItem(path_item)

    def get_point_by_md(self, uwi, md):
        if uwi not in self.scaled_data:
            return None
        for point, point_md in self.scaled_data[uwi]:
            if point_md >= md:
                return point
        return None

    def clearUWILines(self):
        for item in self.scene.items():
            if item.data(0) == 'uwiline':
                if item.scene() is not None:
                    self.scene.removeItem(item)
