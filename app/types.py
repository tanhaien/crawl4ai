from dataclasses import dataclass
from typing import Optional


@dataclass
class CrawlItem:
    source_page_url: str
    file_url: str
    local_path: Optional[str]
    filename: Optional[str]
    mime_type: Optional[str]
    size_bytes: Optional[int]
    status: str  # success | skipped | failed
    error: Optional[str]
