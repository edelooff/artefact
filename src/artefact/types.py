from __future__ import annotations

from dataclasses import dataclass
from functools import cached_property
from typing import TYPE_CHECKING

from .http import Html
from .utils import unwrap

if TYPE_CHECKING:
    from .core import TagResolver


class Blurb:
    def __init__(self, html: Html, tag_resolver: TagResolver):
        self._html = html
        self._tag_resolver = tag_resolver

    @cached_property
    def url(self) -> str:
        work_link = unwrap(self._html.first("h4.heading a"))
        return unwrap(work_link.attr("href"))

    @cached_property
    def title(self) -> str:
        return unwrap(self._html.first("h4.heading a")).text

    @cached_property
    def author(self) -> str | None:
        author = self._html.first("a[rel=author]")
        return None if author is None else author.text

    @cached_property
    def language(self) -> str:
        return unwrap(self._html.first(".stats dd.language")).text

    @cached_property
    def status(self) -> str:
        return unwrap(self._html.first(".required-tags .iswip span")).text

    @cached_property
    def words(self) -> int:
        words = unwrap(self._html.first(".stats dd.words")).text
        return int(words.replace(",", ""))

    @cached_property
    def rating(self) -> str:
        return unwrap(self._html.first(".required-tags .rating span")).text

    @cached_property
    def summary(self) -> str:
        return "\n\n".join(para.text for para in self._html.all(".summary p"))

    @cached_property
    def complete(self) -> bool:
        return self.status == "Complete Work"

    @cached_property
    def tags(self) -> WorkTags:
        def texts_at_path(query: str) -> set[Tag]:
            return {self._tag_resolver(tag.text) for tag in self._html.all(query)}

        return WorkTags(
            warning=texts_at_path(".tags .warnings a"),
            relationship=texts_at_path(".tags .relationships a"),
            character=texts_at_path(".tags .characters a"),
            freeform=texts_at_path(".tags .freeforms a"),
        )


@dataclass
class Tag:
    name: str
    common: bool | None = None
    canonical: Tag | None = None

    def __hash__(self) -> int:
        return hash(self.name)

    def __lt__(self, other) -> bool:
        if not isinstance(other, Tag):
            return NotImplemented
        return self.name.lower() < other.name.lower()


@dataclass
class WorkTags:
    character: set[Tag]
    freeform: set[Tag]
    relationship: set[Tag]
    warning: set[Tag]
