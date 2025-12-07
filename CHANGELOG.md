# Changelog

All notable changes to the OpenSSL Upgrade Agent will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Planned
- Unit tests for core functionality
- Configuration file support
- Interactive mode improvements
- Package manager integration for automatic updates

## [1.1.0] - 2025-12-07

### Added
- **Critical Security Feature**: Automatic vulnerability checking before any download or upgrade
  - Integrates with OSV.dev API to check for known vulnerabilities
  - Displays detailed vulnerability information including severity levels
  - **Automatically aborts** if critical or high severity vulnerabilities are detected
  - Shows warnings for medium/low severity issues but allows proceeding
  - Works for both regular upgrades and dry-runs
- Added `requests` library as a dependency for API communication
- Comprehensive documentation of the vulnerability check feature in README

### Changed
- Updated installation instructions to include dependency installation
- Enhanced security posture by preventing installation of known vulnerable versions

### Security
- Prevents installation of OpenSSL versions with critical or high severity vulnerabilities
- Provides direct links to vulnerability details for user review
- Cannot be bypassed without modifying source code (by design)

## [1.0.0] - 2025-12-02

### Added
- Initial release of OpenSSL Upgrade Agent
- Cross-platform support (Windows, Linux, macOS)
- Automatic OpenSSL detection and version checking
- Automated backup creation with timestamps
- Comprehensive logging system
- Rollback functionality for failed upgrades
- Interactive and non-interactive modes
- Support for custom OpenSSL installation paths
- Detailed upgrade reports
- Error handling and recovery mechanisms

### Features
- **Multi-platform Support**: Works on Windows, Linux, and macOS
- **Safety First**: Automatic backups before any modifications
- **Detailed Logging**: Comprehensive logs stored in `logs/` directory
- **Flexible Options**: Command-line arguments for customization
- **Rollback Support**: Restore previous version if upgrade fails

### Security
- Validates file integrity before operations
- Creates secure backups with proper permissions
- Logs all operations for audit trail

## Release Notes

### Version 1.0.0 - Initial Release

This is the first stable release of the OpenSSL Upgrade Agent. The tool has been tested on:
- Windows 10/11
- Ubuntu 20.04/22.04
- macOS 11+
- CentOS/RHEL 7/8

**Important Notes:**
- Always test in a non-production environment first
- Review the SECURITY.md file for security considerations
- Check CONTRIBUTING.md if you want to contribute

---

[Unreleased]: https://github.com/gopalkoyyana/Open-SSL-Upgrade-Agent/compare/v1.1.0...HEAD
[1.1.0]: https://github.com/gopalkoyyana/Open-SSL-Upgrade-Agent/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/gopalkoyyana/Open-SSL-Upgrade-Agent/releases/tag/v1.0.0

