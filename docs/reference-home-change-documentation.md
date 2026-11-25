# B.E.E.P. Reference Home Change Documentation Requirements

## Document Control

- Document Version: 1.0.0
- Status: PROPOSED
- Approval Authority: B.E.E.P. Board of Directors
- Effective Date: Pending Board Approval

## 1. Purpose

The purpose of this document is to establish consistent
documentation requirements for changes to reference homes
maintained within the B.E.E.P. Software Consistency Repository.

These requirements support transparency, reproducibility,
technical consistency, historical traceability, and informed
review of energy modeling software results.

## 2. Scope

These requirements apply to all newly registered reference-home
versions, including residential, commercial, and institutional
reference buildings developed under the repository.

All reference-home versions shall be documented independently
of any specific software vendor, certification program,
rating provider, or compliance organization.

## 3. Required Change Documentation

Each newly registered reference-home version shall include:

- Version identifier
- Parent-version identifier
- Change classification
- Description of the change
- Reason for the change
- Anticipated impact on modeling results
- Affected building components or data categories
- Date the change was recorded

The initial reference-home version shall have no parent version
and shall use the INITIAL change classification.

Subsequent versions shall use the MAJOR, MINOR, or PATCH
classification consistent with the semantic version increment.

## 4. Change Classification

### 4.1 INITIAL

The initial establishment of a reference home.

The initial version shall be identified as 1.0.0.

### 4.2 MAJOR

A material technical change that is expected to affect energy
modeling assumptions, calculations, or results.

Examples include changes to:

- Building geometry
- Conditioned floor area
- Conditioned building volume
- Thermal envelope assemblies
- Insulation values
- Fenestration performance
- Building infiltration
- Duct leakage
- Mechanical equipment efficiency
- Mechanical ventilation
- Domestic hot water systems
- Energy modeling assumptions

### 4.3 MINOR

An expansion of reference-home testing capabilities or scope
that does not materially alter the existing technical baseline.

Examples include:

- Additional compliance pathways
- Supplemental test scenarios
- Additional reporting requirements
- Expanded software comparison capabilities

### 4.4 PATCH

A nonmaterial correction that does not materially affect
energy modeling assumptions, calculations, or results.

Examples include:

- Typographical corrections
- Documentation clarifications
- Nontechnical metadata corrections
- Formatting corrections

A change shall not be classified as PATCH when it materially
affects energy modeling results.

## 5. Affected Components

Change documentation shall identify applicable affected
components or data categories.

Examples include:

- Building geometry
- Thermal envelope
- Fenestration
- Air infiltration
- Mechanical systems
- Duct systems
- Mechanical ventilation
- Water heating
- Lighting
- Appliances
- Renewable energy
- Energy modeling assumptions
- Compliance pathways
- Documentation
- Metadata
- Other

Multiple affected components may be identified.

## 6. Anticipated Impact

The anticipated impact statement shall describe how the
proposed change may affect:

- Energy consumption
- Energy efficiency
- Energy Rating Index results
- Simulated performance results
- Compliance determinations
- Software comparison results
- Historical result comparability

When no material impact is anticipated, the documentation
shall explain the basis for that determination.

An anticipated impact statement shall not be represented as
a verified modeling result unless supporting analysis exists.

## 7. Review and Approval

All newly registered reference-home versions shall begin
in DEVELOPMENT status.

All MAJOR, MINOR, and PATCH versions shall be subject to
the applicable technical review and approval requirements.

The B.E.E.P. Board of Directors retains final approval
authority for reference-home versions.

## 8. Historical Documentation

Previously registered version identifiers shall not be
deleted, renumbered, reassigned, or reused.

Historical parent-version relationships shall be preserved.

Approved and retired reference-home versions shall remain
subject to established immutability requirements.

Historical modeling results shall remain associated with
the exact reference-home version used to generate them.

## 9. Automated Validation

The repository shall implement automated validation,
where practical, to verify:

- Required change documentation is present
- Change classifications are valid
- Change classifications match semantic version increments
- Parent-version relationships are valid
- Required descriptions are not empty
- Affected components are identified
- Change dates use a consistent format

Automated validation does not replace technical review
or formal Board approval.

## 10. Governance

This document remains proposed until formally adopted
by the B.E.E.P. Board of Directors.

Technical implementation and automated validation do not
constitute formal adoption of this policy.
