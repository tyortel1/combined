import sys
import os
import numpy as np
import pandas as pd
import h5py
from scipy.spatial import KDTree
from scipy import interpolate
from scipy.interpolate import griddata
from scipy.ndimage import gaussian_filter
import matplotlib.pyplot as plt
from scipy.interpolate import interp1d
import numpy as np




# PySide6 Core, GUI, and Widgets
from PySide6.QtCore import Qt, Signal, QRectF, QUrl
from PySide6.QtGui import (
    QIcon, QColor, QPainter, QBrush, QPixmap, QPainterPath, 
    QTransform, QImage, QPen, qRgb
)
from PySide6.QtWidgets import (
    QApplication, QVBoxLayout, QSpacerItem, QSizePolicy, QHBoxLayout,
    QGraphicsDropShadowEffect, QPushButton, QSlider, QDialog, QLabel,
    QFrame, QMessageBox, QGraphicsView, QGraphicsScene, QGraphicsPixmapItem, QGraphicsBlurEffect, QGraphicsItemGroup
)

# Custom Styled UI Components
from StyledDropdown import StyledDropdown, StyledInputBox
from StyledColorbar import StyledColorBar
from StyledSliders import StyledSlider, StyledRangeSlider
from SeismicDatabaseManager import SeismicDatabaseManager  
from DatabaseManager import DatabaseManager


# SuperQt Extension
from superqt import QRangeSlider


