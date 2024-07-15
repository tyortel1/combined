import sys
import pandas as pd
import plotly.graph_objs as go
import plotly.offline as py_offline
from PyQt5.QtWidgets import QApplication, QVBoxLayout,QCalendarWidget, QDialog, QGridLayout, QComboBox, QCheckBox, QLabel, QLineEdit, QPushButton, QHBoxLayout, QSizePolicy, QWidget
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtCore import QSignalBlocker, QDate

class LaunchCombinedCashflow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Combined Cashflow")
        self.setGeometry(150, 150, 1200, 600)
        
        # Set up the main layout
        main_layout = QHBoxLayout()
        
        # Controls widget and layout on the left side
        controls_widget = QWidget()
        controls_widget.setFixedWidth(200)
        controls_layout = QVBoxLayout(controls_widget)
        controls_layout.setContentsMargins(0, 0, 0, 0)
        controls_layout.setSpacing(10)
        
        # Calendar for start date
        self.start_date_label = QLabel("Start Date:")
        controls_layout.addWidget(self.start_date_label)
        self.start_date_calendar = QCalendarWidget()
        controls_layout.addWidget(self.start_date_calendar)
        
        # Checkboxes for traces
        self.trace_checkboxes = {}
        
        traces = ['sum_revenue', 'sum_discounted_revenue', 'profit', 'discounted_profit', 'capex_sum', 'opex_sum']
        for trace in traces:
            self.trace_checkboxes[trace] = QCheckBox(trace)
            self.trace_checkboxes[trace].setChecked(True)
            controls_layout.addWidget(self.trace_checkboxes[trace])
        
        # Text box for discount rate
        self.discount_rate_label = QLabel("Discount Rate (%):")
        controls_layout.addWidget(self.discount_rate_label)
        self.discount_rate_input = QLineEdit()
        controls_layout.addWidget(self.discount_rate_input)
        
        # Button to apply discount rate
        self.apply_discount_button = QPushButton("Apply Discount Rate")
        controls_layout.addWidget(self.apply_discount_button)
        
        main_layout.addWidget(controls_widget)
        
        # Web view to display the plot
        self.web_view = QWebEngineView()
        self.web_view.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        main_layout.addWidget(self.web_view)
        
        self.setLayout(main_layout)
        
        # Connect signals and slots
        self.start_date_calendar.selectionChanged.connect(self.update_plot)
        self.apply_discount_button.clicked.connect(self.apply_discount_rate)
        for checkbox in self.trace_checkboxes.values():
            checkbox.toggled.connect(self.update_plot)
        
        # Sample data
        self.combined_data = pd.DataFrame()
        self.date_ranges = pd.DataFrame()
        self.model_data = pd.DataFrame()
        self.cash_flow_df = pd.DataFrame()
        
        self.plot_figure = None

    
    def apply_discount_rate(self):
        try:
            discount_rate = float(self.discount_rate_input.text()) / 100
            self.combined_data['discounted_revenue'] = self.combined_data['total_revenue'] / (1 + discount_rate)
            self.update_plot()
        except ValueError:
            print("Invalid discount rate entered.")
    
    def update_plot(self):
        selected_date = self.start_date_calendar.selectedDate()
        start_date = pd.Timestamp(selected_date.year(), selected_date.month(), selected_date.day())
        filtered_data = self.cash_flow_df[self.cash_flow_df['date'] >= start_date.strftime('%Y-%m')]

        traces = []
        if self.trace_checkboxes['sum_revenue'].isChecked():
            traces.append(go.Bar(x=filtered_data['date'], y=filtered_data['sum_revenue'], name='Cumulative Total Revenue', marker=dict(color='blue')))
        if self.trace_checkboxes['sum_discounted_revenue'].isChecked():
            traces.append(go.Bar(x=filtered_data['date'], y=filtered_data['sum_discounted_revenue'], name='Cumulative Discounted Revenue', marker=dict(color='lightblue')))
        if self.trace_checkboxes['profit'].isChecked():
            traces.append(go.Bar(x=filtered_data['date'], y=filtered_data['profit'], name='Profit', marker=dict(color='darkgreen')))
        if self.trace_checkboxes['discounted_profit'].isChecked():
            traces.append(go.Bar(x=filtered_data['date'], y=filtered_data['discounted_profit'], name='Discounted Profit', marker=dict(color='lightgreen')))
        if self.trace_checkboxes['capex_sum'].isChecked():
            traces.append(go.Bar(x=filtered_data['date'], y=filtered_data['capex_sum'], name='CapEx Sum', marker=dict(color='red')))
        if self.trace_checkboxes['opex_sum'].isChecked():
            traces.append(go.Bar(x=filtered_data['date'], y=filtered_data['opex_sum'], name='OpEx Sum', marker=dict(color='orange')))
        
        layout = go.Layout(
            title='Combined Cash Flow',
            xaxis=dict(title='Date', type='category'),
            yaxis=dict(title='Value ($)', zeroline=True),
            barmode='overlay'
        )
        
        self.plot_figure = go.Figure(data=traces, layout=layout)
        html_content = py_offline.plot(self.plot_figure, include_plotlyjs='cdn', output_type='div')
        self.web_view.setHtml(html_content)


    def display_cashflow(self, combined_data, date_ranges, model_data, frequency='M'):
        
        # Ensure 'uwi' is the index of the DataFrame
        if 'uwi' in model_data.columns:
            model_data.set_index('uwi', inplace=True)

        # Ensure the indexes are strings
        combined_data.index = combined_data.index.astype(str)
        model_data.index = model_data.index.astype(str)
        date_ranges['uwi'] = date_ranges['uwi'].astype(str)
        min_date = pd.to_datetime(date_ranges['first_date'].min(), errors='coerce')

        with QSignalBlocker(self.start_date_calendar):
            self.start_date_calendar.setSelectedDate(QDate(min_date.year, min_date.month, min_date.day))
        
        combined_data['date'] = pd.to_datetime(combined_data['date'], errors='coerce')

        # Drop rows with invalid dates
        combined_data.dropna(subset=['date'], inplace=True)

        # Group data by the desired frequency and sum the values
        aggregated_data = combined_data.groupby(pd.Grouper(key='date', freq=frequency)).sum()

        # Extract dates and revenue values
        dates = aggregated_data.index.tolist()
        total_revenue_values = [float(aggregated_data['total_revenue'].loc[date]) for date in dates]
        discounted_revenue_values = [float(aggregated_data['discounted_revenue'].loc[date]) for date in dates]

        # Create a DataFrame to store the entries
        entries = []

         # Loop over each uwi to create entries for CapEx and OpEx
        for _, row in date_ranges.iterrows():
            uwi = row['uwi']
            first_date = pd.to_datetime(row['first_date'], errors='coerce')
            last_date = pd.to_datetime(row['last_date'], errors='coerce')

            if pd.isnull(first_date) or pd.isnull(last_date):
                print(f"Invalid date range for uwi {uwi}. Skipping...")
                continue

            if uwi in model_data.index:
                capex = -float(model_data.loc[uwi, 'capital_expenditures'])
                opex_value = -float(model_data.loc[uwi, 'operating_expenditures'])

                # Add CapEx entry for the first date
                entries.append({
                    'uwi': uwi,
                    'date': first_date,
                    'type': 'CapEx',
                    'amount': capex
                })

                # Add OpEx entries for every month between the start and end date
                current_date = first_date
                while current_date <= last_date:
                    entries.append({
                        'uwi': uwi,
                        'date': current_date,
                        'type': 'OpEx',
                        'amount': opex_value
                    })
                    current_date += pd.DateOffset(months=1)

        # Convert entries to a DataFrame
        entries_df = pd.DataFrame(entries)

        opex_sum = entries_df[entries_df['type'] == 'OpEx'].groupby(pd.Grouper(key='date', freq=frequency))['amount'].sum().reset_index()
        capex_sum = entries_df[entries_df['type'] == 'CapEx'].groupby(pd.Grouper(key='date', freq=frequency))['amount'].sum().reset_index()

        # Print the summed OpEx and CapEx for debugging
        
        print("Summed OpEx:\n", opex_sum)
        print("Summed CapEx:\n", capex_sum)
