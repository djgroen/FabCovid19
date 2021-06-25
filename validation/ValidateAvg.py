import plotly.graph_objects as go
import plotly as py
import pandas as pd
import sys
import os
import pathlib
from datetime import datetime
from datetime import timedelta
from plotly.subplots import make_subplots
from pprint import pprint

from plugins.FabCovid19.FabCovid19 import *


@task
@load_plugin_env_vars("FabCovid19")
def covid19_postprocessing(output_dir,
                           output_file="out.csv"):
    """
    run a post-processing on input folder
    Example:

    fab localhost covid19_postprocessing:results_dir=brent_eagle_hidalgo_1
    """

    if env.machine_name != "localhost":
        raise RuntimeError(
            "covid19_postprocessing can not be executed on remote machine, "
            "please use localhost instead "
        )

    Start_Date = env.facs_validation["Start_Date"]
    End_Date = env.facs_validation["End_Date"]

    # check if the output_dir is exists.
    results_dir = os.path.join(env.local_results, output_dir)
    if not os.path.isdir(results_dir):
        raise RuntimeError(
            "\n\nThe input output_dir = {} does NOT exists in "
            "{} direcotry !!!\n"
            "Myabe you did not fetch the results from remote mahcine."
            .format(output_dir, env.local_results)
        )

    # finding the name of borough
    for path in pathlib.Path(results_dir).rglob("*_buildings.csv"):
        borough = os.path.basename(path).split("_buildings.csv")[0]
        # there is no need to contirnue since we already
        # found the name of borough
        break

    # finding admissions.csv file
    for path in pathlib.Path(results_dir).rglob("admissions.csv"):
        adm_csv_fname = str(path)
        # adm_csv_fname = os.path.join(
        #     "/home/hamid/Downloads/moo/FabSim3/results/brent_localhost_derek/RUNS/uk-forecast-0-0.475/validation_data",
        #     "admissions.csv"
        # )
        # since the output_dir contains a single or ensebmle runs for a same
        # borough, in all sub-directories in RUN, the admissions.csv file is
        # replicated
        break

    results = {}
    for dirpath, dirnames, filenames in os.walk(results_dir):
        for filename in [f for f in filenames if f == output_file]:

            try:
                replica = os.path.basename(dirpath).split("_")[1]
            except IndexError:
                pass
            rundir = os.path.basename(dirpath).split("_")[0]
            ci_multiplier = rundir.rsplit("-", 2)[2]
            transition_mode = rundir.rsplit("-", 2)[1]
            transition_scenario = rundir.rsplit("-", 2)[0]

            borough_key = "{}-{}-{}".format(
                borough, transition_scenario, transition_mode
            )
            if borough_key not in results:
                results.update(
                    {
                        borough_key:
                        {
                            "borough_name": borough,
                            "transition_mode": transition_mode,
                            "transition_scenario": transition_scenario,
                            "df_name": [],
                            "df_list": [],
                        }
                    }
                )

            df = pd.read_csv(
                os.path.join(dirpath, output_file),
                usecols=["num hospitalisations today", "num infections today"]
            )
            if "replica" in locals():
                columns = [x + "-" + replica for x in df.columns]
            else:
                columns = [x for x in df.columns]
            df.columns = columns
            for column in df:
                results[borough_key]["df_name"].append(column)
            results[borough_key]["df_list"].append(df)
            # ci_multiplier=rundir.split("-")

    for borough_key in results.keys():
        borough_name = results[borough_key]["borough_name"]
        transition_mode = results[borough_key]["transition_mode"]
        transition_scenario = results[borough_key]["transition_scenario"]
        df = pd.concat(results[borough_key]["df_list"],
                       axis=1, ignore_index=True
                       )
        df.columns = results[borough_key]["df_name"]

        columns = df.columns

        df["ICU new sim-min"] = df[
            [c for c in columns if "num hospitalisations today-" in c]
        ].min(axis=1)
        df["ICU new sim-avg"] = df[
            [c for c in columns if "num hospitalisations today-" in c]
        ].mean(axis=1)
        df["ICU new sim-max"] = df[
            [c for c in columns if "num hospitalisations today-" in c]
        ].max(axis=1)

        df["ICU new sim"] = df["ICU new sim-avg"]

        df["num hospitalisations today-min"] = df["ICU new sim-min"].rolling(
            4, min_periods=1).sum().shift(-4)
        df["num hospitalisations today-avg"] = df["ICU new sim-avg"].rolling(
            4, min_periods=1).sum().shift(-4)
        df["num hospitalisations today-max"] = df["ICU new sim-max"].rolling(
            4, min_periods=1).sum().shift(-4)

        df["num infections today-min"] = df[
            [c for c in columns if "num infections today-" in c]].min(axis=1)
        df["num infections today-avg"] = df[
            [c for c in columns if "num infections today-" in c]].mean(axis=1)
        df["num infections today-max"] = df[
            [c for c in columns if "num infections today-" in c]].max(axis=1)

        df["hosp new data"] = 0

        validation = pd.read_csv(adm_csv_fname, delimiter=',')
        for index, d in validation.iterrows():
            day = int(subtract_dates(d["date"], Start_Date))
            if day >= 0 and day < len(df['hosp new data']):
                df['hosp new data'][day] = int(d['admissions'])

        title = "Location: {} Scenario: {} Mode: {}".format(
                borough_name, transition_scenario, transition_mode
        )

        html_file = os.path.join(
            results_dir,
            "{}-{}-{}.html".format(borough_name, transition_scenario,
                                   transition_mode)
        )
        png_file = os.path.join(
            results_dir,
            "{}-{}-{}.png".format(borough_name, transition_scenario,
                                  transition_mode)
        )
        plot(df, Start_Date, adm_csv_fname, title, html_file, png_file)


