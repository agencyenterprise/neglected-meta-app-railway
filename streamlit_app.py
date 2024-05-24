import pandas as pd
from tqdm.notebook import tqdm
from utils import quantile_transformation, prepare_concept_for_request
from load import LessWrongData  # , LWCounts
import streamlit as st
from specter_cluster_viz import create_viz
from cav_calc import compare_authors, batch_author_similarity_score
import torch
import json
import numpy as np
import os

tqdm.pandas()
app_info: pd.DataFrame = pd.read_json("app_files/app_info_enhanced.jsonl", lines=True)
lwd = LessWrongData()
df = lwd.lw_df()
df.fillna("", inplace=True)
df["articles_id"] = df.index
specter_embeddings = torch.load("app_files/specter_embeddings.pt")
style_embeddings = torch.load("app_files/style_embeddings.pt")
with open("app_files/authors.json", "r") as f:
    author_name_list = json.load(f)
with open("app_files/titles.json", "r") as f:
    article_names = json.load(f)


def custom_sort(columns, ascendings, head_n=5):
    show_columns = list(
        set(
            ["text", "urls", "definition", "comments_total", "karma_total", "lr_stats"]
            + columns
        )
    )
    return app_info.sort_values(columns, ascending=ascendings).head(head_n)[
        show_columns
    ]


tab1, tab2, tab3 = st.tabs(["DataFrame", "Similarity Score", "SPECTER Clustering"])

with tab1:
    score_options = st.multiselect(
        "What is your ordered search criteria?",
        [
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
            "ngram_absolute_count",
            "count_authors",
            "year_mean",
            "ratio_median",
            "karma_upvote_ratio_median",
            "authors_count_articles",
            "authors_karma_total",
            "authors_karma_median",
            "authors_karma_std",
            "authors_upvote_total",
            "authors_upvote_median",
            "authors_upvote_mean",
            "authors_upvote_std",
            "authors_year_mean",
            "authors_year_std",
            "authors_comments_total",
            "authors_comments_mean",
            "authors_comments_median",
            "authors_comments_std",
            "authors_ratio_mean",
            "authors_ratio_median",
            "authors_ratio_std",
            "authors_karma_upvote_ratio_mean",
            "authors_karma_upvote_ratio_median",
            "authors_karma_upvote_ratio_std",
        ],
        ["comments_total", "karma_total", "lr_stats"],
    )
    author_options = st.multiselect(
        "Is there an author similarity score you would like to use?",
        [
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
        ],
        ["Eliezer Yudkowsky Similarity Score"],
    )
    options = score_options + author_options
    with st.sidebar:
        if options:
            agree = [
                st.checkbox(
                    f"Do you want to see lowest values for `{score}`?\nIf not will sort ascending?"
                )
                for score in options
            ]
        else:
            agree = []

        n = st.number_input("How many rows to show?", 5, 100, 5)
    filtered_df = custom_sort(options, agree, n)
    st.write(filtered_df)
    st.write("This is a small subset of the data based on your search criteria.")


with tab2:
    with st.expander("❓ What's this?"):
        st.caption(
        """
        We use the a model that generates embeddings based on the style of a text.
        Most authorship verification models are based on the content of writing; however,
        thanks to the model by Anna Wegmann and team, we can create content-independent embeddings.

        This allows us to compare the style of writing between authors and get a numerical measure
        Authors with similar writing styles will have a higher similarity score with a maximum of 1.

        Authors with very different writings styles will have lower scores.

        Select two authors to compare to one another. We will calculate the average embedding of the first group and the average embedding of the second group. We will then generate a similarity score between the two groups.

        We are also able to compare the similarity of authors to articles. We will calculate the average embedding of the authors and the articles and generate a similarity score between the two groups.
        The default options are the top 10 authors by karma and beren. We also always aggregate the top 10 authors and compare the articles to the average embedding.

        We call this metric less-wronginess. It is an attempt to measure of how much an article fits the style of LessWrong.

        Caveats are that the model is trained on reddit data and may not be fully representative of LessWrong.
        The parity is pretty similar but the distances can be further calibrated to give a more accurate representation of the differences.

        The author level embeddings are created based on the articles they produced.
        Notably Zvi tends to write long pedantic articles, but their comments are short and to the point.
        The model gives a low style similarity between the two.

        This is not a measure of authorship but more a measure of stylistic preference. The actual nature of the weights in the embedding are not known
        Each embedding is a 768 dimensional vector.
        """
        )
    st.write("Similarity Score Calculation")
    st.write(
        "The similarity score is calculated by taking the cosine similarity between the embeddings of the concepts."
    )
    author_pair1 = st.multiselect(
        "Select first set of authors to compare", author_name_list
    )
    author_pair2 = st.multiselect("Select second set of to compare", author_name_list)
    if author_pair1 and author_pair2:
        st.markdown(f"Similarity score between `{author_pair1}` and `{author_pair2}`")
        st.write(compare_authors([author_pair1, author_pair2], df, style_embeddings)[0][0])
    else:
        st.write("Please make your selection")
    article_list = st.multiselect("Select articles to compare", article_names)
    if article_list:
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
        compared_authors = st.multiselect(
            "Select authors to compare",
            author_name_list,
            default_authors,
        )
        labels = [a for a in compared_authors]
        labels.append("Top 10 Authors")
        compared_authors = [[a] for a in compared_authors] + [[a for a in default_authors if a != "beren"]]

        article_idx = np.where(df["title"].isin(article_list))[0]
        sim_scores = batch_author_similarity_score(
                [a for a in compared_authors], df, style_embeddings
            )[:, article_idx].T[0]
        output_text = "|Author|Cosine Similarity|\n|---|---|\n"
        for label, sim in zip(labels, sim_scores):
            output_text += f"|{label}|{sim:.2f}|\n"
        st.markdown(output_text)


with tab3:
    n = st.number_input(
        "How many clusters do you want to divide the concepts into?",
        1,
        app_info.shape[0],
        5,
    )
    st.write("SPECTER Clustering")
    with st.expander("❓ What's this?"):
        st.caption(
        """
        We use the AllenAI SPECTER model which is a
        pretrained model that generates embeddings for text.
        This uses the embeddings generated for the concepts based on the combination of titles and abstracts.
        
        We then use KMeans clustering to group the concepts.
        Since the embeddings are high dimensional, we use PCA to reduce the dimensionality to 2.
        so that we can visualize the clusters.

        Hover over the text and select which cluster you would like more detailed information.
        It will be printed below the selection.
        """
        )
    fig,df_with_clusters = create_viz(app_info, n, specter_embeddings)
    st.plotly_chart(fig)
    cluster_choice = st.number_input("Which cluster would you like to explore?", 0, n-1, 0)
    df_cluster = df_with_clusters[df_with_clusters["cluster_labels"] == cluster_choice].reset_index(drop=True)
    for i, row in df_cluster.iterrows():
        st.write(f"Concept {i}")
        st.html(row["text"])
        st.write("\nDefinition")
        st.write(row["definition"])
        st.write("Articles")
        row_titles = df[df["articles_id"].isin(row["article_ids"])]["title"].to_list()
        for article, url in zip(row_titles,row["urls"]):
            st.markdown(f"[{article}]({url})")
        st.write(f'Total Comments: {row["comments_total"]}')
        st.write(f'Total Karma: {row["karma_total"]}')
        st.write(f'Logistic Regression Score: {row["lr_stats"]}')
        st.write("----")


if __name__=="__main__":
    app.run(host="0.0.0.0",port=os.environ.get("PORT", 8501))