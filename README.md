# Analyze Lesswrong Data to Discover Neglected Approaches

## TOC
1. [Data Walkthrough](#data-walkthrough)
2. [Previous Work - Mose](#update-05152024)
3. [Previous Work - Steve](#update-05012024)

# Data Walkthrough
Data Features
- article text
- authors
- tags
- lw score: score that determines the page ranking. 
- upvotes: number of upvotes 
- karma: karma score on the less wrong website at time of collection
- date: Date posted
- comments: number of comments at time of data collection
# Run Book

# Update 5/15/2024

To set up:
```
git clone https://github.com/agencyenterprise/neglected-meta-analysis-lesswrong.git
python3 -m venv neglected-meta-analysis-lesswrong
cd neglected-meta-analysis-lesswrong
source bin/activate
pip install -r requirements.txt
python make_tsv.py
```
**Note** you may need to install hdf and the tables package. If using conda, python 3.10 will work but not 3.9 or 3.11 with the current code due to small implementation details of pandas and pytorch.

Data collection steps:

- Create whitelist of LessWrong tags (`https://www.lesswrong.com/tags/all#ARTIFICIAL_INTELLIGENCE` -> `tag_whitelist.json`)
- Use GPT-4-Turbo to extract candidate "neglected approaches to AI alignment" from LW articles with at least one whitelisted tag (`gpt.ipynb` -> `results/concept_lists.json`)
- Get definition/summary of each extracted candidate using LlamaIndex (`rag.ipynb` -> `results/concept_definitions/summaries.json`)
- Get semantic embedding of candidates using `all-MiniLM-L6-v2` (`concept-embedding.ipynb` -> `lw_data/features/candidate_embeddings_all-MiniLM-L6-v2.hdf`)
- Get ngrams of candidates (`ngrams.ipynb` -> `results/ngrams.json`)
- Get text embeddings of articles using `text-embedding-3-large` (`body-embedding.ipynb` -> file not contained in repo due to size; contact `mose@ae.studio`)
- Detect which articles were cross-posted from alignment forum (`get_af_articles.ipynb` -> `alignment_urls.json`)

Data limitations:
- No comment, hyperlink, or citation data are included in the dataset from Lightcone

Analysis steps (`concept_list_analysis.ipynb` -> `lw_data/features`)
- Load data (`load.py`)
- Drop candidates which are only one word long (4.5%) or more than 18 words long (~1%)
- Use DBSCAN to cluster/merge semantically similar candidates
- Create mapping from candidate to list of article IDs discussing it
- Compute per-candidate article statistics
- Create candidate-indexed feature dataframe containing aggregated article statistics, embedded candidate, and averaged embedded article text

ML (`ml.ipynb` -> `app_info.json`)
- Train ML models to classify neglected approaches (1=extracted from AE article about neglected approaches; 0 otherwise)
- Save list of candidates ranked by model score

- Use `labeling_tool.html` to load `app_info.json` for additional labeling of neglected approaches

To do:
- Create per-author statistics to use as features (in progress: `author-features.ipynb`)
- Get more labels
- Get comment, citation, and hyperlink data
- Hierarchically cluster concepts and use hierarchy to:
    - map interaction with concept/cluster over time (comment-related timestamps could be useful here for "interaction")
    - shrink search space
- Embed articles which were too long for OpenAI API
- Writeup


Steve's NBs: 
- analyze.ipynb
- contrarian_minority_reports.ipynb
- fetch-graphql.ipynb
- newdata.ipynb
- unpopular_authors.ipynb


# Update 05/01/2024

Lightcone provided us with an updated dataset so we dont have to rely on the third party (outdated) dataset used in the original approach. The data can be found in ./lw_data.

See `newdata.ipynb` for loading and cleaning the data. The notebook also does a bit of author analysis.

The other notebooks are probably mainly useless but some basic clustering was attempted if of interest.

# Original approach (Deprecated)

This repository contains code to analyze the [Lesswrong alignment research](https://github.com/moirage/alignment-research-dataset/tree/main) dataset to discover neglected approaches to AI alignment.

## Getting started

You can download a snapshot of the dataset at the repo linked above. The repo also contains scripts that can be used to scrape a fresh dataset.

I used Conda to manage my environment. You can create a new environment with the following command:

```bash
conda create --name lesswrong_meta python=3.8 jupyterlab pandas numpy matplotlib scikit-learn
```

Then activate the environment with:

```bash
conda activate lesswrong_meta
```

## Approach

Check out the notebook `analyze.ipynb` to see the code that analyzes the dataset. In it, I've done a bit of cleaning up front, then some KMeans clustering to find clusters of articles. From there, I apply TSNE to visualize the clusters in 2D. I also attempted to normalize the tightness and average score to find clusters with a high average score and few articles, which might be neglected.

## Todo - Ideas for determining neglected approaches

- maybe its authors - they post a lot but they aren’t getting a lot of comments on their posts - how many comments are they getting?
- Find a way to analyze the full text of the clusters to determine if there are patterns that may indicate neglected approaches.
- Generate a list of neglected approaches based on the clusters.
