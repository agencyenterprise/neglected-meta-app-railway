## load.py

import glob
import os
import json
from utils import string_list_to_list
import pandas as pd
from typing import List, Optional
import re
from utils import prepare_concept_for_request
from sklearn.feature_extraction.text import CountVectorizer

class LessWrongData:
    include_af_indicator: bool = True
    df_path: str = "lw_data/lw.tsv"
    docid_to_concept_list_path: str = "app_files/concept_lists.json"
    alignment_url_json_path: str = "app_files/alignment_urls.json"
    json_dirpath: str = "lw_data"
    
    def lw_df(self, include_af_indicator: bool = True, tag_whitelist: Optional[List[str]]=None):
        df = pd.read_csv(self.df_path, sep="\t").set_index("_id")
        df['tags'] = df['tags'].apply(string_list_to_list)
        df['authors'] = df['authors'].fillna('[]').apply(string_list_to_list)
        
        if tag_whitelist:
            assert isinstance(tag_whitelist, List[str])
            df = df.loc[df['tags'].apply(lambda x: len(set(x).intersection(set(tag_whitelist)))>0)]

        if include_af_indicator:
            with open(self.alignment_url_json_path, "r") as f:
                urls = json.loads(f.read())
            urls = [x.replace("alignmentforum.org", "lesswrong.com") for x in urls]
            df=df.assign(alignment_forum=df['url'].isin(urls))        
        
        return df

    def docid_to_concept_list(self, strip_numbers=True, replace_special_characters=False):
        with open(self.docid_to_concept_list_path, "r") as f:
            concept_lists = json.loads(f.read())
        if strip_numbers:
            concept_lists = {k: [re.sub("^\d+\.\s+[-\"]?","", c) for c in v] for k,v in concept_lists.items()}
        if replace_special_characters:
            concept_lists = {k: [prepare_concept_for_request(c) for c in v] for k,v in concept_lists.items()}
        return concept_lists


class LWCounts:
    def __init__(self, textseries):
        self.vectorizer = CountVectorizer()
        self.counts = self.vectorizer.fit_transform(textseries)
        self.feature_names = self.vectorizer.get_feature_names_out()
        self.counts_dense = self.counts.todense()
        self.countsdf = pd.DataFrame(self.counts_dense, columns=self.feature_names)

    def get_word_counts(self, word):
        # To get the count of a specific word across all documents
        word_index = self.vectorizer.vocabulary_.get(word)
        word_count = self.counts_dense[:, word_index].sum() if word_index is not None else 0
        return word_count
