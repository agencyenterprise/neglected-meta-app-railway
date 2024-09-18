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
def create_approach(main_article, node_id, link, type, label, email=None, comment=None):
    existing_approach = get_approach_by_node_id(node_id)
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    if existing_approach:
        approach_id = existing_approach[0]
        cur.execute(
            """
            UPDATE approaches
            SET spotlight_count = spotlight_count + 1
            WHERE id = %s
            RETURNING spotlight_count
            """,
            (approach_id,)
        )
        new_count = cur.fetchone()[0]
    else:
        cur.execute(
            """
            INSERT INTO approaches (main_article, node_id, link, type, label, created_at, spotlight_count)
            VALUES (%s, %s, %s, %s, %s, %s, 1)
            RETURNING id, spotlight_count
            """,
            (main_article, node_id, link, type, label, datetime.now(timezone.utc))
        )
        approach_id, new_count = cur.fetchone()
    
    if email or comment:
        cur.execute(
            """
            INSERT INTO spotlights (approach_id, email, comment, created_at)
            VALUES (%s, %s, %s, %s)
            """,
            (approach_id, email, comment, datetime.now(timezone.utc))
        )
    
    conn.commit()
    cur.close()
    conn.close()
    return approach_id, new_count, existing_approach is not None

def get_approach_by_node_id(node_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, main_article, node_id, link, type, label, created_at, spotlight_count
        FROM approaches
        WHERE node_id = %s
        """,
        (node_id,)
    )
    approach = cur.fetchone()
    cur.close()
    conn.close()
    return approach

def get_spotlights_for_approach(approach_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT email, comment, created_at
        FROM spotlights
        WHERE approach_id = %s
        ORDER BY created_at DESC
        """,
        (approach_id,)
    )
    spotlights = cur.fetchall()
    cur.close()
    conn.close()
    return spotlights

def list_approaches(limit=10, last_spotlight_count=None, last_created_at=None, last_id=None):
    conn = get_db_connection()
    cur = conn.cursor()

    if last_spotlight_count is not None and last_created_at and last_id:
        cur.execute(
            """
            SELECT id, main_article, node_id, link, type, label, created_at, spotlight_count
            FROM approaches
            WHERE (spotlight_count, created_at, id) < (%s, %s, %s)
            ORDER BY spotlight_count DESC, created_at DESC, id DESC
            LIMIT %s
            """,
            (last_spotlight_count, last_created_at, last_id, limit + 1)
        )
    else:
        cur.execute(
            """
            SELECT id, main_article, node_id, link, type, label, created_at, spotlight_count
            FROM approaches
            ORDER BY spotlight_count DESC, created_at DESC, id DESC
            LIMIT %s
            """,
            (limit + 1,)
        )

    approaches = cur.fetchall()
    cur.close()
    conn.close()

    has_next = len(approaches) > limit
    approaches = approaches[:limit]

    next_cursor = None
    if has_next and approaches:
        last_approach = approaches[-1]
        next_cursor = f"{last_approach[7]}_{last_approach[6].isoformat()}_{last_approach[0]}"

    approaches_with_spotlights = []
    for approach in approaches:
        spotlights = get_spotlights_for_approach(approach[0])
        approaches_with_spotlights.append(approach + (spotlights,))

    return approaches_with_spotlights, next_cursor

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