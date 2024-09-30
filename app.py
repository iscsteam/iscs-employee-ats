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
from statsmodels.nonparametric.smoothers_lowess import lowess
import warnings
# Ignore all warnings
warnings.filterwarnings("ignore")
from dash import Dash, html
from flask import Flask, jsonify
from database_connection import connect_to_postgresql , get_table_data 
import secrets
import hashlib    

# Generate a random 32-byte secret key
random_secret_key = secrets.token_bytes(32)

# Hash the random secret key using SHA256
hashed_secret_key = hashlib.sha256(random_secret_key).hexdigest()
# Create a Flask server instance
server = Flask(__name__)
server.secret_key = hashed_secret_key

username= os.getenv("database_username")
password = os.getenv("password") 
host = os.getenv("db_host")
port =  os.getenv("db_port")
database = os.getenv("database_name")
# Construct the connection string
database_url = f"postgresql://{username}:{password}@{host}:{port}/{database}"
connection = connect_to_postgresql(database_url)
#----------------------
df=get_table_data(connection,"employee_work_hours")

df1=df.copy()
df1['mean_intime'] = pd.to_datetime(df1['mean_intime'], format='%H:%M').dt.time
df1['mean_outtime'] = pd.to_datetime(df1['mean_outtime'], format='%H:%M').dt.time
df1['duration_in_office'] = pd.to_datetime(df1['duration_in_office'], format='%H:%M').dt.time
df1['working_hours_duration'] = pd.to_datetime(df1['working_hours_duration'], format='%H:%M').dt.time
##the daily logs table 
daily_logs=get_table_data(connection,"employee_attendance_daily")
t2=daily_logs.copy()
def time_to_timedelta(time_str):
    hours, minutes = map(int, time_str.split(':'))
    return pd.Timedelta(hours=hours, minutes=minutes)

# Apply the function to convert time strings to timedelta
t2['duration_in_office1'] = t2['duration_in_office'].apply(time_to_timedelta)
t2['total_working_time1'] = t2['total_working_time'].apply(time_to_timedelta)

