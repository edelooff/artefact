from __future__ import annotations

import json
import logging
from contextlib import contextmanager
from operator import attrgetter
from pathlib import Path
from typing import Iterator

from .http import ArchiveApi, Html
from .types import Blurb, Tag, TagType
from .utils import tag_escape

log = logging.getLogger(__name__)


class Artefact:
    def __init__(self, **kwds):
        tag_cache = kwds.pop("tag_cache", None)
        self.api = ArchiveApi(**kwds)
        self.tag_resolver = TagResolver(api=self.api, cache_file=tag_cache)

    @contextmanager
    def resolve_tags(self) -> Iterator[TagResolver]:
        previous = self.tag_resolver.auto_resolve
        self.tag_resolver.auto_resolve = True
        yield self.tag_resolver
        self.tag_resolver.auto_resolve = previous
        self.tag_resolver.save()

    def search(self, **terms) -> Iterator[Blurb]:
        params = {f"work_search[{key}]": value for key, value in terms.items()}
        print(f"searching for works with {params=}")
        page = self.api.fetch_page("/works/search", params=params)
        yield from self._paginate_blurbs(page)

    def tagged_works(self, tag) -> Iterator[Blurb]:
        page = self.api.fetch_page(f"/tags/{tag_escape(tag)}/works")
        yield from self._paginate_blurbs(page)

    def _paginate_blurbs(self, page: Html) -> Iterator[Blurb]:
        if page_links := list(page.all(".pagination a")):
            print(f"Found a total of {page_links[-2].text} pages")
        yield from self._blurbs_from_index(page)
        while (next_page_link := page.first(".pagination .next a")) is not None:
            page = self.api.fetch_page(next_page_link.attr("href"))
            yield from self._blurbs_from_index(page)

    def _blurbs_from_index(self, page: Html) -> Iterator[Blurb]:
        for blurb in page.all("ol.work.index > li"):
            yield Blurb(html=blurb, tag_resolver=self.tag_resolver)


class TagResolver:
    def __init__(self, api: ArchiveApi, *, cache_file: Path | None = None):
        """Archive tag mapper for canonical tags and their wrangled aliases."""
        self.auto_resolve = False
        self._api = api
        self._cache = {}
        self._cache_file = cache_file
        if self._cache_file is not None:
            raw_tags = json.load(open(self._cache_file))
            self._cache = {key: Tag(**value) for key, value in raw_tags.items()}

    def __call__(self, name: str, tag_type: TagType) -> Tag:
        tag = self.get(name, tag_type)
        if tag.common is None and self.auto_resolve:
            return self.resolve(name)
        return tag

    def get(self, name: str, tag_type: TagType) -> Tag:
        """Return Tag instance for given tag name, added to cache if not known."""
        tag = self._cache.setdefault(name, Tag(name=name))
        tag.type = tag_type
        return tag

    def resolve(self, name: str) -> Tag:
        """Fetches a tag (and its synonyms for common ones) from AO3."""
        print(f"Entering resolver for {name!r}")
        page = self._api.fetch_page(f"/tags/{tag_escape(name)}")

        # First: Check if the tag is common (has navigation actions)
        # This also means it has no synonyms or canonical status
        if page.first(".tag .header .navigation.actions") is None:
            return self._cache.setdefault(name, Tag(name=name, common=False))

        # Second: This is a canonical tag and might have synonyms, update
        # the ones we have cached but not yet resolved.
        self._cache[name] = tag = Tag(name=name, common=True)
        for name in map(attrgetter("text"), page.all(".synonym .tags .tag")):
            synonym = self.get(name)
            synonym.canonical = tag
            synonym.common = True
            print(f"recorded synonym: {self._cache[name]}")

        # Merged tag: check if the tag has been merged with another and resolve if so
        if (merged := page.first(".tag .merger a.tag")) is not None:
            self.resolve(merged.text)
        return tag

    def save(self, path: Path | None = None) -> None:
        """Saves the TagMapper's cache to JSON file for easy retrieval."""
        if (target_path := path or self._cache_file) is None:
            return  # Nothing to export
        tags: dict[str, bool] = {}
        canon_map: dict[str, str] = {}
        for tag in self._cache.values():
            if tag.common is not None:
                tags[tag.name] = tag.common
            if tag.canonical:
                canon_map[tag.name] = tag.canonical.name
        with open(target_path, "w") as outfile:
            json.dump({"tags": tags, "canon_map": canon_map}, outfile)
