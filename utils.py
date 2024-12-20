import logging
import os
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Optional
from urllib.parse import urlparse

import pandas as pd
import psycopg2
from psycopg2 import pool
from psycopg2.extras import Json
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from sklearn.preprocessing import QuantileTransformer

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define a global variable for the connection pool
connection_pool: Optional[pool.SimpleConnectionPool] = None

def initialize_db_pool():
    """Initialize the connection pool if not already created."""
    global connection_pool
    
    try:
        if connection_pool is not None:
            try:
                connection_pool.closeall()
            except Exception:
                pass
            connection_pool = None
            
        db_url = os.getenv("DATABASE_URL") or os.getenv("DATABASE_PUBLIC_URL")
        
        if not db_url:
            raise Exception("DATABASE URL is not set in the environment variables")
            
        result = urlparse(db_url)
        
        connection_pool = pool.ThreadedConnectionPool(
            minconn=1,
            maxconn=10, 
            host=result.hostname,
            port=result.port,
            database=result.path[1:],
            user=result.username,
            password=result.password,
            connect_timeout=5,
            keepalives=1,
            keepalives_idle=30,
            keepalives_interval=10,
            keepalives_count=5
        )
        logger.info("Database connection pool initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize connection pool: {str(e)}")
        raise

@contextmanager
def get_db_connection():
    """Context manager for database connections."""
    conn = None
    max_retries = 3
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            if connection_pool is None:
                initialize_db_pool()
            conn = connection_pool.getconn()
            break
        except (psycopg2.OperationalError, psycopg2.pool.PoolError) as e:
            retry_count += 1
            logger.warning(f"Failed to get connection (attempt {retry_count}/{max_retries}): {str(e)}")
            if retry_count == max_retries:
                raise
            time.sleep(1)  # Longer sleep between retries
    
    if conn is None:
        raise Exception("Failed to acquire database connection")
        
    try:
        yield conn
        if not conn.closed:
            conn.commit()
    except Exception:
        if not conn.closed:
            conn.rollback()
        raise
    finally:
        if conn is not None and not conn.closed:
            try:
                connection_pool.putconn(conn)
            except Exception as e:
                logger.error(f"Error releasing connection: {str(e)}")
                try:
                    conn.close()
                except Exception:
                    pass

def close_db_pool():
    """Close all connections in the pool."""
    global connection_pool
    try:
        if connection_pool:
            connection_pool.closeall()
            logger.info("Database connection pool closed successfully")
    except Exception as e:
        logger.error(f"Error closing connection pool: {str(e)}")
        raise

# Define the Idea model operations using psycopg2
def create_approach(main_article, node_id, link, type, label, email=None, comment=None):
    existing_approach = get_approach_by_node_id(node_id)
    
    with get_db_connection() as conn:
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
        
        cur.close()
        return approach_id, new_count, existing_approach is not None

def get_approach_by_node_id(node_id):
    with get_db_connection() as conn:
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
        return approach

def get_spotlights_for_approach(approach_id):
    with get_db_connection() as conn:
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
        return spotlights

def list_approaches(limit=10, last_spotlight_count=None, last_created_at=None, last_id=None, filter_type=None, order_by='spotlights'):
    with get_db_connection() as conn:
        cur = conn.cursor()

        where_clause = ""
        order_clause = ""
        params = []

        if last_spotlight_count is not None and last_created_at and last_id:
            where_clause = "WHERE (a.spotlight_count, a.created_at, a.id) < (%s, %s, %s)"
            params.extend([last_spotlight_count, last_created_at, last_id])

        if filter_type in ['post', 'comment']:
            where_clause += " AND " if where_clause else "WHERE "
            where_clause += "a.type = %s"
            params.append(filter_type)

        if order_by == 'spotlights':
            order_clause = "ORDER BY a.spotlight_count DESC, a.created_at DESC, a.id DESC"
        elif order_by == 'comments':
            order_clause = "ORDER BY comment_count DESC, a.created_at DESC, a.id DESC"
        elif order_by == 'recency':
            order_clause = "ORDER BY a.created_at DESC, a.id DESC"
        else:
            order_clause = "ORDER BY a.spotlight_count DESC, a.created_at DESC, a.id DESC"

        query = f"""
            SELECT a.id, a.main_article, a.node_id, a.link, a.type, a.label, a.created_at, a.spotlight_count,
                   COUNT(CASE WHEN s.comment IS NOT NULL THEN 1 END) as comment_count
            FROM approaches a
            LEFT JOIN spotlights s ON a.id = s.approach_id
            {where_clause}
            GROUP BY a.id
            {order_clause}
            LIMIT %s
        """
        params.append(limit + 1)

        cur.execute(query, tuple(params))

        approaches = cur.fetchall()
        cur.close()

        has_next = len(approaches) > limit
        approaches = approaches[:limit]

        next_spotlight_count = None
        next_created_at = None
        next_id = None
        if has_next and approaches:
            last_approach = approaches[-1]
            next_spotlight_count = last_approach[7]
            next_created_at = last_approach[6]
            next_id = last_approach[0]

        approaches_with_spotlights = []
        for approach in approaches:
            spotlights = get_spotlights_for_approach(approach[0])
            approaches_with_spotlights.append(approach + (spotlights,))

        return approaches_with_spotlights, next_spotlight_count, next_created_at, next_id

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

