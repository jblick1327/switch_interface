"""Interface definitions to decouple core components."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class KeyReceiver(Protocol):
    """Object capable of handling a key activation."""

    def on_key(self, key: Any) -> None:
        """Process an activated key."""
        ...


@runtime_checkable
class ScannableKeyboard(Protocol):
    """Minimal API required by :class:`Scanner`."""

    root: Any
    highlight_index: int
    highlight_row_index: int | None
    key_widgets: list[tuple[Any, Any]]
    row_start_indices: list[int]
    row_indices: list[int]

    def advance_highlight(self) -> None:
        ...

    def press_highlighted(self) -> None:
        ...

    def next_page(self) -> None:
        ...

    def prev_page(self) -> None:
        ...

    def row_start_for_index(self, index: int) -> int:
        ...

    def highlight_row(self, row_idx: int | None) -> None:
        ...

    def _update_highlight(self) -> None:
        ...
