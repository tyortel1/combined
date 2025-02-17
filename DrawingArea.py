import os
import csv
import numpy as np
from PySide6.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsRectItem, QGraphicsItemGroup, QGraphicsTextItem, QGraphicsEllipseItem, QGraphicsPixmapItem, QGraphicsPathItem, QGraphicsLineItem, QGraphicsItem
from PySide6.QtGui import QPainter, QColor, QPen, QFont, QPainterPath, QBrush, QTransform, QImage, QPixmap, QFontMetrics, QRadialGradient, QLinearGradient
from PySide6.QtCore import Qt, QPointF, QRectF, Signal, QLineF

class BulkZoneTicks(QGraphicsItem):
    def __init__(self, zone_ticks, line_width=1):
        super().__init__()
        self.zone_ticks = zone_ticks
        self._line_width = line_width 
        self.setFlag(QGraphicsItem.ItemUsesExtendedStyleOption)

    @property
    def line_width(self):
        return self._line_width

    @line_width.setter
    def line_width(self, value):
        self._line_width = value 
        self.update()

    def boundingRect(self):
        if not self.zone_ticks:
            return QRectF()
        x_coords, y_coords, _, _ = zip(*self.zone_ticks)
        return QRectF(min(x_coords), min(y_coords), max(x_coords) - min(x_coords), max(y_coords) - min(y_coords))

    def paint(self, painter, option, widget):
        try:
            # Iterate over zone ticks, assuming it's a list of tuples (x, y, md, angle)
            pen = QPen(QColor(0, 100, 0)) 
            pen.setWidthF(self._line_width/10)  # Set the pen width using line_width
            painter.setPen(pen)


            for tick in self.zone_ticks:
                if len(tick) != 4:
                    print(f"Invalid tick data: {tick}")
                    continue

                # Extract x, y, and angle from tick
                x, y, _, angle = tick


                # Check if angle is a valid numeric type (float or int)
                if not isinstance(angle, (int, float)):
                    print(f"Invalid angle type: {angle}")
                    continue

                # Calculate start and end points for the line
                start_point = (x - 100 * np.cos(angle), y - 100 * np.sin(angle))
                end_point = (x + 100 * np.cos(angle), y + 100 * np.sin(angle))
                

                # Draw the line
                painter.drawLine(QPointF(*start_point), QPointF(*end_point))

        except Exception as e:
            print(f"Error in paint: {e}")

