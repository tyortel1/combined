
from PyQt5.QtWidgets import QApplication, QMainWindow, QHeaderView, QMenuBar, QAction, QSizePolicy, QVBoxLayout, QHBoxLayout, QGridLayout, QWidget, QTableWidget, QTableWidgetItem, QComboBox, QLineEdit, QLabel, QDateTimeEdit, QSpinBox, QToolBar, QWidget,QTabWidget, QInputDialog
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEngineSettings
from PyQt5.QtWidgets import QWidget, QStyle
from PyQt5.QtCore import QDateTime, QDate, QSize, Qt
from PyQt5.QtGui import QIcon, QDoubleValidator
import sys
import os
from PyQt5 import QtWidgets
from datetime import datetime, timedelta
from PyQt5.QtWidgets import QTableWidgetItem
import sqlite3

class UI_main(object):

    def __init__(self):
        self.recent_projects_file = os.path.join(os.path.expanduser('~'), 'recent_projects.txt')

    def setupUI(self, MainWindow):
        MainWindow.setWindowTitle("Qt Dialog with Plotly Graph")
        MainWindow.setGeometry(100, 100, 1400, 1000)  # Adjust size as needed

        script_dir = os.path.dirname(os.path.realpath(__file__))

        # Setup the menu bar
        menu_bar = QMenuBar(MainWindow)
        file_menu = menu_bar.addMenu("&File")
        import_menu = menu_bar.addMenu("&Import")
        self.connect_action = QAction("&Connect to SeisWare", MainWindow)
        self.connect_action.triggered.connect(MainWindow.connectToSeisWare)
        import_menu.addAction(self.connect_action)
        self.import_action = QAction("&Import Excel", MainWindow)
        self.import_action.triggered.connect(MainWindow.import_excel)
        import_menu.addAction(self.import_action)
        self.import_action.setEnabled(False)
        self.connect_action.setEnabled(False)
 
        data_properties_menu = menu_bar.addMenu("&Data Properties")

        help_menu = menu_bar.addMenu("&Help")
        help_action = QAction("&About Plotly Graph", MainWindow)
        help_action.triggered.connect(MainWindow.show_help)
        help_menu.addAction(help_action)


        
        project_create_action = QAction("&Create Project", MainWindow)
        project_create_action.triggered.connect(MainWindow.create_project)

        open_action = QAction("&Open Project", MainWindow)
        open_action.triggered.connect(MainWindow.open_project)





        # Add actions to File menu

        file_menu.addAction(project_create_action)
        file_menu.addAction(open_action)

        MainWindow.setMenuBar(menu_bar)


        central_widget = QWidget(MainWindow)
        MainWindow.setCentralWidget(central_widget)

        # Main layout for organizing the widgets
        main_layout = QGridLayout(central_widget)

                # Create tab widget
        tab_widget = QTabWidget()
        main_layout.addWidget(tab_widget)
        

        # Create tabs
        tab1 = QWidget()

        tab2 = QWidget()

        tab_widget.addTab(tab1, "Tab 1")
        tab_widget.addTab(tab2, "Tab 2")
       
        tab1_layout = QGridLayout(tab1)
        tab2_layout = QGridLayout(tab2)


        # Option buttons layout
        options_layout = QVBoxLayout()
        tab1_layout.addLayout(options_layout, 2, 0, 8, 2)  # row: 1-8, column: 0-1

        
        # Add a label for graph options
        options_label = QLabel("Graph Options")
        options_label.setStyleSheet("font-weight: bold; text-decoration: underline; font-size: 14px;")
        options_layout.addWidget(options_label)


        option1_label = QLabel("Graph Type:")
        options_layout.addWidget(option1_label)
        # Option 1 dropdown
        self.option1_dropdown = QComboBox()
        self.option1_dropdown.addItem("Decline Curve")
        self.option1_dropdown.addItem("Cash Flow")

        self.option1_dropdown.currentTextChanged.connect(MainWindow.set_graph_type)  # Connect signal to method
        options_layout.addWidget(self.option1_dropdown)



        # Add labels for Gas Parameters
        gas_parameters_label = QLabel("Gas Parameters")
        gas_parameters_label.setStyleSheet("font-weight: bold; text-decoration: underline;font-size: 14px;")  # Bold and underline the label
        options_layout.addWidget(gas_parameters_label)


                # QHBoxLayout for Gas Start Date
        gas_time_layout = QHBoxLayout()
        gas_time_label = QLabel("Start Date:")
        gas_time_layout.addWidget(gas_time_label)
        gas_time_layout.addStretch(1)
        self.gas_time_input = QDateTimeEdit()
        self.gas_time_input.setCalendarPopup(True)
        self.gas_time_input.setDisplayFormat("yyyy-MM-dd")              
        gas_time_layout.addWidget(self.gas_time_input)
        options_layout.addLayout(gas_time_layout)

        # Initial production rate input for Gas
        # Initial gas production rate input
        ir_gas_layout = QHBoxLayout()
        ir_gas_label = QLabel("IR:")
        ir_gas_layout.addWidget(ir_gas_label)
        ir_gas_layout.addStretch(1)
        self.initial_gas_production_rate_input = QLineEdit()
        self.initial_gas_production_rate_input.setValidator(QDoubleValidator())
        ir_gas_layout.addWidget(self.initial_gas_production_rate_input)
        options_layout.addLayout(ir_gas_layout)

        # Add a label for the initial decline rate input for Gas


        
        # QHBoxLayout for DI (Initial Decline Rate) for Gas
        di_gas_layout = QHBoxLayout()
        di_gas_label = QLabel("DI:")
        di_gas_layout.addWidget(di_gas_label)
        di_gas_layout.addStretch(1)
        self.initial_gas_decline_rate_input = QLineEdit()
        validator = QDoubleValidator(0.0, 100.0, 2)
        validator.setDecimals(2) 
        self.initial_gas_decline_rate_input.setValidator(validator)
        di_gas_layout.addWidget(self.initial_gas_decline_rate_input)
        options_layout.addLayout(di_gas_layout)



        # QHBoxLayout for Gas B Factor
        b_factor_gas_layout = QHBoxLayout()
        b_factor_gas_label = QLabel("B Factor:")
        b_factor_gas_layout.addWidget(b_factor_gas_label)
        b_factor_gas_layout.addStretch(1)
        self.gas_b_factor_input = QLineEdit()
        validator = QDoubleValidator()
        self.gas_b_factor_input.setValidator(validator)
        b_factor_gas_layout.addWidget(self.gas_b_factor_input)
        options_layout.addLayout(b_factor_gas_layout)


                # QHBoxLayout for OIL Min Decline
        min_dec_gas_layout = QHBoxLayout()
        min_dec_gas_label = QLabel("Min Decline:")
        min_dec_gas_layout.addWidget(min_dec_gas_label)
        min_dec_gas_layout.addStretch(1)
        self.min_dec_gas = QLineEdit()
        validator = QDoubleValidator()
        validator.setRange(0.0, 100.0, 2)
        self.min_dec_gas.setValidator(validator)
        min_dec_gas_layout.addWidget(self.min_dec_gas)
        options_layout.addLayout(min_dec_gas_layout)

        # QHBoxLayout for Sum of Errors
        error_gas_layout = QHBoxLayout()
        error_gas_label = QLabel("Sum of Errors:")
        error_gas_layout.addWidget(error_gas_label)
        error_gas_layout.addStretch(1)
        self.error_gas = QLineEdit()
        validator = QDoubleValidator()
        validator.setRange(0.0, 100.0, 2)
        self.error_gas.setValidator(validator)
        error_gas_layout.addWidget(self.error_gas)
        options_layout.addLayout(error_gas_layout)



        # Add spacer to push options to the top
        options_layout.addSpacing(25)





        # Add labels for Oil Parameters
        oil_parameters_label = QLabel("Oil Parameters")
        oil_parameters_label.setStyleSheet("font-weight: bold; text-decoration: underline;font-size: 14px;")  # Bold and underline the label
        options_layout.addWidget(oil_parameters_label)

                # QHBoxLayout for Oil Start Date
        oil_time_layout = QHBoxLayout()
        oil_time_label = QLabel("Start Date:")
        oil_time_layout.addWidget(oil_time_label)
        oil_time_layout.addStretch(1)
        self.oil_time_input = QDateTimeEdit()
        self.oil_time_input.setCalendarPopup(True)
        self.oil_time_input.setDisplayFormat("yyyy-MM-dd")
        oil_time_layout.addWidget(self.oil_time_input)
        options_layout.addLayout(oil_time_layout)
     

        # QHBoxLayout for IR (Initial Production Rate)
        ir_oil_layout = QHBoxLayout()
        ir_oil_label = QLabel("IR:")
        ir_oil_layout.addWidget(ir_oil_label)
        ir_oil_layout.addStretch(1)
        self.initial_oil_production_rate_input = QLineEdit()
        self.initial_oil_production_rate_input.setValidator(QDoubleValidator())
        ir_oil_layout.addWidget(self.initial_oil_production_rate_input)
        options_layout.addLayout(ir_oil_layout)

        # Initial decline rate input for Oil.
        # QHBoxLayout for DI (Initial Decline Rate)
        di_oil_layout = QHBoxLayout()
        di_oil_label = QLabel("DI:")
        di_oil_layout.addWidget(di_oil_label)
        di_oil_layout.addStretch(1)
        self.initial_oil_decline_rate_input = QLineEdit()
        validator = QDoubleValidator(0.0, 100.0, 2)
        self.initial_oil_decline_rate_input.setValidator(validator)
        di_oil_layout.addWidget(self.initial_oil_decline_rate_input)
        options_layout.addLayout(di_oil_layout)





         # Create a QHBoxLayout for the B factor elements
        b_factor_layout = QHBoxLayout()
        oil_b_factor_label = QLabel("B Factor:")
        b_factor_layout.addWidget(oil_b_factor_label)
        b_factor_layout.addStretch(1)
        self.oil_b_factor_input = QLineEdit()
        validator = QDoubleValidator()
        self.oil_b_factor_input.setValidator(validator)
        b_factor_layout.addWidget(self.oil_b_factor_input)
        options_layout.addLayout(b_factor_layout)


        # QHBoxLayout for OIL Min Decline
        min_dec_oil_layout = QHBoxLayout()
        min_dec_oil_label = QLabel("Min Decline:")
        min_dec_oil_layout.addWidget(min_dec_oil_label)
        min_dec_oil_layout.addStretch(1)
        self.min_dec_oil = QLineEdit()
        validator = QDoubleValidator()
        validator.setRange(0.0, 100.0, 2)
        self.min_dec_oil.setValidator(validator)
        min_dec_oil_layout.addWidget(self.min_dec_oil)
        options_layout.addLayout(min_dec_oil_layout)

        # QHBoxLayout for Sum of Errors
        error_oil_layout = QHBoxLayout()
        error_oil_label = QLabel("Sum of Errors:")
        error_oil_layout.addWidget(error_oil_label)
        error_oil_layout.addStretch(1)
        self.error_oil = QLineEdit()
        validator = QDoubleValidator()
        validator.setRange(0.0, 100.0, 2)
        self.error_oil.setValidator(validator)
        error_oil_layout.addWidget(self.error_oil)
        options_layout.addLayout(error_oil_layout)

        options_layout.addSpacing(25)
