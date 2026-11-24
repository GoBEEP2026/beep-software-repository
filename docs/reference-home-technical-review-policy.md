# B.E.E.P. Reference Home Technical Review and Approval Policy

## Document Control

- Policy Version: 1.0.0
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
- Supporting technical review records.
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

## 7. Required Technical Review Documentation

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

## 8. Technical Review Recommendations

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

## 9. Reviewed Technical Content Integrity

The technical content evaluated during review shall be
identified using a reproducible SHA-256 fingerprint.

The fingerprint shall include the reference-home
identity, version, technical metadata, reference-file
inventory, registered file checksums, and applicable
change documentation.

Administrative review and approval fields shall be
excluded from the technical content fingerprint.

The technical content submitted for Board approval
shall match the content evaluated during the completed
technical review.

Changes to reviewed technical content shall invalidate
the existing review recommendation and require
additional technical review.

## 10. Formal Approval Prerequisites

Before a reference-home version may receive APPROVED
status, the following requirements shall be satisfied:

1. Valid reference-home identity and version.
2. Valid reference-file inventory and SHA-256 checksums.
3. Successful applicable automated validation checks.
4. Complete version change documentation.
5. Completed technical review.
6. Recommendation of RECOMMEND_APPROVAL.
7. Matching reviewed technical content fingerprint.
8. Documented reviewer conflict-of-interest disclosure.
9. Assigned test cycles.
10. Formal B.E.E.P. Board authorization.
11. Valid Board resolution reference.
12. Supporting approval documentation.
13. Matching approval audit record.

The Board approval date shall not precede the
technical review completion date.

## 11. Supporting Records

Technical review and approval records shall be maintained
within version-specific repository locations.

Supporting records shall provide sufficient information
to identify the reference home, version, reviewer,
technical findings, review recommendation, and formal
Board decision.

Confidential or sensitive information shall not be
published within the public repository.

## 12. Historical Record Protection

Approved and retired reference-home versions shall
retain their technical review and approval documentation.

Previously recorded approval audit decisions shall not
be modified, removed, or reordered.

Corrections to historical audit information shall be
documented through additional traceable records under
an authorized correction procedure.

Approved technical content and supporting records
shall be protected against unauthorized modification.

Technical changes to an approved reference home shall
require a new reference-home version.

## 13. Automated Validation Limitations

Automated validation supports verification of:

- Required documentation.
- Data consistency.
- Reference-file integrity.
- Version relationships.
- Lifecycle transitions.
- Review and approval prerequisites.
- Historical record preservation.

Automated validation does not independently establish:

- Technical accuracy of all modeling assumptions.
- Reviewer qualifications.
- Reviewer independence.
- Authenticity of human review decisions.
- Authenticity of Board resolutions.
- Actual Board authorization.

Human technical review and formal Board authorization
remain necessary.

## 14. Policy Administration

The B.E.E.P. Board of Directors shall retain authority
over adoption, interpretation, amendment, and
administration of this policy.

Implementation requirements, validation procedures,
and supporting documentation shall remain consistent
with the adopted policy.

## 15. Adoption Status

This document is a proposed policy prepared for
repository development and Board consideration.

Publication within the repository does not constitute
formal adoption by the B.E.E.P. Board of Directors.
