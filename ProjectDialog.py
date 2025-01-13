from PySide6.QtWidgets import QDialog, QLabel, QLineEdit, QPushButton, QVBoxLayout, QHBoxLayout, QFileDialog

class ProjectDialog(QDialog):
    def __init__(self):
        super().__init__()

        self.project_name_input = QLineEdit()
        self.directory_input = QLineEdit()
        self.directory_button = QPushButton("Select Directory")
        self.ok_button = QPushButton("OK")

        layout = QVBoxLayout()
        layout.addWidget(QLabel("Project Name:"))
        layout.addWidget(self.project_name_input)
        layout.addWidget(QLabel("Directory:"))
        directory_layout = QHBoxLayout()
        directory_layout.addWidget(self.directory_input)
        directory_layout.addWidget(self.directory_button)
        layout.addLayout(directory_layout)
        layout.addWidget(self.ok_button)

        self.directory_button.clicked.connect(self.select_directory)

        self.ok_button.clicked.connect(self.accept)
        self.ok_button.setDefault(True)

        self.setLayout(layout)

    def select_directory(self):
        dialog = QFileDialog(self, 'Select Directory')
        dialog.setFileMode(QFileDialog.Directory)
        dialog.setGeometry(100, 100, 300, 200)  # You can try setting the geometry directly
        if dialog.exec_() == QDialog.Accepted:
            directory = dialog.selectedFiles()[0]
            self.directory_input.setText(directory)

