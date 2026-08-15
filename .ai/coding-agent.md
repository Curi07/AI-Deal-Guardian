# AI Deal Guardian — Coding Agent Instructions

## Goal
Resolve GitHub Issues with focused, reviewable code changes and open a Pull Request. Never merge automatically.

## Repository rules
- Groq is the active LLM provider.
- Preserve the existing architecture unless the issue requires a change.
- Keep Scope Guard classification independent from human-review requirements.
- Do not modify GitHub Actions workflows as part of a normal product issue unless the issue explicitly asks for workflow changes.
- Do not modify Docker, deployment infrastructure, secrets, credentials, or production configuration.
- Do not remove existing tests.

## Validation
- Add or update focused tests for the requested behavior.
- Run the full pytest suite before opening the PR.
- If tests fail, diagnose and fix the implementation before creating the PR.

## Delivery
- Work on a dedicated branch.
- Create a Pull Request against `main`.
- Reference the GitHub Issue in the PR body.
- Never merge the PR automatically.
