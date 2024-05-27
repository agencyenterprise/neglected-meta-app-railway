from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
import pandas as pd
import plotly.graph_objs as go
import textwrap
from scipy.spatial import ConvexHull
import numpy as np
import colorsys
import random

def create_clusters(df, n_clusters, embeddings):
    kmeans = KMeans(n_clusters=n_clusters, random_state=0)
    kmeans.fit(embeddings.detach().numpy())
    cluster_labels = kmeans.predict(embeddings.detach().numpy())
    df["cluster_labels"] = cluster_labels
    centers = kmeans.cluster_centers_
    return centers, df


def get_viz_df(df, embeddings):
    pca = PCA(n_components=2)
    principalComponents = pca.fit_transform(embeddings.detach().numpy())
    pca_df = pd.DataFrame(principalComponents, columns=["pca1", "pca2"])
    viz_df = pd.concat([df, pca_df], axis=1).fillna("")
    viz_df["wrapped_definition"] = viz_df["definition"].apply(
        lambda x: textwrap.fill(x, width=50, break_long_words=False)
    )
    wrapper = textwrap.TextWrapper(width=10)
    viz_df["wrapped_text"] = viz_df["text"].apply(lambda x: "<br>".join(wrapper.wrap(x)))
    return viz_df, pca

def aggregate_by_cluster(df):
    scores = [
    "Eliezer Yudkowsky Similarity Score",
    "beren Similarity Score",
    "habryka Similarity Score",
    "gwern Similarity Score",
    "Kaj_Sotala Similarity Score",
    "Scott Alexander Similarity Score",
    "Wei Dai Similarity Score",
    "Zvi Similarity Score",
    "lukeprog Similarity Score",
    "NancyLebovitz Similarity Score",
    "gjm Similarity Score",
    "Vladimir_Nesov Similarity Score",
    "Front Page Similarity",
    "karma_total",
    "count_articles",
    "comments_total",
    "lr_stats",
    "lr_stats_concepts_articles",
    "qda_stats",
    "qda_stats_concepts_articles",
    "rf_stats",
    "rf_stats_concepts_articles",
    "n_words",
    "ngram_absolute_count"
    ]
    cluster_scores = df.groupby("cluster_labels")[scores].mean()
    
    return cluster_scores

def get_traces(df, cluster_choice):
    traces = []
    # colors = ['rgb(255,0,0)', 'rgb(0,255,0)', 'rgb(0,0,255)']  # Red, Green, Blue
    colors = ['rgb' + str(tuple(int(255 * x) for x in colorsys.hsv_to_rgb(random.random(), random.uniform(0.5, 1.0), random.uniform(0.5, 1.0)))) for _ in df["cluster_labels"].unique()]

    colorscale = [[i / (len(colors) - 1), colors[i]] for i in range(len(colors))]
    for i in df["cluster_labels"].unique():
        cluster = df[df["cluster_labels"] == i][["pca1", "pca2"]].values
        if cluster.shape[0] < 3:
            hull_points = cluster
        else:
            hull = ConvexHull(cluster)
            hull_points = cluster[hull.vertices]
            hull_points = np.append(hull_points, [hull_points[0]], axis=0)  # Append first point to close the hull
        colorscale = [[i / (len(colors) - 1), colors[i]] for i in range(len(colors))]
        trace_hull = go.Scatter(
            x=hull_points[:, 0],
            y=hull_points[:, 1],
            marker=dict(
            colorscale=colorscale,
            cmin=0,
            cmax=len(colors) - 1
        ),
            mode="lines",
            showlegend=False,
        )
        traces.append(trace_hull)
        # Add scatter plot with the same color scale
    
    df["shape"] = df["cluster_labels"].apply(lambda x: "star" if x == cluster_choice else "circle")
    # df_cir
    scatter_trace = go.Scatter(
        x=df["pca1"],
        y=df["pca2"],
        mode="markers",  # Set marker mode for data points
        marker=dict(
            color=df["cluster_labels"],
            colorscale=colorscale,
            cmin=0,
            cmax=len(colors) - 1,
            size=10,
            symbol=df["shape"]
        ),  # Use cluster_labels for color
        text=df["wrapped_text"],  # Set hover text data (cluster labels),
        hovertemplate="Concept: %{text}<br>Cluster: %{marker.color}<br>PC1: %{x}<br>PC2: %{y}",  # Update hover text content
    )
    traces.append(scatter_trace)
    return traces

def create_viz(df, n_clusters, embeddings, cluster_choice, selected_content=None):
    centers, df = create_clusters(df, n_clusters, embeddings)
    viz_df, pca = get_viz_df(df, embeddings)
    # Define the trace (scatter plot)
    # trace = go.Scatter(
    #     x=viz_df["pca1"],
    #     y=viz_df["pca2"],
    #     mode="markers",  # Set marker mode for data points
    #     marker=dict(
    #         color=viz_df["cluster_labels"], size=10
    #     ),  # Use cluster_labels for color
    #     text=viz_df["wrapped_text"],  # Set hover text data (cluster labels),
    #     hovertemplate="Concept: %{text}<br>Cluster: %{marker.color}<br>PC1: %{x}<br>PC2: %{y}",  # Update hover text content
    # )
    if selected_content is not None:
        cluster_choice = viz_df[viz_df["text"] ==selected_content]["cluster_labels"].unique()[0]
    traces = get_traces(viz_df, cluster_choice)
    return traces, viz_df, cluster_choice

