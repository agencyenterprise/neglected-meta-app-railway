import html
import re

import pandas as pd
import tqdm


def load_post_centroid(df, comments, post_id, pingback=True):
    main_post = df[df["_id"] == post_id]
    if pingback:
        if len(main_post["pingback"].values) == 0:
            return pd.DataFrame(), pd.DataFrame()
        linked_articles = main_post["pingback"].values[0]
    else:
        if len(main_post["refs"].values) == 0:
            return pd.DataFrame(), pd.DataFrame()
        linked_articles = main_post["refs"].values[0]
    linked_posts = df[df["_id"].isin(linked_articles)]
    new_df = pd.concat([main_post, linked_posts])
    relevant_comments = comments[comments["postId"].isin(new_df["_id"].unique())]
    return new_df, relevant_comments

def get_refs_tree(df, comments, post_id, depth=1, pingback=True):
    queue = [post_id]
    visited = set()
    refs = []
    comms = []

    for i in range(depth):
        new_queue = []
        for current_post_id in queue:
            if current_post_id in visited:
                continue
            visited.add(current_post_id)

            post_df, comm_df = load_post_centroid(df, comments, current_post_id, pingback=pingback)

            if post_df.empty:
                continue  # Skip if the post is not found

            refs.append(post_df)
            comms.append(comm_df)

            # Add the next level of refs and pingback posts to the queue
            if len(post_df["pingback"].values) > 0:
                new_queue.extend(post_df["pingback"].values[0])
            if len(post_df["refs"].values) > 0:
                new_queue.extend(post_df["refs"].values[0])

        queue = new_queue

    ref_df = pd.concat(refs).drop_duplicates(subset="_id")
    comms_df = pd.concat(comms).drop_duplicates(subset="_id")
    return ref_df, comms_df

def get_graph_dfs(df, comments, post_id, user_df, d=2):
    pingback_df, pingback_comment_df = get_refs_tree(df, comments, post_id, depth=d, pingback=True)
    ref_df, ref_comment_df = get_refs_tree(df, comments, post_id, depth=d, pingback=False)
    post_df = pd.concat([pingback_df, ref_df])
    comment_df = pd.concat([pingback_comment_df, ref_comment_df])
    post_df.drop_duplicates(subset="_id", inplace=True)
    comment_df.drop_duplicates(subset="_id", inplace=True)
    post_authors = post_df.explode("authors")["authors"].unique()
    post_user_df = user_df[user_df["display_name"].isin(post_authors)]
    comment_user_df = user_df[user_df["user_id"].isin(comment_df["author_id"].unique())]
    relevant_user_df = pd.concat([post_user_df, comment_user_df])
    relevant_user_df = relevant_user_df.drop_duplicates(subset="user_id")
    return post_df, comment_df, relevant_user_df

def unescape_and_strip_html(text):
    if text is None:
        return ""
    return html.unescape(re.sub(r'<[^>]*>', '', str(text))).strip()

def build_graph(df, comments, post_id, user_df, depth=2):
    post_df, comment_df, relevant_user_df = get_graph_dfs(df, comments, post_id, user_df, d=depth)
    nodes = []
    edges = []
    # create post nodes
    # print("Step 1/5: Creating post nodes")
    for i, row in tqdm.tqdm(post_df.iterrows(), total=post_df.shape[0]):
        nodes.append({
            "id": row["_id"],
            "label": row["title"],
            "type": "post",
            "sizeKarma": row["dot_size_karma"],
            "sizeComments": row["dot_size_comments"],
            "sizeUpvotes": row["dot_size_upvotes"],
            "upvoteCount": row["upvoteCount"],
            "karma": row["karma"],
            "commentCount": row["commentCount"],
            "url": row["url"]
        })
    # print("Step 2/5: Creating refs edges")
    for i, row in tqdm.tqdm(post_df.iterrows(), total=post_df.shape[0]):
        for ref in row["refs"]:
            edges.append({
                "source": row["_id"],
                "target": ref,
                "label": "refs"
            })
    # print("Step 3/7: Creating author nodes")
    # for i, row in tqdm.tqdm(relevant_user_df.iterrows(), total=relevant_user_df.shape[0]):
    #     nodes.append({
    #         "id": row["user_id"],
    #         "label": row["display_name"],
    #         "type": "user",
    #         "post_count": row["post_count"],
    #         "comment_count": row["comment_count"],
    #         "size": row["dot_size"],
    #         "karma": row["karma"],
    #         "url": "https://lesswrong.com/users/" + row["slug"]
    #     })
    # print("Step 4/7: Creating authorship edges")
    # for i, row in tqdm.tqdm(post_df.iterrows(), total=post_df.shape[0]):
    #     for author in row["authors"]:
    #         try:
    #             uid = relevant_user_df[relevant_user_df["display_name"] == author]["user_id"].values[0]
    #             edges.append({
    #                 "source": uid,
    #                 "target": row["_id"],
    #                 "label": "wrote",
    #             })
    #         except IndexError:
    #             continue
    # print("Step 5/7: Creating comment nodes")
    for i, row in tqdm.tqdm(comment_df.iterrows(), total=comment_df.shape[0]):
        nodes.append({
            "id": row["_id"],
            "label": unescape_and_strip_html(row["htmlBody"]),
            "type": "comment",
            "url": "https://lesswrong.com/posts/" + row["postId"] + "/comments/" + row["_id"],
            # "upvoteCount": row["upvoteCount"]
        })
    # print("Step 6/7: Creating comment reply edges")
    for i, row in tqdm.tqdm(comment_df.iterrows(), total=comment_df.shape[0]):
        if row["parentCommentId"] is not None:
            edges.append({
                "source": row["_id"],
                "target": row["parentCommentId"],
                "label": "replyTo"
            })
        else:
            edges.append({
                "source": row["_id"],
                "target": row["postId"],
                "label": "commentOn"
            })
    # print("Step 7/7: Creating authored comment edges")
    for i, row in tqdm.tqdm(comment_df.iterrows(), total=comment_df.shape[0]):
        edges.append({
            "source": row["author_id"],
            "target": row["_id"],
            "label": "authored"
        })
    return nodes, edges
