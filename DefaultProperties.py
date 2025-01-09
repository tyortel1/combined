from PySide6.QtWidgets import (
    QDialog, QApplication, QDialogButtonBox, QVBoxLayout, QHBoxLayout, QWidget, 
    QTableWidget, QTableWidgetItem, QComboBox, QLineEdit, QLabel, QDateTimeEdit, QSpinBox
)

from PySide6.QtCore import QDateTime, QDate, QTime
from PySide6.QtGui import QDoubleValidator
import sys


class DefaultProperties(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Default Parameters")
        self.setGeometry(590, 257, 400, 700)
        self.setMinimumSize(120, 1)
        self.initUI()
        self.iterate_di = False
        self.properties = {}
        
        

    def initUI(self):

        # Option buttons layout
        options_layout = QVBoxLayout()
        iterate_di_layout = QHBoxLayout()
                        # Add a label for graph options
        iterate_options_label = QLabel("itereate Options")
        iterate_options_label.setStyleSheet("font-weight: bold; text-decoration: underline; font-size: 14px;")
        options_layout.addWidget(iterate_options_label)
        # QHBoxLayout for iterate_di dropdown
        iterate_di_layout = QHBoxLayout()



        self.iterate_di_dropdown = QComboBox()
        self.iterate_di_dropdown.addItem("True")
        self.iterate_di_dropdown.addItem("False")
        # Add more items as needed

        iterate_di_label = QLabel("Iterate:")  # Label for the dropdown
        iterate_di_layout.addWidget(iterate_di_label)
        iterate_di_layout.addWidget(self.iterate_di_dropdown)
        self.iterate_di_dropdown.currentTextChanged.connect(self.update_iterate_di_value)
        options_layout.addLayout(iterate_di_layout)
   

        ## QHBoxLayout for iterate_bfactor dropdown
        #iterate_bfactor_layout = QHBoxLayout()

        #self.iterate_bfactor_dropdown = QComboBox()
        #self.iterate_bfactor_dropdown.addItem("False")
        #self.iterate_bfactor_dropdown.addItem("True")
        ## Add more items as needed

        #iterate_bfactor_label = QLabel("Iterate BFactor:")  # Label for the dropdown
        #iterate_bfactor_layout.addWidget(iterate_bfactor_label)
        #iterate_bfactor_layout.addWidget(self.iterate_bfactor_dropdown)
        ##self.iterate_bfactor_dropdown.currentTextChanged.connect(self.update_iterate_bfactor_value)

        #options_layout.addLayout(iterate_di_layout)
        #options_layout.addLayout(iterate_bfactor_layout)


 #--------------------------------------------------------------------------------------------
        # Add a label for graph options
        graph_options_label = QLabel("Graph Options")
        graph_options_label.setStyleSheet("font-weight: bold; text-decoration: underline; font-size: 14px;")
        options_layout.addWidget(graph_options_label)






        self.option1_dropdown = QComboBox()
        self.option1_dropdown.addItem("Both")
        self.option1_dropdown.addItem("Oil")
        self.option1_dropdown.addItem("Gas")
 
        options_layout.addWidget(self.option1_dropdown)

        self.option2_dropdown = QComboBox()
        self.option2_dropdown.addItem("Exponential")
        self.option2_dropdown.addItem("Normal")
          # Connect signal to method
        options_layout.addWidget(self.option2_dropdown)

        #-----------------------------------------------------------------------------------------------------
        # Add labels for Gas Parameters
        gas_parameters_label = QLabel("Decline Curve Parameters")
        gas_parameters_label.setStyleSheet("font-weight: bold; text-decoration: underline;font-size: 14px;")  # Bold and underline the label
        options_layout.addWidget(gas_parameters_label)

    


                # QHBoxLayout for Gas B Factor
        gas_b_factor_layout = QHBoxLayout()
        gas_b_factor_label = QLabel("B Factor  Gas:")
        gas_b_factor_layout.addWidget(gas_b_factor_label)
        gas_b_factor_layout.addStretch(1)
        self.gas_b_factor_input = QLineEdit()
        self.gas_b_factor_input.setText(".6")
        validator = QDoubleValidator()
        self.gas_b_factor_input.setValidator(validator)
        gas_b_factor_layout.addWidget(self.gas_b_factor_input)
        options_layout.addLayout(gas_b_factor_layout)

                # QHBoxLayout for Gas Min Decline
        min_dec_gas_layout = QHBoxLayout()
        min_dec_gas_label = QLabel("Min Decline Gas:")
        min_dec_gas_layout.addWidget(min_dec_gas_label)
        min_dec_gas_layout.addStretch(1)
        self.min_dec_gas = QLineEdit()
        validator = QDoubleValidator()
        validator.setRange(0.0, 100.0, 2)
        self.min_dec_gas.setValidator(validator)
        self.min_dec_gas.setText("6.00")
        min_dec_gas_layout.addWidget(self.min_dec_gas)
        options_layout.addLayout(min_dec_gas_layout)


                 # Create a QHBoxLayout for the B factor elements
        b_factor_layout = QHBoxLayout()
        oil_b_factor_label = QLabel("B Factor Oil:")
        b_factor_layout.addWidget(oil_b_factor_label)
        b_factor_layout.addStretch(1)
        self.oil_b_factor_input = QLineEdit()
        self.oil_b_factor_input.setText(".6")
        validator = QDoubleValidator()
        self.oil_b_factor_input.setValidator(validator)
        b_factor_layout.addWidget(self.oil_b_factor_input)
        options_layout.addLayout(b_factor_layout)


                ## Hyperbolic exponent input for Oil
        # QHBoxLayout for Min Decline
        min_dec_oil_layout = QHBoxLayout()
        min_dec_oil_label = QLabel("Min Decline Oil:")
        min_dec_oil_layout.addWidget(min_dec_oil_label)
        min_dec_oil_layout.addStretch(1)
        self.min_dec_oil = QLineEdit()
        validator = QDoubleValidator()
        validator.setRange(0.0, 100.0, 2)
        self.min_dec_oil.setValidator(validator)
        self.min_dec_oil.setText("6.00")
        min_dec_oil_layout.addWidget(self.min_dec_oil)
        options_layout.addLayout(min_dec_oil_layout)


        options_layout.addSpacing(25)
                  # QHBoxLayout for Oil Start Date
  


#---------------------------------------------------------------------------------------------------
                # CASH FLOW PARAMETERS
#----------------------------------------------------------------
                # CASH FLOW PARAMETERS
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
        
        oil_price_label = QLabel("Oil Price $")
        oil_price_layout.addWidget(oil_price_label)
        oil_price_layout.addStretch(1)
        self.oil_price = QLineEdit()
        self.oil_price.setValidator(QDoubleValidator())
        self.oil_price.setText("70")
        oil_price_layout.addWidget(self.oil_price)
        options_layout.addLayout(oil_price_layout)

        # Initial decline rate input for Oil.
        # QHBoxLayout for DI (Initial Decline Rate)
        gas_price_layout = QHBoxLayout()
        
        gas_price_label = QLabel("Gas Price $:")
        gas_price_layout.addWidget(gas_price_label)
        gas_price_layout.addStretch(1)
        self.gas_price = QLineEdit()
        validator = QDoubleValidator(0.0, 100.0, 2)
        self.gas_price.setValidator(validator)
        self.gas_price.setText("2.5")
        gas_price_layout.addWidget(self.gas_price)
        options_layout.addLayout(gas_price_layout)
                # QHBoxLayout for IR (Initial Production Rate)
        oil_price_dif_layout = QHBoxLayout()
        
        oil_price_dif_label = QLabel("Oil Differential BBL $:")
        oil_price_dif_layout.addWidget(oil_price_dif_label)
        oil_price_dif_layout.addStretch(1)
        self.oil_price_dif = QLineEdit()
        self.oil_price_dif.setValidator(QDoubleValidator())
        self.oil_price_dif.setText("2.5")
        oil_price_dif_layout.addWidget(self.oil_price_dif)
        options_layout.addLayout(oil_price_dif_layout)

        # Initial decline rate input for Oil.
        # QHBoxLayout for DI (Initial Decline Rate)
        gas_price_dif_layout = QHBoxLayout()
        
        gas_price_dif_label = QLabel("Gas Differential MCF $:")
        gas_price_dif_layout.addWidget(gas_price_dif_label)
        gas_price_dif_layout.addStretch(1.5)
        self.gas_price_dif = QLineEdit()
        validator = QDoubleValidator(0.0, 100.0, 2)
        self.gas_price_dif.setText(".5")
        self.gas_price_dif.setValidator(validator)
        gas_price_dif_layout.addWidget(self.gas_price_dif)
        options_layout.addLayout(gas_price_dif_layout)

   
        
        # # Discount rate
        #discount_rate_layout = QHBoxLayout()
        
        #discount_rate_label = QLabel("Discount Rate %:")
        #discount_rate_layout.addWidget(discount_rate_label)
        #discount_rate_layout.addStretch(1)
        #self.discount_rate_input = QLineEdit()
        #self.discount_rate_input.setText("10")
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
        self.working_interest.setText("100")
        working_interest_layout.addWidget(self.working_interest)
        options_layout.addLayout(working_interest_layout)

                        ##Royalty
        royalty_layout = QHBoxLayout()
        royalty_label = QLabel("Royalty Interest %:")
        royalty_layout.addWidget(royalty_label)
        royalty_layout.addStretch(1)
        self.royalty = QLineEdit()
        validator = QDoubleValidator()
        validator.setRange(0.0, 100.0, 2)
        self.royalty.setValidator(validator)
        self.royalty.setText("12.5")
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
        self.discount_rate.setText("12.5")
        discount_rate_layout.addWidget(self.discount_rate)
        options_layout.addLayout(discount_rate_layout)



        #Tax Rate
        tax_rate_layout = QHBoxLayout()
        tax_rate_label = QLabel("Total Rate %:")
        tax_rate_layout.addWidget(tax_rate_label)
        tax_rate_layout.addStretch(1)
        self.tax_rate = QLineEdit()
        validator = QDoubleValidator()
        validator.setRange(0.0, 100.0, 2)
        self.tax_rate.setValidator(validator)
        self.tax_rate.setText("7")
        tax_rate_layout.addWidget(self.tax_rate)
        options_layout.addLayout(tax_rate_layout)








        #Operating expenditures
        operating_expenditures_layout = QHBoxLayout()
        operating_expenditures_label = QLabel("Operating Cost Monthly:")
        operating_expenditures_layout.addWidget(operating_expenditures_label)
        operating_expenditures_layout.addStretch(2)
        self.operating_expenditures = QLineEdit()
        validator = QDoubleValidator()
        validator.setRange(0.0, 100.0, 2)
        self.operating_expenditures.setValidator(validator)
        self.operating_expenditures.setText("10000")
        operating_expenditures_layout.addWidget(self.operating_expenditures)
        options_layout.addLayout(operating_expenditures_layout)



        #net Price oil
        net_price_oil_layout = QHBoxLayout()
        net_price_oil_label = QLabel("Net Price Oil:")
        net_price_oil_layout.addWidget(net_price_oil_label)
        net_price_oil_layout.addStretch(2)
        self.net_price_oil = QLineEdit()
        validator = QDoubleValidator()
        validator.setRange(0.0, 100.0, 2)
        self.net_price_oil.setValidator(validator)
        self.net_price_oil.setText("0")
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
        self.net_price_gas.setText("0")
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
        self.capital_expenditures.setText("10000000")
        capital_expenditures_layout.addWidget(self.capital_expenditures)
        options_layout.addLayout(capital_expenditures_layout)

        self.setLayout(options_layout)

 

            # Create an OK button
        button_box = QDialogButtonBox(QDialogButtonBox.Ok)
        button_box.accepted.connect(self.accept)
        options_layout.addWidget(button_box)

        self.setLayout(options_layout)

        self.calculate_net_price()

        self.royalty.editingFinished.connect(self.calculate_net_price)
        self.working_interest.editingFinished.connect(self.calculate_net_price)
        self.oil_price.editingFinished.connect(self.calculate_net_price)
        self.gas_price.editingFinished.connect(self.calculate_net_price)
        self.oil_price_dif.editingFinished.connect(self.calculate_net_price)
        self.gas_price_dif.editingFinished.connect(self.calculate_net_price)
        self.tax_rate.editingFinished.connect(self.calculate_net_price)

    def update_iterate_di_value(self, text):
        self.iterate_di = text

    def update_iterate_bfactor_value(self, text):
        self.iterate_bfactor = text


    def on_forcast_option_changed(self, index):
        if index == 0:  # Economic Limit selected
            self.ecl_date.setEnabled(False)  # Disable date input
        elif index == 1:  # Date selected
            self.ecl_date.setEnabled(True) 

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


    def accept(self):
        # Emit parameters when the dialog is accepted
        self.properties = {
            'oil_price': float(self.oil_price.text()),
            'gas_price': float(self.gas_price.text()),
            'oil_price_dif': float(self.oil_price_dif.text()),
            'gas_price_dif': float(self.gas_price_dif.text()),
            #'discount_rate': float(self.discount_rate_input.text()),
            'working_interest': float(self.working_interest.text()),
            'royalty': float(self.royalty.text()),
            'discount_rate': float(self.discount_rate.text()),
            'tax_rate': float(self.tax_rate.text()),
            'operating_expenditures': float(self.operating_expenditures.text()),
            'capital_expenditures': float(self.capital_expenditures.text()),
            'gas_b_factor': float(self.gas_b_factor_input.text()),
            'min_dec_gas': float(self.min_dec_gas.text()),
            'oil_b_factor': float(self.oil_b_factor_input.text()),
            'min_dec_oil': float(self.min_dec_oil.text()),
            'ecl_date': self.ecl_date.dateTime().toString("yyyy-MM-dd"),
            'iterate_di': self.iterate_di_dropdown.currentText(),
            #'iterate_bfactor': self.iterate_bfactor_dropdown.currentText(),
            'economic_limit_type': self.end_forcast_type.currentText(),
            'economic_limit_date': self.ecl_date.dateTime().toString("yyyy-MM-dd"),
            'net_price_oil' : self.net_price_oil.text(),
            'net_price_gas' : self.net_price_gas.text(),
          }
    
        super().accept()
        return self.properties



    def calculate_total_reserves(self):
        # Initialize dictionaries to store the total reserves for each uwi
        uwi_oil_reserves = {}
        uwi_gas_reserves = {}
        
        # Group the DataFrame by uwi and sum the oil and gas volumes for each group
        for uwi, uwi_group in self.df_combined_all.groupby('uwi'):
            total_oil_reserves = uwi_group['oil_volume'].sum()
            total_gas_reserves = uwi_group['gas_volume'].sum()
            uwi_oil_reserves[uwi] = total_oil_reserves
            uwi_gas_reserves[uwi] = total_gas_reserves
        
        return uwi_oil_reserves, uwi_gas_reserves

if __name__ == "__main__":
    app = QApplication(sys.argv)
    dialog = DefaultProperties()
    dialog.exec_()
    sys.exit(app.exec_())