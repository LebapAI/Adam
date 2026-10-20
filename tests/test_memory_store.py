"""Tests for Adam's opt-in local memory store."""
import os

import pytest

from memory_store import MemoryStore


def test_memory_can_be_saved_listed_and_searched(tmp_path):
    store = MemoryStore(str(tmp_path / "memory.sqlite3"))
    memory_id = store.remember("Owner prefers concise answers", "preference")

    assert memory_id == 1
    assert store.list_recent()[0]["content"] == "Owner prefers concise answers"
    assert store.search("CONCISE")[0]["category"] == "preference"


def test_memory_store_uses_restrictive_permissions_on_posix(tmp_path):
    store = MemoryStore(str(tmp_path / "memory.sqlite3"))
    store.remember("local only")

    if os.name == "posix":
        assert (tmp_path / "memory.sqlite3").stat().st_mode & 0o777 == 0o600


def test_memory_rejects_empty_oversized_and_nul_content(tmp_path):
    store = MemoryStore(str(tmp_path / "memory.sqlite3"))

    with pytest.raises(ValueError):
        store.remember("  ")
    with pytest.raises(ValueError):
        store.remember("x" * 8001)
    with pytest.raises(ValueError):
        store.remember("unsafe\x00text")


def test_memory_search_treats_wildcards_as_literal(tmp_path):
    store = MemoryStore(str(tmp_path / "memory.sqlite3"))
    store.remember("literal 100% safe")
    store.remember("literal 1000 safe")

    assert len(store.search("100%")) == 1


def test_memory_rejects_symlink_database(tmp_path):
    target = tmp_path / "target.sqlite3"
    target.write_text("not a database", encoding="utf-8")
    link = tmp_path / "memory.sqlite3"
    link.symlink_to(target)

    with pytest.raises(OSError, match="symbolic link"):
        MemoryStore(str(link)).list_recent()


def test_memory_does_not_create_missing_parent_directory(tmp_path):
    store = MemoryStore(str(tmp_path / "missing" / "memory.sqlite3"))

    with pytest.raises(OSError, match="directory"):
        store.remember("hello")
