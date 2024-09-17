import os
import numpy as np
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import plotly.express as px
from datetime import datetime, timedelta
import re
import plotly.graph_objects as go
from ipywidgets import interact
import dash_bootstrap_components as dbc
from dash import dcc
from plotly.subplots import make_subplots
from dash.dependencies import Input, Output
from dash import Dash, html, dcc ,dash_table,dcc ,State
from dash.dash_table.Format import Group
import uvicorn
from waitress import serve
import dash
from pathlib import Path
#database imports
import psycopg2
import warnings
# Ignore all warnings
warnings.filterwarnings("ignore")
from dash import Dash, html
from flask import Flask, jsonify

# Create a Flask server instance
server = Flask(__name__)

# Define the health check endpoint
@server.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "ok"}), 200


#connect to database function
# Define your connection parameters
username = "iscs_ats"
password = "w2mrGcYWJLvxDfXgAhAZ1Q"
host = "fleet-fish-5790.7s5.aws-ap-south-1.cockroachlabs.cloud"
port = "26257"
database = "ats_iscs"
# Construct the connection string
database_url = f"postgresql://{username}:{password}@{host}:{port}/{database}"
def connect_to_postgresql(database_url):
    try:
        # Connect to the PostgreSQL database
        conn = psycopg2.connect(database_url)
        print("The database is connected")
        return conn
    except Exception as e:
        print("Error connecting to PostgreSQL:", e)
        return None

# Call the function to establish the connection
connection = connect_to_postgresql(database_url)
#data frame
if connection:
    try:
        # Create a cursor object
        cursor = connection.cursor()

        # Execute the SQL query
        cursor.execute("SELECT * FROM employee_work_hours")

        # Fetch all results
        results = cursor.fetchall()

        # Process the results (e.g., print them)
        # for row in results:
        #     print(row)
        column_names = [desc[0] for desc in cursor.description]

        # Convert the result into a DataFrame
        df = pd.DataFrame(results, columns=column_names)

    except Exception as e:
        print("Error executing query:", e)

    finally:
        # Close the cursor and connection
        cursor.close()
        connection.close()
        print("The connection is closed")

df1=df.copy()
df1['mean_intime'] = pd.to_datetime(df1['mean_intime'], format='%H:%M').dt.time
df1['mean_outtime'] = pd.to_datetime(df1['mean_outtime'], format='%H:%M').dt.time
df1['duration_in_office'] = pd.to_datetime(df1['duration_in_office'], format='%H:%M').dt.time
df1['working_hours_duration'] = pd.to_datetime(df1['working_hours_duration'], format='%H:%M').dt.time

# Initialize the Dash app
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP], suppress_callback_exceptions=True)
#the over all graph according to months in main page
def cal_meantime(month_name):
    df2 = df1[df1["month_name"] == month_name]
    df2 = df2.sort_values(by='mean_intime')
    
    custom_colorscale = [
        [0, 'lightgreen'],  
        [1, 'red']          
    ]
    df2['seconds_since_midnight'] = df2['mean_intime'].apply(lambda t: t.hour * 3600 + t.minute * 60 + t.second)
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=df2['employee_name'],
        y=df2['mean_intime'],
        marker=dict(
            color=df2['seconds_since_midnight'],  
            colorscale=custom_colorscale
        ),
        text=df2['mean_intime'].apply(lambda x: x.strftime('%H:%M:%S')),
        hoverinfo='text',  
        hovertemplate=(
            'Employee: %{x}<br>' +
            'Log IN Time: %{text}<br>'
        ),
        name='Log IN Time'
    ))
    fig.update_layout(
        title=f'Average Log IN Time by Employee for {month_name}',
        yaxis_title='Log IN Time',
        barmode='group',
        bargap=0.003,  
        bargroupgap=0.15,  
        autosize=True,  
        margin=dict(l=5, r=5, t=30, b=5),  
        width=1100,  
        height=600  
    )
  
    return fig
