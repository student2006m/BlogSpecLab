"""Architecture test: enforce Constitution §II import rules automatically.

Rules checked (Constitution §II.1–5):
  1. `core.domain` imports no other project package.
  2. `core.application` imports `core.domain` only (never `infra`/`endpoints`).
  3. `infra.*` imports only `core.*` (never `endpoints`).
  4. `endpoints.api` imports only itself, `core.application`, and `infra.*`.
  5. No direct imports between different `infra` subpackages, and the
     package dependency graph is acyclic.
"""

from __future__ import annotations

import ast
from pathlib import Path

PROJECT_ROOT = "blogspeclab"

SRC_ROOT = Path(__file__).resolve().parents[2] / "src" / PROJECT_ROOT


def _owner_package(module: str) -> str:
    parts = module.split(".")
    if parts[1:2] == ["core"]:
        return "core.domain" if parts[2:3] == ["domain"] else "core.application"
    if parts[1:2] == ["infra"]:
        return f"infra.{parts[2]}" if len(parts) > 2 else "infra"
    if parts[1:2] == ["endpoints"]:
        return "endpoints.api"
    return PROJECT_ROOT


def _resolve_import(module: str, node: ast.ImportFrom) -> str | None:
    if node.level == 0:
        return node.module
    base = module.split(".")
    prefix = base[: len(base) - node.level + 1]
    if node.module:
        return ".".join(prefix + [node.module])
    return ".".join(prefix) if prefix else None


def _collect_edges() -> dict[str, set[str]]:
    edges: dict[str, set[str]] = {}
    for path in sorted(SRC_ROOT.rglob("*.py")):
        module = ".".join(
            (PROJECT_ROOT,) + path.relative_to(SRC_ROOT).with_suffix("").parts
        )
        if module.endswith(".__init__"):
            module = module[: -len(".__init__")]
        owner = _owner_package(module)
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            target: str | None = None
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name == PROJECT_ROOT or alias.name.startswith(
                        PROJECT_ROOT + "."
                    ):
                        dep = _owner_package(alias.name)
                        if dep != owner:  # same-package imports are not edges
                            edges.setdefault(owner, set()).add(dep)
            elif isinstance(node, ast.ImportFrom):
                target = _resolve_import(module, node)
                if target == PROJECT_ROOT or (
                    target or ""
                ).startswith(PROJECT_ROOT + "."):
                    assert target is not None
                    dep = _owner_package(target)
                    if dep != owner:  # same-package imports are not edges
                        edges.setdefault(owner, set()).add(dep)
    return edges


def _assert_acyclic(edges: dict[str, set[str]]) -> None:
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node: str, trail: list[str]) -> None:
        if node in visited:
            return
        assert node not in visiting, (
            f"Cyclic package dependency forbidden (§II.5):"
            f" {' -> '.join([*trail, node])}"
        )
        visiting.add(node)
        for dep in sorted(edges.get(node, ())):
            visit(dep, [*trail, node])
        visiting.remove(node)
        visited.add(node)

    for root in sorted(set(edges) | {d for v in edges.values() for d in v}):
        visit(root, [])


def test_import_rules() -> None:
    edges = _collect_edges()

    domain_deps = edges.get("core.domain", set())
    assert not (domain_deps - {"core.domain"}), (
        f"core.domain MUST NOT import other project packages (§II.1):"
        f" {sorted(domain_deps)}"
    )

    app_deps = edges.get("core.application", set()) - {"core.application"}
    assert not (app_deps - {"core.domain"}), (
        "core.application MUST NOT import infra/endpoints (§II.2):"
        f" {sorted(app_deps)}"
    )

    for owner, deps in edges.items():
        if owner.startswith("infra."):
            assert not {d for d in deps if d.startswith("endpoints")}, (
                f"{owner} MUST NOT import endpoints (§II.3)"
            )
            others = {
                d
                for d in deps
                if d.startswith("infra.") and d != owner
            }
            assert not others, (
                f"{owner} MUST NOT directly import other infra packages"
                f" (§II.5): {sorted(others)}"
            )

    api_deps = edges.get("endpoints.api", set()) - {"endpoints.api"}
    assert api_deps <= {"core.application", "infra.data_access"}, (
        "endpoints.api MAY import only core.application and infra.* (§II.4):"
        f" {sorted(api_deps)}"
    )

    _assert_acyclic(edges)
