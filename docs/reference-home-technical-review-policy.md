# B.E.E.P. Reference Home Technical Review and Approval Policy

## Document Control

- Policy Version: 1.1.0
- Policy Status: PROPOSED
- Approval Authority: B.E.E.P. Board of Directors
- Effective Date: Pending formal Board adoption
- Applicability: All reference-home versions

## 1. Purpose

The purpose of this policy is to establish a consistent,
transparent, technically defensible, and software-vendor-
independent process for reviewing and approving reference
homes maintained within the B.E.E.P. Software Consistency
Repository.

Technical review shall support the accuracy, reproducibility,
consistency, and traceability of reference-home information
used for software evaluation and comparison.

## 2. Scope

This policy applies to:

- Initial reference-home versions.
- Major version revisions.
- Minor version revisions.
- Patch version revisions.
- Technical reference files.
- Reference-home metadata.
- Modeling assumptions.
- Change documentation.
- Technical review assignments.
- Permanent technical review identifier reservations.
- Supporting technical review records.
- Historical technical review records.
- Formal approval documentation.

All new reference-home versions shall undergo technical
review and formal approval before receiving APPROVED status.

## 3. Approval Authority

The B.E.E.P. Board of Directors retains final authority
for approving reference-home versions.

Technical reviewers may evaluate reference homes and
recommend approval or revisions.

Technical review recommendations do not constitute
formal Board approval.

Software vendors, developers, contributors, and technical
reviewers shall not independently grant APPROVED status.

## 4. Technical Reviewer Responsibilities

Technical reviewers shall evaluate, as applicable:

- Building geometry and dimensions.
- Conditioned floor area.
- Conditioned building volume.
- Building envelope characteristics.
- Insulation and fenestration specifications.
- Mechanical equipment characteristics.
- Air infiltration assumptions.
- Mechanical ventilation assumptions.
- Duct system characteristics.
- Energy modeling inputs and assumptions.
- Applicable energy code compliance pathways.
- Reference-file completeness and consistency.
- Semantic version classifications.
- Change descriptions and anticipated impacts.
- Software comparison applicability.
- Reproducibility of documented technical inputs.

Reviewers shall document identified discrepancies,
limitations, assumptions, and required corrections.

## 5. Reviewer Independence

Technical reviewers shall disclose actual, potential,
or perceived conflicts of interest.

Reviewers should possess technical qualifications and
experience appropriate to the reference home being reviewed.

A contributor shall not serve as the sole independent
reviewer of their own technical work.

The B.E.E.P. Board of Directors shall establish reviewer
eligibility and determine appropriate conflict-of-interest
management procedures.

## 6. Technical Review Status

Technical review status shall be maintained separately
from reference-home lifecycle status.

Permitted technical review statuses are:

- NOT_STARTED
- IN_PROGRESS
- COMPLETED

Reference homes in DEVELOPMENT shall have a technical
review status of NOT_STARTED.

Reference homes in UNDER_REVIEW may have a technical
review status of IN_PROGRESS or COMPLETED.

Reference homes in APPROVED or RETIRED status shall
retain completed technical review documentation.

Permitted technical review status transitions are:

- NOT_STARTED to NOT_STARTED.
- NOT_STARTED to IN_PROGRESS.
- IN_PROGRESS to IN_PROGRESS.
- IN_PROGRESS to COMPLETED.
- IN_PROGRESS to NOT_STARTED.
- COMPLETED to COMPLETED.
- COMPLETED to NOT_STARTED.

A reset to NOT_STARTED shall require the reference-home
version to return from UNDER_REVIEW to DEVELOPMENT.

Approved and retired reference-home versions shall not
have their completed technical reviews reset.

A technical review shall not transition directly from
NOT_STARTED to COMPLETED.

New reference-home versions shall initially enter the
repository in DEVELOPMENT status.

## 7. Technical Review Assignment

Each technical review assignment shall be associated
with one specific reference-home version and one
identified technical reviewer.

A technical review assignment shall include:

- Reference-home identifier.
- Reference-home version.
- Technical review record identifier.
- Assigned technical reviewer.
- Assignment date.
- Conflict-of-interest disclosure.

A new technical review assignment shall require a new
permanent technical review identifier reservation.

The technical review assignment and corresponding
identifier reservation shall be introduced together.

