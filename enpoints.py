import pandas as pd
from utils import quantile_transformation, prepare_concept_for_request
import streamlit as st
from streamlit_agraph import agraph, Node, Edge, Config, ConfigBuilder
from specter_cluster_viz import create_viz
from cav_calc import compare_authors, batch_author_similarity_score
from sentence_transformers import util
import torch
import json
import numpy as np
import os
from Google import create_and_download_files
from knowledge_graph_visuals import build_graph


create_and_download_files()
specter_embeddings = torch.load("app_files/specter_embeddings.pt")
style_embeddings = torch.load("app_files/style_embeddings.pt")
top_100_embeddings = torch.load("app_files/top_100_embeddings.pt")

app_info: pd.DataFrame = pd.read_json("app_files/app_info_enhanced.jsonl", lines=True)
comments = pd.read_parquet("app_files/lw_comments.parquet")
df = pd.read_parquet("app_files/lw_data.parquet")
user_df = pd.read_parquet("app_files/users.parquet")
df.fillna("", inplace=True)
df["articles_id"] = df.index

with open("app_files/authors.json", "r") as f:
    author_name_list = json.load(f)

with open("app_files/titles.json", "r") as f:
    article_names = json.load(f)

STANDARD_SIZE = 25
MIN_SIZE = 10
df["dot_size"] = (
    MIN_SIZE
    + (df["karma"] - df["karma"].min()) / (df["karma"].max() - df["karma"].min()) * 90
)
# df["dot_size"] = (df["karma"] - df["karma"].min()) / (
#     df["karma"].max() - df["karma"].min()
# ) * STANDARD_SIZE + 10
user_df["dot_size"] = (user_df["karma"] - user_df["karma"].min()) / (
    user_df["karma"].max() - user_df["karma"].min()
) * 90 + MIN_SIZE


def custom_sort(columns, ascendings, head_n=5, truncate=False):
    show_columns = list(
        set(
            ["text", "urls", "definition", "comments_total", "karma_total", "lr_stats"]
            + columns
        )
    )
    if truncate:
        return app_info.sort_values(columns, ascending=ascendings).head(head_n)[
            show_columns
        ]
    return app_info.sort_values(columns, ascending=ascendings)[show_columns]



###################################################################################################
###################################################################################################
###################################################################################################
###################################################################################################
###################################################################################################

def convert_ndarrays_to_lists(obj):
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, dict):
        return {k: convert_ndarrays_to_lists(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_ndarrays_to_lists(i) for i in obj]
    else:
        return obj

def get_raw_graph(df, comments, post_id, user_df, d=2):
    return build_graph(df, comments, post_id, user_df, depth=d)

###################################################################################################
###################################################################################################
###################################################################################################
###################################################################################################
###################################################################################################

def endpoint_dataframe(columns, ascendings):
    data = custom_sort(columns, ascendings)
    return data.to_dict(orient='records')


def endpoint_similarity_score(article_list, compared_authors):
    default_authors = [
        "Eliezer Yudkowsky",
        "beren",
        "habryka",
        "gwern",
        "Kaj_Sotala",
        "Scott Alexander",
        "Wei Dai",
        "Zvi",
        "lukeprog",
        "NancyLebovitz",
        "gjm",
        "Vladimir_Nesov",
    ]

    labels = [a for a in compared_authors]
    labels.append("Top 10 Authors")

    compared_authors = [[a] for a in compared_authors] + [
        [a for a in default_authors if a != "beren"]
    ]

    article_idx = np.where(df["title"].isin(article_list))[0]
 
    sim_scores_tensor, top_100_score = batch_author_similarity_score(
        [a for a in compared_authors],
        df,
        style_embeddings,
        top_100_embedding=top_100_embeddings,
    )

    sim_scores = torch.mean(sim_scores_tensor[:, article_idx].T, axis=0)
    top_100_score = torch.mean(top_100_score)

    output = []

    for label, sim in zip(labels, sim_scores):
        output.append({ 'author': label, 'sim': f"{sim:.2f}" })

    output.append({ 'author': 'Top 100 Authors', 'sim': f"{top_100_score:.2f}" })

    return output


def endpoint_author_similarity_score(author_pair1, author_pair2):
    return compare_authors([author_pair1, author_pair2], df, style_embeddings)[0][0]

def endpoint_specter_clustering(n, cluster_choice, select_by_content):
    fig, df_with_clusters, cluster_choice = create_viz(
        app_info, n, specter_embeddings, cluster_choice, select_by_content
    )

    fig_json = [convert_ndarrays_to_lists(scatter.to_plotly_json()) for scatter in fig]

    df_cluster = df_with_clusters[
        df_with_clusters["cluster_labels"] == cluster_choice
    ].reset_index(drop=True)

    df_cluster_output = [];

    for i, row in df_cluster.iterrows():
            
            articles = []

            row_titles = df[df["articles_id"].isin(row["article_ids"])]["title"].to_list()
            for article, url in zip(row_titles, row["urls"]):
                articles.append({
                    'article': article,
                    'url': url,
                })

            df_cluster_output.append({
                'index': i,
                'text': row["text"],
                'definition': row["definition"],
                'comments_total': row["comments_total"],
                'karma_total': row["karma_total"],
                'lr_stats': row["lr_stats"],
                'articles': articles,
            })

    return {
        'fig': fig_json,
        'contents': df_cluster_output,
    }


def endpoint_connected_posts(a_name, depth):
    post_id = df[df["title"] == a_name]["_id"].values[0]

    raw_nodes, raw_edges = get_raw_graph(df, comments, post_id, user_df, d=depth)

    return {
        'nodes': raw_nodes,
        'edges': raw_edges,
    }
