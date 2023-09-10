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


class DashboardCourseSchema(BaseModel):
    """Memrise dashboard course schema."""

    id: str
    name: str
    slug: str


class CourseSchema(BaseModel):
    """Memrise course schema."""

    id: int
    name: str
    slug: str
    url: str
    description: Optional[str]
    photo: HttpUrl
    photo_small: HttpUrl
    photo_large: HttpUrl
    num_things: int
    num_levels: int
    num_learners: int
    target_language_code: str


class DashboardCourses(BaseModel):
    """Memrise dashboard course listing schema."""

    courses: List[DashboardCourseSchema]
    has_more_pages: bool = False


class LevelSchema(BaseModel):
    """Memrise level listing schema."""

    id: int
    index: int
    kind: int
    title: str
    pool_id: int
    course_id: int
    learnable_ids: List[int] = []


class LevelListing(BaseModel):
    """Memrise level listing schema."""

    levels: List[LevelSchema]