def cal_outtime(month_name):
    df2 = df1[df1["month_name"] == month_name]
    df2 = df2.sort_values(by='mean_outtime')
    custom_colorscale = [
        [0, 'lightgreen'],  
        [1, 'red']     
    ]
    df2['seconds_since_midnight'] = df2['mean_outtime'].apply(lambda t: t.hour * 3600 + t.minute * 60 + t.second)
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=df2['employee_name'],
        y=df2['mean_outtime'],
        marker=dict(
            color=df2['seconds_since_midnight'],
            colorscale="Inferno"
        ),
        text=df2['mean_outtime'].apply(lambda x: x.strftime('%H:%M:%S')),  
        hoverinfo='text',
        hovertemplate=(
            'Employee: %{x}<br>' +
            'OUT Time: %{text}<br>' 
        ),
        name='Log OUT Time'
    ))
    fig.update_layout(
        title=f'Average Log OUT Time by Employee for {month_name}',
        yaxis_title='Log OUT Time',
        barmode='group',
        bargap=0.003,
        bargroupgap=0.15,
        autosize=True,
        margin=dict(l=5, r=5, t=30, b=5),
        width=1100,
        height=650 
    )
  
    return fig
def Duration(month_name):
    df2 = df1.loc[df1["month_name"] == month_name]
    def seconds_to_time(seconds):
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        return f"{int(hours):02}:{int(minutes):02}"
    # Calculate seconds since midnight for each time column
    df2['duration_in_office_seconds'] = df2['duration_in_office'].apply(lambda t: t.hour * 3600 + t.minute * 60)
    df2['working_hours_duration_seconds'] = df2['working_hours_duration'].apply(lambda t: t.hour * 3600 + t.minute * 60)
    # Convert seconds to hours (if needed for visualization)
    df2['duration_in_office_hours'] = df2['duration_in_office_seconds'] / 3600
    df2['working_hours_duration_hours'] = df2['working_hours_duration_seconds'] / 3600
    # Format hours to time strings
    df2['duration_in_office_hourS'] = df2['duration_in_office_hours'].apply(lambda h: seconds_to_time(h * 3600))
    df2['working_hours_duration_hourS'] = df2['working_hours_duration_hours'].apply(lambda h: seconds_to_time(h * 3600))
    fig = go.Figure()
    # Add bars for 'duration_in_office_hours' (base layer)
    fig.add_trace(go.Bar(
        x=df2['employee_name'],
        y=df2['duration_in_office_hours'],
        name='Duration in Office',
        marker_color='lightseagreen',
        text=df2['duration_in_office_hourS'],
        textposition='outside'
    ))
    # Add bars for 'working_hours_duration_hours' (stacked on top)
    fig.add_trace(go.Bar(
        x=df2['employee_name'],
        y=df2['working_hours_duration_hours'],
        name='Working Hours',
        marker_color='indianred',
        text=df2['working_hours_duration_hourS'],
        textposition='inside'
    ))
    # Update layout for better visualization
    fig.update_layout(
        title=f'Duration in Office vs Working Hours for {month_name}',
        yaxis_title='Duration',
        barmode='overlay',  # Stack bars on top of each other
        bargap=0.15,  # Gap between bars
        bargroupgap=0.1,  # Gap between groups
        width=1100,
        height=500, 
        legend=dict(
            x=0.5,  # Position legend
            y=1.20,
            traceorder='normal',
            orientation='h',
            bgcolor='rgba(255, 255, 255, 0.8)',  # Semi-transparent background for legend
            bordercolor='LightGray',
            borderwidth=1
        ),
        font=dict(
            family='Arial, sans-serif',
            size=14,
            color='black'
        ),
        xaxis=dict(
        tickangle=-45,  # Rotate x-axis labels for better readability
        tickfont=dict(size=12),
        showgrid=True,  # Enable grid for better data reading
        gridcolor='LightGray',
        gridwidth=0.5
    ),
       
        yaxis=dict(
            tickfont=dict(size=12),
            gridcolor='LightGray',
            gridwidth=0.5
        ),
        margin=dict(l=30, r=30, t=40, b=40)  # Adjust margins
    )
    return fig



#------------------------------------------------------------------------------------------------------------------------#
                               #-----------------------------------------------------#
