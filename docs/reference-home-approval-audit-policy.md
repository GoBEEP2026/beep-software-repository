# B.E.E.P. Reference Home Approval and Audit Governance Policy

Building Energy Efficiency Professionals (B.E.E.P.)

The Professionals Behind the Performance

---

## Document Control

| Field | Value |
|---|---|
| Document Title | Reference Home Approval and Audit Governance Policy |
| Policy Version | 1.0.0 |
| Policy Status | PROPOSED |
| Governance Authority | B.E.E.P. Board of Directors |
| Repository | BEEP Software Consistency Repository |
| Audit Registry Schema | 1.1.0 |
| Effective Date | Pending formal Board adoption |
| Approval Reference | Pending formal Board adoption |

---

## 1. Purpose

This policy establishes governance requirements for the
approval, rejection, retirement, documentation, historical
preservation, and automated validation of reference home
decisions within the B.E.E.P. Software Consistency
Repository.

The policy is intended to support:

- Technical consistency
- Independent technical review
- Transparent decision-making
- Permanent historical accountability
- Reproducible software comparison
- Program-neutral governance
- Protection against unauthorized modifications
- Confidence in reference home integrity

---

## 2. Scope

This policy applies to all reference home identifiers,
reference home versions, technical review records,
approval decisions, rejection decisions, retirement
decisions, supporting documentation, and associated
audit records maintained within the repository.

Governance requirements apply independently to each
registered reference home version.

Approval of one version does not constitute approval
of another version.

---

## 3. Governance Authority

The B.E.E.P. Board of Directors shall serve as the
final decision-making authority for reference home
approval, rejection, and retirement.

The required governance authority designation is:

B.E.E.P. Board of Directors

Technical reviewers, repository administrators,
software vendors, contributors, and automated
validation systems shall not independently exercise
Board approval authority.

Automated validation supports governance enforcement
but does not replace formal Board action.

---

## 4. Reference Home Lifecycle

The recognized reference home lifecycle statuses are:

- DEVELOPMENT
- UNDER_REVIEW
- APPROVED
- RETIRED

The authorized lifecycle transitions are:

| Previous Status | Permitted Subsequent Status |
|---|---|
| DEVELOPMENT | DEVELOPMENT |
| DEVELOPMENT | UNDER_REVIEW |
| UNDER_REVIEW | UNDER_REVIEW |
| UNDER_REVIEW | DEVELOPMENT |
| UNDER_REVIEW | APPROVED |
| APPROVED | APPROVED |
| APPROVED | RETIRED |
| RETIRED | RETIRED |

New reference home versions shall enter the repository
in DEVELOPMENT status.

RETIRED status is permanent.

Previously approved or retired reference home versions
shall not return to DEVELOPMENT or UNDER_REVIEW.

---

## 5. Recognized Audit Decisions

The recognized Board audit decisions are:

- APPROVED
- REJECTED
- RETIRED

Audit decisions document governance actions.

Audit decisions and reference home lifecycle statuses
are related but are not interchangeable.

REJECTED is an audit decision and is not a reference
home lifecycle status.

---

## 6. Approval Requirements

A reference home version may transition to APPROVED
only when:

1. The reference home version is already registered.

2. Its previously accepted lifecycle status is
   UNDER_REVIEW.

3. A completed technical review exists in previously
   accepted repository history.

4. The technical review recommendation is
   RECOMMEND_APPROVAL.

5. The technical review identifier has been permanently
   reserved.

6. Required technical review supporting documentation
   exists and has been preserved.

7. The reviewed technical content fingerprint is valid.

8. The proposed approval metadata matches the
   corresponding audit decision.

9. The B.E.E.P. Board of Directors is identified as
   the approval authority.

10. A Board resolution reference is provided.

11. The approval date does not precede technical
    review completion.

12. Exactly one newly appended APPROVED audit
    decision accompanies the lifecycle transition.

13. All applicable repository validation requirements
    are satisfied.

