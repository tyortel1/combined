import os
import numpy as np
from PySide2.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsRectItem, QGraphicsItemGroup, QGraphicsTextItem, QGraphicsPathItem, QGraphicsLineItem, QGraphicsItem
from PySide2.QtGui import QPainter, QColor, QPen, QFont, QPainterPath, QBrush, QTransform, QWheelEvent, QImage, QPixmap, QFontMetrics
from PySide2.QtCore import Qt, QPointF, QRectF, Signal, QLineF
import time
from PySide2.QtGui import QPixmap, QPainter
from PySide2.QtWidgets import QGraphicsPixmapItem

class BulkZoneTicks(QGraphicsItem):
    def __init__(self, zone_ticks, line_width=1):
        super().__init__()
        self.zone_ticks = zone_ticks
        self._line_width = line_width/10
        self.setFlag(QGraphicsItem.ItemUsesExtendedStyleOption)

    @property
    def line_width(self):
        return self._line_width

    @line_width.setter
    def line_width(self, value):
        self._line_width = value/10
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

            # Draw line
            start_point = (x - 100 * np.cos(angle), y - 100 * np.sin(angle))
            end_point = (x + 100 * np.cos(angle), y + 100 * np.sin(angle))
            painter.drawLine(start_point[0], start_point[1], end_point[0], end_point[1])


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
        self.zoneTicks = []
        self.zoneTickCache = {}
        self.lineItemPool = []
        self.pixmap_item_pool = []  
        self.textItemPool = []
        self.uwi_items = {}
        self.line_items = {}

        # Create a cache for ticks and text pixmaps
        self.textPixmapCache = {}
        self.color_palette = self.load_color_palette('Palettes/Rainbow.pal')
        self.reset_boundaries()

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




    def setScaledData(self, well_data):
        self.well_data = well_data
        self.clearUWILines()
        new_items = []

        # Calculate min/max values directly from well_data
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
                
                    color = md_colors[i] if i < len(md_colors) else QColor(Qt.black)
                    color.setAlphaF(self.uwi_opacity)
                
                    # Create the line
                    line = QGraphicsLineItem(QLineF(start_point, end_point))
                    pen = QPen(color)
                    pen.setWidth(self.line_width)
                    pen.setCapStyle(Qt.FlatCap)  # This ensures the line ends exactly at the points
                    line.setPen(pen)
                    line.setZValue(0)
                    line.setData(0, 'uwiline')
                    new_items.append(line)


                    if uwi not in self.line_items:
                        self.line_items[uwi] = {}
                    self.line_items[uwi][md] = line

                if self.show_uwis:
                    self.add_text_item(uwi, points[0])

        for item in new_items:
            self.scene.addItem(item)

        self.calculate_scene_size()
        self.fitInView(self.scene.sceneRect(), Qt.KeepAspectRatio)
    def add_text_item(self, uwi_times, position):
        """ Helper function to add a text item for UWI. """
        try:
            text_item = QGraphicsTextItem(uwi_times)
            text_item.setFont(QFont("Arial", self.uwi_width))
            text_item.setDefaultTextColor(QColor(0, 0, 0, int(255 * self.uwi_opacity)))
            text_item.setPos(position)

            # Apply transformation to rotate and flip the text item
            transform = QTransform()
            transform.rotate(45)
            transform.scale(1, -1)  # Flip vertically
            text_item.setTransform(transform, True)

            # Set Z-value to ensure the text is drawn on top of other items
            text_item.setZValue(2)

            text_item.setCacheMode(QGraphicsItem.DeviceCoordinateCache)  # Enable caching
            self.scene.addItem(text_item)
            self.uwi_items[uwi_times] = text_item  # Store the text item with a unique key
        except Exception as e:
            print(f"Error adding text item for UWI {uwi_times}: {e}")





    def is_point_in_range(self, start_point, end_point, md):
        # Define how to determine if a point is within the MD range
        # For simplicity, assume `md` should be between `start_point.x()` and `end_point.x()`
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
        # Clear all items from the scene to ensure no residual items are left
       
        # Optionally, you can reset any internal lists or caches
        self.zoneTicks = []
        self.scene.update()  # Update the scene to reflect the changes
   
       
    def setZoneTicks(self, zone_ticks):
        if not zone_ticks:
            print("No zone ticks provided.")
            return

        self.clearZones()
        self.zoneTicks = zone_ticks

        # Remove old BulkZoneTicks item if it exists
        for item in self.scene.items():
            if isinstance(item, BulkZoneTicks):
                self.scene.removeItem(item)

        # Add new BulkZoneTicks item
        bulk_ticks = BulkZoneTicks(zone_ticks, line_width=self.line_width)
        bulk_ticks.setData(0, 'bulkzoneticks')# Use self.line_width
        bulk_ticks.setZValue(1)
        self.scene.addItem(bulk_ticks)

        self.scene.update()
        self.viewport().update()
        

    def setGridPoints(self, points_with_values, min_x, max_x, min_y, max_y, min_z, max_z, bin_size_x, bin_size_y):
        self.min_x, self.max_x, self.min_y, self.max_y = min_x, max_x, min_y, max_y
        self.min_z, self.max_z = min_z, max_z
        self.bin_size_x, self.bin_size_y = bin_size_x, bin_size_y

        # Clear existing grid points if any
        for rect in self.gridPoints:
            self.scene.removeItem(rect)
        self.gridPoints = []

        overlap_factor = 100  # Increased overlap factor to ensure no gaps

        for point, color in points_with_values:
            rect_item = QGraphicsRectItem(
                point.x() - bin_size_x / 2 - overlap_factor,
                point.y() - bin_size_y / 2 - overlap_factor,
                bin_size_x + 2 * overlap_factor,
                bin_size_y + 2 * overlap_factor
            )
            rect_item.setBrush(QBrush(color))
            rect_item.setPen(QPen(Qt.NoPen))  # Remove pen to avoid border lines

            # Set a lower Z-value to ensure it is below other items
            rect_item.setData(0, 'gridpoint') 
            rect_item.setZValue(-1)

            self.scene.addItem(rect_item)
            self.gridPoints.append(rect_item)

        self.calculate_scene_size()

    def calculate_scene_size(self):
        rect = self.scene.itemsBoundingRect()
        self.scene.setSceneRect(rect.adjusted(-rect.width()*0.1, -rect.height()*0.1, rect.width()*0.1, rect.height()*0.1))

    def wheelEvent(self, event):
        if event.modifiers() == Qt.ControlModifier:
            zoom_in_factor = 1.25
            zoom_out_factor = 1 / zoom_in_factor

            if event.angleDelta().y() > 0:
                zoom_factor = zoom_in_factor
            else:
                zoom_factor = zoom_out_factor

            self.zoom(zoom_factor, event.pos())
        else:
            # Scroll vertically
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
            self.currentLine = self.scene.addPath(path, QPen(Qt.red, 100))
            self.currentLine.setZValue(10) 

    def setIntersectionPoints(self, points):
        for point in self.intersectionPoints:
            self.scene.removeItem(point)
        self.intersectionPoints = []
        for point in points:
            item = self.scene.addEllipse(point.x() - 5, point.y() - 5, 10, 10, QPen(Qt.black), QBrush(Qt.black))
            item.setZValue(0)  # Ensure intersection points are above the grid
            self.intersectionPoints.append(item)

    def addRectangle(self, top_left, bottom_right):
        for rect in self.rectangles:
            self.scene.removeItem(rect)
        self.rectangles = []
        rect_item = self.scene.addRect(QRectF(top_left, bottom_right), QPen(Qt.blue, 2))
        rect_item.setZValue(0)  # Ensure rectangles are above the grid
        self.rectangles.append(rect_item)

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
        size = max(100 * self.scale_factor, 1)  # Minimum size of 1
        item = self.scene.addEllipse(point.x() - size/2, point.y() - size/2, size, size, QPen(Qt.red), QBrush(Qt.red))
        item.setZValue(0)  # Ensure click points are above the grid
        self.clickPoints.append(item)
        self.currentLine.setZValue(9) 

    def map_value_to_color(self, value):
        index = int((value - self.min_z) / (self.max_z - self.min_z) * (len(self.color_palette) - 1))
        index = max(0, min(index, len(self.color_palette) - 1))  # Ensure index is within bounds
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
                item.update()  # Trigger a redraw of the BulkZoneTicks item
        self.scene.update()


    def updateLineOpacity(self, opacity):
        self.line_opacity = opacity
        for item in self.scene.items():
            if isinstance(item, QGraphicsLineItem) and item.data(0) == 'uwiline':
                pen = item.pen()
                color = pen.color()
                color.setAlphaF(opacity)  # Set the new opacity
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
        # Convert mouse event position to scene coordinates
        scene_pos = self.mapToScene(event.pos())
    
        # Extract raw scene coordinates
        x = scene_pos.x()
        y = scene_pos.y()
    
        if event.button() == Qt.LeftButton:
            # If needed, convert scene coordinates to original coordinates here
            # original_x, original_y = self.scene_to_original_coordinates(scene_pos)
            # For now, emit the scene coordinates directly
            self.leftClicked.emit(scene_pos)
            print(f"Left Button Clicked at: ({x}, {y})")  # Print or use coordinates as needed

        elif event.button() == Qt.RightButton:
            self.rightClicked.emit(scene_pos)
            print(f"Right Button Clicked at: ({x}, {y})")  # Print or use coordinates as needed

        # Call the base class implementation if needed
        super().mousePressEvent(event)
    def returnPixmapItemToPool(self, pixmap_item):
        """Returns a QGraphicsPixmapItem to the pool."""
        if self.pixmap_item_pool is not None:
            self.pixmap_item_pool.append(pixmap_item)


    def clearGrid(self):
        """
        Clears all grid items from the scene and resets related attributes.
        """
        # Clear existing grid points from the scene
        for rect in self.gridPoints:
            self.scene.removeItem(rect)
        self.gridPoints = []  # Reset the list of grid points

        # Recalculate scene size if necessary
        self.calculate_scene_size()

    def clearZones(self):
        print("Clearing all items from the scene except 'uwiline' items.")

        items_to_remove = []
        # Collect all items except those tagged as 'uwiline'
        for item in self.scene.items():
            if item.data(0) not in ['uwiline']:
                items_to_remove.append(item)

        # Remove collected items from the scene
        for item in items_to_remove:
            if isinstance(item, QGraphicsLineItem):
                self.returnLineItemToPool(item)
            elif isinstance(item, QGraphicsPixmapItem):
                self.returnPixmapItemToPool(item)
            elif isinstance(item, QGraphicsTextItem):
                self.returnTextItemToPool(item)
            elif isinstance(item, QGraphicsPathItem): 
                self.scene.removeItem(item)
            else:
                self.scene.removeItem(item)

        # Check if any non-uwiline items remain (for debugging)
        remaining_items = [item for item in self.scene.items() if item.data(0) != 'uwiline']
        if remaining_items:
            print(f"Warning: {len(remaining_items)} non-uwiline items were not removed.")

        # Clear all zone-related caches (if necessary)
        self.zoneTicks.clear()
        self.zoneTickCache.clear()
        self.textPixmapCache.clear()

        # Update the scene to reflect changes
        self.scene.update()
        self.viewport().update()

        # Additional debug info
        print("Finished clearing non-uwiline and non-colored_segment items.")
        print(f"Remaining items in scene: {len(self.scene.items())}")







    def updateScene(self):
        self.scene.update()
        self.setUpdatesEnabled(True)


    def set_processed_data(self, processed_data):
        """Set the processed data and update the scene."""
        self.processed_data = processed_data
        self.update_colored_segments()

    def update_colored_segments(self):
        """Update the colored segments based on the processed data."""
        # Remove existing colored segments
        for item in self.scene.items():
            if isinstance(item, QGraphicsPathItem) and item.data(0) == 'colored_segment':
                self.scene.removeItem(item)

        for uwi, points in self.processed_data.items():
            if len(points) > 1:
                for i in range(len(points) - 1):
                    segment_path = QPainterPath()
                    segment_path.moveTo(QPointF(points[i]['x'], points[i]['y']))
                    segment_path.lineTo(QPointF(points[i + 1]['x'], points[i + 1]['y']))

                    path_item = QGraphicsPathItem(segment_path)
                    pen = QPen(points[i]['color'])
                    pen.setWidth(self.line_width)
                    path_item.setPen(pen)
                    path_item.setCacheMode(QGraphicsItem.DeviceCoordinateCache)
                    path_item.setData(0, 'colored_segment')# Enable caching
                    path_item.setZValue(4)
            # Set custom attribute
                    self.scene.addItem(path_item)

    def get_point_by_md(self, uwi, md):
        """Get the scaled point by measured depth (MD)."""
        if uwi not in self.scaled_data:
            return None
        for point, point_md in self.scaled_data[uwi]:
            if point_md >= md:
                return point
        return None
    def clearUWILines(self):

        # Iterate over all items in the scene
        for item in self.scene.items():
            # Check if the item has data tagged as 'uwiline'
            if item.data(0) == 'uwiline':
                self.scene.removeItem(item)
       # Optionally delete the item to free up resources