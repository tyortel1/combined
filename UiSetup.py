import os
from PySide6.QtWidgets import QWidget, QHBoxLayout,QSpinBox, QFrame, QVBoxLayout,  QComboBox, QCheckBox, QLabel, QSlider, QScrollArea, QSizePolicy, QMenuBar, QMenu, QToolBar, QToolButton
from PySide6.QtCore import Qt, QMetaObject
from PySide6.QtGui import QIcon,  QPalette, QColor, QAction

from DrawingArea import DrawingArea
from StyledDropdown import StyledDropdown
from StyledButton import StyledButton
from StyledColorbar import StyledColorBar



class Ui_MainWindow:
    def setupUi(self, MainWindow):
        # Basic window setup remains the same
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(1500, 1500)
        MainWindow.centralWidget = QWidget(MainWindow)
        MainWindow.setCentralWidget(MainWindow.centralWidget)

        # Main layout
        MainWindow.mainLayout = QHBoxLayout(MainWindow.centralWidget)

        # Options layout - slightly reduced spacing
        MainWindow.optionsLayout = QVBoxLayout()
        MainWindow.optionsLayout.setSpacing(5)  # Reduced from 10
        MainWindow.optionsLayout.setAlignment(Qt.AlignTop)

        # Well Bore Display Options Section
        MainWindow.zoneFrame = QFrame(MainWindow)
        MainWindow.zoneFrame.setFrameStyle(QFrame.Panel | QFrame.Raised)  # 3D raised panel effect
        MainWindow.zoneFrame.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 1px solid #B0B0B0;
                border-top-color: #E0E0E0;
                border-left-color: #E0E0E0;
                border-bottom-color: #808080;
                border-right-color: #808080;
                border-radius: 8px;
                padding: 12px;
            }
        """)

        # Zone layout with tighter spacing
        MainWindow.zoneLayout = QVBoxLayout(MainWindow.zoneFrame)
        MainWindow.zoneLayout.setSpacing(3)  # Reduced from 5

        # Simplified Zone dropdowns
        MainWindow.zoneDropdown = StyledDropdown("Zone")
        MainWindow.zoneDropdown.setStyleSheet("""
            QLabel {
                background-color: transparent;
                border: none;
                padding: 0;
            }
            QComboBox {
                background-color: transparent;
                border: none;
            }
        """)
        MainWindow.zoneDropdown.combo.addItem("Select Zone")
        MainWindow.zoneLayout.addWidget(MainWindow.zoneDropdown)

        MainWindow.zoneAttributeDropdown = StyledDropdown("Zone Attribute")
        MainWindow.zoneAttributeDropdown.setStyleSheet("""
            QLabel {
                background-color: transparent;
                border: none;
                padding: 0;
            }
            QComboBox {
                background-color: transparent;
                border: none;
            }
        """)
        MainWindow.zoneAttributeDropdown.combo.addItem("Select Zone Attribute")
        MainWindow.zoneLayout.addWidget(MainWindow.zoneAttributeDropdown)

        # Zone color bar section - No bubbles around it
        MainWindow.zone_colorbar = StyledColorBar("Zone Color Bar", parent=MainWindow)
        MainWindow.zone_colorbar.setStyleSheet("""
            QLabel {
                background-color: transparent;
                border: none;
                padding: 0;
                margin: 0;
            }
        """)
        MainWindow.zone_colorbar.setContentsMargins(0, 0, 0, 0)
        MainWindow.zoneLayout.addWidget(MainWindow.zone_colorbar)

        MainWindow.optionsLayout.addWidget(MainWindow.zoneFrame)
        MainWindow.optionsLayout.addSpacing(10)  # Reduced from 15

        # Well Display Options Section
        MainWindow.wellZoneFrame = QFrame(MainWindow)
        MainWindow.wellZoneFrame.setFrameStyle(QFrame.Panel | QFrame.Raised)
        MainWindow.wellZoneFrame.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 1px solid #B0B0B0;
                border-top-color: #E0E0E0;
                border-left-color: #E0E0E0;
                border-bottom-color: #808080;
                border-right-color: #808080;
                border-radius: 8px;
                padding: 12px;
            }
        """)

        MainWindow.wellZoneLayout = QVBoxLayout(MainWindow.wellZoneFrame)
        MainWindow.wellZoneLayout.setSpacing(3)

        # Well Zone dropdowns
        MainWindow.wellZoneDropdown = StyledDropdown("Well Zone")
        MainWindow.wellZoneDropdown.setStyleSheet("""
            QLabel {
                background-color: transparent;
                border: none;
                padding: 0;
            }
            QComboBox {
                background-color: transparent;
                border: none;
            }
        """)
        MainWindow.wellZoneDropdown.combo.addItem("Select Well Zone")
        MainWindow.wellZoneLayout.addWidget(MainWindow.wellZoneDropdown)

        MainWindow.wellAttributeDropdown = StyledDropdown("Well Attribute")
        MainWindow.wellAttributeDropdown.setStyleSheet("""
            QLabel {
                background-color: transparent;
                border: none;
                padding: 0;
            }
            QComboBox {
                background-color: transparent;
                border: none;
            }
        """)
        MainWindow.wellAttributeDropdown.combo.addItem("Select Well Attribute")
        MainWindow.wellZoneLayout.addWidget(MainWindow.wellAttributeDropdown)

        # Well color bar section - No bubbles
        MainWindow.well_colorbar = StyledColorBar("Well Color Bar", parent=MainWindow)
        MainWindow.well_colorbar.setStyleSheet("""
            QLabel {
                background-color: transparent;
                border: none;
                padding: 0;
                margin: 0;
            }
        """)
        MainWindow.well_colorbar.setContentsMargins(0, 0, 0, 0)
        MainWindow.wellZoneLayout.addWidget(MainWindow.well_colorbar)

        MainWindow.optionsLayout.addWidget(MainWindow.wellZoneFrame)
        MainWindow.optionsLayout.addSpacing(10)

        # Grid Display Options Section
        MainWindow.gridFrame = QFrame(MainWindow)
        MainWindow.gridFrame.setFrameStyle(QFrame.Panel | QFrame.Raised)
        MainWindow.gridFrame.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 1px solid #B0B0B0;
                border-top-color: #E0E0E0;
                border-left-color: #E0E0E0;
                border-bottom-color: #808080;
                border-right-color: #808080;
                border-radius: 8px;
                padding: 12px;
            }
        """)

        MainWindow.gridLayout = QVBoxLayout(MainWindow.gridFrame)
        MainWindow.gridLayout.setSpacing(3)

        # Grid dropdown
        MainWindow.gridDropdown = StyledDropdown("Grid")
        MainWindow.gridDropdown.setStyleSheet("""
            QLabel {
                background-color: transparent;
                border: none;
                padding: 0;
            }
            QComboBox {
                background-color: transparent;
                border: none;
            }
        """)
        MainWindow.gridDropdown.combo.addItem("Select Grid")
        MainWindow.gridLayout.addWidget(MainWindow.gridDropdown)

        # Grid color bar section - No bubbles
        MainWindow.grid_colorbar = StyledColorBar("Grid Color Bar", parent=MainWindow)
        MainWindow.grid_colorbar.setStyleSheet("""
            QLabel {
                background-color: transparent;
                border: none;
                padding: 0;
                margin: 0;
            }
        """)
        MainWindow.grid_colorbar.setContentsMargins(0, 0, 0, 0)
        MainWindow.gridLayout.addWidget(MainWindow.grid_colorbar)

        MainWindow.optionsLayout.addWidget(MainWindow.gridFrame)
        MainWindow.optionsLayout.addStretch()

        # Add the options layout to the main layout
        MainWindow.mainLayout.addLayout(MainWindow.optionsLayout, 1)

        # Ensure a minimum width for the options column
        MainWindow.optionsLayout.setContentsMargins(5, 5, 5, 5)


        # Scroll area for the drawing area
        MainWindow.scrollArea = QScrollArea(MainWindow.centralWidget)
        MainWindow.scrollArea.setObjectName("scrollArea")
        MainWindow.scrollArea.setWidgetResizable(True)
        MainWindow.drawingArea = DrawingArea(MainWindow)
        MainWindow.drawingArea.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)


        # Set background color to very light grey
        light_grey = QColor(240, 240, 240)  # Define a very light grey color
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

        file_menu = MainWindow.menu_bar.addMenu("Project")

        MainWindow.new_project_action = QAction("Create", MainWindow)
        file_menu.addAction(MainWindow.new_project_action)

        MainWindow.open_action = QAction("Open", MainWindow)
        file_menu.addAction(MainWindow.open_action)

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

        # Properties Menu (Unchanged)
        MainWindow.properties_menu = MainWindow.menu_bar.addMenu("Properties")
        MainWindow.properties_menu.setEnabled(True)

        MainWindow.well_properties_action = QAction("Well Properties", MainWindow)
        MainWindow.properties_menu.addAction(MainWindow.well_properties_action)

        MainWindow.zone_viewer_action = QAction("Zone Properties", MainWindow)
        MainWindow.properties_menu.addAction(MainWindow.zone_viewer_action)

        MainWindow.map_properties_action = QAction("Map Properties", MainWindow)
        MainWindow.properties_menu.addAction(MainWindow.map_properties_action )




        
        
        MainWindow.toolbar = QToolBar("Main Toolbar", MainWindow)
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

        # Add actions to toolbar
        actions = [
            ("plot_tool_action", MainWindow.plot_icon, "QC Zones"),
            ("gun_barrel_action", MainWindow.gun_barrel_icon, "Create Gun Barrel"),
            ("cross_plot_action", MainWindow.cross_plot_icon, "Cross Plot"),
            ("color_editor_action", MainWindow.color_editor_icon, "Edit Grid Colors"),
            ("zoomOut", MainWindow.zoom_out_icon, "Zoom Out"),
            ("zoomIn", MainWindow.zoom_in_icon, "Zoom In"),
            ("launch_action", MainWindow.launch_icon, "Launch Decline Curve Analysis"),
            ("cashflow_action", MainWindow.launch_cashflow_icon, "Launch Combined Cashflow")
        ]

        for action_name, icon, text in actions:
            action = QAction(icon, text, MainWindow)
            setattr(MainWindow, action_name, action)
            MainWindow.toolbar.addAction(action)

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

        self.populate_color_bar_dropdowns()

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