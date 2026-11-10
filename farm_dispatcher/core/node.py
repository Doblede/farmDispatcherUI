"""A small tree structure used by the breakdown, stack and render views."""

from __future__ import annotations

from typing import Iterator, List, Optional


class Node:
    """A named tree node. Children are kept sorted by name."""

    sep = "/"

    def __init__(self, name: str, parent: Optional["Node"] = None):
        self.name = name
        self.parent: Optional[Node] = None
        self.children: List[Node] = []
        self.tooltip: Optional[str] = None
        self.warning = False
        if parent is not None:
            parent.add_child(self)

    # -- structure -----------------------------------------------------
    def add_child(self, child: "Node") -> "Node":
        if child.parent is not None:
            child.parent.remove_child(child)
        self.children.append(child)
        self.children.sort(key=lambda n: n.name.lower())
        child.parent = self
        return child

    def remove_child(self, child: "Node") -> None:
        self.children.remove(child)
        child.parent = None

    def clear(self) -> None:
        for child in self.children:
            child.parent = None
        self.children = []

    def resort(self) -> None:
        """Call after renaming a child."""
        self.children.sort(key=lambda n: n.name.lower())

    def child(self, row: int) -> Optional["Node"]:
        if 0 <= row < len(self.children):
            return self.children[row]
        return None

    def find_child(self, name: str) -> Optional["Node"]:
        return next((c for c in self.children if c.name == name), None)

    def row(self) -> int:
        return self.parent.children.index(self) if self.parent else 0

    def walk(self) -> Iterator["Node"]:
        """This node and all descendants, depth first."""
        yield self
        for child in self.children:
            yield from child.walk()

    def path(self) -> str:
        names = []
        node: Optional[Node] = self
        while node is not None:
            names.append(node.name)
            node = node.parent
        return self.sep.join(reversed(names))

    def __repr__(self) -> str:
        return "<{} {!r}>".format(type(self).__name__, self.name)
