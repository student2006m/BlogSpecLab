# BlogSpecLab Constitution

> This document is the binding source of stable principles for the `BlogSpecLab` project and governs all `Specify`, `Clarify`, `Plan`, `Tasks`, `Implement`, `Test`, and `Review` stages. Any conflict between a `Specification` or `Plan` and this document MUST be resolved before implementation.

## Project Context

`BlogSpecLab` is an integrated system for managing and publishing blog posts.

- Initial release: post management and controlled publishing of approved content.
- Incremental follow-ups: `Structured Output`, `Tool Calling`, `MCP`, `RAG` with `Qdrant`, and `Agent`, only in response to approved requirements.
- Primary language: `Python` `3.12` or newer; web framework: `Flask`.
- Development method: `SDD` with `Spec Kit`.

Undecided items, to be decided later and NOT selected by this document: operational database, `ORM`, dependency and virtual-environment tooling, test framework, import-rule checker, language-model provider, and `Embedding Model`.

## Core Principles

### I. Specification-Driven Development (NON-NEGOTIABLE)

- Every feature MUST be developed from a reviewed and approved `Specification`.
- Before implementation, expected behavior, constraints, acceptance criteria, and important error scenarios MUST be defined.
- The `SDD` cycle (`Specify`, `Clarify`, `Plan`, `Tasks`, `Implement`, `Test`, `Review`) MUST be followed proportionate to the change type.
- A significant behavioral change MUST first be reflected in the `Specification`; its impact on design, tasks, code, and tests MUST then be reviewed.
- `Coding Agent` output MUST be checked for conformance with the `Specification` and this `Constitution` before acceptance.

### II. Architecture and Dependency Rules (NON-NEGOTIABLE)

The project MUST be developed as one integrated, non-modular system with clear separation of responsibilities. Target structure:

```text
BlogSpecLab/
├── pyproject.toml
├── src/
│   └── blogspeclab/
│       ├── core/
│       │   ├── domain/
│       │   └── application/
│       ├── infra/
│       │   ├── data_access/
│       │   ├── ai/
│       │   └── qdrant/
│       └── endpoints/
│           └── api/
├── tests/
└── .specify/
```

- `infra/ai` and `infra/qdrant` packages MUST be created only when a real need arises.
- Responsibilities:
  - `core.domain`: entities, value objects, domain rules, and invariants; independent of infrastructure and independent of `Flask`.
  - `core.application`: use cases, operation orchestration, use-case authorization checks, and contracts for external services (e.g. `Protocol` or `ABC`).
  - `infra.data_access`: `Persistence` and `Repository` implementations and operational data-access details.
  - `infra.ai`: language-model integration and provider `SDK` implementations.
  - `infra.qdrant`: `Qdrant` integration and vector storage/search operations.
  - `endpoints.api`: `HTTP` entrypoint with `Flask`, `API` contracts, `Application Factory`, and `Composition` (dependency wiring). `Flask Blueprint` use is allowed only for organizing `HTTP` routes inside this layer and does NOT imply a modular architecture.
  - `tests`: automated tests matching the created features.

Binding `Import` and dependency rules:

1. `core.domain` MUST NOT import any other project package and MUST NOT depend on `Flask` or infrastructure libraries.
2. `core.application` MAY import from `core.domain`, but MUST NOT import from `infra` or `endpoints`.
3. `infra` packages MAY import from `core.application` and, when needed, from `core.domain`.
4. `endpoints.api` MAY import from `core.application` and from required `infra` packages for `Composition`.
5. Cyclic imports and direct imports between `infra` packages are forbidden without a documented architecture decision.
6. Business logic MUST NOT be duplicated in `endpoints` or `infra`.
7. `Modules` structure, `Microservices` architecture, `ZaminX`, or proprietary `Building Block`s from other projects are NOT allowed in this project.
8. New packages and abstractions MUST be created only when an approved requirement justifies them.
9. Compliance with `Import` rules MUST be verifiable through tooling or automated tests.

### III. Security and Responsibility Boundaries (NON-NEGOTIABLE)

- Business rules and entity-state invariants MUST be enforced in `Domain` or `Application`.
- Authorization checks and preconditions for sensitive operations MUST run on the trusted path.
- `HTTP` input, language-model output, `Tool` arguments, and data retrieved from external sources are untrusted and MUST be validated appropriate to the use.
- No language model or `Agent` MUST authorize a system-state change solely on the basis of its own output.
- Sensitive and mutating operations MUST verify required approvals in `Application`.
- Secrets and `API Key`s MUST NOT be stored in source code or `Log`s and MUST be provided through environment configuration (e.g. `Environment Variables`).

### IV. Quality and Testability

- Important `Domain` rules and `Application` use cases MUST be covered by automated tests.
- Tests MUST cover success, failure, boundary, and unauthorized-access scenarios proportionate to feature behavior.
- `Domain` and `Application` logic MUST be testable independently of external services and without starting `Flask` wherever possible.
- External integrations MUST be tested at the appropriate level.
- Syntactic or structural validity of language-model output alone does NOT imply semantic or business correctness.
- Every feature MUST have acceptance criteria and reviewable evidence of completion.
- `Python` code MUST have `Type Hint`s; they are mandatory on public layer boundaries (contracts and use-case inputs/outputs).

### V. Simplicity and Incremental Growth

- Readability, simplicity, and explainability take precedence over unnecessary complexity.
- Premature packages, base classes, `Protocol`s, frameworks, and abstractions without a real need MUST be avoided.
- The initial release MUST run without any dependency on a language model, `MCP`, `Agent`, or `Vector Database`.
- `AI` capabilities MUST be added incrementally in response to approved requirements.
- `Tool Calling` and `MCP` MUST reuse existing `Application` capabilities and MUST NOT create independent business logic.
- In `RAG`, the knowledge ingestion/preparation path MUST be separated from the `Retrieval` and `Generation` path.
- An `Agent` MUST use controlled tools, a step limit, stop conditions, and required human approval.
- Selection of `AI` models, `SDK`s, and frameworks MUST happen when the real need arises and with review of constraints and architecture implications.

## Governance

This section is Principle VI and takes precedence over other documents and decisions.

- This `Constitution` is the authoritative source of stable, binding development principles.
- Every change to it MUST state its rationale and review its impact on specifications, design, code, and tests.
- A conflict between a `Specification` or `Plan` and this `Constitution` MUST be resolved before implementation.
- Every change MUST record version, change date, and change summary.
- If a principle cannot be followed in a specific case, the exception MUST be documented with rationale, consequences, and explicit approval.
- Documentation MUST reflect approved decisions and actual project state; planned features MUST NOT be presented as implemented.

**Version**: 1.1.0 | **Ratified**: 2026-10-12 | **Last Amended**: 2026-10-12
