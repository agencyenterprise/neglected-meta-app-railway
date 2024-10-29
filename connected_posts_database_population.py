import argparse
import asyncio
import os
from datetime import datetime, timezone

from sqlalchemy import create_engine, text
from tqdm import tqdm

from enpoints import endpoint_connected_posts, endpoint_get_articles
from utils import close_db_pool, delete_meetup_posts, get_db_connection

DATABASE_URL = os.getenv("DATABASE_URL")
MAX_DB_SIZE_GB = 48

def get_db_size_gb():
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT pg_database_size(current_database()) / 1024 / 1024 / 1024 as size_gb")
        result = cur.fetchone()
        cur.close()
        return result[0]

async def store_all_articles_in_db(depth=2):
    try:
        delete_meetup_posts()
        articles = endpoint_get_articles()
        total_articles = len(articles)

        print(f"Fetching and storing data for {total_articles} articles with depth {depth}...")
        
        successful = []
        failed = []

        for article in tqdm(articles, total=total_articles):
            try:
                if get_db_size_gb() >= MAX_DB_SIZE_GB:
                    print(f"Database size limit reached ({MAX_DB_SIZE_GB}GB). Stopping population.")
                    break

                data = endpoint_connected_posts(article, depth=depth, population=True)
                successful.append(article)
                print(f"Successfully processed article: '{article}'")
                
                # Add a small delay between operations
                await asyncio.sleep(0.1)
                
            except Exception as e:
                error_message = f"Error processing article '{article}': {str(e)}"
                print(error_message)
                failed.append((article, error_message))

        print(f"Successfully processed and stored {len(successful)} articles.")
        if failed:
            print(f"Failed to process {len(failed)} articles.")

        return successful, failed
    finally:
        print("Finalizing database population")

def main():
    parser = argparse.ArgumentParser(description="Populate database with connected posts.")
    parser.add_argument("--depth", type=int, default=2, help="Depth for connected posts (default: 2)")
    args = parser.parse_args()

    initial_size = get_db_size_gb()
    if initial_size >= MAX_DB_SIZE_GB:
        print(f"Database is already {initial_size:.2f}GB. Maximum size ({MAX_DB_SIZE_GB}GB) reached or exceeded. Aborting population.")
        return

    print(f"Starting to search for the target article with depth {args.depth}...")
    print(f"Initial database size: {initial_size:.2f}GB")

    successful, failed = asyncio.run(store_all_articles_in_db(depth=args.depth))
    
    final_size = get_db_size_gb()
    print(f"Final database size: {final_size:.2f}GB")
    print(f"Successful articles: {len(successful)}")
    
    if failed:
        print("Failed articles:")
        for article, reason in failed:
            print(f"  - {article}: {reason}")
    else:
        print("No articles failed due to errors.")

    close_db_pool()

if __name__ == "__main__":
    main()
