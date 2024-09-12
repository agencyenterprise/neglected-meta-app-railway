import os
from datetime import datetime, timezone
from urllib.parse import urlparse

import pandas as pd
import psycopg2
from sklearn.preprocessing import QuantileTransformer


def get_db_connection():
    # Get the database URL from the environment variable
    db_url =  os.getenv("DATABASE_URL") or os.getenv("DATABASE_PUBLIC_URL")

    if db_url:
        # Parse the URL to get the components needed for the connection
        result = urlparse(db_url)
        conn = psycopg2.connect(
            host=result.hostname,
            port=result.port,
            database=result.path[1:],
            user=result.username,
            password=result.password
        )
        return conn
    else:
        raise Exception("DATABASE URL is not set in the environment variables")

# Define the Idea model operations using psycopg2
def create_idea(main_article, node_id, link, type, label, email=None, comment=None):
    existing_idea = get_idea_by_node_id(node_id)
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    if existing_idea:
        idea_id = existing_idea[0]
        cur.execute(
            """
            UPDATE ideas
            SET endorsement_count = endorsement_count + 1
            WHERE id = %s
            RETURNING endorsement_count
            """,
            (idea_id,)
        )
        new_count = cur.fetchone()[0]
    else:
        cur.execute(
            """
            INSERT INTO ideas (main_article, node_id, link, type, label, created_at, endorsement_count)
            VALUES (%s, %s, %s, %s, %s, %s, 1)
            RETURNING id, endorsement_count
            """,
            (main_article, node_id, link, type, label, datetime.now(timezone.utc))
        )
        idea_id, new_count = cur.fetchone()
    
    # Insert the endorsement only if email or comment is present
    if email or comment:
        cur.execute(
            """
            INSERT INTO idea_endorsements (idea_id, email, comment, created_at)
            VALUES (%s, %s, %s, %s)
            """,
            (idea_id, email, comment, datetime.now(timezone.utc))
        )
    
    conn.commit()
    cur.close()
    conn.close()
    return idea_id, new_count, existing_idea is not None

def get_idea_by_node_id(node_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, main_article, node_id, link, type, label, created_at, endorsement_count
        FROM ideas
        WHERE node_id = %s
        """,
        (node_id,)
    )
    idea = cur.fetchone()
    cur.close()
    conn.close()
    return idea

def get_endorsements_for_idea(idea_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT email, comment, created_at
        FROM idea_endorsements
        WHERE idea_id = %s
        ORDER BY created_at DESC
        """,
        (idea_id,)
    )
    endorsements = cur.fetchall()
    cur.close()
    conn.close()
    return endorsements

def list_ideas(limit=10, last_endorsement_count=None, last_created_at=None, last_id=None):
    conn = get_db_connection()
    cur = conn.cursor()

    if last_endorsement_count is not None and last_created_at and last_id:
        cur.execute(
            """
            SELECT id, main_article, node_id, link, type, label, created_at, endorsement_count
            FROM ideas
            WHERE (endorsement_count, created_at, id) < (%s, %s, %s)
            ORDER BY endorsement_count DESC, created_at DESC, id DESC
            LIMIT %s
            """,
            (last_endorsement_count, last_created_at, last_id, limit + 1)
        )
    else:
        cur.execute(
            """
            SELECT id, main_article, node_id, link, type, label, created_at, endorsement_count
            FROM ideas
            ORDER BY endorsement_count DESC, created_at DESC, id DESC
            LIMIT %s
            """,
            (limit + 1,)
        )

    ideas = cur.fetchall()
    cur.close()
    conn.close()

    has_next = len(ideas) > limit
    ideas = ideas[:limit]

    next_cursor = None
    if has_next and ideas:
        last_idea = ideas[-1]
        next_cursor = f"{last_idea[7]}_{last_idea[6].isoformat()}_{last_idea[0]}"

    ideas_with_endorsements = []
    for idea in ideas:
        endorsements = get_endorsements_for_idea(idea[0])
        ideas_with_endorsements.append(idea + (endorsements,))

    return ideas_with_endorsements, next_cursor

def string_list_to_list(strlist):
    return [c.strip("'").strip('"') for c in strlist.strip("[]").split(", ")]

def quantile_transformation(s):
    # Initialize the QuantileTransformer
    # Set 'output_distribution' to 'uniform' or 'normal', depending on your needs
    qt = QuantileTransformer(output_distribution='uniform', n_quantiles=s.nunique(), random_state=323)

    # Fit and transform the data
    # Note: QuantileTransformer expects a 2D array, so we use s.values.reshape(-1, 1) to reshape the Series
    s_transformed = qt.fit_transform(s.values.reshape(-1, 1))

    # The output is a numpy array, convert it back to a pandas Series if needed
    s_transformed = pd.Series(s_transformed.flatten(), index=s.index)

    return s_transformed

def prepare_concept_for_request(c):
    repl_with_space = ["-","_", "\\", "/"]
    repl_with_empty = ["%",":",'"',"+","*","(",")","[","]","{","}","|","'",'.']

    for char in repl_with_space:
        c = c.replace(char, " ")
    for char in repl_with_empty:
        c = c.replace(char, "")
    c = c.replace("  ", " ")
    return c.strip().strip("/").strip()