# Calculate break hours (duration_in_office - total_working_time)
t2['break_hours'] = t2['duration_in_office1'] - t2['total_working_time1']
colummns_to_drop=["duration_in_office1","total_working_time1"]
t2.drop(columns=colummns_to_drop,axis=1,inplace=True)
t2["break_hours"] = t2["break_hours"].apply(lambda x: str(x)[7:])
#---------------------------------------------------------------------------
#t3=daily_logs.copy()
def process_employee_metrics(employee_name, month_name,return_only_graph=False):
    t3=daily_logs.copy()
    t3 = t3[(t3["employee_name"] == employee_name) & (t3["month_name"] ==month_name)]
    def time_to_timedelta(time_str):
        hours, minutes = map(int, time_str.split(':'))
        return pd.Timedelta(hours=hours, minutes=minutes)

    # Apply the function to convert time strings to timedelta
    t3['duration_in_office1'] = t3['duration_in_office'].apply(time_to_timedelta)
    t3['total_working_time1'] = t3['total_working_time'].apply(time_to_timedelta)

    # Calculate break hours (duration_in_office - total_working_time)
    t3['break_hours'] = t3['duration_in_office1'] - t3['total_working_time1']
    colummns_to_drop=["duration_in_office1","total_working_time1"]
    t3.drop(columns=colummns_to_drop,axis=1,inplace=True)
    t3["break_hours"] = t3["break_hours"].apply(lambda x: str(x)[7:])


    # Convert time columns to datetime.time for easy comparison
    t3['in_time'] = pd.to_datetime(t3['in_time'], format='%H:%M').dt.time
    t3['out_time'] = pd.to_datetime(t3['out_time'], format='%H:%M').dt.time
    t3['duration_in_office'] = pd.to_datetime(t3['duration_in_office'], format='%H:%M').dt.time
    t3['total_working_time'] = pd.to_datetime(t3['total_working_time'], format='%H:%M').dt.time
    t3['break_hours'] = pd.to_timedelta(t3['break_hours'])
    #Define cutoff times for different parameters
    login_benchmark="9:40"
    log_out_benchmark="18:25"
    durationoffice_benchmark="9:00"
    break_time_benchmark='01:30:00'

    cutoff_time_logintime = pd.to_datetime(login_benchmark, format='%H:%M').time()
    cutoff_time_logout = pd.to_datetime(log_out_benchmark, format='%H:%M').time()
    cutoff_time_duration_in_office = pd.to_datetime(durationoffice_benchmark, format='%H:%M').time()
    #cutoff_time_break_hours = pd.to_datetime(break_time_benchmark, format='%H:%M').time()
    # Filter employees who logged in after the cutoff login time
    late_logins_df = t3[t3['in_time'] > cutoff_time_logintime]
    # Filter employees who logged out after the cutoff logout time
    late_logout_df = t3[t3['out_time'] < cutoff_time_logout]
    # Filter employees who stayed in the office for more than the cutoff duration
    long_duration_df = t3[t3['duration_in_office'] < cutoff_time_duration_in_office]
    break_duration_df = t3[t3['break_hours'] > pd.Timedelta(break_time_benchmark)]
    break_duration_df["break_hours"]= t3["break_hours"].apply(lambda x: str(x)[7:])
    t3["break_hours"]= t3["break_hours"].apply(lambda x: str(x)[7:])

    data1 = [
        {'Metric': 'No of  Late Logins', 'Value': f"{len(late_logins_df)} out of {len(t3)} days", 'Benchmark': f'after {login_benchmark} am'},
        {'Metric': 'No of Early Logouts', 'Value': f"{len(late_logout_df)} out of {len(t3)} days", 'Benchmark': f' before  {log_out_benchmark} pm'},
        {'Metric': 'No of Short Office Durations', 'Value': f"{len(long_duration_df)} out of {len(t3)} days", 'Benchmark': f' less than {durationoffice_benchmark} houres in office'},
        {'Metric': 'No of Large Break Durations', 'Value': f"{len(break_duration_df)} out of {len(t3)} days", 'Benchmark': f'{break_time_benchmark}'}
    ]
    x=["Late Logins","Early Logouts","No of Short  Office Durations","No of Large Break Durations"]
    y1=[len(late_logins_df),len(late_logout_df),len(long_duration_df),len(break_duration_df)]
    # Bar Chart for graphical representation
    bar_fig = go.Figure()
    bar_fig.add_trace(go.Bar(
    x=['Late Logins', 'Early Logouts', 'Short Office Durations', 'Large Break Durations'],
    y=y1,  # Ensure y1 is provided or replace it with the actual y-values
    marker=dict(
        color=['#f6c23e', '#e74a3b', '#36b9cc', '#1cc88a'],
        line=dict(color='white', width=1.5)  # Adding a white border for better contrast
    ),
    hoverinfo="x+y",  # Show both x and y values on hover
    text=y1,  # Display y-values on the bars
    textposition='auto'  # Automatically place the text inside or outside the bars
))

# Customize layout for a more professional and sleek appearance
    bar_fig.update_layout(
        title={
            'text': "Attendance Metrics",
            'y':0.9,  # Position the title closer to the top
            'x':0.5,  # Center the title horizontally
            'xanchor': 'center',
            'yanchor': 'top',
            'font': dict(size=24, family="Google Sans, Helvetica Neue, sans-serif")  # Stylish title font
        },
        xaxis=dict(
            title="Metrics",
            titlefont=dict(size=18),
            showgrid=True,  # Adding grid lines for x-axis
            gridcolor='#2d2d2d',  # Subtle grid color matching the theme
            tickangle=-45,  # Rotating the x-axis labels for better readability
            tickfont=dict(size=14, family="Google Sans, Helvetica Neue, sans-serif")  # Stylish axis font
        ),
        yaxis=dict(
            title="Count",
            titlefont=dict(size=18),
            showgrid=True,  # Adding grid lines for y-axis
            gridcolor='#2d2d2d',  # Subtle grid color matching the theme
            tickfont=dict(size=14, family="Google Sans, Helvetica Neue, sans-serif")
        ),
        plot_bgcolor='#1c1c1c',  # Matching the dark theme
        paper_bgcolor='#1c1c1c',
        font_color='white',
        hovermode="x"  # Hover information will appear when hovering over x-axis values
    )
    if return_only_graph:
        return bar_fig
    else:
        return bar_fig, late_logins_df, late_logout_df, long_duration_df, break_duration_df, data1


