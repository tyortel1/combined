import os
from PySide6.QtWidgets import QWidget, QHBoxLayout,QSpinBox, QFrame, QVBoxLayout,  QComboBox, QCheckBox, QLabel, QSlider, QScrollArea, QSizePolicy, QMenuBar, QMenu, QToolBar, QToolButton
from PySide6.QtCore import Qt, QMetaObject
from PySide6.QtGui import QIcon,  QPalette, QColor, QAction

from DrawingArea import DrawingArea

class Ui_MainWindow:
    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(1500, 1500)
        MainWindow.centralWidget = QWidget(MainWindow)
        MainWindow.setCentralWidget(MainWindow.centralWidget)

        # Main layout
        MainWindow.mainLayout = QHBoxLayout(MainWindow.centralWidget)

        # Options layout
        MainWindow.optionsLayout = QVBoxLayout()
        MainWindow.optionsLayout.setSpacing(5)  # Minimal spacing

        # Dropdown to select grid
        MainWindow.gridLabel = QLabel("Select Grid:", MainWindow)
        MainWindow.optionsLayout.addWidget(MainWindow.gridLabel)
        MainWindow.gridDropdown = QComboBox(MainWindow)
        MainWindow.gridDropdown.addItem("Select Grid")
        MainWindow.optionsLayout.addWidget(MainWindow.gridDropdown)

                # Dropdown to select grid color bar

                # Color range display for grid
        MainWindow.gridColorRangeDisplay = QLabel(MainWindow)
        MainWindow.gridColorRangeDisplay.setFixedHeight(50)
        MainWindow.gridColorRangeDisplay.setFixedWidth(220)
        MainWindow.gridColorRangeDisplay.setStyleSheet("background-color: white; border: 1px solid black;")
        MainWindow.optionsLayout.addWidget(MainWindow.gridColorRangeDisplay)

        # Dropdown to select grid color bar
        MainWindow.gridColorBarLabel = QLabel("Select Grid Color Bar:", MainWindow)
        MainWindow.optionsLayout.addWidget(MainWindow.gridColorBarLabel)
        MainWindow.gridColorBarDropdown = QComboBox(MainWindow)
        MainWindow.gridColorBarDropdown.addItem("Rainbow") 
        MainWindow.optionsLayout.addWidget(MainWindow.gridColorBarDropdown)

        MainWindow.optionsLayout.addSpacing(25)
                # Separator line below grid color range display
        MainWindow.gridSeparator = QFrame(MainWindow)
        MainWindow.gridSeparator.setFrameShape(QFrame.HLine)
        MainWindow.gridSeparator.setFrameShadow(QFrame.Sunken)
        MainWindow.optionsLayout.addWidget(MainWindow.gridSeparator)

        MainWindow.optionsLayout.addSpacing(5)


        # Dropdown to select zone
        MainWindow.zoneLabel = QLabel("Select Zone:", MainWindow)
        MainWindow.optionsLayout.addWidget(MainWindow.zoneLabel)
        MainWindow.zoneDropdown = QComboBox(MainWindow)
        MainWindow.zoneDropdown.addItem("Select Zone")
        MainWindow.optionsLayout.addWidget(MainWindow.zoneDropdown)

        # Dropdown to select zone attribute
        MainWindow.zoneAttributeLabel = QLabel("Select Zone Attribute:", MainWindow)
        MainWindow.optionsLayout.addWidget(MainWindow.zoneAttributeLabel)
        MainWindow.zoneAttributeDropdown = QComboBox(MainWindow)
        MainWindow.zoneAttributeDropdown.addItem("Select Zone Attribute")
        MainWindow.optionsLayout.addWidget(MainWindow.zoneAttributeDropdown)



                # Color range display for zone attribute
        MainWindow.zoneAttributeColorRangeDisplay = QLabel(MainWindow)
        MainWindow.zoneAttributeColorRangeDisplay.setFixedHeight(50)
        MainWindow.zoneAttributeColorRangeDisplay.setFixedWidth(220)
        MainWindow.zoneAttributeColorRangeDisplay.setStyleSheet("background-color: white; border: 1px solid black;")
        MainWindow.optionsLayout.addWidget(MainWindow.zoneAttributeColorRangeDisplay)

                # Dropdown to select zone color bar
        MainWindow.zoneAttributeColorBarLable = QLabel("Select Zone Color Bar:", MainWindow)
        MainWindow.optionsLayout.addWidget(MainWindow.zoneAttributeColorBarLable)
        MainWindow.zoneAttributeColorBarDropdown = QComboBox(MainWindow)
        MainWindow.zoneAttributeColorBarDropdown.addItem("Rainbow")
        MainWindow.optionsLayout.addWidget(MainWindow.zoneAttributeColorBarDropdown)


        MainWindow.optionsLayout.addSpacing(25)

                # Separator line below grid color range display
        MainWindow.gridSeparator = QFrame(MainWindow)
        MainWindow.gridSeparator.setFrameShape(QFrame.HLine)
        MainWindow.gridSeparator.setFrameShadow(QFrame.Sunken)
        MainWindow.optionsLayout.addWidget(MainWindow.gridSeparator)

        MainWindow.optionsLayout.addSpacing(5)



        # Dropdown to select Well Zone
        MainWindow.WellZoneLabel = QLabel("Select Well Zone:", MainWindow)
        MainWindow.optionsLayout.addWidget(MainWindow.WellZoneLabel)
        MainWindow.WellZoneDropdown = QComboBox(MainWindow)
        MainWindow.WellZoneDropdown.addItem("Select Well Zone")
        MainWindow.optionsLayout.addWidget(MainWindow.WellZoneDropdown)

        # Dropdown to select Well Attribute
        MainWindow.WellAttributeLabel = QLabel("Select Well Attribute:", MainWindow)
        MainWindow.optionsLayout.addWidget(MainWindow.WellAttributeLabel)
        MainWindow.WellAttributeDropdown = QComboBox(MainWindow)
        MainWindow.WellAttributeDropdown.addItem("Select Well Attribute")
        MainWindow.optionsLayout.addWidget(MainWindow.WellAttributeDropdown)

        # Color range display for Well attribute
        MainWindow.WellAttributeColorRangeDisplay = QLabel(MainWindow)
        MainWindow.WellAttributeColorRangeDisplay.setFixedHeight(50)
        MainWindow.WellAttributeColorRangeDisplay.setFixedWidth(220)
        MainWindow.WellAttributeColorRangeDisplay.setStyleSheet("background-color: white; border: 1px solid black;")
        MainWindow.optionsLayout.addWidget(MainWindow.WellAttributeColorRangeDisplay)

        # Dropdown to select Well Color Bar
        MainWindow.WellAttributeColorBarLabel = QLabel("Select Well Color Bar:", MainWindow)
        MainWindow.optionsLayout.addWidget(MainWindow.WellAttributeColorBarLabel)
        MainWindow.WellAttributeColorBarDropdown = QComboBox(MainWindow)
        MainWindow.WellAttributeColorBarDropdown.addItem("Rainbow")
        MainWindow.optionsLayout.addWidget(MainWindow.WellAttributeColorBarDropdown)


        MainWindow.optionsLayout.addSpacing(25)

                # Separator line below grid color range display
        MainWindow.gridSeparator = QFrame(MainWindow)
        MainWindow.gridSeparator.setFrameShape(QFrame.HLine)
        MainWindow.gridSeparator.setFrameShadow(QFrame.Sunken)
        MainWindow.optionsLayout.addWidget(MainWindow.gridSeparator)

        MainWindow.optionsLayout.addSpacing(5)


        # Checkbox to show/hide UWI labels
        MainWindow.UWICheckbox = QCheckBox("Show UWI Labels", MainWindow)
        MainWindow.UWICheckbox.setChecked(True)
        MainWindow.optionsLayout.addWidget(MainWindow.UWICheckbox)

                # Checkbox to show/hide UWI labels
        MainWindow.ticksCheckbox = QCheckBox("Show Ticks", MainWindow)
        MainWindow.ticksCheckbox.setChecked(True)
        MainWindow.optionsLayout.addWidget(MainWindow.ticksCheckbox)

        MainWindow.gradientCheckbox = QCheckBox("Show Drainage", MainWindow)
        MainWindow.gradientCheckbox.setChecked(True)

        # Spin box for gradient size
        MainWindow.gradientSizeSpinBox = QSpinBox(MainWindow)
        MainWindow.gradientSizeSpinBox.setMinimum(1)    # Minimum size
        MainWindow.gradientSizeSpinBox.setMaximum(1000) # Maximum size
        MainWindow.gradientSizeSpinBox.setValue(400)    # Default value
        MainWindow.gradientSizeSpinBox.setSingleStep(10) # Step size for increment/decrement
        MainWindow.gradientSizeSpinBox.setToolTip("Set the size of the drainage gradient")
        


        # Horizontal layout to put checkbox and spinbox together
        gradientLayout = QHBoxLayout()
        gradientLayout.addWidget(MainWindow.gradientCheckbox)
        gradientLayout.addWidget(QLabel("Size:"))
        gradientLayout.addWidget(MainWindow.gradientSizeSpinBox)
        gradientLayout.addStretch()  # Add stretching to prevent cramping

        # Add the horizontal layout to the options layout
        MainWindow.optionsLayout.addLayout(gradientLayout)


        MainWindow.UWIWidthLabel = QLabel("UWI Size:", MainWindow)
        MainWindow.optionsLayout.addWidget(MainWindow.UWIWidthLabel)

        # Slider to change the width of the lines
        MainWindow.UWIWidthSlider = QSlider(Qt.Horizontal, MainWindow)
        MainWindow.UWIWidthSlider.setMinimum(1)
        MainWindow.UWIWidthSlider.setMaximum(100)
        MainWindow.UWIWidthSlider.setValue(25)
        MainWindow.optionsLayout.addWidget(MainWindow.UWIWidthSlider)

        # Label for the opacity slider
        MainWindow.opacityLabel = QLabel("UWI Label Opacity:", MainWindow)
        MainWindow.optionsLayout.addWidget(MainWindow.opacityLabel)

        # Slider to change the opacity of UWI labels
        MainWindow.opacitySlider = QSlider(Qt.Horizontal, MainWindow)
        MainWindow.opacitySlider.setMinimum(0)
        MainWindow.opacitySlider.setMaximum(100)
        MainWindow.opacitySlider.setValue(50)
        MainWindow.optionsLayout.addWidget(MainWindow.opacitySlider)

        # Label for the line width slider
        MainWindow.lineWidthSliderLabel = QLabel("Line Width:", MainWindow)
        MainWindow.optionsLayout.addWidget(MainWindow.lineWidthSliderLabel)

        # Slider to change the width of the lines
        MainWindow.lineWidthSlider = QSlider(Qt.Horizontal, MainWindow)
        MainWindow.lineWidthSlider.setMinimum(1)
        MainWindow.lineWidthSlider.setMaximum(200)
        MainWindow.lineWidthSlider.setValue(25)
        MainWindow.optionsLayout.addWidget(MainWindow.lineWidthSlider)

        MainWindow.lineLabel = QLabel("Line Opacity", MainWindow)
        MainWindow.optionsLayout.addWidget(MainWindow.lineLabel)

        # Slider to change the line opacity
        MainWindow.lineOpacitySlider = QSlider(Qt.Horizontal, MainWindow)
        MainWindow.lineOpacitySlider.setMinimum(0)
        MainWindow.lineOpacitySlider.setMaximum(100)
        MainWindow.lineOpacitySlider.setValue(50)
        MainWindow.optionsLayout.addWidget(MainWindow.lineOpacitySlider)

        # Adding a spacer to push everything to the top
        MainWindow.optionsLayout.addStretch()

        MainWindow.mainLayout.addLayout(MainWindow.optionsLayout, 1)  # Occupy 1/8th of the window

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

        # Launch menu
        MainWindow.launch_menu = MainWindow.menu_bar.addMenu("Launch")
        MainWindow.launch_menu.setEnabled(False)
        MainWindow.plot_action = QAction("Zone Viewer", MainWindow)
        MainWindow.launch_menu.addAction(MainWindow.plot_action)
        MainWindow.color_action = QAction("Color Editor", MainWindow)
        MainWindow.launch_menu.addAction(MainWindow.color_action)
        MainWindow.pud_properties_action = QAction("Pad Production Scenario Builder", MainWindow)
        MainWindow.launch_menu.addAction(MainWindow.pud_properties_action)
        MainWindow.dca_action = QAction("Decline Curve Analysis", MainWindow)
        MainWindow.launch_menu.addAction(MainWindow.dca_action)  # Add this line

  
        MainWindow.launch_cashflow_action = QAction("Launch Combined Cashflow", MainWindow)
        MainWindow.launch_menu.addAction(MainWindow.launch_cashflow_action)

        MainWindow.calculate_menu = MainWindow.menu_bar.addMenu("Calculate")
        MainWindow.calculate_menu.setEnabled(False)
        MainWindow.calc_stage_action = QAction("Calculate Stages", MainWindow)
        MainWindow.calculate_menu.addAction(MainWindow.calc_stage_action)
        MainWindow.calc_grid_to_zone_action = QAction("Grid To Zone", MainWindow)
        MainWindow.calculate_menu.addAction(MainWindow.calc_grid_to_zone_action)
        #MainWindow.calc_well_attribute_action = QAction("Calculate Well Attributes", MainWindow)
        #MainWindow.calculate_menu.addAction(MainWindow.calc_well_attribute_action)
        MainWindow.calc_inzone_action = QAction("Calculate in Zone", MainWindow)
        MainWindow.calculate_menu.addAction(MainWindow.calc_inzone_action)
        MainWindow.pc_dialog_action = QAction("Calculate Parent Child", MainWindow)
        MainWindow.calculate_menu.addAction(MainWindow.pc_dialog_action)
        MainWindow.attribute_analyzer_action = QAction("Attribute Analyzer", MainWindow)
        MainWindow.calculate_menu.addAction(MainWindow.attribute_analyzer_action)
        MainWindow.correlation_matrix_action = QAction("Well Correlation Matrix", MainWindow)
        MainWindow.calculate_menu.addAction(MainWindow.correlation_matrix_action)
        MainWindow.well_comparison_action = QAction("Well Comparison Calculation", MainWindow)
        MainWindow.calculate_menu.addAction(MainWindow.well_comparison_action)
        MainWindow.merge_zones_action = QAction("Merge Zones", MainWindow)
        MainWindow.calculate_menu.addAction(MainWindow.merge_zones_action)
        MainWindow.calc_zone_attb_action = QAction("Calculate Zone Attributes", MainWindow)
        MainWindow.calculate_menu.addAction(MainWindow.calc_zone_attb_action)






        MainWindow.import_menu = MainWindow.menu_bar.addMenu("Import")
        MainWindow.import_menu.setEnabled(False)
        MainWindow.connect_action = QAction("SeisWare Wells and Production", MainWindow)
        MainWindow.connect_action.triggered.connect(MainWindow.connectToSeisWare)
        MainWindow.import_menu.addAction(MainWindow.connect_action)
        MainWindow.data_loader_menu_action = QAction("SeisWare Grids ", MainWindow)
        MainWindow.import_menu.addAction(MainWindow.data_loader_menu_action)
        MainWindow.import_action = QAction("CSV Production", MainWindow)
        MainWindow.import_action.triggered.connect(MainWindow.import_excel)
        MainWindow.import_menu.addAction(MainWindow.import_action)
        MainWindow.dataload_well_zones_action = QAction("CSV Well Zones and Attributes", MainWindow)
        MainWindow.import_menu.addAction(MainWindow.dataload_well_zones_action)
        MainWindow.dataload_segy_action = QAction("Import Segy", MainWindow)
        MainWindow.import_menu.addAction(MainWindow.dataload_segy_action)
        # Add new actions




        MainWindow.export_menu = MainWindow.menu_bar.addMenu("Export")
        MainWindow.export_menu.setEnabled(False)

        MainWindow.export_action = QAction("Export Results", MainWindow)
        MainWindow.export_menu.addAction(MainWindow.export_action)
        MainWindow.export_properties = QAction("Export SWMap Properties", MainWindow)
        MainWindow.export_menu.addAction(MainWindow.export_properties)
        MainWindow.zone_to_sw = QAction("Send Zones to SeisWare", MainWindow)
        MainWindow.export_menu.addAction(MainWindow.zone_to_sw)

        MainWindow.properties_menu = MainWindow.menu_bar.addMenu("Properties")
        MainWindow.properties_menu.setEnabled(True)

        MainWindow.well_properties_action = QAction("Well Properties", MainWindow)
        MainWindow.properties_menu.addAction(MainWindow.well_properties_action)

        MainWindow.zone_viewer_action = QAction("Zone Properties", MainWindow)
        MainWindow.properties_menu.addAction(MainWindow.zone_viewer_action)



        
        
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

        self.zoneAttributeColorBarDropdown.addItems(color_bar_files)
        self.gridColorBarDropdown.addItems(color_bar_files)
        self.WellAttributeColorBarDropdown.addItems(color_bar_files)