Technical review completion and reference home approval
shall not be introduced together as a substitute for
previously accepted technical review history.

---

## 7. Controlled Rejection

The repository shall implement controlled rejection
governance.

A REJECTED audit decision may be introduced only for
a reference home version whose previously accepted
lifecycle status is UNDER_REVIEW.

Following rejection, the reference home may:

- Remain UNDER_REVIEW; or
- Return to DEVELOPMENT.

The Board shall determine the appropriate disposition.

A rejection shall not directly transition a reference
home to APPROVED or RETIRED.

Rejection shall not erase previously accepted technical
review documentation, review identifier reservations,
or audit history.

---

## 8. Rejection With Completed Technical Review

When a previously accepted completed technical review
exists, a newly appended REJECTED audit decision shall
preserve the corresponding technical review evidence.

Required evidence includes:

- Technical review record identifier
- Technical review completion date
- Technical review document SHA-256 checksum
- Reviewed technical content SHA-256 fingerprint

The technical reviewer and associated evidence shall
correspond to the previously accepted technical review.

A rejection shall not substitute unrelated or newly
created technical review evidence.

A rejection decision shall not precede the completion
date of the technical review supporting that decision.

---

## 9. Rejection Without Completed Technical Review

When the previously accepted technical review has
not been completed, a REJECTED audit decision may
contain null technical review evidence fields.

The four technical review evidence fields shall
either be fully populated or all null.

Partial technical review evidence is prohibited.

All other required audit decision metadata shall
remain mandatory.

Null technical review evidence shall not be used
to omit a previously accepted completed review.

---

## 10. Repeated Rejection Decisions

Multiple rejection decisions may be recorded for
the same reference home version when supported by
separate Board decisions.

Each newly appended rejection shall have:

- A unique audit record identifier
- An independent Board resolution reference for
  the applicable reference home version
- Required supporting decision evidence
- A valid decision date
- Applicable historical technical review evidence

A newly appended rejection shall not reuse an
earlier Board resolution reference associated with
the same reference home version.

Board resolution comparisons for this requirement
shall be case-insensitive.

Repeated rejection shall not authorize modification
or removal of previously accepted audit records.

---

## 11. Technical Review Reset Following Rejection

When a rejected reference home returns to DEVELOPMENT,
the active technical review shall be reset in accordance
with the technical review governance policy.

Previously reserved technical review identifiers
shall remain permanently reserved.

Previously accepted technical review documents
shall remain preserved.

A subsequent technical review assignment shall
require a new technical review identifier.

Historical rejection decisions shall remain associated
with their original supporting evidence.

A later review assignment shall not overwrite the
historical evidence supporting an earlier rejection.

---

## 12. Retirement Requirements

A reference home version may transition to RETIRED
only when:

1. Its previously accepted lifecycle status is
   APPROVED.

2. Exactly one original APPROVED audit decision
   exists in previously accepted repository history.

3. The original approval metadata remains unchanged.

4. The original technical review evidence remains
   unchanged.

5. Previously approved technical content and reference
   files remain unchanged.

6. A new RETIRED audit decision is appended.

7. The retirement decision has a unique audit record
   identifier.

8. The retirement decision has an independent Board
   resolution reference distinct from the original
   approval resolution.

9. The retirement date does not precede the original
   approval date.

10. The retirement audit decision appears after the
    original approval audit decision.

11. All applicable repository validation requirements
    are satisfied.

Retirement shall not delete, replace, or invalidate
the historical existence of the original approval.

Retirement shall not modify previously approved
reference home metadata other than lifecycle status.

Approval and retirement of the same reference home
version shall not be introduced together in a single
proposed repository change.

---

## 13. Audit Registry

The official approval audit registry is:

test-homes/reference-approval-audit.json

The current audit registry schema version is:

1.1.0

The audit registry shall maintain permanent,
append-only records of Board decisions.

The registry shall not be treated as a substitute
for official Board minutes, resolutions, or other
organizational governance records.

