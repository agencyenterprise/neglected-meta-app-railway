import pandas as pd
import tqdm
def load_post_centroid(df, comments, post_id, pingback=True):
    main_post = df[df["_id"] == post_id]
    if pingback:
        linked_articles = main_post["pingback_posts"].values[0]
    else:
        linked_articles = main_post["references"].values[0]
    linked_posts = df[df["_id"].isin(linked_articles)]
    new_df = pd.concat([main_post, linked_posts])
    relevant_comments = comments[comments["postId"].isin(new_df["_id"].unique())]
    return new_df, relevant_comments

def get_references_tree(df, comments, post_id, depth=1, pingback=True):
    queue = [post_id]
    visited = set()
    references = []
    comms = []
    for i in range(depth):
        new_queue = []
        for post_id in queue:
            if post_id in visited:
                continue
            visited.add(post_id)
            post_df, comm_df = load_post_centroid(df, comments, post_id, pingback=pingback)
            references.append(post_df)
            comms.append(comm_df)
            new_queue.extend(post_df["pingback_posts"].values[0])
        queue = new_queue
    ref_df = pd.concat(references).drop_duplicates(subset="_id")
    comms_df = pd.concat(comms).drop_duplicates(subset="_id")
    return ref_df, comms_df

def get_graph_dfs(df, comments, post_id, user_df, d=2):
    pingback_df, pingback_comment_df = get_references_tree(df, comments, post_id, depth=d, pingback=True)
    ref_df, ref_comment_df = get_references_tree(df, comments, post_id, depth=d, pingback=False)
    post_df = pd.concat([pingback_df, ref_df])
    comment_df = pd.concat([pingback_comment_df, ref_comment_df])
    post_df.drop_duplicates(subset="_id", inplace=True)
    comment_df.drop_duplicates(subset="_id", inplace=True)
    post_authors = post_df.explode("authors")["authors"].unique()
    relevant_user_df = user_df[user_df["display_name"].isin(post_authors)]
    relevant_user_df = relevant_user_df.drop_duplicates(subset="user_id")
    return post_df, comment_df, relevant_user_df

def build_graph(df, comments, post_id, user_df, depth=2):
    post_df, comment_df, relevant_user_df = get_graph_dfs(df, comments, post_id, user_df, d=depth)
    nodes = []
    edges = []
    # create post nodes
    print("Step 1/5: Creating post nodes")
    for i, row in tqdm.tqdm(post_df.iterrows(), total=post_df.shape[0]):
        nodes.append({
            "id": row["_id"],
            "label": row["title"],
            "type": "post",
            "size": row["dot_size"],
            "upvoteCount": row["upvoteCount"],
            "url": row["url"]
        })
    print("Step 2/5: Creating references edges")
    for i, row in tqdm.tqdm(post_df.iterrows(), total=post_df.shape[0]):
        for ref in row["references"]:
            edges.append({
                "source": row["_id"],
                "target": ref,
                "label": "references"
            })
    print("Step 3/7: Creating author nodes")
    for i, row in tqdm.tqdm(relevant_user_df.iterrows(), total=relevant_user_df.shape[0]):
        nodes.append({
            "id": row["user_id"],
            "label": row["display_name"],
            "type": "user",
            "post_count": row["post_count"],
            "comment_count": row["comment_count"],
            "size": row["dot_size"],
            "url": "https://lesswrong.com/users/" + row["slug"]
        })
    print("Step 4/7: Creating authorship edges")
    for i, row in tqdm.tqdm(post_df.iterrows(), total=post_df.shape[0]):
        for author in row["authors"]:
            try:
                uid = relevant_user_df[relevant_user_df["display_name"] == author]["user_id"].values[0]
                edges.append({
                    "source": uid,
                    "target": row["_id"],
                    "label": "wrote",
                })
            except IndexError:
                continue
    print("Step 5/7: Creating comment nodes")
    for i, row in tqdm.tqdm(comment_df.iterrows(), total=comment_df.shape[0]):
        nodes.append({
            "id": row["_id"],
            # "label": row["htmlBody"],
            "type": "comment",
            "url": "https://lesswrong.com/posts/" + row["postId"] + "/comments/" + row["_id"],
            # "upvoteCount": row["upvoteCount"]
        })
    print("Step 6/7: Creating comment reply edges")
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
    print("Step 7/7: Creating authored comment edges")
    for i, row in tqdm.tqdm(comment_df.iterrows(), total=comment_df.shape[0]):
        edges.append({
            "source": row["author_id"],
            "target": row["_id"],
            "label": "authored"
        })
    return nodes, edges