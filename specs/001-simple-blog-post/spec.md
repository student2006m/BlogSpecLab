# Feature Specification: Simple Blog Post Management and Controlled Publishing

**Feature Branch**: `001-simple-blog-post`

**Created**: 2026-10-13

**Status**: Approved

**Input**: User description: "We want a simple system for managing blog posts. Authors must be able to manage their own posts and editors publish them after review and approval. No post must be published without required authorization or approval."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Author manages own posts (Priority: P1)

An authenticated author creates a draft post, views it later, edits its content, and deletes it while it is still unpublished.

**Why this priority**: This is the core content-creation capability; without it there is nothing to review or publish.

**Independent Test**: Can be fully tested by creating a post as an author, listing only that author's posts, editing it, and deleting it, without any editor or publishing action.

**Acceptance Scenarios**:

1. **Given** an authenticated author, **When** the author creates a post with valid title and content, **Then** the system stores it as an unpublished post owned by that author.
2. **Given** an author with existing posts and another author with existing posts, **When** the first author lists posts, **Then** only posts owned by the first author are returned.
3. **Given** an author owns an unpublished post, **When** the author updates its title/content, **Then** the stored post reflects the new values and ownership is unchanged.
4. **Given** an author owns an unpublished post, **When** the author deletes it, **Then** the post is no longer listed or retrievable by that author.

---

### User Story 2 - Controlled review and publishing (Priority: P2)

An author submits an owned post for review; an editor reviews it and either approves/publishes it or rejects it back to the author. Published posts become visible as published content.

**Why this priority**: This delivers the requested controlled publishing of approved content and is the first end-to-end value slice after P1.

**Independent Test**: Can be fully tested by submitting a draft for review, approving and publishing it as an editor, and verifying its published state; plus a separate reject path returning the post to draft.

**Acceptance Scenarios**:

1. **Given** an author owns a draft post, **When** the author submits it for review, **Then** its state changes to pending review and it is no longer editable as a plain draft.
2. **Given** a post pending review, **When** an editor approves and publishes it, **Then** its state becomes published and the publish decision and actor are recorded.
3. **Given** a post pending review, **When** an editor rejects it, **Then** its state returns to draft with a recorded rejection reason.
4. **Given** a published post, **When** any consumer — including an anonymous (unauthenticated) user — requests the published listing or the post itself, **Then** the post is included with its final approved title and content.

---

### User Story 3 - Authorization and approval enforcement (Priority: P3)

The system prevents publishing without required approval and prevents users from acting on posts outside their permission.

**Why this priority**: This is the security backbone of the feature; it guarantees "no publish without authorization or approval" but is verifiable incrementally after P1–P2.

