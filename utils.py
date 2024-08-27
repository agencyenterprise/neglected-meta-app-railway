import os
from sklearn.preprocessing import QuantileTransformer
import pandas as pd
from urllib.parse import urlparse
import psycopg2
from datetime import datetime, timezone

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
def create_idea(article, description, email=None):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO ideas (article, description, email, created_at)
        VALUES (%s, %s, %s, %s)
        """,
        (article, description, email, datetime.now(timezone.utc))
    )
    conn.commit()
    cur.close()
    conn.close()

def list_ideas():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, article, description, email, created_at
        FROM ideas
        ORDER BY created_at DESC
        """
    )
    ideas = cur.fetchall()
    cur.close()
    conn.close()
    return ideas

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