#---------------------------------------------------------------------------------------------------
                # CASH FLOW PARAMETERS
#----------------------------------------------------------------
        cash_flow_label = QLabel("Cash Flow Parameters")
        cash_flow_label.setStyleSheet("font-weight: bold; text-decoration: underline;font-size: 14px;")  # Bold and underline the label
        options_layout.addWidget(cash_flow_label)


        end_forcast_layout = QHBoxLayout()
        end_forcast_label = QLabel("Forcast Limit")
        end_forcast_layout.addWidget(end_forcast_label)
        end_forcast_layout.addStretch(1)
        self.end_forcast_type = QComboBox()
        self.end_forcast_type.addItem("Net Dollars")
        self.end_forcast_type.addItem("End Date")
        self.end_forcast_type.addItem("GOR")
          # Connect signal to method
        end_forcast_layout.addWidget(self.end_forcast_type)
        options_layout.addLayout(end_forcast_layout)
        self.end_forcast_type.currentIndexChanged.connect(self.on_forcast_option_changed)

        #QHBoxLayout for Date input
        ecl_date_layout = QHBoxLayout()
        ecl_date_label = QLabel("Economic Limit Date:")
        ecl_date_layout.addWidget(ecl_date_label)
        ecl_date_layout.addStretch(1)
        self.ecl_date = QDateTimeEdit()
        self.ecl_date.setCalendarPopup(True)
        self.ecl_date.setDisplayFormat("yyyy-MM-dd")
        current_date = QDate.currentDate()
        ten_years = current_date.addYears(10)
        self.ecl_date.setDate(ten_years) 
        self.ecl_date.setEnabled(False) 
        ecl_date_layout.addWidget(self.ecl_date)# Set default date
        options_layout.addLayout(ecl_date_layout)

        #  # QHBoxLayout for Oil Start Date
        #cf_start_date_layout = QHBoxLayout()
        
        #cf_start_date_label = QLabel("Start Date:")
        #cf_start_date_layout.addWidget(cf_start_date_label)
        #cf_start_date_layout.addStretch(1)
        #self.cf_start_date = QDateTimeEdit()
        #self.cf_start_date.setCalendarPopup(True)
        #self.cf_start_date.setDisplayFormat("yyyy-MM-dd")
        #self.cf_start_date.setDateTime(QDateTime.currentDateTime())
        #cf_start_date_layout.addWidget(self.cf_start_date)
        #options_layout.addLayout(cf_start_date_layout)

        # QHBoxLayout for IR (Initial Production Rate)
        oil_price_layout = QHBoxLayout()
        
        oil_price_label = QLabel("Oil $")
        oil_price_layout.addWidget(oil_price_label)
        oil_price_layout.addStretch(1)
        self.oil_price = QLineEdit()
        self.oil_price.setValidator(QDoubleValidator())
        oil_price_layout.addWidget(self.oil_price)
        options_layout.addLayout(oil_price_layout)

        # Initial decline rate input for Oil.
        # QHBoxLayout for DI (Initial Decline Rate)
        gas_price_layout = QHBoxLayout()
        
        gas_price_label = QLabel("Gas $:")
        gas_price_layout.addWidget(gas_price_label)
        gas_price_layout.addStretch(1)
        self.gas_price = QLineEdit()
        validator = QDoubleValidator(0.0, 100.0, 2)
        self.gas_price.setValidator(validator)
        gas_price_layout.addWidget(self.gas_price)
        options_layout.addLayout(gas_price_layout)
                # QHBoxLayout for IR (Initial Production Rate)
        oil_price_dif_layout = QHBoxLayout()
        
        oil_price_dif_label = QLabel("OilDif BBL $:")
        oil_price_dif_layout.addWidget(oil_price_dif_label)
        oil_price_dif_layout.addStretch(1)
        self.oil_price_dif = QLineEdit()
        self.oil_price_dif.setValidator(QDoubleValidator())
        oil_price_dif_layout.addWidget(self.oil_price_dif)
        options_layout.addLayout(oil_price_dif_layout)

        # Initial decline rate input for Oil.
        # QHBoxLayout for DI (Initial Decline Rate)
        gas_price_dif_layout = QHBoxLayout()
        
        gas_price_dif_label = QLabel("GasDif MCF $:")
        gas_price_dif_layout.addWidget(gas_price_dif_label)
        gas_price_dif_layout.addStretch(1.5)
        self.gas_price_dif = QLineEdit()
        validator = QDoubleValidator(0.0, 100.0, 2)
        self.gas_price_dif.setValidator(validator)
        gas_price_dif_layout.addWidget(self.gas_price_dif)
        options_layout.addLayout(gas_price_dif_layout)

   
        
        # # Discount rate
        #discount_rate_layout = QHBoxLayout()
        
        #discount_rate_label = QLabel("Disc Rate %:")
        #discount_rate_layout.addWidget(discount_rate_label)
        #discount_rate_layout.addStretch(1)
        #self.discount_rate_input = QLineEdit()
        #validator = QDoubleValidator()
        #self.discount_rate_input.setValidator(validator)
        #discount_rate_layout.addWidget(self.discount_rate_input)
        #options_layout.addLayout(discount_rate_layout)


        ## Workign interest percent
        working_interest_layout = QHBoxLayout()
        working_interest_label = QLabel("Working Interest %:")
        working_interest_layout.addWidget(working_interest_label)
        working_interest_layout.addStretch(1)
        self.working_interest = QLineEdit()
        validator = QDoubleValidator()
        validator.setRange(0.0, 100.0, 2)
        self.working_interest.setValidator(validator)
        working_interest_layout.addWidget(self.working_interest)
        options_layout.addLayout(working_interest_layout)

                ##Royalty
        royalty_layout = QHBoxLayout()
        royalty_label = QLabel("Royalty %:")
        royalty_layout.addWidget(royalty_label)
        royalty_layout.addStretch(1)
        self.royalty = QLineEdit()
        validator = QDoubleValidator()
        validator.setRange(0.0, 100.0, 2)
        self.royalty.setValidator(validator)
        royalty_layout.addWidget(self.royalty)
        options_layout.addLayout(royalty_layout)

                ## net Revenue
        discount_rate_layout = QHBoxLayout()
        discount_rate_label = QLabel("Revenue Discount %")
        discount_rate_layout.addWidget(discount_rate_label)
        discount_rate_layout.addStretch(1)
        self.discount_rate = QLineEdit()
        validator = QDoubleValidator()
        validator.setRange(0.0, 100.0, 2)
        self.discount_rate.setValidator(validator)
        discount_rate_layout.addWidget(self.discount_rate)
        options_layout.addLayout(discount_rate_layout)


        #Tax Rate
        tax_rate_layout = QHBoxLayout()
        tax_rate_label = QLabel("Tax Rate %:")
        tax_rate_layout.addWidget(tax_rate_label)
        tax_rate_layout.addStretch(1)
        self.tax_rate = QLineEdit()
        validator = QDoubleValidator()
        validator.setRange(0.0, 100.0, 2)
        self.tax_rate.setValidator(validator)
        tax_rate_layout.addWidget(self.tax_rate)
        options_layout.addLayout(tax_rate_layout)

                #net Price oil
        net_price_oil_layout = QHBoxLayout()
        net_price_oil_label = QLabel("Net Price Oil:")
        net_price_oil_layout.addWidget(net_price_oil_label)
        net_price_oil_layout.addStretch(2)
        self.net_price_oil = QLineEdit()
        validator = QDoubleValidator()
        validator.setRange(0.0, 100.0, 2)
        self.net_price_oil.setValidator(validator)
        net_price_oil_layout.addWidget(self.net_price_oil)
        options_layout.addLayout(net_price_oil_layout)


        #net price gas
        net_price_gas_layout = QHBoxLayout()
        net_price_gas_label = QLabel("Net Price gas:")
        net_price_gas_layout.addWidget(net_price_gas_label)
        net_price_gas_layout.addStretch(2)
        self.net_price_gas = QLineEdit()
        validator = QDoubleValidator()
        validator.setRange(0.0, 100.0, 2)
        self.net_price_gas.setValidator(validator)
        net_price_gas_layout.addWidget(self.net_price_gas)
        options_layout.addLayout(net_price_gas_layout)

                #Cap Exp
        capital_expenditures_layout = QHBoxLayout()
        capital_expenditures_label = QLabel("Total Capex:")
        capital_expenditures_layout.addWidget(capital_expenditures_label)
        capital_expenditures_layout.addStretch(2)
        self.capital_expenditures = QLineEdit()
        validator = QDoubleValidator()
        validator.setRange(0.0, 100.0, 2)
        self.capital_expenditures.setValidator(validator)
        capital_expenditures_layout.addWidget(self.capital_expenditures)
        options_layout.addLayout(capital_expenditures_layout)


        #Operating expenditures
        operating_expenditures_layout = QHBoxLayout()
        operating_expenditures_label = QLabel("opex / month:")
        operating_expenditures_layout.addWidget(operating_expenditures_label)
        operating_expenditures_layout.addStretch(2)
        self.operating_expenditures = QLineEdit()
        validator = QDoubleValidator()
        validator.setRange(0.0, 100.0, 2)
        self.operating_expenditures.setValidator(validator)
        operating_expenditures_layout.addWidget(self.operating_expenditures)
        options_layout.addLayout(operating_expenditures_layout)




        self.calculate_net_price()
        self.royalty.editingFinished.connect(self.calculate_net_price)
        self.working_interest.editingFinished.connect(self.calculate_net_price)
        self.oil_price.editingFinished.connect(self.calculate_net_price)
        self.gas_price.editingFinished.connect(self.calculate_net_price)
        self.oil_price_dif.editingFinished.connect(self.calculate_net_price)
        self.gas_price_dif.editingFinished.connect(self.calculate_net_price)
        self.tax_rate.editingFinished.connect(self.calculate_net_price)

        options_layout.addStretch()


        graph_toolbar = QToolBar("Graph graph Toolbar")
        graph_toolbar.setIconSize(QSize(32, 32))  # Set the icon size

 


                # Add actions to the graph options toolbar
        icon_path_regenerate = os.path.join(script_dir, "Icons", "noun-refresh-4213634.png")
        self.regenerate_curves  = QAction(QIcon(icon_path_regenerate), "Regenerate Curves", MainWindow)
        self.regenerate_curves.triggered.connect(MainWindow.update_decline_curve)

        icon_path_iterate = os.path.join(script_dir, "Icons", "noun-iteration-754477.png")
        self.iterate_di = QAction(QIcon(icon_path_iterate), "Iterate Di", MainWindow)
        self.iterate_di.triggered.connect(MainWindow.iterate_di)
        # Add actions to the graph options toolbar
        
        icon_path_exponential = os.path.join(script_dir, "Icons", "noun-exponential-function-5648634")
        self.graph_type  = QAction(QIcon(icon_path_exponential ), "Exponential", MainWindow)
        self.graph_type.triggered.connect(MainWindow.set_distribution_type)

        icon_path_back = os.path.join(script_dir, "Icons", "noun-arrow-back-5340896")
        self.back_button = QAction(QIcon(icon_path_back), "Graph graph Action 1", MainWindow)
        self.back_button.triggered.connect(MainWindow.navigate_back)


        icon_path_forward = os.path.join(script_dir, "Icons", "noun-forward-arrow-6696156")
        self.forward_button = QAction(QIcon(icon_path_forward), "Next Well", MainWindow)
        self.forward_button.triggered.connect(MainWindow.navigate_forward)

        
        icon_gas_model = os.path.join(script_dir, "Icons", "gas_on")
        self.gas_model = QAction(QIcon(icon_gas_model), "Add Gas", MainWindow)
        self.gas_model.triggered.connect(MainWindow.gas_model)

        
        icon_oil_model  = os.path.join(script_dir, "Icons", "oil_on")
        self.oil_model = QAction(QIcon(icon_oil_model), "Add Oil", MainWindow)
        self.oil_model.triggered.connect(MainWindow.oil_model)

        
        icon_delete_well= os.path.join(script_dir, "Icons", "delete")
        self.delete_well = QAction(QIcon(icon_delete_well), "Delete Well", MainWindow)
        self.delete_well.triggered.connect(MainWindow.delete_well)

        self.regenerate_curves.setEnabled(False)
        self.iterate_di.setEnabled(False)
        self.back_button.setEnabled(False)
        self.forward_button.setEnabled(False)
        self.graph_type.setEnabled(False)
        self.gas_model.setEnabled(False)
        self.oil_model.setEnabled(False)
        self.delete_well.setEnabled(False)
        self.import_action.setEnabled(False)



        

        graph_toolbar.addAction(self.regenerate_curves)
        graph_toolbar.addAction(self.iterate_di)
        graph_toolbar.addAction(self.back_button)
        graph_toolbar.addAction(self.forward_button)
        graph_toolbar.addAction(self.graph_type)
        graph_toolbar.addAction(self.gas_model)
        graph_toolbar.addAction(self.oil_model)
        graph_toolbar.addAction(self.delete_well)

        tab1_layout.addWidget(graph_toolbar, 0, 0, 1, 11)  # row: 0, column: 0-8

        # Placeholder for Plotly graph
        self.graph_area = QWebEngineView(MainWindow)
        web_settings = self.graph_area.settings()
        web_settings.setAttribute(QWebEngineSettings.JavascriptEnabled, True)
   
    
        tab1_layout.addWidget(self.graph_area, 1, 2, 7, 9)  # row: 1-7, column: 2-8

        # Create the Excel widget and set its properties
        self.excel_widget = QTableWidget(50, 20)  # 10 rows, 10 columns
        self.excel_widget.setHorizontalHeaderLabels(["Date", "Days", "Oil Volume", "Cum. oil", "Pred. Oil", "Oil Error", "Oil Revenue $", "Gas Volume", "Cum. Gas", "Pred. Gas", "Gas Error", "Gas Revenue $", "Total Revenue (M$)", "Disc. Net Revenue"])
