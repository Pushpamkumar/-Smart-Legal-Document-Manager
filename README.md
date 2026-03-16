# Smart Legal Document Manager

Production-style FastAPI backend for legal document versioning, diffing, and smart notifications. The system is designed to preserve historical accuracy, keep metadata concerns separate from content history, and expose clean REST APIs that are easy to extend.

## System Overview

This service helps lawyers:

- create legal documents with document metadata and an initial content version
- update document content without overwriting previous versions
- compare any two versions using a readable line-by-line diff
- receive smart notifications only for meaningful changes
- soft delete individual versions or entire documents

The implementation emphasizes correctness, transactional consistency, maintainability, and clear separation of concerns.

## Architecture

```text
app/
    main.py
    database.py
    core/
        config.py
        logging.py
    models/
        document.py
        version.py
        notification.py
        user.py
    routes/
        document_routes.py
    schemas/
        document_schema.py
    services/
        document_service.py
        notification_service.py
        user_service.py
    utils/
        content.py
        diff_engine.py
        similarity.py
```

### Layer Responsibilities

- `routes/`: HTTP boundary, request parsing, response serialization, dependency injection, background task orchestration
- `services/`: business rules, transactions, version sequencing, validation, soft deletion, pagination
- `models/`: normalized relational schema with indexes and constraints
- `schemas/`: request and response contracts using Pydantic
- `utils/`: reusable diff and similarity helpers
- `core/`: config, logging, and centralized exception handling

## Database Schema

### `users`

- `user_id` primary key
- `name`
- `email` unique
- `created_at`

### `documents`

- `document_id` primary key
- `title`
- `created_at`
- `updated_at`
- `created_by` foreign key to `users.user_id`
- `is_deleted`

Notes:

- document metadata is stored here
- content is intentionally not stored here

### `document_versions`

- `version_id` primary key
- `document_id` foreign key to `documents.document_id`
- `version_number`
- `content`
- `created_by` foreign key to `users.user_id`
- `created_at`
- `is_deleted`

Constraints and indexing:

- unique constraint on `(document_id, version_number)`
- index on `(document_id, created_at)`
- index on `is_deleted`

### `notifications`

- `notification_id` primary key
- `document_id` foreign key
- `version_id` foreign key
- `message`
- `similarity_score`
- `triggered`
- `created_at`
- `details`

## Versioning Design

Every content update creates a new `DocumentVersion`; existing rows are never overwritten. Version numbers are sequential per document. If new content is effectively identical after normalization, a new version is not created.

Normalization removes superficial changes such as:

- repeated whitespace
- leading and trailing spaces
- formatting-only spacing changes

This prevents duplicate or whitespace-only versions from polluting history.

An optional `base_version_number` is supported on content updates for optimistic version validation. If the caller updates against a stale version, the API returns `409 Conflict`.

## Diff Algorithm

The comparison engine is implemented in `app/utils/diff_engine.py` using Python's `difflib.SequenceMatcher`.

Behavior:

- inserted lines are reported under `added`
- deleted lines are reported under `removed`
- replaced lines are reported under `modified` with `before` and `after`

This structure is suitable for lawyer-facing UIs because it keeps the output deterministic and easy to render.

Example response:

```json
{
  "document_id": 1,
  "version_1": 1,
  "version_2": 2,
  "added": ["Clause 7 has been added."],
  "removed": ["Clause 4 has been removed."],
  "modified": [
    {
      "before": "The agreement is valid for 12 months.",
      "after": "The agreement is valid for 24 months."
    }
  ]
}
```

## Notification Logic

When a new content version is created, the system computes a normalized similarity score using `difflib.SequenceMatcher`.

- If similarity is `>= 0.95`, no notification is created.
- If similarity is `< 0.95`, a background task stores a notification record asynchronously.

This means:

- whitespace-only changes do not trigger notifications
- tiny edits usually do not trigger notifications
- meaningful content updates do trigger notifications

The API returns immediately while notification persistence runs in the background through FastAPI `BackgroundTasks`.

## API Endpoints

### Create document

`POST /documents`

```json
{
  "title": "MSA Draft",
  "content": "Clause 1: Payment within 30 days.",
  "author_name": "Asha Rao",
  "author_email": "asha@example.com"
}
```

### Update content

`PUT /documents/{id}/content`

```json
{
  "content": "Clause 1: Payment within 45 days.",
  "created_by_email": "asha@example.com",
  "base_version_number": 1
}
```

### Update title only

`PUT /documents/{id}/title`

```json
{
  "title": "MSA Draft - Updated"
}
```

### List versions

`GET /documents/{id}/versions?page=1&page_size=10`

### Compare versions

`GET /documents/{id}/compare?v1=1&v2=2`

### Delete document

`DELETE /documents/{id}`

### Delete version

`DELETE /documents/{id}/versions/{version_number}`

## Reliability and Safety

- SQLAlchemy transactions protect document creation and version creation from partial failures
- soft deletes preserve auditability
- duplicate version detection avoids unnecessary writes
- optimistic version validation reduces concurrent update conflicts
- indexes and foreign keys protect lookup performance and referential integrity
- response models and request validation improve API correctness
- centralized exception handlers keep error responses consistent

## Running the Project

### 1. Create a virtual environment

```bash
python -m venv .venv
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Start the server

```bash
uvicorn app.main:app --reload
```

### 4. Open API docs

- Swagger UI: `http://127.0.0.1:8000/docs`
- ReDoc: `http://127.0.0.1:8000/redoc`

