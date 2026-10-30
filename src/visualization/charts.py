import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

BG = "#071827"
TEXT = "#dceeff"

def _layout(fig, height=290):
    fig.update_layout(template="plotly_dark",paper_bgcolor=BG,plot_bgcolor=BG,
        font=dict(color=TEXT,family="Inter"),height=height,
        margin=dict(l=18,r=18,t=48,b=18),legend=dict(orientation="h",y=-.2))
    return fig

def create_gauge(title,value,maximum=100,color="#39c8e8"):
    value=max(0,min(float(value or 0),maximum))
    fig=go.Figure(go.Indicator(mode="gauge+number",value=value,
        title={"text":title,"font":{"size":13,"color":"#a9bfd2"}},
        number={"font":{"size":30,"color":"#eff8ff"}},
        gauge={"axis":{"range":[0,maximum],"tickcolor":"#8ca8bf"},
               "bar":{"color":color,"thickness":.25},
               "bgcolor":"rgba(255,255,255,.03)",
               "borderwidth":0,
               "steps":[{"range":[0,maximum*.4],"color":"rgba(255,82,111,.10)"},
                        {"range":[maximum*.4,maximum*.7],"color":"rgba(243,196,94,.10)"},
                        {"range":[maximum*.7,maximum],"color":"rgba(54,214,154,.10)"}]}))
    return _layout(fig,260)

def create_trend_chart(avg_time,event):
    # Illustrative time series anchored to the calculated current average.
    vals=[max(0,avg_time*.88),avg_time*.94,avg_time*.91,avg_time*1.04,
          avg_time*.98,avg_time*1.08,avg_time]
    df=pd.DataFrame({"Interval":["06:00","07:00","08:00","09:00","10:00","11:00","Now"],
                     "Travel time (min)":vals})
    fig=px.line(df,x="Interval",y="Travel time (min)",markers=True,
                title="Commuter travel-time trend",color_discrete_sequence=["#39c8e8"])
    return _layout(fig,285)

def create_mode_share_chart():
    df=pd.DataFrame({"Mode":["Private car","Bus","Walking","Cycling"],"Share":[47,28,15,10]})
    fig=px.pie(df,values="Share",names="Mode",hole=.68,title="Illustrative mobility mode share",
        color_discrete_sequence=["#39c8e8","#a78bfa","#42d6a0","#f3c45e"])
    fig.update_traces(textinfo="percent",textfont_size=10)
    return _layout(fig,285)

def create_road_status_chart(roads):
    counts={"Low":0,"Moderate":0,"High":0,"Severe":0,"Closed":0}
    for road in roads:
        status=road.get("status","Moderate")
        if status in counts: counts[status]+=1
    if sum(counts.values())==0:
        counts["Moderate"]=1
    df=pd.DataFrame({"Status":list(counts),"Road links":list(counts.values())})
    fig=px.bar(df,x="Status",y="Road links",color="Status",
        color_discrete_map={"Low":"#36d69a","Moderate":"#39c8e8","High":"#f3c45e",
                            "Severe":"#ff965e","Closed":"#ff526f"},
        title="Road condition distribution")
    fig.update_layout(showlegend=False)
    return _layout(fig,285)

def create_bar_chart(title,labels,values,color="#39c8e8"):
    df=pd.DataFrame({"Category":labels,"Value":values})
    fig=px.bar(df,x="Category",y="Value",title=title,
               color_discrete_sequence=[color])
    fig.update_traces(marker_line_width=0)
    return _layout(fig,285)

# -----------------------------------------
# BACKWARD COMPATIBILITY WITH EXISTING APP
# -----------------------------------------

def create_comparison_chart(baseline, scenario):

    import pandas as pd
    import plotly.express as px

    df = pd.DataFrame({
        "Scenario": ["Normal City", "Current Scenario"],
        "Average Travel Time": [
            baseline.get("average_travel_time", 0),
            scenario.get("average_travel_time", 0)
        ]
    })

    fig = px.bar(
        df,
        x="Scenario",
        y="Average Travel Time",
        color="Scenario",
        color_discrete_sequence=["#42d6a0", "#ff965e"],
        title="Travel Time Comparison",
        template="plotly_dark"
    )

    return _layout(fig)


def create_congestion_chart(scenario):

    return create_gauge(
        "Road Congestion",
        scenario.get("average_congestion", 0),
        100,
        "#f3c45e"
    )


def create_health_chart(scenario):

    return create_gauge(
        "City Health Score",
        scenario.get("city_health_score", 0),
        100,
        "#42d6a0"
    )


def create_road_status_chart(scenario):

    roads = scenario.get("road_metrics", [])

    if isinstance(roads, dict):
        roads = list(roads.values())

    if not isinstance(roads, list):
        roads = []

    return create_road_status_chart_from_list(roads)


def create_road_status_chart_from_list(roads):

    import pandas as pd
    import plotly.express as px

    statuses = ["Low", "Moderate", "High", "Severe", "Closed"]
    counts = {status: 0 for status in statuses}

    for road in roads:
        if isinstance(road, dict):
            status = road.get("status", "Moderate")
            if status in counts:
                counts[status] += 1

    df = pd.DataFrame({
        "Road Status": statuses,
        "Road Count": [counts[s] for s in statuses]
    })

    fig = px.bar(
        df,
        x="Road Status",
        y="Road Count",
        color="Road Status",
        title="Road Condition Distribution",
        template="plotly_dark"
    )

    return _layout(fig)