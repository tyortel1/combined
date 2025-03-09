import os
from PySide6.QtWidgets import QWidget, QHBoxLayout,QSpinBox, QFrame, QVBoxLayout, QGraphicsDropShadowEffect, QComboBox, QCheckBox, QLabel, QSlider, QScrollArea, QSizePolicy, QMenuBar, QMenu, QToolBar, QToolButton
from PySide6.QtCore import Qt, QMetaObject, QSize
from PySide6.QtGui import QIcon,  QPalette, QColor, QAction

from DrawingArea import DrawingArea
from StyledDropdown import StyledDropdown
from StyledButton import StyledButton
from StyledColorbar import StyledColorBar




class Ui_MainWindow:
    def setupUi(self, MainWindow):
        # Basic window setup
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(1500, 1500)
        MainWindow.centralWidget = QWidget(MainWindow)
        MainWindow.setCentralWidget(MainWindow.centralWidget)
        MainWindow.centralWidget.setStyleSheet("background-color: white;")

        # Main layout
        MainWindow.mainLayout = QHBoxLayout(MainWindow.centralWidget)

        # Options layout - Significantly reduced spacing
        MainWindow.optionsLayout = QVBoxLayout()
        MainWindow.optionsLayout.setSpacing(2)  # Reduced drastically
        MainWindow.optionsLayout.setAlignment(Qt.AlignTop)

        def create_section(frame_name, fixed_height=None):
            frame = QFrame(MainWindow)
            frame.setFrameStyle(QFrame.Panel | QFrame.Raised)
            frame.setStyleSheet("""
                QFrame {
                    background-color: white;
                    border: 2px solid #A0A0A0; /* Slightly darker border for depth */
                    border-radius: 6px;
                    padding: 4px;
                }
            """)
            if fixed_height:
                frame.setFixedHeight(fixed_height)  # Set fixed height if provided
                frame.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)  # Prevent stretching

            # Apply 3D Drop Shadow
            shadow = QGraphicsDropShadowEffect()
            shadow.setBlurRadius(10)  # Softer shadow
            shadow.setXOffset(3)  # Slight right shadowF
            shadow.setYOffset(3)  # Slight bottom shadow
            shadow.setColor(QColor(0, 0, 0, 100))  # Semi-transparent black shadow

            frame.setGraphicsEffect(shadow)  # Apply effect



            layout = QVBoxLayout(frame)
            layout.setSpacing(1)  # Minimal spacing
            layout.setContentsMargins(5, 5, 5, 5)  # Reduce margins
            layout.setAlignment(Qt.AlignTop)  # Align everything to the top
            return frame, layout



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

        def create_colorbar():
            colorbar = StyledColorBar("Color Bar", parent=MainWindow)
            colorbar.setStyleSheet("""
                QLabel {
                    background-color: transparent;
                    border: none;
                    padding: 0;
                    margin: 0;
                }
            """)
            # No need to set contents margins as StyledBaseWidget handles alignment
            return colorbar

        labels = [
            "Zone",
            "Attribute",
            "Well",
            "Grid",
            "Well Zone"  # Including all possible labels used in dropdowns
        ]


        StyledDropdown.calculate_label_width(labels)


        # Zone Section
        MainWindow.zoneFrame, MainWindow.zoneLayout = create_section("Zone", fixed_height=170)
        MainWindow.zoneDropdown = create_dropdown("Zone")
        MainWindow.zoneAttributeDropdown = create_dropdown("Attribute")
        MainWindow.zone_colorbar = create_colorbar()

        MainWindow.zoneDropdown.combo.addItem("Select Zone")
        MainWindow.zoneAttributeDropdown.combo.addItem("Select Zone Attribute")

        MainWindow.zoneLayout.addWidget(MainWindow.zoneDropdown)
        MainWindow.zoneLayout.addWidget(MainWindow.zoneAttributeDropdown)
        MainWindow.zoneLayout.addWidget(MainWindow.zone_colorbar)
        MainWindow.optionsLayout.addWidget(MainWindow.zoneFrame)

        # Well Section
        MainWindow.wellZoneFrame, MainWindow.wellZoneLayout = create_section("Well Zone", fixed_height=170)
        MainWindow.wellZoneDropdown = create_dropdown("Well")
        MainWindow.wellAttributeDropdown = create_dropdown("Attribute")
        MainWindow.well_colorbar = create_colorbar()

        MainWindow.wellZoneDropdown.combo.addItem("Select Well Zone")
        MainWindow.wellAttributeDropdown.combo.addItem("Select Well Attribute")

        MainWindow.wellZoneLayout.addWidget(MainWindow.wellZoneDropdown)
        MainWindow.wellZoneLayout.addWidget(MainWindow.wellAttributeDropdown)
        MainWindow.wellZoneLayout.addWidget(MainWindow.well_colorbar)
        MainWindow.optionsLayout.addWidget(MainWindow.wellZoneFrame)

        # Grid Section
        MainWindow.gridFrame, MainWindow.gridLayout = create_section("Grid", fixed_height=140)
        MainWindow.gridDropdown = create_dropdown("Grid")
        MainWindow.grid_colorbar = create_colorbar()

        MainWindow.gridDropdown.combo.addItem("Select Grid")

        MainWindow.gridLayout.addWidget(MainWindow.gridDropdown)
        MainWindow.gridLayout.addWidget(MainWindow.grid_colorbar)
        MainWindow.optionsLayout.addWidget(MainWindow.gridFrame)

        MainWindow.optionsLayout.addStretch()

        # Add options layout to main layout
        MainWindow.mainLayout.addLayout(MainWindow.optionsLayout, 1)

        # Reduce overall margins to make the UI tighter
        MainWindow.optionsLayout.setContentsMargins(2, 2, 2, 2)



        # Scroll area for the drawing area
        MainWindow.scrollArea = QScrollArea(MainWindow.centralWidget)
        MainWindow.scrollArea.setObjectName("scrollArea")
        MainWindow.scrollArea.setWidgetResizable(True)
        MainWindow.drawingArea = DrawingArea(MainWindow)
        MainWindow.drawingArea.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)


        # Set background color to very light grey
        light_grey = QColor(200, 200, 200)  # Define a very light grey color
        palette = MainWindow.drawingArea.palette()  # Get the current palette
        palette.setColor(QPalette.Window, light_grey)  # Set the background color
        MainWindow.drawingArea.setPalette(palette)
        MainWindow.drawingArea.setAutoFillBackground(True) 
        MainWindow.scrollArea.setWidget(MainWindow.drawingArea)
        MainWindow.mainLayout.addWidget(MainWindow.scrollArea, 7)
        MainWindow.drawingArea.leftClicked.connect(MainWindow.handle_left_click)
        MainWindow.drawingArea.rightClicked.connect(MainWindow.handle_right_click)



        # Menu bar
        MainWindow.menu_bar = QMenuBar(MainWindow)
        MainWindow.setMenuBar(MainWindow.menu_bar)

        # Project Menu
        file_menu = MainWindow.menu_bar.addMenu("Project")

        MainWindow.new_project_action = QAction("Create", MainWindow)
        file_menu.addAction(MainWindow.new_project_action)
        
        MainWindow.open_action = QAction("Open", MainWindow)
        file_menu.addAction(MainWindow.open_action)

        # Prepare Attributes Menu (Renamed from Calculate)
        MainWindow.prepare_attributes_menu = MainWindow.menu_bar.addMenu("Prepare Attributes")
        MainWindow.prepare_attributes_menu.setEnabled(False)

        MainWindow.calc_stage_action = QAction("Calculate Stages", MainWindow)
        MainWindow.prepare_attributes_menu.addAction(MainWindow.calc_stage_action)

        MainWindow.calc_grid_to_zone_action = QAction("Grid To Zone", MainWindow)
        MainWindow.prepare_attributes_menu.addAction(MainWindow.calc_grid_to_zone_action)

        MainWindow.calc_inzone_action = QAction("Calculate in Zone", MainWindow)
        MainWindow.prepare_attributes_menu.addAction(MainWindow.calc_inzone_action)

        MainWindow.merge_zones_action = QAction("Merge Zones", MainWindow)
        MainWindow.prepare_attributes_menu.addAction(MainWindow.merge_zones_action)

        MainWindow.calc_zone_attb_action = QAction("Calculate Zone Attributes", MainWindow)
        MainWindow.prepare_attributes_menu.addAction(MainWindow.calc_zone_attb_action)

        MainWindow.pc_dialog_action = QAction("Calculate Parent Child", MainWindow)
        MainWindow.prepare_attributes_menu.addAction(MainWindow.pc_dialog_action)

        # Regression Menu (New)
        MainWindow.regression_menu = MainWindow.menu_bar.addMenu("Regression")
        MainWindow.regression_menu.setEnabled(False)

        MainWindow.correlation_matrix_action = QAction("Well Correlation Matrix", MainWindow)
        MainWindow.regression_menu.addAction(MainWindow.correlation_matrix_action)

        MainWindow.attribute_analyzer_action = QAction("Run Regression", MainWindow)  # Renamed
        MainWindow.regression_menu.addAction(MainWindow.attribute_analyzer_action)



        # Production Menu (New)
        MainWindow.production_menu = MainWindow.menu_bar.addMenu("Production")
        MainWindow.production_menu.setEnabled(False)

        MainWindow.pud_properties_action = QAction("Pad Production Scenarios", MainWindow)
        MainWindow.production_menu.addAction(MainWindow.pud_properties_action)

        MainWindow.well_comparison_action = QAction("Well Comparison Calculation", MainWindow)
        MainWindow.production_menu.addAction(MainWindow.well_comparison_action)


        MainWindow.dca_action = QAction("Decline Curve Analysis", MainWindow)
        MainWindow.production_menu.addAction(MainWindow.dca_action)

        MainWindow.launch_cashflow_action = QAction("Launch Combined Cashflow", MainWindow)
        MainWindow.production_menu.addAction(MainWindow.launch_cashflow_action)

        # Import Menu (Unchanged)
        MainWindow.import_menu = MainWindow.menu_bar.addMenu("Import")
        MainWindow.import_menu.setEnabled(False)

        MainWindow.connect_action = QAction("SeisWare Wells and Production", MainWindow)
        MainWindow.connect_action.triggered.connect(MainWindow.connectToSeisWare)
        MainWindow.import_menu.addAction(MainWindow.connect_action)

        MainWindow.data_loader_menu_action = QAction("SeisWare Grids", MainWindow)
        MainWindow.import_menu.addAction(MainWindow.data_loader_menu_action)

        MainWindow.import_action = QAction("CSV Production", MainWindow)
        MainWindow.import_action.triggered.connect(MainWindow.import_excel)
        MainWindow.import_menu.addAction(MainWindow.import_action)

        MainWindow.dataload_well_zones_action = QAction("CSV Well Zones and Attributes", MainWindow)
        MainWindow.import_menu.addAction(MainWindow.dataload_well_zones_action)

        MainWindow.dataload_segy_action = QAction("Import Segy", MainWindow)
        MainWindow.import_menu.addAction(MainWindow.dataload_segy_action)

        MainWindow.properties_menu = MainWindow.menu_bar.addMenu("Properties")
        MainWindow.properties_menu.setEnabled(True)

        # Well Properties
        MainWindow.well_properties_action = QAction("Well Properties", MainWindow)
        MainWindow.properties_menu.addAction(MainWindow.well_properties_action)

        # Zone related actions
        MainWindow.zone_viewer_action = QAction("Zone Properties", MainWindow)  # Renamed from Zone Properties
        MainWindow.properties_menu.addAction(MainWindow.zone_viewer_action)


        # Map Properties
        MainWindow.map_properties_action = QAction("Map Properties", MainWindow)
        MainWindow.properties_menu.addAction(MainWindow.map_properties_action)

        # Grid Properties
        MainWindow.grid_properties_action = QAction("Grid Properties", MainWindow)
        MainWindow.properties_menu.addAction(MainWindow.grid_properties_action)

        # Seismic Properties
        MainWindow.seismic_properties_action = QAction("Seismic Properties", MainWindow)
        MainWindow.properties_menu.addAction(MainWindow.seismic_properties_action)

        # Regression Properties
        MainWindow.regression_properties_action = QAction("Regression Properties", MainWindow)
        MainWindow.properties_menu.addAction(MainWindow.regression_properties_action)



        
        
        # Create the Toolbar
        MainWindow.toolbar = QToolBar("Main Toolbar", MainWindow)
        MainWindow.toolbar.setStyleSheet("""
            QToolBar {
                background-color: white;
                border: none;
                padding: 0px;  /* Remove extra padding */
            }
            QToolButton {
                padding: 2px; /* Reduce button padding */
                margin: 0px;  /* Remove unnecessary spacing */
                border-radius: 4px;
                background: transparent;
            }
            QToolButton:hover {
                background: rgba(0, 0, 0, 0.1);
            }
        """)


        MainWindow.toolbar.setIconSize(QSize(32, 32))  # Set modern icon size
        MainWindow.addToolBar(MainWindow.toolbar)

        MainWindow.setWindowIcon(QIcon("icons/ZoneAnalyzer.png"))
        MainWindow.plot_icon = QIcon("icons/plot.ico")
        MainWindow.gun_barrel_icon = QIcon("icons/gunb.ico")
        MainWindow.zoom_in_icon = QIcon("icons/Zoom_in.ico")
        MainWindow.zoom_out_icon = QIcon("icons/Zoom_out.ico")
        MainWindow.color_editor_icon = QIcon("icons/color_editor.ico")
        MainWindow.cross_plot_icon = QIcon("icons/Cross-Plot-Data-Icon.ico")
        MainWindow.launch_cashflow_icon = QIcon("icons/Launch Graph.png")
        MainWindow.launch_icon = QIcon("icons/Decline.ico")

        # Toolbar actions with spacing and grouping
        actions = [
            ("plot_tool_action", MainWindow.plot_icon, "QC Zones"),
            ("gun_barrel_action", MainWindow.gun_barrel_icon, "Create Gun Barrel"),
            ("cross_plot_action", MainWindow.cross_plot_icon, "Cross Plot"),
            ("color_editor_action", MainWindow.color_editor_icon, "Edit Grid Colors"),
        ]

        # Add first batch of actions
        for action_name, icon, text in actions:
            action = QAction(icon, text, MainWindow)
            setattr(MainWindow, action_name, action)
            MainWindow.toolbar.addAction(action)

        # Add separator to visually divide the toolbar
        MainWindow.toolbar.addSeparator()

        # Add zoom and analysis actions
        extra_actions = [
            ("zoomOut", MainWindow.zoom_out_icon, "Zoom Out"),
            ("zoomIn", MainWindow.zoom_in_icon, "Zoom In"),
            ("launch_action", MainWindow.launch_icon, "Launch Decline Curve Analysis"),
            ("cashflow_action", MainWindow.launch_cashflow_icon, "Launch Combined Cashflow")
        ]

        for action_name, icon, text in extra_actions:
            action = QAction(icon, text, MainWindow)
            setattr(MainWindow, action_name, action)
            MainWindow.toolbar.addAction(action)

        # Ensure icons have proper spacing
        MainWindow.toolbar.setContentsMargins(4, 4, 4, 4)


