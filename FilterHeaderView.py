from PySide2.QtWidgets import QHeaderView, QComboBox

class FilterHeaderView(QHeaderView):
    def __init__(self, orientation, parent=None):
        super(FilterHeaderView, self).__init__(orientation, parent)
        self.filters = {}

    def add_filter(self, filter_widget, section):
        self.filters[section] = filter_widget
        self.setSectionResizeMode(section, QHeaderView.Stretch)
        self.setFixedHeight(30)  # Adjust header height as needed
        self.setStyleSheet("QHeaderView::section { background-color: #f0f0f0; }")  # Example header style
        self.setFilterWidgets()

    def setFilterWidgets(self):
        for section, filter_widget in self.filters.items():
            filter_widget.setParent(self)
            filter_widget.setFixedWidth(100)  # Adjust width as needed
            self.setSectionResizeMode(section, QHeaderView.Fixed)
            self.setSectionResizeMode(section, QHeaderView.Stretch)
