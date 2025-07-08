from state import State
from schemas import CrawledContent
from typing import List

def inject_crawled_content(state: State, current_batch: int) -> str:
    crawled_content = state.get('crawled_content', [])
    
    if not crawled_content:
        return ""
    
    batch_size = 3
    start_idx = current_batch * batch_size
    end_idx = start_idx + batch_size
    batch_content = crawled_content[start_idx:end_idx]
    
    if not batch_content:
        return ""
    
    formatted_content = []
    for item in batch_content:
        if isinstance(item, str):
            formatted_content.append(item)
        else:
            content = item.get('content', '')[:3000]
            title = item.get('title', 'No title')
            url = item.get('url', '')
            formatted_content.append(f"Title: {title}\nURL: {url}\nContent: {content}\n---\n")
    
    return "\n".join(formatted_content)

def get_total_batches(state: State) -> int:
    crawled_content = state.get('crawled_content', [])
    if not crawled_content:
        return 0
    batch_size = 3
    return (len(crawled_content) + batch_size - 1) // batch_size

def has_more_batches(state: State) -> bool:
    current_batch = state.get('current_batch', 0)
    if current_batch is None:
        current_batch = 0
    total_batches = get_total_batches(state)
    return current_batch < total_batches - 1

    