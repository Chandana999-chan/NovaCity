
import plotly.graph_objects as go


def get_coordinates(data):
    """Support both sample-city and NovaCity node formats."""

    if "pos" in data:
        return data["pos"]

    return data["x"], data["y"]


def create_city_map(graph):

    fig = go.Figure()

    # Draw roads
    for u, v, data in graph.edges(data=True):

        x1, y1 = get_coordinates(graph.nodes[u])
        x2, y2 = get_coordinates(graph.nodes[v])

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

    # Draw junctions
    node_x = []
    node_y = []
    node_names = []

    for node, data in graph.nodes(data=True):

        x, y = get_coordinates(data)

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
        name="City Junctions"
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
