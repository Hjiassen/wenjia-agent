# Implementation Plan: Account, Profiles, and Independent Long-Term Memory

## Overview

Implement the approved v0.3 Web feature in vertical slices. Keep `wenjia_agent` reusable while moving account ownership and profile CRUD into an account-aware Web boundary. Long-term memory will reject profile-shaped records and will be composed independently at runtime.

## Architecture Decisions

- Use server-side sessions with an HttpOnly cookie; store only token hashes.
- Use Argon2id via `pwdlib[argon2]`; do not put credentials in localStorage.
- Keep the existing SQLite URL and add idempotent schema migration helpers because the repository currently uses `create_all` and has no Alembic setup.
- Add account/profile services under `apps/web/backend/modules`; remove legacy runtime profile ownership.
- Account-owned profile APIs are the only profile APIs.
- Profile deletion is soft deletion with restore; memory deletion remains physical and profile records are never mirrored into memory.

## Task List

### Phase 1: Foundation

- [ ] Task 1: Add account/session persistence, password hashing, auth dependency, and auth API.
- [ ] Task 2: Add account-scoped profile service/API with CRUD, soft delete, restore, and ownership tests.
- [ ] Task 3: Remove profile-to-memory writes and reject profile-shaped long-term memory records.

### Checkpoint: Backend contracts

- [ ] Auth, profile, and memory API tests pass.
- [ ] Existing unauthenticated chat/profile/memory requests are rejected with `401`.

### Phase 2: Runtime and migration

- [ ] Task 4: Add authenticated user propagation and separate profile/memory context assembly.
- [ ] Task 5: Add idempotent schema/data migration for account profiles and legacy `kind=profile` memories.

### Checkpoint: Runtime isolation

- [ ] Authenticated requests cannot read another user's data.
- [ ] Profile data is never injected through the long-term memory path.

### Phase 3: Frontend

- [ ] Task 6: Add auth state, registration/login/logout UI, and cache namespace isolation.
- [ ] Task 7: Move profile UI to account-scoped CRUD with soft-delete/recycle-bin behavior.
- [ ] Task 8: Update long-term memory UI and chat requests to use authenticated identity and explicit memory types.

### Checkpoint: Complete

- [ ] Backend tests, frontend tests, type-check, lint, and build pass.
- [ ] Manual flow works: register -> create profile -> chat with selected profile -> manage memory -> logout/login on another browser.

## Risks and Mitigations

| Risk | Impact | Mitigation |
| --- | --- | --- |
| Existing SQLite tables lack account columns | High | Idempotent additive migration and compatibility tests before changing queries |
| SDK session tables are not user-owned | High | Add an ownership table for Web sessions and authorize before Agent access |
| Existing auto-save creates profile memories | High | Remove the call, reject `kind=profile`, and add regression tests |
| Frontend localStorage leaks account data after logout | High | Namespace caches by auth user and clear the active account namespace on logout |
| Password reset is unavailable in username MVP | Medium | Keep explicit open scope; do not claim recovery until verified email is implemented |

## Open Questions

- The approved product scope still needs a future decision on email verification and soft-delete retention. MVP keeps username/password and indefinite soft deletion.