# Connect the action to the method that launches the secondary window
        MainWindow.launch_action.triggered.connect(MainWindow.launch_secondary_window)
        #MainWindow.exportSw = QAction(MainWindow.exportSw_icon, "Send to SeisWare", MainWindow)
        #MainWindow.toolbar.addAction(MainWindow.exportSw)
        # Add scenario dropdown to toolbar
        MainWindow.toolbar.addSeparator()
        
        # Add scenario dropdown to toolbar
        MainWindow.scenarioLabel = QLabel("Active Scenario:", MainWindow)
        MainWindow.toolbar.addWidget(MainWindow.scenarioLabel)
        MainWindow.scenarioDropdown = QComboBox(MainWindow)
        # Will be populated later with populate_scenario_dropdown
        MainWindow.scenarioDropdown.setFixedWidth(150)  # Set a reasonable width
        MainWindow.toolbar.addWidget(MainWindow.scenarioDropdown)

     

        self.retranslateUi()
        QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self):
        pass  # If you need to retranslate UI, you can add the code here

    def populate_color_bar_dropdowns(self):
        """Populate the color bar dropdowns with file names from the Palettes directory."""
        palettes_path = os.path.join(os.path.dirname(__file__), 'Palettes')
        color_bar_files = [f.split('.')[0] for f in os.listdir(palettes_path) if f.endswith('.pal')]
    
        self.zone_colorbar.addColorBarOptions(color_bar_files)
        self.well_colorbar.addColorBarOptions(color_bar_files)
        self.grid_colorbar.addColorBarOptions(color_bar_files)