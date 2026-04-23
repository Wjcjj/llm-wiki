# Skill: GitHub Workflow for Codex

## Purpose

Ensure Codex works safely inside the repository.

The goal is:

- keep `main` stable
- isolate every new change in its own branch
- use pull requests for review and merge
- reduce risk from large or incorrect AI-generated changes
- preserve a clean project history

This skill must be read before Codex starts any implementation task.

---

## Core Working Model

Use a lightweight GitHub Flow style process.

### Rules

- `main` is the stable branch
- never develop directly on `main`
- every new feature, bug fix, refactor, or experiment starts from a new branch
- every branch should have a single clear purpose
- merge into `main` only after review and validation
- delete merged branches after completion

---

## Branch Types

### Feature branches

Used for new functionality.

Examples:

- `feature/parser-framework`
- `feature/wiki-writer`
- `feature/search-index`

### Fix branches

Used for bug fixes.

Examples:

- `fix/pdf-encoding`
- `fix/notebook-parser`
- `fix/windows-path-handling`

### Refactor branches

Used for internal restructuring without changing product goals.

Examples:

- `refactor/document-schema`
- `refactor/parser-api`

### Experiment branches

Used for trials, prototypes, and risky AI engineering exploration.

Examples:

- `exp/deepdoc-backend`
- `exp/local-embedding`
- `exp/langgraph-orchestrator`

Experiments are allowed to fail.
If an experiment is not useful, close it and delete the branch.

---

## Main Branch Policy

`main` must always remain:

- runnable
- understandable
- minimally documented
- structurally clean
- suitable as the current best version of the system

Do not allow unfinished work to accumulate on `main`.

---

## Before Starting Any Task

Codex must do the following before implementation:

1. read this skill
2. identify the exact scope of the task
3. determine the correct branch type
4. confirm whether the current branch is safe to use
5. if not already on a task-specific branch, instruct the user to create one or note the required branch name
6. summarize the implementation plan before changing files

---

## Branch Naming Rules

Branch names should be:

- short
- descriptive
- lowercase
- hyphen-separated

Pattern:

- `feature/<name>`
- `fix/<name>`
- `refactor/<name>`
- `exp/<name>`

Good examples:

- `feature/source-registry`
- `feature/parser-adapters`
- `fix/docx-title-extraction`
- `exp/deepdoc-pdf-parser`

Bad examples:

- `newbranch`
- `my-work`
- `feature/parser-and-writer-and-ui`
- `test123`

---

## Scope Control Rules

Each branch should do one thing only.

### Good

- one parser milestone
- one bug fix
- one schema refactor
- one experiment

### Bad

- parser + search + UI in one branch
- refactor + bug fix + docs rewrite mixed together
- unrelated changes across many modules without clear reason

If scope is too large, split the work into multiple branches.

---

## Codex Execution Rules

When implementing on a branch, Codex should:

- work only within the requested scope
- avoid unrelated file changes
- avoid opportunistic rewrites unless necessary
- explain architectural changes before applying them
- keep commits logically grouped
- preserve stability of existing working modules

If a requested task would require unrelated changes, Codex should explicitly say so before proceeding.

---

## Pull Request Policy

Every branch should be merged through a pull request.

The pull request should contain:

- purpose of the change
- affected modules
- key design decisions
- validation performed
- known limitations
- follow-up tasks if any

### Pull Request Title Format

- `feat(parser): add adapter-based parser framework`
- `fix(ipynb): preserve markdown cells correctly`
- `refactor(schema): simplify normalized document model`

---

## Commit Message Rules

Use structured commit messages.

Pattern:

`type(scope): summary`

Examples:

- `feat(parser): add parser manager and adapter interface`
- `fix(pdf): handle missing title metadata`
- `refactor(repo): simplify source scanning`
- `docs(skill): improve parser architecture spec`
- `test(notebook): add malformed ipynb coverage`

### Commit Types

- `feat`
- `fix`
- `refactor`
- `docs`
- `test`
- `chore`

Avoid vague commit messages like:

- `update`
- `change stuff`
- `fix bug`
- `work in progress`

---

## Review and Validation Rules

Before merge, the branch should be checked for:

- correct scope
- no obvious regression
- tests added or updated if needed
- documentation updated if architecture changed
- no accidental unrelated edits
- branch still aligned with product spec

Codex should encourage validation before merge.

---

## Merge Rules

Preferred merge path:

1. branch work completed
2. tests or validation completed
3. pull request opened
4. review performed
5. merge into `main`
6. delete branch

Do not merge obviously unstable or exploratory code into `main`.

---

## Protected Branch Recommendation

Repository owners should protect `main`.

Recommended protection settings:

- require pull request before merge
- require passing checks before merge
- restrict direct pushes to `main`
- optionally require review before merge

This reduces the chance that unstable or unreviewed changes land on the default branch.

---

## Experimental Work Policy

AI engineering projects often require exploration.

Use `exp/*` branches for:

- trying alternate parsers
- trying new embedding strategies
- testing LangGraph or other orchestration ideas
- evaluating DeepDoc or other parsing backends

Rules for experiments:

- do not pollute `main`
- document the purpose of the experiment
- summarize findings before merge decision
- merge only if the experiment produces clear value

---

## Recovery Rules

If Codex produces poor or risky changes:

- stop further edits
- summarize the risk
- recommend reverting the branch or selected commits
- do not continue stacking more changes on a broken branch

If the branch becomes too messy:

- create a fresh branch
- re-implement the clean subset of changes

---

## Task Start Checklist for Codex

Before coding, confirm:

- what is the task?
- what branch should this be on?
- is the current branch correct?
- what files are expected to change?
- what files should not change?
- how will the result be validated?

Codex should state this clearly before implementation.

---

## Task End Checklist for Codex

Before considering work complete, confirm:

- implementation matches requested scope
- unrelated changes were avoided
- tests or validation steps are documented
- docs were updated if needed
- branch is ready for PR or further review

---

## Standard Prompting Pattern

The user can instruct Codex with prompts like:

### Start work

Read `docs/skills/git-github-workflow-skill.md` before doing anything.

We are implementing:
`Milestone X`

Work only on the current task scope.
Before coding:
1. restate the task
2. confirm the correct branch name
3. list files likely to change
4. identify risks
5. then implement

### Review work

Read `docs/skills/git-github-workflow-skill.md`.

Review this branch against:
- scope control
- architectural cleanliness
- unnecessary file changes
- readiness for PR

Do not implement yet.
Only report findings.

---

## Non-Goals

This skill does not require:

- heavyweight GitFlow
- long-lived `develop` branch
- release branch process in early project stages
- complex multi-team branching rules

This project should stay simple and disciplined.

---

## Final Principle

Git is not only version control.

In this project, Git is the safety boundary that keeps Codex productive without letting AI-generated changes damage the main line of development.

`main` is trust.
Branches are isolation.
Pull requests are review.