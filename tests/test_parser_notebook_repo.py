from __future__ import annotations

import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from llm_wiki import DocumentParser  # noqa: E402
from llm_wiki.parsers.notebook import NotebookParserAdapter  # noqa: E402
from llm_wiki.parsers.repo import RepoParserAdapter  # noqa: E402


class NotebookAndRepoParserTests(unittest.TestCase):
    def test_notebook_parser_preserves_markdown_and_code_cells(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "analysis.ipynb"
            path.write_text(
                json.dumps(
                    {
                        "metadata": {"language_info": {"name": "python"}},
                        "cells": [
                            {
                                "cell_type": "markdown",
                                "source": ["# Analysis\n", "Notebook notes."],
                            },
                            {
                                "cell_type": "code",
                                "execution_count": 3,
                                "source": ["value = 42\n", "print(value)"],
                                "outputs": [{"ignored": "no execution"}],
                            },
                        ],
                    }
                ),
                encoding="utf-8",
            )

            document = NotebookParserAdapter().parse(path)

            self.assertEqual(document.source_type, "ipynb")
            self.assertEqual(document.title, "Analysis")
            self.assertEqual(document.language, "python")
            self.assertEqual(document.sections[0].kind, "markdown")
            self.assertEqual(document.sections[1].kind, "code")
            self.assertEqual(len(document.code_blocks), 1)
            self.assertIn("value = 42", document.code_blocks[0].content)
            self.assertEqual(document.code_blocks[0].metadata["execution_count"], 3)
            self.assertEqual(document.parse_quality, "high")

    def test_notebook_parser_reports_bad_cells_without_crashing(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "bad.ipynb"
            path.write_text(
                json.dumps(
                    {
                        "metadata": {},
                        "cells": [{"cell_type": "raw", "source": "not supported"}, 12],
                    }
                ),
                encoding="utf-8",
            )

            document = NotebookParserAdapter().parse(path)

            self.assertEqual(document.parse_quality, "failed")
            self.assertEqual(len(document.errors), 2)

    def test_repo_parser_handles_tree_docs_code_and_skips_binary(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory) / "repo"
            package = root / "package"
            git_dir = root / ".git"
            package.mkdir(parents=True)
            git_dir.mkdir(parents=True)
            (root / "README.md").write_text("# Repo\n\nProject overview.", encoding="utf-8")
            (package / "module.py").write_text("def answer():\n    return 42\n", encoding="utf-8")
            (root / "image.png").write_bytes(b"\x89PNG\x00binary")
            (git_dir / "config").write_text("ignored", encoding="utf-8")

            document = RepoParserAdapter().parse(root)

            self.assertEqual(document.source_type, "repo")
            self.assertEqual(document.title, "repo")
            self.assertEqual(document.sections[0].heading, "Repository tree")
            self.assertIn("README.md", document.sections[0].content)
            self.assertIn("package/module.py", document.sections[0].content)
            self.assertNotIn(".git/config", document.sections[0].content)
            self.assertTrue(any(section.heading == "README.md" for section in document.sections))
            self.assertEqual(len(document.code_blocks), 1)
            self.assertEqual(document.code_blocks[0].language, "python")
            self.assertIn("image.png", document.metadata["skipped_files"][0]["path"])
            self.assertEqual(document.parse_quality, "high")

    def test_document_parser_routes_folders_to_repo_adapter(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory) / "notes"
            root.mkdir()
            (root / "README.md").write_text("# Notes", encoding="utf-8")

            document = DocumentParser().parse_path(root)

            self.assertEqual(document.source_type, "repo")
            self.assertEqual(document.title, "notes")


if __name__ == "__main__":
    unittest.main()
