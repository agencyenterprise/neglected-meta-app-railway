from sentence_transformers import SentenceTransformer, util
import numpy as np
import pandas as pd
from typing import List, Optional
def get_author_style_embedding(author_name_list: List, df: pd.DataFrame, style_embeddings: np.ndarray):
    author_df = df.explode("authors")
    author_df = author_df[author_df["authors"].isin(author_name_list)]
    if author_df.shape[0] == 0:
        raise RuntimeWarning(f"No articles for this author {author_name_list}")
    article_ids = set(author_df["articles_id"].to_list())
    authorindices = np.where(df["articles_id"].isin(article_ids))[0]
    author_embeddings = style_embeddings[authorindices]
    author_average_embedding = np.sum(author_embeddings, axis=0)/author_embeddings.shape[0]
    return author_average_embedding

def get_author_similarity_score(author_name_list: List[str], df: pd.DataFrame, style_embeddings: np.ndarray):
    """_summary_

    Args:
        author_name_list (List): _description_
        df (pd.DataFrame): _description_
        style_embeddings (np.ndarray): _description_
    """
    author_average_embedding = get_author_style_embedding(author_name_list, df, style_embeddings)
    return util.cos_sim(author_average_embedding, style_embeddings)[0]

def batch_author_similarity_score(author_name_batch: List[List[str]], df: pd.DataFrame,
                                  style_embeddings: np.ndarray,
                                  concept_embedding: Optional[np.ndarray] = None):
    """_summary_

    Args:
        author_name_batch (_type_): _description_
        df (pd.DataFrame): _description_
        style_embeddings (np.ndarray): _description_
    """
    author_embeddings = [get_author_style_embedding(a, df, style_embeddings)
                         for a in author_name_batch]
    if concept_embedding is not None:
        scores = util.cos_sim(np.vstack(author_embeddings), concept_embedding)
    else:
        scores = util.cos_sim(np.vstack(author_embeddings), style_embeddings)
    return scores

def compare_authors(author_pair: List[str], df: pd.DataFrame, style_embeddings: np.ndarray):
    """Creates pairwise score for the style of two selected authors.

    Args:
        author_pair (List[str]): _description_
        df (pd.DataFrame): _description_
        style_embeddings (np.ndarray): _description_
    """
    e_author_1, e_author_2 = [get_author_style_embedding(a, df, style_embeddings) for a in author_pair]
    return util.cos_sim(e_author_1, e_author_2)

def average_article_embeddings(article_ids: List[List[str]], df: pd.DataFrame, style_embeddings):
    idxs = np.where(df["articles_id"].isin(article_ids))[0]
    embeddings = style_embeddings[idxs]
    return np.sum(embeddings, axis=0)/embeddings.shape[0]

def compare_articles(article_ids: List[List[str]], df: pd.DataFrame, style_embeddings):
    idxs = np.where(df["articles_id"].isin(article_ids))[0]
    embeddings = style_embeddings[idxs]
    return util.cos_sim(embeddings[0], embeddings[1])
