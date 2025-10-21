import asyncio
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig
from crawl4ai.deep_crawling import BFSDeepCrawlStrategy
from crawl4ai.content_scraping_strategy import LXMLWebScrapingStrategy
from crawl4ai.deep_crawling.filters import (
    FilterChain,
    DomainFilter,
    URLPatternFilter,
    ContentTypeFilter
)

async def main():

    filter_chain = FilterChain([
        # Domain boundaries
        DomainFilter(
            allowed_domains=["www.mitsubishi-electric.vn"],
        ),

        # URL patterns to include
        URLPatternFilter(patterns=["*"]),

        # Content type filtering
        ContentTypeFilter(allowed_types=["text/html"])
    ])
    # Configure a 2-level deep crawl
    config = CrawlerRunConfig(
        deep_crawl_strategy=BFSDeepCrawlStrategy(
            max_depth=10, 
            include_external=False,
            max_pages=100,
            filter_chain=filter_chain

        ),
        scraping_strategy=LXMLWebScrapingStrategy(),
        verbose=True
    )

    async with AsyncWebCrawler() as crawler:
        results = await crawler.arun("https://www.mitsubishi-electric.vn/", config=config)

        print(f"Crawled {len(results)} pages in total")

        # Access individual results
        with open(f"crawl_data/www.mitsubishi-electric.vn.md", "w") as f:
            for result in results:  # Show first 3 results

                if result.markdown is not None:
                    f.write(result.markdown)
                print(f"URL: {result.url}")
                print(f"Depth: {result.metadata.get('depth', 0)}")
                print(f"Title: {result.metadata.get('title', '')}")
                print(f"Description: {result.metadata.get('description', '')}")
                print(f"Keywords: {result.metadata.get('keywords', '')}")
                print(f"Author: {result.metadata.get('author', '')}")

if __name__ == "__main__":
    asyncio.run(main())
