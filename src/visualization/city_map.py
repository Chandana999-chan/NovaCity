import plotly.graph_objects as go


def create_city_map(graph):

    fig = go.Figure()

    for u, v, data in graph.edges(data=True):

        x1, y1 = graph.nodes[u]["pos"]
        x2, y2 = graph.nodes[v]["pos"]

        closed = data.get("closed", False)

        fig.add_trace(go.Scatter(
            x=[x1, x2],
            y=[y1, y2],
            mode="lines",
            line=dict(
                color="red" if closed else "#38bdf8",
                width=4 if closed else 2
            ),
            hoverinfo="text",
            text=f"{u} - {v}",
            showlegend=False
        ))

    node_x = []
    node_y = []
    node_names = []

    for node, data in graph.nodes(data=True):
        x, y = data["pos"]

        node_x.append(x)
        node_y.append(y)
        node_names.append(node)

    fig.add_trace(go.Scatter(
        x=node_x,
        y=node_y,
        mode="markers+text",
        text=node_names,
        textposition="top center",
        marker=dict(
            size=17,
            color="#22c55e",
            line=dict(width=2, color="white")
        ),
        name="City Locations"
    ))

    fig.update_layout(
        title="NOVACITY | LIVE ROAD NETWORK",
        template="plotly_dark",
        height=550,
        showlegend=False,
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        plot_bgcolor="#0b1220",
        paper_bgcolor="#0b1220"
    )

    return fig