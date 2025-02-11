import sys
import os
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QLabel,
    QMenuBar,
    QTabWidget,
    QComboBox,
    QToolBar,
    QLineEdit,
    QDateTimeEdit,
    QTableWidget,
    QCheckBox, QSpacerItem, QSizePolicy, QLayout, QMenu, QDialog
   
)
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtGui import QIcon, QDoubleValidator, QAction
from PySide6.QtCore import Qt, QDate, QDateTime, QSize
from PySide6.QtWebEngineCore import QWebEngineSettings
from SaveDeclineCurveDialog import SaveDeclineCurveDialog


class UI_main:
    def __init__(self):
        self.recent_projects_file = os.path.join(os.path.expanduser('~'), 'recent_projects.txt')
        self.script_dir = None
        self.gas_parameters_widgets = []
        self.oil_parameters_widgets = []
        self.cash_flow_parameters_widgets = []
        self.well_dropdown = None

    def setupUI(self, MainWindow):
        # Set main window properties
        MainWindow.setWindowTitle("Qt Dialog with Plotly Graph")
        MainWindow.setGeometry(100, 100, 1400, 1000)

        # Initialize script directory for resources
        self.script_dir = os.path.dirname(os.path.realpath(__file__))

        # Set up the menu bar
        menu_bar = MainWindow.menuBar()

        # Add Help menu
        help_menu = menu_bar.addMenu("&Help")
        help_action = QAction("&About Plotly Graph", MainWindow)
        help_action.triggered.connect(MainWindow.show_help)  # Connect to MainWindow's method
        help_menu.addAction(help_action)

        # Set central widget
        central_widget = QWidget(MainWindow)
        MainWindow.setCentralWidget(central_widget)

        # Set layout for central widget
        main_layout = QVBoxLayout(central_widget)


        # Create tab widget
        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)

        # Create tabs
        self.create_dca_tab(MainWindow)
        self.create_well_parameters_tab(MainWindow)
        self.create_future_production_tab(MainWindow)


        self.tab_widget.currentChanged.connect(MainWindow.on_tab_changed) 

    def create_dca_tab(self, MainWindow):
        tab1 = QWidget()
        tab1_layout = QGridLayout(tab1)
        self.tab_widget.addTab(tab1, "DCA")

        # Option buttons layout
        options_layout = QVBoxLayout()
        tab1_layout.addLayout(options_layout, 2, 0, 8, 2)  # row: 1-8, column: 0-1

        # Add a label for graph options
        options_label = QLabel("Graph Options")
        options_label.setStyleSheet("font-weight: bold; text-decoration: underline; font-size: 14px;")
        options_layout.addWidget(options_label)

        well_type_layout = QHBoxLayout()
        well_type_label = QLabel("Well Type:")
        well_type_layout.addWidget(well_type_label)
        well_type_layout.addStretch(1)
        self.well_type_dropdown = QComboBox()
        self.well_type_dropdown.addItem("Active")
        self.well_type_dropdown.addItem("Planned")
        self.well_type_dropdown.currentTextChanged.connect(MainWindow.set_well_type)  # Connect signal to method
        self.well_type_dropdown.setMinimumWidth(150)  # Set minimum width
        well_type_layout.addWidget(self.well_type_dropdown)
        options_layout.addLayout(well_type_layout)

                    # Scenarios dropdown (initially hidden)
        # Scenarios dropdown (initially hidden)
        scenario_layout1 = QHBoxLayout()
        scenario_label1 = QLabel("Scenario:")
        scenario_layout1.addWidget(scenario_label1)
        scenario_layout1.addStretch(1)
        self.scenario_dropdown1 = QComboBox()
        self.scenario_dropdown1.currentTextChanged.connect(MainWindow.on_scenario_changed_tab1)
        self.scenario_dropdown1.setMinimumWidth(150)  # Set minimum width
         # Initially hidden
        scenario_layout1.addWidget(self.scenario_dropdown1)
        options_layout.addLayout(scenario_layout1)


        # Option 1 dropdown for Graph Type
        option1_layout = QHBoxLayout()
        option1_label = QLabel("Graph Type:")
        option1_layout.addWidget(option1_label)
        option1_layout.addStretch(1)
        self.option1_dropdown = QComboBox()
        self.option1_dropdown.addItem("Decline Curve")
        self.option1_dropdown.addItem("Cash Flow")
        self.option1_dropdown.currentTextChanged.connect(MainWindow.set_graph_type) 
        self.option1_dropdown.setMinimumWidth(150)  # Connect signal to method
        option1_layout.addWidget(self.option1_dropdown)
        options_layout.addLayout(option1_layout)

       # Well dropdown
        well_layout = QHBoxLayout()
        well_label = QLabel("Select Well:")
        well_layout.addWidget(well_label)
        well_layout.addStretch(1)
        self.well_dropdown = QComboBox()
        self.well_dropdown.currentIndexChanged.connect(MainWindow.on_well_selected)
        self.well_dropdown.setMinimumWidth(150) # Connect signal to method
        well_layout.addWidget(self.well_dropdown)
        options_layout.addLayout(well_layout)
        self.well_type_dropdown.setEnabled(False)
        self.option1_dropdown.setEnabled(False)
        self.well_dropdown.setEnabled(False)

        # Gas Parameters
        self.gas_parameters_widgets = []
        gas_parameters_label = QLabel("Gas Parameters")
        gas_parameters_label.setStyleSheet("font-weight: bold; text-decoration: underline;font-size: 14px;")  # Bold and underline the label
        options_layout.addWidget(gas_parameters_label)
        self.gas_parameters_widgets.append(gas_parameters_label)

        # Gas parameters widgets
        gas_time_layout = QHBoxLayout()
        gas_time_label = QLabel("Start Date:")
        gas_time_layout.addWidget(gas_time_label)
        gas_time_layout.addStretch(1)
        self.gas_time_input = QDateTimeEdit()
        self.gas_time_input.setCalendarPopup(True)
        self.gas_time_input.setDisplayFormat("yyyy-MM-dd")
        gas_time_layout.addWidget(self.gas_time_input)
        options_layout.addLayout(gas_time_layout)
        self.gas_parameters_widgets.extend([gas_time_label, gas_time_layout])

        ir_gas_layout = QHBoxLayout()
        ir_gas_label = QLabel("IR:")
        ir_gas_layout.addWidget(ir_gas_label)
        ir_gas_layout.addStretch(1)
        self.initial_gas_production_rate_input = QLineEdit()
        self.initial_gas_production_rate_input.setValidator(QDoubleValidator())
        ir_gas_layout.addWidget(self.initial_gas_production_rate_input)
        options_layout.addLayout(ir_gas_layout)
        self.gas_parameters_widgets.extend([ir_gas_label, ir_gas_layout])

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
        self.gas_parameters_widgets.extend([di_gas_label, di_gas_layout])

        gas_b_factor_layout = QHBoxLayout()
        gas_b_factor_label = QLabel("B Factor:")
        gas_b_factor_layout.addWidget(gas_b_factor_label)
        gas_b_factor_layout.addStretch(1)
        self.gas_b_factor_input = QLineEdit()
        validator = QDoubleValidator()
        self.gas_b_factor_input.setValidator(validator)
        gas_b_factor_layout.addWidget(self.gas_b_factor_input)
        options_layout.addLayout(gas_b_factor_layout)
        self.gas_parameters_widgets.extend([gas_b_factor_label, gas_b_factor_layout])

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
        self.gas_parameters_widgets.extend([min_dec_gas_label, min_dec_gas_layout])

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
        self.gas_parameters_widgets.extend([error_gas_label, error_gas_layout])

        # Oil Parameters
        self.oil_parameters_widgets = []
        oil_parameters_label = QLabel("Oil Parameters")
        oil_parameters_label.setStyleSheet("font-weight: bold; text-decoration: underline;font-size: 14px;")  # Bold and underline the label
        options_layout.addWidget(oil_parameters_label)
        self.oil_parameters_widgets.append(oil_parameters_label)

        oil_time_layout = QHBoxLayout()
        oil_time_label = QLabel("Start Date:")
        oil_time_layout.addWidget(oil_time_label)
        oil_time_layout.addStretch(1)
        self.oil_time_input = QDateTimeEdit()
        self.oil_time_input.setCalendarPopup(True)
        self.oil_time_input.setDisplayFormat("yyyy-MM-dd")
        oil_time_layout.addWidget(self.oil_time_input)
        options_layout.addLayout(oil_time_layout)
        self.oil_parameters_widgets.extend([oil_time_label, oil_time_layout])

        ir_oil_layout = QHBoxLayout()
        ir_oil_label = QLabel("IR:")
        ir_oil_layout.addWidget(ir_oil_label)
        ir_oil_layout.addStretch(1)
        self.initial_oil_production_rate_input = QLineEdit()
        self.initial_oil_production_rate_input.setValidator(QDoubleValidator())
        ir_oil_layout.addWidget(self.initial_oil_production_rate_input)
        options_layout.addLayout(ir_oil_layout)
        self.oil_parameters_widgets.extend([ir_oil_label, ir_oil_layout])

        di_oil_layout = QHBoxLayout()
        di_oil_label = QLabel("DI:")
        di_oil_layout.addWidget(di_oil_label)
        di_oil_layout.addStretch(1)
        self.initial_oil_decline_rate_input = QLineEdit()
        validator = QDoubleValidator(0.0, 100.0, 2)
        self.initial_oil_decline_rate_input.setValidator(validator)
        di_oil_layout.addWidget(self.initial_oil_decline_rate_input)
        options_layout.addLayout(di_oil_layout)
        self.oil_parameters_widgets.extend([di_oil_label, di_oil_layout])

        oil_b_factor_layout = QHBoxLayout()
        oil_b_factor_label = QLabel("B Factor:")
        oil_b_factor_layout.addWidget(oil_b_factor_label)
        oil_b_factor_layout.addStretch(1)
        self.oil_b_factor_input = QLineEdit()
        validator = QDoubleValidator()
        self.oil_b_factor_input.setValidator(validator)
        oil_b_factor_layout.addWidget(self.oil_b_factor_input)
        options_layout.addLayout(oil_b_factor_layout)
        self.oil_parameters_widgets.extend([oil_b_factor_label, oil_b_factor_layout])

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
        self.oil_parameters_widgets.extend([min_dec_oil_label, min_dec_oil_layout])

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
        self.oil_parameters_widgets.extend([error_oil_label, error_oil_layout])

        # Cash Flow Parameters
        self.cash_flow_parameters_widgets = []
        cash_flow_label = QLabel("Cash Flow Parameters")
        cash_flow_label.setStyleSheet("font-weight: bold; text-decoration: underline;font-size: 14px;")  # Bold and underline the label
        options_layout.addWidget(cash_flow_label)
        self.cash_flow_parameters_widgets.append(cash_flow_label)

        end_forecast_layout = QHBoxLayout()
        end_forecast_label = QLabel("Forecast Limit")
        end_forecast_layout.addWidget(end_forecast_label)
        end_forecast_layout.addStretch(1)
        self.end_forecast_type = QComboBox()
        self.end_forecast_type.addItem("Net Dollars")
        self.end_forecast_type.addItem("End Date")
        self.end_forecast_type.addItem("GOR")
        self.end_forecast_type.currentTextChanged.connect(self.on_forecast_option_changed)
        end_forecast_layout.addWidget(self.end_forecast_type)
        options_layout.addLayout(end_forecast_layout)
        self.cash_flow_parameters_widgets.extend([end_forecast_label, end_forecast_layout])

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
        ecl_date_layout.addWidget(self.ecl_date)
        options_layout.addLayout(ecl_date_layout)
        self.cash_flow_parameters_widgets.extend([ecl_date_label, ecl_date_layout])

        oil_price_layout = QHBoxLayout()
        oil_price_label = QLabel("Oil $")
        oil_price_layout.addWidget(oil_price_label)
        oil_price_layout.addStretch(1)
        self.oil_price = QLineEdit()
        self.oil_price.setValidator(QDoubleValidator())
        oil_price_layout.addWidget(self.oil_price)
        options_layout.addLayout(oil_price_layout)
        self.cash_flow_parameters_widgets.extend([oil_price_label, oil_price_layout])

        gas_price_layout = QHBoxLayout()
        gas_price_label = QLabel("Gas $:")
        gas_price_layout.addWidget(gas_price_label)
        gas_price_layout.addStretch(1.5)
        self.gas_price = QLineEdit()
        validator = QDoubleValidator(0.0, 100.0, 2)
        self.gas_price.setValidator(validator)
        gas_price_layout.addWidget(self.gas_price)
        options_layout.addLayout(gas_price_layout)
        self.cash_flow_parameters_widgets.extend([gas_price_label, gas_price_layout])

        oil_price_dif_layout = QHBoxLayout()
        oil_price_dif_label = QLabel("OilDif BBL $:")
        oil_price_dif_layout.addWidget(oil_price_dif_label)
        oil_price_dif_layout.addStretch(1)
        self.oil_price_dif = QLineEdit()
        self.oil_price_dif.setValidator(QDoubleValidator())
        oil_price_dif_layout.addWidget(self.oil_price_dif)
        options_layout.addLayout(oil_price_dif_layout)
        self.cash_flow_parameters_widgets.extend([oil_price_dif_label, oil_price_dif_layout])

        gas_price_dif_layout = QHBoxLayout()
        gas_price_dif_label = QLabel("GasDif MCF $:")
        gas_price_dif_layout.addWidget(gas_price_dif_label)
        gas_price_dif_layout.addStretch(1.5)
        self.gas_price_dif = QLineEdit()
        validator = QDoubleValidator(0.0, 100.0, 2)
        self.gas_price_dif.setValidator(validator)
        gas_price_dif_layout.addWidget(self.gas_price_dif)
        options_layout.addLayout(gas_price_dif_layout)
        self.cash_flow_parameters_widgets.extend([gas_price_dif_label, gas_price_dif_layout])

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
        self.cash_flow_parameters_widgets.extend([working_interest_label, working_interest_layout])

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
        self.cash_flow_parameters_widgets.extend([royalty_label, royalty_layout])

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
        self.cash_flow_parameters_widgets.extend([discount_rate_label, discount_rate_layout])

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
        self.cash_flow_parameters_widgets.extend([tax_rate_label, tax_rate_layout])

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
        self.cash_flow_parameters_widgets.extend([net_price_oil_label, net_price_oil_layout])

        net_price_gas_layout = QHBoxLayout()
        net_price_gas_label = QLabel("Net Price Gas:")
        net_price_gas_layout.addWidget(net_price_gas_label)
        net_price_gas_layout.addStretch(2)
        self.net_price_gas = QLineEdit()
        validator = QDoubleValidator()
        validator.setRange(0.0, 100.0, 2)
        self.net_price_gas.setValidator(validator)
        net_price_gas_layout.addWidget(self.net_price_gas)
        options_layout.addLayout(net_price_gas_layout)
        self.cash_flow_parameters_widgets.extend([net_price_gas_label, net_price_gas_layout])

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
        self.cash_flow_parameters_widgets.extend([capital_expenditures_label, capital_expenditures_layout])

        operating_expenditures_layout = QHBoxLayout()
        operating_expenditures_label = QLabel("Opex / month:")
        operating_expenditures_layout.addWidget(operating_expenditures_label)
        operating_expenditures_layout.addStretch(2)
        self.operating_expenditures = QLineEdit()
        validator = QDoubleValidator()
        validator.setRange(0.0, 100.0, 2)
        self.operating_expenditures.setValidator(validator)
        operating_expenditures_layout.addWidget(self.operating_expenditures)
        options_layout.addLayout(operating_expenditures_layout)
        self.cash_flow_parameters_widgets.extend([operating_expenditures_label, operating_expenditures_layout])

        self.calculate_net_price()
        self.royalty.editingFinished.connect(self.calculate_net_price)
        self.working_interest.editingFinished.connect(self.calculate_net_price)
        self.oil_price.editingFinished.connect(self.calculate_net_price)
        self.gas_price.editingFinished.connect(self.calculate_net_price)
        self.oil_price_dif.editingFinished.connect(self.calculate_net_price)
        self.gas_price_dif.editingFinished.connect(self.calculate_net_price)
        self.tax_rate.editingFinished.connect(self.calculate_net_price)

        options_layout.addStretch()

        graph_toolbar = QToolBar("Graph Toolbar")
        graph_toolbar.setIconSize(QSize(32, 32))  # Set the icon size

        # Add actions to the graph options toolbar
        icon_path_regenerate = os.path.join(self.script_dir, "Icons", "Update Curve")
        self.regenerate_curves = QAction(QIcon(icon_path_regenerate), "Update", MainWindow)
        self.regenerate_curves.triggered.connect(MainWindow.update_decline_curve)

        icon_path_iterate = os.path.join(self.script_dir, "Icons", "Iterate")
        self.iterate_di = QAction(QIcon(icon_path_iterate), "Iterate", MainWindow)
        self.iterate_di.triggered.connect(MainWindow.iterate_curve)

        icon_path_exponential = os.path.join(self.script_dir, "Icons", "Logrithmic.png")
        self.graph_type = QAction(QIcon(icon_path_exponential), "Exponential", MainWindow)
        self.graph_type.triggered.connect(MainWindow.set_distribution_type)

        icon_path_back = os.path.join(self.script_dir, "Icons", "back")
        self.back_button = QAction(QIcon(icon_path_back), "Graph Action 1", MainWindow)
        self.back_button.triggered.connect(MainWindow.navigate_back)

        icon_path_forward = os.path.join(self.script_dir, "Icons", "forward")
        self.forward_button = QAction(QIcon(icon_path_forward), "Next Well", MainWindow)
        self.forward_button.triggered.connect(MainWindow.navigate_forward)

        icon_gas_model = os.path.join(self.script_dir, "Icons", "gas_on")
        self.gas_model = QAction(QIcon(icon_gas_model), "Add Gas", MainWindow)
        self.gas_model.triggered.connect(MainWindow.gas_model)

        icon_oil_model = os.path.join(self.script_dir, "Icons", "oil_on")
        self.oil_model = QAction(QIcon(icon_oil_model), "Add Oil", MainWindow)
        self.oil_model.triggered.connect(MainWindow.oil_model)

        save_dc = os.path.join(self.script_dir, "Icons", "Save Type")
        self.save_dc = QAction(QIcon(save_dc), "Save Type Curve", MainWindow)
        self.save_dc.triggered.connect(MainWindow.save_dc)

        icon_delete_well = os.path.join(self.script_dir, "Icons", "delete")
        self.delete_well = QAction(QIcon(icon_delete_well), "Delete Well", MainWindow)
        self.delete_well.triggered.connect(MainWindow.delete_well)

        launch_combined_cashflow = os.path.join(self.script_dir, "Icons", "Launch Graph")
        self.launch_combined_cashflow = QAction(QIcon(launch_combined_cashflow), "Launch Combined Cashflow", MainWindow)
        self.launch_combined_cashflow.triggered.connect(MainWindow.launch_combined_cashflow)

        self.regenerate_curves.setEnabled(False)
        self.iterate_di.setEnabled(False)
        self.back_button.setEnabled(False)
        self.forward_button.setEnabled(False)
        self.graph_type.setEnabled(False)
        self.gas_model.setEnabled(False)
        self.oil_model.setEnabled(False)
        self.delete_well.setEnabled(False)
        self.launch_combined_cashflow.setEnabled(False)
        self.scenario_dropdown1.setEnabled(False)
        self.save_dc.setEnabled(True)


        graph_toolbar.addAction(self.back_button)
        graph_toolbar.addAction(self.forward_button)
        graph_toolbar.addAction(self.graph_type)
        graph_toolbar.addAction(self.regenerate_curves)
        graph_toolbar.addAction(self.iterate_di)
        graph_toolbar.addAction(self.save_dc)
        graph_toolbar.addAction(self.delete_well)
        graph_toolbar.addAction(self.gas_model)
        graph_toolbar.addAction(self.oil_model)
        graph_toolbar.addAction(self.launch_combined_cashflow)

        tab1_layout.addWidget(graph_toolbar, 0, 0, 1, 11)  # row: 0, column: 0-8


        options_layout.addStretch()
        # Placeholder for Plotly graph
        self.graph_area = QWebEngineView(MainWindow)
        web_settings = self.graph_area.settings()
        web_settings.setAttribute(QWebEngineSettings.JavascriptEnabled, True)
        tab1_layout.addWidget(self.graph_area, 1, 2, 7, 9)  # row: 1-7, column: 2-8

        # Create the Excel widget and set its properties
        self.excel_widget = QTableWidget(50, 20)  # 50 rows, 20 columns
        self.excel_widget.setHorizontalHeaderLabels(["Date", "Days", "Oil Volume", "Cum. oil", "Pred. Oil", "Oil Error", "Oil Revenue $", "Gas Volume", "Cum. Gas", "Pred. Gas", "Gas Error", "Gas Revenue $", "Total Revenue (M$)", "Disc. Net Revenue"])
        self.excel_widget.verticalHeader().setVisible(False)
        for i in range(self.excel_widget.rowCount()):
            self.excel_widget.setRowHeight(i, 10)
            self.excel_widget.setColumnWidth(i, 80)
        tab1_layout.addWidget(self.excel_widget, 8, 2, 2, 9)  # row: 8-9, column: 2-8

    def create_well_parameters_tab(self, MainWindow):
        tab2 = QWidget()
        tab2_layout = QGridLayout(tab2)
        self.tab_widget.addTab(tab2, "Well Parameters")
    
        model_toolbar = QToolBar("Model Toolbar")
        model_toolbar.setIconSize(QSize(32, 32))
        update_action = QAction(QIcon(os.path.join(self.script_dir, "Icons", "Update Curve")), "Update Curves", MainWindow)
        update_action.triggered.connect(MainWindow.model_table_update)
        model_toolbar.addAction(update_action)
        tab2_layout.addWidget(model_toolbar, 0, 1, 1, 6)
    
        self.scenario_dropdown2 = QComboBox()
        self.scenario_dropdown2.setFixedHeight(32)
        self.scenario_dropdown2.currentTextChanged.connect(MainWindow.on_scenario_changed2)
        tab2_layout.addWidget(self.scenario_dropdown2, 0, 0, 1, 1)
    
        self.model_properties = QTableWidget(30, 33)
    
        # Set up context menu
        self.model_properties.setContextMenuPolicy(Qt.CustomContextMenu)
        self.model_properties.customContextMenuRequested.connect(MainWindow.show_context_menu)
    
        # Rest of your existing table setup code
        self.model_properties.setHorizontalHeaderLabels([
            "UWI", "max_oil_production", "max_gas_production", "max_oil_production_date", "max_gas_production_date",
            "one_year_oil_production", "one_year_gas_production", "di_oil", "di_gas", "oil_b_factor", "gas_b_factor",
            "min_dec_oil", "min_dec_gas", "model_oil", "model_gas", "gas_b_factor", "oil_b_factor", "oil_price",
            "gas_price", "oil_price_dif", "gas_price_dif", "discount_rate", "working_interest", "royalty", "tax_rate",
            "capital_expenditures", "operating_expenditures", "economic_limit_type", "economic_limit_date", "net_price_oil",
            "net_price_gas", "gas_model_status", "oil_model_status"
        ])
    
        self.model_properties.verticalHeader().setVisible(False)
        for i in range(self.model_properties.rowCount()):
            self.model_properties.setRowHeight(i, 10)
            self.model_properties.setColumnWidth(i, 80)
    
        tab2_layout.addWidget(self.model_properties, 1, 0, 9, 6)
        self.model_properties.itemChanged.connect(MainWindow.on_model_properties_item_changed)
    
        header = self.model_properties.horizontalHeader()
        header.sectionClicked.connect(MainWindow.on_header_clicked)

    def create_future_production_tab(self, MainWindow):
        # Create the tab and layout
        tab3 = QWidget()
        tab3_layout = QGridLayout(tab3)
        self.tab_widget.addTab(tab3, "Future Production")

        # Scenario dropdown
        self.scenario_dropdown3 = QComboBox()
        self.scenario_dropdown3.setFixedHeight(32)  # Set the height to 32px
        self.scenario_dropdown3.currentTextChanged.connect(MainWindow.on_scenario_changed3)

        # Dropdown for data type selection
        self.data_type_dropdown3 = QComboBox()
        self.data_type_dropdown3.setFixedHeight(32)  # Set the height to 32px
        self.data_type_dropdown3.addItem("Gas Production")
        self.data_type_dropdown3.addItem("Oil Production")
        self.data_type_dropdown3.addItem("Total Revenues")
        self.data_type_dropdown3.currentTextChanged.connect(MainWindow.updateTable3)

        # Checkbox for active wells selection
        self.include_active_wells_checkbox = QCheckBox("Include Active Wells")
        self.include_active_wells_checkbox.setFixedHeight(32)  # Set the height to 32px
        self.include_active_wells_checkbox.stateChanged.connect(MainWindow.updateTable3)

        # Create a horizontal layout for the dropdowns
        dropdown_layout = QHBoxLayout()
        dropdown_layout.addWidget(QLabel("Scenario:"))
        dropdown_layout.addWidget(self.scenario_dropdown3)
        dropdown_layout.addWidget(QLabel("Data Type:"))
        dropdown_layout.addWidget(self.data_type_dropdown3)
        dropdown_layout.addWidget(self.include_active_wells_checkbox)
    
        # Add a spacer to control the width of the dropdowns
        dropdown_layout.addSpacerItem(QSpacerItem(60, 32, QSizePolicy.Expanding, QSizePolicy.Minimum))

        # Add the dropdown layout to the tab3 layout at the appropriate position
        tab3_layout.addLayout(dropdown_layout, 0, 0, 1, 2)  # Adjust the row, column, rowSpan, and columnSpan as needed

        # Table for displaying data
        self.data_table3 = QTableWidget()
        tab3_layout.addWidget(self.data_table3, 1, 1, 1, 1)  # Adjust the row, column, rowSpan, and columnSpan as needed

        # Create the graph area for displaying graphs
        self.graph_area3 = QWebEngineView(MainWindow)  # Using a distinct name for this graph area
        web_settings = self.graph_area3.settings()
        web_settings.setAttribute(QWebEngineSettings.JavascriptEnabled, True)
        tab3_layout.addWidget(self.graph_area3, 1, 0, 1, 1)  # Adjust the row, column, rowSpan, and columnSpan as needed

        # Adjust the column spans to make sure the graph area and table are properly aligned
        tab3_layout.setColumnStretch(0, 1)
        tab3_layout.setColumnStretch(1, 1)

        # Set the layout for the tab
        tab3.setLayout(tab3_layout)



    def activate_icons(self):
        self.regenerate_curves.setEnabled(True)
        self.iterate_di.setEnabled(True)
        self.back_button.setEnabled(True)
        self.forward_button.setEnabled(True)
        self.graph_type.setEnabled(True)
        self.gas_model.setEnabled(True)
        self.oil_model.setEnabled(True)
        self.delete_well.setEnabled(True)
    

   
        self.launch_combined_cashflow.setEnabled(True)
        self.well_type_dropdown.setEnabled(True)
        self.option1_dropdown.setEnabled(True)
        self.well_dropdown.setEnabled(True)
        self.scenario_dropdown1.setEnabled(True)

  

    def calculate_net_price(self):
        try:
            # Get tax rate and operating expenditures from QLineEdit widgets
            royalty = float(self.royalty.text())
            working_interest = float(self.working_interest.text())
            nri = working_interest / 100 * (1 - royalty / 100)
            oil_price = float(self.oil_price.text())
            gas_price = float(self.gas_price.text())
            oil_price_dif = float(self.oil_price_dif.text())
            gas_price_dif = float(self.gas_price_dif.text())
            tax_rate = float(self.tax_rate.text())
            net_price_oil = nri * (oil_price - oil_price_dif) * (1 - tax_rate / 100)
            net_price_gas = nri * (gas_price - gas_price_dif) * (1 - tax_rate / 100)
            print(net_price_oil)

            # Update QLabel with calculated net price
            self.net_price_oil.setText(f"{net_price_oil:.2f}")
            self.net_price_gas.setText(f"{net_price_gas:.2f}")
        except ValueError:
            pass  # Handle invalid input

    def on_forecast_option_changed(self, text):
        if text == "Net Dollars":  # Economic Limit selected
            self.ecl_date.setEnabled(False)  # Disable date input
        elif text == "End Date":  # Date selected
            self.ecl_date.setEnabled(True)  # Enable date input
        elif text == "GOR":  # Another option, for example
            self.ecl_date.setEnabled(False)  # Adjust as needed for GOR

    def set_graph_type(self, graph_type):
        if graph_type == "Decline Curve":
            self.toggle_parameter_widgets(self.gas_parameters_widgets, True)
            self.toggle_parameter_widgets(self.oil_parameters_widgets, True)
            self.toggle_parameter_widgets(self.cash_flow_parameters_widgets, False)
        elif graph_type == "Cash Flow":
            self.toggle_parameter_widgets(self.gas_parameters_widgets, False)
            self.toggle_parameter_widgets(self.oil_parameters_widgets, False)
            self.toggle_parameter_widgets(self.cash_flow_parameters_widgets, True)

    def toggle_parameter_widgets(self, widgets, visible):
        for widget in widgets:
            if isinstance(widget, QWidget):
                widget.setVisible(visible)
            elif isinstance(widget, QLayout):
                for i in range(widget.count()):
                    item = widget.itemAt(i)
                    if item.widget():
                        item.widget().setVisible(visible)




if __name__ == "__main__":
    app = QApplication(sys.argv)
    MainWindow = QMainWindow()
    ui = UI_main()
    ui.setupUI(MainWindow)
    MainWindow.set_graph_type("Decline Curve")  # Initialize with Decline Curve
    MainWindow.show()
    sys.exit(app.exec_()) 