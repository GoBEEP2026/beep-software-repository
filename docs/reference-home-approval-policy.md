# B.E.E.P. Reference Home Approval Policy

Status: DRAFT
Policy Version: 1.0.0

## Purpose

Establish a consistent, documented, and impartial
approval process for reference homes used in the
B.E.E.P. Software Consistency Repository.

## Reference Home Status

### DEVELOPMENT

The reference home is being created or modified.

- Modeling inputs may change.
- Test results are not considered official.
- The home is not available for production cycles.

### UNDER_REVIEW

The reference home has been submitted for
independent technical review.

Requirements:

- Complete reference-home documentation
- Valid reference-file checksums
- Documented modeling assumptions
- Technical review checklist
- Identified reviewer

No changes may be made during review without
returning the home to DEVELOPMENT or restarting
the review process.

### APPROVED

The reference home has completed technical review
and received authorization for publication.

Requirements:

- Successful integrity validation
- Completed technical review
- Recorded approval authority
- Approval date
- Approval record
- Assigned test cycle

Approved reference-home files must be preserved
without modification.

Any change affecting modeling inputs requires
a new reference-home version.

### RETIRED

The reference-home version is no longer available
for new testing cycles.

- Historical submissions remain accessible.
- Previous comparison results are preserved.
- Existing audit records remain available.
- The version must not be deleted.

## Approval Authority

B.E.E.P. will designate authorized technical
reviewers and approval authorities.

The person approving a reference home should
not be the sole person responsible for preparing
or reviewing it.

Reviewer independence and conflicts of interest
must be documented.

## Approval Record

Each approved reference-home version must have:

- Reference home ID
- Reference home version
- Reviewer identity
- Approval authority
- Approval date
- Reference file checksums
- Approval decision
- Supporting review documentation
- Authorized test cycle

## Publication Controls

Only APPROVED reference-home versions may be
published for production vendor submissions.

Published reference-home versions must be
preserved with their original files and hashes.

Approval metadata must be validated before
production submissions are accepted.

## Changes After Approval

Approved reference-home files must not be
overwritten.

Changes to modeling inputs require a new version.

Administrative corrections must be documented
and must not alter modeled inputs.

## Audit Requirements

All approval and retirement actions must be
traceable through retained records.

GitHub commit history alone is not sufficient
as the complete approval record.

## Current Implementation

This policy describes the intended production
approval process.

Automated enforcement and authorized approval
roles will be implemented in later development
steps.

The existing sample reference home remains
classified as DEVELOPMENT.