# Define functions to generate graphs
def intime_overall(employee_name):
    test = df1.loc[df1["employee_name"] == employee_name].copy()
    if test.empty:
        raise ValueError(f"No data found for employee: {employee_name}")
    test['mean_intimes'] = test['mean_intime'].apply(lambda t: t.hour * 3600 + t.minute * 60)
    test["mean_outtimes"] = test["mean_outtime"].apply(lambda t: t.hour * 3600 + t.minute * 60)
    def seconds_to_time(seconds):
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        return f"{int(hours):02}:{int(minutes):02}"
    test['mean_intimes_formatted'] = test['mean_intimes'].apply(seconds_to_time)
    test['mean_outtimes_formatted'] = test['mean_outtimes'].apply(seconds_to_time)
    fig = make_subplots(
        rows=1, cols=2,
        subplot_titles=('Mean In-Time', 'Mean Out-Time'),
        column_widths=[0.5, 0.5]
    )
    fig.add_trace(
        go.Scatter(
            x=test["month_name"],
            y=test["mean_intimes"],
            mode='lines+markers',
            line=dict(color='#003366'),
            marker=dict(size=10, color='#FF4500', line=dict(color='rgba(0,0,0,0.5)', width=2))
        ),
        row=1, col=1
    )
    fig.add_trace(
        go.Scatter(
            x=test["month_name"],
            y=test["mean_outtimes"],
            mode='lines+markers',
            line=dict(color='#003366'),
            marker=dict(size=10, color='#FF4500', line=dict(color='rgba(0,0,0,0.5)', width=2))
        ),
        row=1, col=2
    )
    fig.update_layout(
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgb(245,245,245)',
        yaxis=dict(
            tickvals=test['mean_intimes'],
            ticktext=test['mean_intimes_formatted'],
            title="Mean In-Time"
        ),
        yaxis2=dict(
            tickvals=test['mean_outtimes'],
            ticktext=test['mean_outtimes_formatted'],
            title="Mean Out-Time"
        ),
        xaxis=dict(
            title="Month"
        ),
        xaxis2=dict(
            title="Month"
        ),
        title=dict(text=F'Mean In-Time and Out-Time Over Months', x=0.5),
        margin=dict(l=40, r=40, t=60, b=40),
        showlegend=False
    )
    return fig

def duration_employee(employee_name):
    df1['duration_in_office_seconds'] = df1['duration_in_office'].apply(lambda t: t.hour * 3600 + t.minute * 60)
    df1['working_hours_duration_seconds'] = df1['working_hours_duration'].apply(lambda t: t.hour * 3600 + t.minute * 60)
    def seconds_to_time(seconds):
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        return f"{int(hours):02}:{int(minutes):02}"
    df1['duration_in_office_hours'] = df1['duration_in_office_seconds'] / 3600
    df1['working_hours_duration_hours'] = df1['working_hours_duration_seconds'] / 3600
    df1['duration_in_office_hourS'] = df1['duration_in_office_hours'].apply(lambda h: seconds_to_time(h * 3600))
    df1['working_hours_duration_hourS'] = df1['working_hours_duration_hours'].apply(lambda h: seconds_to_time(h * 3600))
    filtered_df = df1.loc[df1['employee_name'] == employee_name]
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=filtered_df['month_name'],
        y=filtered_df['duration_in_office_hours'],
        name='Duration in Office',
        marker_color='#1f77b4',
        text=filtered_df['duration_in_office_hourS'],
        textposition='outside'
    ))
    fig.add_trace(go.Bar(
        x=filtered_df['month_name'],
        y=filtered_df['working_hours_duration_hours'],
        name='Working Hours',
        marker_color='#ff7f0e',
        text=filtered_df['working_hours_duration_hourS'],
        textposition='inside'
    ))
    fig.update_layout(
        title='Duration in Office vs Working Hours' ,
        yaxis_title='Duration',
        barmode='overlay',
        bargap=0.15,
        bargroupgap=0.1,
        width=1100,
        height=500,
        legend=dict(
            x=1.05,
            y=1.0,
            xanchor='left',
            yanchor='top',
            traceorder='normal',
            orientation='v'
        ),
        font=dict(
            family='Nunito, sans-serif',
            size=14,
            color='teal'
        ),
        xaxis=dict(
            tickangle=360,
            tickfont=dict(
                size=14,
                family="Courier New, monospace",
                color="rgba(0, 128, 128, 0.8)"
            )
        ),
        yaxis=dict(
            tickfont=dict(size=12),
            gridcolor='LightBlue',
            gridwidth=0.5
        ),
        margin=dict(l=30, r=30, t=40, b=40)
    )
    return fig

# Layout for main page
app.layout = html.Div(
    style={'fontFamily': 'Arial, sans-serif', 'padding': '20px', 'backgroundColor': '#ECF0F1'},
    children=[
        dcc.Location(id='url', refresh=False),  # Added Location component for URL routing
        html.Div(id='page-content'),  # Placeholder for page content
    ]
)