---

## 14. Required Audit Record Fields

Each audit record under schema version 1.1.0
shall contain the following fields:

| Field | Purpose |
|---|---|
| record_id | Unique audit decision identifier |
| reference_home_id | Registered reference home identifier |
| reference_home_version | Applicable reference home version |
| decision | APPROVED, REJECTED, or RETIRED |
| reviewer | Reviewer associated with the decision |
| approval_authority | B.E.E.P. Board of Directors |
| evidence | Supporting decision evidence reference |
| pull_request | Associated pull request reference |
| board_resolution_reference | Board resolution reference |
| decision_date | Date of the Board decision |
| technical_review_record | Technical review identifier |
| technical_review_date | Technical review completion date |
| technical_review_sha256 | Technical review document checksum |
| reviewed_content_sha256 | Reviewed technical content fingerprint |

Technical review evidence fields shall comply with
the decision-specific requirements of this policy.

Audit identifiers shall be unique throughout the
audit registry using case-insensitive comparisons.

Dates shall use the YYYY-MM-DD format.

SHA-256 values shall use the required lowercase
64-character hexadecimal representation.

---

## 15. Append-Only Audit Preservation

Previously accepted audit records shall not be:

- Deleted
- Replaced
- Renumbered
- Reordered
- Reassigned
- Modified
- Silently corrected

New audit records shall be appended after existing
historical records.

Historical audit registry metadata shall remain
unchanged except through an explicitly authorized
schema migration.

Any future correction or supplemental record
mechanism shall require separately documented
governance requirements and corresponding validation.

No correction mechanism is authorized by this policy.

---

## 16. Audit Schema Migration

Audit schema changes shall be explicitly controlled.

The authorized migration from schema version 1.0.0
to schema version 1.1.0 requires:

- An empty previously accepted audit registry
- An empty proposed audit registry
- Preservation of required registry metadata
- Successful schema validation

The migration shall not introduce new audit decisions.

Schema downgrades are prohibited.

Future schema migrations shall require documented
governance authorization and corresponding validation.

---

## 17. Bidirectional Audit Consistency

Every APPROVED reference home version shall have
exactly one corresponding APPROVED audit decision.

Every RETIRED reference home version shall retain
exactly one original APPROVED audit decision and
exactly one corresponding RETIRED audit decision.

Every APPROVED audit decision shall reference an
eligible registered reference home version.

Every RETIRED audit decision shall reference a
registered reference home version in RETIRED status.

Historical rejection decisions may remain associated
with reference home versions that subsequently
undergo authorized lifecycle transitions.

Current lifecycle status shall not invalidate a
properly preserved historical rejection decision.

---

## 18. Historical Decision Authorization

Newly appended audit decisions shall be evaluated
against previously accepted repository history.

Authorized historical decision transitions are:

| Decision | Previous Status | Proposed Status |
|---|---|---|
| APPROVED | UNDER_REVIEW | APPROVED |
| REJECTED | UNDER_REVIEW | UNDER_REVIEW |
| REJECTED | UNDER_REVIEW | DEVELOPMENT |
| RETIRED | APPROVED | RETIRED |

Previously accepted registry snapshots shall be
used to distinguish historical decisions from newly
proposed decisions.

New decisions shall not rely on technical review
completion or original approval introduced only
within the same proposed repository change when
previously accepted evidence is required.

Historical validation shall supplement current
registry consistency validation.

---

## 19. Technical Evidence Preservation

Technical review evidence supporting audit decisions
shall remain permanently traceable.

Required protections include:

- Permanent technical review identifier reservations
- Preservation of historical review documentation
- Verification of document SHA-256 checksums
- Verification of reviewed content fingerprints
- Consistency between audit records and review metadata
- Consistency between review records and identifier
  reservations
- Preservation of original approval evidence
- Preservation of retirement evidence

Historical audit records shall remain associated
with their original technical review evidence even
when subsequent reviews are conducted.

