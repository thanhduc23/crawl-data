"""
Main script for running VnExpress crawler.

This script:
1. Crawls articles from configured categories
2. Filters articles within specified time range
3. Saves data to JSON file
4. Prints crawling statistics
"""

import logging
from datetime import datetime
import time
import random
from src.crawler import NewsCrawler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def main():
    """
    Main function to run the crawler.
    
    Process:
    1. Initialize crawler
    2. Get article URLs from category pages
    3. Crawl each article with delay
    4. Save new articles to JSON file
    5. Print statistics
    """
    # Initialize crawler
    crawler = NewsCrawler()
    
    # List of category URLs to crawl
    category_urls = [
        'https://vnexpress.net/oto-xe-may',
    ]
    
    new_articles = []  # List of new articles
    failed_urls = []   # List of failed URLs
    
    # Crawl each category
    for category_url in category_urls:
        logging.info(f"\nCrawling category: {category_url}")
        
        try:
            # Get list of article URLs
            article_urls = crawler.get_article_list(category_url)
            logging.info(f"Found {len(article_urls)} articles in category")
            
            # Crawl each article with delay
            for url in article_urls:
                # Check if URL was already crawled
                if crawler.is_crawled(url):
                    logging.info(f"Already crawled: {url}")
                    continue
                    
                try:
                    logging.info(f"\nProcessing article: {url}")
                    article = crawler.crawl_article(url)
                    
                    if article and article['content'] and article['publish_date']:
                        # Check if article is within 7 days
                        if crawler.is_within_days(article['publish_date'], days=7):
                            filtered_article = {
                                'url': article['url'],
                                'title': article['title'],
                                'content': article['content'],
                                'publish_date': article['publish_date']
                            }
                            new_articles.append(filtered_article)
                            crawler.crawled_urls.add(url)
                            logging.info(f"Successfully crawled: {article['title']}")
                        else:
                            logging.info("Article too old, skipping...")
                    else:
                        logging.warning(f"Failed to crawl article: {url}")
                        failed_urls.append(url)
                        
                except Exception as e:
                    logging.error(f"Error processing article {url}: {str(e)}")
                    failed_urls.append(url)
                    continue
                
                # Random delay between 3-6 seconds between articles
                time.sleep(random.uniform(3, 6))
                
        except Exception as e:
            logging.error(f"Error processing category {category_url}: {str(e)}")
            continue
    
    # Save new articles to file
    if new_articles:
        crawler.save_articles_to_json(new_articles)
    
    # Print statistics
    print(f"\n=== Crawling Results ===")
    print(f"Existing articles: {len(crawler.articles) - len(new_articles)}")
    print(f"New articles: {len(new_articles)}")
    print(f"Total articles: {len(crawler.articles)}")
    print(f"Failed URLs: {len(failed_urls)}")
    if failed_urls:
        print("\nFailed URLs:")
        for url in failed_urls:
            print(f"- {url}")
    print(f"\nOutput file: {crawler.data_file}")

if __name__ == "__main__":
    main()
