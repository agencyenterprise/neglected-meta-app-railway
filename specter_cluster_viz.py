from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
import pandas as pd
import plotly.graph_objs as go
import textwrap



def create_clusters(df, n_clusters, embeddings):
    kmeans = KMeans(n_clusters=n_clusters, random_state=0)
    kmeans.fit(embeddings.detach().numpy())
    cluster_labels = kmeans.predict(embeddings.detach().numpy())
    df["cluster_labels"] = cluster_labels
    return df


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
    return viz_df

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
def create_viz(df, n_clusters, embeddings):
    df = create_clusters(df, n_clusters, embeddings)
    viz_df = get_viz_df(df, embeddings)
    # Define the trace (scatter plot)
    trace = go.Scatter(
        x=viz_df["pca1"],
        y=viz_df["pca2"],
        mode="markers",  # Set marker mode for data points
        marker=dict(
            color=viz_df["cluster_labels"], size=10
        ),  # Use cluster_labels for color
        text=viz_df["wrapped_text"],  # Set hover text data (cluster labels),
        hovertemplate="Concept: %{text}<br>Cluster: %{marker.color}<br>PC1: %{x}<br>PC2: %{y}",  # Update hover text content
    )
    # Define the layout (customize axis titles and colors)
    layout = go.Layout(
        # xaxis=dict(title="PC1", tickfont=dict(color="blue"), showgrid=True),
        # yaxis=dict(title="PC2", tickfont=dict(color="green"), showgrid=True),
        # plot_bgcolor="white",  # Set background color (optional)
    )

    # Create the figure and add the trace
    fig = go.Figure(data=[trace], layout=layout)
    return fig, viz_df
