import plotly.offline as py_offline
import plotly.graph_objs as go

def plot_totals(date_labels, column_totals):
    trace = go.Scatter(x=date_labels, y=column_totals, mode='lines+markers')
    layout = go.Layout(title='Total vs Date', xaxis={'title': 'Date'}, yaxis={'title': 'Total'})

    fig = go.Figure(data=[trace], layout=layout)
    html_content = py_offline.plot(fig, include_plotlyjs='cdn', output_type='div')

    return html_content
