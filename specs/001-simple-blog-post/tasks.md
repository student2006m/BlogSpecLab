# Tasks: Simple Blog Post Management and Controlled Publishing

**Input**: Design documents from `/specs/001-simple-blog-post/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/api.md, quickstart.md, technical-baseline.md

**Tests**: INCLUDED — automated coverage of Domain rules, use cases, and unauthorized access is explicitly required by Constitution Principle IV and Success Criteria SC-001..SC-006. Write tests first; ensure they FAIL before implementation.

**Organization**: Grouped by user story; each story is an independently testable increment.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [X] T001 Create pyproject.toml (PEP 621, requires-python >=3.12, runtime Flask, dev pytest) in pyproject.toml
- [X] T002 [P] Create src package skeleton __init__.py files in src/blogspeclab/__init__.py, src/blogspeclab/core/__init__.py, src/blogspeclab/core/domain/__init__.py, src/blogspeclab/core/application/__init__.py, src/blogspeclab/infra/__init__.py, src/blogspeclab/infra/data_access/__init__.py, src/blogspeclab/endpoints/__init__.py, src/blogspeclab/endpoints/api/__init__.py
- [X] T003 [P] Create tests skeleton and shared fixtures (temp SQLite, Flask test client, demo users) in tests/conftest.py

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T004 Create SQLite schema and connection helper (posts, users, decisions tables) in src/blogspeclab/infra/data_access/db.py
- [X] T005 [P] Define ports (PostRepository, UserStore, PasswordHasher, Clock) in src/blogspeclab/core/application/ports.py
- [X] T006 Implement SQLite repositories behind ports in src/blogspeclab/infra/data_access/repositories.py (depends on T004, T005)
- [X] T007 Implement env-based demo-user seeding in src/blogspeclab/infra/data_access/seed.py (depends on T004, T006)
- [X] T008 Create Flask application factory with dependency composition in src/blogspeclab/endpoints/api/app.py (depends on T006, T007)
- [X] T009 Implement centralized RFC 9457 problem+json error handlers in src/blogspeclab/endpoints/api/errors.py (depends on T008)
- [X] T010 Implement session/current-user loader (id + roles into request context) in src/blogspeclab/endpoints/api/auth.py (depends on T005, T008)
- [X] T011 [P] Implement ast-based import-rule test asserting Constitution §II.1–5 in tests/architecture/test_import_rules.py

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Author manages own posts (Priority: P1) 🎯 MVP

**Goal**: Authenticated authors create, list, retrieve, update, delete, and submit their own draft posts.

**Independent Test**: Create a post as author A, list (only A's posts visible), edit, submit, delete — with zero editor involvement; author B sees none of A's posts (SC-001, SC-002).

### Tests for User Story 1

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [X] T012 [P] [US1] Domain unit tests for Post validation ("MUST be non-empty after trimming; no max length in v1") and states in tests/unit/test_post.py
- [X] T013 [P] [US1] Application tests for author use cases with fake repository in tests/application/test_author_posts.py
- [X] T014 [P] [US1] HTTP contract tests for author endpoints (201/200/204/400/401/404 per contracts/api.md) in tests/http/test_author_posts.py

### Implementation for User Story 1

- [X] T015 [P] [US1] Implement Post entity, states (draft/pending_review/published), and ownership invariant ("ownership never changes") in src/blogspeclab/core/domain/post.py
- [X] T016 [P] [US1] Implement User entity with roles (author/editor, "MAY hold both") in src/blogspeclab/core/domain/user.py
- [X] T017 [US1] Implement author use cases (create/get/list-own/update/delete/submit, draft-only guards) in src/blogspeclab/core/application/author_posts.py (depends on T015, T016)
- [X] T018 [US1] Implement author routes (POST/GET/PATCH/DELETE /api/posts, POST /api/posts/<id>/submit) in src/blogspeclab/endpoints/api/posts.py (depends on T017)

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently

---

## Phase 4: User Story 2 - Controlled review and publishing (Priority: P2)

**Goal**: Editors work a cross-ownership review queue — revise, approve/publish, reject, unpublish — and published posts are publicly readable.

**Independent Test**: Submit as author, revise + approve as a different editor, verify anonymous published listing; reject path returns to draft with reason (SC-004, SC-006).

### Tests for User Story 2

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [X] T019 [P] [US2] Application tests for review queue, approve, reject/unpublish with mandatory reason, editor revise, separation of duties in tests/application/test_review.py
- [X] T020 [P] [US2] HTTP contract tests for review and public endpoints per contracts/api.md in tests/http/test_review.py
- [X] T021 [P] [US2] SQLite repository tests on temp DB (transitions, append-only history with actor/timestamp) in tests/application/test_repositories.py

### Implementation for User Story 2

- [X] T022 [US2] Implement review transitions and Decision record ("reject/unpublish always carry a non-empty reason") in src/blogspeclab/core/domain/post.py (depends on T015)
- [X] T023 [US2] Implement review use cases (queue/approve/reject/revise/unpublish/list-published, no self-approval) in src/blogspeclab/core/application/review.py (depends on T022)
- [X] T024 [P] [US2] Implement editor routes (review-queue/revise/approve/reject/unpublish) in src/blogspeclab/endpoints/api/review.py (depends on T023)
- [X] T025 [P] [US2] Implement anonymous published routes (GET /api/published) in src/blogspeclab/endpoints/api/public.py (depends on T023)

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently

---

## Phase 5: User Story 3 - Authorization and approval enforcement (Priority: P3)

**Goal**: No publish without approval; no cross-ownership or self-approved actions; correct 401/403/404 problem+json mapping.

**Independent Test**: Direct publish rejected; cross-author access → 404; self-approval → 403; unauthenticated → 401; state unchanged in all cases (SC-002, SC-003, SC-005).

### Tests for User Story 3

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T026 [P] [US3] Application tests for cross-author 404, direct-publish rejection, non-editor 403 in tests/application/test_authorization.py
- [ ] T027 [P] [US3] HTTP tests for 401/403/404 mapping, self-approval 403, problem+json shape in tests/http/test_authorization.py
- [ ] T028 [P] [US3] Security unit tests for pbkdf2 verification and env-only secrets in tests/unit/test_security.py

### Implementation for User Story 3

- [ ] T029 [US3] Harden status-code mapping (401/403/404) on all routes with problem+json bodies in src/blogspeclab/endpoints/api/errors.py (depends on T009)
- [ ] T030 [US3] Audit src/blogspeclab/endpoints/api/ for business-logic leaks and move violations into Application (files under src/blogspeclab/endpoints/api/)

**Checkpoint**: All user stories should now be independently functional

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [ ] T031 [P] Verify type hints on all public layer boundaries (contracts, use-case inputs/outputs) in files under src/blogspeclab/core/
- [ ] T032 [P] Validate quickstart.md end-to-end flow per specs/001-simple-blog-post/quickstart.md
- [ ] T033 Update AGENTS.md §7 with real install/run/test commands in AGENTS.md
- [ ] T034 Run full pytest suite and fix failures (no new files; evidence for SC-001..SC-006)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3-5)**: All depend on Foundational phase completion
  - User stories can then proceed in parallel (if staffed)
  - Or sequentially in priority order (P1 → P2 → P3)
- **Polish (Phase 6)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P2)**: Can start after Foundational (Phase 2) - Extends US1 domain module; independently testable
- **User Story 3 (P3)**: Can start after Foundational (Phase 2) - Hardens US1/US2 behavior; independently testable

### Within Each User Story

- Tests MUST be written and FAIL before implementation
- Domain before application
- Application before endpoints
- Story complete before moving to next priority

### Parallel Opportunities

- T002, T003 run in parallel (different files)
- T005, T011 run in parallel with the sequential foundation chain
- Once Foundational completes, US1/US2/US3 can start in parallel (if staffed)
- All test tasks within a story (T012-T014, T019-T021, T026-T028) run in parallel
- T015 + T016, T024 + T025 run in parallel (different files)

---

## Parallel Example: User Story 1

```bash
# Launch all tests for User Story 1 together:
Task: "Domain unit tests in tests/unit/test_post.py" (T012)
Task: "Application tests in tests/application/test_author_posts.py" (T013)
Task: "HTTP contract tests in tests/http/test_author_posts.py" (T014)

# Launch both domain entities together:
Task: "Post entity in src/blogspeclab/core/domain/post.py" (T015)
Task: "User entity in src/blogspeclab/core/domain/user.py" (T016)
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: Test User Story 1 independently (SC-001, SC-002)
5. Deploy/demo if ready

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Test independently → Deploy/Demo (MVP!)
3. Add User Story 2 → Test independently → Deploy/Demo
4. Add User Story 3 → Test independently → Deploy/Demo
5. Each story adds value without breaking previous stories

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Tests are required here by Constitution Principle IV + SC-001..SC-006 (not optional for this feature)
- Verify tests fail before implementing
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Avoid: vague tasks, same file conflicts, cross-story dependencies that break independence
