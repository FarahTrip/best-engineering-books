from turtle import mode
from tavily import TavilyClient
import os
from schemas import Book, SearchResult, BookList
from typing import List
from state import State
from pydantic import BaseModel
from langchain.chat_models import init_chat_model
from langchain_openai import ChatOpenAI
from crawl4ai import AsyncWebCrawler
from utility import inject_crawled_content, has_more_batches
import json

class QuerySchema(BaseModel):
    queries: List[str]

prompt = """
Generate 15 specific search queries to find the highest quality engineering books from authoritative sources.

Target these specific sources and topics:
- "best software engineering books reddit programming"
- "top computer science books university curriculum"
- "essential algorithms books competitive programming"
- "system design books senior engineer interview"
- "machine learning books stanford mit course"
- "software architecture books microservices distributed systems"
- "database design books postgresql mysql performance"
- "devops books kubernetes docker cloud native"
- "programming language books rust golang python advanced"
- "clean code books uncle bob martin fowler"
- "data structures algorithms books sedgewick cormen"
- "artificial intelligence books russell norvig"
- "deep learning books goodfellow bengio"
- "functional programming books haskell scala clojure"
- "operating systems books tanenbaum silberschatz"

Focus on classic, authoritative, and highly-rated technical books.
"""

def web_search(state: State) -> State:
    tavily = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))
    
    queries = state.get('queries', [])
    all_results = []
    
    for query in queries[:8]:
        clean_query = query.strip('"').strip("'")
        print(f"Searching for: {clean_query}")
        
        response = tavily.search(str(clean_query), max_results=15)
        if response and 'results' in response:
            all_results.extend(response['results'])
    
    print(f"Total search results collected: {len(all_results)}")
    return {**state, "search_results": all_results}


def initial_node(state: State) -> State:

    api_key = os.getenv("OPENAI_API_KEY")

    if not api_key:
        raise ValueError("OPENAI_API_KEY is not set")

    model = ChatOpenAI(model="gpt-4o", temperature=0)

    structured_model = model.with_structured_output(QuerySchema)
    
    response = structured_model.invoke(prompt)
    
    return {
        **state,
        'queries': getattr(response, 'queries', [])
    }


import asyncio

def crawler_node(state: State) -> State:
    search_results = state.get('search_results', [])
    
    async def crawl_urls():
        async with AsyncWebCrawler() as crawler:
            crawled_content = []
            for result in search_results[:15]:
                url = result['url'] if isinstance(result, dict) else result.url
                title = result['title'] if isinstance(result, dict) else result.title
                score = result['score'] if isinstance(result, dict) else result.score
                
                if url and not any(skip in url.lower() for skip in ['youtube.com', 'reddit.com/r/', 'twitter.com', 'linkedin.com']):
                    try:
                        crawl_result = await crawler.arun(url=url)
                        crawled_content.append({
                            'url': url,
                            'content': crawl_result.markdown if hasattr(crawl_result, 'markdown') else str(crawl_result),
                            'title': title,
                            'score': score
                        })
                    except Exception as e:
                        print(f"Failed to crawl {url}: {e}")
                        continue
            return crawled_content
    
    crawled_content = asyncio.run(crawl_urls())
    print(f"Successfully crawled {len(crawled_content)} pages")
    
    return {**state, 'crawled_content': crawled_content}


def book_finding_node(state: State) -> State:
    current_batch = state.get('current_batch', 0)
    if current_batch is None:
        current_batch = 0

    model = ChatOpenAI(model="gpt-4o-mini", temperature=0, timeout=30)
    books = state.get('books', [])
    model_with_structured_output = model.with_structured_output(BookList)

    existing_titles = [book.title if hasattr(book, 'title') else str(book) for book in books]

    content = inject_crawled_content(state, current_batch)
    if len(content) > 8000:
        content = content[:8000] + "... [truncated]"

    prompt = f"""
    Extract ONLY high-quality, authoritative technical books from the content below.

    STRICT CRITERIA:
    - Only include books with specific author names and publication details
    - Focus on classic, well-known technical books (like Clean Code, Design Patterns, SICP, etc.)
    - Skip generic articles, blog posts, or vague book mentions
    - Only include books from reputable publishers (O'Reilly, MIT Press, Addison-Wesley, etc.)
    - Avoid duplicates - these titles already exist: {existing_titles[:5]}

    PRIORITIZE these types of books:
    - Classic computer science textbooks
    - Authoritative programming language books
    - Fundamental algorithms and data structures books
    - System design and architecture books
    - Well-known software engineering books

    Content to analyze:
    {content}
    
    Return only books that meet the strict quality criteria above.
    """

    try:
        response = model_with_structured_output.invoke(prompt)
        
        new_books = books.copy() if books else []
        if isinstance(response, BookList) and response.books:
            filtered_books = []
            for book in response.books:
                book_title = book.title if hasattr(book, 'title') else str(book)
                if book_title not in existing_titles and len(book_title) > 5:
                    filtered_books.append(book)
                    existing_titles.append(book_title)
            
            new_books.extend(filtered_books)
            books_found_this_batch = len(filtered_books)
        else:
            books_found_this_batch = 0
            
        print(f"Processed batch {current_batch + 1}, found {books_found_this_batch} quality books this batch, {len(new_books)} total books")
        
    except Exception as e:
        print(f"Error processing batch {current_batch + 1}: {e}")
        new_books = books
        
    return {
        **state, 
        'books': new_books,
        'current_batch': current_batch + 1
    }

def save_books_node(state: State) -> State:
    books = state.get('books', [])
    
    books_data = []
    for book in books:
        if hasattr(book, 'dict'):
            book_dict = book.dict()
            if 'category' in book_dict and hasattr(book_dict['category'], 'value'):
                book_dict['category'] = book_dict['category'].value
            books_data.append(book_dict)
        else:
            books_data.append(book)
    
    with open('books.json', 'w') as f:
        json.dump(books_data, f, indent=2, default=str)
    
    print(f"Saved {len(books_data)} books to books.json")
    return state

def should_continue_processing(state: State) -> str:
    if has_more_batches(state):
        return "book_finding"
    else:
        return "save_books"