An existing technical review identifier shall not be
reassigned to another reviewer, reference home, or
reference-home version.

When a reviewer must be replaced, the existing review
shall be reset through the permitted lifecycle process.

A subsequent review assignment shall require a new
technical review record identifier.

## 8. Permanent Technical Review Identifier Reservations

### 8.1 Reservation Scope

Technical review record identifiers shall be unique
throughout the entire repository.

Identifier uniqueness shall apply across:

- All reference homes.
- All reference-home versions.
- All technical reviewers.
- All completed reviews.
- All incomplete reviews.
- All abandoned reviews.
- All historical review assignments.

Identifier uniqueness shall be evaluated without regard
to capitalization.

The exact capitalization of a reserved identifier shall
be retained in associated registry entries and supporting
technical review records.

### 8.2 Reservation Trigger

A technical review record identifier shall be reserved
when a new technical review assignment is accepted
into the authoritative repository history.

A reservation shall not depend on successful completion
of the technical review.

A proposed assignment that has not been accepted into
the authoritative repository history does not establish
a permanent reservation under this policy.

### 8.3 Reservation Duration

Accepted technical review identifier reservations
shall be permanent.

A reserved identifier shall not be:

- Reused.
- Reassigned.
- Renamed.
- Replaced.
- Deleted.
- Released for future use.

These restrictions shall remain applicable regardless
of the outcome of the associated technical review.

### 8.4 Reservation Registry

Permanent technical review identifier reservations
shall be maintained in:

test-homes/reference-review-identifier-registry.json

Each reservation shall contain:

- review_record_id
- reference_home_id
- reference_home_version
- assigned_reviewer
- assignment_date

Each reservation shall reference a registered
reference-home version.

The reservation registry shall remain append-only.

New reservations shall be appended without modifying,
removing, replacing, or reordering existing reservations.

Each newly appended reservation shall correspond to
a legitimate new technical review assignment.

Reservations shall not be created solely to hold
identifiers for unspecified future reviews.

Historical reservation records shall remain immutable.

## 9. Abandoned Technical Reviews

A technical review may be abandoned or reset before
completion through the permitted reference-home
lifecycle transition process.

A completed review may also be superseded by a new
review when revisions are required.

Abandonment describes the historical disposition of a
review assignment and does not establish an additional
technical review status.

When a review is reset:

- The reference-home version shall return to DEVELOPMENT.
- The active technical review status shall become NOT_STARTED.
- The previous identifier reservation shall remain permanent.
- The previous identifier shall not be reassigned.
- Previously accepted supporting documents shall be retained.
- A subsequent assignment shall receive a new identifier.

An abandoned review identifier shall not be used to
authorize a new technical review supporting document.

An incomplete abandoned review is not required to have
a completed technical review supporting document.

## 10. Required Technical Review Documentation

A completed technical review shall include:

- Reference-home identification.
- Reference-home version.
- Reviewer identification.
- Technical review record identifier.
- Technical review completion date.
- Technical review findings.
- Technical review recommendation.
- Conflict-of-interest disclosure.
- Reviewed technical content SHA-256 fingerprint.
- Supporting technical review documentation.

Technical review documentation shall be associated
with the exact reference-home version reviewed.

The technical review completion date shall not precede
the corresponding identifier reservation assignment date.

## 11. Technical Review Recommendations

Permitted completed review recommendations are:

- RECOMMEND_APPROVAL
- REVISIONS_REQUIRED

A recommendation of RECOMMEND_APPROVAL indicates that
the reviewer considers the reference-home version
suitable for consideration by the Board.

A recommendation of REVISIONS_REQUIRED indicates that
additional technical work is necessary.

Reference-home versions requiring revisions shall
return to DEVELOPMENT before resubmission for review.

A new review shall be required when reviewed technical
content is modified.

The new review shall receive a new technical review
record identifier and permanent reservation.

## 12. Reviewed Technical Content Integrity

The technical content evaluated during review shall be
identified using a reproducible SHA-256 fingerprint.

The fingerprint shall include the reference-home
identity, version, technical metadata, reference-file
inventory, registered file checksums, and applicable
change documentation.

The following administrative fields shall be excluded
from the technical content fingerprint:

- status
- review
- approval
- test_cycles

The technical content submitted for Board approval
shall match the content evaluated during the completed
technical review.

