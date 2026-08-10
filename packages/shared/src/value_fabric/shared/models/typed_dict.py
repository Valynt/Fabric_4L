"""TypedDict-style model base for shared package.

Provides a Pydantic BaseModel subclass used across the codebase
for type-safe dictionary-like response models.
"""

from typing import Any

from pydantic import BaseModel, ConfigDict


class TypedDictModel(BaseModel):
    """Base model for typed-dict style response objects.

    Subclass this to define structured response shapes that can be
    validated with `.model_validate()` and serialized with `.model_dump()`.

    Supports dict-like access via ``[]``, ``in``, ``.get()``,
    iteration over keys/values/items, and assignment.
    """

    model_config = ConfigDict(
        extra="allow",
        populate_by_name=True,
        arbitrary_types_allowed=True,
        strict=False,
    )

    def __getitem__(self, key: str) -> Any:
        try:
            return getattr(self, key)
        except AttributeError as exc:
            raise KeyError(key) from exc

    def __setitem__(self, key: str, value: Any) -> None:
        setattr(self, key, value)

    def __contains__(self, key: str) -> bool:
        return hasattr(self, key)

    def get(self, key: str, default: Any = None) -> Any:
        """Return the value for ``key`` if it exists, else ``default``."""
        return getattr(self, key, default)

    def __iter__(self):
        """Iterate over field names."""
        return iter(self.model_dump())

    def keys(self):
        return self.model_dump().keys()

    def values(self):
        return self.model_dump().values()

    def items(self):
        return self.model_dump().items()

    def __len__(self) -> int:
        """Return the number of fields."""
        return len(self.model_dump())
