# Tool cache

## Goal of the document

This document describes disposable cache storage, coordinated access, and cleanup at the library caller boundary.

## Scope

This specification applies to shared filesystem cache operations.
Application-specific payload validity, refresh policy, and command selection are out of scope.
Protection of subprocesses that outlive the process holding cache access is out of scope.

## Cache entries

Cache-root selection MUST follow Cache roots under Tool storage locations in `specs/behavior/paths.md`.
Supplying cache settings MUST NOT itself create storage or acquire exclusive access.
An existing root accessed for cached data MUST be a directory.
Missing directories MUST be created only when an operation needs to store cache data.
Entry acquisition MUST return a location satisfying Filesystem containment in `specs/behavior/paths.md`, using the selected cache root as the supplied root.

Existing data MUST be verified as cache-owned and associated with the requested identity before reuse or replacement.
A directory MUST NOT become disposable merely because it resides under the cache root or resembles a cache entry.
A conflict with unrelated content at a required entry location MUST fail without overwriting or deleting that content.
Data belonging to one identity MUST NOT satisfy a request for another.
Repeated acquisition of the same identity in the same cache MUST reuse its owned entry without replacing its contents.

Failed preparation MAY leave partial data.
Entry acquisition MUST establish storage ownership without claiming that caller-provided payloads are complete or valid.
Callers MUST establish payload validity before using cached content.

## Exclusive access

All operations using the same effective cache root MUST coordinate exclusive access across its entries.
Different effective cache roots MUST have independent coordination.
Entry acquisition MUST obtain exclusive access before inspecting or changing cached data and retain it throughout the caller's protected use.
Callers MUST retain protected access for the full lifetime of their use of cached data, including subprocess access while the holding process remains running.

Acquisition MUST honor the caller-supplied wait timeout and proceed if access becomes available within that period.
Expiration MUST fail with a diagnostic identifying the effective root and acquisition timeout.
Waiting for or failing to obtain exclusive access MUST NOT modify cached payloads.
Other acquisition failures MUST retain the applicable filesystem diagnostic information.

Normal completion, failure, or process termination MUST release exclusive access once protected use has ended, without requiring removal of stale coordination files.
Retained coordination data MUST NOT by itself indicate that the cache is in use.

**Example:** While one process uses an entry, another process cannot acquire a different entry under the same root.
Cleanup also waits for protected use to end, but retained coordination files alone do not block it.

## Cleanup

Cleanup MUST operate locally without network access or application-specific payload processing.
It MUST remove all verified disposable entries in the selected cache, across their identities, while preserving unrelated content.
Content whose ownership cannot be verified MUST remain untouched.
Cleanup MUST NOT follow symlinks within cached data to delete their targets.

If the root is absent, cleanup MUST succeed without creating the root or coordination data and indicate that no entries were removed.
For an existing root, cleanup MUST follow Exclusive access above before inspecting disposable data and retain that access until deletion ends.
Other processes using that root MUST NOT begin protected access to data being deleted.
Successful cleanup MUST indicate whether owned entries were removed; finding none MUST succeed without reporting a removal.

Cleanup MUST preserve an existing cache root and the coordination needed by concurrent or later operations.
Coordination metadata MAY remain, but owned disposable entries MUST be removed on success.
Inspection or deletion failures MUST fail explicitly without reporting successful complete cleanup or selecting another root.
If deletion fails after removing some data, diagnostics MUST identify the possibility of partial cleanup rather than imply rollback.
Remaining owned data MUST remain eligible for a later cleanup attempt.

**Example:** Cleanup of a root containing owned entries and an unrelated notes file removes the entries and preserves the notes.
Repeating cleanup reports no removal and keeps the root available for later use.

## Failures

Cache diagnostics MUST identify the effective root when it can be resolved and the affected entry or filesystem path when applicable.
Diagnostics MUST distinguish:

- an unavailable location.
- unsafe or conflicting cached data.
- an acquisition timeout.
- a deletion failure that may have left partial cleanup.

Filesystem diagnostics MUST retain their path and failure information.
Failures at a selected location MUST NOT silently select another cache root.