Changes to reviewed technical content shall invalidate
the existing review recommendation and require
additional technical review.

A completed technical review shall not be modified
while remaining in COMPLETED status.

Technical changes requiring additional review shall
follow the permitted review reset and reassignment
process.

## 13. Technical Review Supporting Documents

### 13.1 Required Document Location

Technical review supporting documents shall be maintained
within the following version-specific repository structure:

    approvals/
      <reference-home-id>/
        <reference-home-version>/
          technical-reviews/
            <technical-review-record-id>.md

The document filename shall match the exact permanently
reserved technical review record identifier.

Each technical review identifier shall correspond to
no more than one supporting technical review document.

### 13.2 Required Document Metadata

Completed technical review supporting documents
shall include the following metadata fields:

- Reference Home ID
- Reference Home Version
- Technical Review Record ID
- Technical Reviewer
- Technical Review Date
- Technical Review Status
- Review Findings
- Review Recommendation
- Conflict-of-Interest Disclosure
- Reviewed Content SHA-256
- Review Scope
- Supporting Evidence

Required metadata shall be complete and shall not
contain unresolved placeholder values.

Technical review supporting documents shall identify
the review status as COMPLETED.

Document metadata shall match the corresponding
reference-home review information and permanent
identifier reservation, as applicable.

The document completion date shall not precede the
identifier reservation assignment date.

### 13.3 Document Creation Authorization

A new technical review supporting document shall
be authorized only through a legitimate transition
from IN_PROGRESS to COMPLETED.

The previous accepted repository state shall contain
the corresponding IN_PROGRESS technical review.

The assigned reviewer and technical review record
identifier shall remain unchanged during completion.

The completed review and its supporting document
shall be introduced together.

A supporting document shall not be created for:

- An unassigned technical review identifier.
- An identifier without a permanent reservation.
- A review that has not entered IN_PROGRESS status.
- An incomplete technical review.
- An abandoned technical review identifier.
- An unrelated reference-home version.
- A different assigned technical reviewer.

Previously accepted supporting documents shall not
be reused to authorize a new review completion.

Retroactive creation of a supporting document for
an already completed historical review shall not
be permitted through the ordinary review process.

### 13.4 Document Preservation

Once accepted into the authoritative repository
history, a technical review supporting document
shall be permanently preserved.

Historical supporting documents shall not be:

- Modified.
- Replaced.
- Deleted.
- Renamed.
- Relocated.
- Reused for another technical review.

These protections shall apply even when the
associated reference-home version returns to
DEVELOPMENT or receives a subsequent technical review.

Historical supporting documents shall retain their
original file content and version-specific location.

## 14. Formal Approval Prerequisites

Before a reference-home version may receive APPROVED
status, the following requirements shall be satisfied:

1. Valid reference-home identity and version.
2. Valid reference-file inventory and SHA-256 checksums.
3. Successful applicable automated validation checks.
4. Complete version change documentation.
5. Valid permanent technical review identifier reservation.
6. Consistent technical review assignment information.
7. Completed technical review.
8. Recommendation of RECOMMEND_APPROVAL.
9. Matching reviewed technical content fingerprint.
10. Documented reviewer conflict-of-interest disclosure.
11. Valid and authorized supporting technical review document.
12. Assigned test cycles.
13. Formal B.E.E.P. Board authorization.
14. Valid Board resolution reference.
15. Supporting approval documentation.
16. Matching approval audit record.

The completed technical review shall exist in the
accepted UNDER_REVIEW repository state before the
reference-home version transitions to APPROVED.

The Board approval date shall not precede the
technical review completion date.

The technical review completion date shall not precede
the technical review identifier assignment date.

Technical review and Board approval shall remain
separate governance decisions.

## 15. Supporting Records

Technical review and approval records shall be maintained
within version-specific repository locations.

Supporting records shall provide sufficient information
to identify the reference home, version, reviewer,
technical findings, review recommendation, and formal
Board decision.

Confidential or sensitive information shall not be
published within the public repository.

## 16. Historical Record Protection

Approved and retired reference-home versions shall
retain their technical review and approval documentation.

Previously recorded approval audit decisions shall not
be modified, removed, or reordered.

Previously accepted technical review identifier
reservations shall not be modified, removed, or reordered.

