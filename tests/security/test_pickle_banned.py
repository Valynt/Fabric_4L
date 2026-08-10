"""Static security regression tests: pickle serialization is banned in cache.py.

These tests analyze source code directly — no Redis, no runtime dependencies.
They fail if pickle serialization is ever reintroduced.
"""

import ast
import importlib.util
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
CACHE_PY = REPO_ROOT / "services" / "layer3-knowledge" / "src" / "performance" / "cache.py"


def _load_cache_module():
    """Load cache.py directly without package relative import issues."""
    spec = importlib.util.spec_from_file_location("performance_cache", CACHE_PY)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestPickleBanned:
    """P0: pickle serialization must never be used in cache modules."""

    @pytest.mark.security
    def test_cache_source_never_imports_pickle(self):
        """cache.py must not import pickle module."""
        source = CACHE_PY.read_text(encoding="utf-8")

        # Parse AST to find import statements
        tree = ast.parse(source)

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert alias.name != "pickle", (
                        "cache.py imports pickle — use json or msgpack instead"
                    )
            elif isinstance(node, ast.ImportFrom):
                assert node.module != "pickle", (
                    "cache.py imports from pickle — use json or msgpack instead"
                )

    @pytest.mark.security
    def test_cache_source_never_calls_pickle_dumps(self):
        """cache.py must not call pickle.dumps or pickle.loads."""
        source = CACHE_PY.read_text(encoding="utf-8")

        banned = ["pickle.dumps", "pickle.loads", "pickle.dump", "pickle.load"]
        for call in banned:
            assert call not in source, (
                f"cache.py contains banned call '{call}' — use json or msgpack instead"
            )

    @pytest.mark.security
    def test_memory_cache_serialize_raises_for_pickle(self):
        """MemoryCache._serialize must raise ValueError when pickle is requested."""
        mod = _load_cache_module()
        config = mod.CacheConfig(
            serialization=mod.SerializationType.PICKLE,
            enable_background_cleanup=False,
        )
        cache = mod.MemoryCache(config)

        with pytest.raises(ValueError, match="pickle serializer is disabled"):
            cache._serialize({"test": "data"})

    @pytest.mark.security
    def test_memory_cache_deserialize_raises_for_pickle(self):
        """MemoryCache._deserialize must raise ValueError when pickle is requested."""
        mod = _load_cache_module()
        config = mod.CacheConfig(
            serialization=mod.SerializationType.PICKLE,
            enable_background_cleanup=False,
        )
        cache = mod.MemoryCache(config)

        with pytest.raises(ValueError, match="pickle serializer is disabled"):
            cache._deserialize(b"test")

    @pytest.mark.security
    def test_redis_cache_serialize_raises_for_pickle(self):
        """RedisCache._serialize must raise ValueError when pickle is requested."""
        mod = _load_cache_module()
        config = mod.CacheConfig(
            serialization=mod.SerializationType.PICKLE,
            enable_background_cleanup=False,
        )
        cache = mod.RedisCache("redis://localhost:6379/0", config)

        with pytest.raises(ValueError, match="pickle serializer is disabled"):
            cache._serialize({"test": "data"})

    @pytest.mark.security
    def test_redis_cache_deserialize_raises_for_pickle(self):
        """RedisCache._deserialize must raise ValueError when pickle is requested."""
        mod = _load_cache_module()
        config = mod.CacheConfig(
            serialization=mod.SerializationType.PICKLE,
            enable_background_cleanup=False,
        )
        cache = mod.RedisCache("redis://localhost:6379/0", config)

        with pytest.raises(ValueError, match="pickle serializer is disabled"):
            cache._deserialize(b"test")

    @pytest.mark.security
    def test_default_serialization_is_json(self):
        """CacheConfig default serialization must be JSON."""
        mod = _load_cache_module()
        config = mod.CacheConfig()
        assert config.serialization == mod.SerializationType.JSON, (
            "Default serialization must be JSON, not pickle"
        )

    @pytest.mark.security
    def test_json_serialization_works(self):
        """JSON serialization must function correctly."""
        mod = _load_cache_module()
        config = mod.CacheConfig(enable_background_cleanup=False)
        cache = mod.MemoryCache(config)

        data = {"key": "value", "number": 42, "nested": {"a": 1}}
        serialized = cache._serialize(data)
        deserialized = cache._deserialize(serialized)

        assert deserialized == data