# Merge revenue, OpEx, and CapEx data
        revenue_df = pd.DataFrame({
            'date': dates,
            'total_revenue': total_revenue_values,
            'discounted_revenue': discounted_revenue_values
        })

        self.cash_flow_df = revenue_df.merge(opex_sum, on='date', how='left').merge(capex_sum, on='date', how='left')
        self.cash_flow_df.fillna(0, inplace=True)
        self.cash_flow_df.rename(columns={'amount_x': 'opex_sum', 'amount_y': 'capex_sum'}, inplace=True)

        # Print the resulting table
        # Calculate cumulative sums for total and discounted revenues
        self.cash_flow_df['sum_revenue'] = self.cash_flow_df['total_revenue'].cumsum()
        self.cash_flow_df['sum_discounted_revenue'] = self.cash_flow_df['discounted_revenue'].cumsum()
        self.cash_flow_df['cumsum_opex'] = self.cash_flow_df['opex_sum'].cumsum()
        self.cash_flow_df['cumsum_capex'] = self.cash_flow_df['capex_sum'].cumsum()

        # Calculate profit and discounted profit
        self.cash_flow_df['profit'] = self.cash_flow_df['sum_revenue'] + self.cash_flow_df['cumsum_opex'] + self.cash_flow_df['cumsum_capex']
        self.cash_flow_df['discounted_profit'] = self.cash_flow_df['sum_discounted_revenue'] + self.cash_flow_df['cumsum_opex'] + self.cash_flow_df['cumsum_capex']
        self.cash_flow_df['date'] = self.cash_flow_df['date'].dt.strftime('%Y-%m')

 

    
        # Print the resulting table
        pd.set_option('display.max_rows', None)
        pd.set_option('display.max_columns', None)
        pd.set_option('display.width', 1000)
        pd.set_option('display.colheader_justify', 'center')
        pd.set_option('display.precision', 2)

        print(self.cash_flow_df)
        # Optionally, you can return this DataFrame for further use