class SeismicGraphicsView(QGraphicsView):
    seismic_range_changed = Signal(float, float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.scene_obj = QGraphicsScene(self)
        self.setScene(self.scene_obj)
        
        # Apply scaling **AFTER** setting the scene
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)
        self.scale(1, -1)  # Flip vertically AFTER setting up everything
        self.scene_obj.setBackgroundBrush(Qt.white)  
        
        # Store references to data and kdtree
        self.seismic_kdtree = None
        
        # Enable antialiasing and smooth transforms
        self.setRenderHints(QPainter.Antialiasing | 
                           QPainter.SmoothPixmapTransform |
                           QPainter.TextAntialiasing)
        
        # Setup view properties
        self.setViewportUpdateMode(QGraphicsView.FullViewportUpdate)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setFrameStyle(QFrame.NoFrame)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        
        # Initialize storage for items
        self.seismic_item = None
        self.well_path_item = None
        self.grid_lines = []
        self.zone_markers = []
        self.zone_fills = []
        self.seismic_kdtree = None
        self.seismic_data = None
        self.last_smoothed_data = None
        self.last_max_abs_value = None
        self.original_colors = None
        self.seismic_time_axis = None
        self.selected_attribute = None

        
        # Scale factors for coordinate transformation
        self.scale_x = 1.0
        self.scale_y = 1.0



    def update_seismic_data(self, seismic_data, seismic_distances, time_axis):
        """
        Update seismic data visualization using fully vectorized NumPy operations.
        Uses a simple linear interpolation approach for performance.
        """
        try:
            import numpy as np
        
            # Get color palette and normalize data
            color_palette = self.parent().seismic_colorbar.selected_color_palette
            max_abs_value = np.max(np.abs(seismic_data))
            if max_abs_value == 0:
                max_abs_value = 1.0  # Avoid division by zero
        
            self.parent().seismic_colorbar.display_color_range(-max_abs_value, max_abs_value)
        
            # Normalize seismic data to range [-1, 1]
            normalized_data = np.clip(seismic_data / max_abs_value, -1, 1)
        
            # Compute width and height
            min_x, max_x = min(seismic_distances), max(seismic_distances)
            width = int(max_x - min_x) + 1
            height = len(time_axis)
        
            # Create the target x coordinate grid (one for each pixel column)
            pixel_x_coords = np.arange(width)
        
            # Precompute x positions of traces relative to our display
            trace_x_coords = np.array(seismic_distances) - min_x
        
            # Simple linear interpolation using NumPy
            interpolated_data = np.zeros((height, width))
        
            # Interpolate each row of the seismic data
            for row in range(height):
                row_data = normalized_data[row, :]
                interpolated_data[row, :] = np.interp(pixel_x_coords, trace_x_coords, row_data)
        
            # Map interpolated values to color indices
            color_indices = ((interpolated_data + 1) / 2 * (len(color_palette) - 1)).astype(int)
            color_indices = np.clip(color_indices, 0, len(color_palette) - 1)
        
            # Convert color palette to NumPy array for fast lookup
            palette_array = np.array([[c.red(), c.green(), c.blue(), 255] for c in color_palette], dtype=np.uint8)
        
            # Create image data array using NumPy broadcasting
            image_data = palette_array[color_indices]
        
            # Flip vertically to display seismic data with time increasing downward
            image_data = np.flip(image_data, axis=0)
        
            # Make sure data is C-contiguous (required for QImage)
            image_data_contiguous = np.ascontiguousarray(image_data)
        
            # Convert NumPy array to QImage
            image = QImage(image_data_contiguous.data, width, height, width * 4, QImage.Format_RGBA8888)
        
            # Ensure the image data isn't garbage collected while the QImage uses it
            image.ndarray = image_data_contiguous
        
            # Convert to QPixmap for display
            pixmap = QPixmap.fromImage(image)
        
            # Add the pixmap to the scene
            pixmap_item = self.scene_obj.addPixmap(pixmap)
            pixmap_item.setPos(min_x, min(time_axis))
        
            # Scale to match the time axis range
            time_range = max(time_axis) - min(time_axis)
            scale_y = time_range / height
        
            transform = QTransform()
            transform.scale(1.0, scale_y)
            pixmap_item.setTransform(transform)
        
            # Store data for colorbar updates
            self.last_smoothed_data = interpolated_data
            self.last_max_abs_value = max_abs_value
        
            # Group management for efficient scene updates
            self.seismic_items = [pixmap_item]
            group = QGraphicsItemGroup()
            self.scene_obj.addItem(group)
            group.addToGroup(pixmap_item)
            self.seismic_item_group = group
            self.seismic_item_group.setZValue(0)
        
            # Store reference to the primary pixmap item for colorbar updates
            self.seismic_item = pixmap_item
        
        except Exception as e:
            print(f"Error updating seismic data: {e}")
            import traceback
            traceback.print_exc()

    def update_well_path(self, path_points):
        """Update well path display"""
        # Clear any existing well path items first
        if hasattr(self, 'well_path_item') and self.well_path_item:
            try:
                self.scene_obj.removeItem(self.well_path_item)
            except RuntimeError:
                # Item already deleted, just set to None
                pass
    
        self.well_path_item = None
    
        if not path_points:
            return
        
        path = QPainterPath()
        path.moveTo(path_points[0][0], path_points[0][1])
        for point in path_points[1:]:
            path.lineTo(point[0], point[1])
        
        pen = QPen(Qt.black, 2)
        self.well_path_item = self.scene_obj.addPath(path, pen)
        self.well_path_item.setZValue(2)  # Above seismic, below markers
        
    def add_zone_marker(self, position, tick_size, color='black'):
        """Add a vertical line as a zone marker, ensuring only height is affected by tick size."""
        x, y = position

        path = QPainterPath()
    
        # ✅ Adjust height but keep width constant
        path.moveTo(x, y - tick_size / 2)
        path.lineTo(x, y + tick_size / 2)
    
        pen = QPen(QColor(color), 2)  # ✅ Keep pen width constant (not fatter)
        marker = self.scene_obj.addPath(path, pen)

        marker.setZValue(9)  # ✅ Ensure it's above everything
        self.zone_markers.append(marker)


        
    def add_zone_fill(self, points, color, tick_size):
        """Add colored fill between zone markers with thickness matching tick size."""
        if len(points) < 2:
            return

     

        path = QPainterPath()

        # ✅ Make the fill rectangle match tick size in height
        path.moveTo(points[0][0], points[0][1] - tick_size / 2)
        path.lineTo(points[1][0], points[1][1] - tick_size / 2)
        path.lineTo(points[1][0], points[1][1] + tick_size / 2)
        path.lineTo(points[0][0], points[0][1] + tick_size / 2)
        path.closeSubpath()

        brush = QBrush(color, Qt.SolidPattern)
        fill_item = self.scene_obj.addPath(path, QPen(Qt.NoPen), brush)

        fill_item.setZValue(8)  # ✅ Ensure it's above well path
        fill_item.setOpacity(0.7)  # ✅ Keep visibility high
        self.zone_fills.append(fill_item)

   

        # ✅ Refresh scene
        self.scene_obj.update()
        self.viewport().update()



        
    def add_grid_line(self, points, color):
        """Add a grid line"""
        if len(points) < 2:
            return
            
        path = QPainterPath()
        path.moveTo(points[0][0], points[0][1])
        for point in points[1:]:
            path.lineTo(point[0], point[1])
            
        pen = QPen(QColor(*color), 1)
        line = self.scene_obj.addPath(path, pen)
        line.setZValue(1)  # Above seismic, below well path
        self.grid_lines.append(line)
        
    def clear_zone_items(self):
        """Clear all zone-related items"""
        for item in self.zone_markers + self.zone_fills:
            self.scene_obj.removeItem(item)
        self.zone_markers.clear()
        self.zone_fills.clear()
        
    def wheelEvent(self, event):
        """Handle zoom with mouse wheel"""
        zoom_factor = 1.15
        if event.angleDelta().y() < 0:
            zoom_factor = 1.0 / zoom_factor
            
        self.scale(zoom_factor, zoom_factor)
        
    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.fitHorizontally()
        self.updateTimingLines()

    def fitHorizontally(self):
        if self.scene().sceneRect().width() > 0:
            viewRect = self.viewport().rect()
            sceneRect = self.scene().sceneRect()

            scale_x = viewRect.width() / sceneRect.width()

            # Preserve the vertical flip by using self.transform().m22()
            scale_y = self.transform().m22()  # Get current vertical scale (-1 if flipped)

            self.setTransform(QTransform().scale(scale_x, scale_y))  # Keep vertical scale
            self.centerOn(sceneRect.center())


    def add_timing_lines(self, time_intervals, distance_intervals=None, color=(50, 50, 50)):
        """
        Add clear timing lines to the scene.
    
        Args:
            time_intervals: List of time values to mark with horizontal lines
            distance_intervals: Optional list of distance values to mark with vertical lines
            color: RGB tuple for line color
        """
        # Remove existing timing lines
        for line in getattr(self, 'timing_lines', []):
            try:
                self.scene_obj.removeItem(line)
            except:
                pass
        self.timing_lines = []
    
        # Early return if no seismic item
        if not hasattr(self, 'seismic_item') or self.seismic_item is None:
            return
    
        # Get scene dimensions
        scene_rect = self.scene_obj.sceneRect()
    
        # Get seismic data boundaries
        pixmap_rect = self.seismic_item.boundingRect()
        transform = self.seismic_item.transform()
        pos = self.seismic_item.pos()
    
        # Calculate actual seismic bounds in scene coordinates
        seismic_left = pos.x()
        seismic_right = seismic_left + pixmap_rect.width() * transform.m11()
        seismic_top = pos.y()
        seismic_bottom = seismic_top + pixmap_rect.height() * transform.m22()
    
        # Add horizontal time lines
        for time in time_intervals:
            # Calculate y coordinate for this time value
            y = seismic_top + (time - min(time_intervals)) * transform.m22() * pixmap_rect.height() / (max(time_intervals) - min(time_intervals))
        
            # Add line across the entire scene width
            line = self.scene_obj.addLine(
                scene_rect.left(), y, scene_rect.right(), y, 
                QPen(QColor(*color), 1)
            )
            line.setZValue(3)  # Above seismic
            self.timing_lines.append(line)
        
            # Add label that won't be upside down
            # Create a label with correct orientation
            text = f"{time:.0f}"
            label = self.scene_obj.addText(text)
            label.setPos(seismic_left - 40, y - 10)
        
            # For correctly oriented text, use a QGraphicsTextItem with a transform
            label.setTransform(QTransform().scale(1, -1))  # Flip text vertically
            label.setDefaultTextColor(QColor(*color))
            self.timing_lines.append(label)
    
        # Add vertical distance lines if provided
        if distance_intervals is not None:
            for distance in distance_intervals:
                # Calculate x coordinate for this distance value
                x = seismic_left + (distance - min(distance_intervals)) * transform.m11() * pixmap_rect.width() / (max(distance_intervals) - min(distance_intervals))
            
                # Add line from top to bottom of seismic
                line = self.scene_obj.addLine(
                    x, scene_rect.top(), x, scene_rect.bottom(), 
                    QPen(QColor(*color), 1, Qt.DashLine)
                )
                line.setZValue(3)
                self.timing_lines.append(line)
            
                # Add distance label
                text = f"{distance:.0f}"
                label = self.scene_obj.addText(text)
                label.setPos(x - 20, seismic_bottom + 10)
            
                # Fix orientation
                label.setTransform(QTransform().scale(1, -1))
                label.setDefaultTextColor(QColor(*color))
                self.timing_lines.append(label)

    def updateTimingLines(self):
        """Update timing lines based on current seismic data"""
        if not hasattr(self, 'seismic_time_axis') or self.seismic_time_axis is None:
            return
        
        # Calculate time intervals (10 divisions)
        time_min = min(self.seismic_time_axis)
        time_max = max(self.seismic_time_axis)
        time_step = (time_max - time_min) / 10
        time_intervals = np.linspace(time_min, time_max, 11)
    
        # Calculate distance intervals if available
        distance_intervals = None
        if hasattr(self, 'raw_distance_axis') and self.raw_distance_axis is not None:
            distance_min = min(self.raw_distance_axis)
            distance_max = max(self.raw_distance_axis)
            distance_step = (distance_max - distance_min) / 10
            distance_intervals = np.linspace(distance_min, distance_max, 11)
    
        # Add the timing lines
        self.add_timing_lines(time_intervals, distance_intervals)



    def mousePressEvent(self, event):
        if event.button() == Qt.MiddleButton:
            self.setDragMode(QGraphicsView.ScrollHandDrag)
            self.original_cursor = self.cursor()
            self.setCursor(Qt.ClosedHandCursor)
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MiddleButton:
            self.setDragMode(QGraphicsView.NoDrag)
            self.setCursor(self.original_cursor)
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def wheelEvent(self, event):
        if event.modifiers() == Qt.ControlModifier:
            # Zoom vertically only
            factor = 1.2
            if event.angleDelta().y() < 0:
                factor = 1.0 / factor

            # Get the scene point under the mouse
            mousePos = self.mapToScene(event.position().toPoint())

            # Calculate new vertical scale
            newTransform = self.transform()
            newTransform.scale(1, factor)

            # Set the new transformation
            self.setTransform(newTransform)

            # Adjust the view to keep the point under the mouse fixed
            newMousePos = self.mapToScene(event.position().toPoint())
            delta = newMousePos - mousePos
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() + delta.y())

        else:
            # Regular vertical scrolling
            delta = event.angleDelta().y()
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - delta)

        event.accept()

    def update_zones(self, zone_data, tick_size=20, color_map=None, min_val=None, max_val=None):
        """Update zone markers and fills, ensuring tick size applies to both."""
    
        # ✅ Clear old items properly
        self.clear_zone_items()
    
    

        for zone in zone_data:
            # ✅ Add top marker
            self.add_zone_marker(
                (zone['top_cum_dist'], zone['top_tvd']), 
                tick_size=tick_size
            )

            # ✅ Add colored zone fill
            if color_map and 'attribute_value' in zone:
                color = color_map(zone['attribute_value'], min_val, max_val)

                self.add_zone_fill(
                    [
                        (zone['top_cum_dist'], zone['top_tvd']), 
                        (zone['base_cum_dist'], zone['base_tvd'])
                    ],
                    QColor(color.red(), color.green(), color.blue()),
                    tick_size  # ✅ Ensuring fill matches tick size
                )

        # ✅ Force a refresh of the scene
        self.scene_obj.update()
        self.viewport().update()



        
    def add_grid_line(self, points, color):
        """Add a grid line"""
        if len(points) < 2:
            return
            
        path = QPainterPath()
        path.moveTo(points[0][0], points[0][1])
        for point in points[1:]:
            path.lineTo(point[0], point[1])
            
        pen = QPen(QColor(*color), 1)
        line = self.scene_obj.addPath(path, pen)
        line.setZValue(1)  # Above seismic, below well path
        self.grid_lines.append(line)
        
    def clear_zone_items(self):
        """Clear all zone-related items"""
        for item in self.zone_markers + self.zone_fills:
            if item:
                try:
                    self.scene_obj.removeItem(item)
                except RuntimeError:
                    pass  # Ignore already deleted items

        self.zone_markers.clear()
        self.zone_fills.clear()


