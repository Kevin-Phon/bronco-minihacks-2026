# SideQuest Backend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Prepare Kevin's runnable, validated AI/backend and team handoff.
**Architecture:** Flask endpoint orchestrates typed candidate places, Groq generation, validation and deterministic fallback. Explicit synthetic demo remains separate from real place generation.
**Tech Stack:** Python 3.10+, Flask 3, Pydantic 2, Groq Python SDK, pytest.
**Spec:** docs/superpowers/specs/2026-10-23-sidequest-backend-design.md

## Global Constraints
- No frontend or Overpass implementation, repository push, secret logging, or automatic paid calls.
- Exactly 3 places; model llama-3.1-8b-instant; one invalid-output retry, no SDK retries; bounded provider timeout.
- Names/coordinates are server-owned. All fallback/demo modes labeled.

## Review Focus
- Unknown/duplicate IDs must not escape into a response.
- Malformed requests, booleans/nan/out-of-range numbers must not trigger external calls.
- Empty or unsuitable candidate lists must not become an unrelated campus quest.
- Missing key and provider errors must not leak secrets or cause unbounded retry.
- Demo must not depend on internet or pretend to be live AI.

### Task 1: Typed request and response validation
- [x] Add failing tests for strict input bounds, IDs, duplicate candidates and creative fields.
- [x] Run tests and observe missing behavior.
- [x] Implement backend/schemas.py using Pydantic, lat/lon bounds and finite nonnegative budget.
- [x] Run tests until green.

### Task 2: Quest generation and Groq boundary
- [x] Add failing tests for original-coordinate preservation, ID validation, one retry, provider failure and labeled fallback.
- [x] Implement backend/quest_ai.py: generate_quest(request, places, complete=None); make Groq adapter with max_retries=0 and 10-second timeout.
- [x] Use httpx MockTransport to exercise actual SDK serialization without paid/network calls.
- [x] Run full suite.

### Task 3: Flask integration and team handoff
- [x] Add failing route tests for JSON request errors, no candidates, explicit demo, health and injected place provider.
- [x] Implement create_app with POST /api/quest, POST /api/demo-quest and GET /api/health; add places.py adapter stub.
- [x] Add diagnostic page and smoke script, README/API docs, config placeholders.
- [x] Run full suite and actual local HTTP smoke check, then review before delivery.
