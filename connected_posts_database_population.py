import argparse
import asyncio
import os
from concurrent.futures import ThreadPoolExecutor

from sqlalchemy import create_engine, text
from tqdm import tqdm

from enpoints import endpoint_connected_posts, endpoint_get_articles
from utils import delete_meetup_posts

DATABASE_URL = os.getenv("DATABASE_URL")
MAX_DB_SIZE_GB = 32

def get_db_size_gb():
    engine = create_engine(DATABASE_URL)
    with engine.connect() as connection:
        result = connection.execute(text("SELECT pg_database_size(current_database()) / 1024 / 1024 / 1024 as size_gb"))
        return result.scalar()

async def store_all_articles_in_db(depth=2):
    delete_meetup_posts()
    articles = endpoint_get_articles()
    total_articles = len(articles)

    print(f"Fetching and storing data for {total_articles} articles with depth {depth}...")
    
    def process_article(article):
        try:
            if get_db_size_gb() >= MAX_DB_SIZE_GB:
                print(f"Database size limit reached ({MAX_DB_SIZE_GB}GB). Stopping population.")
                return article, False, "Database size limit reached"

            data = endpoint_connected_posts(article, depth=depth, population=True)
            print(f"Processing article: '{article}'")
            return article, True, None
        except Exception as e:
            error_message = f"Error processing article '{article}': {str(e)}"
            print(error_message)
            return article, False, error_message

    with ThreadPoolExecutor(max_workers=1) as executor:
        results = list(tqdm(executor.map(process_article, articles), total=total_articles))

    successful = [article for article, success, _ in results if success]
    failed = [(article, reason) for article, success, reason in results if not success and reason is not None]

    print(f"Successfully processed and stored {len(successful)} articles.")
    if failed:
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

if __name__ == "__main__":
    main()
