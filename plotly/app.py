import pandas as pd
import numpy as np
import urllib.request
import socket

import dash
import dash_core_components as dcc
import dash_html_components as html
import plotly.graph_objects as go
import plotly.express as px
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output, State
import io
import json
import geojson
from flask import Flask
#init_notebook_mode(connected = True)


df = pd.read_csv("mor_loc.csv",header=None, skiprows=3)
df = df[0].str.split(';', expand=True).replace('"', '', regex=True)
df.columns = df.iloc[0]
df = df.drop([0])
df.rename(columns={'INLANDAUSLAND': 'Cantons'}, inplace=True)
df['BANKENGRUPPE'] = df['BANKENGRUPPE'].replace({'S10': 'AllBanks', 'G10': 'CantonalBanks', 'G15': 'BigBanks', 'G20': 'RegAndSavBanks', 'G25':'Raiffeisen'})
mor_Cant = df.groupby(["Date","Cantons", "BANKENGRUPPE"])['Value'].aggregate(lambda x: x).unstack().reset_index()
cols = mor_Cant.columns.drop('Cantons')
mor_Cant[cols] = mor_Cant[cols].apply(pd.to_numeric, errors='coerce')
#mor_Cant = mor_Cant.astype({'Date': 'int8','Cantons': 'str','AllBanks': 'float32','BigBanks': 'float32','CantonalBanks': 'float32','Raiffeisen': 'float32','RegAndSavBanks': 'float32'})


mor_Nat = mor_Cant[mor_Cant["Cantons"] == 'CHE1']
mor_Cant = mor_Cant[~mor_Cant.isin(mor_Nat)].dropna()
mor_Cant[cols] = mor_Cant[cols].astype(int)

#Get cantons by themselves
available_indicators = mor_Cant['Cantons'].unique()


#Get only cantons in 2002
All_Bank2002 = mor_Cant.loc[mor_Cant["Date"] == 2002,:]
#Create numpy arrays of df
All_Bank2002V = All_Bank2002.values




# Create server variable with Flask server object for use with gunicorn
swiss_url = 'https://raw.githubusercontent.com/empet/Datasets/master/swiss-cantons.geojson'


def read_geojson(url):
    with urllib.request.urlopen(url) as url:
        jdata = json.loads(url.read().decode())
    return jdata 
jdata = read_geojson(swiss_url)




title = '2019 Mortgage volume per Canton'

swissmap = go.Figure(go.Choroplethmapbox(geojson=jdata, 
                                    locations=available_indicators, 
                                    z=All_Bank2002["AllBanks"],
                                    featureidkey='properties.id',
                                    coloraxis="coloraxis",
                                    customdata=All_Bank2002V,
                                    hovertemplate= 'Canton: %{customdata[1]}'+\
                                    '<br>All Banks: %{customdata[2]}CHF mill'+\
                                    '<br>Big Banks: %{customdata[3]}CHF mill'+\
                                    '<br>Cantonal Banks: %{customdata[4]}CHF mill'+\
                                    '<br>Raiffeisen Banks: %{customdata[5]}CHF mill'+\
                                    '<br>Reg & Sav Banks: %{customdata[6]}CHF mill<extra></extra>',
                                    colorbar_title="Millions USD",
                                    marker_line_width=1))


swissmap.update_layout(title_text = title,
                  title_x=0.5,
                  width=800,
                  height=500,
                  margin={"r":0,"t":30,"l":30,"b":30},
                  #paper_bgcolor="LightSteelBlue",
                  coloraxis_colorscale='Tealgrn',
                  mapbox=dict(style='carto-positron',
                              zoom=6.5, 
                              center = {"lat": 46.8181877 , "lon":8.2275124 },
                              ))


bar_fig = px.bar(mor_Cant, x="Cantons", y=["BigBanks", "CantonalBanks", "Raiffeisen", "RegAndSavBanks"],
                 title="Mortgages per type bank Switzerland",
                 animation_frame="Date",
                 labels={"value": "CHF mill", "variable": "Type of Bank"})
bar_fig.update_yaxes(range=[0, 183000])
bar_fig.update_layout(title_x=0.5, margin={"r":0,"t":30,"l":30,"b":30})