# Layout for the main dashboard page
def main_page_layout():
    months = df1["month_name"].unique()
    return html.Div(
    style={
        'fontFamily': 'Arial, sans-serif', 
        'padding': '20px', 
        'backgroundColor': '#F4F6F6'
          # Light background for contrast
    },
    children=[
        html.H1(
            children='Employee Attendance Dashboard',
            style={
                'textAlign': 'center', 
                'color': '#2C3E50',  # Dark blue for prominence
                'marginBottom': '20px', 
                'fontSize': '36px', 
                'fontWeight': 'bold'
            }
        ),
        html.Div(
            children='An interactive Dashboard for Tracking Employee Attendance',
            style={
                'textAlign': 'center', 
                'color': '#34495E',  # Slightly lighter blue-gray for a softer look
                'marginBottom': '40px', 
                'fontSize': '18px'
            }
        ),

            html.Div(
            style={'textAlign': 'center', 'marginBottom': '40px'},
            children=[
                dcc.Dropdown(
                    id='month-dropdown',
                    options=[{'label': month, 'value': month} for month in months],
                    value=months[0],  
                    clearable=False,
                    style={'width': '50%', 'margin': '0 auto', 'color': '#2c5766','background-color': '#e6f2ff',  # Background color of the dropdown
      # Optional: border styling
        # Background color of the dropdown
                      # Optional: border styling
                    }
                ),
                dbc.Tooltip(
                    "Select the month you want to view the attendance data for.",
                    target="month-dropdown",
                    placement="top"
                )
            ]
        ),
            html.Div(
                style={'textAlign': 'center', 'marginBottom': '40px'},
                children=[
                    dash_table.DataTable(
            id='attendance-table',
            columns=[{"name": i, "id": i} for i in df.columns],
            data=df.to_dict('records'),
            style_table={
                'overflowX': 'auto',
                'border': '1px solid #ddd',
                'width': '100%',
                'margin': 'auto',
                'minWidth': '600px'  # Ensures a minimum width for better visibility
            },
            style_header={
                'backgroundColor': '#282c34',  # Dark background for the header
                'color': 'white',
                'fontWeight': 'bold',
                'fontSize': '18px',
                'fontFamily': 'Lato',
                'textAlign': 'center',
                'position': 'sticky',
                'top': '0',
                'zIndex': '1'
            },
            style_cell={
                'textAlign': 'center',
                'fontFamily': 'Lato',
                'padding': '12px',
                'backgroundColor': '#f4f6f9',
                'border': '1px solid #e0e0e0',
                'fontSize': '16px',
                'color': '#333',
                'height': 'auto',
                'whiteSpace': 'normal',
                'maxWidth': '200px',  # Allow column width to be adjustable
                'overflow': 'hidden',
                'textOverflow': 'ellipsis'
            },
            style_data_conditional=[
                {'if': {'row_index': 'odd'}, 'backgroundColor': '#fafafa'},
                {'if': {'row_index': 'even'}, 'backgroundColor': '#ffffff'},
                {'if': {'state': 'active'}, 'backgroundColor': '#d0e4ff', 'border': '1px solid #4A90E2'}
            ],
            editable=True,  # Allow users to edit table data
            #row_selectable='single',  # Allows selection of one row at a time
            selected_rows=[],
            sort_action='native',  # Allow sorting of columns
            #filter_action='native',  # Allow filtering
            page_action='native',  # Allow pagination if needed
            page_size=30  # Adjust page size if necessary
                    )
                ]
                
                    ),
              
            # Dropdown for selecting the type of time (IN or OUT)
    html.Div(
        style={'textAlign': 'center', 'marginBottom': '40px'},
        children=[
            dcc.Dropdown(
                id='time-type-dropdown',
                options=[
                    {'label': 'IN Time', 'value': 'in'},
                    {'label': 'OUT Time', 'value': 'out'}
                ],
                value='in',  
                clearable=False,
                style={'width': '50%', 'margin': '0 auto', 'color': '#573b46'}
            ),
            dbc.Tooltip(
                "Select Employee login time or Logout time for Analysis",
                target="time-type-dropdown",
                placement="bottom"
            )
        ]
    ),
    # Graphs to display times
    html.Div(
        children=[
            dcc.Graph(
                id='time-graph',
                config={'responsive': True},
                style={'height': '650px'}
            ),
            dcc.Graph(
                id='duration-graph',
                config={'responsive': True},
                style={'height': '500px', 'marginTop': '40px'}
            )
        ]
    )
    ]
    ),


