# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.7.0] - 2023-07-17
- Added minimal hypothesis length validation for new `Submission` instances.

## [0.7.0] - 2023-07-14
- Updated `Submission.file_format` default value to `XML_FILE`.
- Updated `SubmissionForm` and made `file_format` widget readonly. This ensures that via the UI only XML files can be submitted. [[#101](https://github.com/AppraiseDev/OCELoT/issues/101)]
- Fixed temporary file cleanup bugs in `leaderboard.tests`.
- Added `is_valid` field to `Submission` object model.
- More cleanup related to `TestSet` instances without reference file.
- Updated `install-psql.sh` for PostgreSQL 14 and Debian.
- Added download links for General MT and Biomedical shared tasks.
- Added basic support for `TestSet` instances without reference(s).
- Accept optional 'domain' attribute in XML submissions. [[#112](https://github.com/AppraiseDev/OCELoT/issues/112)]

## [0.7.0] - 2023-07-13
- Fixed tests re: unverified teams' submission access. [[#56](https://github.com/AppraiseDev/OCELoT/issues/56)]
- Fixed page templates to use `ocelot_team_verified` for access to submission view. [[#56](https://github.com/AppraiseDev/OCELoT/issues/56)]
- Fixed #tags and updated to #wmt23dev.
- Submission page/view now only works for verified teams. [[#56](https://github.com/AppraiseDev/OCELoT/issues/56)]
- Added support for sorting `Submission` objects by `submitted_by` and `date_created`. [[#96](https://github.com/AppraiseDev/OCELoT/issues/96)]
- Added default logic for `Team` submissions: we will choose the highest-scoring, or
  the latest `Submission` for each distinct test set. This requires users to explicitly
  withdraw from a language pair/test set if they don't want to participate in that one. [[#104](https://github.com/AppraiseDev/OCELoT/issues/104)]
- Added `is_primary` selection to `SubmissionForm`. [[#104](https://github.com/AppraiseDev/OCELoT/issues/104)]

## [Unreleased]

### Added
- Running multiple competitions at the same time with own deadlines
- Segment-level comparison of two submissions
- Sorting result tables with jQuery tablesorter 2.0 (MIT license)
- Support for new XML format
- Changed descriptions, updates and links for WMT21
- Unverified accounts cannot make submissions
- Show file format and is-verified flag in the Admin Panel
- Institution name, system paper, and system description fields to Team

### Fixed
- Pylint formatter knows about Django after adding the `pylint-django` plugin
- Show an error message for submissions in XML format with no system translations
- Do not show removed submissions on leaderboards
- The deadline counter on the competition page uses server timezone (UTC)

### Changed
- Updated requirements to Django 3
- Removed static files which now need to be generated using `collectstatic`

## [0.0.1] - 2021-01-04

### Added
- This CHANGELOG file
- OCELoT code used at WMT20

[Unreleased]: https://github.com/AppraiseDev/OCELoT/compare/v0.0.1...HEAD
[0.0.1]: https://github.com/AppraiseDev/OCELoT/releases/tag/v0.0.1
