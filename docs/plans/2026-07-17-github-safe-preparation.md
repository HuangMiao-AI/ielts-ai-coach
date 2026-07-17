# GitHub-Safe Local Preparation Plan

**Goal:** Prepare IELTS AI Coach for a first private GitHub repository commit
without creating a remote, pushing, calling a real AI provider, or changing
runtime user data.

## Audit

- Read the active project instructions and handover documents.
- Inspect the actual source tree, local Git state, configuration templates,
  data files, archives, screenshots, and available tooling.
- Scan text files for high-confidence secrets, credentials, private contact
  details, and local absolute paths without printing matched values.
- Record database file fingerprints so later checks can prove that runtime
  data was not deleted or changed.

## Prepare

- Extend `.gitignore` for virtual environments, caches, private configuration,
  databases, backups, logs, uploads, editor state, archived prototypes, and
  unsanitized local screenshots.
- Update English and Chinese documentation with accurate features, stack,
  installation, local/LAN startup, testing, AI modes, database behavior,
  copyright status, and limitations.
- Remove machine-specific paths and real database record counts from project
  documentation.
- Keep example configuration files trackable and free of real credentials.

## Verify

- Initialize the existing empty Git metadata directory as a `main` repository
  while preserving any valid history if discovered.
- Confirm ignored files are not staged or tracked, inspect the complete staged
  file list, and rescan staged text for sensitive material.
- Run the full pytest suite, `pip check`, headless Streamlit startup, and HTTP
  health checks with a temporary SQLite database and Mock AI mode.
- Compare runtime database fingerprints before and after verification.

## Finish

- Update `.memory.md` with the durable repository-preparation state and fresh
  verification baseline.
- Create one local commit named
  `Prepare IELTS AI Coach private GitHub release` only after all safety and
  verification checks pass.
- Report local repository status, tracked-file count, test results, remote
  state, and any items that still require manual review.
