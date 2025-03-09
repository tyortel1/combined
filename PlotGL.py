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
import ctypes 
from ctypes import c_void_p 


# PySide6 Core, GUI, and Widgets
from PySide6.QtCore import Qt, Signal, QRectF, QUrl, QTimer
from PySide6.QtGui import (
    QIcon, QColor, QPainter, QBrush, QPixmap, QPainterPath, 
    QTransform, QImage, QPen, qRgb, QSurfaceFormat, QMatrix4x4, QVector2D
)
from PySide6.QtWidgets import (
    QApplication, QVBoxLayout, QSpacerItem, QSizePolicy, QHBoxLayout,
    QGraphicsDropShadowEffect, QPushButton, QSlider, QDialog, QLabel,
    QFrame, QMessageBox, QWidget
)
from PySide6.QtOpenGL import (
   QOpenGLShader, QOpenGLShaderProgram, 
    QOpenGLBuffer, QOpenGLVertexArrayObject, QOpenGLTexture
)
from PySide6.QtOpenGLWidgets import QOpenGLWidget

# Import OpenGL constants directly
import OpenGL.GL as GL

# Custom Styled UI Components
from StyledDropdown import StyledDropdown, StyledInputBox
from StyledColorbar import StyledColorBar
from StyledSliders import StyledSlider, StyledRangeSlider
from SeismicDatabaseManager import SeismicDatabaseManager  
from DatabaseManager import DatabaseManager

# SuperQt Extension
from superqt import QRangeSlider



