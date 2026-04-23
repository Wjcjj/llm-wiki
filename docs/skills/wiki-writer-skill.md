# docs/skills/wiki-writer-skill.md

# Skill: Wiki Writer

## Purpose

Transform extracted knowledge into durable, high-quality markdown wiki pages.

The wiki is the primary memory layer of the system.

Raw files are temporary inputs.  
Parsed documents are intermediate artifacts.  
Embeddings are secondary retrieval memory.  
Wiki pages are long-term structured knowledge assets.

This skill is responsible for converting fragmented source information into readable,
maintainable, interconnected knowledge pages.

---

## Core Responsibilities

The Wiki Writer must:

- create new topic pages
- update existing pages
- merge overlapping knowledge
- preserve readability
- preserve structural consistency
- add internal links
- track source provenance
- support incremental improvement over time

---

## Output Format

All pages must be standard Markdown.

Location:

```text
data/wiki/
```

## Recommended structure:

```
data/wiki/
├── concepts/
├── frameworks/
├── repos/
├── methods/
├── experiments/
├── glossary/
└── indexes/
```

## Page Naming Rules

Use stable, human-readable names.

Examples:

- rag.md
- agent-memory.md
- langgraph.md
- autogen.md
- vector-database.md

Avoid:

- timestamps
- random IDs
- vague names
- duplicate synonyms

Bad examples:

- note1.md
- newtopic.md
- 20260423_abc.md
## Page Type Classification

The writer must classify output pages into one of the following types.

### Concept Pages

Examples:

- RAG
- Tool Calling
- Reflection Agents
- Memory Systems
### Framework Pages

Examples:

- LangGraph
- CrewAI
- AutoGen
### Repository Pages

Examples:

- OpenManus repo
- LangGraph starter repo
### Method Pages

Examples:

- Hybrid Retrieval
- Agent Planning Patterns
### Experiment Pages

Examples:

- Local embedding benchmark
- Parser comparison results
### Index Pages

Examples:

- Agent ecosystem map
- LLM learning roadmap
## Canonical Page Template

Every page should follow a stable schema.

```Markdown
# Topic Name

## Summary

Short overview of the topic.

## Key Concepts

Core ideas, components, terminology.

## Architecture / How It Works

Mechanisms, flow, design patterns.

## Use Cases

Where it is useful.

## Strengths

Advantages.

## Weaknesses

Limitations, tradeoffs.

## Related Topics

Linked internal pages.

## Practical Notes

Implementation insights, engineering notes.

## Sources

Origin documents / repos / references.
```

## Content Quality Rules

The writer must produce pages that are:

- concise but useful
- technically accurate
- easy to scan
- logically structured
- free from fluff
- useful for future engineering work

Avoid:

- generic filler language
- repeated paragraphs
- overlong prose
- vague statements
- hallucinated details
## Writing Style Rules

Use an engineering knowledge-base style.

Preferred tone:

- precise
- neutral
- practical
- high signal
- compact

Avoid:

- marketing tone
- dramatic claims
- excessive verbosity
- casual chat style
## Summarization Rules

When converting sources into wiki pages:

### Must Preserve
- core technical ideas
- architecture insights
- implementation patterns
- important caveats
- notable comparisons
### May Compress
- repetitive explanations
- examples not central to learning goal
- irrelevant setup details
### Must Not Invent
- unsupported claims
- fake benchmarks
- fake citations
- fake implementation details
## Multi-Source Synthesis Rules

If multiple sources discuss same topic:

The writer should synthesize into one stronger page instead of creating duplicates.

Example:

Sources:

- blog about RAG
- repo about hybrid retrieval
- notes about reranking

Output:
```
rag.md
```

With sections:

- baseline RAG
- hybrid retrieval
- reranking
- practical tradeoffs
## Duplicate Prevention Rules

Before creating a page, check if similar page already exists.

Examples:

- retrieval-augmented-generation.md
- rag.md

Prefer one canonical page.

Use aliases inside content if needed.

## Incremental Update Rules

When new knowledge arrives:

Do not rewrite the whole page unnecessarily.

Prefer:

- append missing insights
- refine weak sections
- update outdated comparisons
- improve structure
- add new related links

Preserve useful prior content.

## Manual Edit Preservation

If user manually edits wiki pages:

System should try to preserve manual edits whenever possible.

Suggested strategies:

- protected sections
- merge markers
- append mode
- structured patch updates

Never blindly overwrite curated pages.

## Internal Linking Rules

Writer should insert meaningful internal links.

Examples:

Within langgraph.md

Link to:

- agents.md
- tool-calling.md
- state-machine-patterns.md
- memory-systems.md

Rules:

- prioritize high-value links
- avoid link spam
- use canonical page names
## Source Provenance Rules

Every page should contain a Sources section.

Examples:
```Markdown
## Sources

- source: repo/langgraph
- source: paper/agent-memory.pdf
- source: notes/my-rag-notes.md
```
Purpose:

- traceability
- trust
- future reprocessing
- explainability
## Repository Writing Rules

For repo-derived pages, include:
```Markdown
## What This Repo Does

## Architecture

## Key Modules

## Interesting Design Choices

## How It Relates To Other Systems

## What To Learn From It
```
## Framework Writing Rules

For frameworks:
```Markdown
## Core Abstractions

## Execution Model

## Strengths

## Weaknesses

## Best Use Cases

## Compared With Alternatives
```
## Concept Writing Rules

For concepts:
```Markdown
## Definition

## Why It Matters

## Common Designs

## Tradeoffs

## Real Usage Patterns
```
## Comparison Writing Rules

When appropriate, include comparison tables.

Example:

|Tool	|Strength	|Weakness	|Best Use|
| ---- | ---- | ---- | ---- |
|LangGraph	|structured flows|	more setup|	production agents|
|CrewAI	|easy multi-agent|	less control|	fast prototyping|

Only include if meaningful.

## Update Trigger Rules

Writer should update pages when:

- new relevant source added
- existing source changed
- stale information detected
- better synthesis available
- missing links discovered
## Failure Rules

If knowledge confidence is low:

- mark uncertain sections
- use tentative wording
- request more sources if needed
- do not fabricate certainty
## Acceptance Criteria

Wiki Writer is successful when pages are:

- readable by humans
- useful for engineering decisions
- structurally consistent
- non-duplicated
- linked to related knowledge
- source-traceable
- incrementally improvable
## Non-Goals

This skill is not responsible for:

- raw parsing
- embedding search
- OCR
- UI rendering
- task orchestration

Those belong to other modules.

## Final Principle

Do not generate notes.

Generate reusable knowledge assets.

Every page should become more valuable each time the system learns something new.