import os
import json
from nodes import web_search, should_continue_processing, book_finding_node, save_books_node
from state import State
from langgraph.graph import START, END, StateGraph
from nodes import initial_node, crawler_node

def main():

    graph_builder = StateGraph(State)

    graph_builder.add_node("initial", initial_node)
    graph_builder.add_node("web_search", web_search)
    graph_builder.add_node("crawler", crawler_node)
    graph_builder.add_node("book_finding", book_finding_node)
    graph_builder.add_node("save_books", save_books_node)

    graph_builder.add_edge(START, "initial")
    graph_builder.add_edge("initial", "web_search")
    graph_builder.add_edge("web_search", "crawler")
    graph_builder.add_edge("crawler", "book_finding")
    graph_builder.add_edge("save_books", END)
    
    graph_builder.add_conditional_edges(
        "book_finding",
        should_continue_processing,
        {
            "book_finding": "book_finding",
            "save_books": "save_books"
        }
    )

    graph = graph_builder.compile()

    initial_state: State = {
        'books': [],
        'search_results': [],
        'queries': None,
        'crawled_content': None,
        'current_batch': 0
    }

    config = {"recursion_limit": 100}
    result = graph.invoke(initial_state, config=config)

    # Print the results
    print("=== GRAPH EXECUTION RESULT ===")
    print(f"Generated queries: {result.get('queries', [])}")
    print(f"Number of search results: {len(result.get('search_results', []))}")
    print(f"Number of crawled pages: {len(result.get('crawled_content', []))}")
    print(f"Total batches processed: {result.get('current_batch', 0)}")
    print(f"Books found: {len(result.get('books', []))}")
    
    # Print found books
    books = result.get('books', [])
    if books:
        print("\n=== FOUND BOOKS ===")
        for i, book in enumerate(books):
            print(f"{i+1}. {book.title if hasattr(book, 'title') else 'Unknown Title'}")
            print(f"   Author: {book.author if hasattr(book, 'author') else 'Unknown Author'}")
            print(f"   Category: {book.category if hasattr(book, 'category') else 'Unknown Category'}")
            print()

if __name__ == "__main__":
    main()