import pandas as pd
import numpy as np
import urllib.request
import zipfile
import random
import itertools
import math
import shapefile
from shapely.geometry import Polygon
from descartes.patch import PolygonPatch
import matplotlib as mpl
import matplotlib.pyplot as plt
import dash
import dash_core_components as dcc
import dash_html_components as html
import pandas as pd
from sqlalchemy import create_engine
from plotly.tools import mpl_to_plotly
import plotly.express as px
import plotly.graph_objects as go

mapbox_access_token = 'pk.eyJ1IjoiZGFkZW1vZ2x1IiwiYSI6ImNrNTB6dWxndDA3cDAzc21ycmMzejR5dmMifQ.449W8hBKRSsGCtPgip5GAQ'

px.set_mapbox_access_token('pk.eyJ1IjoiZGFkZW1vZ2x1IiwiYSI6ImNrNTB6dWxndDA3cDAzc21ycmMzejR5dmMifQ.449W8hBKRSsGCtPgip5GAQ')

nyc_database = create_engine('sqlite:///nyc_database2.db')

external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']

app = dash.Dash(__name__, external_stylesheets=external_stylesheets)

def get_lat_lon(sf):
    content = []
    for sr in sf.shapeRecords():
        shape = sr.shape
        rec = sr.record
        loc_id = rec[shp_dic['LocationID']]

        x = (shape.bbox[0]+shape.bbox[2])/2
        y = (shape.bbox[1]+shape.bbox[3])/2

        content.append((loc_id, x, y))
    return pd.DataFrame(content, columns=["LocationID", "longitude", "latitude"])

def currentSet(day):
    if day == 1:
        dframe = pd.read_sql_query('SELECT *\
                                FROM small_record3 \
                                WHERE SUBSTR(tpep_pickup_datetime, 9, 2)=\'02\'\
                                ', nyc_database)
        dframe = dframe.drop(dframe['fare_amount'].idxmin())
        return dframe
    elif day == 2:
        return pd.read_sql_query('SELECT *\
                                FROM small_record3 \
                                WHERE SUBSTR(tpep_pickup_datetime, 9, 2)=\'03\'\
                                ', nyc_database)
    elif day == 3:
        return pd.read_sql_query('SELECT *\
                                FROM small_record3 \
                                WHERE SUBSTR(tpep_pickup_datetime, 9, 2)=\'04\'\
                                ', nyc_database)
    else:
        return pd.read_sql_query('SELECT *\
                                FROM small_record3 \
                                WHERE SUBSTR(tpep_pickup_datetime, 9, 2)=\'05\'\
                                ', nyc_database)


df = pd.read_sql_query('SELECT *\
                        FROM small_record3 \
                        ', nyc_database)

df = df.drop(df['total_amount'].idxmax())

lonlat = pd.read_csv('taxi_zones.csv')

# urllib.request.urlretrieve("https://s3.amazonaws.com/nyc-tlc/misc/taxi_zones.zip", "taxi_zones.zip")
# with zipfile.ZipFile("taxi_zones.zip","r") as zip_ref:
#     zip_ref.extractall("./shape")

df = pd.read_sql_query('SELECT *\
                        FROM small_record3 \
                        ', nyc_database)

sf = shapefile.Reader("shape/taxi_zones.shp")
fields_name = [field[0] for field in sf.fields[1:]]
shp_dic = dict(zip(fields_name, list(range(len(fields_name)))))
attributes = sf.records()
shp_attr = [dict(zip(fields_name, attr)) for attr in attributes]

df_loc = pd.DataFrame(shp_attr).join(get_lat_lon(sf).set_index("LocationID"), on="LocationID")


def currentFrame(day):
    day = '0' + str(day)

    df_pu = pd.read_sql_query('SELECT PULocationID AS LocationID, count(*) AS PUcount \
                            FROM small_record3 \
                            WHERE SUBSTR(tpep_pickup_datetime, 9, 2)=\'{}\'\
                            GROUP BY PULocationID'.format(day), nyc_database)
    df_do = pd.read_sql_query('SELECT DOLocationID AS LocationID, count(*) AS DOcount \
                            FROM small_record3 \
                            WHERE SUBSTR(tpep_pickup_datetime, 9, 2)=\'{}\'\
                            GROUP BY DOLocationID'.format(day), nyc_database)

    template = pd.DataFrame([x for x in range(1,max(df_loc['LocationID'].tolist()))], columns=["LocationID"])
    df_q1 = pd.concat([df_pu, df_do]).join(template.set_index("LocationID"), how = 'outer', on=["LocationID"]).fillna(0) \
                                        .groupby(["LocationID"], as_index=False) \
                                        .agg({'PUcount': 'sum', 'DOcount': 'sum'})\
                                        .sort_values(by=['LocationID'])

    df_q1['TOTALcount'] = df_q1['PUcount'] + df_q1['DOcount']
    loc = lonlat[["LocationID", "zone", "borough", "X", "Y"]]
    df_q1 = df_q1.merge(loc, left_on="LocationID", right_on="LocationID")

    print(df_q1)
    return df_q1

