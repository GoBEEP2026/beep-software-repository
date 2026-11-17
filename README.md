# B.E.E.P. Software Consistency Repository

An independent, vendor-neutral initiative administered by Building Energy Efficiency Professionals (B.E.E.P.).

## Purpose

Evaluate consistency in residential energy modeling software by comparing standardized building inputs, HPXML files, and calculation outputs.

The repository begins with OpenStudio-ERI and is designed to support additional residential energy modeling engines in the future.

## Objectives

- Maintain standardized reference test homes.
- Compare software-generated HPXML inputs against approved reference specifications.
- Compare energy modeling outputs across participating software tools.
- Track differences between software and calculation engine versions.
- Publish independently reviewed comparison results.
- Protect proprietary vendor information and unpublished submissions.

## Project Structure

- `docs/` — Technical documentation and project requirements.
- `test-homes/` — Standardized reference home specifications.
- `schemas/` — Input and submission data definitions.
- `hpxml-parser/` — HPXML extraction and validation tools.
- `comparison-engine/` — Input and output comparison scripts.
- `reference-results/` — Approved reference calculation results.

## Reference Engine

[OpenStudio-ERI](https://github.com/NatLabRockies/OpenStudio-ERI)

## Administrator

Building Energy Efficiency Professionals (B.E.E.P.)

https://www.gobeep.org

*Participation does not constitute software certification or approval by B.E.E.P.*
