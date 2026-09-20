from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Field:
    name: str
    label: str
    type: str  # text | multiline | image | list_of_str | bool | url | nested_links
    required: bool = True
    sub_fields: Optional[List[str]] = None  # only for nested_links, e.g. ["spotify", "appleMusic"]


@dataclass
class ContentType:
    key: str
    label: str
    json_file: str
    fields: List[Field]
    supports_placeholder: bool = True


CONTENT_TYPES = {
    "games": ContentType(
        key="games",
        label="Game Projects",
        json_file="projects.json",
        supports_placeholder=False,
        fields=[
            Field("title", "Title", "text"),
            Field("image", "Image", "image"),
            Field("alt", "Alt Text", "text"),
            Field("description", "Description", "multiline"),
            Field("tools", "Tools", "list_of_str"),
            Field("link", "Link", "url"),
            Field("featured", "Featured", "bool", required=False),
            Field("hidden", "Hidden", "bool", required=False),
        ],
    ),
    "art": ContentType(
        key="art",
        label="Art",
        json_file="art.json",
        fields=[
            Field("title", "Title", "text"),
            Field("image", "Image", "image"),
            Field("alt", "Alt Text", "text"),
            Field("type", "Type", "text"),
            Field("description", "Description", "multiline"),
            Field("hidden", "Hidden", "bool", required=False),
        ],
    ),
    "music": ContentType(
        key="music",
        label="Music",
        json_file="music.json",
        fields=[
            Field("title", "Title", "text"),
            Field("image", "Image", "image"),
            Field("alt", "Alt Text", "text"),
            Field("genre", "Genre", "text"),
            Field("description", "Description", "multiline"),
            Field("links", "Listen Links", "nested_links", sub_fields=["spotify", "appleMusic"]),
            Field("hidden", "Hidden", "bool", required=False),
        ],
    ),
    "models": ContentType(
        key="models",
        label="3D Models",
        json_file="models.json",
        fields=[
            Field("title", "Title", "text"),
            Field("image", "Image", "image"),
            Field("alt", "Alt Text", "text"),
            Field("software", "Software", "text"),
            Field("description", "Description", "multiline"),
            Field("link", "Link", "url"),
            Field("hidden", "Hidden", "bool", required=False),
        ],
    ),
}