##For the whole data
# df = pd.read_sql_query('SELECT *\
#                         FROM table_record \
#                         WHERE SUBSTR(tpep_pickup_datetime, 9, 2)=\'05\' OR SUBSTR(tpep_pickup_datetime, 9, 2)=\'04\' \
#                         OR SUBSTR(tpep_pickup_datetime, 9, 2)=\'03\' OR SUBSTR(tpep_pickup_datetime, 9, 2)=\'02\' \
#                         ', nyc_database)

available_indicators = ['Pick Up', 'Drop Off']

colors = {
    'background': '#111111',
    'text': '#7FDBFF'
}

app.layout = html.Div([
    html.Div([
        html.Div([
            dcc.Dropdown(
                id='crossfilter-xaxis-column',
                options=[{'label': i, 'value': i} for i in available_indicators],
                value='Pick Up'
            )
        ],
        style={'width': '49%', 'display': 'inline-block','color': colors['text']}),
    ], style={
        'borderBottom': 'thin lightgrey solid',
        'backgroundColor': 'rgb(250, 250, 250)',
        'padding': '10px 5px'
    }),
    html.Div([
        dcc.Graph(id='map-box')
    ], style={'width': '50%', 'display': 'inline-block', 'float': 'right','color': colors['text']}),
    html.Div([
        dcc.Graph(
            id='crossfilter-indicator-scatter',
            hoverData={'points': [{'customdata': 1}]}
        )
    ], style={'width': '49%', 'display': 'inline-block', 'padding': '0 20','color': colors['text']}),
    html.Div(dcc.Slider(
        id='crossfilter-year--slider',
        min=2,
        max=5,
        value=5,
        marks={str(year): 'Jan' + str(year) for year in [2,3,4,5]},
        step=1
    ), style={'width': '49%', 'padding': '0px 0px 0px 20px'}),
    html.Div([
        dcc.Graph(id='x-time-series'),
    ], style={'display': 'block', 'width': '90%', 'margin-left': '10px','color': colors['text']})
])


@app.callback(
    dash.dependencies.Output('crossfilter-indicator-scatter', 'figure'),
    [dash.dependencies.Input('crossfilter-xaxis-column', 'value'),
     dash.dependencies.Input('crossfilter-year--slider', 'value')])
def update_graph(xaxis_column_name,
                 year_value):
    dff = currentSet(year_value)

    return {
        'data': [dict(
            x=dff['trip_distance'],
            y=dff['fare_amount'],
            text=dff['VendorID'],
            customdata=dff['VendorID'],
            mode='markers',
            marker={
                'size': 15,
                'opacity': 0.5,
                'line': {'width': 0.5, 'color': 'white'}
            }
        )],
        'layout': dict(
            title = 'Fare Amount Over Trip Distance',
            margin={'l': 40, 'b': 30, 't': 30, 'r': 0},
            height=450,
            hovermode='closest'
        )
    }


def create_time_series(dff, title):
    return {
        'data': [dict(
            x=dff['tpep_pickup_datetime'],
            y=dff['total_amount'],
            mode='lines+markers'
        )],
        'layout': {
            'title': 'Given Vendor\'s total earned amount over days',
            'height': 225,
            'margin': {'l': 50, 'b': 30, 'r': 10, 't': 50},
            'annotations': [{
                'x': 0, 'y': 0.85, 'xanchor': 'left', 'yanchor': 'bottom',
                'xref': 'paper', 'yref': 'paper', 'showarrow': False,
                 'bgcolor': 'rgba(255, 255, 255, 0.5)',
                'text': title
            }],
        }
    }

@app.callback(
    dash.dependencies.Output('x-time-series', 'figure'),
    [dash.dependencies.Input('crossfilter-indicator-scatter', 'hoverData'),
     dash.dependencies.Input('crossfilter-xaxis-column', 'value')])
def update_y_timeseries(hoverData, xaxis_column_name):
    vendor = hoverData['points'][0]['customdata']
    #print(hoverData['points'])
    dff = df[df['VendorID'] == vendor]
    title = '<b>Vendor ID {}</b>'.format(vendor)
    return create_time_series(dff, title)

@app.callback(
    dash.dependencies.Output('map-box', 'figure'),
    [dash.dependencies.Input('crossfilter-year--slider', 'value'),
    dash.dependencies.Input('crossfilter-xaxis-column', 'value')])
def update_y_timeseries(day,state):
    df_q1 = currentFrame(day)
    if state == 'Pick Up':
        fig = px.scatter_mapbox(df_q1, lat="Y", lon="X", size="PUcount",
              color_continuous_scale=px.colors.cyclical.IceFire, size_max=15, zoom=10)
    else:
        fig = px.scatter_mapbox(df_q1, lat="Y", lon="X", size="DOcount",
              color_continuous_scale=px.colors.cyclical.IceFire, size_max=15, zoom=10)

    return fig


if __name__ == '__main__':
    app.run_server(debug=True)
