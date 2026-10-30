import plotly.express as px
import pandas as pd


def create_comparison_chart(baseline, scenario):

    df = pd.DataFrame({
        "Scenario": ["Normal City", "Disrupted City"],
        "Average Travel Time": [
            baseline["average_travel_time"],
            scenario["average_travel_time"]
        ]
    })

    fig = px.bar(
        df,
        x="Scenario",
        y="Average Travel Time",
        color="Scenario",
        title="Average Commuter Travel Time",
        template="plotly_dark"
    )

    return fig