# OpenSSL Upgrade Agent

A cross-platform Python agent designed to detect, backup, and upgrade OpenSSL on various operating systems including Linux, macOS, Windows, AIX, HP-UX, and Solaris.

## Features

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

No special installation is required. Simply download the script `openssl_agent_all_unix_and_windows.py` to the target machine.

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
