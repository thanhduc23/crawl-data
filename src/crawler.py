"""
Module for crawling data from VnExpress.net

Classes:
    BaseCrawler: Base class providing fundamental crawling methods
    NewsCrawler: Main class for crawling articles from VnExpress
"""

import requests
from bs4 import BeautifulSoup
import time
from datetime import datetime, timedelta
import logging
import json
import random
import os

class BaseCrawler:
    """
    Base class providing fundamental crawling methods.
    
    Attributes:
        headers (dict): HTTP request headers
        session (requests.Session): Session for connection reuse
        max_retries (int): Maximum number of retry attempts
        retry_delay (int): Delay between retries in seconds
    """

    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        self.session = requests.Session()
        self.max_retries = 3
        self.retry_delay = 5
    
    def get_page(self, url, retry_count=0):
        """
        Get HTML content of a webpage with retry mechanism.

        Args:
            url (str): URL of the target page
            retry_count (int): Number of retry attempts made

        Returns:
            str: HTML content of the page, None if failed
        """
        try:
            # Random delay between 2-5 seconds
            time.sleep(random.uniform(2, 5))
            
            response = self.session.get(url, headers=self.headers)
            response.raise_for_status()
            return response.text
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429 and retry_count < self.max_retries:
                # If too many requests, wait and retry
                wait_time = self.retry_delay * (retry_count + 1)
                self.logger.warning(f"Too many requests, waiting {wait_time} seconds before retry...")
                time.sleep(wait_time)
                return self.get_page(url, retry_count + 1)
            else:
                self.logger.error(f"Error fetching {url}: {str(e)}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error fetching {url}: {str(e)}")
            return None

