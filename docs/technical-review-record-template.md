# B.E.E.P. Technical Review Record

Building Energy Efficiency Professionals (B.E.E.P.)

The Professionals Behind the Performance

## Template Administration

Template Version: 1.0.0

Template Status: PROPOSED

Governing Authority: B.E.E.P. Board of Directors

This template establishes the proposed documentation
requirements for technical reviews of reference-home
versions maintained within the B.E.E.P. Software
Consistency Repository.

This template does not constitute a completed technical
review or authorization for approval.

---

## 1. Reference Home Identification

Reference Home ID: [REQUIRED]

Reference Home Version: [REQUIRED]

Technical Review Record ID: [REQUIRED]

Technical Reviewer: [REQUIRED]

Technical Review Date: [YYYY-MM-DD]

Technical Review Status: COMPLETED

## 2. Review Scope

Review Scope: [REQUIRED]

The technical reviewer shall evaluate applicable
components of the reference-home definition, including:

- Building geometry and dimensions
- Conditioned floor area
- Conditioned building volume
- Building orientation
- Building thermal envelope
- Fenestration characteristics
- Mechanical systems
- Domestic water heating systems
- Air infiltration assumptions
- Mechanical ventilation assumptions
- Duct systems and duct leakage assumptions
- Internal loads and occupancy assumptions
- Applicable energy modeling assumptions
- Applicable compliance pathways
- Reference-file integrity
- Version classification
- Change documentation
- Modeling reproducibility

Items that are not applicable shall be identified
and explained in the supporting review narrative.

## 3. Technical Review Findings

Review Findings: [REQUIRED]

### Detailed Findings

Document the technical findings, identified
discrepancies, limitations, assumptions, and any
required corrective actions.

### Required Corrections

Identify any corrections required before the
reference-home version may be recommended
for approval.

## 4. Technical Review Recommendation

Review Recommendation: [REQUIRED]

Permitted recommendation values:

- RECOMMEND_APPROVAL
- REVISIONS_REQUIRED

A recommendation for approval does not constitute
final approval by the B.E.E.P. Board of Directors.

A recommendation of REVISIONS_REQUIRED requires
the reference-home version to return to DEVELOPMENT
before undergoing a subsequent technical review.

## 5. Conflict-of-Interest Disclosure

Conflict-of-Interest Disclosure: [REQUIRED]

The technical reviewer shall disclose applicable
actual, potential, or perceived conflicts of interest.

Reviewer eligibility and conflict-of-interest
determinations remain subject to applicable
B.E.E.P. governance requirements.

Confidential or sensitive personal information
shall not be included in public repository records.

## 6. Technical Content Verification

Reviewed Content SHA-256: [REQUIRED]

The SHA-256 fingerprint shall correspond to the
technical content of the exact reference-home
version reviewed.

The fingerprint shall match the value recorded
in the reference-home registry.

A change to reviewed technical content requires
a new technical review in accordance with the
applicable lifecycle and versioning requirements.

## 7. Supporting Evidence

Supporting Evidence: [REQUIRED]

Identify the applicable supporting documentation,
calculations, reference files, technical standards,
and other evidence used during the review.

Where supporting documents are maintained within
the repository, provide their repository-relative
locations.

## 8. Reviewer Attestation

By completing this technical review record,
the reviewer attests that:

- The identified reference-home version was reviewed.
- The review findings accurately represent the review.
- Applicable conflicts of interest were disclosed.
- The recommendation reflects the technical findings.
- The reviewed content fingerprint identifies the
  technical content evaluated.
- Applicable limitations have been documented.

## 9. Board Approval Authority

Final approval authority remains with the
B.E.E.P. Board of Directors.

Technical review completion and a recommendation
for approval do not independently authorize a
reference-home version for official software
consistency testing.

## 10. Record Preservation

Completed technical review records shall be
preserved as historical documentation.

Each subsequent technical review shall receive
a new technical review record identifier.

Previously completed technical review records
shall not be overwritten or deleted.

Corrections shall be documented through an
authorized supplemental record.

---

## Record Storage Requirements

Completed records shall be stored using the
following repository directory structure:

approvals/REFERENCE-HOME-ID/VERSION/technical-reviews/REVIEW-RECORD-ID.md

The filename shall match the technical review
record identifier recorded in the reference-home
registry.

The reference-home identifier and version shall
match the corresponding registry entry.

## Automated Validation Requirements

The completed technical review record shall
contain exactly one occurrence of each required
metadata field.

Required metadata fields shall be written on
individual lines using the following format:

Field Name: Field Value

Required metadata values shall not contain
line breaks.

Additional explanations shall be provided
within the applicable narrative sections.

Registry-matched metadata values shall match
the corresponding registry values exactly.

Placeholder values shall not be accepted in
completed technical review records.

Automated validation establishes document
existence and consistency. It does not
independently authenticate the reviewer,
review findings, supporting evidence, or
Board authorization.

---

Document Authority: B.E.E.P. Board of Directors

Effective Date: Pending formal Board adoption