link_picture = "http://"+socket.gethostbyname(socket.gethostname())+"/static/mortgage.png"


fontawesome = 'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/4.7.0/css/font-awesome.min.css'

server = Flask(__name__)
appBeautify = dash.Dash(assets_folder="./static" ,external_stylesheets=[dbc.themes.LUMEN, fontawesome], server=server)


navbar = dbc.Nav(className="nav nav-pills navbar-expand-lg navbar-light bg-ligth", children=[
    ## logo/home
    dbc.NavItem(html.Img(src=link_picture, height="40px")),
    ## about
    dbc.Col(width="auto"),
    dbc.NavItem(html.Div([
        dbc.NavLink("About",href="/", id="about-popover", active=False),
        dbc.Popover(id="about", is_open=False, target="about-popover", children=[
            dbc.PopoverHeader("Try it out!"), dbc.PopoverBody("Choose the different interactive tools and see how the mortgage market evolves")
        ])
    ])),
    ## links
    dbc.DropdownMenu(label="Code", nav=True, children=[
        dbc.DropdownMenuItem([html.I(className="fa fa-github"), "  Github"], href="https://github.com/vinwinter/Production-ready-dash.git", target="_blank")
    ])
])



appBeautify.layout = html.Div(children=[
    #Set headline of the page.
    navbar,
    html.H1('Overview of the Swiss mortgage market',  id="nav-pills", 
            className="table-primary", style = {'text-align':'center', 'height':'50px'}),
    
    #Set the details for dropdown of the line plot
    html.Div([
        html.Br(),
        html.Label(['Compare different bank categories in different canonts:'],style={'font-weight': 'bold', "text-align": "center",'margin-left': '40px'}),
        dcc.Dropdown(id='Cantons',
            options=[{'label':x, 'value':x} for x in df.Cantons.unique()],
            value='ZH',
            multi=False,
            disabled=False,
            clearable=False,
            searchable=True,
            placeholder='Choose Cuisine...',
            className='form-dropdown',
            style={'width':"50%",'align': 'right','margin-left': '20px'},
            persistence='string',
            persistence_type='memory'),

    ]),
    #Plot the lineplot and mapplot in the same row
    dbc.Row([dbc.Col(children=[html.Br(),html.P("On the right you can find the volume of mortgages for the different type \
    of banks in 2019. Under you can see the development over time. At the bottom you can interactively play with the chart and see how the mortages evolve as a total over time." 
    ,className="table-dark"
    ,style={'margin-left': '40px','color': 'white', 'fontSize': 14,'margin-right': '40px'})
    ,html.Br(),dcc.Graph(id='line_graph',style={'width': '100%', 'height':'80%'}),
    ]),dbc.Col(children=[html.Div([dcc.Graph(id='example-graph',figure=swissmap,style={'width': '48%', 'align': 'right'})
        ]),
                                  ])]),
        
    
    
    #Set the dash core component graph for the automated bar-graph we created
    dcc.Graph(
        id='bar-graph',
        figure=bar_fig
    )
    
])

#Set callback function. When the input of the dropdown we created above changes, 
#the output will aslo change accordingly. 
#In this case the input value is the canton and the values of that canton
@appBeautify.callback(
    Output('line_graph','figure'),
    [Input('Cantons','value')]
)

def build_graph(DropDown):
    dff=df[(df['Cantons']==DropDown)]

    linep = px.line(dff, x="Date", y="Value", color='BANKENGRUPPE')
    linep.update_layout(yaxis={'title':'Volume'},
                      title={'text':'Development of mortage volume',
                      'font':{'size':17},'x':0.5,'xanchor':'center'})
    return linep


@appBeautify.callback(output=Output("about","is_open"), inputs=[Input("about-popover","n_clicks")], state=[State("about","is_open")])
def about_popover(n, is_open):
    if n:
        return not is_open
    return is_open

@appBeautify.callback(output=Output("about-popover","active"), inputs=[Input("about-popover","n_clicks")], state=[State("about-popover","active")])
def about_active(n, active):
    if n:
        return not active
    return active


if __name__ == '__main__':
    appBeautify.run_server(debug=True)



















