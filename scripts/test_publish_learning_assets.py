import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).with_name("publish_learning_assets.py")
spec = importlib.util.spec_from_file_location("publish_learning_assets", SCRIPT)
assert spec is not None and spec.loader is not None
pub = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = pub
spec.loader.exec_module(pub)


class PublishLearningAssetsTests(unittest.TestCase):
    def run_tool(self, source, dest, force=False, index_only=False):
        return pub.process(Path(source) if source else Path(), Path(dest), force, index_only)

    def test_secret_quarantine_local_only_and_not_in_public_catalog(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); src = root / "src"; dst = root / "learning"; src.mkdir()
            secret = "sk-" + "A" * 24
            (src / "secret-2026-01-02.md").write_text(f"# Secret 2026-01-02\napi_key={secret}\n", "utf-8")
            results = self.run_tool(src, dst)
            self.assertEqual(results[0].status, "quarantined")
            self.assertFalse((dst / "assets" / "secret-2026-01-02.md").exists())
            self.assertEqual(json.loads((dst / "catalog.json").read_text("utf-8")), [])
            self.assertFalse((dst / "publish_report.json").exists())
            report = (dst / ".publish-local" / "quarantine_report.json").read_text("utf-8")
            self.assertIn("named_secret", report)
            self.assertNotIn(secret, report)
            self.assertNotIn("Secret 2026-01-02", (dst / "catalog.json").read_text("utf-8"))

    def test_internal_path_scrub_does_not_corrupt_urls_or_claude_example(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); src = root / "src"; dst = root / "learning"; src.mkdir()
            url = "https://example.com/backlog/digest/ledger"
            (src / "asset.md").write_text(
                "# Agent Note\n"
                f"See /home/someone/private/file and [public]({url}). Use ~/.claude/settings.json. "
                "Contact a@example.com. HTTP 200\n", "utf-8")
            self.run_tool(src, dst)
            out = (dst / "assets" / "asset.md").read_text("utf-8")
            self.assertIn("[已移除本地路径]", out)
            self.assertIn(f"[public]({url})", out)
            self.assertIn("~/.claude/settings.json", out)
            self.assertIn("[已移除邮箱]", out)
            self.assertIn("不代表本次已重验", out)
            self.assertNotIn("/home/someone", out)

    def test_symlink_skipped_and_cli_returns_nonzero(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); src = root / "src"; dst = root / "learning"; src.mkdir()
            target = root / "outside.md"; target.write_text("# Outside\n", "utf-8")
            (src / "link.md").symlink_to(target)
            results = self.run_tool(src, dst)
            self.assertEqual(results[0].status, "skipped_symlink")
            cp = subprocess.run([sys.executable, str(SCRIPT), "--source", str(src), "--dest", str(dst)], text=True, stdout=subprocess.PIPE)
            self.assertEqual(cp.returncode, 2)

    def test_index_only_uses_existing_assets_without_rewriting_body(self):
        with tempfile.TemporaryDirectory() as td:
            dst = Path(td) / "learning"; assets = dst / "assets"; assets.mkdir(parents=True)
            body = "# Public 2026-03-04\nManual reviewed text with codex mention only in body.\n"
            asset = assets / "public.md"
            asset.write_text(body, "utf-8")
            self.run_tool(None, dst, index_only=True)
            self.assertEqual(asset.read_text("utf-8"), body)
            catalog = json.loads((dst / "catalog.json").read_text("utf-8"))
            self.assertEqual(len(catalog), 1)
            self.assertEqual(catalog[0]["path"], "assets/public.md")
            self.assertEqual(catalog[0]["date"], "2026-03-04")
            self.assertEqual(catalog[0]["topic"], "其他")

    def test_unknown_dates_are_null_not_body_url_or_mtime(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); src = root / "src"; dst = root / "learning"; src.mkdir()
            (src / "no-date.md").write_text("# No Date\nURL https://x.test/2026/01/02 and body 2026-01-02.\n", "utf-8")
            self.run_tool(src, dst)
            catalog = json.loads((dst / "catalog.json").read_text("utf-8"))
            row = next(x for x in catalog if x["source_name"] == "no-date.md")
            self.assertIsNone(row["date"])

    def test_existing_edited_protection_and_nonzero(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); src = root / "src"; dst = root / "learning"; src.mkdir()
            (src / "asset.md").write_text("# Asset\nFirst\n", "utf-8")
            self.run_tool(src, dst)
            target = dst / "assets" / "asset.md"
            target.write_text(target.read_text("utf-8") + "\nmanual edit\n", "utf-8")
            (src / "asset.md").write_text("# Asset\nSecond\n", "utf-8")
            results = self.run_tool(src, dst)
            conflict = next(r for r in results if r.source_name == "asset.md")
            self.assertEqual(conflict.status, "conflict_existing_changed")
            self.assertIn("manual edit", target.read_text("utf-8"))
            cp = subprocess.run([sys.executable, str(SCRIPT), "--source", str(src), "--dest", str(dst)], text=True, stdout=subprocess.PIPE)
            self.assertEqual(cp.returncode, 2)

    def test_slug_collision_is_detected(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); src = root / "src"; dst = root / "learning"; src.mkdir()
            (src / "A B.md").write_text("# One\n", "utf-8")
            (src / "A+B.md").write_text("# Two\n", "utf-8")
            results = self.run_tool(src, dst)
            self.assertEqual({r.status for r in results}, {"slug_collision"})
            self.assertFalse((dst / "assets" / "a-b.md").exists())

    def test_classification_uses_title_and_filename_not_body_mentions(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); src = root / "src"; dst = root / "learning"; src.mkdir()
            (src / "governance-note.md").write_text("# Governance Policy\nThis body mentions codex once.\n", "utf-8")
            self.run_tool(src, dst)
            catalog = json.loads((dst / "catalog.json").read_text("utf-8"))
            self.assertEqual(catalog[0]["topic"], "安全与治理")


if __name__ == "__main__":
    unittest.main()
