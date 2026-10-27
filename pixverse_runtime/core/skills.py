from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from .state import plugin_root, repo_root

FRONTMATTER_RE = re.compile("^---\\s*\\n(.*?)\\n---\\s*\\n", re.DOTALL)
RELATIVE_MARKDOWN_REF_RE = re.compile("`((?:\\.{1,2}/)[^`\\n]+\\.md(?:#[^`\\n]*)?)`")
RELATIVE_MARKDOWN_LINK_RE = re.compile(
    "\\[[^\\]\\n]*\\]\\(<?((?:\\.{1,2}/)[^\\s)>]+\\.md(?:#[^\\s)>]*)?)>?\\)"
)


@dataclass
class SkillInfo:
    name: str
    path: Path
    description: str = ""
    visibility: str = "public"


PUBLIC_SKILLS_DIR = "skills"
INTERNAL_SKILLS_DIR = "skills-internal"


def list_skills(root: Path | None = None, *, include_internal: bool = False) -> list[SkillInfo]:
    root_path = _skill_root(root)
    bases = _skill_bases(root_path, include_internal=include_internal)
    out: list[SkillInfo] = []
    for base, visibility in bases:
        if not base.exists():
            continue
        for skill_md in sorted(base.glob("*/SKILL.md")):
            text = skill_md.read_text(encoding="utf-8")
            fm = _parse_frontmatter(text)
            out.append(
                SkillInfo(
                    name=fm.get("name") or skill_md.parent.name,
                    path=skill_md.parent,
                    description=fm.get("description", ""),
                    visibility=visibility,
                )
            )
    return out


def validate_skills(root: Path | None = None, *, include_internal: bool = True) -> list[str]:
    issues: list[str] = []
    root_path = _skill_root(root)
    if not (root_path / PUBLIC_SKILLS_DIR).exists():
        issues.append(f"{root_path / PUBLIC_SKILLS_DIR}: missing public skills directory")
    for skill in list_skills(root_path, include_internal=include_internal):
        text = (skill.path / "SKILL.md").read_text(encoding="utf-8")
        fm = _parse_frontmatter(text)
        if not fm.get("name"):
            issues.append(f"{skill.path}: missing name")
        if not fm.get("description"):
            issues.append(f"{skill.path}: missing description")
        if skill.name != skill.path.name:
            issues.append(f"{skill.path}: frontmatter name should match folder name")
    bases = [base for (base, _) in _skill_bases(root_path, include_internal=include_internal)]
    bases.append(root_path / "skills-shared")
    for base in bases:
        for document in sorted(base.rglob("*.md")):
            for ref in _relative_markdown_refs(document.read_text(encoding="utf-8")):
                target = (document.parent / ref.split("#", 1)[0]).resolve()
                if not target.is_file():
                    issues.append(f"{document}: references missing {ref}")
    return issues


def _skill_bases(root_path: Path, *, include_internal: bool) -> list[tuple[Path, str]]:
    public = root_path / PUBLIC_SKILLS_DIR
    internal = root_path / INTERNAL_SKILLS_DIR
    if not public.exists() and internal.exists():
        return [(internal, "public")]
    bases = [(public, "public")]
    if include_internal:
        bases.append((internal, "internal"))
    return bases


def _skill_root(root: Path | None) -> Path:
    if root is None:
        return plugin_root()
    return repo_root(root)


def _parse_frontmatter(text: str) -> dict[str, str]:
    match = FRONTMATTER_RE.match(text)
    if not match:
        return {}
    data: dict[str, str] = {}
    for line in match.group(1).splitlines():
        if ":" not in line:
            continue
        (key, value) = line.split(":", 1)
        data[key.strip()] = value.strip().strip('"')
    return data


def _relative_markdown_refs(text: str) -> list[str]:
    return list(
        dict.fromkeys(
            (
                match.group(1)
                for pattern in (RELATIVE_MARKDOWN_REF_RE, RELATIVE_MARKDOWN_LINK_RE)
                for match in pattern.finditer(text)
            )
        )
    )
