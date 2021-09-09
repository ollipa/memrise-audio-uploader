"""Memrise SDK models."""
from typing import List, Optional

from pydantic import BaseModel, HttpUrl


class Language(BaseModel):
    """Memrise course language."""

    id: int
    slug: str
    name: str
    photo: HttpUrl
    parent_id: int
    index: int
    language_code: str


class Category(BaseModel):
    """Memrise course category."""

    name: str
    photo: HttpUrl


class CourseSchema(BaseModel):
    """Memrise course schema."""

    id: int
    name: str
    slug: str
    url: str
    description: str
    photo: HttpUrl
    photo_small: HttpUrl
    photo_large: HttpUrl
    num_things: int
    num_levels: int
    num_learners: int
    source: Language
    target: Language
    learned: int
    review: int
    ignored: int
    ltm: int
    difficult: int
    category: Category
    percent_complete: int


class CourseListing(BaseModel):
    """Memrise course listing schema."""

    courses: List[CourseSchema]
    to_review_total: int = 0
    has_more_courses: bool = False


class LevelSchema(BaseModel):
    """Memrise level listing schema."""

    id: int
    index: int
    kind: int
    title: str
    pool_id: int
    course_id: int
    mission_id: Optional[int]


class LevelListing(BaseModel):
    """Memrise level listing schema."""

    levels: List[LevelSchema]
