from pydantic import BaseModel
from enum import Enum
from typing import Optional, Any, List

class Category(Enum):
    PROGRAMMING = "programming"
    SOFTWARE_ENGINEERING = "software_engineering"
    ALGORITHMS = "algorithms"
    SYSTEM_DESIGN = "system_design"
    AI = "ai"
    MACHINE_LEARNING = "machine_learning"
    SOFTWARE_ARCHITECTURE = "software_architecture"
    DEVOPS = "devops"
    DATABASE_DESIGN = "database_design"
    COMPUTER_SCIENCE = "computer_science"
    CLOUD_COMPUTING = "cloud_computing"
    DATA_STRUCTURES = "data_structures"

class SearchResult(BaseModel):
    url: str
    title: str
    content: str
    score: float
    raw_content: Optional[str] = None

    def __getitem__(self, key: str) -> Any:
        return getattr(self, key)

class Book(BaseModel):
    title: str
    category: Category
    url: str
    price: float
    description: str
    image_url: str
    publisher: str
    publication_date: str
    author: str

class BookList(BaseModel):
    books: List[Book]

class CrawledContent(BaseModel):
    url: str
    content: str
    title: str
    score: float