---

## 20. Automated Validation

Repository validation shall include, as applicable:

- Audit registry schema validation
- Live audit schema enforcement
- Append-only audit history validation
- Technical review evidence validation
- Technical review reservation validation
- Bidirectional approval audit consistency
- Bidirectional retirement audit consistency
- Historical audit decision authorization
- Reference home lifecycle validation
- Reference home versioning validation
- Technical review chronology validation
- Historical review document preservation
- Technical review assignment authorization
- Technical review document creation authorization

Applicable validation failures shall prevent
successful completion of the required repository
validation workflow.

Historical authorization checks require access
to an appropriate trusted historical repository
snapshot.

---

## 21. Regression Testing

The repository shall maintain automated regression
tests covering governance and technical integrity
requirements.

The development verification baseline at the time
of this proposed policy is:

| Verification Category | Baseline |
|---|---|
| Required unit test suites | 29 |
| Required unit tests | 954 |
| Technical review document demonstration checks | 6 |
| Historical audit demonstration checks | 9 |
| Combined controlled demonstration checks | 15 |

These quantities document the current development
baseline and may increase as additional validation
requirements are implemented.

Required test counts shall not be reduced merely
to obtain successful validation results.

Changes to the testing baseline shall be documented
and reviewed.

---

## 22. Controlled Failure Demonstrations

The repository shall maintain controlled failure
demonstrations that verify rejection of unauthorized
governance actions.

Historical audit demonstrations shall include:

- Acceptance of valid historical approval
- Rejection of unauthorized approval
- Successful approval recovery
- Acceptance of valid controlled rejection
- Rejection of unauthorized controlled rejection
- Successful rejection recovery
- Acceptance of valid historical retirement
- Rejection of unauthorized retirement
- Successful retirement recovery

Demonstrations shall use isolated fictional data
and shall not introduce actual Board decisions
into the live audit registry.

---

## 23. Supporting Governance Records

Board decisions shall be supported by appropriate
organizational governance records.

Supporting records may include:

- Board meeting minutes
- Written resolutions
- Technical review recommendations
- Decision supporting documentation
- Conflict-of-interest disclosures
- Associated repository pull requests

Repository records shall provide sufficient
references to support traceability.

Confidential or personally sensitive information
shall not be unnecessarily published within the
repository.

---

## 24. Validation Limitations

Automated validation establishes structural,
technical, and historical consistency.

Automated validation does not independently establish:

- Authenticity of Board resolutions
- Authenticity of reviewer identities
- Actual Board voting outcomes
- Accuracy of asserted decision dates
- Completeness of organizational meeting records
- Technical correctness of every reviewer conclusion
- Independence of every participating reviewer
- Authenticity of asserted pull request references

Repository access controls, trusted historical
snapshots, appropriate review procedures, and
organizational governance remain necessary.

Successful automated validation does not constitute
formal Board approval.

---

## 25. Policy Administration

The B.E.E.P. Board of Directors shall retain
authority over adoption, interpretation, amendment,
and administration of this policy.

Repository administrators shall implement approved
governance requirements through documented
repository procedures and automated validation.

Proposed policy changes shall be reviewed for
technical consistency, historical preservation,
and governance implications.

---

## 26. Policy Adoption

This policy is designated PROPOSED.

Formal adoption requires action by the B.E.E.P.
Board of Directors.

Following adoption, the document control information
shall be updated to reflect the approved policy
status, effective date, and applicable Board
resolution reference.

Repository development and testing shall not be
interpreted as formal adoption.

---

## 27. Revision History

| Version | Status | Description |
|---|---|---|
| 1.0.0 | PROPOSED | Initial approval audit governance policy covering approval, controlled rejection, retirement, append-only preservation, historical authorization, technical evidence protection, and automated validation. |

---

Building Energy Efficiency Professionals (B.E.E.P.)

The Professionals Behind the Performance

https://www.GoBEEP.org
