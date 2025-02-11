from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QLineEdit, QPushButton, QHBoxLayout, QComboBox, QListWidget, QListWidgetItem, QFormLayout
from PySide6.QtCore import Qt

class SaveDeclineCurveDialog(QDialog):
    def __init__(self, parent=None, UWIs=None, from_context_menu=False):
        super().__init__(parent)
        if UWIs is not None:
            self.UWIs = [str(UWI) for UWI in UWIs]
        self.from_context_menu = from_context_menu
        self.setWindowTitle("Save Decline Curve Parameters")

        self.layout = QVBoxLayout()

        self.option_label = QLabel("Select an option:")
        self.layout.addWidget(self.option_label)

        self.options = QComboBox()
        self.options.addItems(["Current Well", "Average", "Manual"])
        if self.from_context_menu:
            self.options.setCurrentText("Average")
            self.options.setEnabled(False)
        self.layout.addWidget(self.options)
        
        self.name_label = QLabel("Enter a name for the decline curve parameters:")
        self.layout.addWidget(self.name_label)

        self.name_input = QLineEdit()
        self.layout.addWidget(self.name_input)
        
        # Layouts for Average and Manual options
        self.average_layout = QVBoxLayout()
        self.manual_layout = QFormLayout()
        
        # Average Option
        self.UWI_list_label = QLabel("Select UWIs to average:")
        self.average_layout.addWidget(self.UWI_list_label)

        self.UWI_list = QListWidget()
        if self.UWIs:
            for UWI in self.UWIs:
                item = QListWidgetItem(UWI)
                item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
                item.setCheckState(Qt.Checked if self.from_context_menu else Qt.Unchecked)
                self.UWI_list.addItem(item)
        self.average_layout.addWidget(self.UWI_list)
        
        # Rest of your existing dialog code...
        
        # Manual Option
        self.economic_limit_type = QLineEdit()
        self.gas_b_factor = QLineEdit()
        self.min_dec_gas = QLineEdit()
        self.oil_b_factor = QLineEdit()
        self.min_dec_oil = QLineEdit()
        self.economic_limit_date = QLineEdit()
        self.oil_price = QLineEdit()
        self.gas_price = QLineEdit()
        self.oil_price_dif = QLineEdit()
        self.gas_price_dif = QLineEdit()
        self.discount_rate = QLineEdit()
        self.tax_rate = QLineEdit()
        self.capital_expenditures = QLineEdit()
        self.operating_expenditures = QLineEdit()
        self.net_price_oil = QLineEdit()
        self.net_price_gas = QLineEdit()

        self.manual_layout.addRow("Economic Limit Type:", self.economic_limit_type)
        self.manual_layout.addRow("B Factor Gas:", self.gas_b_factor)
        self.manual_layout.addRow("Min Dec Gas:", self.min_dec_gas)
        self.manual_layout.addRow("B Factor Oil:", self.oil_b_factor)
        self.manual_layout.addRow("Min Dec Oil:", self.min_dec_oil)
        self.manual_layout.addRow("Economic Limit Date:", self.economic_limit_date)
        self.manual_layout.addRow("Oil Price:", self.oil_price)
        self.manual_layout.addRow("Gas Price:", self.gas_price)
        self.manual_layout.addRow("Oil Price Dif:", self.oil_price_dif)
        self.manual_layout.addRow("Gas Price Dif:", self.gas_price_dif)
        self.manual_layout.addRow("Discount Rate:", self.discount_rate)
        self.manual_layout.addRow("Tax Rate:", self.tax_rate)
        self.manual_layout.addRow("Capital Expenditures:", self.capital_expenditures)
        self.manual_layout.addRow("Operating Expenditures:", self.operating_expenditures)
        self.manual_layout.addRow("Net Price Oil:", self.net_price_oil)
        self.manual_layout.addRow("Net Price Gas:", self.net_price_gas)

        # Add Average and Manual layouts but hide them initially
        self.layout.addLayout(self.average_layout)
        self.layout.addLayout(self.manual_layout)
        self.toggle_layout(self.average_layout, False)
        self.toggle_layout(self.manual_layout, False)

        self.button_layout = QHBoxLayout()
        self.save_button = QPushButton("Save")
        self.cancel_button = QPushButton("Cancel")

        self.button_layout.addWidget(self.save_button)
        self.button_layout.addWidget(self.cancel_button)

        self.layout.addLayout(self.button_layout)
        self.setLayout(self.layout)

        self.options.currentTextChanged.connect(self.on_option_change)
        self.save_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)

    def toggle_layout(self, layout, show):
        for i in range(layout.count()):
            widget = layout.itemAt(i).widget()
            if widget:
                widget.setVisible(show)

    def on_option_change(self, text):
        if text == "Current Well":
            self.toggle_layout(self.average_layout, False)
            self.toggle_layout(self.manual_layout, False)
        elif text == "Average":
            self.toggle_layout(self.average_layout, True)
            self.toggle_layout(self.manual_layout, False)
        elif text == "Manual":
            self.toggle_layout(self.average_layout, False)
            self.toggle_layout(self.manual_layout, True)

    def get_curve_name(self):
        return self.name_input.text()

    def get_selected_option(self):
        return self.options.currentText()

    def get_selected_UWIs(self):
        selected_UWIs = []
        for index in range(self.UWI_list.count()):
            item = self.UWI_list.item(index)
            if item.checkState() == Qt.Checked:
                selected_UWIs.append(item.text())
        return selected_UWIs

    def get_manual_data(self):
        return {
            'economic_limit_type': self.economic_limit_type.text(),
            'gas_b_factor': float(self.gas_b_factor.text() or 0),
            'min_dec_gas': float(self.min_dec_gas.text() or 0),
            'oil_b_factor': float(self.oil_b_factor.text() or 0),
            'min_dec_oil': float(self.min_dec_oil.text() or 0),
            'economic_limit_date': self.economic_limit_date.text(),
            'oil_price': float(self.oil_price.text() or 0),
            'gas_price': float(self.gas_price.text() or 0),
            'oil_price_dif': float(self.oil_price_dif.text() or 0),
            'gas_price_dif': float(self.gas_price_dif.text() or 0),
            'discount_rate': float(self.discount_rate.text() or 0),
            'tax_rate': float(self.tax_rate.text() or 0),
            'capital_expenditures': float(self.capital_expenditures.text() or 0),
            'operating_expenditures': float(self.operating_expenditures.text() or 0),
            'net_price_oil': float(self.net_price_oil.text() or 0),
            'net_price_gas': float(self.net_price_gas.text() or 0),
        }
