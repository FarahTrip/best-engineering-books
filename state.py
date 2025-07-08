from typing import List, Dict, Any, TypedDict, Optional
from schemas import Book, SearchResult

class State(TypedDict):
    books: List[Book]
    search_results: List[SearchResult]
    queries: Optional[List[str]]
    crawled_content: Optional[List[str]]
    current_batch: Optional[int]