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
You need to find the best books for software engineering, AI, and related technical topics.

Generate 10 diverse search queries that will help find the best books across these categories:
- Software Engineering
- Artificial Intelligence 
- Machine Learning
- System Design
- Software Architecture
- Algorithms and Data Structures
- Programming Languages
- DevOps and Cloud
- Database Design
- Computer Science Fundamentals

Return only the query text without quotes or extra formatting.

Focus serch on getting lists so we can crawl as much as possible.
"""

def web_search(state: State) -> State:
    tavily = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))
    
    queries = state.get('queries', [])
    all_results = []
    
    for query in queries[:5]:
        clean_query = query.strip('"').strip("'")
        print(f"Searching for: {clean_query}")
        
        response = tavily.search(str(clean_query), max_results=10)
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
            for result in search_results[:20]:
                url = result['url'] if isinstance(result, dict) else result.url
                title = result['title'] if isinstance(result, dict) else result.title
                score = result['score'] if isinstance(result, dict) else result.score
                
                if url:
                    crawl_result = await crawler.arun(url=url)
                    crawled_content.append({
                        'url': url,
                        'content': crawl_result.markdown if hasattr(crawl_result, 'markdown') else str(crawl_result),
                        'title': title,
                        'score': score
                    })
            return crawled_content
    
    crawled_content = asyncio.run(crawl_urls())
    print(f"Successfully crawled {len(crawled_content)} pages")
    
    return {**state, 'crawled_content': crawled_content}


def book_finding_node(state: State) -> State:
    current_batch = state.get('current_batch', 0)
    if current_batch is None:
        current_batch = 0

    model = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    books = state.get('books', [])
    model_with_structured_output = model.with_structured_output(BookList)

    prompt = f"""
    You are a book finding assistant.
    Extract ALL books mentioned in the crawled content below.
    
    Look for books about software engineering, AI, programming, system design, etc.
    
    For each book found, provide complete details:
    - title: exact book title
    - author: book author
    - category: choose from available categories
    - url: book purchase/info URL (use Amazon if not available)
    - price: estimated price in USD (use reasonable estimate)
    - description: brief description of the book
    - image_url: book cover URL (use placeholder if not available)
    - publisher: publisher name
    - publication_date: publication date (YYYY-MM-DD format)

    Previous books found: {len(books)} books

    Crawled content:
    {inject_crawled_content(state, current_batch)}
    
    Extract ALL books mentioned in this content. Return a list of books.
    """

    response = model_with_structured_output.invoke(prompt)
    
    new_books = books.copy() if books else []
    if isinstance(response, BookList) and response.books:
        new_books.extend(response.books)
        books_found_this_batch = len(response.books)
    else:
        books_found_this_batch = 0
    
    print(f"Processed batch {current_batch + 1}, found {books_found_this_batch} books this batch, {len(new_books)} total books")
    
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