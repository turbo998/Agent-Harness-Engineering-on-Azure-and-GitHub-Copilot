#!/usr/bin/env python3
"""Prepare reusable learning assets from Markdown snapshots.

Offline/std-lib only.  Source Markdown is untrusted: code blocks are never
executed, referenced files are not imported, and symlinks are rejected.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

NOTICE = """<!-- learning-asset-sanitized: v1 -->
> **发布界定 / Publication boundary**
>
> 本文是由历史研究快照整理出的补充学习材料。原始资料中的 HTTP 200、抓取时间或“已核实”表述只代表当时的来源可达性/文本核对，不代表本次发布时已经重新核验；本文也不是正式实验报告、生产部署建议或合规结论。
>
> 未对其中的命令、代码块、外部仓库、云资源、生产环境或合规控制做本次实机验证。请在独立测试环境中重新验证后再用于客户/生产场景。

"""

RUN_MARKER = "<!-- generated-by: publish_learning_assets.py -->"
LOCAL_REPORT_DIRNAME = ".publish-local"

SECRET_PATTERNS = [
    ("private_key", re.compile(r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----", re.I)),
    ("credentialed_url", re.compile(r"\bhttps?://[^\s/@:]+:[^\s/@]+@[^\s)>'\"]+", re.I)),
    ("access_token", re.compile(r"\b(?:ghp|gho|github_pat|glpat|xox[baprs]|sk-[A-Za-z0-9])[A-Za-z0-9_\-]{12,}\b")),
    ("named_secret", re.compile(r"\b(?:api[_-]?key|access[_-]?token|refresh[_-]?token|client[_-]?secret|password)\b\s*[:=]\s*['\"]?[A-Za-z0-9_./+=\-]{16,}", re.I)),
    ("azure_subscription_or_tenant_id", re.compile(r"(?i)(?:subscription(?:\s+id)?|tenant(?:\s+id)?|/subscriptions/)\W{0,80}[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")),
]

# Path scrubbing deliberately targets concrete local filesystem forms only.  It
# avoids global replacements that would corrupt URLs or generic product examples
# such as "use ~/.claude/settings.json".
INTERNAL_PATH_PATTERNS = [
    re.compile(r"(?<![\w:/])/(?:home|Users|workspace|mnt|tmp|var|etc)/[^\s)`>'\"]+"),
    re.compile(r"(?<![\w`])~/(?:\.hermes|\.codex|\.agents|private|secrets|workspace|tmp)(?:/[^\s)`>'\"]*)?"),
    re.compile(r"[A-Za-z]:\\(?:Users|workspace|Temp|tmp)\\[^\s)`>'\"]+"),
]

EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I)
DATE_RE = re.compile(r"(?<!\d)(20\d{2}|19\d{2})[-/.](0[1-9]|1[0-2])[-/.](0[1-9]|[12]\d|3[01])(?!\d)")
MD_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")

DROP_LINE_HINTS = [
    ".hermes",
    "hermes profile",
    "研究台账",
    "内部台账",
    "流水账",
    "本台账",
    "本 profile",
]

TOPIC_RULES = [
    ("MCP 与插件", ["mcp", "plugin", "插件", "skill", "skills", "技能"]),
    ("评测与观测", ["eval", "observability", "telemetry", "metrics", "trace", "评测", "观测", "监控"]),
    ("记忆与检索", ["memory", "rag", "vector", "cosmos", "redis", "记忆", "向量"]),
    ("网关与部署", ["gateway", "apim", "foundry", "deploy", "release", "部署", "网关"]),
    ("Workshop 练习", ["workshop", "lab", "练习", "实验", "harness"]),
    ("Agent 运行时", ["runtime", "framework", "maf", "agent service", "orchestration", "workflow", "运行时", "编排"]),
    ("安全与治理", ["security", "sandbox", "approval", "auth", "policy", "dlp", "egress", "governance", "合规", "治理", "审批", "隔离"]),
    ("编码 Agent", ["codex", "claude code", "copilot", "coding", "代码", "code review", "编程", "编码"]),
]

BAD_STATUSES = {"quarantined", "slug_collision", "conflict_existing_changed", "skipped_symlink", "dest_symlink"}


@dataclass
class AssetResult:
    source_name: str
    relative_path: str | None
    title: str | None
    date: str | None
    topic: str | None
    status: str
    reasons: list[str]
    sha256: str | None = None


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Sanitize and publish Markdown learning assets.")
    parser.add_argument("--source", help="Flat source directory containing ordinary .md files")
    parser.add_argument("--dest", required=True, help="Destination learning directory")
    parser.add_argument("--force", action="store_true", help="Overwrite generated destination files when content changed")
    parser.add_argument("--index-only", action="store_true", help="Only rebuild catalog/README from dest/assets; requires no source")
    ns = parser.parse_args(argv)
    if not ns.index_only and not ns.source:
        parser.error("--source is required unless --index-only is used")
    return ns


def ensure_not_symlink(path: Path, label: str) -> None:
    if path.is_symlink():
        raise SystemExit(f"{label} must not be a symlink")


def safe_source_entries(source: Path) -> Iterable[Path]:
    if source.is_symlink() or not source.is_dir():
        raise SystemExit("source must be an existing non-symlink directory")
    for child in sorted(source.iterdir(), key=lambda p: p.name):
        yield child


def detect_secrets(text: str) -> list[str]:
    return [name for name, pattern in SECRET_PATTERNS if pattern.search(text)]


def slugify(name: str) -> str:
    base = Path(name).stem.lower()
    base = re.sub(r"[^a-z0-9\u4e00-\u9fff._-]+", "-", base).strip("-._")
    return (base or "asset") + ".md"


def clean_inline(value: str) -> str:
    value = EMAIL_RE.sub("[email removed]", value)
    for pat in INTERNAL_PATH_PATTERNS:
        value = pat.sub("[local path removed]", value)
    return value.strip()


def extract_title(text: str, fallback_name: str) -> str:
    for line in text.splitlines():
        m = re.match(r"^#\s+(.+?)\s*$", line)
        if m:
            return clean_inline(m.group(1))[:160]
    return Path(fallback_name).stem.replace("-", " ").strip()[:160]


def extract_date(title: str, name: str) -> str | None:
    # Do not inspect arbitrary body/URLs or filesystem mtime for provenance dates.
    for blob in (title, name):
        m = DATE_RE.search(blob)
        if m:
            return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    return None


def classify_topic(title: str, name: str) -> str:
    hay = f"{title}\n{name}".lower()
    for topic, keys in TOPIC_RULES:
        if any(k.lower() in hay for k in keys):
            return topic
    return "其他"


def should_drop_line(line: str) -> bool:
    low = line.lower()
    if any(h in low for h in DROP_LINE_HINTS):
        return True
    if re.search(r"(本轮|本班|今晚|下一班).{0,18}(流水|台账|digest|ledger|backlog|复核记录|巡检)", line, re.I):
        return True
    return False


def replace_md_link(match: re.Match[str]) -> str:
    text = match.group(1).strip()
    href = match.group(2).strip().strip('"\'')
    if re.match(r"(?i)^(https?://|mailto:|#)", href):
        if detect_secrets(href):
            return f"{text}（链接已移除）"
        return f"[{text}]({href})"
    return f"{text}（内部文件引用已移除）"


def sanitize_markdown(text: str) -> str:
    out = []
    for line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        if should_drop_line(line):
            continue
        line = MD_LINK_RE.sub(replace_md_link, line)
        for pat in INTERNAL_PATH_PATTERNS:
            line = pat.sub("[已移除本地路径]", line)
        line = EMAIL_RE.sub("[已移除邮箱]", line)
        line = line.replace("研究台账", "历史研究记录")
        line = line.replace("本台账", "历史研究记录")
        line = line.replace("HTTP 200", "HTTP 200（仅代表原快照当时可达，不代表本次已重验）")
        line = line.replace("http 200", "http 200（仅代表原快照当时可达，不代表本次已重验）")
        line = line.replace("本轮", "原研究快照中")
        line = line.replace("本班", "原研究快照中")
        out.append(line.rstrip())
    body = "\n".join(out).strip() + "\n"
    return NOTICE + body


def write_if_allowed(path: Path, content: str, force: bool) -> tuple[bool, str]:
    encoded = content.encode("utf-8")
    if path.is_symlink():
        return False, "dest_symlink"
    if path.exists():
        old = path.read_bytes()
        if old == encoded:
            return False, "unchanged"
        if not force:
            return False, "conflict_existing_changed"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(encoded)
    return True, "written"


def catalog_json(results: list[AssetResult]) -> str:
    rows = []
    for r in results:
        if r.status not in {"published", "unchanged", "indexed"} or not r.relative_path:
            continue
        rows.append({
            "path": r.relative_path,
            "title": r.title,
            "date": r.date,
            "topic": r.topic,
            "status": "published",
            "source_name": r.source_name,
            "sha256": r.sha256,
        })
    rows.sort(key=lambda x: (x["topic"] or "", x["date"] or "9999-99-99", x["title"] or x["source_name"]))
    return json.dumps(rows, ensure_ascii=False, indent=2) + "\n"


def readme_md(results: list[AssetResult]) -> str:
    published = [r for r in results if r.status in {"published", "unchanged", "indexed"} and r.relative_path]
    quarantined = [r for r in results if r.status == "quarantined"]
    skipped = [r for r in results if r.status not in {"published", "unchanged", "indexed", "quarantined"}]
    published.sort(key=lambda r: (r.topic or "", r.date or "9999-99-99", r.title or ""))
    by_topic: dict[str, list[AssetResult]] = {}
    for r in published:
        by_topic.setdefault(r.topic or "其他", []).append(r)
    lines = [
        RUN_MARKER,
        "# Learning Assets（补充学习材料）",
        "",
        "> 这些条目是从历史研究快照脱敏整理出的补充学习材料，用于学习、讨论、POC 设计前的思路准备；它们不是正式实验报告、不是本次实机验证结论，也不构成生产部署或合规建议。原快照中的来源可达性、HTTP 200 或核验时间不代表本次发布时已经重新核验。",
        "",
        f"- 已发布：{len(published)}",
        f"- 已隔离：{len(quarantined)}（详见本地报告，不发布敏感原文）",
        f"- 跳过/冲突：{len(skipped)}（详见本地报告）",
        "",
    ]
    for topic in sorted(by_topic):
        lines += [f"## {topic}", ""]
        for r in by_topic[topic]:
            date = r.date or "日期未知"
            lines.append(f"- {date} — [{r.title}]({r.relative_path})")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def source_slug_collisions(entries: list[Path]) -> dict[str, list[str]]:
    buckets: dict[str, list[str]] = {}
    for e in entries:
        if e.is_file() and not e.is_symlink() and e.suffix.lower() == ".md":
            buckets.setdefault(slugify(e.name), []).append(e.name)
    return {slug: names for slug, names in buckets.items() if len(names) > 1}


def result_for_public_asset(path: Path, dest: Path) -> AssetResult:
    raw = path.read_text("utf-8", errors="replace")
    title = extract_title(raw, path.name)
    date = extract_date(title, path.name)
    topic = classify_topic(title, path.name)
    rel = path.relative_to(dest).as_posix()
    sha = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    return AssetResult(path.name, rel, title, date, topic, "indexed", [], sha)


def write_indexes(dest: Path, results: list[AssetResult], force: bool) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    for file_path, content in [(dest / "catalog.json", catalog_json(results)), (dest / "README.md", readme_md(results))]:
        if file_path.is_symlink():
            results.append(AssetResult(file_path.name, file_path.relative_to(dest).as_posix(), file_path.name, None, "索引", "dest_symlink", ["index_path_is_symlink"]))
            continue
        if file_path.exists() and not force:
            old = file_path.read_text("utf-8", errors="replace")
            if old != content and file_path.name == "README.md" and RUN_MARKER not in old:
                results.append(AssetResult(file_path.name, file_path.relative_to(dest).as_posix(), file_path.name, None, "索引", "conflict_existing_changed", ["generated_index_edited_manually"]))
                continue
        file_path.write_text(content, "utf-8")


def write_local_reports(dest: Path, results: list[AssetResult]) -> None:
    local = dest / LOCAL_REPORT_DIRNAME
    local.mkdir(parents=True, exist_ok=True)
    report = {
        "note": "Local operator report; do not commit. Quarantined entries are intentionally excluded from public catalog.",
        "summary": summary_for(results),
        "results": [asdict(r) for r in results],
    }
    (local / "publish_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", "utf-8")
    q = [asdict(r) for r in results if r.status == "quarantined"]
    (local / "quarantine_report.json").write_text(json.dumps(q, ensure_ascii=False, indent=2) + "\n", "utf-8")


def build_index_from_dest(dest: Path, force: bool) -> list[AssetResult]:
    ensure_not_symlink(dest, "dest")
    assets_dir = dest / "assets"
    ensure_not_symlink(assets_dir, "dest/assets")
    results: list[AssetResult] = []
    if assets_dir.exists():
        for path in sorted(assets_dir.glob("*.md"), key=lambda p: p.name):
            if path.is_symlink():
                results.append(AssetResult(path.name, None, None, None, None, "skipped_symlink", ["symlink_not_allowed"]))
                continue
            if path.is_file():
                reasons = detect_secrets(path.read_text("utf-8", errors="replace"))
                if reasons:
                    results.append(AssetResult(path.name, path.relative_to(dest).as_posix(), None, None, None, "quarantined", sorted(set(reasons))))
                else:
                    results.append(result_for_public_asset(path, dest))
    write_indexes(dest, results, force)
    write_local_reports(dest, results)
    return results


def process(source: Path, dest: Path, force: bool, index_only: bool = False) -> list[AssetResult]:
    if index_only:
        return build_index_from_dest(dest, force)
    ensure_not_symlink(dest, "dest")
    assets_dir = dest / "assets"
    ensure_not_symlink(assets_dir, "dest/assets")
    entries = list(safe_source_entries(source))
    collisions = source_slug_collisions(entries)
    results: list[AssetResult] = []
    for entry in entries:
        if entry.is_symlink():
            results.append(AssetResult(entry.name, None, None, None, None, "skipped_symlink", ["symlink_not_allowed"]))
            continue
        if not entry.is_file():
            results.append(AssetResult(entry.name, None, None, None, None, "skipped_non_file", ["not_a_regular_file"]))
            continue
        if entry.suffix.lower() != ".md":
            results.append(AssetResult(entry.name, None, None, None, None, "skipped_non_md", ["not_markdown"]))
            continue
        slug = slugify(entry.name)
        raw = entry.read_text("utf-8", errors="replace")
        title = extract_title(raw, entry.name)
        date = extract_date(title, entry.name)
        topic = classify_topic(title, entry.name)
        if slug in collisions:
            results.append(AssetResult(entry.name, f"assets/{slug}", title, date, topic, "slug_collision", ["slug_collides", *sorted(collisions[slug])]))
            continue
        secret_reasons = detect_secrets(raw)
        if secret_reasons:
            results.append(AssetResult(entry.name, None, title, date, topic, "quarantined", sorted(set(secret_reasons))))
            continue
        sanitized = sanitize_markdown(raw)
        target = assets_dir / slug
        rel = target.relative_to(dest).as_posix()
        sha = hashlib.sha256(sanitized.encode("utf-8")).hexdigest()
        changed, state = write_if_allowed(target, sanitized, force)
        if state in {"conflict_existing_changed", "dest_symlink"}:
            results.append(AssetResult(entry.name, rel, title, date, topic, state, ["destination_exists_with_different_content" if state == "conflict_existing_changed" else "destination_path_is_symlink"], sha))
        else:
            results.append(AssetResult(entry.name, rel, title, date, topic, "published" if changed else "unchanged", [], sha))
    write_indexes(dest, results, force)
    write_local_reports(dest, results)
    return results


def summary_for(results: list[AssetResult]) -> dict[str, int]:
    return {
        "published_or_unchanged": sum(1 for r in results if r.status in {"published", "unchanged", "indexed"}),
        "quarantined": sum(1 for r in results if r.status == "quarantined"),
        "skipped_or_conflict": sum(1 for r in results if r.status not in {"published", "unchanged", "indexed", "quarantined"}),
    }


def main(argv: list[str]) -> int:
    ns = parse_args(argv)
    results = process(Path(ns.source) if ns.source else Path(), Path(ns.dest), ns.force, ns.index_only)
    print(json.dumps(summary_for(results), ensure_ascii=False, sort_keys=True))
    if any(r.status in BAD_STATUSES for r in results):
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