class Plot(QDialog):
    closed = Signal()
    
    def __init__(self, UWI_list, directional_surveys_df, depth_grid_data_df, grid_info_df, kd_tree_depth_grids, current_UWI, depth_grid_data_dict, db_manager,seismic_db_manager, parent=None):
        super().__init__(parent)
        self.setWindowFlags(self.windowFlags() | Qt.WindowMinMaxButtonsHint | Qt.Window)

        self.main_app = parent
        self.UWI_list = UWI_list
        self.directional_surveys_df = directional_surveys_df
        self.depth_grid_data_df = depth_grid_data_df
        self.grid_info_df = grid_info_df
        self.kd_tree_depth_grids = kd_tree_depth_grids
        self.current_index = self.UWI_list.index(current_UWI)
        self.current_UWI = current_UWI
        self.depth_grid_data_dict = depth_grid_data_dict
        self.seismic_db_manager = seismic_db_manager
        self.db_manager = db_manager
        self.seismic_db_manager = seismic_db_manager
        self.current_well_data = pd.DataFrame()
        self.well_attribute_traces = {}
        self.well_seismic_indices = {}  
  
        self.zones = []
        self.combined_distances = []
            # Initialize seismic-related attributes
        self.seismic_data = None
        self.seismic_kdtree = None
        self.seismic_bounding_box = None
        self.current_hdf5_path =None
        self.intersecting_files = []




        self.attributes_names = []
        self.UWI_att_data = pd.DataFrame()
        self.selected_zone_df = pd.DataFrame()
        
        self.selected_attribute = None
        self.min_attr = 0
        self.max_attr = 1
        self.selected_zone = None
        self.tick_size_value = 20

      

        self.next_well = False
        
     


        self.current_well_data = self.directional_surveys_df[
        self.directional_surveys_df['UWI'] == self.current_UWI].reset_index(drop=True)
        well_coords = np.column_stack((
            self.current_well_data['X Offset'],
            self.current_well_data['Y Offset']
                ))

        self.intersecting_files = self.get_intersecting_seismic_files(well_coords)
       
        self.plot_widget = SeismicGraphicsView()  # New custom QGraphicsView
        self.plot_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)




        self.init_ui()



    def closeEvent(self, event):
        self.closed.emit()
        event.accept()

    def init_ui(self):
        labels = [
            "Well",
            "Zone",
            "Attribute",
            "Color Bar",
            "Tick Size",
            "Display",
            "Heat",
            "Tick Size",
            "Transparency",
            "Seismic"
            
        ]
        StyledDropdown.calculate_label_width(labels)

        self.setStyleSheet("""
                QDialog {
                    background-color: white;
                }
                QLabel {
                    color: black;
                }
                QPushButton {
                    background-color: white;
                    border: none;
                }
            """)




        # Create main layout first
        main_layout = QHBoxLayout(self)  # Parent to self immediately

        # Control Layout setup
        control_layout = QVBoxLayout()
    
        # Create and populate frames
        wellFrame, wellLayout = self.create_section("Well Navigation", fixed_height=90)
        self.setup_well_section(wellFrame, wellLayout)
    
        seismicFrame, seismicLayout = self.create_section("Seismic Display", fixed_height=270)
        self.setup_seismic_section(seismicFrame, seismicLayout)
    
        zoneFrame, zoneLayout = self.create_section("Zone and Attribute", fixed_height=170)
        self.setup_zone_section(zoneFrame, zoneLayout)
    
        tickFrame, tickLayout = self.create_section("Tick Settings", fixed_height=150)  # Increased height for transparency
        self.setup_tick_section(tickFrame, tickLayout)
    
        # Add frames to control layout
        control_layout.addWidget(wellFrame)
        control_layout.addWidget(seismicFrame)
        control_layout.addWidget(zoneFrame)
        control_layout.addWidget(tickFrame)
        control_layout.addStretch()

        # Plot Layout setup
        plot_layout = QVBoxLayout()
        plot_layout.addWidget(self.plot_widget)

        # Add layouts to main layout
        main_layout.addLayout(control_layout, stretch=1)
        main_layout.addLayout(plot_layout, stretch=7)

        # Set up connections
        self.setup_connections()

        # Initial population
        self.populate_zone_names()

        # Trigger well selection for the initial well
        self.on_well_selected(self.current_index)

    def create_section(self, frame_name, fixed_height=None):
        """
        Create a framed section with optional fixed height
    
        Args:
            frame_name (str): Name or description of the section
            fixed_height (int, optional): Fixed height for the section
    
        Returns:
            tuple: (QFrame, QVBoxLayout)
        """
        frame = QFrame()
        frame.setFrameStyle(QFrame.Panel | QFrame.Raised)
        frame.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 2px solid #A0A0A0;
                border-radius: 6px;
                padding: 4px;
            }
        """)
    
        if fixed_height:
            frame.setFixedHeight(fixed_height)
            frame.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)

        # Add drop shadow effect
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(10)
        shadow.setXOffset(3)
        shadow.setYOffset(3)
        shadow.setColor(QColor(0, 0, 0, 100))
        frame.setGraphicsEffect(shadow)

        # Create layout
        layout = QVBoxLayout(frame)
        layout.setSpacing(1)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setAlignment(Qt.AlignTop)
    
        return frame, layout



    def setup_well_section(self, frame, layout):
            # Well Selector setup
        self.well_selector = self.create_dropdown("Well")
        self.well_selector.addItems(self.UWI_list)
        current_index = self.UWI_list.index(self.current_UWI)
        self.well_selector.setCurrentIndex(current_index)
    
        # Navigation buttons setup
        button_layout = QHBoxLayout()
    
        self.prev_button = QPushButton()
        self.next_button = QPushButton()
    
        # Set up icons
        prev_icon = QIcon(os.path.join(os.path.dirname(__file__), 'Icons', 'arrow_left.ico'))
        next_icon = QIcon(os.path.join(os.path.dirname(__file__), 'Icons', 'arrow_right.ico'))
    
        self.prev_button.setIcon(prev_icon)
        self.next_button.setIcon(next_icon)
    
        self.prev_button.setFixedSize(40, 40)
        self.next_button.setFixedSize(40, 40)
    
        # Add to button layout with spacers
        spacer_20 = QSpacerItem(0, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)
        spacer_40 = QSpacerItem(0, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)
    
        button_layout.addItem(spacer_20)
        button_layout.addWidget(self.prev_button)
        button_layout.addItem(spacer_40)
        button_layout.addWidget(self.next_button)
        button_layout.addStretch()
    
        # Add to well layout
        layout.addWidget(self.well_selector)
        layout.addLayout(button_layout)

    def setup_zone_section(self, frame, layout):
        self.zone_selector = self.create_dropdown("Zone")
        self.zone_attribute_selector = self.create_dropdown("Attribute")
        self.color_colorbar = self.create_colorbar()
    
        layout.addWidget(self.zone_selector)
        layout.addWidget(self.zone_attribute_selector)
        layout.addWidget(self.color_colorbar)
        
        self.zone_attribute_selector.combo.setEnabled(False)


    def create_dropdown(self, label):
        dropdown = StyledDropdown(label)
        dropdown.setStyleSheet("""
            QLabel, QComboBox {
                background-color: transparent;
                border: none;
                padding: 0;
                margin: 0;
            }
        """)
        return dropdown



    def create_input(self, label, default_value='', validator=None):
        input_box = StyledInputBox(label, default_value, validator)
        input_box.label.setFixedWidth(StyledDropdown.label_width)  # Use the same width
        input_box.setStyleSheet("""
            QLabel {
                background-color: transparent;
                border: none;
                padding: 0;
                margin: 0;
            }
        """)
        return input_box

    def create_colorbar(self):
        colorbar = StyledColorBar("Color Bar")  # Make sure to pass the label text
        colorbar.colorbar_dropdown.label.setFixedWidth(StyledDropdown.label_width)  # Use the calculated width
    
        # Apply consistent styling
        colorbar.setStyleSheet("""
            QLabel {
                background-color: transparent;
                border: none;
                padding: 0;
                margin: 0;
            }
        """)
        return colorbar

    def create_slider(self, label_text, slider_type='single'):
        """
        Create a styled slider with consistent appearance
    
        Args:
            label_text (str): Label for the slider
            slider_type (str): 'single' for regular slider, 'range' for range slider
    
        Returns:
            StyledSlider or StyledRangeSlider: Configured slider
        """
        if slider_type == 'single':
            slider = StyledSlider(label_text)
        elif slider_type == 'range':
            slider = StyledRangeSlider(label_text)
        else:
            raise ValueError("slider_type must be 'single' or 'range'")
    
        # Set consistent label width
        slider.label.setFixedWidth(StyledDropdown.label_width)
    
        # Apply consistent styling
        slider.setStyleSheet("""
            QLabel {
                background-color: transparent;
                border: none;
                padding: 0;
                margin: 0;
            }
        """)
    
        return slider


    def setup_seismic_section(self, frame, layout):
        # Create seismic selector first
        self.seismic_selector = self.create_dropdown("Seismic")
        layout.addWidget(self.seismic_selector)

        # Create attribute selector (initially disabled)
        self.seismic_attribute_selector = self.create_dropdown("Attribute")
        self.seismic_attribute_selector.combo.setEnabled(False)
        layout.addWidget(self.seismic_attribute_selector)

        # Colorbar for seismic
        self.seismic_colorbar = self.create_colorbar()
        layout.addWidget(self.seismic_colorbar)


        # Display Range section
        display_range_layout = QHBoxLayout()

        # Placeholder range slider
        self.seismic_range_slider = self.create_slider("Display", slider_type='range')
        display_range_layout.addWidget(self.seismic_range_slider)
        layout.addLayout(display_range_layout)

        # Heat Clipping section
        heat_layout = QHBoxLayout()
        self.heat_slider = self.create_slider("Heat", slider_type='single')
        heat_layout.addWidget(self.heat_slider)
        layout.addLayout(heat_layout)

        # Connect seismic selector to attribute population
        self.seismic_selector.combo.currentTextChanged.connect(self.populate_seismic_attributes)







    def get_intersecting_seismic_files(self, well_coords):

        """Check which seismic volumes intersect with well coordinates"""
        intersecting_files = []
    
        try:
            # Get all seismic file info from database
            seismic_files = self.seismic_db_manager.get_all_seismic_files()
        
            # Get min/max coordinates of well path
            well_x_min = np.min(well_coords[:, 0])
            well_x_max = np.max(well_coords[:, 0])
            well_y_min = np.min(well_coords[:, 1])
            well_y_max = np.max(well_coords[:, 1])
        
            for file_info in seismic_files:
                # Check if well path intersects seismic volume bounding box
                if (well_x_min <= file_info['geometry']['x_max'] and 
                    well_x_max >= file_info['geometry']['x_min'] and 
                    well_y_min <= file_info['geometry']['y_max'] and 
                    well_y_max >= file_info['geometry']['y_min']):
                    intersecting_files.append(file_info)
                
            
            return intersecting_files

        
        except Exception as e:
            print(f"Error checking seismic intersections: {e}")
            return []


    def populate_seismic_attributes(self, seismic_name):
        """
        Populate attribute dropdown based on selected seismic volume
        """
        # Block signals to prevent triggering change events
        self.seismic_attribute_selector.combo.blockSignals(True)
    
        # Clear previous attributes
        self.seismic_attribute_selector.combo.clear()
        self.seismic_attribute_selector.combo.setEnabled(False)
    
        # If no seismic name selected, return
        if not seismic_name or seismic_name == "Select Seismic":
            # Unblock signals before returning
            self.seismic_attribute_selector.combo.blockSignals(False)
            return
    
        try:
            # Get seismic file info from database
            seismic_file = self.seismic_db_manager.get_seismic_file_info(name=seismic_name)
    
            if not seismic_file:
                print(f"No seismic file found for {seismic_name}")
                # Unblock signals before returning
                self.seismic_attribute_selector.combo.blockSignals(False)
                return
        
            # Get attributes from the 'attributes' key
            attributes = seismic_file.get('attributes', [])
    
            if attributes:
                # Extract just the attribute names
                attribute_names = [attr['name'] for attr in attributes]
        
                # Populate dropdown
                self.seismic_attribute_selector.combo.addItems(attribute_names)
                if self.seismic_attribute_selector.combo.count() > 0:
                    self.seismic_attribute_selector.combo.setCurrentIndex(0)
                self.seismic_attribute_selector.combo.setEnabled(True)
            else:
                # No attributes found
                self.seismic_attribute_selector.combo.addItem("No attributes found")
                self.seismic_attribute_selector.combo.setEnabled(False)
    
        except Exception as e:
            print(f"Error populating seismic attributes: {e}")
            self.seismic_attribute_selector.combo.addItem("Error loading attributes")
            self.seismic_attribute_selector.combo.setEnabled(False)
    
        # Unblock signals when finished
        self.seismic_attribute_selector.combo.blockSignals(False)



    def on_attribute_changed(self, attribute_name):
        """
        Handle attribute change and replot the well
        """
        # Set the selected attribute
        self.selected_attribute = attribute_name
    
        try:
            # Verify the current UWI exists in the well_attribute_traces
            if self.current_UWI not in self.well_attribute_traces:
                print(f"⚠️ Current UWI {self.current_UWI} not found in well_attribute_traces")
                self.plot_current_well()
                return
            
            # Verify the attribute exists for this well
            if attribute_name not in self.well_attribute_traces[self.current_UWI]:
                print(f"⚠️ Attribute '{attribute_name}' not found for well {self.current_UWI}")
                self.plot_current_well()
                return
            
            # Retrieve preprocessed data
            selected_data = self.well_attribute_traces[self.current_UWI][attribute_name]
        
            # Verify all required keys exist in the selected data
            required_keys = ['seismic_data', 'unique_distances', 'unique_times']
            missing_keys = [key for key in required_keys if key not in selected_data]
        
            if missing_keys:
                print(f"⚠️ Missing required data keys: {missing_keys}")
                self.plot_current_well()
                return
            
            # Verify data dimensions match
            if len(selected_data['unique_distances']) == 0:
                print(f"⚠️ No distance data available for {attribute_name}")
                self.plot_current_well()
                return
            
            if len(selected_data['unique_times']) == 0:
                print(f"⚠️ No time data available for {attribute_name}")
                self.plot_current_well()
                return
            
            # Check if seismic_data has the right shape
            expected_shape = (len(selected_data['unique_times']), len(selected_data['unique_distances']))
            actual_shape = selected_data['seismic_data'].shape if hasattr(selected_data['seismic_data'], 'shape') else None
        
            if actual_shape != expected_shape:
                print(f"⚠️ Data shape mismatch: expected {expected_shape}, got {actual_shape}")
                self.plot_current_well()
                return
            
            # Plot the data
            self.plot_widget.update_seismic_data(
                selected_data['seismic_data'],
                selected_data['unique_distances'],
                selected_data['unique_times']
            )
        except Exception as e:
            print(f"❌ Error in on_attribute_changed: {e}")
            import traceback
            traceback.print_exc()
            self.plot_current_well()

    def setup_tick_section(self, frame, layout):
        # Existing tick size controls
        tick_slider_layout = QHBoxLayout()
    
        # Tick Size slider
        self.tick_size_slider = self.create_slider("Tick Size", slider_type='single')
        self.tick_size_slider.setRange(5, 50)
        self.tick_size_slider.setValue(20)

        # Add tick position and interval if needed
        self.tick_size_slider.slider.setTickPosition(QSlider.TicksBelow)
        self.tick_size_slider.slider.setTickInterval(4)

        tick_slider_layout.addWidget(self.tick_size_slider)

        layout.addLayout(tick_slider_layout)

        # Transparency slider section
        transparency_layout = QHBoxLayout()

        self.transparency_slider = self.create_slider("Transparency", slider_type='single')
        self.transparency_slider.setRange(0, 100)
        self.transparency_slider.setValue(100)

        transparency_layout.addWidget(self.transparency_slider)
        layout.addLayout(transparency_layout)


    def setup_connections(self):
        self.well_selector.combo.currentIndexChanged.connect(self.on_well_selected)
        self.prev_button.clicked.connect(self.on_prev)
        self.next_button.clicked.connect(self.on_next)
        self.zone_selector.combo.currentIndexChanged.connect(self.zone_selected)
        self.zone_attribute_selector.combo.currentIndexChanged.connect(self.attribute_selected)
        self.color_colorbar.colorbar_dropdown.combo.currentIndexChanged.connect(self.palette_selected)
        self.seismic_selector.combo.currentIndexChanged.connect(self.on_seismic_selected)
        self.seismic_attribute_selector.combo.currentTextChanged.connect(self.on_attribute_changed)
    
        # Corrected connections for sliders
        self.tick_size_slider.slider.valueChanged.connect(self.update_tick_size_value_label)
        self.seismic_range_slider.slider.valueChanged.connect(
            lambda values: self.seismic_range_slider._update_value_labels(values)
        )
        # Do the heavy pixel updates only on release
        self.seismic_range_slider.slider.sliderReleased.connect(
            lambda: self.update_seismic_range(*self.seismic_range_slider.value())
        )
        self.heat_slider.slider.valueChanged.connect(
            lambda value: self.heat_slider._update_value_label(value)
        )

        # Apply heavy update only when slider is released
        self.heat_slider.slider.sliderReleased.connect(
            lambda: self.update_heat_value(self.heat_slider.value())
)
        self.transparency_slider.slider.valueChanged.connect(self.update_transparency_value)
        self.seismic_colorbar.colorbar_dropdown.combo.currentIndexChanged.connect(self.update_seismic_colorbar)

    def update_seismic_colorbar(self):
        """
        Update the seismic display colorbar using optimized NumPy operations.
        Modified to support both heat value adjustments and range-based transparency.
        """
        self.seismic_colorbar.color_selected()

        # Early returns if requirements aren't met
        if not all(hasattr(self.plot_widget, attr) for attr in 
                   ['seismic_item', 'last_smoothed_data', 'last_max_abs_value']):
            return
        if self.plot_widget.seismic_item is None:
            return

        color_palette = self.seismic_colorbar.selected_color_palette
        if not color_palette:
            return

        try:
            import numpy as np
    
            # Get the raw data (already normalized to [-1, 1] range)
            smoothed_data = self.plot_widget.last_smoothed_data
            max_abs_value = self.plot_widget.last_max_abs_value
    
            # Check if we're using heat adjustment or range filtering
            using_heat = hasattr(self.plot_widget, 'using_heat_adjustment') and self.plot_widget.using_heat_adjustment
            using_range = hasattr(self.plot_widget, 'using_range_filter') and self.plot_widget.using_range_filter
    
            # Convert normalized data back to original units
            original_units = smoothed_data * max_abs_value
        
            # Default alpha mask - all visible
            alpha_mask = np.full_like(original_units, 255, dtype=np.uint8)
        
            if using_heat or using_range:
                # Get adjusted range
                adjusted_min = self.plot_widget.heat_adjusted_min
                adjusted_max = self.plot_widget.heat_adjusted_max
        
                # Map values to [0, 1] range based on adjusted min/max
                mapped_values = np.zeros_like(original_units)
        
                # Handle values in range
                in_range = (original_units >= adjusted_min) & (original_units <= adjusted_max)
                range_size = adjusted_max - adjusted_min
            
                if range_size > 0 and np.any(in_range):
                    mapped_values[in_range] = (original_units[in_range] - adjusted_min) / range_size
        
                # Handle values outside range
                mapped_values[original_units < adjusted_min] = 0
                mapped_values[original_units > adjusted_max] = 1
            
                # If using range filter, set alpha to 0 (transparent) for out-of-range values
                if using_range:
                    alpha_mask[~in_range] = 0
        
                # Map to color indices
                color_indices = (mapped_values * (len(color_palette) - 1)).astype(int)
            else:
                # Normal colorbar update - direct mapping from normalized data
                color_indices = ((smoothed_data + 1) / 2 * (len(color_palette) - 1)).astype(int)
        
            # Ensure indices are in valid range
            color_indices = np.clip(color_indices, 0, len(color_palette) - 1)

            # Create color array using NumPy for better performance
            height, width = smoothed_data.shape

            # Convert palette to NumPy array for faster operations
            palette_array = np.array([
                [color.red(), color.green(), color.blue(), 255] 
                for color in color_palette
            ], dtype=np.uint8)

            # Use palette lookup with NumPy broadcasting (much faster than loops)
            image_data = palette_array[color_indices]
        
            # Apply alpha mask for transparency
            image_data[:, :, 3] = alpha_mask

            # Flip the data to match the original orientation
            image_data = np.flip(image_data, axis=0)

            # Ensure contiguous memory layout
            image_data_contiguous = np.ascontiguousarray(image_data)

            # Create QImage directly from the array
            image = QImage(
                image_data_contiguous.data, 
                width, height, 
                width * 4, 
                QImage.Format_RGBA8888
            )

            # Retain reference to prevent garbage collection
            image.ndarray = image_data_contiguous

            # Update the pixmap
            self.plot_widget.seismic_item.setPixmap(QPixmap.fromImage(image))

        except Exception as e:
            print(f"Error updating seismic colorbar: {e}")
            import traceback
            traceback.print_exc()

    def update_seismic_range(self, min_val, max_val):
        """
        Update seismic range by setting range filter parameters and calling the colorbar update.
        Values outside the range will be transparent.
        """
        try:
            # Early returns if requirements aren't met
            if not all(hasattr(self.plot_widget, attr) for attr in 
                    ['seismic_item', 'last_smoothed_data', 'last_max_abs_value']):
                return
            if self.plot_widget.seismic_item is None:
                return
        
            # Store range parameters that the colorbar update will use
            self.plot_widget.heat_adjusted_min = min_val
            self.plot_widget.heat_adjusted_max = max_val
            self.plot_widget.using_heat_adjustment = False  # Not using heat adjustment
            self.plot_widget.using_range_filter = True     # Using range filter with transparency
        
            # Call the existing colorbar update to refresh the visualization
            self.update_seismic_colorbar()
        
            # Reset the temporary flag
            self.plot_widget.using_range_filter = False
        
        except Exception as e:
            print(f"Error updating seismic range: {e}")
            import traceback
            traceback.print_exc()



    def update_seismic_selector(self):
        try:
            # Block signals to prevent premature triggers
            self.seismic_selector.blockSignals(True)
            self.seismic_selector.combo.clear()  # Use .combo to clear
        
            # Reset seismic-related attributes
            self.seismic_data = None
            self.seismic_kdtree = None
        
            # Get well coordinates
            well_coords = np.column_stack((
                self.current_well_data['X Offset'],
                self.current_well_data['Y Offset']
            ))
        
            # Find intersecting seismic files
            intersecting_files = self.get_intersecting_seismic_files(well_coords)
            print(intersecting_files)
        
            # Process intersecting files
            for file_info in intersecting_files:
                # Use the database name field for display
                display_name = file_info.get('name', 'Unknown')
                self.seismic_selector.combo.addItem(display_name)
        
            # Automatically select first file if available
            if self.seismic_selector.combo.count() > 0:
                self.seismic_selector.combo.setCurrentIndex(0)
            
                # Trigger attribute population for the first selected seismic volume
                first_seismic_name = self.seismic_selector.combo.currentText()
                self.populate_seismic_attributes(first_seismic_name)
    
        except Exception as e:
            print(f"Error updating seismic selector: {e}")
            import traceback
            traceback.print_exc()
    
        finally:
            self.seismic_selector.blockSignals(False)



    def update_tick_size_value_label(self):
        value = self.tick_size_slider.value()
        # The value label is now handled internally by the StyledSlider

    def update_transparency_value(self):
        value = self.transparency_slider.value()
    
        if hasattr(self, 'plot_widget'):
            opacity = value / 100.0  # Convert percentage to decimal
            for zone_fill in self.plot_widget.zone_fills:
                zone_fill.setOpacity(opacity)


    def update_heat_value(self, value):
        """
        Update heat value by adapting the working colorbar update method.
        Adjusts how data is mapped to colors based on heat value.
        """
        # Early returns if requirements aren't met
        if not all(hasattr(self.plot_widget, attr) for attr in 
                   ['seismic_item', 'last_smoothed_data', 'last_max_abs_value']):
            return
        if self.plot_widget.seismic_item is None:
            return

        color_palette = self.seismic_colorbar.selected_color_palette
        if not color_palette:
            return

        try:
            import numpy as np
        
            # Get the original data
            smoothed_data = self.plot_widget.last_smoothed_data
            max_abs_value = self.plot_widget.last_max_abs_value
        
            # Calculate adjusted range based on heat value
            heat_factor = max(0.05, 1 - (value / 100))
            adjusted_min = -max_abs_value * heat_factor
            adjusted_max = max_abs_value * heat_factor
        
            # Update display range indicators
            self.seismic_colorbar.display_color_range(adjusted_min, adjusted_max)
            if hasattr(self, 'seismic_range_slider'):
                self.seismic_range_slider.setRange(adjusted_min, adjusted_max)
                self.seismic_range_slider.setValue([adjusted_min, adjusted_max])
        
            # Get image dimensions
            height, width = smoothed_data.shape
        
            # Instead of directly using normalized data, we'll map it to colors
            # based on the adjusted range
        
            # Start with data in [-1, 1] range (already normalized)
            # First convert to original units
            original_units = smoothed_data * max_abs_value
        
            # Calculate color indices based on adjusted range
            # Values below min get first color (0)
            # Values above max get last color (palette_length - 1)
            # Values in range get proportionally mapped
        
            # Map to [0, 1] range for color mapping
            mapped_values = np.zeros_like(original_units)
        
            # Handle values in range
            in_range = (original_units >= adjusted_min) & (original_units <= adjusted_max)
            if np.any(in_range):
                mapped_values[in_range] = (original_units[in_range] - adjusted_min) / (adjusted_max - adjusted_min)
        
            # Handle values outside range
            mapped_values[original_units < adjusted_min] = 0
            mapped_values[original_units > adjusted_max] = 1
        
            # Map to color palette indices
            color_indices = (mapped_values * (len(color_palette) - 1)).astype(int)
            color_indices = np.clip(color_indices, 0, len(color_palette) - 1)
        
            # Convert palette to NumPy array for faster operations
            palette_array = np.array([
                [color.red(), color.green(), color.blue(), 255] 
                for color in color_palette
            ], dtype=np.uint8)
        
            # Use palette lookup with NumPy broadcasting
            image_data = palette_array[color_indices]
        
            # Flip the data to match the original orientation
            image_data = np.flip(image_data, axis=0)
        
            # Ensure contiguous memory layout
            image_data_contiguous = np.ascontiguousarray(image_data)
        
            # Create QImage directly from the array
            image = QImage(
                image_data_contiguous.data, 
                width, height, 
                width * 4, 
                QImage.Format_RGBA8888
            )
        
            # Retain reference to prevent garbage collection
            image.ndarray = image_data_contiguous
        
            # Update the pixmap
            self.plot_widget.seismic_item.setPixmap(QPixmap.fromImage(image))
        
        except Exception as e:
            print(f"Error updating heat value: {e}")
            import traceback
            traceback.print_exc()

    def palette_selected(self):
        """Update zone ticks when a new color palette is selected"""
        if not self.next_well:
            # If a zone is already selected, update the zone ticks with the new color palette
            if self.selected_zone and self.selected_zone != "Select_Zone":
                self.update_zone_ticks()

    def attribute_selected(self):
        """Handle attribute selection for zone visualization"""
        if self.next_well:
            return

        # Get the current attribute selection
        attribute = self.zone_attribute_selector.currentText()

        # Early return if no valid attribute is selected
        if attribute == "Select Zone Attribute" or not attribute:
            return

        try:
            # Safety check for selected zone and zone data
            if not self.selected_zone or self.selected_zone == "Select_Zone" or self.selected_zone_df is None:
                print("No valid zone selected")
                return

            # Filter the zone data for the current UWI
            zone_data = self.selected_zone_df[self.selected_zone_df['UWI'] == self.current_UWI].copy()

            if zone_data.empty:
                print(f"No zone data found for UWI {self.current_UWI}")
                return

            # Ensure the selected attribute exists in the data
            if attribute not in zone_data.columns:
                print(f"Attribute {attribute} not found in zone data")
                return

            # Update color range for the colorbar
            self.min_attr = zone_data[attribute].min()
            self.max_attr = zone_data[attribute].max()
            self.color_colorbar.display_color_range(self.min_attr, self.max_attr)

            # Recreate zone ticks with color mapped to the selected attribute
            self.update_zone_ticks()

        except Exception as e:
            print(f"Error updating attribute display: {e}")
            import traceback
            traceback.print_exc()

    def change_tick_size_from_input(self):
     
        new_size = int(self.tick_size_input.text())
         
        self.tick_size_value = new_size
        if self.next_well == False:
            self.plot_current_well()






    def populate_zone_names(self):

        
        self.zone_selector.blockSignals(True)
        # Clear existing items
        self.zone_selector.clear()

        # Add default option
        self.zone_selector.addItem("Select Zone")

        try:
            # Fetch unique zone names from the database where type is 'Well'
            zones = self.db_manager.fetch_zone_names_by_type("Zone")

            if zones:
                # Sort zones alphabetically
                zones = [zone[0] for zone in zones if zone[0].strip()] 
                zones = sorted(zones)
             

                # Populate the dropdown with sorted zone names
                self.zone_selector.addItems(zones)
            else:
                print("No zones of type 'Well' found.")

        except Exception as e:
            print(f"Error populating Well Zone dropdown: {e}")

        finally:
            # Unblock signals after populating the dropdown
            self.zone_selector.blockSignals(False)
            self.zone_attribute_selector.combo.setEnabled(True)



    def populate_zone_attribute(self):
        """Update the zone attribute selector based on the selected zone filter and add a default 'Select Zone Attribute' option."""
        self.zone_attribute_selector.blockSignals(True)
        self.zone_attribute_selector.setEnabled(True)

        zone_df = self.selected_zone_df
      
        columns = self.selected_zone_df.columns.tolist() 

        # Columns to exclude
        columns_to_exclude = [
            'id', 'Zone_Name', 'Zone_Type', 'Attribute_Type',
            'Top_Depth', 'Base_Depth', 'UWI', 'Top_X_Offset',
            'Base_X_Offset', 'Top_Y_Offset', 'Base_Y_Offset',
            'Angle_Top', 'Angle_Base', 'Base_TVD', 'Top_TVD'
        ]

        # Drop fixed columns and find columns with at least one non-null value
        zone_df = zone_df.drop(columns=columns_to_exclude, errors='ignore')
        self.attributes_names = sorted(zone_df.columns[zone_df.notna().any()].tolist())
      
        # Find attributes (columns with at least one non-null value)
 
    
        # Clear and populate the attribute selector
        self.zone_attribute_selector.clear()
        self.zone_attribute_selector.addItem("Select Zone Attribute")
        self.zone_attribute_selector.addItems(self.attributes_names)
    
        # Set default selection to the first item (e.g., "Select Zone Attribute")
        self.zone_attribute_selector.setCurrentIndex(0)
        self.zone_attribute_selector.blockSignals(False)


    def populate_seismic_selector(self):
        try:
            self.seismic_selector.blockSignals(True)
            self.seismic_selector.clear()
        
            if not self.intersecting_files:
                print("No intersecting seismic files found.")
                return
            
            for file_info in self.intersecting_files:
                # Use database name field instead of extracting from path
                display_name = file_info.get('name', 'Unknown')
                self.seismic_selector.addItem(display_name)
            
            if self.seismic_selector.count() > 0:
                self.seismic_selector.setCurrentIndex(0)
                # Manually trigger the selection of the first item
                self.on_seismic_selected(0)

            
        except Exception as e:
            print(f"Unexpected error in populate_seismic_selector: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self.seismic_selector.blockSignals(False)

    def on_seismic_selected(self, index):
        try:
            # Get the selected seismic name from the combo box
            selected_display_name = self.seismic_selector.combo.currentText()
            if not selected_display_name:
                print("No seismic selected")
                return
        
            print(f"Selected display name: {selected_display_name}")
        
            # Get file info by name
            file_info = self.seismic_db_manager.get_seismic_file_info(name=selected_display_name)
            print(f"File info: {file_info}")
        
            if not file_info:
                print(f"Could not find seismic data info for: {selected_display_name}")
                return
        
            # Extract HDF5 path
            hdf5_path = file_info.get('hdf5_path')
            print(f"HDF5 path from file_info: {hdf5_path}")
        
            if not hdf5_path:
                print("No HDF5 path found in file info")
                return
        
            # Verify file exists
            if not os.path.exists(hdf5_path):
                print(f"HDF5 file does not exist at path: {hdf5_path}")
                return
        
            # Explicitly set the HDF5 path
            self.current_hdf5_path = hdf5_path
            print(f"Set self.current_hdf5_path to: {self.current_hdf5_path}")
        
            # Update the visualization
            self.populate_seismic_attributes(selected_display_name)
            self.plot_current_well()
        
        except Exception as e:
            print(f"Error in on_seismic_selected: {e}")
            import traceback
            traceback.print_exc()
            






    def plot_current_well(self):
        """Find the closest seismic trace for each well point, store it, and interpolate the data."""
        try:
            # Clear scene before replotting
            if self.plot_widget.scene_obj.items():
                self.plot_widget.scene_obj.clear()

            # ✅ Step 1: Load Well Data
            self.current_well_data = self.directional_surveys_df[
                self.directional_surveys_df['UWI'] == self.current_UWI
            ].reset_index(drop=True)
            print(self.current_well_data)

            if self.current_well_data.empty:
                print(f"⚠ No well data found for UWI: {self.current_UWI}")
                return

            # ✅ Extract well coordinates and cumulative distances
            well_coords = np.column_stack((self.current_well_data['X Offset'], self.current_well_data['Y Offset']))
            self.tvd_values = self.current_well_data['TVD'].tolist()
            self.combined_distances = np.array(self.current_well_data['Cumulative Distance'])

            # ✅ Step 2: Verify HDF5 Path
            if not self.current_hdf5_path or not os.path.exists(self.current_hdf5_path):
                print("❌ ERROR: HDF5 file does not exist or is invalid!")
                return
            self.selected_attribute = self.seismic_attribute_selector.combo.currentText()
            # ✅ Step 3: Open HDF5 File and Check Contents
            # ✅ Step 3: Open HDF5 File and Check Contents
            with h5py.File(self.current_hdf5_path, 'r') as f:
                # Check if 'attributes' group exists
                if 'attributes' not in f:
                    print("❌ ERROR: 'attributes' group not found in HDF5 file!")
                    return

                # Get all available attributes
                all_attributes = list(f['attributes'].keys())
    
                # Get the selected attribute from the dropdown
                self.selected_attribute = self.seismic_attribute_selector.combo.currentText()

                # Verify the selected attribute exists
                if self.selected_attribute not in f['attributes']:
                    print(f"❌ ERROR: Attribute '{self.selected_attribute}' not found in HDF5 file!")
                    return

                # Ensure well_attribute_traces is initialized
                if not hasattr(self, 'well_attribute_traces'):
                    self.well_attribute_traces = {}
    
                if self.current_UWI not in self.well_attribute_traces:
                    self.well_attribute_traces[self.current_UWI] = {}

                # Load geometry datasets once
                time_axis = f['geometry']['time_axis'][:]
                x_coords = f['geometry']['x_coords'][:]
                y_coords = f['geometry']['y_coords'][:]

                # Create KDTree once
                if 'kdtree' in f['geometry']:
                    kdtree_data = f['geometry']['kdtree']['data'][:]
                    leafsize = f['geometry']['kdtree'].attrs.get('leafsize', 16)
                    seismic_kdtree = KDTree(kdtree_data, leafsize=leafsize)
                else:
                    # Fallback to creating a new KDTree if not found
                    seismic_coords = np.column_stack((x_coords, y_coords))
                    seismic_kdtree = KDTree(seismic_coords)

                # Iterate through all attributes and store traces
                for attribute in all_attributes:
                    # Get the attribute group
                    attribute_group = f['attributes'][attribute]
        
                    # Load trace data
                    trace_data = attribute_group['trace_data'][:]

                    distances, indices = seismic_kdtree.query(well_coords)

                    # Print inline, crossline, and distance for each well point
                    if 'inlines' in f['geometry'] and 'crosslines' in f['geometry']:
                        inline_numbers = f['geometry']['inlines'][:]
                        crossline_numbers = f['geometry']['crosslines'][:]
    
                    if attribute == all_attributes[0]:
                        for i, (idx, dist) in enumerate(zip(indices, distances)):
                            print(f"Well point {i}: MD position {self.current_well_data['MD'].iloc[i]:.2f}, "
                                  f"Cumulative distance {self.combined_distances[i]:.2f}, "
                                  f"Nearest trace at inline {inline_numbers[idx]}, crossline {crossline_numbers[idx]}, "
                                  f"distance: {dist:.2f}")


                    # Ensure indices are valid
                    max_index = trace_data.shape[0] - 1
                    indices = np.clip(indices, 0, max_index)

                    # Read Seismic Traces
                    seismic_trace_amplitudes = []
                    for idx in indices:
                        try:
                            trace = trace_data[idx, :]
                            seismic_trace_amplitudes.append(trace)
                        except Exception as e:
                            print(f"❌ ERROR: Failed to load trace for attribute {attribute}, index {idx}: {e}")

                    # Convert to numpy array
                    seismic_trace_amplitudes = np.array(seismic_trace_amplitudes)

                    # Store traces for this attribute
                    self.well_attribute_traces[self.current_UWI][attribute] = seismic_trace_amplitudes

                # Proceed with plotting the selected attribute
                # Use the stored traces for the selected attribute
                seismic_trace_amplitudes = self.well_attribute_traces[self.current_UWI][self.selected_attribute]


                trace_inline_numbers = inline_numbers[indices]
                trace_crossline_numbers = crossline_numbers[indices]

                # Create seismic section and print info about which trace goes where
                seismic_section = np.zeros((len(time_axis), len(self.combined_distances)))
                print("\nChecking which trace is assigned to each cumulative distance:")
                for i in range(len(self.combined_distances)):
                    seismic_section[:, i] = seismic_trace_amplitudes[i]
    
                    # Print every 10th point or points around where traces should change
                    if i % 10 == 0 or (i > 40 and i < 60) or (i > 150 and i < 170):
                        print(f"Cumulative distance {self.combined_distances[i]:.2f}: Using trace from inline {trace_inline_numbers[i]}, crossline {trace_crossline_numbers[i]}")
        
                        # Optional: Check if adjacent traces are identical
                        if i > 0:
                            traces_equal = np.array_equal(seismic_trace_amplitudes[i], seismic_trace_amplitudes[i-1])
                            print(f"  Trace at position {i} same as previous trace? {traces_equal}")

                # Save raw data for later reference
                self.raw_seismic_section = seismic_section
                self.raw_time_axis = time_axis
                self.raw_distance_axis = self.combined_distances
                print(self.raw_distance_axis)


                prev_trace = None
                for i, (inline, crossline) in enumerate(zip(trace_inline_numbers, trace_crossline_numbers)):
                    current_trace = (inline, crossline)
                    if prev_trace is not None and current_trace != prev_trace:
                        # Add a vertical line at this position
                        line = self.plot_widget.scene_obj.addLine(
                            self.combined_distances[i], min(time_axis),
                            self.combined_distances[i], max(time_axis),
                            QPen(Qt.red, 2)
                        )
                        line.setZValue(3)  # Above everything else
                    prev_trace = current_trace



                # ✅ Step 9: Pass the raw data directly to the plot widget
                # The plotting widget will handle interpolation during rendering
                self.plot_widget.update_seismic_data(
                    self.raw_seismic_section,  # Original traces (time × distance)
                    self.raw_distance_axis,    # Actual measured distances along wellbore
                    self.raw_time_axis         # Time axis
                )

                # Store data for timing lines
                self.plot_widget.seismic_time_axis = self.raw_time_axis
                self.plot_widget.raw_distance_axis = self.combined_distances

                # Update timing lines
                self.plot_widget.updateTimingLines()

            # ✅ Step 14: Process Grid Intersections
            print("🔍 Processing grid intersections...")
            grid_values = {}
            sorted_grids = sorted(self.kd_tree_depth_grids.keys())

            for grid_name in sorted_grids:
                kdtree = self.kd_tree_depth_grids[grid_name]
                grid_values[grid_name] = []

                for x2, y2 in well_coords:
                    if kdtree.data.size > 0:
                        _, indices = kdtree.query((x2, y2))
                        if indices < len(self.depth_grid_data_dict[grid_name]):
                            grid_values[grid_name].append(self.depth_grid_data_dict[grid_name][indices])

            # ✅ Step 15: Plot Grids and Fills
            for i, grid_name in enumerate(sorted_grids):
                try:
                    grid_row = self.grid_info_df.loc[self.grid_info_df['Grid'] == grid_name]
                    if grid_row.empty:
                        continue

                    current_color = grid_row['Color (RGB)'].values[0]
                    current_points = list(zip(self.combined_distances, grid_values[grid_name]))

                    # Draw grid line
                    self.plot_widget.add_grid_line(current_points, current_color)

                    # Add fill between this grid and the next
                    if i < len(sorted_grids) - 1:
                        next_grid_name = sorted_grids[i + 1]
                        next_points = list(zip(self.combined_distances, grid_values[next_grid_name]))

                        path = QPainterPath()
                        path.moveTo(current_points[0][0], current_points[0][1])

                        for point in current_points:
                            path.lineTo(point[0], point[1])

                        for point in reversed(next_points):
                            path.lineTo(point[0], point[1])

                        path.lineTo(current_points[0][0], current_points[0][1])

                        # Apply transparency to the fill
                        color = QColor(*current_color)
                        color.setAlpha(76)  # 30% opacity
                        fill_item = self.plot_widget.scene_obj.addPath(
                            path, QPen(Qt.NoPen), QBrush(color)
                        )
                        fill_item.setZValue(0)

                except Exception as e:
                    print(f"❌ Error processing grid {grid_name}: {e}")

            # ✅ Step 16: Plot Well Path Last
            path_points = list(zip(self.combined_distances, self.tvd_values))
            self.plot_widget.update_well_path(path_points)

            print("✅ Well plotting complete!")

        except Exception as e:
            print(f"❌ CRITICAL ERROR: {e}")
            import traceback
            traceback.print_exc()


    def update_tick_size_value_label(self, value):
        """Update tick size without reloading the entire plot"""
        self.tick_size_value = max(2, min(self.tick_size_slider.value(), 20))
        self.tick_size_value = value
    
        # If a zone is selected, update the ticks with new size
        if self.selected_zone and self.selected_zone != "Select_Zone":
            self.update_zone_ticks()







    def update_zone_ticks(self):
        """Update zone ticks in the SeismicGraphicsView"""
        if not self.selected_zone or self.selected_zone == "Select_Zone":
            return

        try:
            # Prepare zone data for SeismicGraphicsView
            zone_data = []
            for _, zone_row in self.selected_zone_df[
                self.selected_zone_df['UWI'] == self.current_UWI
            ].iterrows():
                try:
                    top_md = zone_row['Top_Depth']
                    base_md = zone_row['Base_Depth']

                    top_cum_dist = self.interpolate_value(top_md, 'Cumulative Distance')
                    base_cum_dist = self.interpolate_value(base_md, 'Cumulative Distance')
                    top_tvd = self.interpolate_value(top_md, 'TVD')
                    base_tvd = self.interpolate_value(base_md, 'TVD')

                    if all(v is not None for v in [top_cum_dist, base_cum_dist, top_tvd, base_tvd]):
                        zone_entry = {
                            'top_cum_dist': top_cum_dist,
                            'base_cum_dist': base_cum_dist,
                            'top_tvd': top_tvd,
                            'base_tvd': base_tvd
                        }

                        # Add attribute value if selected
                        attribute = self.zone_attribute_selector.currentText()
                        if attribute != "Select Zone Attribute" and attribute in zone_row:
                            zone_entry['attribute_value'] = zone_row[attribute]

                        zone_data.append(zone_entry)

                except Exception as e:
                    print(f"Error processing zone row: {e}")
                    continue

            # Get the selected color palette from colorbar
            color_palette = self.color_colorbar.selected_color_palette

            # Ensure color_palette is valid before passing it
            if not color_palette:
                print("⚠️ No color palette selected, defaulting to grayscale.")
                color_palette = [QColor(i, i, i) for i in range(256)]  # Example grayscale fallback

            # Fix: Use a lambda function to pass color_palette explicitly
            color_map = None
            if self.zone_attribute_selector.currentText() != "Select Zone Attribute":
                color_map = lambda value, min_val, max_val: self.color_colorbar.map_value_to_color(
                    value, min_val, max_val, color_palette
                )

            # Update zones in SeismicGraphicsView
            self.plot_widget.update_zones(
                zone_data, 
                tick_size=self.tick_size_value,
                color_map=color_map,
                min_val=self.min_attr,
                max_val=self.max_attr
            )

        except Exception as e:
            print(f"Error in update_zone_ticks: {e}")
            import traceback
            traceback.print_exc()



    def update_color_range(self):
        """Update the color range display and refresh the plot based on the selected palette from StyledColorBar."""
        self.palette_name = self.color_colorbar.colorbar_dropdown.currentText()
    
        # Update the color range display
        self.color_colorbar.display_color_range(self.min_attr, self.max_attr)

        # Force a replot to apply new colors
        self.plot_current_well()







    def zone_selected(self):
        print("zone_selected() was triggered!")  # Debugging

        selected_text = self.zone_selector.currentText()
        if not selected_text:  
            print("Empty zone selection")
            return

        self.selected_zone = selected_text.replace(" ", "_")
 

        self.zone_attribute_selector.clear()
        self.zone_attribute_selector.addItem("Select Zone Attribute")

        if self.selected_zone == "Select_Zone":
            self.selected_zone_df = None
            self.attributes_names = []
        else:
            try:
                # Fetch zone data
                self.selected_zone_df = self.db_manager.fetch_table_data(self.selected_zone)
                

                # Update zone ticks and attributes
                self.update_zone_ticks()
                self.populate_zone_attribute()

                # ✅ Update the **existing** plot widget instead of creating a new one
                if self.plot_widget:
                    self.plot_widget.update()  # Force UI refresh
                    self.plot_widget.repaint()
        
            except Exception as e:
                print(f"Error fetching zone data: {str(e)}")
                self.selected_zone_df = None

        

    def on_well_selected(self, index):
        try:
            selected_UWI = self.well_selector.currentText()
            if selected_UWI in self.UWI_list:
                self.current_UWI = selected_UWI
                self.current_index = index
            
                # Only plot the current well's seismic and grid data
                self.populate_seismic_selector()
       
            
                # Optionally add zone ticks if a zone is selected
                if self.selected_zone and self.selected_zone != "Select_Zone":
                    self.update_zone_ticks()
            else:
                print(f"Selected UWI {selected_UWI} not found in UWI list.")
        except Exception as e:
            print(f"Error in on_well_selected: {e}")

    def on_next(self):
        """Navigate to the next well in alphabetical order, wrapping if needed."""
        try:
            self.current_index = (self.current_index + 1) % len(self.UWI_list)
            self.current_UWI = self.UWI_list[self.current_index]
            self.update_well_selector_to_current_UWI()
            self.plot_current_well()
            if self.selected_zone and self.selected_zone != "Select_Zone":
                self.update_zone_ticks()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"An error occurred while processing the next well: {str(e)}")

    def on_prev(self):
        """Navigate to the previous well in alphabetical order, stopping at the first well."""
        try:
            if self.current_index > 0:
                self.current_index -= 1
                self.current_UWI = self.UWI_list[self.current_index]
                self.update_well_selector_to_current_UWI()
                self.plot_current_well()
                if self.selected_zone and self.selected_zone != "Select_Zone":
                    self.update_zone_ticks()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"An error occurred while processing the previous well: {str(e)}")



    def update_well_selector_to_current_UWI(self):
        """Set the dropdown to the current UWI."""
        try:
            current_index = self.UWI_list.index(self.current_UWI)
            self.well_selector.blockSignals(True)
            self.well_selector.setCurrentIndex(current_index)
            self.well_selector.blockSignals(False)
        except ValueError:
            QMessageBox.critical(self, "Error", f"UWI '{self.current_UWI}' not found in the list.")




    def update_well_related_data(self):
        # Re-populate dropdowns and plots based on the newly selected UWI
        self.populate_zone_names()
        self.zone_selected()  # This triggers zone filtering and replotting based on the new UWI

        # Update the plot
        self.plot_current_well()

    def update_plot(self, grid_info_df):
        self.grid_info_df = grid_info_df
        self.plot_current_well()

    def receive_UWI(self):
      
        self.main_app.handle_hover_event(self.current_UWI)

    def interpolate_value(self, md, column):
        # Check if MD is within the range of our data
        if md < self.current_well_data['MD'].min():
      
            return self.current_well_data[column].iloc[0]
        elif md > self.current_well_data['MD'].max():
           
            return self.current_well_data[column].iloc[-1]

        # Find the indices where MD falls between
        idx = np.searchsorted(self.current_well_data['MD'].values, md)

        # Handle the case where md exactly matches the last MD in the data
        if idx == len(self.current_well_data):
            return self.current_well_data[column].iloc[-1]

        # Get the bounding values
        md_lower = self.current_well_data['MD'].iloc[idx-1]
        md_upper = self.current_well_data['MD'].iloc[idx]
        val_lower = self.current_well_data[column].iloc[idx-1]
        val_upper = self.current_well_data[column].iloc[idx]

        # Interpolate
        fraction = (md - md_lower) / (md_upper - md_lower)
        interpolated_val = val_lower + fraction * (val_upper - val_lower)

        return interpolated_val


    def show_error_message(self, message):
        """Display an error message box."""
        QMessageBox.critical(self, "Error", message)




if __name__ == '__main__':
    app = QApplication(sys.argv)

    # Sample directional_surveys_df
    data = {
        'UWI': ['well1', 'well1', 'well2', 'well2', 'well3', 'well3'],
        'MD': [0, 100, 0, 100, 0, 100],  # Added proper MD values
        'TVD': [200, 250, 250, 300, 300, 350],
        'X Offset': [0, 50, 0, 50, 0, 50],
        'Y Offset': [0, 25, 0, 25, 0, 25],
        'Cumulative Distance': [100, 150, 150, 200, 200, 250],
    }
    directional_surveys_df = pd.DataFrame(data)

    # Create sample seismic data
    seismic_time = np.linspace(0, 1000, 200)  # 200 time samples
    seismic_distance = np.linspace(0, 300, 150)  # 150 distance samples
    time_grid, dist_grid = np.meshgrid(seismic_time, seismic_distance)
    
    # Create synthetic seismic data with some features
    seismic_data = {
        'trace_data': np.sin(time_grid/100) * np.cos(dist_grid/50),
        'time_axis': seismic_time,
        'distance_axis': seismic_distance
    }

    # Create synthetic coordinates for seismic data
    seismic_coords = np.array([(x, y) for x in np.linspace(0, 100, 20) 
                              for y in np.linspace(0, 100, 20)])
    seismic_kdtree = KDTree(seismic_coords)

    # Sample depth_grid_data_df for testing
    depth_grid_data = {
        'Grid': ['Grid1', 'Grid1', 'Grid2', 'Grid2'],
        'X': [0, 100, 0, 100],
        'Y': [0, 0, 100, 100],
        'Z': [200, 250, 300, 350]
    }
    depth_grid_data_df = pd.DataFrame(depth_grid_data)

    # Sample grid_info_df for testing
    grid_info_data = {
        'Grid': ['Grid1', 'Grid2'],
        'Type': ['Depth', 'Depth'],
        'min_x': [0, 0],
        'max_x': [100, 100],
        'min_y': [0, 0],
        'max_y': [100, 100],
        'min_z': [200, 300],
        'max_z': [250, 350],
        'bin_size_x': [10, 10],
        'bin_size_y': [10, 10],
        'Color (RGB)': [(255, 0, 0), (0, 255, 0)]
    }
    grid_info_df = pd.DataFrame(grid_info_data)

    # Create depth grid data dictionary
    depth_grid_data_dict = {}
    for grid in grid_info_df['Grid'].unique():
        grid_df = depth_grid_data_df[depth_grid_data_df['Grid'] == grid]
        points = list(zip(grid_df['X'], grid_df['Y']))
        depth_grid_data_dict[grid] = points

    # Create KD-Trees for each grid
    kd_tree_depth_grids = {
        grid: KDTree(depth_grid_data_df[depth_grid_data_df['Grid'] == grid][['X', 'Y']].values)
        for grid in depth_grid_data_df['Grid'].unique()
    }

    # Create a mock database manager
    class MockDBManager:
        def fetch_zone_names_by_type(self, zone_type):
            return [("Zone1",), ("Zone2",)]
        
        def fetch_table_data(self, zone_name):
            return pd.DataFrame({
                'UWI': ['well1', 'well2', 'well3'],
                'Top_Depth': [50, 150, 250],
                'Base_Depth': [100, 200, 300],
                'Top_TVD': [220, 270, 320],
                'Base_TVD': [250, 300, 350],
                'Attribute1': [0.5, 0.7, 0.9]
            })

    db_manager = MockDBManager()

    # Create and show the window
    window = Plot(
        UWI_list=['well1', 'well2', 'well3'],
        directional_surveys_df=directional_surveys_df,
        depth_grid_data_df=depth_grid_data_df,
        grid_info_df=grid_info_df,
        kd_tree_depth_grids=kd_tree_depth_grids,
        current_UWI='well1',
        depth_grid_data_dict=depth_grid_data_dict,
        master_df=None,
        seismic_data=seismic_data,
        seismic_kdtree=seismic_kdtree,
        db_manager=db_manager
    )
    
    window.show()
    sys.exit(app.exec_())