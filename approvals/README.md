# B.E.E.P. Reference Home Approval Records

This directory contains technical review and approval
records for reference homes maintained by the
B.E.E.P. Software Consistency Repository.

## Purpose

Provide traceable documentation of reference-home
reviews, approval decisions, publication authorization,
and historical changes.

## Directory Structure

Approval records will be organized by reference-home
identifier and version.

Example:

approvals/
  BEEP-HOME-001/
    1.0.0/
      technical-review.md
      approval-record.md

## Required Documentation

Before a reference-home version may be approved,
its records must include:

1. Reference-home ID and version
2. Technical reviewer identification
3. Completed technical review checklist
4. Reviewer independence disclosure
5. Review findings and recommendations
6. Approval authority and decision
7. Approval date
8. Reference-file SHA-256 checksums
9. Authorized test cycles
10. Publication authorization

## Record Identification

Each approval record must receive a unique identifier.

Example:

BEEP-APPROVAL-001

The identifier must correspond to the approval_record
field in the reference-home registry.

## Approval Requirements

A reference-home version must not be marked APPROVED
solely because an approval record file exists.

Approval requires:

- Completed technical review
- Authorized approval decision
- Successful integrity validation
- Complete approval metadata
- Authorized test cycle
- Required repository review and publication controls

## Historical Records

Approval records must be retained for historical
reference and audit purposes.

Records associated with retired reference-home
versions must not be deleted.

## Current Status

The existing BEEP-HOME-001 version 1.0.0 remains
in DEVELOPMENT status.

No production reference-home approval has been issued.

## Future Controls

Automated validation will verify that approval records
exist and correspond to the registry.

GitHub pull-request reviews and branch protection will
be used to control changes to approved reference homes.