class NewsCrawler(BaseCrawler):
    """
    Main class for crawling articles from VnExpress.
    
    Attributes:
        logger (Logger): Logger instance for logging
        crawled_urls (set): Set of already crawled URLs
        data_file (str): Path to JSON data file
        articles (list): List of crawled articles
    """

    def __init__(self):
        """Khởi tạo crawler với các thiết lập cơ bản"""
        super().__init__()
        self.logger = logging.getLogger(__name__)
        self.crawled_urls = set()  # Lưu các URL đã crawl
        self.data_file = 'data/vnexpress_articles.json'
        
        # Tạo thư mục data nếu chưa có
        os.makedirs('data', exist_ok=True)
        
        # Load dữ liệu đã crawl từ file (nếu có)
        self.articles = self.load_articles()
        
    def load_articles(self):
        """
        Load articles from JSON file.

        Returns:
            list: List of articles, empty list if file doesn't exist
        """
        try:
            if os.path.exists(self.data_file):
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    articles = json.load(f)
                    # Thêm các URL đã crawl vào set
                    self.crawled_urls.update(article['url'] for article in articles)
                    self.logger.info(f"Loaded {len(articles)} articles from {self.data_file}")
                    return articles[:5]
        except Exception as e:
            self.logger.error(f"Error loading articles: {str(e)}")
        return []
        
    def save_articles_to_json(self, new_articles):
        """
        Save new articles to JSON file.

        Args:
            new_articles (list): List of new articles to save
        """
        try:
            # Thêm bài mới vào danh sách hiện có
            self.articles.extend(new_articles)
            
            # Lưu toàn bộ danh sách vào file
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(self.articles, f, ensure_ascii=False, indent=2)
            self.logger.info(f"Saved {len(self.articles)} articles to {self.data_file}")
            
        except Exception as e:
            self.logger.error(f"Error saving to file: {str(e)}")
            
    def is_crawled(self, url):
        """
        Check if URL has been crawled.

        Args:
            url (str): URL to check

        Returns:
            bool: True if already crawled, False otherwise
        """
        return url in self.crawled_urls
        
    def parse_article(self, html, url):
        """
        Parse article content from HTML.

        Args:
            html (str): HTML content of the page
            url (str): URL of the article

        Returns:
            dict: Article data including:
                - title: article title
                - content: article content
                - publish_date: Unix timestamp of publish date
                - crawled_at: Unix timestamp of crawl time
                - url: article URL
                None if parsing fails
        """
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # Selectors for VnExpress
            title = soup.select_one('h1.title-detail')
            content = soup.select_one('article.fck_detail')
            publish_date = soup.select_one('.header-content .date')
            description = soup.select_one('p.description')
            
            # Log for debugging
            self.logger.info(f"Parsing article: {url}")
            self.logger.info(f"Title found: {title is not None}")
            self.logger.info(f"Content found: {content is not None}")
            self.logger.info(f"Date found: {publish_date is not None}")
            
            # Process article content
            content_text = ''
            if content:
                for div in content.select('.box_embed_video, .box_ins_readmore'):
                    div.decompose()
                    
                paragraphs = content.select('p')
                content_text = '\n'.join([p.text.strip() for p in paragraphs if p.text.strip()])
                
                if description:
                    content_text = description.text.strip() + '\n\n' + content_text
            
            # Validate required data
            if not title or not content_text or not publish_date:
                self.logger.warning(f"Missing required data for {url}")
                self.logger.warning(f"Title: {title.text if title else 'None'}")
                self.logger.warning(f"Content length: {len(content_text) if content_text else 0}")
                self.logger.warning(f"Date: {publish_date.text if publish_date else 'None'}")
                return None
            
            # Convert publish date to Unix timestamp
            date_str = publish_date.text.strip()
            publish_timestamp = self.convert_date_to_timestamp(date_str)
            if not publish_timestamp:
                self.logger.error(f"Failed to parse publish date: {date_str}")
                return None
                
            article_data = {
                'title': title.text.strip(),
                'content': content_text,
                'publish_date': publish_timestamp,  # Unix timestamp
                'crawled_at': int(datetime.now().timestamp()),  # Current Unix timestamp
                'url': url
            }
            
            self.logger.info(f"Successfully parsed article: {article_data['title']}")
            self.logger.info(f"Publish timestamp: {article_data['publish_date']}")
            return article_data
            
        except Exception as e:
            self.logger.error(f"Error parsing article {url}: {str(e)}")
            return None

    def convert_date_to_timestamp(self, date_str):
        """
        Convert VnExpress date string to Unix timestamp.

        Args:
            date_str (str): Date string (e.g. "Thứ năm, 21/2/2025, 09:56 (GMT+7)")

        Returns:
            int: Unix timestamp, None if parsing fails
        """
        try:
            # Split by comma and get the date part
            date_parts = date_str.split(',')
            if len(date_parts) >= 3:
                # Get date and time parts
                date_part = date_parts[1].strip()  # "21/2/2025"
                time_part = date_parts[2].split('(')[0].strip()  # "09:56"
                
                # Combine date and time
                datetime_str = f"{date_part} {time_part}"
                # Parse datetime
                dt = datetime.strptime(datetime_str, '%d/%m/%Y %H:%M')
                # Convert to timestamp
                return int(dt.timestamp())
                
            return None
            
        except Exception as e:
            self.logger.error(f"Error converting date {date_str}: {str(e)}")
            return None

    def is_within_days(self, publish_timestamp, days=7):
        """
        Check if article is within specified time range.

        Args:
            publish_timestamp (int): Article publish timestamp
            days (int): Number of days to check (default: 7)

        Returns:
            bool: True if article is within time range
        """
        try:
            # Calculate timestamps
            now = int(datetime.now().timestamp())
            days_ago = int((datetime.now() - timedelta(days=days)).timestamp())
            
            # Check if article is within range
            return days_ago <= publish_timestamp <= now
            
        except Exception as e:
            self.logger.error(f"Error checking date range: {str(e)}")
            return False

    def crawl_article(self, url):
        """
        Crawl a single article from URL.

        Args:
            url (str): Article URL to crawl

        Returns:
            dict: Article data, None if failed or already crawled
        """
        if self.is_crawled(url):
            self.logger.info(f"URL {url} đã được crawl trước đó")
            return None
        
        html = self.get_page(url)
        if html:
            article_data = self.parse_article(html, url)
            if article_data:
                self.crawled_urls.add(url)
                return article_data
        return None
        
    def crawl_multiple_articles(self, urls, delay=2):
        """Crawl nhiều bài viết từ danh sách URL"""
        articles = []
        for url in urls:
            article = self.crawl_article(url)
            if article:
                articles.append(article)
                # Random delay between delay and delay*2 seconds
                time.sleep(random.uniform(delay, delay*2))
        return articles

    def get_article_list(self, category_url):
        """
        Get list of article URLs from a category page.

        Args:
            category_url (str): URL of the category page

        Returns:
            list: List of article URLs
        """
        try:
            html = self.get_page(category_url)
            if not html:
                return []
                
            soup = BeautifulSoup(html, 'html.parser')
            articles = soup.select('article.item-news')
            
            article_list = []
            for article in articles:
                link = article.select_one('h3.title-news > a')
                if link and 'href' in link.attrs:
                    url = link['href']
                    if 'vnexpress.net' in url:
                        article_list.append(url)
            
            return article_list  # Lấy hết tất cả các bài viết
            
        except Exception as e:
            self.logger.error(f"Error getting article list: {str(e)}")
            return []