Previously accepted technical review supporting
documents shall not be modified, removed, or relocated.

Historical protections shall apply to completed,
superseded, and abandoned technical review assignments,
as applicable to the records created for those assignments.

Corrections to historical audit information shall be
documented through additional traceable records under
an authorized correction procedure.

Corrections shall not overwrite original historical
technical review records or identifier reservations.

Any supplemental correction procedure shall require
appropriate governance authorization and supporting
implementation controls.

Approved technical content and supporting records
shall be protected against unauthorized modification.

Technical changes to an approved reference home shall
require a new reference-home version.

## 17. Automated Validation and Enforcement

### 17.1 Current Repository Validation

Automated validation shall evaluate, as applicable:

- Reference-home identity and version integrity.
- Reference-file checksums.
- Technical review status consistency.
- Technical review fingerprint consistency.
- Identifier reservation registry structure.
- Repository-wide identifier uniqueness.
- Case-insensitive identifier uniqueness.
- Cross-registry review assignment consistency.
- Supporting document metadata.
- Supporting document location.
- Supporting document reservation matching.
- Review assignment and completion chronology.
- Review and Board approval chronology.

### 17.2 Historical Repository Validation

Historical validation shall compare proposed changes
against the applicable accepted repository baseline.

Historical validation shall evaluate, as applicable:

- Reference-home lifecycle transitions.
- Historical version preservation.
- Permitted technical review status transitions.
- Append-only identifier reservation history.
- Permanent identifier reservation preservation.
- Historical review assignment consistency.
- Unauthorized identifier reuse.
- Unauthorized reviewer reassignment.
- Historical supporting document preservation.
- New supporting document creation authorization.
- Historical approval audit preservation.

Historical validation shall be performed before
proposed changes are accepted into the authoritative
repository history.

### 17.3 Required Automated Testing

Repository validation controls shall be supported
by automated unit tests and regression tests.

Required test suites shall verify both acceptable
and prohibited repository conditions.

Controlled failure demonstrations may be used to
verify that prohibited repository changes produce
the expected rejection messages and failure exit codes.

Controlled failure demonstrations shall use isolated
test fixtures and shall not modify actual reference-home
registries, identifier reservations, or approval records.

Required validation failures shall prevent acceptance
of proposed repository changes through the applicable
repository governance and enforcement controls.

## 18. Automated Validation Limitations

Automated validation supports verification of:

- Required documentation.
- Data consistency.
- Reference-file integrity.
- Version relationships.
- Lifecycle transitions.
- Review and approval prerequisites.
- Permanent identifier reservation consistency.
- Historical record preservation.
- Supporting document creation authorization.

Automated validation does not independently establish:

- Technical accuracy of all modeling assumptions.
- Reviewer qualifications.
- Reviewer independence.
- Authenticity of human review decisions.
- Accuracy of reviewer findings.
- Accuracy of declared assignment or completion dates.
- Authenticity of supporting evidence.
- Authenticity of Board resolutions.
- Actual Board authorization.

Successful automated validation does not constitute
technical review, professional certification, or
formal Board approval.

Human technical review and formal Board authorization
remain necessary.

Repository administrators shall maintain appropriate
access controls, required validation checks, and
historical protection mechanisms.

Automated historical validation depends on an
appropriate and trustworthy accepted repository baseline.

## 19. Policy Administration

The B.E.E.P. Board of Directors shall retain authority
over adoption, interpretation, amendment, and
administration of this policy.

Implementation requirements, validation procedures,
and supporting documentation shall remain consistent
with the adopted policy.

Changes to the permanent identifier reservation policy
shall require formal governance consideration and
appropriate implementation controls.

Policy amendments shall not be used to retroactively
authorize identifier reuse, unauthorized historical
record modification, or undocumented approval decisions.

## 20. Adoption Status

This document is a proposed policy prepared for
repository development and Board consideration.

Publication within the repository does not constitute
formal adoption by the B.E.E.P. Board of Directors.

## 21. Policy Revision History

| Version | Status | Description |
| --- | --- | --- |
| 1.0.0 | PROPOSED | Initial technical review and approval governance policy. |
| 1.1.0 | PROPOSED | Expanded technical review assignment requirements, permanent identifier reservations, abandoned review protections, supporting document authorization, historical record preservation, and automated validation requirements. |