## Running Tests

```bash
pytest
```

## User Guide

Open Swagger UI at `http://127.0.0.1:8000/docs` and test the APIs in the following order.

### 1. Create a document

Use `POST /documents`

```json
{
  "title": "Lease Agreement",
  "content": "Clause 1: Rent must be paid before the 5th of every month.\nClause 2: Security deposit is two months rent.\nClause 3: Term of lease is 12 months.",
  "author_name": "Riya Sharma",
  "author_email": "riya@example.com"
}
```

Verify:

- response code is `201`
- a `document_id` is returned
- `latest_version.version_number` is `1`

This confirms the system creates document metadata and stores the initial content as version `v1`.

### 2. Verify version history

Use `GET /documents/{document_id}/versions`

Example:

- `document_id = 4`
- `page = 1`
- `page_size = 10`

Verify:

- `total_items = 1`
- only version `1` is present

This confirms the initial version history is stored correctly.

### 3. Update only document metadata

Use `PUT /documents/{document_id}/title`

```json
{
  "title": "Lease Agreement - Mumbai Office"
}
```

Verify:

- the title is updated
- calling `GET /documents/{document_id}/versions` still shows only one version

This confirms metadata updates do not create unnecessary content versions.

### 4. Create a new content version

Use `PUT /documents/{document_id}/content`

```json
{
  "content": "Clause 1: Rent must be paid before the 10th of every month.\nClause 2: Security deposit is three months rent.\nClause 3: Term of lease is 24 months.\nClause 4: Maintenance charges will be shared equally.",
  "created_by_email": "riya@example.com",
  "base_version_number": 1
}
```

Verify:

- `version_created = true`
- returned version number is `2`

This confirms old versions are preserved and new versions are appended sequentially.

### 5. Validate stale update protection

Repeat the same content update but intentionally use an old base version:

```json
{
  "content": "Clause 1: Rent must be paid before the 10th of every month.\nClause 2: Security deposit is three months rent.\nClause 3: Term of lease is 24 months.\nClause 4: Maintenance charges will be shared equally.",
  "created_by_email": "riya@example.com",
  "base_version_number": 1
}
```

Expected:

- response code `409 Conflict`
- message indicates the latest version is `v2`

This confirms optimistic version validation is working and stale edits are rejected safely.

### 6. Validate identical-content handling

Use `PUT /documents/{document_id}/content` again with the exact same content, but with the current version:

```json
{
  "content": "Clause 1: Rent must be paid before the 10th of every month.\nClause 2: Security deposit is three months rent.\nClause 3: Term of lease is 24 months.\nClause 4: Maintenance charges will be shared equally.",
  "created_by_email": "riya@example.com",
  "base_version_number": 2
}
```

Verify:

- `version_created = false`
- response message says no new version was created

This confirms identical uploads do not create duplicate versions.

### 7. Validate whitespace-only change handling

Use `PUT /documents/{document_id}/content`

```json
{
  "content": "Clause 1: Rent must be paid before the 10th of every month. \nClause 2:   Security deposit is three months rent.\nClause 3: Term of lease is 24 months.\nClause 4: Maintenance charges will be shared equally.",
  "created_by_email": "riya@example.com",
  "base_version_number": 2
}
```

Verify:

- `version_created = false`

This confirms whitespace-only or formatting-only changes are ignored and do not pollute version history.

### 8. Compare two versions

Use `GET /documents/{document_id}/compare?v1=1&v2=2`

Verify:

- `modified` shows:
  - rent due date changed from 5th to 10th
  - security deposit changed from two months to three months
  - lease term changed from 12 months to 24 months
- `added` shows:
  - `Clause 4: Maintenance charges will be shared equally.`

This confirms the comparison output is structured and readable for a legal reviewer.

### 9. Delete a single version

Use `DELETE /documents/{document_id}/versions/{version_number}`

Example:

- `document_id = 4`
- `version_number = 1`

Verify:

- delete is successful
- version listing no longer shows version `1`

This confirms version-level soft deletion works.

### 10. Delete an entire document

Use `DELETE /documents/{document_id}`

Example:

- `document_id = 4`

Verify:

- delete is successful
- the document is no longer returned as active data

This confirms document-level soft deletion works.

## Comparison Logic Explanation

The comparison feature uses Python's `difflib.SequenceMatcher` on document content split line by line. It compares two stored versions and categorizes changes into `added`, `removed`, and `modified`.

For replaced lines, the API returns a clear `before` and `after` structure instead of a raw developer-style diff. This makes the output easier for lawyers to review because it focuses on clause-level meaning rather than low-level text noise.

## Product-Minded Engineering Notes

- content is stored only in `DocumentVersion`, preserving immutable history
- duplicate versions are prevented for identical or formatting-only changes
- metadata changes do not pollute content history
- transactions reduce risk of partial writes during failures
- stale updates are rejected using version validation
- comparison output is structured for lawyer readability, not just technical correctness

## Notes and Tradeoffs

- SQLite is used for simplicity in a take-home setting; the schema is compatible with migration to PostgreSQL
- background notifications are implemented via FastAPI tasks, but the design can be swapped to Celery, RQ, or Kafka-backed workers later
- large document handling is bounded through request validation with a configurable maximum content length

## Future Improvements

- add Alembic migrations
- add authentication and authorization
- add richer diff rendering with paragraph and clause awareness
- expose notification listing endpoints
- add automated tests and CI
