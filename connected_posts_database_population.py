import argparse
import asyncio
import os
from concurrent.futures import ThreadPoolExecutor

from sqlalchemy import create_engine, text
from tqdm import tqdm

from enpoints import endpoint_connected_posts, endpoint_get_articles

DATABASE_URL = os.getenv("DATABASE_URL")
MAX_DB_SIZE_GB = 32

def get_db_size_gb():
    engine = create_engine(DATABASE_URL)
    with engine.connect() as connection:
        result = connection.execute(text("SELECT pg_database_size(current_database()) / 1024 / 1024 / 1024 as size_gb"))
        return result.scalar()

async def store_all_articles_in_db(depth=2):
    articles = endpoint_get_articles()
    total_articles = len(articles)
    
    print(f"Fetching and storing data for {total_articles} articles with depth {depth}...")

    def process_article(article):
        try:
            if get_db_size_gb() >= MAX_DB_SIZE_GB:
                print(f"Database size limit reached ({MAX_DB_SIZE_GB}GB). Stopping population.")
                return article, False
            data = endpoint_connected_posts(article, depth=depth, population=True)
            return article, True
        except Exception as e:
            print(f"Error processing article '{article}': {str(e)}")
            return article, False

    with ThreadPoolExecutor(max_workers=10) as executor:
        results = list(tqdm(executor.map(process_article, articles), total=total_articles))
        if any(not success for _, success in results):
            if get_db_size_gb() >= MAX_DB_SIZE_GB:
                print(f"Database size limit reached ({MAX_DB_SIZE_GB}GB). Stopping population.")

    successful = [article for article, success in results if success]
    failed = [article for article, success in results if not success]

    print(f"Successfully processed and stored {len(successful)} articles.")
    print(f"Failed to process {len(failed)} articles.")

    return successful, failed

def main():
    parser = argparse.ArgumentParser(description="Populate database with connected posts.")
    parser.add_argument("--depth", type=int, default=2, help="Depth for connected posts (default: 2)")
    args = parser.parse_args()

    initial_size = get_db_size_gb()
    if initial_size >= MAX_DB_SIZE_GB:
        print(f"Database is already {initial_size:.2f}GB. Maximum size ({MAX_DB_SIZE_GB}GB) reached or exceeded. Aborting population.")
        return

    print(f"Starting to store {len(endpoint_get_articles())} articles in the database with depth {args.depth}...")
    print(f"Initial database size: {initial_size:.2f}GB")

    successful, failed = asyncio.run(store_all_articles_in_db(depth=args.depth))
    
    final_size = get_db_size_gb()
    print(f"Final database size: {final_size:.2f}GB")
    print(f"Successful articles: {len(successful)}")
    print(f"Failed articles: {len(failed)}")
    
    if failed:
        print("Failed articles:")
        for article in failed:
            print(f"  - {article}")

if __name__ == "__main__":
    main()
