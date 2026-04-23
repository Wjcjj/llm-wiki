# Skill: Parser

## Purpose

Transform heterogeneous raw sources into a stable, normalized document representation
for downstream knowledge extraction, wiki generation, linking, and updates.

This is foundational infrastructure.

The parser layer must be:

- deterministic
- modular
- fault tolerant
- extensible
- local-first

---

## Supported Source Types

### Documents

- pdf
- docx
- txt
- md
- html

### Structured Notes

- ipynb

### Code Sources

- local repositories
- cloned git repositories

---

## Output Contract

Every parser must return a `NormalizedDocument`.

```json
{
  "doc_id": "uuid",
  "source_path": "...",
  "source_type": "pdf",
  "title": "...",
  "language": "en",
  "metadata": {},
  "sections": [],
  "code_blocks": [],
  "assets": [],
  "parse_quality": "high",
  "errors": []
}
```

## Section Schema
```json
{
  "section_id": "...",
  "heading": "Introduction",
  "level": 2,
  "content": "...",
  "kind": "text"
}
```
Kinds:
- text
- code
- markdown
- table
- quote
- list

## Functional Requirements
### Must Do
- preserve headings when possible
- preserve reading order
- preserve code blocks
- preserve notebook markdown cells
- preserve notebook code cells
- retain source metadata
- never crash full pipeline because of one bad file
### Should Do
- infer title when missing
- detect language
- strip useless whitespace
- normalize unicode
### Nice to Have
- table extraction
- image OCR
- formula detection
- citation extraction

## Failure Policy
If parsing fails:

- record structured error
- continue pipeline
- downgrade parse_quality
- preserve raw bytes path reference

Never block other files.

## Parse Quality Levels
- high = structure preserved
- medium = text extracted, weak structure
- low = partial extraction only
- failed = unreadable

## Performance Rules
- support batch processing
- support large folders
- stream large files when possible
- skip binary files
- configurable max file size

## Security Rules
- never execute notebook code
- never execute repo scripts
- never trust embedded macros
- sanitize paths
- no network calls by default

## Extensibility Rules

Use adapter pattern:

- PdfParserAdapter
- DocxParserAdapter
- NotebookParserAdapter
- RepoParserAdapter
- MarkdownParserAdapter

All adapters must emit same schema.

## Acceptance Criteria

Parser considered complete when:

- mixed folder can be parsed
- output schema valid
- no fatal crash
- repo tree handled correctly
- notebooks preserve cells
- downstream modules can consume output