#####$break ---time graph-----------------------------------------------------------------------
b2=daily_logs.copy()
def plot_employee_break_hours(employee_name, month_name):
    # Filter data for the specific employee and month
    employee_data = b2[b2["employee_name"] == employee_name].copy()
    filtered_data = employee_data[employee_data["month_name"] == month_name].copy()
    # Function to convert time strings (HH:MM) to timedelta
    def time_to_timedelta(time_str):
        hours, minutes = map(int, time_str.split(':'))
        return pd.Timedelta(hours=hours, minutes=minutes)

    # Apply the function to convert time strings to timedelta
    filtered_data['duration_in_office1'] = filtered_data['duration_in_office'].apply(time_to_timedelta)
    filtered_data['total_working_time1'] = filtered_data['total_working_time'].apply(time_to_timedelta)

    # Calculate break hours (duration_in_office - total_working_time)
    filtered_data['break_hours'] = filtered_data['duration_in_office1'] - filtered_data['total_working_time1']

    # Drop intermediate timedelta columns
    filtered_data.drop(columns=["duration_in_office1", "total_working_time1"], inplace=True)

    # Convert break_hours to string for hover information
    filtered_data["break_hours_str"] = filtered_data["break_hours"].apply(lambda x: str(x)[7:])

    # Convert timedelta to minutes for plotting
    filtered_data["break_minutes"] = filtered_data["break_hours"].dt.total_seconds() / 60

    # Parse and format attendance dates
    filtered_data['attendance_dates'] = pd.to_datetime(filtered_data['attendance_date'], format='%d-%m-%Y')
    filtered_data['date_column'] = filtered_data['attendance_dates'].dt.strftime('%d%b%Y').str.lstrip('0')

    # Apply LOWESS (Locally Weighted Scatterplot Smoothing) for a smooth trend line
    smoothed_values = lowess(filtered_data['break_minutes'], filtered_data['attendance_dates'].map(pd.Timestamp.toordinal), frac=0.3)[:, 1]

    # Plot the line graph using Plotly
    fig = go.Figure()

    # Add trace for break minutes with color gradient
    fig.add_trace(go.Scatter(
        x=filtered_data["date_column"],
        y=filtered_data["break_minutes"],
        mode='lines+markers',
        name='Break Duration',
        marker=dict(
            size=12,
            color=filtered_data["break_minutes"],  # Color based on break_minutes value
            colorscale='Blues',  # Professional color scheme
            showscale=True,      # Display the color scale
            line=dict(width=2, color='black')
        ),
        line=dict(color='#118AB2', width=4),
        hovertemplate="<b>Date:</b> %{x}<br><b>Break Duration:</b> %{y:.2f} minutes<br><b>Break Time:</b> %{customdata}",
        customdata=filtered_data["break_hours_str"]
    ))

    # Add a smooth LOWESS trend line to the figure
    fig.add_trace(go.Scatter(
        x=filtered_data["date_column"],
        y=smoothed_values,
        mode='lines',
        name='Smooth Trend Line',
        line=dict(color='red', width=3, dash='dot')
    ))

    # Annotations for max/min points
    max_break = filtered_data.loc[filtered_data['break_minutes'].idxmax()]
    min_break = filtered_data.loc[filtered_data['break_minutes'].idxmin()]

    fig.add_annotation(
        x=max_break["date_column"], y=max_break["break_minutes"],
        text=f"Max Break: {max_break['break_hours_str']}",
        showarrow=True, arrowhead=2, ax=-20, ay=-40,
        bgcolor='lightblue', bordercolor='blue', font=dict(color='black')
    )

    fig.add_annotation(
        x=min_break["date_column"], y=min_break["break_minutes"],
        text=f"Min Break: {min_break['break_hours_str']}",
        showarrow=True, arrowhead=2, ax=-20, ay=40,
        bgcolor='lightblue', bordercolor='blue', font=dict(color='black')
    )

    # Enhance the layout with a dark theme
    fig.update_layout(
        title={
            'text': f'Break Hours for {employee_name} ({month_name})',
            'y': 0.9,
            'x': 0.5,
            'xanchor': 'center',
            'yanchor': 'top',
            'font': dict(size=24, color='#A9A9A9')
        },
        legend=dict(
        x=1,   # X position (0 to 1)
        y=1.15,   # Y position (0 to 1)
        traceorder='normal',
        orientation='v'  # Vertical orientation
    ),
        yaxis_title='Break Duration (minutes)',
        plot_bgcolor='black',  # Black background as per your app
        paper_bgcolor='black',
        font=dict(family="Arial", size=14, color='white'),
        xaxis=dict(showgrid=True, gridcolor='#A9A9A9'),
        yaxis=dict(showgrid=True, gridcolor='#A9A9A9'),
        margin=dict(l=40, r=40, t=80, b=40),
    )

    return fig 