**Independent Test**: Can be fully tested by attempting forbidden actions (author publishing directly, author editing another author's post, editor publishing a draft never submitted) and verifying each is rejected without state change.

**Acceptance Scenarios**:

1. **Given** a draft post never submitted for review, **When** anyone attempts to publish it directly, **Then** the request is rejected and the post remains unpublished.
2. **Given** a post owned by author A, **When** author B attempts to view, edit, delete, or submit it, **Then** the system responds with `404 Not Found` without revealing whether the post exists, and no state change occurs.
3. **Given** an authenticated author without the editor role, **When** the author attempts an editor-only publish/approve action on their own post, **Then** the request is rejected with `403 Forbidden` and no state change occurs.
4. **Given** a published post, **When** an author attempts to edit, delete, or submit it as a draft operation, **Then** the request is rejected; corrections require an editor to unpublish the post back to `draft` first.
5. **Given** a post owned by a user who also holds the editor role, **When** that same user attempts to approve or publish their own post, **Then** the request is rejected; a different editor MUST approve it (separation of duties).
6. **Given** a published post, **When** an editor unpublishes it with a recorded reason, **Then** its state returns to `draft` and it immediately leaves the public listing.

### Edge Cases

- What happens when title or content is empty or whitespace-only? The request is rejected with `400 Bad Request`; there is no maximum length in v1.
- What happens when a requested post does not exist or was already deleted? The system responds with `404 Not Found`.
- What happens when a caller requests an unpublished post owned by another user? The system responds with `404 Not Found` without revealing its existence.
- What happens when an author tries to submit an already pending-review or already published post? The request is rejected and the state is unchanged.
- What happens when an editor tries to approve an already published post or reject a draft post? The request is rejected and the state is unchanged.
- What happens when an editor attempts to approve their own post? The request is rejected (separation of duties); another editor MUST approve it.
- What happens when author and editor act concurrently on the same post (e.g. delete vs. publish)? The first committed transition wins; the second request is rejected against the new state.
- How does the system handle unauthenticated requests to author/editor operations? They are rejected with `401 Unauthorized`; anonymous access is allowed only for the published listing and published post reads.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST allow an authenticated author to create a post with title and content.
- **FR-002**: System MUST record post ownership at creation and MUST preserve it on updates.
- **FR-003**: Authors MUST be able to list and retrieve only posts they own. Anonymous (unauthenticated) users MUST be able to list and read published posts, and MUST NOT access unpublished posts.
- **FR-004**: System MUST allow an author to update title/content of an owned post while it is in draft state. Published posts are locked against author edits.
- **FR-005**: System MUST allow an author to delete an owned post while it is in draft state, and MUST reject author deletion of posts in `pending_review` or `published` state.
- **FR-006**: System MUST support explicit post states `draft`, `pending_review`, and `published`; transitions MUST follow: `draft -> pending_review -> published`, plus `pending_review -> draft` on rejection and `published -> draft` on editor unpublish.
- **FR-007**: System MUST allow an author to submit an owned draft post for review, moving it to `pending_review`.
- **FR-008**: System MUST allow a user in the editor role to approve and publish a post that is in `pending_review`. An editor MUST NOT approve or publish a post they own (separation of duties); self-approval MUST be rejected.
- **FR-009**: System MUST allow a user in the editor role to reject a post in `pending_review` back to `draft` with a recorded reason.
- **FR-009b**: System MUST allow a user in the editor role to unpublish a `published` post back to `draft` with a recorded reason; the post MUST immediately leave the public listing.
- **FR-010**: System MUST reject any publish transition that does not originate from `pending_review` with editor approval; no other path MAY set state to `published`.
- **FR-011**: System MUST enforce ownership on every author-scoped operation; operations on posts owned by another user MUST be rejected.
- **FR-012**: System MUST enforce role checks on the trusted path (`Application` layer per Constitution): editor-only actions MUST be rejected for non-editors.
- **FR-013**: System MUST validate title and content on create/update/submit and MUST reject empty or whitespace-only values with `400 Bad Request`. No maximum length is enforced in v1.
- **FR-014**: System MUST NOT leak the existence of other users' unpublished posts: requests for non-existent posts and requests for unpublished posts owned by another user MUST both receive `404 Not Found`. Insufficient-role actions on a caller's own post MUST receive `403 Forbidden`; unauthenticated requests to protected operations MUST receive `401 Unauthorized`.
- **FR-015**: System MUST authenticate users with username/password plus session and MUST make caller identity and roles available for every operation. A single user MAY hold both `author` and `editor` roles. User/credential storage technology is NOT selected by this spec.
- **FR-016**: System MUST persist posts and their state transitions across restarts via operational storage selected later; this spec does NOT select database or `ORM`.

### Key Entities

- **Post**: A blog entry with title, content, owner reference, lifecycle state (`draft`, `pending_review`, `published`), and review/publish history (actor, decision, timestamp, reason where applicable).
- **User**: An authenticated actor identified via username/password session; each user has an identity and one or both roles. Roles: `author` (owns and manages own posts) and `editor` (reviews, approves/rejects, publishes, unpublishes). A user MAY hold both roles, but MUST NOT approve or publish their own post.
- **Review Decision**: The outcome of editor review on a `pending_review` post: approval leading to publish, or rejection with reason returning the post to `draft`.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: An author can create a draft and retrieve it as owner in 100% of valid trials.
- **SC-002**: Authors can only see and mutate their own unpublished posts; 100% of cross-author access attempts receive `404` without state change.
- **SC-003**: 100% of direct publish attempts bypassing `pending_review` plus editor approval are rejected and leave state unchanged.
- **SC-004**: 100% of valid `draft -> pending_review -> published` flows, `pending_review -> draft` rejection flows, and `published -> draft` unpublish flows reach the expected end state with recorded actor and decision.
- **SC-005**: 100% of unauthenticated requests to protected operations (`401`), 100% of non-editor publish/approve attempts, and 100% of self-approval attempts are rejected.
- **SC-006**: Anonymous users can list and read 100% of published posts and 0% of unpublished posts.

## Assumptions

- Authentication is username/password plus session; caller identity and roles come from the session. User/credential storage technology is NOT selected by this spec.
- Validation is minimal in v1: title and content MUST be non-empty; no maximum length.
- Published posts are locked: author edits/deletes of published posts are rejected; only an editor unpublish (`published -> draft` with recorded reason) reopens them.
- Published listing and published reads are public and anonymous; all unpublished access requires authentication plus ownership or editor role, and cross-user unpublished access returns `404`.
- A user MAY hold both roles but MUST NOT approve or publish their own post; approval requires a different editor.
- A minimal post model (title, content, owner, state, history) is sufficient for v1; rich features such as tags, categories, comments, scheduling, versioning, and media uploads are out of scope.
- Single integrated deployment; multi-tenancy and metering are out of scope. Public anonymous listing of published posts is in scope per FR-003.
- `AI`, `MCP`, `Agent`, `RAG`, and vector search are explicitly out of scope for this feature; the initial implementation MUST run without them per the Constitution.
- Persistence technology, `ORM`, dependency tooling, test framework, and import-rule checker are NOT selected by this spec per the Constitution.