# Layout for employee-specific page
def employee_page_layout(employee_name):
    return html.Div(
        style={'fontFamily': 'Arial, sans-serif', 'padding': '20px', 'backgroundColor': '#ECF0F1'},
        children=[
            html.Div(
                style={
                    'backgroundColor': '#F0F8FF',  # Light background color
                    'border': '1px solid #B0C4DE',  # Light border color
                    'borderRadius': '8px',  # Rounded corners
                    'padding': '20px',  # Padding inside the div
                    'margin': '20px 0',  # Margin around the div
                    'boxShadow': '0px 4px 8px rgba(0, 0, 0, 0.2)'  # Shadow for better visual appeal
                },
                children=[
                    html.H2(
                        children='Employee Office Hours Overview',
                        style={
                            'textAlign': 'center',
                            'color': '#2C3E50',  # Dark color for heading
                            'marginBottom': '10px'
                        }
                    ),
                    html.P(
                        children=[
                            "This section provides an overview of the office login and logout times for each individual employee. ",
                            "It includes detailed information about their duration in the office and the total working hours. ",
                            "The average login time is tracked to monitor punctuality, while the logout time ensures accurate record-keeping of end-of-day activities. ",
                            "The duration in the office helps in understanding the total time an employee spends in the office, ",
                            "while the working hours measure the effective working time within the office environment."
                        ],
                        style={
                            'fontSize': '16px',
                            'color': '#34495E',  # Dark gray color for text
                            'lineHeight': '1.6',  # Line height for better readability
                            'textAlign': 'justify'  # Justified alignment for better readability
                        }
                    )
                ]
            ),
            html.H1(
                children=f'{employee_name} - Attendance Overview',
                style={'textAlign': 'center', 'color': '#2C3E50', 'marginBottom': '20px'}
            ),
            dcc.Graph(
                id='employee-time-graph',
                config={'responsive': True},
                style={'height': '500px', 'marginTop': '40px'}
            ),
            dcc.Graph(
                id='employee-duration-graph',
                config={'responsive': True},
                style={'height': '500px', 'marginTop': '40px'}
            )
        ]
    )


#---------------------------------------------------------------------------------------------#
#first main page graphs 
# Define the callback to update the graphs based on the selected month and time type
@app.callback(
    [Output('time-graph', 'figure'),
     Output('duration-graph', 'figure')],
    [Input('month-dropdown', 'value'),
     Input('time-type-dropdown', 'value')]
)
def update_graphs(selected_month, time_type):
    if time_type == 'in':
        time_fig = cal_meantime(selected_month)
    else:
        time_fig = cal_outtime(selected_month)
    duration_fig = Duration(selected_month)
    return time_fig, duration_fig
#---------------------------------------------------------------------------------------------------------------------
@app.callback(
    Output('attendance-table', 'data'),
    [Input('month-dropdown', 'value')]
)
def update_table(month_name):
    filtered_df = df1[df1["month_name"] == month_name].copy()
    return filtered_df.to_dict('records')
# Callback to update the page content based on URL
@app.callback(
    Output('page-content', 'children'),
    [Input('url', 'pathname')],
    [State('url', 'search')]
    
)
def display_page(pathname, search):
    if pathname.startswith('/employee/'):
        employee_name = pathname.split('/')[-1]
        return employee_page_layout(employee_name)
    else:
        return main_page_layout()

@app.callback(
    Output('url', 'pathname'),
    [Input('attendance-table', 'active_cell')],
    [State('month-dropdown', 'value')]
)
def redirect_to_employee_page(active_cell, selected_month):
    if active_cell:
        # Filter the dataframe based on the selected month
        filtered_df = df1[df1['month_name'] == selected_month].copy()
        # Use the filtered dataframe's row index to get the correct employee
        employee_name = filtered_df.iloc[active_cell['row']]['employee_name']
        return f'/employee/{employee_name}'
    return '/'


#Callback to update the graphs on the employee-specific page
@app.callback(
    [Output('employee-time-graph', 'figure'),
     Output('employee-duration-graph', 'figure')],
    [Input('url', 'pathname')]
)
def update_employee_graphs(pathname):
    if pathname.startswith('/employee/'):
        employee_name = pathname.split('/')[-1]
        employee_time_fig = intime_overall(employee_name)
        employee_duration_fig = duration_employee(employee_name)
        return employee_time_fig, employee_duration_fig
    return {}, {}

if __name__ == '__main__':
    app.run_server(host='0.0.0.0', port=8050, debug=True)
    


