# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

- Install dependencies:
  - `.venv/bin/python -m pip install pytest httpx pydantic`
- Run all tests:
  - `.venv/bin/python -m pytest -v tests`
- Run single tests:
  - `.venv/bin/python -m pytest tests/test_phase1_monitor.py::test_phase1_always_read_only -v`
  - `.venv/bin/python -m pytest tests/test_phase2_auto_enroll.py::test_stop_after_first_success_is_enabled -v`
  - `.venv/bin/python -m pytest tests/integration/test_reverse_flow_dry_run.py -v`
- Run phase scripts:
  - `EXECUTION_MODE=READ_ONLY .venv/bin/python scripts/phase1_monitor.py`
  - `EXECUTION_MODE=DRY_RUN .venv/bin/python scripts/phase2_auto_enroll.py`
  - `EXECUTION_MODE=ARMED .venv/bin/python scripts/phase2_auto_enroll.py`

## Architecture

- Two-entry architecture:
  - `scripts/phase1_monitor.py`: read-only monitoring of target courses.
  - `scripts/phase2_auto_enroll.py`: monitor + auto-enroll, stop after first success.
- Core modules under `src/byxt_bot/`:
  - `auth_client.py`: token/batch auth state + request headers.
  - `http_session.py`: authenticated HTTP session wrapper (token cookies + headers).
  - `course_client.py`: reverse-engineered API client for
    - `POST /elective/buaa/clazz/list`
    - `POST /elective/select`
    - `POST /elective/clazz/add`
  - `rule_engine.py`: target filtering rule
    - category in `通识选修课`/`综合素养课`
    - language = `全英语`
    - schedule contains `智慧树[主讲]` or `网络授课无教室`
  - `safety_guard.py`: hard safety gates (deny deselect endpoints + no-course-lost check).
  - `enroll_executor.py`: execution mode aware enrollment (`READ_ONLY`/`DRY_RUN`/`ARMED`).
  - `monitor_service.py`: polling and availability detection.

## Reverse artifacts

- Captured request/response and JS assets are stored in `reverse_artifacts/`.
- Key captured endpoints:
  - `POST /elective/buaa/clazz/list`
  - `POST /elective/clazz/add`
  - `POST /elective/clazz/del` (must never be called by automation)

## Safety constraints

- Never call deselect endpoints (`/elective/clazz/del`, `/elective/deselect`).
- Always verify selected-course set before/after enroll to ensure no existing course is lost.
- For implementation changes, preserve the red-line behavior above.
