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
df["dot_size"] = (df["karma"] - df["karma"].min()) / (
    df["karma"].max() - df["karma"].min()
) * STANDARD_SIZE + 10
user_df["dot_size"] = (user_df["karma"] - user_df["karma"].min()) / (
    user_df["karma"].max() - user_df["karma"].min()
) * STANDARD_SIZE + 10


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


tab1, tab2, tab3, tab4 = st.tabs(
    ["DataFrame", "Similarity Score", "SPECTER Clustering", "Connected Posts"]
)

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
                    f"Do you want to sort `{score}` ascending?\nThis will show the lowest values first"
                )
                for score in options
            ]
        else:
            agree = []

        n = st.number_input("How many rows to show?", 5, 100, 5)
        truncate = st.checkbox(
            f"Truncate to only the top {n} rows?\n This will limit how many categories you can see and interact with.",
            True,
        )
    filtered_df = custom_sort(options, agree, n, truncate=truncate)
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
        st.write(
            compare_authors([author_pair1, author_pair2], df, style_embeddings)[0][0]
        )
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
        output_text = "|Author|Cosine Similarity|\n|---|---|\n"
        for label, sim in zip(labels, sim_scores):
            output_text += f"|{label}|{sim:.2f}|\n"
        output_text += f"|Top 100 Authors|{top_100_score:.2f}|\n"
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
    cluster_choice = st.number_input(
        "Which cluster would you like to explore?", 0, n - 1, 0
    )
    select_by_content = st.selectbox(
        "Select by content", app_info["text"].to_list(), None
    )
    fig, df_with_clusters, cluster_choice = create_viz(
        app_info, n, specter_embeddings, cluster_choice, select_by_content
    )

    st.plotly_chart(fig)
    df_cluster = df_with_clusters[
        df_with_clusters["cluster_labels"] == cluster_choice
    ].reset_index(drop=True)
    for i, row in df_cluster.iterrows():
        st.write(f"Concept {i}")
        st.html(row["text"])
        st.write("\nDefinition")
        st.write(row["definition"])
        st.write("Articles")
        row_titles = df[df["articles_id"].isin(row["article_ids"])]["title"].to_list()
        for article, url in zip(row_titles, row["urls"]):
            st.markdown(f"[{article}]({url})")
        st.write(f'Total Comments: {row["comments_total"]}')
        st.write(f'Total Karma: {row["karma_total"]}')
        st.write(f'Logistic Regression Score: {row["lr_stats"]}')
        st.write("----")
@st.cache_data
def get_raw_graph(df, comments, post_id, user_df, d=2):
    return build_graph(df, comments, post_id, user_df, depth=d)

with tab4:
    st.write("Knowledge Graph")
    raw_nodes, raw_edges = get_raw_graph(df, comments, "qAdDzcBuDBLexb4fC", user_df, d=1)
    nodes = []
    edges = []
    STANDARD_SIZE = 25
    print("creating nodes")
    for node in raw_nodes:
        if node["type"] == "post":
            nodes.append(
                Node(
                    id=node["id"],
                    label=node["label"],
                    title=node["url"],
                    size=node["size"],
                    type=node["type"],
                    color="blue",
                )
            )
        elif node["type"] == "user":
            nodes.append(
                Node(
                    id=node["id"],
                    label=node["label"],
                    title=node["url"],
                    size=node["size"],
                    type=node["type"],
                    color="green",
                )
            )
        else:
            nodes.append(
                Node(
                    id=node["id"],
                    # label=node["label"],
                    title=node["url"],
                    size=STANDARD_SIZE,
                    type=node["type"],
                    color="orange",
                )
            )
    print("creating edges")
    for edge in raw_edges:
        edges.append(
            Edge(
                source=edge["source"],
                label=edge["label"],
                target=edge["target"],
            )
        )
    config = Config(width=750,
                    height=950,
                    directed=True,
                    physics=True,
                    hierarchical=False,
                    node={'labelProperty':'label'},
                    link={'labelProperty': 'label', 'renderLabel': True}
                    # **kwargs
                    )
    # config_builder = ConfigBuilder(nodes)
    print("here's a graph")
    # config = config_builder.build()
    return_value = agraph(nodes=nodes, edges=edges, config=config)
    print("foo")
    # nodes.append( Node(id="Marvel",
    #                 label="foobar",
    #                 size=25,
    #                 shape="circularImage",
    #                 image="https://upload.wikimedia.org/wikipedia/commons/thumb/b/b9/Marvel_Logo.svg/2560px-Marvel_Logo.svg.png")
    #             ) # includes **kwargs
    # nodes.append( Node(id="Spiderman",
    #                 label="Peter Parker",
    #                 title="https://en.wikipedia.org/wiki/Spider",
    #                 size=25,
    #                 shape="circularImage",
    #                 link="https://en.wikipedia.org/wiki/Spider",
    #                 image="http://marvel-force-chart.surge.sh/marvel_force_chart_img/top_spiderman.png")
    #             ) # includes **kwargs
    # nodes.append( Node(id="https://en.wikipedia.org/wiki/Captain_Marvel_(film)",
    #                 label="Captain Marvel",
    #                 size=25,
    #                 shape="circularImage",
    #                 link="https://en.wikipedia.org/wiki/Spider",
    #                 image="http://marvel-force-chart.surge.sh/marvel_force_chart_img/top_captainmarvel.png")
    #             )
    # edges.append( Edge(source="Spiderman",
    #                 label="belongs_to",
    #                 target="Marvel",
    #                 # **kwargs
    #                 )
    #             )
    # edges.append( Edge(source="https://en.wikipedia.org/wiki/Spider",
    #                 label="friends_with",
    #                 target="https://en.wikipedia.org/wiki/Captain_Marvel_(film)",
    #                 # **kwargs
    #                 )
    #             )

    # st.write("This is a work in progress. We are working on generating a knowledge graph that will allow you to explore the relationships between concepts.")
    # st.write("Please check back later for updates.")
    # st.write("If you have any questions or suggestions please reach out to us at the LessWrong Discord server.")
