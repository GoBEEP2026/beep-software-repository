# B.E.E.P. Reference Home Versioning Policy

**Organization:** Building Energy Efficiency Professionals (B.E.E.P.)

**Project:** Software Consistency Repository

**Policy Status:** Proposed — Pending Board Approval

**Policy Version:** 1.0.0

**Approval Authority:** B.E.E.P. Board of Directors

## 1. Purpose

This policy establishes a consistent, transparent, and
traceable method for managing reference-home versions
within the B.E.E.P. Software Consistency Repository.

The policy supports software consistency, repeatability,
technical accuracy, program neutrality, and historical
accountability.

## 2. Versioning Format

Reference homes shall use semantic versioning:

MAJOR.MINOR.PATCH

Example: BEEP-HOME-001, Version 1.0.0

Each reference-home ID and version combination shall
be unique.

## 3. Major Version Changes

A major version change represents a material revision
to the reference home's technical characteristics,
modeling assumptions, or intended testing scope.

Examples include:

- Building geometry or conditioned floor area changes.
- Building envelope configuration changes.
- Material changes to insulation or fenestration.
- HVAC system configuration changes.
- Significant changes to modeling assumptions.
- Changes that affect comparability with previous results.

Example: 1.0.0 to 2.0.0

## 4. Minor Version Changes

A minor version change represents an expansion or
enhancement of the reference home's testing capabilities
without fundamentally changing its established design
or technical basis.

Examples include:

- Additional testing scenarios.
- Supplemental modeling inputs.
- Expanded technical documentation.
- Additional software comparison requirements.

Example: 1.0.0 to 1.1.0

## 5. Patch Version Changes

A patch version change represents a limited correction
that does not materially alter the reference home's
technical basis or intended testing scope.

Examples include:

- Typographical corrections.
- Documentation clarifications.
- Nonmaterial input corrections.
- Formatting corrections.
- Correction of inconsistent terminology.

Example: 1.0.0 to 1.0.1

Corrections that materially affect modeling results
shall not be classified as patch changes.

## 6. Version Progression

The proposed initial version of a new reference home
shall be 1.0.0.

Subsequent versions shall follow these progression rules:

- Major: X.Y.Z to (X+1).0.0
- Minor: X.Y.Z to X.(Y+1).0
- Patch: X.Y.Z to X.Y.(Z+1)

Version numbers shall not be reused or reassigned.

## 7. Approved Version Immutability

Approved and retired reference-home versions shall
remain immutable.

Technical or documentation changes to an approved
reference home shall require creation of a new version.

Previously approved reference files, metadata,
approval records, and historical results shall
be preserved.

Retirement shall not authorize modification or
deletion of historical records.

## 8. Parent-Version Traceability

Each subsequent reference-home version shall identify
the preceding version from which it was developed.

Version history shall document:

- Reference-home ID.
- New version number.
- Parent version number.
- Change classification.
- Description of changes.
- Reason for changes.
- Anticipated impact on modeling results.
- Review and approval records.

## 9. Lifecycle Requirements

Every newly registered reference-home version shall
begin in DEVELOPMENT status.

Permitted lifecycle transitions are:

- DEVELOPMENT to UNDER_REVIEW.
- UNDER_REVIEW to DEVELOPMENT.
- UNDER_REVIEW to APPROVED.
- APPROVED to RETIRED.

RETIRED is a terminal lifecycle status.

Existing lifecycle validation requirements shall
remain applicable to all reference-home versions.

## 10. Review and Approval

All new reference-home versions shall undergo
formal technical review before approval.

The B.E.E.P. Board of Directors shall retain final
approval authority.

Major, minor, and patch versions shall be subject
to the established approval process.

Automated validation, successful software testing,
or merging a GitHub pull request shall not constitute
formal Board approval.

## 11. Historical Results

Software consistency results shall be associated
with the exact reference-home ID and version used
during testing.

Results from different reference-home versions shall
not be represented as directly equivalent without
documented technical justification.

Historical testing results shall remain available
for traceability and comparison.

## 12. Automated Validation

The repository shall implement automated validation
to support:

- Semantic version format requirements.
- Unique reference-home version identifiers.
- Authorized version progression.
- Parent-version traceability.
- Required change documentation.
- Lifecycle transition enforcement.
- Approved version immutability.
- Historical reference-file integrity.

Automated validation shall supplement, but shall
not replace, technical review or Board approval.

## 13. Policy Administration

The B.E.E.P. Board of Directors shall retain authority
over adoption, interpretation, amendment, and
administration of this policy.

This document shall remain proposed until formally
adopted through the established Board approval process.

---

Building Energy Efficiency Professionals (B.E.E.P.)

"The Professionals Behind the Performance"

https://www.GoBEEP.org
