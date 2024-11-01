import json
import os
import subprocess
import sys
from datetime import datetime, timezone

import numpy as np
import pandas as pd
import torch
from streamlit_agraph import Config, ConfigBuilder, Edge, Node, agraph

from cav_calc import batch_author_similarity_score, compare_authors
from Google import create_and_download_files
from knowledge_graph_visuals import build_graph
from specter_cluster_viz import create_viz
from utils import (get_connected_comments_from_db, get_connected_posts_from_db,
                   save_connected_posts_to_db)


def start_population_script():
  try:
      subprocess.Popen([sys.executable, 'run_population.py'])
      print("Population process started.")
  except Exception as e:
      print(f"Failed to start population process: {e}")

file_date = create_and_download_files()

start_population_script()
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

def calculate_dot_sizes(df: pd.DataFrame, min_size: float = 15, max_size: float = 150) -> pd.DataFrame:
    def linear_scale(values):
        # Convert to numeric, replacing non-numeric values with min_size
        numeric_values = pd.to_numeric(values, errors='coerce').fillna(0)
        
        # If all values are 0 or the min equals max, return min_size
        if numeric_values.max() == numeric_values.min() or numeric_values.max() == 0:
            return np.full(len(values), min_size)
            
        # Calculate scaled values
        return (min_size + (numeric_values - numeric_values.min()) / 
                (numeric_values.max() - numeric_values.min()) * (max_size - min_size))

    # Apply standard scaling for karma and upvotes
    df["dot_size_karma"] = linear_scale(df["karma"])
    df["dot_size_upvotes"] = linear_scale(df["upvoteCount"])
    
    # Enhanced scaling for comments
    comment_values = pd.to_numeric(df["commentCount"], errors='coerce').fillna(0)
    
    # Using square root scaling for better distribution
    sqrt_values = np.sqrt(comment_values)
    max_sqrt = sqrt_values.max()
    
    # Scale the square root values
    df["dot_size_comments"] = min_size + (sqrt_values / max_sqrt) * (max_size - min_size) * 1.2
    
    # Ensure minimum size for zero comments
    df["dot_size_comments"] = df["dot_size_comments"].clip(lower=min_size)

    return df

def get_raw_graph(df: pd.DataFrame, comments: pd.DataFrame, post_id: str, user_df: pd.DataFrame, d: int = 2) -> tuple[list, list]:
    df = calculate_dot_sizes(df)

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
        # "NancyLebovitz",
        "gjm",
        "Vladimir_Nesov",
    ]

    labels = [a for a in compared_authors]
    labels.append("Top 10 Authors")

    compared_authors = [[a] for a in compared_authors] + [
        [a for a in default_authors if a != "beren"]
    ]

    article_idx = np.where(df["title"].str.strip().isin(article_list))[0]
 
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
        output.append({ 'author': label, 'score': f"{sim:.2f}" })

    output.append({ 'author': 'Top 100 Authors', 'score': f"{top_100_score:.2f}" })

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


def endpoint_connected_posts(a_name, depth, population=False):
    # Try to get the result from database
    db_result = get_connected_posts_from_db(a_name, depth)
    
    # Check if db_result exists and has required data
    if db_result and 'updated_at' in db_result:
        # Convert to date for comparison, handling both string and datetime inputs
        db_date = (db_result['updated_at'].date() 
                  if isinstance(db_result['updated_at'], datetime) 
                  else datetime.strptime(db_result['updated_at'], "%Y-%m-%d %H:%M:%S").date())
        current_date = datetime.now(timezone.utc).date()
        
        is_up_to_date = db_date == current_date
        
        if not population or (population and is_up_to_date):
            return db_result

    # If not found in database or data is invalid, compute the result
    filtered = df[df["title"].str.strip() == a_name]

    if filtered.empty:
        return {
            'nodes': [],
            'edges': [],
            'updated_at': datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        }

    post_id = filtered["_id"].values[0]
    raw_nodes, raw_edges = get_raw_graph(df, comments, post_id, user_df, d=depth)

    result = {
        'nodes': raw_nodes,
        'edges': raw_edges,
    }

    # Save the result to the database
    save_connected_posts_to_db(a_name, depth, result)

    # Return only post nodes and edges
    return {
        'nodes': [node for node in raw_nodes if node['type'] == 'post'],
        'edges': raw_edges
    }

def endpoint_connected_comments(a_name, depth):
    # Try to get the result from database
    db_result = get_connected_comments_from_db(a_name, depth)
    
    if db_result:
        return db_result

    # If not found in database, compute the result
    filtered = df[df["title"].str.strip() == a_name]

    if not filtered.empty:
        post_id = filtered["_id"].values[0]
    else:
        return {
            'nodes': [],
        }

    raw_nodes, _ = get_raw_graph(df, comments, post_id, user_df, d=depth)

    # Return only comment nodes
    return {
        'nodes': [node for node in raw_nodes if node['type'] == 'comment']
    }

def endpoint_get_authors():
    return author_name_list

def endpoint_get_articles():
    filtered_articles = [article for article in article_names if 'meetup' not in article.lower()]
    
    return filtered_articles

def endpoint_get_content():
    return app_info["text"].to_list()
