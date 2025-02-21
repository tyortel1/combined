import sys
import os

from PySide6.QtGui import QPainterPath, QTransform
from PySide6.QtGui import QIcon,  QColor, QPainter, QBrush, QPixmap, QPainterPath, QTransform
from PySide6.QtWidgets import (
    QApplication, QVBoxLayout,QSpacerItem,QSizePolicy, QHBoxLayout,QGraphicsDropShadowEffect, QPushButton, QSlider, 
   QDialog, QSizePolicy, QLabel, QFrame, QMessageBox
)
import numpy as np
from scipy.spatial import KDTree
from scipy import interpolate
from scipy.ndimage import gaussian_filter  #
import pandas as pd
import numpy as np
from scipy.spatial import KDTree
from PySide6.QtCore import Signal,  Qt, QRectF
from PySide6.QtCore import QUrl
from StyledDropdown import StyledDropdown, StyledInputBox
from StyledColorbar import StyledColorBar 

from PySide6.QtWidgets import QGraphicsView, QGraphicsScene, QFrame
from PySide6.QtCore import Qt
from PySide6.QtGui import (QPainter, QColor, QImage, QPen, 
                          QBrush, QPainterPath)
import numpy as np

class SeismicGraphicsView(QGraphicsView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.scene_obj = QGraphicsScene(self)
        self.setScene(self.scene_obj)
        
        # Apply scaling **AFTER** setting the scene
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)
        self.scale(1, -1)  # Flip vertically AFTER setting up everything
        
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
        
        # Scale factors for coordinate transformation
        self.scale_x = 1.0
        self.scale_y = 1.0

    def set_seismic_kdtree(self, kdtree, seismic_data):
        """Set the KDTree for seismic data"""
        self.seismic_kdtree = kdtree
        self.seiscmi_data = seismic_data

    def update_seismic_data(self, seismic_data, well_coords, combined_distances, time_axis, grid_start, grid_end):
        if self.seismic_item:
            self.scene_obj.removeItem(self.seismic_item)

        if seismic_data is None or self.seismic_kdtree is None:
            print("DEBUG: seismic_data or kdtree is None")
            return

        try:
            distances, indices = self.seismic_kdtree.query(well_coords)
            print("KDTree indices range:", indices.min(), "to", indices.max())

            # Add distance-based filtering
            max_distance = 100  # Maximum distance in same units as your coordinates
            valid_traces = distances <= max_distance
            indices = indices[valid_traces]
            filtered_distances = distances[valid_traces]

            seismic_trace_amplitudes = self.seismic_data['trace_data'][indices, :]

            # Vectorized construction of seismic data
            seismic_time_axis = np.tile(self.seismic_data['time_axis'], len(combined_distances))
            seismic_amplitude_flattened = seismic_trace_amplitudes.flatten()

            UWI_seismic_data = np.column_stack((
                np.repeat(well_coords[:, 0], len(self.seismic_data['time_axis'])),
                np.repeat(well_coords[:, 1], len(self.seismic_data['time_axis'])),
                np.repeat(combined_distances, len(self.seismic_data['time_axis'])),
                seismic_time_axis,
                seismic_amplitude_flattened
            ))

            seismic_df = pd.DataFrame(UWI_seismic_data, columns=['x', 'y', 'cumulative_distance', 'time', 'amplitude'])
            seismic_df = seismic_df.drop_duplicates(subset=['time', 'cumulative_distance'])
            seismic_df = seismic_df.sort_values(['cumulative_distance', 'time'])

            # Create a regular grid for interpolation
            unique_distances = np.linspace(grid_start, grid_end, num=500)
            unique_times = np.sort(seismic_df['time'].unique())
            grid_distances, grid_times = np.meshgrid(unique_distances, unique_times)

            # Perform 2D interpolation
            points = seismic_df[['cumulative_distance', 'time']].values
            values = seismic_df['amplitude'].values
            interpolated_data = interpolate.griddata(points, values, (grid_distances, grid_times), method='cubic', fill_value=0)

            # Apply Gaussian smoothing
            smoothed_data = gaussian_filter(interpolated_data, sigma=(5, 2))  # Adjust sigma as needed

            # Normalize the smoothed data
            normalized = (smoothed_data - np.min(smoothed_data)) / (np.max(smoothed_data) - np.min(smoothed_data))

            # Create image
            height, width = normalized.shape
            image = QImage(width, height, QImage.Format_RGB32)

            for i in range(height):
                for j in range(width):
                    value = int(255 * normalized[i, j])
                    if value > 127:
                        r = 255
                        g = b = int(255 * (1 - (value - 128) / 127))
                    else:
                        b = 255
                        r = g = int(255 * value / 127)
                    image.setPixelColor(j, i, QColor(r, g, b))

            pixmap = QPixmap.fromImage(image)

            # Create and position the seismic item
            self.seismic_item = self.scene_obj.addPixmap(pixmap)
            self.seismic_item.setZValue(0)

            # Set position and scale
            min_distance = grid_start
            max_distance = grid_end
            min_time = min(time_axis)
            max_time = max(time_axis)
            self.seismic_item.setPos(min_distance, min_time)

            distance_range = max_distance - min_distance
            time_range = max_time - min_time

            scale_x = distance_range / width
            scale_y = time_range / height
            self.seismic_item.setScale(scale_x)
            self.seismic_item.setTransform(QTransform().scale(1, scale_y / scale_x), True)

            # Add timing lines
            time_step = time_range / 10  # 10 intervals
            time_intervals = np.arange(min_time, max_time, time_step)
            self.add_timing_lines(time_intervals)

            print(f"Seismic position: ({min_distance}, {min_time})")
            print(f"Scale factors: x={scale_x}, y={scale_y}")
            print(f"Distance range: {distance_range}")
            print(f"Time range: {time_range}")

        except Exception as e:
            print(f"Error updating seismic data: {e}")
            import traceback
            traceback.print_exc()
    
    def load_seismic_data(self, well_coords, cumulative_distances, seismic_kdtree, seismic_data):
        self.seismic_data = seismic_data
        """
        Load and process seismic data for the current well path
    
        Args:
            well_coords (np.ndarray): X and Y coordinates of well path
            cumulative_distances (np.ndarray): Cumulative distances along well path
            seismic_kdtree (KDTree): KD-Tree of seismic coordinates
    
        Returns:
            dict: Processed seismic data with trace_data, time_axis, and distance_axis
        """
        if seismic_data is None:
            print("No seismic data available")
            return None

        try:
            # Print debug information
            print("Seismic data shape:", self.seismic_data['trace_data'].shape if 'trace_data' in self.seismic_data else "No trace_data found")
            print("Time axis length:", len(self.seismic_data['time_axis']) if 'time_axis' in self.seismic_data else "No time_axis found")

            print("Well coordinates shape:", well_coords.shape)
            print("Well X range:", well_coords[:, 0].min(), "to", well_coords[:, 0].max())
            print("Well Y range:", well_coords[:, 1].min(), "to", well_coords[:, 1].max())

            # Use the provided seismic_kdtree for querying
            print("First few seismic coordinates from KDTree:")
            print(seismic_kdtree.data[:5])
            print("\nSeismic coordinate ranges:")
            print("X range:", seismic_kdtree.data[:, 0].min(), "to", seismic_kdtree.data[:, 0].max())
            print("Y range:", seismic_kdtree.data[:, 1].min(), "to", seismic_kdtree.data[:, 1].max())

            # Batch query for all well path points to find nearest seismic traces
            distances, indices = seismic_kdtree.query(well_coords)
            print("KDTree indices range:", indices.min(), "to", indices.max())

            # Add distance-based filtering
            max_distance = 100  # Maximum distance in same units as your coordinates
            valid_traces = distances <= max_distance
            indices = indices[valid_traces]
            filtered_distances = distances[valid_traces]

            seismic_trace_amplitudes = self.seismic_data['trace_data'][indices, :]

            # Vectorized construction of seismic data
            seismic_time_axis = np.tile(self.seismic_data['time_axis'], len(cumulative_distances))
            seismic_amplitude_flattened = seismic_trace_amplitudes.flatten()

            UWI_seismic_data = np.column_stack((
                np.repeat(well_coords[:, 0], len(self.seismic_data['time_axis'])),
                np.repeat(well_coords[:, 1], len(self.seismic_data['time_axis'])),
                np.repeat(cumulative_distances, len(self.seismic_data['time_axis'])),
                seismic_time_axis,
                seismic_amplitude_flattened
            ))

            seismic_df = pd.DataFrame(UWI_seismic_data, columns=['x', 'y', 'cumulative_distance', 'time', 'amplitude'])
            seismic_df = seismic_df.drop_duplicates(subset=['time', 'cumulative_distance'])
            seismic_df = seismic_df.sort_values(['cumulative_distance', 'time'])

            # Create a regular grid for interpolation
            unique_distances = np.linspace(seismic_df['cumulative_distance'].min(),
                                           seismic_df['cumulative_distance'].max(),
                                           num=500)
            unique_times = np.sort(seismic_df['time'].unique())
            grid_distances, grid_times = np.meshgrid(unique_distances, unique_times)

            # Perform 2D interpolation
            points = seismic_df[['cumulative_distance', 'time']].values
            values = seismic_df['amplitude'].values
            interpolated_data = interpolate.griddata(points, values, (grid_distances, grid_times), method='cubic', fill_value=0)

            # Apply Gaussian smoothing
            smoothed_data = gaussian_filter(interpolated_data, sigma=(5, 2))  # Adjust sigma as needed

            # Create a new DataFrame with the smoothed data
            smoothed_df = pd.DataFrame({
                'cumulative_distance': grid_distances.flatten(),
                'time': grid_times.flatten(),
                'amplitude': smoothed_data.flatten()
            })

            seismic_data = smoothed_df.pivot(index='time', columns='cumulative_distance', values='amplitude').values
            seismic_distances = unique_distances
            seismic_time_axis = unique_times[::-1]  # Reverse the time axis if needed

            max_amplitude = np.max(np.abs(seismic_data))

            return {
                'trace_data': seismic_data,
                'time_axis': seismic_time_axis,
                'distance_axis': seismic_distances
            }

        except Exception as e:
            print(f"Error processing seismic data: {e}")
            import traceback
            traceback.print_exc()
            return None

    def add_timing_lines(self, time_intervals, color=(200, 200, 200)):
        # Remove existing timing lines
        for line in getattr(self, 'timing_lines', []):
            self.scene_obj.removeItem(line)
        self.timing_lines = []

        if not self.seismic_item:
            return

        seismic_rect = self.seismic_item.boundingRect()
        seismic_pos = self.seismic_item.pos()
        start_x = seismic_pos.x()
        end_x = start_x + seismic_rect.width() * self.seismic_item.scale()

        for time in time_intervals:
            y = seismic_pos.y() + time * self.seismic_item.transform().m22()
            line = self.scene_obj.addLine(start_x, y, end_x, y, QPen(QColor(*color)))
            line.setZValue(1)  # Above seismic, below well path
            self.timing_lines.append(line)

            # Add time label
            label = self.scene_obj.addText(f"{time:.0f}")
            label.setPos(start_x - 40, y - 10)  # Adjust position as needed
            label.setDefaultTextColor(QColor(*color))
            self.timing_lines.append(label)


    def updateTimingLines(self):
        """Update timing lines dynamically when tick size or zoom changes."""
        if not hasattr(self, 'seismic_item') or self.seismic_item is None:
            return

        # ✅ Clear existing timing lines before adding new ones
        for line in getattr(self, 'timing_lines', []):
            self.scene_obj.removeItem(line)
        self.timing_lines = []

        # ✅ Calculate timing intervals based on seismic data
        time_step = (max(self.seismic_data['time_axis']) - min(self.seismic_data['time_axis'])) / 10
        time_intervals = np.arange(min(self.seismic_data['time_axis']), max(self.seismic_data['time_axis']), time_step)

        # ✅ Refresh timing lines
        seismic_rect = self.seismic_item.boundingRect()
        seismic_pos = self.seismic_item.pos()
        start_x = seismic_pos.x()
        end_x = start_x + seismic_rect.width() * self.seismic_item.scale()

        for time in time_intervals:
            y = seismic_pos.y() + time * self.seismic_item.transform().m22()

            # ✅ Darker color for visibility
            line = self.scene_obj.addLine(start_x, y, end_x, y, QPen(QColor(100, 100, 100), 1))
            line.setZValue(2)  # Ensure it's visible above seismic but below well path
            self.timing_lines.append(line)

            # ✅ Add time label
            label = self.scene_obj.addText(f"{time:.0f}")
            label.setPos(start_x - 40, y - 10)  # Adjust position
            label.setDefaultTextColor(QColor(200, 200, 200))  # Lighter but visible text
            self.timing_lines.append(label)

        print("✅ Timing Lines Updated")

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

        print(f"🟡 Adding Zone Fill from {points[0]} to {points[1]} with color RGB({color.red()}, {color.green()}, {color.blue()})")

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

        print(f"✔️ Zone fill added with tick size: {tick_size} | Opacity: {fill_item.opacity()} | ZValue: {fill_item.zValue()}")

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


    def add_timing_lines(self, time_intervals, color=(50, 50, 50)):  # Darker gray or black
        """Add dark timing lines to the scene."""
        # Remove existing timing lines
        for line in getattr(self, 'timing_lines', []):
            self.scene_obj.removeItem(line)
        self.timing_lines = []

        if not self.seismic_item:
            return

        seismic_rect = self.seismic_item.boundingRect()
        seismic_pos = self.seismic_item.pos()
        start_x = seismic_pos.x()
        end_x = start_x + seismic_rect.width() * self.seismic_item.scale()

        for time in time_intervals:
            y = seismic_pos.y() + time * self.seismic_item.transform().m22()

            # ✅ Darker timing line
            line = self.scene_obj.addLine(start_x, y, end_x, y, QPen(QColor(*color), 1.5))  # Thicker & darker
            line.setZValue(2)  # Above seismic data

            self.timing_lines.append(line)

            # ✅ Darker text labels for timing lines
            label = self.scene_obj.addText(f"{time:.0f}")
            label.setPos(start_x - 40, y - 10)
            label.setDefaultTextColor(QColor(*color))
            self.timing_lines.append(label)

        print("Updated timing lines with darker color.")


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
    
        print('Updating zones...')

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
    
    def __init__(self, UWI_list, directional_surveys_df, depth_grid_data_df, grid_info_df, kd_tree_depth_grids, current_UWI, depth_grid_data_dict, master_df,seismic_data,seismic_kdtree,db_manager, parent=None):
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
        self.seismic_data = seismic_data
        self.master_df = master_df
        self.seismic_kdtree = seismic_kdtree
        self.zones =[]
        self.combined_distances = []
        print(seismic_data)
        print(seismic_kdtree)
        print("Seismic data shape:", self.seismic_data['trace_data'].shape if 'trace_data' in self.seismic_data else "No trace_data found")
    


        self.attributes_names = []
        self.UWI_att_data = pd.DataFrame()
        self.selected_zone_df = pd.DataFrame()
        self.current_well_data = pd.DataFrame()
        self.selected_attribute = None
        self.min_attr = 0
        self.max_attr = 1
        self.selected_zone = None
        self.tick_size_value = 20

      

        self.next_well = False
        self.db_manager = db_manager
     
       
        self.plot_widget = SeismicGraphicsView()  # New custom QGraphicsView
        self.plot_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.plot_widget.seismic_kdtree = seismic_kdtree
        self.plot_widget.seismic_data = seismic_data
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
            "Tick Size"
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



        def create_dropdown(label):
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

        def create_section(frame_name, fixed_height=None):
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

            shadow = QGraphicsDropShadowEffect()
            shadow.setBlurRadius(10)
            shadow.setXOffset(3)
            shadow.setYOffset(3)
            shadow.setColor(QColor(0, 0, 0, 100))
            frame.setGraphicsEffect(shadow)

            layout = QVBoxLayout(frame)
            layout.setSpacing(1)
            layout.setContentsMargins(5, 5, 5, 5)
            layout.setAlignment(Qt.AlignTop)
            return frame, layout

        def create_input(label, default_value='', validator=None):
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

        def create_colorbar():
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

        # Create main layout first
        main_layout = QHBoxLayout(self)  # Parent to self immediately

        # Control Layout setup
        control_layout = QVBoxLayout()
    
        # Create and populate frames
        wellFrame, wellLayout = self.create_section("Well Navigation", fixed_height=90)
        self.setup_well_section(wellFrame, wellLayout)
    
        zoneFrame, zoneLayout = self.create_section("Zone and Attribute", fixed_height=170)
        self.setup_zone_section(zoneFrame, zoneLayout)
    
        tickFrame, tickLayout = self.create_section("Tick Settings", fixed_height=110)
        self.setup_tick_section(tickFrame, tickLayout)
    
        # Add frames to control layout
        control_layout.addWidget(wellFrame)
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
        self.plot_current_well()

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
        self.well_selector = StyledDropdown("Well")
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
        self.zone_selector = StyledDropdown("Zone")
        self.zone_attribute_selector = StyledDropdown("Attribute")
        self.color_colorbar = StyledColorBar("Color Bar")
    
        layout.addWidget(self.zone_selector)
        layout.addWidget(self.zone_attribute_selector)
        layout.addWidget(self.color_colorbar)
        
        self.zone_attribute_selector.combo.setEnabled(False)

    def setup_tick_section(self, frame, layout):
        tick_slider_layout = QHBoxLayout()
    
        tick_size_label = QLabel("Tick Size:")
        tick_size_label.setStyleSheet("""
            QLabel {
                background-color: transparent;
                border: none;
                padding: 0;
                margin: 0;
            }
        """)
    
        self.tick_size_slider = QSlider(Qt.Horizontal)
        self.tick_size_slider.setMinimum(5)
        self.tick_size_slider.setMaximum(50)
        self.tick_size_slider.setValue(20)
        self.tick_size_slider.setTickPosition(QSlider.TicksBelow)
        self.tick_size_slider.setTickInterval(4)
    
        self.tick_size_value_label = QLabel("20")
    
        tick_slider_layout.addWidget(tick_size_label)
        tick_slider_layout.addWidget(self.tick_size_slider)
        tick_slider_layout.addWidget(self.tick_size_value_label)
    
        layout.addLayout(tick_slider_layout)

    def setup_connections(self):
        self.well_selector.combo.currentIndexChanged.connect(self.on_well_selected)
        self.prev_button.clicked.connect(self.on_prev)
        self.next_button.clicked.connect(self.on_next)
        self.zone_selector.combo.currentIndexChanged.connect(self.zone_selected)
        self.zone_attribute_selector.combo.currentIndexChanged.connect(self.attribute_selected)
        self.color_colorbar.colorbar_dropdown.combo.currentIndexChanged.connect(self.palette_selected)
        self.tick_size_slider.valueChanged.connect(self.update_tick_size_value_label)

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
                print(zones)

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
        print(zone_df)
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
        print(self.attributes_names)
        # Find attributes (columns with at least one non-null value)
 
    
        # Clear and populate the attribute selector
        self.zone_attribute_selector.clear()
        self.zone_attribute_selector.addItem("Select Zone Attribute")
        self.zone_attribute_selector.addItems(self.attributes_names)
    
        # Set default selection to the first item (e.g., "Select Zone Attribute")
        self.zone_attribute_selector.setCurrentIndex(0)
        self.zone_attribute_selector.blockSignals(False)


    


    def update_tick_size_value_label(self, value):
        """Update tick size without reloading the entire plot"""
        self.tick_size_value = max(2, min(self.tick_size_slider.value(), 20))
        self.tick_size_value_label.setText(str(value))
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






    def plot_current_well(self):
        """Plot well path and intersections using proven approach"""
        try:
            # Clear scene
           
            self.plot_widget.scene_obj.clear()

            # Get well data
            self.current_well_data = self.directional_surveys_df[
                self.directional_surveys_df['UWI'] == self.current_UWI
            ].reset_index(drop=True)

            if self.current_well_data.empty:
                print(f"No data found for UWI: {self.current_UWI}")
                return

            self.tvd_values = self.current_well_data['TVD'].tolist()
            self.combined_distances = self.current_well_data['Cumulative Distance'].tolist()
            print("Seismic data shape:", self.seismic_data['trace_data'].shape if 'trace_data' in self.seismic_data else "No trace_data found")
            print("Time axis length:", len(self.seismic_data['time_axis']) if 'time_axis' in self.seismic_data else "No time_axis found")

        # Process seismic data if available
            if self.seismic_data and self.seismic_kdtree:
                well_coords = np.column_stack((
                    self.current_well_data['X Offset'],
                    self.current_well_data['Y Offset']
                ))

                # Get grid extent
                grid_start = min(self.combined_distances)
                grid_end = max(self.combined_distances)

                # Load and process seismic data
                processed_seismic_data = self.plot_widget.load_seismic_data(
                    well_coords, 
                    self.combined_distances, 
                    self.seismic_kdtree,
                    self.seismic_data
                )

                if processed_seismic_data:
                    # Update seismic display 
                    self.plot_widget.update_seismic_data(
                        processed_seismic_data['trace_data'],
                        well_coords,
                        self.combined_distances,
                        processed_seismic_data['time_axis'],
                        grid_start,
                        grid_end
                    )


            # Process grid intersections
            well_coords_grid = np.column_stack((
                self.current_well_data['X Offset'],
                self.current_well_data['Y Offset']
            ))

            # Create dictionary to store grid values
            grid_values = {}
        
            # Get sorted grids for consistent order
            sorted_grids = sorted(self.kd_tree_depth_grids.keys())

            # Calculate grid values
            for grid_name in sorted_grids:
                kdtree = self.kd_tree_depth_grids[grid_name]
                grid_values[grid_name] = []
            
                for x2, y2 in well_coords_grid:
                    if kdtree.data.size > 0:
                        distances, indices = kdtree.query((x2, y2))
                        if indices < len(self.depth_grid_data_dict[grid_name]):
                            grid_values[grid_name].append(self.depth_grid_data_dict[grid_name][indices])

            # Plot grids and fills
            for i, grid_name in enumerate(sorted_grids):
                try:
                    # Get grid colors
                    grid_row = self.grid_info_df.loc[self.grid_info_df['Grid'] == grid_name]
                    if grid_row.empty:
                        continue
                    
                    current_color = grid_row['Color (RGB)'].values[0]
                
                    # Create points list for current grid
                    current_points = list(zip(self.combined_distances, grid_values[grid_name]))
                
                    # Draw the grid line
                    self.plot_widget.add_grid_line(current_points, current_color)

                    # Add fill between this grid and next grid
                    if i < len(sorted_grids) - 1:
                        next_grid_name = sorted_grids[i + 1]
                        next_points = list(zip(self.combined_distances, grid_values[next_grid_name]))
                    
                        # Create fill path
                        path = QPainterPath()
                        path.moveTo(current_points[0][0], current_points[0][1])
                    
                        # Draw top line
                        for point in current_points:
                            path.lineTo(point[0], point[1])
                        
                        # Draw bottom line in reverse
                        for point in reversed(next_points):
                            path.lineTo(point[0], point[1])
                        
                        # Close path
                        path.lineTo(current_points[0][0], current_points[0][1])
                    
                        # Create semi-transparent fill
                        color = QColor(*current_color)
                        color.setAlpha(76)  # 30% opacity (0-255)
                        fill_item = self.plot_widget.scene_obj.addPath(
                            path,
                            QPen(Qt.NoPen),
                            QBrush(color)
                        )
                        fill_item.setZValue(0)  # Put fill behind grid lines

                except Exception as e:
                    print(f"Error processing grid {grid_name}: {e}")

            # Update well path last so it's on top
            path_points = list(zip(self.combined_distances, self.tvd_values))
            self.plot_widget.update_well_path(path_points)

        except Exception as e:
            print(f"Error in plot_current_well: {e}")
            import traceback
            traceback.print_exc()

    def zone_selected(self):
        print("zone_selected() was triggered!")  # Debugging

        selected_text = self.zone_selector.currentText()
        if not selected_text:  
            print("Empty zone selection")
            return

        self.selected_zone = selected_text.replace(" ", "_")
        print(f"Selected zone: {self.selected_zone}")

        self.zone_attribute_selector.clear()
        self.zone_attribute_selector.addItem("Select Zone Attribute")

        if self.selected_zone == "Select_Zone":
            self.selected_zone_df = None
            self.attributes_names = []
        else:
            try:
                # Fetch zone data
                self.selected_zone_df = self.db_manager.fetch_table_data(self.selected_zone)
                print(f"Fetched data: {self.selected_zone_df}")  # Debugging

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
                self.plot_current_well()
            
                # Optionally add zone ticks if a zone is selected
                if self.selected_zone and self.selected_zone != "Select_Zone":
                    self.update_zone_ticks()
            else:
                print(f"Selected UWI {selected_UWI} not found in UWI list.")
        except Exception as e:
            print(f"Error in on_well_selected: {e}")

    def on_next(self):
        """Navigate to the next well in alphabetical order."""
        try:
            current_index = self.UWI_list.index(self.current_UWI)
            next_index = (current_index + 1) % len(self.UWI_list)
            self.current_UWI = self.UWI_list[next_index]
            self.update_well_selector_to_current_UWI()
        
            # Only plot the current well's seismic and grid data
            self.plot_current_well()
        
            # Optionally add zone ticks if a zone is selected
            if self.selected_zone and self.selected_zone != "Select_Zone":
                self.update_zone_ticks()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"An error occurred while processing the next well: {str(e)}")

    def on_prev(self):
        """Navigate to the previous well in alphabetical order."""
        try:
            current_index = self.UWI_list.index(self.current_UWI)
            prev_index = (current_index - 1) % len(self.UWI_list)
            self.current_UWI = self.UWI_list[prev_index]
            self.update_well_selector_to_current_UWI()
        
            # Only plot the current well's seismic and grid data
            self.plot_current_well()
        
            # Optionally add zone ticks if a zone is selected
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
            print(f"MD {md} is below the range of the well data. Using minimum value.")
            return self.current_well_data[column].iloc[0]
        elif md > self.current_well_data['MD'].max():
            print(f"MD {md} is above the range of the well data. Using maximum value.")
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