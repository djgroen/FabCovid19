import pandas as pd
import plotly.graph_objects as go
import sys

if __name__ == "__main__":
  needs_name = sys.argv[1]

  df = pd.read_csv(sys.argv[1])

  fig = go.Figure()

  for l in ["office","school","leisure"]:
    fig.add_trace(go.Scatter(x = df['age'], y = df[l], name=l))

  fig.update_layout(title='Needs',
                   plot_bgcolor='rgb(230, 230,230)',
                   showlegend=True, xaxis_title="age [years]", yaxis_title="time / week [minutes]", legend_title="location type",)

  fig.show()


  fig = go.Figure()

  for l in ["shopping","supermarket","park","hospital"]:
    fig.add_trace(go.Scatter(x = df['age'], y = df[l], name=l))

  fig.update_layout(title='Needs',
                   plot_bgcolor='rgb(230, 230,230)',
                   showlegend=True, xaxis_title="age [years]", yaxis_title="time / week [minutes]", legend_title="location type",)

  fig.show()
