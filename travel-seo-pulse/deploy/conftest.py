"""Test scaffolding: stub heavy feed dependencies so feed_puller imports
in environments without feedparser (the VPS venv has the real one)."""
import sys
import types

if "feedparser" not in sys.modules:
    try:
        import feedparser  # noqa: F401
    except ImportError:
        stub = types.ModuleType("feedparser")
        stub.parse = lambda *a, **k: types.SimpleNamespace(bozo=1, entries=[])
        sys.modules["feedparser"] = stub
