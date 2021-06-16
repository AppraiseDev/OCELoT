# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Running multiple competitions at the same time with own deadlines
- Segment-level comparison of two submissions
- Sorting result tables with jQuery tablesorter 2.0 (MIT license)
- Support for new XML format
- Changed descriptions, updates and links for WMT21
- Unverified accounts cannot make submissions
- Show file format and is-verified flag in the Admin Panel.

### Fixed
- Pylint formatter knows about Django after adding the `pylint-django` plugin
- Show an error message for submissions in XML format with no system translations
- Do not show removed submissions on leaderboards

### Changed
- Updated requirements to Django 3
- Removed static files which now need to be generated using `collectstatic`

## [0.0.1] - 2021-01-04

### Added
- This CHANGELOG file
- OCELoT code used at WMT20

[Unreleased]: https://github.com/AppraiseDev/OCELoT/compare/v0.0.1...HEAD
[0.0.1]: https://github.com/AppraiseDev/OCELoT/releases/tag/v0.0.1
