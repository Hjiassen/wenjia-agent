# Implementation Tasks

- [x] Task 1: Account/session persistence and authentication API
  - Acceptance: register, login, me, logout; Argon2id hashes; HttpOnly cookie; expired/revoked sessions return 401.
  - Verify: `poetry run pytest tests/test_auth.py tests/test_web_example.py -q`
  - Files: `apps/web/backend/modules/auth.py`, `apps/web/backend/api/auth.py`, `apps/web/backend/schemas.py`, `apps/web/backend/app_factory.py`, `apps/web/backend/lifespan.py`, `tests/test_auth.py`

- [x] Task 2: Account-scoped profile CRUD
  - Acceptance: list/get/create/update/delete/restore; delete sets `deleted_at`; all operations enforce `user_id`.
  - Verify: `poetry run pytest tests/test_profiles_api.py tests/test_profile_store.py -q`
  - Files: `apps/web/backend/modules/profiles.py`, `apps/web/backend/api/profiles.py`, `tests/test_profiles_api.py`

- [x] Task 3: Independent memory logic
  - Acceptance: no profile auto-save; profile-shaped memory writes fail; memory CRUD is account-scoped.
  - Verify: `poetry run pytest tests/test_memory_store.py tests/test_web_example.py -q`
  - Files: `wenjia_agent/runtime/memory_store.py`, `wenjia_agent/runtime/profile_store.py`, `apps/web/backend/api/memories.py`, `tests/test_memory_store.py`

- [ ] Task 4: Runtime user/profile/memory context isolation
  - Acceptance: authenticated user ID is derived server-side; selected active profiles and relevant memories are separate context blocks.
  - Verify: `poetry run pytest tests/test_web_example.py tests/test_context_builders.py -q`

- [ ] Task 5: Existing database migration
  - Acceptance: existing tables upgrade idempotently; legacy profile memories are excluded and report migration outcomes.
  - Verify: `poetry run pytest tests/test_migrations.py -q`

- [ ] Task 6: Frontend authentication and cache isolation
  - Acceptance: register/login/logout state, protected fetches, no account data visible after logout, unauthenticated app access is blocked.
  - Verify: `npm test -- --runInBand`; `npm run build`

- [ ] Task 7: Frontend profile CRUD and soft-delete UI
  - Acceptance: account profile list/create/edit/delete/restore; deleted profiles cannot be selected for chat.
  - Verify: `npm test -- --runInBand`; `npm run build`

- [ ] Task 8: Frontend memory and chat contract
  - Acceptance: memory page excludes profile records; chat sends selected profile IDs and authenticated cookies.
  - Verify: `npm test -- --runInBand`; `npm run build`
