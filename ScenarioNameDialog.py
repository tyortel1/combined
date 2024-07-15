from PyQt5.QtWidgets import QDialog, QLabel, QLineEdit, QVBoxLayout, QHBoxLayout, QPushButton, QMessageBox, QCheckBox

class ScenarioNameDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Scenario Name")
        self.setGeometry(100, 100, 300, 150)
        
        main_layout = QVBoxLayout()

        # Scenario Name Input
        scenario_name_layout = QHBoxLayout()
        self.scenario_name_label = QLabel("Scenario Name:")
        self.scenario_name_input = QLineEdit()
        scenario_name_layout.addWidget(self.scenario_name_label)
        scenario_name_layout.addWidget(self.scenario_name_input)
        main_layout.addLayout(scenario_name_layout)


        # Buttons
        buttons_layout = QHBoxLayout()
        self.add_button = QPushButton("Add")
        self.add_button.clicked.connect(self.accept)
        buttons_layout.addWidget(self.add_button)

        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        buttons_layout.addWidget(self.cancel_button)

        main_layout.addLayout(buttons_layout)
        self.setLayout(main_layout)

    def get_scenario_name(self):
        return self.scenario_name_input.text()