def subtract_dates(date1, Start_Date, date_format="%d/%m/%Y"):
    """
    Takes two dates %m/%d/%Y format. Returns date1 - date2, measured in days.
    28/04/2021
    %d-%m-%Y
    2020-02-28
    %Y-%m-%d
    """
    a = datetime.strptime(date1, date_format)
    b = datetime.strptime(Start_Date, date_format)
    delta = a - b
    return delta.days


def getline(name):
    line = dict()
    fill = dict()
    if "-62" in name:
        line.update({"dash": "solid"})
    elif "-77" in name:
        line.update({"dash": "dash"})
    elif "-93" in name:
        line.update({"dash": "dot"})

    if "all" in name:
        line.update({"color": "red"})
        fill.update({"fillcolor": "rgba(231,107,243,0.2)",
                     "line_color": "rgba(231,107,243,0.2)"})
    elif "leisure" in name:
        line.update({"color": "blue"})
        fill.update({"fillcolor": "rgba(0,0,255,0.2)",
                     "line_color": "rgba(0,0,255,0.2)"})
    elif "schools" in name:
        line.update({"color": "green"})
        fill.update({"fillcolor": "rgba(0,102,0,0.2)",
                     "line_color": "rgba(0,102,0,0.2)"})
    elif "shopping" in name:
        line.update({"color": "orange"})
        fill.update({"fillcolor": "rgba(255,153,0,0.2)",
                     "line_color": "rgba(255,153,0,0.2)"})
    elif "work100" in name:
        line.update({"color": "red"})
        fill.update({"fillcolor": "rgba(231,107,243,0.2)",
                     "line_color": "rgba(231,107,243,0.2)"})
    elif "work75" in name:
        line.update({"color": "blue"})
        fill.update({"fillcolor": "rgba(0,0,255,0.2)",
                     "line_color": "rgba(0,0,255,0.2)"})
    elif "work50" in name:
        line.update({"color": "green"})
        fill.update({"fillcolor": "rgba(0,102,0,0.1)",
                     "line_color": "rgba(0,102,0,0.1)"})
    elif "num infections today" in name:
        line.update({"color": "red"})
        fill.update({"fillcolor": "rgba(231,107,243,0.2)",
                     "line_color": "rgba(231,107,243,0.2)"})
    elif "num hospitalisations today" in name:
        line.update({"color": "blue"})
        fill.update({"fillcolor": "rgba(0,0,255,0.2)",
                     "line_color": "rgba(0,0,255,0.2)"})
    else:
        line.update({"color": "black"})
        fill.update({"fillcolor": "rgba(187,187,187,0.2)",
                     "line_color": "rgba(187,187,187,0.2)"})
    return (line, fill)