class WellAttributeBox(QGraphicsRectItem):
    def __init__(self, UWI, position, color, size=10):
        super().__init__(-size / 2, -size / 2, size, size)
        self.UWI = UWI  # Store the UWI associated with this box
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
        self.setRenderHint(QPainter.Antialiasing) 
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
        self.hovered_UWI = None
        self.show_UWIs = True
        self.UWI_opacity = 0.5
        self.gridPoints = []
        self.gridGroup = None
        self.zoneTicks = []
        self.zoneTickCache = {}
        self.lineItemPool = []
        self.pixmap_item_pool = []
        self.textItemPool = []
        self.UWI_items = {}
        self.well_attribute_boxes = {}
        self.line_items = {}
        self.view_adjusted = False
        self.initial_fit_in_view_done = False 
        # Default settings
        self.show_UWIs = True
        self.show_ticks = True  # Default ON
        self.drainage_visible = True
        self.drainage_size = 400  # Default 400
        self.UWI_width = 25
        self.UWI_opacity = 0.5
        self.line_width = 25
        self.line_opacity = 0.5

        self.textPixmapCache = {}
        self.color_palette = self.load_color_palette('Palettes/Rainbow.pal')
        self.reset_boundaries()
                # Set background color to very light grey
        light_grey = QColor(240, 240, 240)
        self.setBackgroundBrush(QBrush(light_grey))
        self.show_UWIs = True  # Default: Show UWI labels
        self.show_ticks = True  # Default: Show zone ticks
        self.drainage_visible = True  # NEW: Store drainage visibility state


    def reset_boundaries(self):
        self.min_x = self.max_x = self.min_y = self.max_y = self.min_z = self.max_z = 0
        self.bin_size_x = self.bin_size_y = 1
        self.UWI_width = 80
        self.UWI_opacity = 1
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
        # Clear existing UWI lines
        self.clearUWILines()

        new_items = []

        # Flatten x and y offsets to calculate min/max values
        all_x = [x for well in well_data.values() for x in well['x_offsets']]
        all_y = [y for well in well_data.values() for y in well['y_offsets']]

        self.min_x, self.max_x = min(all_x), max(all_x)
        self.min_y, self.max_y = min(all_y), max(all_y)

        for UWI, well in well_data.items():
            # Check for heel and toe coordinates
            if 'heel_x' in well and 'heel_y' in well and 'toe_x' in well and 'toe_y' in well and \
               well['heel_x'] is not None and well['toe_x'] is not None:
    
                # Skip if coordinates are empty or invalid
                if not well.get('heel_x') or not well.get('toe_x'):
                    continue

                # Ensure numeric conversion
                try:
                    heel_x = float(well['heel_x'])
                    heel_y = float(well['heel_y'])
                    toe_x = float(well['toe_x'])
                    toe_y = float(well['toe_y'])
                except (ValueError, TypeError):
                    print(f"Skipping UWI {UWI} due to invalid coordinates")
                    continue

                # Calculate angle between heel and toe
                dx = toe_x - heel_x
                dy = toe_y - heel_y
                angle = np.arctan2(dy, dx) * 180 / np.pi

                # Use drainage size from well data, with fallback to default
                width = well.get('drainage_size', self.drainage_size)
               
   
                length = np.sqrt(dx*dx + dy*dy)

                # Create the ellipse centered on the heel-toe midpoint
                center_x = (heel_x + toe_x) / 2
                center_y = (heel_y + toe_y) / 2

                ellipse = QGraphicsEllipseItem(
                    center_x - length/2,  # x position
                    center_y - width/2,   # y position
                    length,               # width
                    width                 # height
                )

                # Create a linear gradient along the length of the well
                gradient = QLinearGradient(
                    QPointF(center_x, center_y - width/2),  # Top edge
                    QPointF(center_x, center_y + width/2)   # Bottom edge
                )
                gradient.setColorAt(0.1, QColor(135, 206, 235, 150))   # Light blue at the edges
                gradient.setColorAt(0.5, QColor(0, 0, 100, 100))       # Dark blue in the middle
                gradient.setColorAt(0.9, QColor(135, 206, 235, 150))   # Light blue at the other edge

                # Apply rotation and position transform
                transform = QTransform()
                transform.translate(center_x, center_y)
                transform.rotate(angle)
                transform.translate(-center_x, -center_y)
                ellipse.setTransform(transform)

                ellipse.setBrush(QBrush(gradient))
                ellipse.setPen(QPen(Qt.NoPen))
                ellipse.setZValue(1)
                ellipse.setData(0, 'drainage')
                new_items.append(ellipse)

            # Existing well line drawing code
            points = well['points']
            mds = well['mds']
            md_colors = well.get('md_colors', [QColor(Qt.black)] * (len(points) - 1))

            if len(points) > 1:
                for i in range(len(points) - 1):
                    start_point = points[i]
                    end_point = points[i + 1]
                    md = mds[i]

                    # Calculate the direction of the line
                    direction = (end_point - start_point)
                    if direction.manhattanLength() == 0:
                        continue  # Skip if direction length is zero
                    direction = direction / direction.manhattanLength()  # Normalize direction

                    # Dynamically calculate the offset based on the zoom level
                    current_scale = self.transform().m11()  # Get the current scale factor from QGraphicsView transform
                    base_offset = 0.5  # Base offset for extending the line
                    adjusted_offset = base_offset / max(current_scale, 1e-6)  # Avoid division by zero

                    # Extend the start and end points
                    adjusted_start_point = start_point - direction * adjusted_offset
                    adjusted_end_point = end_point + direction * adjusted_offset

                    # Get line color
                    color = md_colors[i] if i < len(md_colors) else QColor(Qt.black)
                    color.setAlphaF(self.UWI_opacity)

                    # Create a QGraphicsLineItem
                    line = QGraphicsLineItem(QLineF(adjusted_start_point, adjusted_end_point))
                    pen = QPen(color)
                    pen.setWidthF(self.line_width)
                    pen.setCapStyle(Qt.FlatCap)
                    line.setPen(pen)
                    line.setZValue(5)
                    line.setData(0, 'UWIline')
                    new_items.append(line)

                    # Store the line item by UWI and MD
                    if UWI not in self.line_items:
                        self.line_items[UWI] = {}
                    self.line_items[UWI][md] = line

                # Add UWI text label if enabled
                if self.show_UWIs:
                    self.add_text_item(UWI, points[0])

            # Handle well attribute values if provided
            if well_attribute_values and UWI in well_attribute_values:
                color = well_attribute_values[UWI]['color']
                box_position = points[0] + QPointF(0, 20)

                if UWI in self.well_attribute_boxes:
                    self.well_attribute_boxes[UWI].setPos(box_position)
                    self.well_attribute_boxes[UWI].update_color(color)
                else:
                    well_attribute_box = WellAttributeBox(UWI, box_position, color, size=20)
                    self.scene.addItem(well_attribute_box)
                    self.well_attribute_boxes[UWI] = well_attribute_box

                new_items.append(self.well_attribute_boxes[UWI])

        # Add new items to the scene
        for item in new_items:
            self.scene.addItem(item)

        # Only run fitInView the first time
        if not hasattr(self, 'initial_fit_in_view_done') or not self.initial_fit_in_view_done:
            self.fitInView(self.scene.sceneRect(), Qt.KeepAspectRatio)
            self.initial_fit_in_view_done = True

        # Explicitly trigger updates to ensure changes are displayed
        self.scene.update()
        self.viewport().update()
        #self.export_well_data_to_csv(well_data)
        
        # Only run fitInView the first time
        if not self.initial_fit_in_view_done:
            self.fitInView(self.scene.sceneRect(), Qt.KeepAspectRatio)
            self.initial_fit_in_view_done = True 

    def export_well_data_to_csv(self, well_data, output_file="well_data_export.csv"):
        if not isinstance(well_data, dict):
            print("Invalid well_data format. Expected a dictionary.")
            return

        if not well_data:
            print("No data to export!")
            return

        flattened_data = []

        for UWI, data in well_data.items():
            # Debugging: Ensure data is valid
            if not isinstance(data, dict):
                print(f"Invalid data for UWI {UWI}. Skipping.")
                continue

  

            # Extract data, handling missing keys gracefully
            mds = data.get('mds', [])
            points = data.get('points', [])
            x_offsets = data.get('x_offsets', [])
            y_offsets = data.get('y_offsets', [])
            md_colors = data.get('md_colors', [])

            for i in range(len(mds)):
                row = {
                    "UWI": UWI,
                    "MD": mds[i] if i < len(mds) else None,
                    "X Offset": x_offsets[i] if i < len(x_offsets) else None,
                    "Y Offset": y_offsets[i] if i < len(y_offsets) else None,
                    "Point X": points[i].x() if i < len(points) else None,
                    "Point Y": points[i].y() if i < len(points) else None,
                    "Color (RGB)": str(md_colors[i].getRgb()) if i < len(md_colors) else None,
                }
                flattened_data.append(row)

        # Write to CSV
        output_file_path = os.path.abspath(output_file)
        with open(output_file_path, mode="w", newline="") as csvfile:
            fieldnames = ["UWI", "MD", "X Offset", "Y Offset", "Point X", "Point Y", "Color (RGB)"]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

            writer.writeheader()
            writer.writerows(flattened_data)

        print(f"Well data exported successfully to {output_file_path}")
    def clearWellAttributeBoxes(self):
        for UWI, box in self.well_attribute_boxes.items():
            self.scene.removeItem(box)
        self.well_attribute_boxes.clear()

    def add_text_item(self, UWI_times, position):
        try:
            text_item = QGraphicsTextItem(UWI_times)
            text_item.setFont(QFont("Arial", self.UWI_width))
            text_item.setDefaultTextColor(QColor(0, 0, 0, int(255 * self.UWI_opacity)))
            text_item.setPos(position)

            transform = QTransform()
            transform.rotate(45)
            transform.scale(1, -1)
            text_item.setTransform(transform, True)

            text_item.setZValue(2)
            text_item.setCacheMode(QGraphicsItem.DeviceCoordinateCache)
                    # Add a tag or metadata
            text_item.setData(0, "UWI_label")  # Key 0 with value "UWI_label"
            text_item.setData(1, UWI_times)   # Key 1 with UWI identifier
            self.scene.addItem(text_item)
            self.UWI_items[UWI_times] = text_item

        except Exception as e:
            print(f"Error adding text item for UWI {UWI_times}: {e}")

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
        if self.show_ticks:
            if not zone_ticks:
                print("No zone ticks provided.")
                return

            self.clearZones()
            self.zoneTicks = zone_ticks

            for item in self.scene.items():
                if isinstance(item, BulkZoneTicks):
                    self.scene.removeItem(item)

            # Create BulkZoneTicks object
            thick = self.line_width 
            bulk_ticks = BulkZoneTicks(zone_ticks, line_width=thick)
            bulk_ticks.setData(0, 'bulkzoneticks')
            bulk_ticks.setZValue(6)

            # Set opacity for the ticks (value between 0.0 and 1.0)
            bulk_ticks.setOpacity(1)  # Example: 50% opacity

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

            # Determine zoom factor based on scroll direction
            zoom_factor = zoom_in_factor if event.angleDelta().y() > 0 else zoom_out_factor

            # Convert event.position() to QPoint
            center_point = event.position().toPoint()

            # Pass the QPoint to the zoom method
            self.zoom(zoom_factor, center_point)
        else:
            # Scroll vertically if no ControlModifier is pressed
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - event.angleDelta().y())

    def zoom(self, zoom_factor, center_point):
        # Map the QPoint to scene coordinates
        old_pos = self.mapToScene(center_point)

        # Apply the scaling transformation
        self.scale(zoom_factor, zoom_factor)
        self.scale_factor *= zoom_factor

        # Map the center point after scaling
        new_pos = self.mapToScene(center_point)

        # Translate the view to maintain the focus
        delta = new_pos - old_pos
        self.translate(delta.x(), delta.y())

        # Update scroll bars or any other UI elements
        if hasattr(self.map_instance, 'updateScrollBars'):
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

    def updateHoveredUWI(self, UWI):
        self.hovered_UWI = UWI
        for item in self.scene.items():
            if isinstance(item, QGraphicsTextItem):
                if item.toPlainText() == UWI:
                    item.setFont(QFont("Arial", self.map_instance.UWI_width * 2, QFont.Bold))
                    item.setDefaultTextColor(QColor(255, 0, 0))
                else:
                    item.setFont(QFont("Arial", self.map_instance.UWI_width))
                    item.setDefaultTextColor(QColor(0, 0, 0, int(255 * self.map_instance.UWI_opacity)))
        self.scene.update()

    def updateUWIWidth(self, width):
        self.UWI_width = width
        for item in self.scene.items():
            if isinstance(item, QGraphicsTextItem):
                font = item.font()
                font.setPointSize(width)
                item.setFont(font)
        self.scene.update()



    def updateLineWidth(self, width):
        self.line_width = width
        for item in self.scene.items():
            if isinstance(item, QGraphicsLineItem) and item.data(0) == 'UWIline':
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
            if isinstance(item, QGraphicsLineItem) and item.data(0) == 'UWIline':
                pen = item.pen()
                color = pen.color()
                color.setAlphaF(opacity)
                pen.setColor(color)
                item.setPen(pen)
        self.scene.update()

    def resizeEvent(self, event):

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
        print("Clearing 'UWIline', tick data, and 'BulkZoneTicks' items from the scene.")

        # Remove 'UWIline' items
        UWIlines_to_remove = [item for item in self.scene.items() if item.data(0) == 'UWIline']
        for item in UWIlines_to_remove:
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

    #    for UWI, points in self.processed_data.items():
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


    def toggleTextItemsVisibility(self, visible):
        """Toggle the visibility of UWI text labels."""
        visible = (visible == Qt.Checked)  # Convert Qt state to boolean
        print(f"Toggling UWI visibility: {visible}")

        try:
            text_items = [item for item in self.scene.items() if item.data(0) == "UWI_label"]

            for item in text_items:
                item.setOpacity(self.UWI_opacity if visible else 0.0)

            self.scene.update()
            self.viewport().update()

        except Exception as e:
            print(f"Error toggling text item visibility: {e}")


    def togglegradientVisibility(self, visible):
        """Toggle the visibility of the drainage area."""
        self.drainage_visible = visible

        print(f"Toggling drainage visibility: {visible}")

        try:
            drainage_items = [item for item in self.scene.items() if item.data(0) == "drainage"]

            if not visible:
                # Hide drainage items
                for item in drainage_items:
                    item.setOpacity(0.0)
            else:
                #   If turning ON, ensure drainage is redrawn
                if not drainage_items:
                    print("  Redrawing drainage")
                    self.setScaledData(self.scaled_data)  #   Redraw well paths and drainage
                else:
                    for item in drainage_items:
                        item.setOpacity(1.0)  # Show existing drainage

            self.scene.update()
            self.viewport().update()

        except Exception as e:
            print(f"Error toggling drainage visibility: {e}")
   

   
    def setUWIOpacity(self, opacity):
        # Ensure opacity is within valid bounds (0.0 to 1.0)
        print(opacity)
        if not (0.0 <= opacity <= 1.0):
            print("Invalid opacity value. Must be between 0.0 and 1.0.")
            return
        text_items = [item for item in self.scene.items() if item.data(0) == "UWI_label"]
        # Store the new opacity value
        self.UWI_opacity = opacity
        for item in text_items:
            item.setOpacity(opacity)

  

        # Update the scene to reflect changes
        self.scene.update()

    #def toggleticksVisibility(self, visible, zone_ticks=None):
        

    #    if visible == 0:
    #        self.show_ticks = False
    #        # Clear tick lines
    #        tick_items = [item for item in self.scene.items() if item.data(0) == 'bulkzoneticks']
    #        for item in tick_items:
    #            if item.scene() is not None:
    #                self.scene.removeItem(item)
    #    else:
    #        self.show_ticks = True
    #        self.setZoneTicks(zone_ticks)

    def toggleticksVisibility(self, visible):
        print(f"🔄 toggleticksVisibility called with: {visible}")

        tick_items = [item for item in self.scene.items() if item.data(0) == 'bulkzoneticks']

        if visible == 0:
            print("❌ Hiding ticks")
            self.show_ticks = False
            for item in tick_items:
                item.setOpacity(0.0)
        else:
            print("Showing ticks")
            self.show_ticks = True
            for item in tick_items:
                item.setOpacity(0.5)  # Adjust this value for desired opacity

        print(f"🎯 After toggleticksVisibility: show_ticks={self.show_ticks}")
        self.scene.update()
        self.viewport().update()



    def get_point_by_md(self, UWI, md):
        if UWI not in self.scaled_data:
            return None
        for point, point_md in self.scaled_data[UWI]:
            if point_md >= md:
                return point
        return None

    def clearDrainageItems(self):
        for item in self.scene.items():
            if item.data(0) == 'drainage':  # Check if the item's data(0) is 'drainage'
                self.scene.removeItem(item)



    def clearUWILines(self):
        for item in self.scene.items():
            if item.data(0) == 'UWIline':
                if item.scene() is not None:
                    self.scene.removeItem(item)