---
phase: "12-review-dashboard-ui"
plan: "12-01"
subsystem: "frontend"
tags: ["reviews", "ui", "human-in-the-loop", "dashboard"]
requires: ["11-02-hitl-review-api"]
provides: ["review-queue-ui", "needs-review-badges"]
affects: ["base.html", "session_controller", "dashboard.js", "session.js", "dashboard.css"]
tech-stack:
  added: ["reviews.js"]
  patterns: ["review queue page", "session filter", "status filter chips"]
key-files:
  created:
    - "templates/reviews.html"
    - "static/js/reviews.js"
  modified:
    - "templates/base.html"
    - "controllers/session_controller.py"
    - "static/js/dashboard.js"
    - "static/js/session.js"
    - "static/dashboard.css"
decisions: []
metrics:
  duration: "~15 min"
  completed_date: "2026-07-18"
---

# Phase 12 Plan 01: Review Dashboard & Navigation UI Summary

Human-in-the-Loop review queue page with navigation, stats, filters, and repository review badges on session cards.

## Completed Tasks

### Task 1: Reviews nav item and route
- **base.html:** Added Reviews link between Reports and Analytics in sidebar nav, plus Reviews entry in command palette search
- **session_controller.py:** Added `GET /reviews` route rendering `reviews.html`
- **Commit:** `b49a022`

### Task 2: Create templates/reviews.html
- Full review queue template extending base.html
- Stats grid with Pending, In Review, Reviewed, Total Flagged metric cards
- Toolbar with session filter dropdown (`id="sessionFilter"`) and status filter chips (All, Pending, In Review, Reviewed)
- Data table with Session, Repository, Roll Number, Score, Flag Reason, Status, Actions columns
- Action buttons per row: "Start Review" (for pending), "View" link
- Includes reviews.js script
- **Commit:** `bba9994`

### Task 3: Create static/js/reviews.js
- Full review queue page logic:
  - On DOMContentLoaded, check for `#reviewsStats` element
  - Fetch sessions list and populate session filter dropdown
  - Status filter chips toggle via click
  - `loadReviews()` function with dual mode:
    - Single session: fetch `/api/reviews/<session_id>?status=...`
    - All sessions: fetch all sessions then `Promise.all` over each session's reviews
  - Aggregate results, update stat counters
  - Render table rows with session name, linked repo name, roll, score, flag reason, status badge, action buttons
  - `startReview()` global function: POST to `/api/reviews/<sid>/<rid>/start`, toast, reload
  - Reviewed rows get class `reviewed-row` with reduced opacity
- Added CSS for review status badges (`status-in-review`, `status-reviewed`), data table, empty-table, action-cell, reviewed-row opacity, review-flag
- **Commit:** `fb50a24`

### Task 4: Update dashboard.js with pending_reviews
- Changed `pendingValue` from showing pending evaluation count (`pRem`) to showing `d.pending_reviews || 0` from the dashboard API, matching the "Pending Reviews" label in the health panel
- **Commit:** `97c75bf`

### Task 5: Add review badges to session page repo cards
- Added `reviewBadge` variable in `session.js` `card()` function using `r.needs_review` flag
- Appended `reviewBadge` to card HTML after `confidenceWarning`
- Added `.review-flag` CSS class to dashboard.css (indigo-colored warning strip matching existing pattern)
- **Commit:** `cd9b431`

## Success Criteria Verification

- [x] Navigation: Reviews tab appears between Reports and Analytics in sidebar (command palette too)
- [x] Route: `/reviews` endpoint renders reviews.html without crashing
- [x] Template: reviews.html has stats grid, toolbar, filter chips, data table, script include
- [x] JS Logic: reviews.js loads sessions, supports dual mode (single/all), filters, starts reviews, renders table
- [x] Dashboard: pendingValue shows review queue count from dashboard API
- [x] Session cards: repos with `needs_review` flag show "! Needs review" badge with indigo styling

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None — all wiring is complete. The review queue page populates from existing APIs.

## Threat Flags

None — all code operates within existing endpoint surface and auth patterns.

## Self-Check: PASSED

- [x] Created files: templates/reviews.html, static/js/reviews.js
- [x] Modified files: all 5 existing files found
- [x] All 5 commits verified in git log