def plot(df, Start_Date, adm_csv_fname, title, html_file, png_file):
    df["#time"] = pd.date_range(start=Start_Date, periods=len(df))
    print(df["#time"])
    step0 = datetime.strptime("2020-12-02", "%Y-%m-%d")
    step1 = datetime.strptime("2020-12-16", "%Y-%m-%d")
    step2 = datetime.strptime("2020-12-20", "%Y-%m-%d")

    # Add traces
    fig = make_subplots(
        rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.01
    )
    line = getline("num infections today")[0]
    fill = getline("num infections today")[1]

    fig.add_trace(
        go.Scatter(x=df["#time"],
                   y=df["num infections today-avg"],
                   mode="lines+markers",
                   name="# of new infections (sim)",
                   line=line,
                   line_shape="spline",
                   legendgroup="group1"),
        row=1,
        col=1
    )
    fig.add_trace(
        go.Scatter(x=df["#time"],
                   y=df["num infections today-min"],
                   name="# of new infections (sim)",
                   fillcolor=fill.get("fillcolor"),
                   line_color=fill.get("line_color"),
                   fill="tonexty",
                   showlegend=False,
                   legendgroup="group1"),
        row=1,
        col=1
    )
    fig.add_trace(
        go.Scatter(x=df["#time"],
                   y=df["num infections today-max"],
                   name="# of new infections (sim)",
                   fillcolor=fill.get("fillcolor"),
                   line_color=fill.get("line_color"),
                   fill="tonexty",
                   showlegend=False,
                   legendgroup="group1"),
        row=1,
        col=1
    )

    line = getline("num hospitalisations today")[0]
    fill = getline("num hospitalisations today")[1]
    fig.add_trace(
        go.Scatter(x=df["#time"],
                   y=df["num hospitalisations today-avg"],
                   mode="lines+markers",
                   name="# of new hospitalisations (sim)",
                   line=line,
                   line_shape="spline",
                   legendgroup="group2"),
        row=2,
        col=1
    )
    fig.add_trace(
        go.Scatter(x=df["#time"],
                   y=df["num hospitalisations today-min"],
                   name="# of new hospitalisations (sim)",
                   fillcolor=fill.get("fillcolor"),
                   line_color=fill.get("line_color"),
                   fill="tonexty",
                   showlegend=False,
                   legendgroup="group2"),
        row=2,
        col=1
    )
    fig.add_trace(
        go.Scatter(x=df["#time"],
                   y=df["num hospitalisations today-max"],
                   name="# of new hospitalisations (sim)",
                   fillcolor=fill.get("fillcolor"),
                   line_color=fill.get("line_color"),
                   fill="tonexty",
                   showlegend=False,
                   legendgroup="group2"),
        row=2,
        col=1
    )
    fig.add_trace(
        go.Scatter(x=df["#time"],
                   y=df["hosp new data"],
                   mode="lines",
                   name="# of new hospitalisations (data:" +
                   adm_csv_fname + ")",
                   line=dict(color="green")),
        row=2,
        col=1
    )

    fig.update_xaxes(
        showline=True, linewidth=1, linecolor="black", zeroline=True,
        zerolinewidth=2, zerolinecolor="black", showgrid=False,
        mirror=True, dtick="M1"
    )
    fig.update_yaxes(
        showline=True, linewidth=1, linecolor="black", zeroline=True,
        zerolinewidth=2, zerolinecolor="black", showgrid=False,
        mirror=True
    )

    fig.update_traces(
        mode="lines+markers", marker=dict(size=1, colorscale="Plotly3")
    )
    fig.update_layout(
        legend_orientation="h",
        title={
            "text": title,
            "y": 0.9,
            "x": 0.5,
            "xanchor": "center",
            "yanchor": "top"},
        legend=dict(x=0, y=-0.2),
        autosize=True,
        width=1200,
        height=800,
        shapes=[
            dict(type="rect", xref="x", yref="paper", x0=step0, y0=0,
                 x1=step0 + timedelta(days=1), y1=1,
                 fillcolor="salmon", opacity=1, layer="below", line_width=0, ),
            dict(type="rect", xref="x", yref="paper", x0=step1, y0=0,
                 x1=step1 + timedelta(days=1), y1=1,
                 fillcolor="salmon", opacity=1, layer="below", line_width=0, ),
            dict(type="rect", xref="x", yref="paper", x0=step2, y0=0,
                 x1=step2 + timedelta(days=1), y1=1,
                 fillcolor="salmon", opacity=1, layer="below", line_width=0, )
        ]
    )

    py.offline.plot(fig, filename=html_file)

    # fig.write_image(png_file)