# Create traces for the bar graph
        
        
        
        trace_sum_revenue = go.Bar(x=self.cash_flow_df['date'], y=self.cash_flow_df['sum_revenue'], name='Cumulative Total Revenue', marker=dict(color='blue'))
        trace_sum_discounted_revenue = go.Bar(x=self.cash_flow_df['date'], y=self.cash_flow_df['sum_discounted_revenue'], name='Cumulative Discounted Revenue', marker=dict(color='lightblue'))
        trace_profit = go.Bar(x=self.cash_flow_df['date'], y=self.cash_flow_df['profit'], name='Profit', marker=dict(color='darkgreen'))
        trace_discounted_profit = go.Bar(x=self.cash_flow_df['date'], y=self.cash_flow_df['discounted_profit'], name='Discounted Profit', marker=dict(color='lightgreen'))
        trace_capex_sum = go.Bar(x=self.cash_flow_df['date'], y=self.cash_flow_df['capex_sum'], name='CapEx Sum', marker=dict(color='red'))
        trace_opex_sum = go.Bar(x=self.cash_flow_df['date'], y=self.cash_flow_df['opex_sum'], name='OpEx Sum', marker=dict(color='orange'))

        # Set up the layout
        layout = go.Layout(
            title='Combined Cash Flow',
            xaxis=dict(title='Date', type='category'),
            yaxis=dict(title='Value ($)', zeroline=True),
            barmode='overlay'
        )

        # Create the figure
        fig = go.Figure(data=[
            
            trace_sum_revenue, trace_sum_discounted_revenue, trace_profit, trace_discounted_profit, trace_capex_sum, trace_opex_sum
        ], layout=layout)

        # Generate the HTML content
        html_content = py_offline.plot(fig, include_plotlyjs='cdn', output_type='div')

        self.web_view.setHtml(html_content)



if __name__ == "__main__":
    app = QApplication(sys.argv)
    cashflow_window = LaunchCombinedCashflow()
    cashflow_window.show()
    sys.exit(app.exec_())