## Set text alignment for headers to include wrapping
#        header = self.excel_widget.horizontalHeader()
#        header.setSectionResizeMode(QHeaderView.ResizeToContents)
#        for i in range(self.excel_widget.columnCount()):
#            header.setSectionResizeMode(i, QHeaderView.Stretch)  # Allow column to stretch
#            header.setDefaultAlignment(Qt.Alignment(Qt.AlignTop| Qt.AlignTop| Qt.TextWordWrap))

        self.excel_widget.verticalHeader().setVisible(False)
        for i in range(self.excel_widget.rowCount()):
            self.excel_widget.setRowHeight(i, 10)
            self.excel_widget.setColumnWidth(i, 80)  
        tab1_layout.addWidget(self.excel_widget, 8, 2, 2, 9 )  # row: 8-9, column: 2-8

        # Add the Excel layout to the central layout

        self.cf_excel_widget = QTableWidget(50, 10)  # 10 rows, 10 columns
        self.cf_excel_widget.setHorizontalHeaderLabels(["Date"])
        self.cf_excel_widget.verticalHeader().setVisible(False)
        for i in range(self.cf_excel_widget.rowCount()):
            self.cf_excel_widget.setRowHeight(i, 10)
            self.cf_excel_widget.setColumnWidth(i, 80)  
        tab2_layout.addWidget(self.cf_excel_widget, 0, 0, 9, 2 )  # row: 8-9, column: 2-8


        self.total_prod_rev_excel_widget = QTableWidget(50, 25)  # 10 rows, 10 columns
        self.total_prod_rev_excel_widget.setHorizontalHeaderLabels(["Date", "Revenue", "Disc. Revenue", "Pred. Oil", "Pred. Gas"])
        self.total_prod_rev_excel_widget.verticalHeader().setVisible(False)
        for i in range(self.total_prod_rev_excel_widget.rowCount()):
            self.total_prod_rev_excel_widget.setRowHeight(i, 10)
            self.total_prod_rev_excel_widget.setColumnWidth(i, 80)  
        tab2_layout.addWidget(self.total_prod_rev_excel_widget, 0, 3, 9, 6  )  # row: 8-9, column: 2-8



    def activate_icons(self):        
        self.regenerate_curves.setEnabled(True)
        self.iterate_di.setEnabled(True)
        self.back_button.setEnabled(True)
        self.forward_button.setEnabled(True)
        self.graph_type.setEnabled(True)
        self.gas_model.setEnabled(True)
        self.oil_model.setEnabled(True)
        self.delete_well.setEnabled(True)
        self.import_action.setEnabled(True)
        self.connect_action.setEnabled(True)




    def connect_parameters_triggers(self, MainWindow):
        pass
        # Connect triggers for oil and gas parameters
        #self.regenerate_curves.clicked.connect(MainWindow.update_decline_curve)
        #        # Connect signals of dialog elements to update_flag method
        ##self.option1_dropdown.currentTextChanged.connect(MainWindow.update_flag)
        ##self.option2_dropdown.currentTextChanged.connect(MainWindow.update_flag)
        #self.future_date_input.dateTimeChanged.connect(MainWindow.update_flag)
        #self.initial_gas_production_rate_input.textChanged.connect(MainWindow.update_flag)
        #self.initial_gas_decline_rate_input.textChanged.connect(MainWindow.update_flag)
        #self.gas_time_input.dateTimeChanged.connect(MainWindow.update_flag)
        #self.gas_b_factor_input.textChanged.connect(MainWindow.update_flag)
        #self.min_dec_gas.textChanged.connect(MainWindow.update_flag)
        #self.initial_oil_production_rate_input.textChanged.connect(MainWindow.update_flag)
        #self.initial_oil_decline_rate_input.textChanged.connect(MainWindow.update_flag)
        #self.oil_time_input.dateTimeChanged.connect(MainWindow.update_flag)
        #self.oil_b_factor_input.textChanged.connect(MainWindow.update_flag)
        #self.min_dec_oil.textChanged.connect(MainWindow.update_flag)




    def disconnect_parameters_triggers(self, MainWindow):

        self.option1_dropdown.currentTextChanged.disconnect(MainWindow.update_flag)
        self.option2_dropdown.currentTextChanged.disconnect(MainWindow.update_flag)
        self.future_date_input.dateTimeChanged.disconnect(MainWindow.update_flag)
        self.initial_gas_production_rate_input.textChanged.disconnect(MainWindow.update_flag)
        self.initial_gas_decline_rate_input.textChanged.disconnect(MainWindow.update_flag)
        self.gas_time_input.dateTimeChanged.disconnect(MainWindow.update_flag)
        self.gas_b_factor_input.textChanged.disconnect(MainWindow.update_flag)
        self.min_dec_gas.textChanged.disconnect(MainWindow.update_flag)
        self.initial_oil_production_rate_input.textChanged.disconnect(MainWindow.update_flag)
        self.initial_oil_decline_rate_input.textChanged.disconnect(MainWindow.update_flag)
        self.oil_time_input.dateTimeChanged.disconnect(MainWindow.update_flag)
        self.oil_b_factor_input.textChanged.disconnect(MainWindow.update_flag)
        self.min_dec_oil.textChanged.disconnect(MainWindow.update_flag)

    def calculate_net_price(self):
        try:
            # Get tax rate and operating expenditures from QLineEdit widgets
            royalty = float(self.royalty.text())
            working_interest = float(self.working_interest.text())
            nri = working_interest/100*(1-royalty/100)
            oil_price = float(self.oil_price.text())
            gas_price = float(self.gas_price.text())
            oil_price_dif = float(self.oil_price_dif.text())
            gas_price_dif = float(self.gas_price_dif.text())
            tax_rate = float(self.tax_rate.text())
            net_price_oil = nri*(oil_price - oil_price_dif)*(1-tax_rate/100)*(1-royalty/100)
            net_price_gas = nri*(gas_price - gas_price_dif)*(1-tax_rate/100)*(1-royalty/100)
            print(net_price_oil)





            # Update QLabel with calculated net price
            self.net_price_oil.setText(f"{net_price_oil:.2f}")
            self.net_price_gas.setText(f"{net_price_gas:.2f}")
        except ValueError:


            pass  # Handle invalid input

    def on_forcast_option_changed(self, index):
        if index == 0:  # Economic Limit selected
            self.ecl_date.setEnabled(False)  # Disable date input
        elif index == 1:  # Date selected
            self.ecl_date.setEnabled(True) 



if __name__ == "__main__":
    app = QApplication(sys.argv)
    MainWindow = QMainWindow()
    ui = UI_main()
    ui.setupUI(MainWindow)
    MainWindow.show()
    sys.exit(app.exec_())