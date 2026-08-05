# Default HACS Submission Checklist

Use this checklist when preparing `megaesp-ha` for inclusion in the default HACS store.

## Required

- repository is public
- repository works as a HACS custom repository
- `Validate` GitHub Action passes
- `Hassfest` GitHub Action passes
- create a GitHub release after validations pass
- repository has description and topics
- repository has brand assets
- repository has `manifest.json` with required keys

## Before submission

- verify installation on a clean Home Assistant instance
- verify config flow works
- verify at least one controller can be added successfully
- verify the MegaESP panel is generated
- verify `climate` entities appear for DS18B20 regulators

## Submission

Submit the repository to HACS default repositories after the above checks are green.
