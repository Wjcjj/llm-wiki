# LLM Wiki Product Spec

## Goal

Build a local-first AI-powered knowledge system that converts raw files into structured markdown wiki pages.

Inspired by Karpathy's LLM Wiki concept:

Raw docs are temporary memory.
Wiki pages are permanent memory.

---

## Input Sources

- PDF
- DOCX
- Markdown
- TXT
- Jupyter Notebook
- Git Repositories

---

## Core Workflow

Sources
→ Parse
→ Normalize
→ Extract Knowledge
→ Detect Topics
→ Generate Wiki Pages
→ Cross-link Pages
→ Incremental Updates

---

## Output

Human-readable markdown wiki.

Examples:

- rag.md
- langgraph.md
- agent-memory.md
- autogen.md
- openmanus.md

---

## Design Principles

- local first
- markdown first
- modular architecture
- editable outputs
- transparent memory
- incremental updates
- wiki is primary memory
- vector DB is secondary memory

---

## Non-goals (Phase 1)

- fancy UI
- cloud sync
- autonomous browsing
- multi-user collaboration