#################### the table data 

def table_data_daily(employee_name, month_name):
    table_month=daily_logs.copy()
    table_month = table_month[table_month["employee_name"] == employee_name]
    table_month = table_month[table_month["month_name"] == month_name]
    def time_to_timedelta(time_str):
        hours, minutes = map(int, time_str.split(':'))
        return pd.Timedelta(hours=hours, minutes=minutes)

    # Apply the function to convert time strings to timedelta
    table_month['duration_in_office1'] = table_month['duration_in_office'].apply(time_to_timedelta)
    table_month['total_working_time1'] = table_month['total_working_time'].apply(time_to_timedelta)

    # Calculate break hours (duration_in_office - total_working_time)
    table_month['break_hours'] = table_month['duration_in_office1'] - table_month['total_working_time1']
    columns_to_drop = ["duration_in_office1", "total_working_time1"]
    table_month.drop(columns=columns_to_drop, axis=1, inplace=True)
    table_month["break_hours"] = table_month["break_hours"].apply(lambda x: str(x)[7:])

    # Convert time columns to datetime.time for easy comparison
    table_month['in_time'] = pd.to_datetime(table_month['in_time'], format='%H:%M').dt.time
    table_month['out_time'] = pd.to_datetime(table_month['out_time'], format='%H:%M').dt.time
    table_month['duration_in_office'] = pd.to_datetime(table_month['duration_in_office'], format='%H:%M').dt.time
    table_month['total_working_time'] = pd.to_datetime(table_month['total_working_time'], format='%H:%M').dt.time
    table_month['break_hours'] = pd.to_timedelta(table_month['break_hours'])
    table_month["break_hours"] = table_month["break_hours"].apply(lambda x: str(x)[7:])

    return table_month
