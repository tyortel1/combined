from PySide6.QtCore import QObject
from PySide6.QtCore import Signal
import plotly.offline as py_offline
import plotly.graph_objs as go
from PySide6.QtWidgets import QMessageBox
import pandas as pd

class Plotting(QObject):

    rightClicked = Signal(dict, dict)

    def __init__(self):
        super().__init__()


    def generate_plot_html(self, uwi_prod_rates_all, current_uwi, data_type, distribution_type, uwi_model_data):


        if uwi_prod_rates_all.empty:
            html_content = "<h1>No data to display.</h1>"
        else:
            if data_type == "Decline Curve":
                self.generate_decline_curve(uwi_prod_rates_all, current_uwi, distribution_type)

            elif data_type == "Cash Flow":
                self.cash_flow(uwi_prod_rates_all, current_uwi, distribution_type, uwi_model_data)

     
    def generate_decline_curve(self, uwi_prod_rates_all, current_uwi, distribution_type):

        if distribution_type == "Normal":
            mode = 'lines'
            yaxis_type = 'linear'
        else:  # Exponential
            mode = 'lines+markers'
            yaxis_type = 'log'


            
        if uwi_prod_rates_all.empty:
            html_content = "<h1>No data to display.</h1>"
        else:
            data_column = ['oil_volume', 'gas_volume']
  


        traces = []
        if isinstance(data_column, list):
            for column in data_column:
                trace = go.Scatter(x=uwi_prod_rates_all['date'], y=uwi_prod_rates_all[column], mode=mode, name=column.replace('_', ' ').title())
                traces.append(trace)
        else:
            trace = go.Scatter(x=uwi_prod_rates_all['date'], y=uwi_prod_rates_all[data_column], mode=mode, name=data_column.replace('_', ' ').title())
            traces.append(trace)

        # Plot production rates if available
        if 'q_oil' in uwi_prod_rates_all.columns:
            trace_oil_rate = go.Scatter(x=uwi_prod_rates_all['date'], y=uwi_prod_rates_all['q_oil'], mode='lines', name='Oil Production Rate')
            traces.append(trace_oil_rate)
        if 'q_gas' in uwi_prod_rates_all.columns:
            trace_gas_rate = go.Scatter(x=uwi_prod_rates_all['date'], y=uwi_prod_rates_all['q_gas'], mode='lines', name='Gas Production Rate')
            traces.append(trace_gas_rate)

        layout = go.Layout(title=f'Production Volumes Over Time - uwi: {current_uwi}', xaxis=dict(title='Date'), yaxis=dict(title='Volume', type=yaxis_type))
        fig = go.Figure(data=traces, layout=layout)
        # Generate HTML content
        html_content = py_offline.plot(fig, include_plotlyjs='cdn', output_type='div')
        
    # Update the UI element directly
        self.html_content = html_content
        return html_content






    def cash_flow(self, uwi_prod_rates_all, current_uwi, distribution_type, uwi_model_data):
        # Convert dates to pandas datetime format for easy manipulation
        uwi_prod_rates_all['date'] = pd.to_datetime(uwi_prod_rates_all['date'])
    
        # Group data by year and sum the values
        annual_data = uwi_prod_rates_all.groupby(uwi_prod_rates_all['date'].dt.year).sum()
        print("Annual data after grouping and summing:", annual_data)
        annual_dates = annual_data.index.tolist()  # Get the list of years

        # Retrieve CapEx and OpEx from model data
        capex = -float(uwi_model_data['capital_expenditures'])
        print("CapEx value:", capex)
        opex_value = -float(uwi_model_data['operating_expenditures'])
        print("OpEx value:", opex_value)
        
        # Extract total and discounted revenue values from the grouped data
        total_revenue_values = [float(annual_data['total_revenue'].loc[year]) for year in annual_dates]
        discounted_revenue_values = [float(annual_data['discounted_revenue'].loc[year]) for year in annual_dates]
        
        # Debug: Print revenue values to ensure correctness
        print("Total Revenue values:", total_revenue_values)
        print("Discounted Revenue values:", discounted_revenue_values)

        # Calculate net cash flow for each year
        net_cash_flow = []
        discounted_net_cash_flow = []
        accumulated_cash_flow = capex  # Start with CapEx as the initial value
        accumulated_discounted_cash_flow = capex  # Start with CapEx as the initial value for discounted cash flow
        for i in range(len(annual_dates)):
            if i == 0:
                # For the first year, include CapEx, OpEx, and total revenue
                net_cash_flow.append(accumulated_cash_flow + opex_value + total_revenue_values[i])
                discounted_net_cash_flow.append(accumulated_discounted_cash_flow + opex_value + discounted_revenue_values[i])
                accumulated_cash_flow = net_cash_flow[-1]
                accumulated_discounted_cash_flow = discounted_net_cash_flow[-1]
            else:
                # For subsequent years, calculate based on OpEx and total revenue
                net_cash_flow.append(accumulated_cash_flow + opex_value + total_revenue_values[i])
                discounted_net_cash_flow.append(accumulated_discounted_cash_flow + opex_value + discounted_revenue_values[i])
                accumulated_cash_flow = net_cash_flow[-1]
                accumulated_discounted_cash_flow = discounted_net_cash_flow[-1]
        
        # Debug: Print net cash flow values to ensure correctness
        print("Net Cash Flow values:", net_cash_flow)
        print("Discounted Net Cash Flow values:", discounted_net_cash_flow)

        # Separate positive and negative net cash flow values
        net_cash_flow_positive = [x if x >= 0 else 0 for x in net_cash_flow]
        net_cash_flow_negative = [x if x < 0 else 0 for x in net_cash_flow]

        # Separate positive and negative discounted net cash flow values
        discounted_net_cash_flow_positive = [x if x >= 0 else 0 for x in discounted_net_cash_flow]
        discounted_net_cash_flow_negative = [x if x < 0 else 0 for x in discounted_net_cash_flow]

        # Create traces for the graph
        trace_capex = go.Bar(
            x=[annual_dates[0]],
            y=[capex],
            name='CapEx',
            marker=dict(color='red')
        )

        trace_opex = go.Bar(
            x=annual_dates,
            y=[opex_value] * len(annual_dates),
            name='OpEx',
            marker=dict(color='orange')
        )

        trace_total_revenue = go.Bar(
            x=annual_dates,
            y=total_revenue_values,
            name='Total Revenue',
            marker=dict(color='blue')
        )

        trace_discounted_revenue = go.Bar(
            x=annual_dates,
            y=discounted_revenue_values,
            name='Discounted Revenue',
            marker=dict(color='purple')
        )

        trace_net_positive = go.Bar(
            x=annual_dates,
            y=net_cash_flow_positive,
            name='Net Cash Flow (Positive)',
            marker=dict(color='green')
        )

        trace_net_negative = go.Bar(
            x=annual_dates,
            y=net_cash_flow_negative,
            name='Net Cash Flow (Negative)',
            marker=dict(color='red')
        )

        trace_discounted_net_positive = go.Bar(
            x=annual_dates,
            y=discounted_net_cash_flow_positive,
            name='Discounted Net Cash Flow (Positive)',
            marker=dict(color='lightgreen')
        )

        trace_discounted_net_negative = go.Bar(
            x=annual_dates,
            y=discounted_net_cash_flow_negative,
            name='Discounted Net Cash Flow (Negative)',
            marker=dict(color='darkred')
        )

        # Set up the layout
        layout = go.Layout(
            title=f'Annual Cash Flow - uwi: {current_uwi}',
            xaxis=dict(title='Year', type='category'),  # Use category to treat years as discrete intervals
            yaxis=dict(title='Cash Flow ($)', zeroline=True),
            barmode='overlay'  # Set barmode to relative
        )

        fig = go.Figure(data=[trace_capex, trace_opex, trace_net_positive, trace_net_negative, trace_discounted_net_positive, trace_discounted_net_negative, trace_total_revenue, trace_discounted_revenue], layout=layout)
        html_content = py_offline.plot(fig, include_plotlyjs='cdn', output_type='div')
        self.html_content = html_content

