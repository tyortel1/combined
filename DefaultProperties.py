from PySide6.QtWidgets import (
    QDialog, QApplication, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel, QDateTimeEdit
)
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QDoubleValidator
import sys
from StyledDropdown import StyledDropdown
from StyledDropdown import StyledDropdown, StyledInputBox, StyledDateSelector
from StyledButton import StyledButton  # Keep this if StyledButton is used
  # Import the new StyledInputBox


class DefaultProperties(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Default Decline Curve Parameters")
        self.setGeometry(590, 257, 800, 600)  # Wider dialog
        self.setMinimumSize(800, 600)

        self.properties = {}
        self.initUI()

    def initUI(self):
        # Main layout
        main_layout = QVBoxLayout(self)

        # Two-column layout for parameters
        columns_layout = QHBoxLayout()

        # Left column - Decline Curve Parameters
        left_column = QVBoxLayout()
        decline_curve_group = self.create_decline_curve_section()
        left_column.addWidget(decline_curve_group)

        # Right column - Cash Flow Parameters
        right_column = QVBoxLayout()
        cash_flow_financial_group = self.create_cash_flow_financial_section()
        right_column.addWidget(cash_flow_financial_group)

        # Add columns to main layout
        columns_layout.addLayout(left_column)
        columns_layout.addLayout(right_column)
        main_layout.addLayout(columns_layout)

        # Load Data button (bottom-right)
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        self.load_button = StyledButton("Load Data", "function")
        self.load_button.clicked.connect(self.accept)
        button_layout.addWidget(self.load_button)
        main_layout.addLayout(button_layout)



        self.royalty.editingFinished.connect(self.calculate_net_price)
        self.working_interest.editingFinished.connect(self.calculate_net_price)
        self.oil_price.editingFinished.connect(self.calculate_net_price)
        self.gas_price.editingFinished.connect(self.calculate_net_price)
        self.oil_price_dif.editingFinished.connect(self.calculate_net_price)
        self.gas_price_dif.editingFinished.connect(self.calculate_net_price)
        self.tax_rate.editingFinished.connect(self.calculate_net_price)

        # Initial calculation
        self.calculate_net_price()


    def create_decline_curve_section(self):
        """Create Decline Curve Parameters section inside a GroupBox with proper alignment"""
        group_box = QGroupBox("Decline Curve Parameters")
        group_layout = QVBoxLayout()
        # Minimal margins and spacing
        group_layout.setContentsMargins(0, 0, 0, 0)
        group_layout.setSpacing(5)
    
        self.labels = [
            "Iterate",
            "Production Type",
            "Curve Type",
            "B Factor Gas",
            "Min Decline Gas",
            "B Factor Oil",
            "Min Decline Oil"
        ]
        StyledDropdown.calculate_label_width(self.labels)
    
        def create_dropdown(label, items=None):
            dropdown = StyledDropdown(label)
            if items:
                dropdown.addItems(items)
            return dropdown

        def create_input(label, default_value="", validator=None):
            # Pass the validator directly to StyledInputBox
            input_box = StyledInputBox(label, default_value, validator)
            input_box.label.setFixedWidth(StyledDropdown.label_width) 
            return input_box

        # Iteration Options
        self.iterate_di_dropdown = create_dropdown("Iterate", ["True", "False"])
        group_layout.addWidget(self.iterate_di_dropdown, alignment=Qt.AlignTop)
    
        # Graph Options
        self.option1_dropdown = create_dropdown("Production Type", ["Both", "Oil", "Gas"])
        self.option2_dropdown = create_dropdown("Curve Type", ["Exponential", "Normal"])
        group_layout.addWidget(self.option1_dropdown)
        group_layout.addWidget(self.option2_dropdown)
    
        # Validators
        double_validator = QDoubleValidator()
        percent_validator = QDoubleValidator(0.0, 100.0, 2)
    
        # Decline Curve Inputs
        self.gas_b_factor_input = create_input("B Factor Gas", ".6", double_validator)
        self.min_dec_gas = create_input("Min Decline Gas", "6.00", percent_validator)
        self.oil_b_factor_input = create_input("B Factor Oil", ".6", double_validator)
        self.min_dec_oil = create_input("Min Decline Oil", "6.00", percent_validator)
    
        group_layout.addWidget(self.gas_b_factor_input)
        group_layout.addWidget(self.min_dec_gas)
        group_layout.addWidget(self.oil_b_factor_input)
        group_layout.addWidget(self.min_dec_oil)
    
        # Push everything to the top
        group_layout.addStretch(1)
        group_box.setLayout(group_layout)
        return group_box

    def create_cash_flow_financial_section(self):
        """Create Cash Flow Parameters section inside a GroupBox with proper alignment"""
        group_box = QGroupBox("Cash Flow Parameters")
        group_layout = QVBoxLayout()
        # Minimal margins and spacing
        group_layout.setContentsMargins(0, 0, 0, 0)
        group_layout.setSpacing(5)

        # Add labels for width calculation
        self.labels = [
            "Forecast Limit",
            "Economic Limit Date",
            "Oil Price $",
            "Gas Price $",
            "Oil Differential BBL $",
            "Gas Differential MCF $",
            "Working Interest %",
            "Royalty Interest %",
            "Revenue Discount %",
            "Total Rate %",
            "Operating Cost Monthly",
            "Total Capex",
            "Net Oil Price $",
            "Net Gas Price $"
        ]
        StyledDropdown.calculate_label_width(self.labels)

        def create_dropdown(label, items=None):
            dropdown = StyledDropdown(label)
            if items:
                dropdown.addItems(items)
            return dropdown

        def create_input(label, default_value="", validator=None):
            input_box = StyledInputBox(label, default_value, validator)
            input_box.label.setFixedWidth(StyledDropdown.label_width)
            return input_box

        # Forecast Limit Dropdown
        self.end_forcast_type = create_dropdown("Forecast Limit", ["Net Dollars", "End Date", "GOR"])
        group_layout.addWidget(self.end_forcast_type)

        # Economic Limit Date
        self.ecl_date = StyledDateSelector("Economic Limit Date", default_date=QDate.currentDate().addYears(10))
        self.ecl_date.setEnabled(False)
        self.ecl_date.label.setFixedWidth(StyledDropdown.label_width)
        group_layout.addWidget(self.ecl_date)

        # Connect forecast type to enable/disable economic limit date
        self.end_forcast_type.combo.currentIndexChanged.connect(self.on_forcast_option_changed)

        # Validators
        double_validator = QDoubleValidator()
        percent_validator = QDoubleValidator(0.0, 100.0, 2)

        # Pricing Inputs
        self.oil_price = create_input("Oil Price $", "70", double_validator)
        self.gas_price = create_input("Gas Price $", "2.5", double_validator)
        self.oil_price_dif = create_input("Oil Differential BBL $", "2.5", double_validator)
        self.gas_price_dif = create_input("Gas Differential MCF $", ".5", double_validator)

        group_layout.addWidget(self.oil_price)
        group_layout.addWidget(self.gas_price)
        group_layout.addWidget(self.oil_price_dif)
        group_layout.addWidget(self.gas_price_dif)

        # Percentage Inputs
        self.working_interest = create_input("Working Interest %", "100", percent_validator)
        self.royalty = create_input("Royalty Interest %", "12.5", percent_validator)
        self.discount_rate = create_input("Revenue Discount %", "12.5", percent_validator)
        self.tax_rate = create_input("Total Rate %", "7", percent_validator)

        group_layout.addWidget(self.working_interest)
        group_layout.addWidget(self.royalty)
        group_layout.addWidget(self.discount_rate)
        group_layout.addWidget(self.tax_rate)

        # Cost Parameters
        self.operating_expenditures = create_input("Operating Cost Monthly", "10000", double_validator)
        self.capital_expenditures = create_input("Total Capex", "10000000", double_validator)

        group_layout.addWidget(self.operating_expenditures)
        group_layout.addWidget(self.capital_expenditures)

        # Net Price Calculation (Results)
        self.net_price_oil = create_input("Net Oil Price $", "0.0", double_validator)
        self.net_price_gas = create_input("Net Gas Price $", "0.0", double_validator)

        # Disable editing since these are calculated fields
        self.net_price_oil.setEnabled(False)
        self.net_price_gas.setEnabled(False)

        group_layout.addWidget(self.net_price_oil)
        group_layout.addWidget(self.net_price_gas)

        # Push everything to the top
        group_layout.addStretch(1)
        group_box.setLayout(group_layout)
        return group_box





    def on_forcast_option_changed(self, index):
        """Enable/disable economic limit date based on forecast type"""
        self.ecl_date.setEnabled(index == 1)

    def accept(self):
        """Collect and return dialog parameters"""
        try:
            self.properties = {
                'iterate_di': self.iterate_di_dropdown.currentText(),
                'production_type': self.option1_dropdown.currentText(),
                'curve_type': self.option2_dropdown.currentText(),
                'gas_b_factor': float(self.gas_b_factor_input.text()),
                'min_dec_gas': float(self.min_dec_gas.text()),
                'oil_b_factor': float(self.oil_b_factor_input.text()),
                'min_dec_oil': float(self.min_dec_oil.text()),
                'economic_limit_type': self.end_forcast_type.currentText(),
                'economic_limit_date': self.ecl_date.dateString(),  # Use dateString() method
                'oil_price': float(self.oil_price.text()),
                'gas_price': float(self.gas_price.text()),
                'oil_price_dif': float(self.oil_price_dif.text()),
                'gas_price_dif': float(self.gas_price_dif.text()),
                'working_interest': float(self.working_interest.text()),
                'royalty': float(self.royalty.text()),
                'discount_rate': float(self.discount_rate.text()),
                'tax_rate': float(self.tax_rate.text()),
                'operating_expenditures': float(self.operating_expenditures.text()),
                'capital_expenditures': float(self.capital_expenditures.text()),
                'ecl_date': self.ecl_date.date().toString("yyyy-MM-dd"),  # Use date() method
                'net_price_oil': float(self.net_price_oil.text()),
                'net_price_gas': float(self.net_price_gas.text())
            }
            super().accept()
        except ValueError as e:
            print(f"Error processing input: {e}")

    def calculate_net_price(self):
        """Calculate Net Price for Oil & Gas based on financial parameters."""
        try:
            royalty = float(self.royalty.text()) / 100  # Convert percentage to decimal
            working_interest = float(self.working_interest.text()) / 100
            oil_price = float(self.oil_price.text())
            gas_price = float(self.gas_price.text())
            oil_price_dif = float(self.oil_price_dif.text())
            gas_price_dif = float(self.gas_price_dif.text())
            tax_rate = float(self.tax_rate.text()) / 100  # Convert percentage to decimal

            # Calculate Net Revenue Interest (NRI)
            nri = working_interest * (1 - royalty)

            # Calculate Net Price
            net_price_oil = nri * (oil_price - oil_price_dif) * (1 - tax_rate) * (1 - royalty)
            net_price_gas = nri * (gas_price - gas_price_dif) * (1 - tax_rate) * (1 - royalty)

            # Update UI
            self.net_price_oil.setText(f"{net_price_oil:.2f}")
            self.net_price_gas.setText(f"{net_price_gas:.2f}")
        except ValueError:
            pass  # Ignore errors from invalid input


 


if __name__ == "__main__":
    app = QApplication(sys.argv)
    dialog = DefaultProperties()
    dialog.exec_()
    sys.exit(app.exec_())
