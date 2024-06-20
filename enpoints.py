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

def endpoint_dataframe(columns, ascendings):
    data = custom_sort(columns, ascendings)
    return data.to_dict(orient='records')