def get_connected_posts_from_db(a_name, depth):
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT post_nodes, edges, updated_at
            FROM connected_posts
            WHERE a_name = %s AND depth = %s
            """,
            (a_name, depth)
        )
        result = cur.fetchone()
        cur.close()
        
        if result:
            post_nodes, edges, updated_at = result
            return {
                'nodes': post_nodes,
                'edges': edges,
                'updated_at': updated_at
            }
        return None

def save_connected_posts_to_db(a_name, depth, result):
    with get_db_connection() as conn:
        cur = conn.cursor()
        
        post_nodes = [node for node in result['nodes'] if node['type'] == 'post']
        comment_nodes = [node for node in result['nodes'] if node['type'] == 'comment']

        cur.execute(
            """
            INSERT INTO connected_posts (a_name, depth, post_nodes, comment_nodes, edges)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (a_name, depth) DO UPDATE
            SET post_nodes = EXCLUDED.post_nodes,
                comment_nodes = EXCLUDED.comment_nodes,
                edges = EXCLUDED.edges,
                updated_at = CURRENT_TIMESTAMP
            """,
            (a_name, depth, Json(post_nodes), Json(comment_nodes), Json(result['edges']))
        )
        
        cur.close()

def get_connected_comments_from_db(a_name, depth):
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT comment_nodes
            FROM connected_posts
            WHERE a_name = %s AND depth = %s
            """,
            (a_name, depth)
        )
        result = cur.fetchone()
        cur.close()
        
        if result:
            return {
                'nodes': result[0]
            }
        return None

def send_feedback_email(name: str, email: str, feedback: str) -> bool:
    sendgrid_api_key = os.getenv("SENDGRID_API_KEY")
    sender_email = os.getenv("SENDER_EMAIL")
    recipient_email = os.getenv("RECIPIENT_EMAIL")

    if not all([sendgrid_api_key, sender_email, recipient_email]):
        raise ValueError("SendGrid configuration is incomplete. Please check your environment variables.")

    
    message = Mail(
        from_email=sender_email,
        to_emails=recipient_email,
        subject="NAE - New Feedback Received",
        plain_text_content=f"""
        New feedback has been received on the NAE website:

        Name: {name}
        Email: {email}
        Feedback: {feedback}
        """
    )

    try:
        sg = SendGridAPIClient(sendgrid_api_key)
        response = sg.send(message)
        if response.status_code == 202:
            return True
        else:
            print(f"Error sending email: Status code {response.status_code}")
            return False
    except Exception as e:
        print(f"Error sending email: {str(e)}")
        return False

def delete_meetup_posts():
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM connected_posts WHERE LOWER(a_name) LIKE LOWER('%meetup%')")
        cur.close()

def delete_all_connected_posts():
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("TRUNCATE TABLE connected_posts")
        cur.execute("ALTER SEQUENCE IF EXISTS connected_posts_id_seq RESTART WITH 1")
        cur.close()

    conn = None
    try:
        if connection_pool is None:
            initialize_db_pool()
        conn = connection_pool.getconn()
        conn.set_session(autocommit=True)
        cur = conn.cursor()
        cur.execute("VACUUM FULL")
        cur.close()
    finally:
        if conn is not None:
            try:
                conn.set_session(autocommit=False) 
                connection_pool.putconn(conn)
            except Exception as e:
                logger.error(f"Error releasing connection: {str(e)}")
                try:
                    conn.close()
                except Exception:
                    pass

def get_pool_status() -> dict[str, Any]:
    """Get current status of the connection pool."""
    if connection_pool is None:
        return {"status": "not_initialized"}
    
    return {
        "status": "active",
        "min_connections": connection_pool.minconn,
        "max_connections": connection_pool.maxconn,
        "used_connections": len(connection_pool._used),
        "free_connections": len(connection_pool._pool)
    }