#----------------------------------------------------------
#
#HGGPIUSGFDPIU                                                OJSHDOFIHASDPIOFHOI
#                     IHSGDOIFUGPISUGFPIUWS
#                   ISJDHGPOUAHSDPGIOH[ASOD]
#               kjhsdgfhsgfiSHDGF
# Initialize the Dash app
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP], suppress_callback_exceptions=True,server=server)
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

    # In-Time Plot
    fig.add_trace(
        go.Scatter(
            x=test["month_name"],
            y=test["mean_intimes"],
            mode='lines+markers',
            line=dict(color='#007BFF', width=2),
            marker=dict(size=8, color='#0056b3', line=dict(color='rgba(0,0,0,0.6)', width=1.5)),
            name='Mean In-Time'
        ),
        row=1, col=1
    )

    # Out-Time Plot
    fig.add_trace(
        go.Scatter(
            x=test["month_name"],
            y=test["mean_outtimes"],
            mode='lines+markers',
            line=dict(color='#28A745', width=2),
            marker=dict(size=8, color='#218838', line=dict(color='rgba(0,0,0,0.6)', width=1.5)),
            name='Mean Out-Time'
        ),
        row=1, col=2
    )

    # Layout Updates
    fig.update_layout(
        plot_bgcolor='rgba(255,255,255,0.85)',
        paper_bgcolor='rgba(245,245,245)',
        yaxis=dict(
            title="Mean In-Time (Seconds)",
            tickvals=test['mean_intimes'],
            ticktext=test['mean_intimes_formatted'],
            gridcolor='rgba(200,200,200,0.5)'
        ),
        yaxis2=dict(
            title="Mean Out-Time (Seconds)",
            tickvals=test['mean_outtimes'],
            ticktext=test['mean_outtimes_formatted'],
            gridcolor='rgba(200,200,200,0.5)'
        ),
        xaxis=dict(
            title="Month",
            tickangle=-45
        ),
        xaxis2=dict(
            title="Month",
            tickangle=-45
        ),
        title=dict(text='Mean In-Time and Out-Time Over Months', x=0.5, font=dict(size=20)),
        margin=dict(l=40, r=40, t=60, b=40),
        showlegend=True
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
    
    # Duration in Office - Muted Dark Teal
    fig.add_trace(go.Bar(
        x=filtered_df['month_name'],
        y=filtered_df['duration_in_office_hours'],
        name='Duration in Office',
        marker_color='#005B5B',  # Muted Dark Teal
        text=filtered_df['duration_in_office_hourS'],
        textposition='outside'
    ))
    
    # Working Hours - Matte Gold
    fig.add_trace(go.Bar(
        x=filtered_df['month_name'],
        y=filtered_df['working_hours_duration_hours'],
        name='Working Hours',
        marker_color='#C1A052',  # Matte Gold
        text=filtered_df['working_hours_duration_hourS'],
        textposition='inside'
    ))
    
    # Calculate average lines
    avg_duration = filtered_df['duration_in_office_hours'].mean()
    avg_working_hours = filtered_df['working_hours_duration_hours'].mean()
    
    # Add average lines
    fig.add_trace(go.Scatter(
        x=filtered_df['month_name'],
        y=[avg_duration] * len(filtered_df),  # Average line for duration in office
        mode='lines',
        name='Avg Duration in Office',
        line=dict(color='#007C92', width=2, dash='dash')  # Dash line for average
    ))
    
    fig.add_trace(go.Scatter(
        x=filtered_df['month_name'],
        y=[avg_working_hours] * len(filtered_df),  # Average line for working hours
        mode='lines',
        name='Avg Working Hours',
        line=dict(color='#FFD700', width=2, dash='dash')  # Dash line for average
    ))
    
    # Layout updates
    fig.update_layout(
        title='Duration in Office vs Working Hours',
        title_font=dict(size=28, color='#FFCC00', family='Arial, sans-serif'),  # Advanced title font and color
        yaxis_title='Duration (Hours)',
        barmode='overlay',  # Group mode for better distinction
        bargap=0.15,
        bargroupgap=0.1,
        width=1100,
        height=500,
        paper_bgcolor='rgba(0, 0, 0, 1)',  # Black background
        plot_bgcolor='rgba(0, 0, 0, 1)',  # Black plot background
        legend=dict(
            x=1.05,
            y=1.0,
            xanchor='left',
            yanchor='top',
            traceorder='normal',
            orientation='v',
            font=dict(color='#D3D3D3')  # Light grey legend text
        ),
        font=dict(
            family='Nunito, sans-serif',
            size=14,
            color='#D3D3D3'  # Light grey text
        ),
        xaxis=dict(
            tickangle=360,
            tickfont=dict(
                size=14,
                family="Courier New, monospace",
                color="rgba(211, 211, 211, 0.8)"  # X-axis light grey
            )
        ),
        yaxis=dict(
            tickfont=dict(size=12, color='#D3D3D3'),  # Y-axis light grey
            gridcolor='rgba(68, 68, 68, 0.4)',  # Subtle dark grey grid lines
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
 #-------------------------------------------------------------------------------------------------------
 #--------------------------------------------------------------------------------------------
   #----------------------------------------------ojdfhgpjshgs-----------
# Layout for employee-specific page
def employee_page_layout(employee_name,table_data,
                         late_logins_df,late_logout_df,long_duration_df,break_duration_df,data1): #late_logins_df late_logout_df long_duration_df,break_duration_df
    return html.Div(
        style={'background-color': '#1c1c1c', 'min-height': '100vh', 'padding': '20px'}, 
        children=[
            html.H1(
                'Attendance Validation Summary', 
                style={
                    'text-align': 'center', 
                    'color': '#f8f9fa', 
                    'font-size': '40px', 
                    'margin-bottom': '20px',
                    'text-shadow': '2px 2px 4px rgba(0, 0, 0, 0.7)',  # Text shadow for depth
                    'font-style': 'italic'
                } ),
            html.H2(
    children=f' of {employee_name}',
    style={
        'textAlign': 'center',
        'color': '#ECF0F1',  # Light color for contrast against a black background
        'marginBottom': '20px',
        'fontFamily': 'Arial, sans-serif',  # Good font choice
        'fontSize': '24px',  # Adjust font size as needed
        'fontWeight': 'italic',  # Make the text bold
        'textShadow': '1px 1px 2px rgba(0, 0, 0, 0.7)',  # Optional shadow for depth
    }
),
    html.Div(
       
        children=[
            # Dropdown for selecting the month
            html.Div(
                style={'width': '20%', 'margin': '0 auto', 'paddingBottom': '20px'},
                children=[
                    dcc.Dropdown(
                        id='break-month-dropdown',  # Dropdown ID for callback
                        options=[{'label': month, 'value': month} for month in b2['month_name'].unique()],
                        value=daily_logs['month_name'].unique()[0],  # Default value (first month in the dataset)
                        clearable=False,
                        placeholder="Select Month",
                        style={'color': '#2c5766', 'background-color': '#e6f2ff'}
                    ),
                    #dcc.Graph(id='break-duration-graph', style={'height': '600px', 'width': '100%'}) # Set height and width) 
                ]
            ),
    html.Div(
         dash_table.DataTable(
        id='employee-table',
        columns=[{"name": i, "id": i} for i in table_data.columns],
        data=table_data.to_dict('records'),
        page_action="native",
        page_size=30,
        style_table={
            'maxWidth': '100%',
            'overflowX': 'auto',
            'backgroundColor': '#121212',  # Darker table background for better contrast
            'boxShadow': '0 4px 8px rgba(0, 0, 0, 0.2)',  # Add shadow for a modern look
            'borderRadius': '8px',  # Rounded corners for a softer appearance
        },
        style_cell={
            'backgroundColor': '#121212',  # Cell background color
            'color': 'white',               # Text color for cell content
            'border': 'thin lightgrey solid',
            'padding': '8px',             # Increased cell padding for better spacing
            'textAlign': 'center',          # Center text alignment for uniformity
            'fontFamily': 'Google Sans, Helvetica Neue, sans-serif',  # Professional font
            'fontSize': '13px',             # Slightly larger font size for readability
        },
        fixed_columns={'headers': True, 'data': 1},
        style_header={
            'backgroundColor': '#1c1c1c',  # Darker header for contrast
            'color': 'white',
            'fontWeight': 'bold',
            'border': 'thin lightgrey solid',  # Border for header cells
            'fontSize': '15px',               # Larger font for headers
            'textAlign': 'center',            # Center align headers
        },
       style_data_conditional=[
            # Condition 1: Time greater than 09:41:00 (tomato background)
            {
                'if': {
                    'filter_query': '{in_time} >= "09:41:00"',
                    'column_id': 'in_time'
                },
                'backgroundColor': 'tomato',
                'color': 'white'
            },
            # Condition 2: Time less than 09:30:00 (green background)
            {
                'if': {
                    'filter_query': '{in_time} <= "09:30:00"',
                    'column_id': 'in_time'
                },
                'backgroundColor': 'green',
                'color': 'white'
            },
            {
                'if': {
                    'filter_query': '{in_time} >= "09:30:00" && {in_time} <= "09:40:00"',
                    'column_id': 'in_time'
                },
                'backgroundColor': 'yellow',
                'color': 'black'
            },
            {
                'if': {
                    'filter_query': '{out_time} <= "18:29:00"',
                    'column_id': 'out_time'
                },
                'backgroundColor': 'red',
                'color': 'black'
            },
            {
                'if': {
                    'filter_query': '{duration_in_office} <= "09:00" && {duration_in_office} >= "08:30:00"',
                    'column_id': 'duration_in_office'
                },
                'backgroundColor': 'yellow',
                'color': 'black'
            },
            {
                'if': {
                    'filter_query': '{duration_in_office} < "08:30:00"',
                    'column_id': 'duration_in_office'
                },
                'backgroundColor': 'red',
                'color': 'black'
            },
            {
                'if': {
                    'filter_query': '{duration_in_office} > "09:00:00"',
                    'column_id': 'duration_in_office'
                },
                'backgroundColor': 'green',
                'color': 'black'
            },
            {
                'if': {
                    'filter_query': '{break_hours} > "02:00:00"',
                    'column_id': 'break_hours'
                },
                'backgroundColor': 'red',
                'color': 'black'
            }
        ],
        export_format='csv',
        export_headers='display',
        merge_duplicate_headers=True,
        style_data={
            'whiteSpace': 'normal',   # Allow line breaks
            'height': 'auto',         # Let rows expand naturally
        },
    )
),
    html.Div([
    html.H2(' Employee Attendance Metrics ', 
             style={
                 'text-align': 'center', 
                 'color': '#ffffff', 
                 'font-weight': 'bold', 
                 'font-size': '40px', 
                 'margin-bottom': '10px', 
                 'text-shadow': '2px 2px 4px rgba(0, 0, 0, 0.7)'
             }),
    html.P('Insights into employee attendance performance, including total late logins, logouts, and duration metrics.', 
            style={
                'text-align': 'center', 
                'color': '#d1d1d1', 
                'font-size': '20px', 
                'margin-bottom': '30px',
                'font-style': 'italic'
            })
], style={'margin-bottom': '30px'}),  # Add some spacing below the heading



            # KPI Boxes
        html.Div([
            html.Div([
                html.H3(id='late-logins-count', children=str(len(late_logins_df)), style={'color': '#f6c23e'}),
                html.P('No of Late Logins', style={'color': '#f8f9fa'}),
            ], id='late-logins-box', style={'background-color': '#2e2e2e', 'padding': '20px', 'border-radius': '10px', 'width': '200px', 'margin': '10px'}),
            
            html.Div([
                html.H3(id='early-logouts-count', children=str(len(late_logout_df)), style={'color': '#e74a3b'}),
                html.P('No of Early Logouts', style={'color': '#f8f9fa'}),
            ], id='early-logouts-box', style={'background-color': '#2e2e2e', 'padding': '20px', 'border-radius': '10px', 'width': '200px', 'margin': '10px'}),
            
            html.Div([
                html.H3(id='short-durations-count', children=str(len(long_duration_df)), style={'color': '#36b9cc'}),
                html.P('No of Short Office Durations', style={'color': '#f8f9fa'}),
            ], id='short-durations-box', style={'background-color': '#2e2e2e', 'padding': '20px', 'border-radius': '10px', 'width': '200px', 'margin': '10px'}),
            
            html.Div([
                html.H3(id='large-breaks-count', children=str(len(break_duration_df)), style={'color': '#1cc88a'}),
                html.P('No of Large Break Durations', style={'color': '#f8f9fa'}),
            ], id='large-breaks-box', style={'background-color': '#2e2e2e', 'padding': '20px', 'border-radius': '10px', 'width': '200px', 'margin': '10px'}),
        ], style={'display': 'flex', 'justify-content': 'center'}),

        # Summary DataTable
        dash_table.DataTable(
            id='summary-data-table',  # Unique ID for the DataTable
            data=data1,
            columns=[
                {'name': 'Metric', 'id': 'Metric'},
                {'name': 'Value', 'id': 'Value'},
                {'name': 'Benchmark', 'id': 'Benchmark'}
            ],
            style_table={'width': '60%', 'margin': 'auto', 'margin-top': '20px'},
            style_header={
                'backgroundColor': '#2e2e2e',
                'fontWeight': 'bold',
                'fontSize': '18px',
                'color': '#f8f9fa'
            },
            style_cell={
                'padding': '10px',
                'backgroundColor': '#1c1c1c',
                'color': '#f8f9fa',
                'border': '1px solid #444'
            },
            style_data_conditional=[
                {
                    'if': {'filter_query': '{Metric} contains "Late Logins" and {Value} > "8"'},
                    'backgroundColor': '#e74a3b',
                    'color': 'white',
                },
                {
                    'if': {'filter_query': '{Metric} contains "Late Logins" and {Value} <= "8"'},
                    'backgroundColor': '#1cc88a',
                    'color': 'white',
                }
            ]
        ),

            # Break Duration Graph
             dcc.Graph(
                id='employee-metrics-graph',
                style={'height': '450px', 'width': '100%'}  # Set height and width
            ),
            dcc.Graph(
                id='break-duration-graph',
                style={'height': '450px', 'width': '100%'}  # Set height and width
            ),
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
            )
        ]),
           
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
        employee_name = pathname.split('/')[-1]  # Extract employee name from URL
        default_month = daily_logs['month_name'].unique()[0]  # Get the default month from data
        table_data = table_data_daily(employee_name, default_month)  # Fetch table data for the employee and default month

        # Call the process_employee_metrics function to get metrics without returning the graph
        _, late_logins_df, late_logout_df, long_duration_df, break_duration_df, data1 = process_employee_metrics(employee_name, default_month)

        # Pass the data and metrics to employee_page_layout without the bar figure
        return employee_page_layout(employee_name, table_data, late_logins_df, late_logout_df, long_duration_df, break_duration_df, data1)
    else:
        return main_page_layout()

# Callback function to update the employee table when a new month is selected
# @app.callback(
#     Output('employee-table', 'data'),
#     [Input('break-month-dropdown', 'value')],
#     [State('url', 'pathname')]
# )

# def update_employee_table(month_name, pathname):
#     if pathname.startswith('/employee/'):
#         employee_name = pathname.split('/')[-1]  # Extract employee name from URL

#         # If no month is selected, default to the first available month in the dropdown
#         if not month_name:
#             month_name = daily_logs['month_name'].unique()[0]

#         table_data = table_data_daily(employee_name, month_name)  # Fetch table data for the selected month

#         return table_data.to_dict('records')  # Return the table data in dictionary format
#     return []
@app.callback(
    [Output('employee-table', 'data'),
     Output('summary-data-table', 'data'),
     Output('late-logins-count', 'children'),
     Output('early-logouts-count', 'children'),
     Output('short-durations-count', 'children'),
     Output('large-breaks-count', 'children')],
    [Input('break-month-dropdown', 'value')],
    [State('url', 'pathname')]
)
def update_metrics_and_table(month_name, pathname):
    if pathname.startswith('/employee/'):
        employee_name = pathname.split('/')[-1]
        
        # Get the table data for the selected month
        table_data = table_data_daily(employee_name, month_name)

        # Get the metrics based on the employee and month
        _, late_logins_df, late_logout_df, long_duration_df, break_duration_df, data1 = process_employee_metrics(employee_name, month_name)

        return (
            table_data.to_dict('records'),
            data1,
            str(len(late_logins_df)),
            str(len(late_logout_df)),
            str(len(long_duration_df)),
            str(len(break_duration_df))
        )
    return [], [], '', '', '', ''  # Default return if no pathname matches

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



@app.callback(
    [Output('employee-time-graph', 'figure'),
     Output('employee-duration-graph', 'figure'),
     Output('break-duration-graph', 'figure'),#
     Output('employee-metrics-graph', 'figure')],
    [Input('url', 'pathname'), 
     Input('break-month-dropdown', 'value')]
)

def update_employee_graphs(pathname,month_name):
    if pathname.startswith('/employee/'):
        employee_name = pathname.split('/')[-1]
        #table_data = table_data_daily(employee_name, month_name)  # Pass employee and month name
        employee_time_fig = intime_overall(employee_name)
        employee_duration_fig = duration_employee(employee_name)
        employee_break_fig=plot_employee_break_hours(employee_name,month_name)
        employee_metrics_fig=process_employee_metrics(employee_name, month_name,return_only_graph=True)

        return employee_time_fig, employee_duration_fig, employee_break_fig,employee_metrics_fig
    return {}, {},{},[]

if __name__ == "__main__":
    # Use Waitress to serve the Flask server with Dash app
    serve(app.server, host='0.0.0.0', port=8050)
