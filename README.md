# OpenSSL Upgrade Agent

A cross-platform Python agent designed to detect, backup, and upgrade OpenSSL on various operating systems including Linux, macOS, Windows, AIX, HP-UX, and Solaris.

## Features

*   **Vulnerability Check**: Automatically checks for known vulnerabilities in the target OpenSSL version using the OSV.dev API before any download or upgrade. Aborts if critical or high severity vulnerabilities are detected.
*   **Detection**: Identifies existing OpenSSL installations and package managers.
*   **Dependency Analysis**: Checks which libraries an application is linked against (using `ldd`, `otool`, etc.).
*   **Dependency Upgrade**: Identifies and upgrades application dependencies (libraries) using system package managers, with user confirmation. Supports Linux, macOS, Windows, AIX, and Solaris.
*   **Backup**: Automatically backs up existing OpenSSL binaries and libraries before making changes.
*   **Smart Upgrade**:
    *   Uses system package managers (`apt`, `yum`, `brew`, etc.) if available.
    *   Falls back to a "side-install" (compiling from source) into a separate prefix (e.g., `/opt/openssl-<version>`) to avoid breaking system dependencies.
*   **Verification**: Runs smoke tests including version checks and optional TLS handshake/health checks.
*   **Reporting**: Generates detailed logs and a run report.

## Prerequisites

*   **Python 3.x** installed on the system.
*   **Build Tools** (only for side-install/compilation):
    *   C Compiler (`gcc`, `clang`, or `cl` on Windows).
    *   `make` or `gmake`.
    *   `perl`.
*   **Internet Access**: Required to download OpenSSL source code if compiling from source.

## Installation

1. Download the script `openssl_agent_all_unix_and_windows.py` to the target machine.

2. Install required dependencies:

```bash
pip install -r requirements.txt
```

Or install the requests library directly:

```bash
pip install requests
```

**Note**: The `requests` library is required for the vulnerability check feature. If not installed, the agent will skip the vulnerability check and proceed with a warning.

## Usage

Run the script from the command line using Python 3.

### Basic Usage

To upgrade OpenSSL to a specific version (e.g., 3.0.8):

```bash
python3 openssl_agent_all_unix_and_windows.py --target-version 3.0.8
```

### Dry Run (Recommended First Step)

To see what the agent *would* do without actually making any changes:

```bash
python3 openssl_agent_all_unix_and_windows.py --target-version 3.0.8 --dry-run
```

### Inspecting an Application

To check which OpenSSL libraries a specific application is using:

```bash
python3 openssl_agent_all_unix_and_windows.py --target-version 3.0.8 --app-path /path/to/your/application
```

### Upgrading Application Dependencies

When `--app-path` is provided, the agent will also check for other outdated system dependencies linked to the application. It will list them and ask for your permission to upgrade them using the system package manager (e.g., `apt`, `yum`, `brew`, `choco`).

### Customizing Directories

You can specify where backups and logs are stored:

```bash
python3 openssl_agent_all_unix_and_windows.py \
  --target-version 3.0.8 \
  --backup-dir /var/backups/openssl \
  --log-dir /var/log/openssl-agent
```

### Health Check

To run a TLS handshake check against a specific host after upgrade:

```bash
python3 openssl_agent_all_unix_and_windows.py --target-version 3.0.8 --health-url example.com
```

## Vulnerability Check

**Important Security Feature**: Before any download or upgrade operation (including dry-runs), the agent automatically checks for known vulnerabilities in the specified OpenSSL version using the [OSV.dev](https://osv.dev) vulnerability database.

### How It Works

1. The agent queries the OSV.dev API for the target OpenSSL version
2. If vulnerabilities are found, they are displayed with severity levels
3. **Critical or High severity vulnerabilities will abort the operation**
4. Medium or Low severity vulnerabilities will display a warning but allow you to proceed

### Example Output

```
======================================================================
SECURITY CHECK: Vulnerability Scan
======================================================================

Checking for vulnerabilities in OpenSSL 3.0.0...

======================================================================
⚠ WARNING: 5 vulnerabilities found for OpenSSL 3.0.0
======================================================================
  CRITICAL: 2
  HIGH: 1

Vulnerability Details:
----------------------------------------------------------------------

  ID: CVE-2022-XXXXX
  Severity: CRITICAL
  Summary: Buffer overflow in SSL handshake...
  Details: https://osv.dev/vulnerability/CVE-2022-XXXXX

❌ ABORTING: Critical or high severity vulnerabilities detected!
   Found 2 CRITICAL and 1 HIGH severity issues.

   Recommendation: Choose a different OpenSSL version without known vulnerabilities.
   Visit https://www.openssl.org/news/vulnerabilities.html for more information.
```

### Bypassing the Check

The vulnerability check **cannot be bypassed**. This is a critical security feature designed to prevent you from installing vulnerable versions of OpenSSL. If you need to proceed with a version that has known vulnerabilities, you must modify the source code (not recommended).

## Command Line Arguments

| Argument | Description | Required | Default |
| :--- | :--- | :--- | :--- |
| `--target-version` | The OpenSSL version to install (e.g., `3.0.8`). | **Yes** | - |
| `--app-path` | Path to an application binary to inspect for OpenSSL linkage. | No | `None` |
| `--dry-run` | Simulate the process without making changes. | No | `False` |
| `--backup-dir` | Directory to store backups. | No | `temp/openssl-agent-backups` |
| `--log-dir` | Directory to store logs and reports. | No | `temp/openssl-agent-logs` |
| `--health-url` | URL or host for smoke tests (e.g., `example.com`). | No | `None` |
| `--force` | Force destructive actions (use with caution). | No | `False` |

## Output

The agent creates a timestamped directory in the `log-dir` containing:
*   `README.md`: A summary report of the run.
*   `commands.log`: A detailed log of all executed commands and their output.
*   `agent-run.jsonl`: Structured logs in JSONL format.
*   `pre/`: Snapshots of system state before the run.
*   `post/`: Snapshots of system state after the run.

## Rollback

If an upgrade causes issues, the agent provides rollback instructions in the generated run report (`README.md` in the log directory). Generally, this involves restoring the files from the created backup tarball.