class SeismicOpenGLWidget(QOpenGLWidget):
    seismic_range_changed = Signal(float, float)
    
    def __init__(self, parent=None, plot_instance=None):
        super().__init__(parent)
        self.plot_instance = plot_instance
        
        # Configure OpenGL format
        fmt = QSurfaceFormat()
        fmt.setDepthBufferSize(24)
        fmt.setStencilBufferSize(8)
        fmt.setVersion(3, 3)  # OpenGL 3.3
        fmt.setProfile(QSurfaceFormat.CoreProfile)
        fmt.setSamples(4)  # Multisampling for anti-aliasing
        fmt.setAlphaBufferSize(8)  # Important for transparency
        QSurfaceFormat.setDefaultFormat(fmt)
        self.setFormat(fmt)
        
        # Initialize state variables
        self.seismic_data = None
        self.seismic_distances = None
        self.time_axis = None
        self.color_palette = None
        self.last_smoothed_data = None
        self.last_max_abs_value = None
        self.well_path_points = None
        self.zone_markers = []
        self.zone_fills = []
        self.grid_lines = []
        self.timing_lines = []
        
        # Transformation variables
        self.zoom_level = 1.0
        self.offset_x = 0.0
        self.offset_y = 0.0
        self.scale_y = 1.0  # For vertical flipping
        
        # OpenGL variables
        self.shader_program = None
        self.vao = None
        self.vbo = None
        self.ebo = None  # Added missing EBO declaration
        self.texture = None
        self.well_shader = None
        self.well_vao = None
        self.well_vbo = None
        self.zone_shader = None
        
        # Range filtering
        self.using_range_filter = False
        self.min_range_value = None
        self.max_range_value = None
        
        # Mouse tracking
        self.setMouseTracking(True)
        self.last_mouse_pos = None
        self.dragging = False
        
        # Animation timer
        self.animation_timer = QTimer(self)
        self.animation_timer.timeout.connect(self.safeUpdate)
        self.animation_timer.start(100)  # Slower update rate: 10 FPS instead of 60
    
        # Track if we're currently rendering to prevent re-entrancy
        self.is_rendering = False

    def initializeGL(self):
        print("🟢 initializeGL() called!")
    
        try:
            # Initialize OpenGL functions
            self.gl = self.context().functions()
            if not self.gl:
                raise RuntimeError("Failed to obtain OpenGL functions")
        
            # Set clear color
            self.gl.glClearColor(1.0, 1.0, 1.0, 1.0)
        
            # Enable blending for transparency
            self.gl.glEnable(GL.GL_BLEND)
            self.gl.glBlendFunc(GL.GL_SRC_ALPHA, GL.GL_ONE_MINUS_SRC_ALPHA)
        
            # Initialize shaders
            success = True
        
            # Initialize seismic shader
            try:
                self.initializeSeismicShader()
                print("✅ Seismic shader initialized")
            except Exception as e:
                success = False
                print(f"❌ Seismic shader initialization failed: {e}")
                import traceback
                traceback.print_exc()
        
            # Initialize well path shader
            try:
                self.initializeWellPathShader()
                print("✅ Well path shader initialized")
            except Exception as e:
                success = False
                print(f"❌ Well path shader initialization failed: {e}")
                import traceback
                traceback.print_exc()
        
            # Initialize zone shader
            try:
                self.initializeZoneShader()
                print("✅ Zone shader initialized")
            except Exception as e:
                success = False
                print(f"❌ Zone shader initialization failed: {e}")
                import traceback
                traceback.print_exc()
        
            if success:
                print("✅ All shaders initialized successfully!")
            else:
                print("❌ Some shader initializations failed")
            
        except Exception as e:
            print(f"❌ Error in initializeGL: {e}")
            import traceback
            traceback.print_exc()

    
    def initializeSeismicShader(self):
        # Create shader for seismic data rendering
        self.shader_program = QOpenGLShaderProgram(self)
        
        # Vertex shader
        vertex_shader = """
        #version 330 core
        layout (location = 0) in vec3 position;
        layout (location = 1) in vec2 texCoord;
        
        out vec2 TexCoord;
        uniform mat4 model;
        uniform mat4 view;
        uniform mat4 projection;
        
        void main()
        {
            gl_Position = projection * view * model * vec4(position, 1.0);
            TexCoord = texCoord;
        }
        """
        
        # Fragment shader with range filtering
        fragment_shader = """
        #version 330 core
        in vec2 TexCoord;
        out vec4 FragColor;
        
        uniform sampler2D seismicTexture;
        uniform float opacity;
        uniform bool useRangeFilter;
        uniform float minRange;
        uniform float maxRange;
        uniform float maxAbsValue;
        
        void main()
        {
            // Get the color from texture
            vec4 texColor = texture(seismicTexture, TexCoord);
            
            // Apply range filtering if enabled
            if (useRangeFilter) {
                // Convert RGB to grayscale value (assuming the RGB represents a single data value)
                float dataValue = texColor.r;  // Simplified - assumes grayscale stored in R channel
                
                // Scale from [0,1] to original data range
                dataValue = (dataValue * 2.0 - 1.0) * maxAbsValue;
                
                // Check if the value is outside the range
                if (dataValue < minRange || dataValue > maxRange) {
                    // Outside range - make transparent
                    FragColor = vec4(texColor.rgb, 0.0);
                } else {
                    // Inside range - use original opacity
                    FragColor = vec4(texColor.rgb, texColor.a * opacity);
                }
            } else {
                // Normal rendering
                FragColor = vec4(texColor.rgb, texColor.a * opacity);
            }
        }
        """
        
        # Add shaders to program
        self.shader_program.addShaderFromSourceCode(QOpenGLShader.Vertex, vertex_shader)
        self.shader_program.addShaderFromSourceCode(QOpenGLShader.Fragment, fragment_shader)
        
        # Link shader program
        if not self.shader_program.link():
            print(f"❌ Failed to link shader program: {self.shader_program.log()}")
            return
        
        # Create VAO and VBO for seismic data quad
        self.vao = QOpenGLVertexArrayObject()
        self.vao.create()
        self.vao.bind()
        
        self.vbo = QOpenGLBuffer()
        self.vbo.create()
        self.vbo.bind()
        
        # Quad vertices: position (x,y,z) and texture coordinates (s,t)
        quad_vertices = np.array([
            # positions        # texture coords
            -1.0, -1.0, 0.0,   0.0, 0.0,  # bottom left
             1.0, -1.0, 0.0,   1.0, 0.0,  # bottom right
             1.0,  1.0, 0.0,   1.0, 1.0,  # top right
            -1.0,  1.0, 0.0,   0.0, 1.0   # top left
        ], dtype=np.float32)
        
        # Quad indices
        quad_indices = np.array([
            0, 1, 2,  # first triangle
            2, 3, 0   # second triangle
        ], dtype=np.uint32)
        
        # Upload vertex data
        self.vbo.allocate(quad_vertices.tobytes(), quad_vertices.nbytes)
        
        # Set up vertex attribute pointers
        stride = 5 * 4  # 5 floats * 4 bytes
        
        self.gl.glEnableVertexAttribArray(0)
        # Use None for the pointer offset or ctypes
   
        self.gl.glVertexAttribPointer(0, 3, 0x1406, 0, stride, ctypes.c_void_p(0))

        # Texture coordinate attribute
        self.gl.glEnableVertexAttribArray(1)
        self.gl.glVertexAttribPointer(1, 2, 0x1406, 0, stride, ctypes.c_void_p(12))
        
        # Create EBO (Element Buffer Object)
        self.ebo = QOpenGLBuffer(QOpenGLBuffer.IndexBuffer)
        self.ebo.create()
        self.ebo.bind()
        self.ebo.allocate(quad_indices.tobytes(), quad_indices.nbytes)
        
        # Unbind
        self.vao.release()
    
    def initializeWellPathShader(self):
        # Create shader for well path rendering
        self.well_shader = QOpenGLShaderProgram(self)
        
        # Vertex shader
        vertex_shader = """
        #version 330 core
        layout (location = 0) in vec3 position;
        
        uniform mat4 model;
        uniform mat4 view;
        uniform mat4 projection;
        
        void main()
        {
            gl_Position = projection * view * model * vec4(position, 1.0);
        }
        """
        
        # Fragment shader
        fragment_shader = """
        #version 330 core
        out vec4 FragColor;
        
        uniform vec4 color;
        
        void main()
        {
            FragColor = color;
        }
        """
        
        # Add shaders to program
        self.well_shader.addShaderFromSourceCode(QOpenGLShader.Vertex, vertex_shader)
        self.well_shader.addShaderFromSourceCode(QOpenGLShader.Fragment, fragment_shader)
        
        # Link shader program
        if not self.well_shader.link():
            print(f"❌ Failed to link well shader program: {self.well_shader.log()}")
            return
        
        # Create VAO and VBO for well path
        self.well_vao = QOpenGLVertexArrayObject()
        self.well_vao.create()
        
        self.well_vbo = QOpenGLBuffer()
        self.well_vbo.create()
    
    def initializeZoneShader(self):
        # Create shader for zone markers and fills
        self.zone_shader = QOpenGLShaderProgram(self)
        
        # Vertex shader
        vertex_shader = """
        #version 330 core
        layout (location = 0) in vec3 position;
        
        uniform mat4 model;
        uniform mat4 view;
        uniform mat4 projection;
        
        void main()
        {
            gl_Position = projection * view * model * vec4(position, 1.0);
        }
        """
        
        # Fragment shader
        fragment_shader = """
        #version 330 core
        out vec4 FragColor;
        
        uniform vec4 color;
        
        void main()
        {
            FragColor = color;
        }
        """
        
        # Add shaders to program
        self.zone_shader.addShaderFromSourceCode(QOpenGLShader.Vertex, vertex_shader)
        self.zone_shader.addShaderFromSourceCode(QOpenGLShader.Fragment, fragment_shader)
        
        # Link shader program
        if not self.zone_shader.link():
            print(f"❌ Failed to link zone shader program: {self.zone_shader.log()}")
            return
    
    def resizeGL(self, width, height):
        try:
            # Ensure we have valid dimensions
            if width <= 0 or height <= 0:
                print(f"⚠️ Invalid resize dimensions: {width}x{height}")
                return
            
            print(f"Resizing GL viewport to {width}x{height}")
        
            # Update viewport - critical for correct rendering
            self.gl.glViewport(0, 0, width, height)
        
            # Update projection matrix
            aspect_ratio = width / max(1, height)  # Prevent division by zero
            self.projection_matrix = QMatrix4x4()
            self.projection_matrix.ortho(
                -aspect_ratio, aspect_ratio,
                -1.0, 1.0,
                -1.0, 1.0
            )
        
            print(f"Updated projection matrix with aspect ratio: {aspect_ratio}")
        
            # Force a repaint to reflect the new size
            self.update()
        
        except Exception as e:
            print(f"❌ Error in resizeGL: {e}")
            import traceback
            traceback.print_exc()
    
    def updateProjectionMatrix(self):
        # Create orthographic projection matrix
        self.projection_matrix = QMatrix4x4()
        
        aspect_ratio = self.width() / self.height()
        self.projection_matrix.ortho(
            -aspect_ratio * self.zoom_level, 
            aspect_ratio * self.zoom_level, 
            -1.0 * self.zoom_level, 
            1.0 * self.zoom_level, 
            -1.0, 
            1.0
        )
    
    def safeUpdate(self):
        """Safe update method that prevents re-entrancy and handles exceptions"""
        if self.is_rendering:
            return  # Skip if already rendering
    
        try:
            self.is_rendering = True
            self.update()  # Request a repaint
        except Exception as e:
            print(f"❌ Error during update: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self.is_rendering = False

    def paintGL(self):
        """Render grid lines using NDC coordinates"""
        # Clear background
        self.gl.glClearColor(0.2, 0.3, 0.3, 1.0)
        self.gl.glClear(GL.GL_COLOR_BUFFER_BIT)

        # Basic grid line rendering
        if hasattr(self, 'grid_lines') and self.grid_lines:
            self.gl.glLineWidth(2.0)
        
            for grid_line in self.grid_lines:
                points = grid_line.get('points', [])
                color = grid_line.get('color', (0.5, 0.5, 0.5))
            
                # Convert color to float
                color_float = [c/255.0 for c in color] if isinstance(color[0], int) else color
            
                self.gl.glColor3f(*color_float[:3])
            
                self.gl.glBegin(GL.GL_LINE_STRIP)
                for point in points:
                    x = self.map_to_ndc(point[0], 'x')
                    y = self.map_to_ndc(point[1], 'y')
                    self.gl.glVertex2f(x, y)
                self.gl.glEnd()


    #def paintGL(self):
    #    """Simplified painting method that avoids problematic OpenGL calls"""
    #    try:
    #        # Set render flag to prevent re-entry
    #        self.render_disabled = True
        
    #        # Basic validation
    #        if not self.isValid():
    #            print("⚠️ OpenGL context is not valid")
    #            return
            
    #        if not hasattr(self, 'gl') or self.gl is None:
    #            print("⚠️ OpenGL functions not initialized")
    #            return
        
    #        # Simple clear with a visible color - use try/except for each OpenGL call
    #        try:
    #            self.gl.glClearColor(0.2, 0.3, 0.3, 1.0)
    #        except Exception as e:
    #            print(f"⚠️ Error in glClearColor: {e}")
            
    #        try:
    #            self.gl.glClear(0x4000 | 0x100)  # COLOR_BUFFER_BIT | DEPTH_BUFFER_BIT
    #        except Exception as e:
    #            print(f"⚠️ Error in glClear: {e}")
        
    #        # Render seismic data if available
    #        if hasattr(self, 'seismic_data') and self.seismic_data is not None and hasattr(self, 'shader_program'):
    #            try:
    #                # Very simplified seismic rendering
    #                if self.shader_program and self.vao and self.texture:
    #                    self.shader_program.bind()
                    
    #                    # Set up matrices
    #                    view = QMatrix4x4()
    #                    view.translate(self.offset_x, self.offset_y, 0)
                    
    #                    model = QMatrix4x4()
    #                    model.scale(1.0, self.scale_y, 1.0)
                    
    #                    try:
    #                        # Retrieve uniform locations
    #                        model_location = self.shader_program.uniformLocation("model")
    #                        view_location = self.shader_program.uniformLocation("view")
    #                        projection_location = self.shader_program.uniformLocation("projection")
    #                        opacity_location = self.shader_program.uniformLocation("opacity")

    #                        # Set uniforms only if locations are valid
    #                        if model_location != -1:
    #                            self.shader_program.setUniformValue(model_location, model)
    #                        else:
    #                            print("⚠️ Warning: Uniform 'model' not found in shader.")

    #                        if view_location != -1:
    #                            self.shader_program.setUniformValue(view_location, view)
    #                        else:
    #                            print("⚠️ Warning: Uniform 'view' not found in shader.")

    #                        if projection_location != -1:
    #                            self.shader_program.setUniformValue(projection_location, self.projection_matrix)
    #                        else:
    #                            print("⚠️ Warning: Uniform 'projection' not found in shader.")

    #                        if opacity_location != -1:
    #                            self.shader_program.setUniformValue(opacity_location, 1.0)
    #                        else:
    #                            print("⚠️ Warning: Uniform 'opacity' not found in shader.")

    #                    except Exception as uniform_error:
    #                        print(f"❌ Error setting uniforms: {uniform_error}")

                    
    #                    # Bind texture
    #                    try:
    #                        self.gl.glActiveTexture(0x84C0)  # GL_TEXTURE0
    #                        self.texture.bind()
    #                        self.shader_program.setUniformValue("seismicTexture", 0)
    #                    except Exception as texture_error:
    #                        print(f"⚠️ Error binding texture: {texture_error}")
                    
    #                    # Draw quad
    #                    try:
    #                        self.vao.bind()
    #                        self.gl.glDrawElements(0x4, 6, 0x1405, ctypes.c_void_p(0))  # GL_TRIANGLES, 6 vertices, GL_UNSIGNED_INT
    #                    except Exception as draw_error:
    #                        print(f"⚠️ Error drawing elements: {draw_error}")
                    
    #                    # Clean up
    #                    try:
    #                        self.vao.release()
    #                        self.texture.release()
    #                        self.shader_program.release()
    #                    except Exception as cleanup_error:
    #                        print(f"⚠️ Error in cleanup: {cleanup_error}")
    #            except Exception as seismic_error:
    #                print(f"⚠️ Error rendering seismic data: {seismic_error}")
        
    #        # Skip the problematic glFinish and glFlush calls
        
    #        # Let Qt handle buffer swapping automatically
        
    #        print("✅ paintGL completed successfully")
    
    #    except Exception as e:
    #        print(f"❌ Critical error in paintGL: {e}")
    #        import traceback
    #        traceback.print_exc()
    #    finally:
    #        # Re-enable rendering for next frame
    #        self.render_disabled = False
        
    #        # Use a single-shot timer instead of directly calling processEvents
    #        # This avoids potential re-entrancy issues
    #        if hasattr(self, 'is_scheduled_update') and not self.is_scheduled_update:
    #            self.is_scheduled_update = True
    #            QTimer.singleShot(50, self.scheduleNextUpdate)
    

    def scheduleNextUpdate(self):
        """Safely schedule the next update"""
        try:
            self.is_scheduled_update = False
            if not self.render_disabled and self.isValid():
                self.update()
        except Exception as e:
            print(f"Error in scheduleNextUpdate: {e}")
   
    def render_seismic_data(self, model, view):
        """Render seismic data with range filtering"""
        # Early return if crucial components are missing
        if self.texture is None or self.seismic_data is None:
            return
    
        # Make sure shader program is valid before proceeding
        if not self.shader_program or not self.vao:
            print("⚠️ Missing shader program or VAO")
            return
        
        try:
            # Bind shader program
            self.shader_program.bind()
        
            # Set up model-view-projection matrices with additional error checking
            try:
                # Set uniforms using uniformLocation
                modelLoc = self.shader_program.uniformLocation("model")
                viewLoc = self.shader_program.uniformLocation("view")
                projLoc = self.shader_program.uniformLocation("projection")
                opacityLoc = self.shader_program.uniformLocation("opacity")
            
                # Check uniform locations before setting values
                if modelLoc != -1:
                    self.shader_program.setUniformValue(modelLoc, model)
                else:
                    print("⚠️ Warning: 'model' uniform not found")
                
                if viewLoc != -1:
                    self.shader_program.setUniformValue(viewLoc, view)
                else:
                    print("⚠️ Warning: 'view' uniform not found")
                
                if projLoc != -1 and hasattr(self, 'projection_matrix'):
                    self.shader_program.setUniformValue(projLoc, self.projection_matrix)
                else:
                    print("⚠️ Warning: 'projection' uniform not found or no projection matrix")
                
                if opacityLoc != -1:
                    self.shader_program.setUniformValue(opacityLoc, 1.0)
                else:
                    print("⚠️ Warning: 'opacity' uniform not found")
                
            except Exception as matrix_error:
                print(f"❌ Error setting matrix uniforms: {matrix_error}")
            
            # Set range filter uniforms with defensive approach
            try:
                useRangeFilterLoc = self.shader_program.uniformLocation("useRangeFilter")
                if useRangeFilterLoc != -1:
                    self.shader_program.setUniformValue(useRangeFilterLoc, 
                                                       getattr(self, 'using_range_filter', False))
                
                # Only set range values if filtering is enabled
                if getattr(self, 'using_range_filter', False) and hasattr(self, 'min_range_value') and hasattr(self, 'max_range_value'):
                    minRangeLoc = self.shader_program.uniformLocation("minRange")
                    maxRangeLoc = self.shader_program.uniformLocation("maxRange")
                    maxAbsValueLoc = self.shader_program.uniformLocation("maxAbsValue")
                
                    if minRangeLoc != -1 and self.min_range_value is not None:
                        self.shader_program.setUniformValue(minRangeLoc, self.min_range_value)
                    
                    if maxRangeLoc != -1 and self.max_range_value is not None:
                        self.shader_program.setUniformValue(maxRangeLoc, self.max_range_value)
                    
                    if maxAbsValueLoc != -1:
                        self.shader_program.setUniformValue(maxAbsValueLoc, 
                                                           getattr(self, 'last_max_abs_value', 1.0))
            except Exception as range_error:
                print(f"❌ Error setting range filter uniforms: {range_error}")
        
            # Texture binding with safety checks
            try:
                if hasattr(self, 'gl') and self.gl and self.texture:
                    self.gl.glActiveTexture(GL.GL_TEXTURE0)
                    self.texture.bind()
                    textureLoc = self.shader_program.uniformLocation("seismicTexture")
                    if textureLoc != -1:
                        self.shader_program.setUniformValue(textureLoc, 0)
            except Exception as texture_error:
                print(f"❌ Error binding texture: {texture_error}")
            
            # Draw the geometry
            try:
                if self.vao:
                    self.vao.bind()
                    if hasattr(self, 'gl') and self.gl:
                        self.gl.glDrawElements(GL.GL_TRIANGLES, 6, GL.GL_UNSIGNED_INT, ctypes.c_void_p(0))
                    self.vao.release()
            except Exception as draw_error:
                print(f"❌ Error drawing elements: {draw_error}")
            
            # Ensure cleanup happens regardless of any drawing errors
            try:
                if self.texture:
                    self.texture.release()
                if self.shader_program:
                    self.shader_program.release()
            except Exception as cleanup_error:
                print(f"❌ Error during cleanup: {cleanup_error}")
            
        except Exception as e:
            # Catch-all for any other errors
            print(f"❌ Error rendering seismic data: {e}")
            import traceback
            traceback.print_exc()

    def render_grid_lines(self, model, view):
        """Render grid lines"""
        if not hasattr(self, 'grid_lines') or not self.grid_lines:
            return
    
        # Skip if shader is not initialized
        if self.well_shader is None:
            print("Warning: Well shader is not initialized for grid lines")
            return
    
        try:
            # Get uniform locations for well shader
            modelLoc = self.well_shader.uniformLocation("model")
            viewLoc = self.well_shader.uniformLocation("view")
            projLoc = self.well_shader.uniformLocation("projection")
            colorLoc = self.well_shader.uniformLocation("color")
        
            for grid_line in self.grid_lines:
                points = grid_line['points']
                color = grid_line['color']
            
                # Prepare points for rendering
                line_vertices = []
                for point in points:
                    # Convert points to NDC space
                    x = self.map_to_ndc(point[0], 'x')
                    y = self.map_to_ndc(point[1], 'y')
                    line_vertices.extend([x, y, 0.0])
            
                # Convert to numpy array
                vertices = np.array(line_vertices, dtype=np.float32)
            
                self.well_shader.bind()
            
                # Set uniform values using locations
                self.well_shader.setUniformValue(modelLoc, model)
                self.well_shader.setUniformValue(viewLoc, view)
                self.well_shader.setUniformValue(projLoc, self.projection_matrix)
                self.well_shader.setUniformValue(colorLoc, QColor(*color))
            
                # Create temporary VAO and VBO
                temp_vao = QOpenGLVertexArrayObject()
                temp_vao.create()
                temp_vao.bind()
            
                temp_vbo = QOpenGLBuffer()
                temp_vbo.create()
                temp_vbo.bind()
                temp_vbo.allocate(vertices.tobytes(), vertices.nbytes)
            
                # Set up vertex attributes
                self.gl.glEnableVertexAttribArray(0)
                self.gl.glVertexAttribPointer(0, 3, 0x1406, 0, 3 * 4, ctypes.c_void_p(0))
            
                # Draw lines
                self.gl.glLineWidth(1.0)
                self.gl.glDrawArrays(GL.GL_LINE_STRIP, 0, len(points))
            
                # Cleanup
                temp_vao.release()
                temp_vbo.destroy()
                temp_vao.destroy()
                self.well_shader.release()
            
        except Exception as e:
            print(f"❌ Error rendering grid lines: {e}")
            import traceback
            traceback.print_exc()

    def render_well_path(self, model, view):
        """Render well path"""
        if not hasattr(self, 'well_path_points') or self.well_path_points is None or len(self.well_path_points) < 2:
            return
    
        # Skip if shader is not initialized
        if self.well_shader is None:
            print("Warning: Well shader is not initialized")
            return
    
        try:
            # Get uniform locations
            modelLoc = self.well_shader.uniformLocation("model")
            viewLoc = self.well_shader.uniformLocation("view")
            projLoc = self.well_shader.uniformLocation("projection")
            colorLoc = self.well_shader.uniformLocation("color")
        
            self.well_shader.bind()
        
            # Set uniform values
            self.well_shader.setUniformValue(modelLoc, model)
            self.well_shader.setUniformValue(viewLoc, view)
            self.well_shader.setUniformValue(projLoc, self.projection_matrix)
            self.well_shader.setUniformValue(colorLoc, QColor(0, 0, 0, 255))
        
            # Create and bind VAO
            self.well_vao.bind()
        
            # Create and bind VBO
            self.well_vbo.bind()
        
            # Convert path points to normalized device coordinates
            path_points_flat = []
            for point in self.well_path_points:
                # Map from data space to NDC space
                x = self.map_to_ndc(point[0], 'x')
                y = self.map_to_ndc(point[1], 'y')
                path_points_flat.extend([x, y, 0.0])
        
            # Upload vertex data
            path_points_array = np.array(path_points_flat, dtype=np.float32)
            self.well_vbo.allocate(path_points_array.tobytes(), path_points_array.nbytes)
        
            # Set up vertex attribute pointers
            self.gl.glEnableVertexAttribArray(0)
            self.gl.glVertexAttribPointer(0, 3, GL.GL_FLOAT, GL.GL_FALSE, 3 * 4, ctypes.c_void_p(0))
        
            # Draw line strip
            self.gl.glLineWidth(2.0)
            self.gl.glDrawArrays(GL.GL_LINE_STRIP, 0, len(self.well_path_points))
        
            # Unbind
            self.well_vao.release()
            self.well_shader.release()
        
        except Exception as e:
            print(f"❌ Error rendering well path: {e}")
            import traceback
            traceback.print_exc()

    def render_zones(self, model, view):
        """Render zones"""
        if not self.zone_fills and not self.zone_markers:
            return
    
        # Skip if shader is not initialized
        if self.zone_shader is None:
            print("Warning: Zone shader is not initialized")
            return
    
        try:
            # Get uniform locations
            modelLoc = self.zone_shader.uniformLocation("model")
            viewLoc = self.zone_shader.uniformLocation("view")
            projLoc = self.zone_shader.uniformLocation("projection")
            colorLoc = self.zone_shader.uniformLocation("color")
        
            self.zone_shader.bind()
        
            # Set uniform values
            self.zone_shader.setUniformValue(modelLoc, model)
            self.zone_shader.setUniformValue(viewLoc, view)
            self.zone_shader.setUniformValue(projLoc, self.projection_matrix)
        
            # Render zone fills first
            for zone_fill in self.zone_fills:
                # Set color with transparency
                color = zone_fill['color']
                self.zone_shader.setUniformValue(colorLoc, QColor(
                    color.red(), color.green(), color.blue(), 
                    int(color.alpha() * zone_fill['opacity'])
                ))
            
                # Create and bind temporary VAO and VBO
                temp_vao = QOpenGLVertexArrayObject()
                temp_vao.create()
                temp_vao.bind()
            
                temp_vbo = QOpenGLBuffer()
                temp_vbo.create()
                temp_vbo.bind()
            
                # Convert quad points to normalized device coordinates
                points = zone_fill['points']
            
                # Points order: top-left, top-right, bottom-right, bottom-left
                # Adjusted for tick size in y-direction
                tick_size_ndc = self.map_tick_size_to_ndc(zone_fill['tick_size'])
            
                points_flat = [
                    self.map_to_ndc(points[0][0], 'x'), self.map_to_ndc(points[0][1] - tick_size_ndc/2, 'y'), 0.0,  # Top left
                    self.map_to_ndc(points[1][0], 'x'), self.map_to_ndc(points[1][1] - tick_size_ndc/2, 'y'), 0.0,  # Top right
                    self.map_to_ndc(points[1][0], 'x'), self.map_to_ndc(points[1][1] + tick_size_ndc/2, 'y'), 0.0,  # Bottom right
                    self.map_to_ndc(points[0][0], 'x'), self.map_to_ndc(points[0][1] + tick_size_ndc/2, 'y'), 0.0   # Bottom left
                ]
            
                # Upload vertex data
                points_array = np.array(points_flat, dtype=np.float32)
                temp_vbo.allocate(points_array.tobytes(), points_array.nbytes)
            
                # Set up vertex attribute pointers
                self.gl.glEnableVertexAttribArray(0)
                self.gl.glVertexAttribPointer(0, 3, GL.GL_FLOAT, GL.GL_FALSE, 3 * 4, ctypes.c_void_p(0))
            
                # Draw quad
                self.gl.glDrawArrays(GL.GL_TRIANGLE_FAN, 0, 4)
            
                # Clean up
                temp_vao.release()
                temp_vbo.destroy()
                temp_vao.destroy()
        
            # Render zone markers
            for marker in self.zone_markers:
                # Set color
                self.zone_shader.setUniformValue(colorLoc, QColor('black'))
            
                # Create and bind temporary VAO and VBO
                temp_vao = QOpenGLVertexArrayObject()
                temp_vao.create()
                temp_vao.bind()
            
                temp_vbo = QOpenGLBuffer()
                temp_vbo.create()
                temp_vbo.bind()
            
                # Convert line points to normalized device coordinates
                position = marker['position']
                tick_size_ndc = self.map_tick_size_to_ndc(marker['tick_size'])
            
                points_flat = [
                    self.map_to_ndc(position[0], 'x'), self.map_to_ndc(position[1] - tick_size_ndc/2, 'y'), 0.0,
                    self.map_to_ndc(position[0], 'x'), self.map_to_ndc(position[1] + tick_size_ndc/2, 'y'), 0.0
                ]
            
                # Upload vertex data
                points_array = np.array(points_flat, dtype=np.float32)
                temp_vbo.allocate(points_array.tobytes(), points_array.nbytes)
            
                # Set up vertex attribute pointers
                self.gl.glEnableVertexAttribArray(0)
                self.gl.glVertexAttribPointer(0, 3, GL.GL_FLOAT, GL.GL_FALSE, 3 * 4, ctypes.c_void_p(0))
            
                # Draw line
                self.gl.glLineWidth(2.0)
                self.gl.glDrawArrays(GL.GL_LINES, 0, 2)
            
                # Clean up
                temp_vao.release()
                temp_vbo.destroy()
                temp_vao.destroy()
        
            self.zone_shader.release()
        
        except Exception as e:
            print(f"❌ Error rendering zones: {e}")
            import traceback
            traceback.print_exc()

    def render_timing_lines(self, model, view):
        """Render timing lines"""
        if not self.timing_lines:
            return
    
        # Skip if shader is not initialized
        if self.well_shader is None:
            print("Warning: Well shader is not initialized for timing lines")
            return
    
        try:
            # Get uniform locations
            modelLoc = self.well_shader.uniformLocation("model")
            viewLoc = self.well_shader.uniformLocation("view")
            projLoc = self.well_shader.uniformLocation("projection")
            colorLoc = self.well_shader.uniformLocation("color")
        
            self.well_shader.bind()  # Reuse well path shader for timing lines
        
            # Set common uniform values
            self.well_shader.setUniformValue(modelLoc, model)
            self.well_shader.setUniformValue(viewLoc, view)
            self.well_shader.setUniformValue(projLoc, self.projection_matrix)
        
            for line in self.timing_lines:
                # Set color
                self.well_shader.setUniformValue(colorLoc, QColor(50, 50, 50, 255))
            
                # Create and bind temporary VAO and VBO
                temp_vao = QOpenGLVertexArrayObject()
                temp_vao.create()
                temp_vao.bind()
            
                temp_vbo = QOpenGLBuffer()
                temp_vbo.create()
                temp_vbo.bind()
            
                # Convert points to normalized device coordinates
                points_flat = []
                for point in line['points']:
                    x = self.map_to_ndc(point[0], 'x')
                    y = self.map_to_ndc(point[1], 'y')
                    points_flat.extend([x, y, 0.0])
            
                # Upload vertex data
                points_array = np.array(points_flat, dtype=np.float32)
                temp_vbo.allocate(points_array.tobytes(), points_array.nbytes)
            
                # Set up vertex attribute pointers
                self.gl.glEnableVertexAttribArray(0)
                self.gl.glVertexAttribPointer(0, 3, GL.GL_FLOAT, GL.GL_FALSE, 3 * 4, ctypes.c_void_p(0))
            
                # Draw line
                self.gl.glLineWidth(1.0)
                self.gl.glDrawArrays(GL.GL_LINES, 0, 2)
            
                # Clean up
                temp_vao.release()
                temp_vbo.destroy()
                temp_vao.destroy()
        
            self.well_shader.release()
        
        except Exception as e:
            print(f"❌ Error rendering timing lines: {e}")
            import traceback
            traceback.print_exc()

    def getUniformLocation(self, shader_program, name):
        """Get uniform location safely, with error handling"""
        if not shader_program:
            return -1
    
        try:
            # Convert string to bytes if it's not already
            if isinstance(name, str):
                name = name.encode('utf-8')
        
            location = shader_program.uniformLocation(name)
            if location == -1:
                print(f"Warning: Uniform '{name}' not found in shader program")
            return location
        except Exception as e:
            print(f"Error getting uniform location for '{name}': {e}")
            return -1

    # Alternative method to set shader uniform values
    def setShaderUniform(self, shader, name, value):
        """Set shader uniform with proper type handling"""
        if shader is None:
            return False
    
        # Get uniform location
        location = self.getUniformLocation(shader, name)
        if location == -1:
            return False
    
        try:
            # Handle different value types
            if isinstance(value, float):
                shader.setUniformValue(location, value)
            elif isinstance(value, int) or isinstance(value, bool):
                shader.setUniformValue(location, value)
            elif isinstance(value, QMatrix4x4):
                shader.setUniformValue(location, value)
            elif isinstance(value, QColor):
                shader.setUniformValue(location, value)
            else:
                print(f"Unsupported uniform type for '{name}': {type(value)}")
                return False
        
            return True
        except Exception as e:
            print(f"Error setting uniform '{name}': {e}")
            return False


    
    def map_to_ndc(self, value, axis):
        """
        Map a data value to Normalized Device Coordinates (-1 to 1) with extensive logging
    
        Args:
            value (float): The input value to be mapped
            axis (str): The axis to map ('x' or 'y')
    
        Returns:
            float: Normalized device coordinate between -1 and 1
        """
        # Print detailed input information
        print(f"🌐 Mapping to NDC: value={value}, axis={axis}")
    
        # First, try mapping using combined distances and seismic data
        if axis == 'x':
            # Check seismic_distances first
            if hasattr(self, 'seismic_distances') and self.seismic_distances is not None:
                print("📏 Using seismic_distances for X axis mapping")
                try:
                    distances = self.seismic_distances
                    min_x = min(distances)
                    max_x = max(distances)
                
                    # Validate input
                    if min_x == max_x:
                        print("⚠️ Warning: All seismic distances are the same")
                        return 0.0  # Return center of NDC space
                
                    # Normalize
                    normalized = 2.0 * (value - min_x) / (max_x - min_x) - 1.0
                
                    print(f"🔢 X Mapping: {value} -> {normalized}")
                    print(f"   X Range: {min_x} to {max_x}")
                
                    return normalized
                except Exception as x_err:
                    print(f"❌ Error mapping X: {x_err}")
    
        elif axis == 'y':
            # Check time_axis first
            if hasattr(self, 'time_axis') and self.time_axis is not None:
                print("📏 Using time_axis for Y axis mapping")
                try:
                    times = self.time_axis
                    min_y = min(times)
                    max_y = max(times)
                
                    # Validate input
                    if min_y == max_y:
                        print("⚠️ Warning: All time values are the same")
                        return 0.0  # Return center of NDC space
                
                    # Normalize
                    normalized = 2.0 * (value - min_y) / (max_y - min_y) - 1.0
                
                    print(f"🔢 Y Mapping: {value} -> {normalized}")
                    print(f"   Y Range: {min_y} to {max_y}")
                
                    return normalized
                except Exception as y_err:
                    print(f"❌ Error mapping Y: {y_err}")
    
        # Fallback: If no specific mapping is possible, use grid line points
        try:
            if hasattr(self, 'grid_lines') and self.grid_lines:
                # Collect all values from grid lines
                all_values = []
                for grid_line in self.grid_lines:
                    points = grid_line.get('points', [])
                    all_values.extend([point[1 if axis == 'y' else 0] for point in points])
            
                if all_values:
                    min_val = min(all_values)
                    max_val = max(all_values)
                
                    # Prevent division by zero
                    if min_val == max_val:
                        print("⚠️ Warning: All grid line values are the same")
                        return 0.0
                
                    # Normalize
                    normalized = 2.0 * (value - min_val) / (max_val - min_val) - 1.0
                
                    print(f"🔢 Grid Line Fallback Mapping: {value} -> {normalized}")
                    print(f"   Value Range: {min_val} to {max_val}")
                
                    return normalized
        except Exception as grid_err:
            print(f"❌ Error with grid line fallback mapping: {grid_err}")
    
        # Ultimate fallback: If all else fails, return the original value
        print("⚠️ No mapping method found. Returning original value.")
        return value
    
    def map_tick_size_to_ndc(self, tick_size):
        """Convert tick size from screen space to NDC space"""
        if not self.time_axis or len(self.time_axis) < 2:
            return 0.05  # Default if no data
        
        # Get the range of the time axis
        min_y = min(self.time_axis)
        max_y = max(self.time_axis)
        range_y = max_y - min_y
        
        # Scale tick size relative to the range
        return tick_size / range_y * 2.0

    def add_timing_lines(self, time_intervals, distance_intervals=None):
        """Add timing lines to the scene for OpenGL rendering"""
        # Clear existing timing lines
        self.timing_lines.clear()

        # Check if required data is available
        if (not hasattr(self, 'seismic_distances') or self.seismic_distances is None or 
            len(self.seismic_distances) == 0 or not hasattr(self, 'time_axis') or 
            self.time_axis is None or len(self.time_axis) == 0):
            return

        # Get data boundaries
        min_x = min(self.seismic_distances)
        max_x = max(self.seismic_distances)
        min_y = min(self.time_axis)
        max_y = max(self.time_axis)

        # Add horizontal time lines
        for time in time_intervals:
            self.timing_lines.append({
                'points': [(min_x, time), (max_x, time)],
                'color': (0.2, 0.2, 0.2),  # Dark gray
                'dash_pattern': False
            })

        # Add vertical distance lines if provided
        if distance_intervals is not None:
            for distance in distance_intervals:
                self.timing_lines.append({
                    'points': [(distance, min_y), (distance, max_y)],
                    'color': (0.2, 0.2, 0.2),  # Dark gray
                    'dash_pattern': True  # Use dashed lines for distance markers
                })

        # Trigger a repaint
        self.update()    
    def update_seismic_data(self, seismic_data, seismic_distances, time_axis):
        """Update seismic data and create OpenGL texture"""
        try:
            # Store raw data
            self.seismic_data = seismic_data
            self.seismic_distances = seismic_distances
            self.time_axis = time_axis
        
            # Get color palette with multiple fallback mechanisms
            color_palette = None
            
            # Try multiple ways to retrieve color palette
            try:
                # Option 1: Direct method call
                current_palette_name = self.plot_instance.seismic_colorbar.currentText()
                color_palette = self.plot_instance.seismic_colorbar.load_color_palette(current_palette_name)
                print(f"Retrieved color palette from plot instance: {current_palette_name}")
            except Exception as direct_error:
                print(f"Direct parent retrieval failed: {direct_error}")
                
                # Option 2: Search through widget hierarchy
                try:
                    from PySide6.QtWidgets import QApplication
                    
                    # Search all widgets in the application
                    for widget in QApplication.allWidgets():
                        # Check for any widget that might have a seismic_colorbar
                        if hasattr(widget, 'seismic_colorbar'):
                            current_palette_name = widget.seismic_colorbar.currentText()
                            color_palette = widget.seismic_colorbar.load_color_palette(current_palette_name)
                            print(f"Retrieved color palette from application-wide search: {current_palette_name}")
                            break
                except Exception as search_error:
                    print(f"Application-wide search failed: {search_error}")
            
            # If still no color palette, create a default one
            if color_palette is None:
                print("⚠️ Could not retrieve color palette. Using default.")
                color_palette = [
                    QColor(0, 0, 0),      # Black
                    QColor(128, 128, 128), # Gray
                    QColor(255, 255, 255)  # White
                ]
            
            # Calculate max absolute value
            max_abs_value = np.max(np.abs(seismic_data))
            if max_abs_value == 0:
                max_abs_value = 1.0  # Avoid division by zero
            
            # Store for later use in filtering
            self.last_max_abs_value = max_abs_value
            
            # Try to update color range, with fallback
            try:
                # First try parent's seismic_colorbar
                self.parent().seismic_colorbar.display_color_range(-max_abs_value, max_abs_value)
            except Exception:
                try:
                    # If that fails, find a widget with display_color_range method
                    for child in self.parent().findChildren(QWidget):
                        if hasattr(child, 'display_color_range'):
                            child.display_color_range(-max_abs_value, max_abs_value)
                            break
                except Exception:
                    print("⚠️ Could not update color range")
            
            # Normalize seismic data
            normalized_data = np.clip(seismic_data / max_abs_value, -1, 1)
            
            # Compute dimensions
            min_x, max_x = min(seismic_distances), max(seismic_distances)
            width = int(max_x - min_x) + 1
            height = len(time_axis)
            
            # Create the target x coordinate grid
            pixel_x_coords = np.arange(width)
            
            # Precompute x positions of traces relative to display
            trace_x_coords = np.array(seismic_distances) - min_x
            
            # Interpolate data for better quality
            interpolated_data = np.zeros((height, width))
            
            # Interpolate each row of the seismic data
            for row in range(height):
                row_data = normalized_data[row, :]
                interpolated_data[row, :] = np.interp(pixel_x_coords, trace_x_coords, row_data)
            
            # Store interpolated data for range filtering
            self.last_smoothed_data = interpolated_data
            
            # Map interpolated values to color indices
            color_indices = ((interpolated_data + 1) / 2 * (len(color_palette) - 1)).astype(int)
            color_indices = np.clip(color_indices, 0, len(color_palette) - 1)
            
            # Convert color palette to NumPy array for fast lookup
            palette_array = np.array([[c.red(), c.green(), c.blue(), 255] for c in color_palette], dtype=np.uint8)
            
            # Create image data array using NumPy broadcasting
            image_data = palette_array[color_indices]
            
            # Flip vertically to display seismic data with time increasing downward
            image_data = np.flip(image_data, axis=0)
            
            # Make sure data is contiguous
            image_data_contiguous = np.ascontiguousarray(image_data)
            
            # Create QImage from NumPy array
            image = QImage(image_data_contiguous.data, width, height, width * 4, QImage.Format_RGBA8888)
            image.ndarray = image_data_contiguous  # Keep a reference to prevent garbage collection
            
            # Create OpenGL texture
            if self.texture is not None:
                self.texture.destroy()
            
            self.texture = QOpenGLTexture(QOpenGLTexture.Target2D)
            self.texture.create()
            self.texture.setData(image)
            self.texture.setMinificationFilter(QOpenGLTexture.LinearMipMapLinear)
            self.texture.setMagnificationFilter(QOpenGLTexture.Linear)
            self.texture.setWrapMode(QOpenGLTexture.ClampToEdge)
            
            # Update timing lines based on new data
            self.update_timing_lines()
            
            # Update view
            self.update()

        except Exception as e:
                    print(f"Error updating seismic data: {e}")
                    import traceback
                    traceback.print_exc()
    
    def update_seismic_range(self, min_val, max_val):
        """Update seismic range filter settings for transparency"""
        try:
            # Set range filter parameters
            self.min_range_value = min_val
            self.max_range_value = max_val
            self.using_range_filter = True
            
            # Signal that range has changed
            self.seismic_range_changed.emit(min_val, max_val)
            
            # Update the visualization
            self.update()
            
        except Exception as e:
            print(f"Error updating seismic range: {e}")
            import traceback
            traceback.print_exc()
    
    def reset_seismic_range(self):
        """Reset range filter and show all data"""
        self.using_range_filter = False
        
        # If we have a max value, emit signal with full range
        if hasattr(self, 'last_max_abs_value') and self.last_max_abs_value is not None:
            self.seismic_range_changed.emit(-self.last_max_abs_value, self.last_max_abs_value)
        
        # Update the visualization
        self.update()
    
    def update_well_path(self, path_points):
        """Update well path display"""
        self.well_path_points = path_points
        self.update()
    
    def add_zone_marker(self, position, tick_size, color='black'):
        """Add a vertical line as a zone marker"""
        self.zone_markers.append({
            'position': position,
            'tick_size': tick_size,
            'color': QColor(color)
        })
        self.update()
    
    def add_zone_fill(self, points, color, tick_size):
        """Add colored fill between zone markers"""
        if len(points) < 2:
            return
        
        self.zone_fills.append({
            'points': points,
            'color': color,
            'tick_size': tick_size,
            'opacity': 0.7  # Default opacity
        })
        self.update()
    
    def add_grid_line(self, points, color):
        """Add a grid line with comprehensive debugging and initialization support"""
        # Ensure grid_lines list exists
        if not hasattr(self, 'grid_lines'):
            print("🆕 Initializing grid_lines list")
            self.grid_lines = []
    
        # Validate input
        if points is None:
            print("❌ Cannot add grid line: points are None")
            return
    
        if len(points) < 2:
            print(f"❌ Cannot add grid line: insufficient points ({len(points)})")
            return
    
        # Validate point structure
        if not all(isinstance(p, (list, tuple)) and len(p) == 2 for p in points):
            print(f"❌ Invalid point structure: {points}")
            return
    
        # Convert color to tuple if it's a QColor
        if hasattr(color, 'redF'):
            color = (color.redF(), color.greenF(), color.blueF())
    
        # Create grid line dictionary
        grid_line = {
            'points': points,
            'color': color
        }
    
        # Extensive logging
        print("🌐 Adding Grid Line:")
        print(f"  Total Points: {len(points)}")
    
        # Log point ranges
        x_values = [p[0] for p in points]
        y_values = [p[1] for p in points]
    
        print(f"  X Range: {min(x_values)} to {max(x_values)}")
        print(f"  Y Range: {min(y_values)} to {max(y_values)}")
        print(f"  Color: {color}")
    
        # Add to grid lines
        self.grid_lines.append(grid_line)
    
        # Print total grid lines after addition
        print(f"🔢 Total Grid Lines: {len(self.grid_lines)}")
    
        # Trigger update
        self.update()
    def update_timing_lines(self):
        """Update timing lines based on current seismic data"""
        if not hasattr(self, 'time_axis') or self.time_axis is None or len(self.time_axis) == 0:
            return
    
        # Calculate time intervals (10 divisions)
        time_min = min(self.time_axis)
        time_max = max(self.time_axis)
        time_intervals = np.linspace(time_min, time_max, 11)
    
        # Calculate distance intervals if available
        distance_intervals = None
        if hasattr(self, 'seismic_distances') and self.seismic_distances is not None and len(self.seismic_distances) > 0:
            distance_min = min(self.seismic_distances)
            distance_max = max(self.seismic_distances)
            distance_intervals = np.linspace(distance_min, distance_max, 11)
    
        # Add the timing lines
        self.add_timing_lines(time_intervals, distance_intervals)
    
    def update_zones(self, zone_data, tick_size=20, color_map=None, min_val=None, max_val=None):
        """Update zone markers and fills"""
        # Clear old items
        self.clear_zone_items()
        
        for zone in zone_data:
            # Add top marker
            self.add_zone_marker(
                (zone['top_cum_dist'], zone['top_tvd']), 
                tick_size=tick_size
            )
            
            # Add colored zone fill
            if color_map and 'attribute_value' in zone:
                color = color_map(zone['attribute_value'], min_val, max_val)
                
                self.add_zone_fill(
                    [
                        (zone['top_cum_dist'], zone['top_tvd']), 
                        (zone['base_cum_dist'], zone['base_tvd'])
                    ],
                    QColor(color.red(), color.green(), color.blue()),
                    tick_size
                )
        
        self.update()
    
    def update_transparency(self, value):
        """Update transparency of zone fills"""
        opacity = value / 100.0  # Convert percentage to decimal
        for zone_fill in self.zone_fills:
            zone_fill['opacity'] = opacity
        self.update()
    
    def wheelEvent(self, event):
        """Handle zoom with mouse wheel"""
        # Get the mouse position for zoom to center
        mouse_pos = event.position()
        
        # Calculate zoom factor
        zoom_factor = 1.1
        if event.angleDelta().y() < 0:
            zoom_factor = 1.0 / zoom_factor
        
        # Check for modifiers
        if event.modifiers() == Qt.ControlModifier:
            # Zoom vertically only
            self.scale_y *= zoom_factor
        else:
            # Zoom both axes
            self.zoom_level /= zoom_factor
            
            # Adjust offset to zoom toward mouse position
            viewport_center_x = self.width() / 2
            viewport_center_y = self.height() / 2
            
            dx = (mouse_pos.x() - viewport_center_x) / self.width()
            dy = (mouse_pos.y() - viewport_center_y) / self.height()
            
            self.offset_x += dx * (1 - zoom_factor)
            self.offset_y += dy * (1 - zoom_factor)
        
        # Update projection matrix
        self.updateProjectionMatrix()
        
        # Trigger redraw
        self.update()
        
        event.accept()
    
    def mousePressEvent(self, event):
        """Handle mouse press events for panning"""
        try:
            if event.button() == Qt.MiddleButton or event.button() == Qt.LeftButton:
                self.dragging = True
                self.last_mouse_pos = event.position()
                self.setCursor(Qt.ClosedHandCursor)
                event.accept()
            elif event.button() == Qt.RightButton:
                # Safely ignore right clicks
                print("Right click ignored for stability")
                event.accept()
            else:
                super().mousePressEvent(event)
        except Exception as e:
            print(f"Error in mousePressEvent: {e}")
            import traceback
            traceback.print_exc()
            event.accept()
    def mouseMoveEvent(self, event):
        """Handle mouse move events for panning"""
        if self.dragging and self.last_mouse_pos:
            delta = event.position() - self.last_mouse_pos
            
            # Scale delta by zoom level
            dx = delta.x() / self.width() * 2 * self.zoom_level
            dy = delta.y() / self.height() * 2 * self.zoom_level
            
            # Update offset
            self.offset_x += dx
            self.offset_y -= dy  # Invert y-axis for intuitive panning
            
            # Store new position
            self.last_mouse_pos = event.position()
            
            # Trigger redraw
            self.update()
            
            event.accept()
        else:
            super().mouseMoveEvent(event)
    
    def mouseReleaseEvent(self, event):
        """Handle mouse release events"""
        if event.button() == Qt.MiddleButton or event.button() == Qt.LeftButton:
            self.dragging = False
            self.setCursor(Qt.ArrowCursor)
            event.accept()
        else:
            super().mouseReleaseEvent(event)
    
    def fitHorizontally(self):
        """Fit the view horizontally to the available space"""
        if not self.seismic_distances:
            return
        
        # Reset zoom and offsets
        self.zoom_level = 1.0
        self.offset_x = 0.0
        self.offset_y = 0.0
        
        # Update projection
        self.updateProjectionMatrix()
        self.update()
    
    def resetView(self):
        """Reset the view to default settings"""
        self.zoom_level = 1.0
        self.offset_x = 0.0
        self.offset_y = 0.0
        self.scale_y = -1.0  # Flip vertically by default
        
        self.updateProjectionMatrix()
        self.update()




class Plot(QDialog):
    closed = Signal()
    
    def __init__(self, UWI_list, directional_surveys_df, depth_grid_data_df, grid_info_df, kd_tree_depth_grids, 
                 current_UWI, depth_grid_data_dict, db_manager, seismic_db_manager, parent=None):
        super().__init__(parent)
        self.setWindowFlags(self.windowFlags() | Qt.WindowMinMaxButtonsHint | Qt.Window)
        self.resize(1200, 800)  # Set an initial size

        # Store references to data
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
        self.selected_zone = None

        # Initialize well data
        self.current_well_data = self.directional_surveys_df[
            self.directional_surveys_df['UWI'] == self.current_UWI
        ].reset_index(drop=True)

        # Initialize the OpenGL widget but don't set up the layout yet
        self.plot_widget = SeismicOpenGLWidget(self, plot_instance=self)  # Parent and plot instance
        self.plot_widget.setParent(self)  # Extra safety with setParent call
        self.plot_widget.setMinimumSize(600, 600)
        self._safe_reference = self.plot_widget

        # Let init_ui handle all the layout setup
        self.init_ui()
        
        # Force a layout update and resize event
        QTimer.singleShot(100, self.adjustSize)





    def init_ui(self):
        labels = [
            "Well", "Zone", "Attribute", "Color Bar",
            "Tick Size", "Display", "Heat",
            "Transparency", "Seismic"
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

        # Create main layout
        main_layout = QHBoxLayout(self)  # Set as dialog's layout

        # Control Layout setup
        control_layout = QVBoxLayout()

        # Create and populate frames
        wellFrame, wellLayout = self.create_section("Well Navigation", fixed_height=90)
        self.setup_well_section(wellFrame, wellLayout)
    

        seismicFrame, seismicLayout = self.create_section("Seismic Display", fixed_height=270)
        self.setup_seismic_section(seismicFrame, seismicLayout)

        zoneFrame, zoneLayout = self.create_section("Zone and Attribute", fixed_height=170)
        self.setup_zone_section(zoneFrame, zoneLayout)

        tickFrame, tickLayout = self.create_section("Tick Settings", fixed_height=150)
        self.setup_tick_section(tickFrame, tickLayout)

        # Add frames to control layout
        # Add frames to control layout
        control_layout.addWidget(wellFrame)
        control_layout.addWidget(seismicFrame)
        control_layout.addWidget(zoneFrame)
        control_layout.addWidget(tickFrame)
        control_layout.addStretch()

        # Create plot container with the OpenGL widget
        plot_container = QFrame()
        plot_container.setFrameStyle(QFrame.Panel | QFrame.Raised)
        plot_container.setMinimumSize(800, 600)  # Ensure minimum size
        plot_container.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 2px solid #A0A0A0;
                border-radius: 6px;
                padding: 0px;
            }
        """)

        # Create layout for the plot container
        plot_layout = QVBoxLayout(plot_container)
        plot_layout.setContentsMargins(2, 2, 2, 2)
    
        # Add the OpenGL widget to the plot container
        plot_layout.addWidget(self.plot_widget)

        # Add both layouts to the main layout with appropriate stretch factors
        main_layout.addLayout(control_layout, 1)  # Smaller portion for controls
        main_layout.addWidget(plot_container, 7)  # Larger portion for the plot

        # Set up connections
        self.setup_connections()

        # Initial population
        try:
            self.populate_zone_names()
        except Exception as e:
            print(f"❌ Error in populate_zone_names(): {e}")

        # Trigger well selection for the initial well
        if 0 <= self.current_index < len(self.UWI_list):
            self.on_well_selected(self.current_index)
        else:
            print(f"⚠️ Invalid current_index: {self.current_index}, skipping on_well_selected()")
        
        # Print debug info
        print(f"Dialog size after init_ui: {self.width()}x{self.height()}")
    def create_section(self, frame_name, fixed_height=None):
        """
        Create a framed section with optional fixed height
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
        current_palette_name = self.seismic_colorbar.currentText()
        current_palette = self.seismic_colorbar.load_color_palette(current_palette_name)
        print(f"Current Palette: {current_palette_name}")
        print(f"Number of Colors: {len(current_palette)}")
            # Diagnostic print statements
       
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
        
        # Connect transparency slider to OpenGL widget
        self.transparency_slider.slider.valueChanged.connect(
            lambda value: self.plot_widget.update_transparency(value)
        )
        
        self.seismic_colorbar.colorbar_dropdown.combo.currentIndexChanged.connect(self.update_seismic_colorbar)

    def check_widget_status(self):
        """Check if the widget is still valid and attempt recovery if needed."""
        if not hasattr(self, 'plot_widget') or not self.plot_widget or not self.plot_widget.isValid():
            print("⚠️ OpenGL widget appears to be invalid - attempting recovery")
            try:
                old_widget = self.plot_widget

                # Create a new OpenGL widget
                self.plot_widget = SeismicOpenGLWidget(plot_instance=self)
                self.plot_widget.setMinimumSize(400, 400)
                self._safe_reference = self.plot_widget

                # Replace in layout
                if hasattr(self, 'plot_layout'):
                    for i in range(self.plot_layout.count()):
                        item = self.plot_layout.itemAt(i)
                        if item and item.widget() == old_widget:
                            self.plot_layout.replaceWidget(old_widget, self.plot_widget)
                            break
                else:
                    print("❌ plot_layout not available for widget recovery")

                # Replot data
                QTimer.singleShot(100, self.plot_current_well)
            except Exception as recovery_error:
                print(f"❌ Recovery failed: {recovery_error}")
                import traceback
                traceback.print_exc()


    def closeEvent(self, event):
        try:
            print("Window closing, cleaning up resources...")
            # Release any OpenGL resources
            if hasattr(self, 'plot_widget') and self.plot_widget:
                self.plot_widget.cleanup()
        
            # Call parent implementation
            super().closeEvent(event)
            print("Clean shutdown complete")
        except Exception as e:
            print(f"❌ Error during shutdown: {e}")
            import traceback
            traceback.print_exc()



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
            
            # Plot the data with OpenGL widget
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

    def update_seismic_colorbar(self):
        """Update the seismic display colorbar when color palette changes"""
        try:
            # Get the color palette
            color_palette = self.seismic_colorbar.selected_color_palette
            
            # If we have seismic data, rerender with the new palette
            if hasattr(self.plot_widget, 'seismic_data') and self.plot_widget.seismic_data is not None:
                # Reapply the current seismic data with the new palette
                self.plot_widget.update_seismic_data(
                    self.plot_widget.seismic_data,
                    self.plot_widget.seismic_distances,
                    self.plot_widget.time_axis
                )
        except Exception as e:
            print(f"Error updating seismic colorbar: {e}")
            import traceback
            traceback.print_exc()
    
    def update_seismic_range(self, min_val, max_val):
        """Update seismic range filtering"""
        try:
            # Early returns if requirements aren't met
            if not hasattr(self.plot_widget, 'seismic_data') or self.plot_widget.seismic_data is None:
                return
            
            # Store range parameters 
            self.plot_widget.heat_adjusted_min = min_val
            self.plot_widget.heat_adjusted_max = max_val
            self.plot_widget.using_range_filter = True
            
            # Rerender with the current settings
            self.update_seismic_colorbar()
            
        except Exception as e:
            print(f"Error updating seismic range: {e}")
    
    def update_heat_value(self, value):
        """Update heat value (contrast adjustment)"""
        try:
            # Early returns if requirements aren't met
            if not hasattr(self.plot_widget, 'seismic_data') or self.plot_widget.seismic_data is None:
                return
            
            # Calculate adjusted range based on heat value
            heat_factor = max(0.05, 1 - (value / 100))
            max_abs_value = self.plot_widget.last_max_abs_value if hasattr(self.plot_widget, 'last_max_abs_value') else 1.0
            
            adjusted_min = -max_abs_value * heat_factor
            adjusted_max = max_abs_value * heat_factor
            
            # Update display range indicators
            self.seismic_colorbar.display_color_range(adjusted_min, adjusted_max)
            if hasattr(self, 'seismic_range_slider'):
                self.seismic_range_slider.setRange(adjusted_min, adjusted_max)
                self.seismic_range_slider.setValue([adjusted_min, adjusted_max])
            
            # Store parameters
            self.plot_widget.heat_adjusted_min = adjusted_min
            self.plot_widget.heat_adjusted_max = adjusted_max
            self.plot_widget.using_heat_adjustment = True
            
            # Rerender with the current settings
            self.update_seismic_colorbar()
            
        except Exception as e:
            print(f"Error updating heat value: {e}")
    
    def populate_zone_names(self):
        self.zone_selector.blockSignals(True)
        # Clear existing items
        self.zone_selector.clear()

        # Add default option
        self.zone_selector.addItem("Select Zone")

        try:
            # Fetch unique zone names from the database where type is 'Zone'
            zones = self.db_manager.fetch_zone_names_by_type("Zone")

            if zones:
                # Sort zones alphabetically
                zones = [zone[0] for zone in zones if zone[0].strip()] 
                zones = sorted(zones)
             
                # Populate the dropdown with sorted zone names
                self.zone_selector.addItems(zones)
            else:
                print("No zones of type 'Zone' found.")

        except Exception as e:
            print(f"Error populating Zone dropdown: {e}")

        finally:
            # Unblock signals after populating the dropdown
            self.zone_selector.blockSignals(False)
            self.zone_attribute_selector.combo.setEnabled(True)

    def populate_zone_attribute(self):
        """Update the zone attribute selector based on the selected zone"""
        self.zone_attribute_selector.blockSignals(True)
        self.zone_attribute_selector.setEnabled(True)

        if self.selected_zone_df is None or self.selected_zone_df.empty:
            # No data available
            self.zone_attribute_selector.clear()
            self.zone_attribute_selector.addItem("Select Zone Attribute")
            self.zone_attribute_selector.blockSignals(False)
            return
      
        # Columns to exclude from attribute selection
        columns_to_exclude = [
            'id', 'Zone_Name', 'Zone_Type', 'Attribute_Type',
            'Top_Depth', 'Base_Depth', 'UWI', 'Top_X_Offset',
            'Base_X_Offset', 'Top_Y_Offset', 'Base_Y_Offset',
            'Angle_Top', 'Angle_Base', 'Base_TVD', 'Top_TVD'
        ]

        # Drop fixed columns and find columns with at least one non-null value
        zone_df = self.selected_zone_df.drop(columns=columns_to_exclude, errors='ignore')
        self.attributes_names = sorted(zone_df.columns[zone_df.notna().any()].tolist())
    
        # Clear and populate the attribute selector
        self.zone_attribute_selector.clear()
        self.zone_attribute_selector.addItem("Select Zone Attribute")
        self.zone_attribute_selector.addItems(self.attributes_names)
    
        # Set default selection to the first item
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
        """Find the closest seismic trace for each well point, store it, and visualize using OpenGL"""
        try:
            # ✅ Step 1: Load Well Data
            self.current_well_data = self.directional_surveys_df[
                self.directional_surveys_df['UWI'] == self.current_UWI
            ].reset_index(drop=True)

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

                # Get distances and indices for all well points
                distances, indices = seismic_kdtree.query(well_coords)
            
                # Print information for debugging if inline/crossline data is available
                if 'inlines' in f['geometry'] and 'crosslines' in f['geometry']:
                    inline_numbers = f['geometry']['inlines'][:]
                    crossline_numbers = f['geometry']['crosslines'][:]
                
                    # Print details for the first attribute
                    print("\nWell point information:")
                    for i, (idx, dist) in enumerate(zip(indices, distances)):
                        if i % 10 == 0:  # Print every 10th point to avoid too much output
                            print(f"Well point {i}: MD position {self.current_well_data['MD'].iloc[i]:.2f}, "
                                  f"Cumulative distance {self.combined_distances[i]:.2f}, "
                                  f"Nearest trace at inline {inline_numbers[idx]}, crossline {crossline_numbers[idx]}, "
                                  f"distance: {dist:.2f}")

                # Ensure indices are valid
                max_index = f['attributes'][all_attributes[0]]['trace_data'].shape[0] - 1
                indices = np.clip(indices, 0, max_index)

                # Iterate through all attributes and store traces
                for attribute in all_attributes:
                    # Get the attribute group
                    attribute_group = f['attributes'][attribute]
    
                    # Load trace data
                    trace_data = attribute_group['trace_data'][:]

                    # Read Seismic Traces
                    seismic_trace_amplitudes = []
                    for idx in indices:
                        try:
                            trace = trace_data[idx, :]
                            seismic_trace_amplitudes.append(trace)
                        except Exception as e:
                            print(f"❌ ERROR: Failed to load trace for attribute {attribute}, index {idx}: {e}")
                            # Add a zero array of the correct size to maintain indexing
                            seismic_trace_amplitudes.append(np.zeros(len(time_axis)))

                    # Convert to numpy array
                    seismic_trace_amplitudes = np.array(seismic_trace_amplitudes)

                    # Pre-allocate the seismic data array
                    seismic_data = np.zeros((len(time_axis), len(self.combined_distances)))
                
                    # Fill the seismic data array with trace amplitudes
                    for i in range(len(self.combined_distances)):
                        seismic_data[:, i] = seismic_trace_amplitudes[i]

                    # Store data for this attribute
                    self.well_attribute_traces[self.current_UWI][attribute] = {
                        'seismic_data': seismic_data,
                        'unique_distances': self.combined_distances,
                        'unique_times': time_axis
                    }

                # Access the data for visualization
                selected_data = self.well_attribute_traces[self.current_UWI][self.selected_attribute]
            
                # Update the OpenGL widget with seismic data
                self.plot_widget.update_seismic_data(
                    selected_data['seismic_data'],
                    selected_data['unique_distances'],
                    selected_data['unique_times']
                )
            
                # Update well path in the OpenGL widget
                path_points = list(zip(self.combined_distances, self.tvd_values))
                self.plot_widget.update_well_path(path_points)
            
                # Update timing lines in the OpenGL widget
                self.plot_widget.update_timing_lines()

                # ✅ Process Grid Intersections
                print("🔍 Processing grid intersections...")

                # Debug: Print available attributes
                print("Depth Grid Dictionary Keys:", list(self.depth_grid_data_dict.keys()))
                print("KD Tree Depth Grids Keys:", list(self.kd_tree_depth_grids.keys()))

                grid_values = {}
                sorted_grids = sorted(self.kd_tree_depth_grids.keys())

                # Diagnostic print to verify sorted grids
                print("Grid names:", sorted_grids)
                print("Number of grids:", len(sorted_grids))

                # Detailed grid dictionary diagnostic
                def print_depth_grid_details(depth_grid_dict):
                    print("🌍 Depth Grid Dictionary Details:")
                    for grid_name, grid_data in depth_grid_dict.items():
                        print(f"Grid: {grid_name}")
                        print(f"  Total points: {len(grid_data)}")
                        print(f"  Data type: {type(grid_data)}")
                        if hasattr(grid_data, 'dtype'):
                            print(f"  Data dtype: {grid_data.dtype}")
                        if len(grid_data) > 0:
                            try:
                                print(f"  Value range: {min(grid_data)} to {max(grid_data)}")
                            except Exception as e:
                                print(f"  Error getting value range: {e}")
                                print(f"  First few values: {grid_data[:5]}")

                # Call this diagnostic method
                print_depth_grid_details(self.depth_grid_data_dict)

                # Validate well coordinates
                print("Well Coordinates:")
                print(f"  Total points: {len(well_coords)}")
                print(f"  First few points: {well_coords[:5]}")

                for grid_name in sorted_grids:
                    print(f"\n🔍 Processing Grid: {grid_name}")
    
                    # Validate KD Tree
                    kdtree = self.kd_tree_depth_grids[grid_name]
                    print(f"  KD Tree data size: {kdtree.data.size}")
    
                    # Validate depth grid data
                    if grid_name not in self.depth_grid_data_dict:
                        print(f"  ❌ Grid {grid_name} not found in depth grid dictionary")
                        continue
    
                    grid_values[grid_name] = []
    
                    for i, (x2, y2) in enumerate(well_coords):
                        try:
                            if kdtree.data.size > 0:
                                _, indices = kdtree.query((x2, y2))
                
                                # Add extensive logging
                                print(f"  Well Point {i}: x={x2}, y={y2}")
                                print(f"    Nearest indices: {indices}")
                
                                if indices < len(self.depth_grid_data_dict[grid_name]):
                                    value = self.depth_grid_data_dict[grid_name][indices]
                                    grid_values[grid_name].append(value)
                                    print(f"    Appended value: {value}")
                                else:
                                    print(f"    ❌ Invalid index: {indices}")
                        except Exception as e:
                            print(f"  ❌ Error processing well point {i}: {e}")

                # Print grid intersection details after collecting all values
                self.print_grid_intersection_details(grid_values, sorted_grids)

                print("🔲 Adding Grid Lines:")
                for i, grid_name in enumerate(sorted_grids):
                    try:
                        # Find the grid row in grid_info_df
                        grid_row = self.grid_info_df.loc[self.grid_info_df['Grid'] == grid_name]
                        if grid_row.empty:
                            print(f"  ❌ No grid info found for {grid_name}")
                            continue
        
                        # Extract color information
                        current_color = grid_row['Color (RGB)'].values[0]
                        print(f"  Grid: {grid_name}")
                        print(f"    Color: {current_color}")
        
                        # Create points for grid line
                        current_points = list(zip(self.combined_distances, grid_values[grid_name]))

                        # Diagnostic print of points
                        print(f"    Points count: {len(current_points)}")
                        if current_points:
                            print(f"    X range: {min(p[0] for p in current_points)} to {max(p[0] for p in current_points)}")
                            print(f"    Y range: {min(p[1] for p in current_points)} to {max(p[1] for p in current_points)}")

                        # Add grid line to OpenGL widget
                        self.plot_widget.add_grid_line(current_points, current_color)
    
                    except Exception as e:
                        print(f"❌ Error processing grid {grid_name}: {e}")
                        import traceback
                        traceback.print_exc()

            try:
                print("Starting final rendering and display...")
            
                # More comprehensive update mechanism
                QApplication.processEvents()  # Process any pending events
            
                # Explicitly call update methods
                self.plot_widget.update()
            
                # Force a repaint
                self.plot_widget.repaint()
            
                # Additional Qt event processing
                QApplication.processEvents()
            
                print("Update called successfully")
            
                # Instead of sleep, use a shorter timeout
                QTimer.singleShot(100, self.finalize_rendering)
            
            except Exception as e:
                print(f"❌ Exception during final rendering: {e}")
                import traceback
                traceback.print_exc()
    
        except Exception as e:
            print(f"❌ CRITICAL ERROR in plot_current_well: {e}")
            import traceback
            traceback.print_exc()


    def print_grid_intersection_details(self, grid_values, sorted_grids):
        """Print detailed information about grid intersections"""
        print("🌐 Grid Intersection Diagnostic:")
        for grid_name in sorted_grids:
            print(f"Grid: {grid_name}")
        
            # Check if grid exists in grid_values
            if grid_name not in grid_values:
                print(f"  ❌ No grid values found for {grid_name}")
                continue
        
            grid_intersections = grid_values[grid_name]
        
            print(f"  Total Intersections: {len(grid_intersections)}")
        
            if grid_intersections:
                # Print first few intersections
                print("  Sample Intersections:")
                for i, value in enumerate(grid_intersections[:5]):
                    print(f"    Intersection {i}: {value}")
            
                # Print range of values
                print(f"  Value Range: {min(grid_intersections)} to {max(grid_intersections)}")


    def finalize_rendering(self):
        try:
            print("Finalizing rendering...")
            print("Finalizing rendering...")
            self.plot_widget.update()
            self.plot_widget.repaint()
            self.plot_widget.update()
  # ⬅️ Ensures frame is displayed
        
            # Additional checks and potential recovery steps
            if self.plot_widget is None:
                print("❌ Plot widget is None!")
                return
        
            # Verify data is loaded
            if (not hasattr(self.plot_widget, 'seismic_data') or 
                self.plot_widget.seismic_data is None):
                print("⚠️ No seismic data loaded")
        
            # Additional diagnostic information
            print(f"OpenGL Widget Valid: {self.plot_widget.isValid()}")
            print(f"OpenGL Widget Visible: {self.plot_widget.isVisible()}")
        
            # Use single shot timer instead of direct update call
            QTimer.singleShot(50, self.plot_widget.update)
        
            print("Rendering completed")
    
        except Exception as e:
            print(f"❌ Error in finalize_rendering: {e}")
            import traceback
            traceback.print_exc()
    
    def update_tick_size_value_label(self, value):
        """Update tick size without reloading the entire plot"""
        self.tick_size_value = value
    
        # If a zone is selected, update the ticks with new size
        if self.selected_zone and self.selected_zone != "Select_Zone":
            self.update_zone_ticks()
    
    def update_zone_ticks(self):
        """Update zone ticks in the OpenGL widget"""
        if not self.selected_zone or self.selected_zone == "Select_Zone":
            return

        try:
            # Prepare zone data for OpenGL widget
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

            # Update zones in OpenGL widget
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
    
    def zone_selected(self):
        print("zone_selected() was triggered!")

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
            
            # Clear zone markers in OpenGL widget
            self.plot_widget.clear_zone_items()
        else:
            try:
                # Fetch zone data
                self.selected_zone_df = self.db_manager.fetch_table_data(self.selected_zone)
                
                # Update zone ticks and attributes
                self.update_zone_ticks()
                self.populate_zone_attribute()
        
            except Exception as e:
                print(f"Error fetching zone data: {str(e)}")
                self.selected_zone_df = None
    
    def on_well_selected(self, index):
        try:
            selected_UWI = self.well_selector.currentText()
            if selected_UWI in self.UWI_list:
                self.current_UWI = selected_UWI
                self.current_index = index
            
                # Update the current well's data
                self.current_well_data = self.directional_surveys_df[
                    self.directional_surveys_df['UWI'] == self.current_UWI
                ].reset_index(drop=True)
                
                # Get well coordinates
                well_coords = np.column_stack((
                    self.current_well_data['X Offset'],
                    self.current_well_data['Y Offset']
                ))
                
                # Find intersecting seismic files
                self.intersecting_files = self.get_intersecting_seismic_files(well_coords)
                
                # Populate seismic selector
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
            self.on_well_selected(self.current_index)  # This will reload data and update UI
        except Exception as e:
            QMessageBox.critical(self, "Error", f"An error occurred while processing the next well: {str(e)}")
    
    def on_prev(self):
        """Navigate to the previous well in alphabetical order, stopping at the first well."""
        try:
            if self.current_index > 0:
                self.current_index -= 1
                self.current_UWI = self.UWI_list[self.current_index]
                self.update_well_selector_to_current_UWI()
                self.on_well_selected(self.current_index)  # This will reload data and update UI
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

    def cleanup(self):
        """Clean up OpenGL resources properly"""
        try:
            self.makeCurrent()
        
            # Clean up shader programs
            for shader in [self.shader_program, self.well_shader, self.zone_shader]:
                if shader:
                    shader.release()
                
            # Clean up texture
            if self.texture:
                self.texture.destroy()
            
            # Clean up buffers
            for buffer in [self.vbo, self.ebo, self.well_vbo]:
                if buffer:
                    buffer.destroy()
                
            # Clean up VAOs
            for vao in [self.vao, self.well_vao]:
                if vao:
                    vao.destroy()
                
            self.doneCurrent()
        except Exception as e:
            print(f"Error during cleanup: {e}")
