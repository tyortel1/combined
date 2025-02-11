import sys
import pandas as pd
import plotly.graph_objs as go
import plotly.offline as py_offline
from PySide6.QtWidgets import QApplication, QVBoxLayout,QCalendarWidget, QDialog, QTableWidget, QTableWidgetItem, QPushButton, QFileDialog, QGridLayout, QComboBox, QCheckBox, QLabel, QLineEdit, QHBoxLayout, QSizePolicy, QWidget
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtCore import QSignalBlocker, QDate

import openpyxl

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
        
        # Add Export and Table buttons AFTER other controls
        self.export_button = QPushButton("Export to Excel")
        controls_layout.addWidget(self.export_button)
        
        self.show_table_button = QPushButton("Show Data Table")
        controls_layout.addWidget(self.show_table_button)
        
        # Connect buttons
        self.export_button.clicked.connect(self.export_to_excel)
        self.show_table_button.clicked.connect(self.show_table)
        
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
# Add these new methods to your class:
    def export_to_excel(self):
        try:
            # Open file dialog for saving
            file_name, _ = QFileDialog.getSaveFileName(
                self, "Save Excel File", "", "Excel Files (*.xlsx)"
            )
            
            if file_name:
                # If no extension is provided, add .xlsx
                if not file_name.endswith('.xlsx'):
                    file_name += '.xlsx'
                
                # Export DataFrame to Excel
                self.cash_flow_df.to_excel(file_name, index=False)
                print(f"Data exported successfully to {file_name}")
        except Exception as e:
            print(f"Error exporting to Excel: {str(e)}")

    def show_table(self):
        # Create table window
        self.table_window = QDialog(self)
        self.table_window.setWindowTitle("Cash Flow Data")
        self.table_window.setGeometry(200, 200, 1000, 600)
        
        # Create table widget
        table = QTableWidget()
        layout = QVBoxLayout()
        layout.addWidget(table)
        self.table_window.setLayout(layout)
        
        # Set up table
        df = self.cash_flow_df
        table.setRowCount(len(df))
        table.setColumnCount(len(df.columns))
        table.setHorizontalHeaderLabels(df.columns)
        
        # Populate table
        for i in range(len(df)):
            for j in range(len(df.columns)):
                value = str(df.iloc[i, j])
                if df.columns[j] in ['profit', 'discounted_profit', 'sum_revenue', 
                                   'sum_discounted_revenue', 'capex_sum', 'opex_sum']:
                    # Format financial numbers
                    try:
                        value = f"${float(value):,.2f}"
                    except ValueError:
                        pass
                item = QTableWidgetItem(value)
                table.setItem(i, j, item)
        
        # Resize columns to content
        table.resizeColumnsToContents()
        
        # Show the window
        self.table_window.show()
    
    def apply_discount_rate(self):
        try:
            discount_rate = float(self.discount_rate_input.text()) / 100
        
            # Recalculate discounted revenue
            self.cash_flow_df['discounted_revenue'] = self.cash_flow_df['total_revenue'] / (1 + discount_rate)
        
            # Recalculate cumulative discounted revenue
            self.cash_flow_df['sum_discounted_revenue'] = self.cash_flow_df['discounted_revenue'].cumsum()
        
            # Recalculate discounted profit using the new discounted revenue
            self.cash_flow_df['discounted_profit'] = (self.cash_flow_df['sum_discounted_revenue'] + 
                                                     self.cash_flow_df['cumsum_opex'] + 
                                                     self.cash_flow_df['cumsum_capex'])
        
            # Update the plot
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
        
        # Ensure 'UWI' is the index of the DataFrame
        if 'UWI' in model_data.columns:
            model_data.set_index('UWI', inplace=True)

        # Ensure the indexes are strings
        combined_data.index = combined_data.index.astype(str)
        model_data.index = model_data.index.astype(str)
        date_ranges['UWI'] = date_ranges['UWI'].astype(str)
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

         # Loop over each UWI to create entries for CapEx and OpEx
        for _, row in date_ranges.iterrows():
            UWI = row['UWI']
            first_date = pd.to_datetime(row['first_date'], errors='coerce')
            last_date = pd.to_datetime(row['last_date'], errors='coerce')

            if pd.isnull(first_date) or pd.isnull(last_date):
                print(f"Invalid date range for UWI {UWI}. Skipping...")
                continue

            if UWI in model_data.index:
                print(f"Raw CapEx value for {UWI}:", model_data.loc[UWI, 'capital_expenditures'])
                capex = -float(model_data.loc[UWI, 'capital_expenditures'])
                opex_value = -float(model_data.loc[UWI, 'operating_expenditures'])

                # Add CapEx entry for the first date
                entries.append({
                    'UWI': UWI,
                    'date': first_date,
                    'type': 'CapEx',
                    'amount': capex
                })

                # Add OpEx entries for every month between the start and end date
                current_date = first_date
                while current_date <= last_date:
                    entries.append({
                        'UWI': UWI,
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




        revenue_df = pd.DataFrame({
            'date': dates,
            'total_revenue': total_revenue_values,
            'discounted_revenue': discounted_revenue_values
        })

        # First create cash_flow_df
        self.cash_flow_df = revenue_df.merge(opex_sum, on='date', how='left').merge(capex_sum, on='date', how='left')
        self.cash_flow_df.fillna(0, inplace=True)
        self.cash_flow_df.rename(columns={'amount_x': 'opex_sum', 'amount_y': 'capex_sum'}, inplace=True)

        # Now we can print because cash_flow_df exists
        print("\nBefore calculations:")
        print("Sample of total_revenue:", self.cash_flow_df['total_revenue'].head())
        print("Sample of opex_sum:", self.cash_flow_df['opex_sum'].head())
        print("Sample of capex_sum:", self.cash_flow_df['capex_sum'].head())

        # Calculate cumulative sums
        self.cash_flow_df['sum_revenue'] = self.cash_flow_df['total_revenue'].cumsum()
        self.cash_flow_df['sum_discounted_revenue'] = self.cash_flow_df['discounted_revenue'].cumsum()
        self.cash_flow_df['cumsum_opex'] = self.cash_flow_df['opex_sum'].cumsum()
        self.cash_flow_df['cumsum_capex'] = self.cash_flow_df['capex_sum'].cumsum()

        print("\nChecking values before profit calculation:")
        print("\nRevenue values:")
        print(self.cash_flow_df[['date', 'total_revenue', 'sum_revenue']].head())
        print("\nOpEx values:")
        print(self.cash_flow_df[['date', 'opex_sum', 'cumsum_opex']].head())
        print("\nCapEx values:")
        print(self.cash_flow_df[['date', 'capex_sum', 'cumsum_capex']].head())

        # Calculate profit and discounted profit
        self.cash_flow_df['profit'] = self.cash_flow_df['sum_revenue'] + self.cash_flow_df['cumsum_opex'] + self.cash_flow_df['cumsum_capex']
        self.cash_flow_df['discounted_profit'] = self.cash_flow_df['sum_discounted_revenue'] + self.cash_flow_df['cumsum_opex'] + self.cash_flow_df['cumsum_capex']
        print("\nFinal profit calculations:")
        print(self.cash_flow_df[['date', 'sum_revenue', 'cumsum_opex', 'cumsum_capex', 'profit']].head())

        self.cash_flow_df['date'] = self.cash_flow_df['date'].dt.strftime('%Y-%m')

 
        print("\nAfter cumulative sums:")
        print("Sample of sum_revenue:", self.cash_flow_df['sum_revenue'].head())
        print("Sample of cumsum_opex:", self.cash_flow_df['cumsum_opex'].head())
        print("Sample of cumsum_capex:", self.cash_flow_df['cumsum_capex'].head())
    
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
