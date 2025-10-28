import os
import sys
import tempfile

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from app.crawler import BFSCrawler


def main():
    url = "https://www.siemens.com/global/en/products/automation/systems/industrial/plc/s7-1200.html"
    crawler = BFSCrawler(root_url=url, max_depth=3, include_images=False, max_pages=80)
    pages, file_urls = crawler.crawl()
    print({"pages": len(pages), "files": len(file_urls)})
    for i, f in enumerate(sorted(list(file_urls))[:10], 1):
        print(f"FILE[{i}]: {f}")

    # Optional small download test
    tmp = os.path.join(tempfile.gettempdir(), "crawler-test")
    items = crawler.download_all(dest_dir=tmp, max_size_mb=25, max_workers=4)
    ok = sum(1 for it in items if it.status == "success")
    print({"download_success": ok, "download_total": len(items), "dest": tmp})


if __name__ == "__main__":
    main()
