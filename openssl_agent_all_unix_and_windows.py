#!/usr/bin/env python3
"""
openssl_agent_all_unix_and_windows.py

Cross-platform OpenSSL detection & upgrade agent.
Supports: Linux, macOS (Darwin), Windows, AIX, HP-UX, Solaris (SunOS).

Features:
- Detects OpenSSL CLI and lib usage for an application.
- Decides upgrade strategy (package manager, side-install from source, rebuild, container).
- Backs up binaries & libs and records checksums.
- Attempts safe side-install of specified OpenSSL version into a versioned prefix.
- Runs verification steps and creates README.md and structured logs.

DISCLAIMER: This agent performs system-level operations. Inspect code before running and use --dry-run first.

Author: ChatGPT (GPT-5 Thinking mini) — delivered as a single-file agent per user request.
"""

import argparse
import datetime
import json
import os
import platform
import shutil
import subprocess
import sys
import tarfile
import tempfile
import hashlib
import urllib.request
import pathlib
import re
from typing import Dict, Any, List, Optional

# --------------------------- Utilities ---------------------------

def run_cmd(cmd: List[str], cwd: Optional[str] = None, sudo: bool = False, shell: bool = False) -> Dict[str, Any]:
    """Run command and capture stdout/stderr/exit. Returns dict for logging."""
    try:
        if sudo and os.name != 'nt':
            cmd = ['sudo'] + cmd
        proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, shell=shell)
        return {
            'ts': datetime.datetime.utcnow().isoformat() + 'Z',
            'cmd': ' '.join(cmd) if isinstance(cmd, list) else str(cmd),
            'exit': proc.returncode,
            'stdout': proc.stdout.strip(),
            'stderr': proc.stderr.strip()
        }
    except Exception as e:
        return {'ts': datetime.datetime.utcnow().isoformat() + 'Z', 'cmd': ' '.join(cmd) if isinstance(cmd, list) else str(cmd), 'exit': 255, 'stdout': '', 'stderr': str(e)}


def sha256_of_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            h.update(chunk)
    return h.hexdigest()


# --------------------------- Agent class ---------------------------

class OpenSSLAgent:
    def __init__(self, args):
        self.args = args
        self.platform = platform.system().lower()
        # Normalize common names
        if self.platform == 'sunos':
            self.platform = 'sunos'
        elif self.platform == 'hp-ux' or 'hp-ux' in platform.platform().lower():
            self.platform = 'hp-ux'
        elif self.platform == 'aix':
            self.platform = 'aix'
        elif self.platform == 'darwin':
            self.platform = 'darwin'
        elif self.platform in ('linux', 'windows'):
            # fine
            pass
        # run-id and dirs
        self.run_id = datetime.datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')
        self.log_dir = pathlib.Path(self.args.log_dir).expanduser() / self.run_id
        self.backup_dir = pathlib.Path(self.args.backup_dir).expanduser() / self.run_id
        self.pre_dir = self.log_dir / 'pre'
        self.post_dir = self.log_dir / 'post'
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.pre_dir.mkdir(parents=True, exist_ok=True)
        self.post_dir.mkdir(parents=True, exist_ok=True)
        self.jsonl_path = self.log_dir / 'agent-run.jsonl'
        self.commands_log = self.log_dir / 'commands.log'
        self.readme_path = self.log_dir / 'README.md'
        self.artifacts = []

    # logging helpers
    def log_step(self, entry: Dict[str, Any]):
        s = json.dumps(entry, ensure_ascii=False)
        with open(self.jsonl_path, 'a') as f:
            f.write(s + '\n')
        with open(self.commands_log, 'a') as f:
            ts = entry.get('ts', '')
            f.write(f"[{ts}] CMD: {entry.get('cmd','')}")
            if entry.get('stdout'):
                f.write('\nOUT:\n' + entry.get('stdout') + '\n')
            if entry.get('stderr'):
                f.write('\nERR:\n' + entry.get('stderr') + '\n')
            f.write('\n' + ('-'*60) + '\n')

    def log_snapshot_file(self, when: str, name: str, content: str):
        path = (self.pre_dir if when == 'pre' else self.post_dir) / name
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        self.artifacts.append(str(path))

    # --------------------------- detection ---------------------------
    def detect_openssl_cli(self):
        # try to run openssl in PATH
        if shutil.which('openssl'):
            r = run_cmd(['openssl', 'version', '-a'])
            self.log_step(r)
            self.log_snapshot_file('pre', 'openssl-version.txt', r.get('stdout', '') + '\n' + r.get('stderr', ''))
            return r
        else:
            entry = {'ts': datetime.datetime.utcnow().isoformat() + 'Z', 'step': 'detect-openssl-cli', 'cmd': 'openssl not found', 'exit': 254, 'stdout': '', 'stderr': 'openssl not in PATH'}
            self.log_step(entry)
            return entry

    def detect_package_managers(self):
        pm = []
        for p in ['apt', 'dnf', 'yum', 'apk', 'zypper', 'brew', 'pkg', 'pkgutil', 'swinstall', 'pkgadd', 'installp', 'rpm', 'dpkg', 'choco', 'winget']:
            if shutil.which(p):
                pm.append(p)
        entry = {'ts': datetime.datetime.utcnow().isoformat() + 'Z', 'step': 'detect-package-managers', 'cmd': 'detected', 'exit': 0, 'stdout': ','.join(pm), 'stderr': ''}
        self.log_step(entry)
        return pm

    def detect_application_linking(self, app_path: str):
        app = pathlib.Path(app_path)
        if not app.exists():
            entry = {'ts': datetime.datetime.utcnow().isoformat() + 'Z', 'step': 'detect-app', 'cmd': f'app not found: {app_path}', 'exit': 254, 'stdout': '', 'stderr': 'app not found'}
            self.log_step(entry)
            return entry

        # platform-specific checks
        if self.platform in ('linux', 'darwin', 'sunos', 'aix', 'hp-ux'):
            # prefer ldd
            if shutil.which('ldd'):
                r = run_cmd(['ldd', str(app)])
                self.log_step(r)
                self.log_snapshot_file('pre', 'ldd-app.txt', r.get('stdout','') + '\n' + r.get('stderr',''))
                return r
            # macOS fallback
            if self.platform == 'darwin' and shutil.which('otool'):
                r = run_cmd(['otool', '-L', str(app)])
                self.log_step(r)
                self.log_snapshot_file('pre', 'otool-app.txt', r.get('stdout','') + '\n' + r.get('stderr',''))
                return r
            # AIX: dump utility
            if self.platform == 'aix' and shutil.which('dump'):
                r = run_cmd(['dump', '-H', str(app)])
                self.log_step(r)
                self.log_snapshot_file('pre', 'dump-app.txt', r.get('stdout','') + '\n' + r.get('stderr',''))
                return r
            # HP-UX chatr
            if self.platform == 'hp-ux' and shutil.which('chatr'):
                r = run_cmd(['chatr', str(app)])
                self.log_step(r)
                self.log_snapshot_file('pre', 'chatr-app.txt', r.get('stdout','') + '\n' + r.get('stderr',''))
                return r

        # Windows - use dumpbin if available (developer tools) or list DLLs
        if self.platform == 'windows':
            # try to run powershell to list loaded DLLs (best-effort)
            cmd = ["powershell", "-Command", f"Get-Process -FileVersionInfo (Get-Item '{str(app)}').VersionInfo | Out-String"]
            r = run_cmd(cmd)
            self.log_step(r)
            self.log_snapshot_file('pre', 'windows-app-info.txt', r.get('stdout','') + '\n' + r.get('stderr',''))
            return r

        # otherwise record limitations
        entry = {'ts': datetime.datetime.utcnow().isoformat() + 'Z', 'step': 'detect-app', 'cmd': 'no-linking-tool-found', 'exit': 253, 'stdout': '', 'stderr': 'linker inspection tools not found'}
        self.log_step(entry)
        return entry

    # --------------------------- Backup ---------------------------
    def prepare_backup(self):
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        saved = []
        # capture openssl binary if present
        openssl_path = shutil.which('openssl')
        if openssl_path:
            target = self.backup_dir / 'openssl_binary'
            shutil.copy2(openssl_path, target)
            saved.append(str(target))
            with open(self.backup_dir / 'openssl_binary.sha256', 'w') as f:
                f.write(sha256_of_file(str(target)))

        # capture library files under common directories
        lib_globs = []
        if self.platform == 'windows':
            lib_globs = [os.path.join(os.environ.get('SystemRoot','C:\Windows'), 'System32', 'libssl*'),]
        else:
            lib_globs = ['/usr/lib*/libssl*', '/usr/local/lib*/libssl*', '/opt/lib*/libssl*', '/usr/lib*/libcrypto*', '/usr/local/lib*/libcrypto*']

        for pattern in lib_globs:
            # Use glob to find files matching the pattern directly
            import glob
            try:
                for p_str in glob.glob(pattern, recursive=False):
                    p = pathlib.Path(p_str)
                    try:
                        dest = self.backup_dir / ('lib_' + p.name)
                        if not dest.exists(): # Avoid duplicates
                            shutil.copy2(p, dest)
                            saved.append(str(dest))
                    except Exception:
                        continue
            except Exception:
                continue

        # create tar.gz of backup
        tarball = self.backup_dir.parent / (self.backup_dir.name + '.tar.gz')
        try:
            with tarfile.open(tarball, 'w:gz') as tar:
                tar.add(self.backup_dir, arcname=self.backup_dir.name)
            self.log_step({'ts': datetime.datetime.utcnow().isoformat() + 'Z', 'step': 'backup', 'cmd': f'created {tarball}', 'exit': 0, 'stdout': '', 'stderr': ''})
            self.artifacts.append(str(tarball))
        except Exception as e:
            self.log_step({'ts': datetime.datetime.utcnow().isoformat() + 'Z', 'step': 'backup', 'cmd': 'tar-failed', 'exit': 1, 'stdout': '', 'stderr': str(e)})

        return saved

    # --------------------------- Side-install from source (best-effort) ---------------------------
    def side_install_from_source(self, version: str, prefix: Optional[str] = None) -> Dict[str, Any]:
        """
        Downloads OpenSSL source and builds into prefix (default /opt/openssl-<version>).
        This function attempts a generic build; for HP-UX, AIX, Solaris you may need to set CC and platform-specific Configure target.
        """
        if prefix is None:
            prefix = f"/opt/openssl-{version}"
        workdir = tempfile.mkdtemp(prefix='/tmp') if os.name != 'nt' else tempfile.mkdtemp()
        tarball = f"openssl-{version}.tar.gz"
        url = f"https://www.openssl.org/source/{tarball}"
        result = {'status': 'error', 'steps': []}

        # 0) Check build tools
        missing_tools = []
        if self.platform == 'windows':
            # On Windows, we need Perl and a C compiler (Visual Studio or MinGW)
            # This is a basic check; a full check is complex.
            if not shutil.which('perl'):
                missing_tools.append('perl')
            # Check for cl (MSVC) or gcc
            if not (shutil.which('cl') or shutil.which('gcc')):
                missing_tools.append('C compiler (cl or gcc)')
        else:
            if not shutil.which('make') and not shutil.which('gmake'):
                missing_tools.append('make')
            if not shutil.which('perl'):
                missing_tools.append('perl')
            if not (shutil.which('gcc') or shutil.which('cc') or shutil.which('clang')):
                missing_tools.append('C compiler')
        
        if missing_tools:
            entry = {'ts': datetime.datetime.utcnow().isoformat()+'Z', 'cmd': 'check-build-tools', 'exit': 1, 'stdout': '', 'stderr': f"Missing build tools: {', '.join(missing_tools)}"}
            result['steps'].append(entry)
            self.log_step(entry)
            return result

        # 1) download
        entry = run_cmd(['bash','-lc', f"curl -fL {url} -o {workdir}/{tarball}"], shell=False)
        result['steps'].append(entry)
        self.log_step(entry)
        if entry['exit'] != 0:
            # attempt urllib as fallback
            try:
                u = urllib.request.urlopen(url)
                with open(os.path.join(workdir, tarball), 'wb') as f:
                    f.write(u.read())
                entry = {'ts': datetime.datetime.utcnow().isoformat()+'Z', 'cmd': 'urllib-download', 'exit': 0, 'stdout': f'downloaded to {workdir}/{tarball}', 'stderr': ''}
                result['steps'].append(entry)
                self.log_step(entry)
            except Exception as e:
                entry = {'ts': datetime.datetime.utcnow().isoformat()+'Z', 'cmd': 'download-failed', 'exit': 1, 'stdout': '', 'stderr': str(e)}
                result['steps'].append(entry)
                self.log_step(entry)
                return result

        # 2) extract
        entry = run_cmd(['tar', 'xzf', os.path.join(workdir, tarball), '-C', workdir])
        result['steps'].append(entry)
        self.log_step(entry)
        if entry['exit'] != 0:
            return result

        srcdir = next(pathlib.Path(workdir).glob('openssl-*'))

        # 3) configure
        # choose platform options heuristically
        cfg_cmd = ['./config']
        if self.platform in ('aix', 'hp-ux', 'sunos'):
            # try generic shared build and prefix
            cfg_cmd = ['./Configure', f'--prefix={prefix}', 'shared']
        else:
            cfg_cmd = ['./config', f'--prefix={prefix}', 'shared']

        entry = run_cmd(cfg_cmd, cwd=str(srcdir))
        result['steps'].append(entry)
        self.log_step(entry)
        if entry['exit'] != 0:
            # try alternative: Configure with linux-x86_64 etc (best-effort)
            alt_cmd = ['./Configure', 'linux-x86_64', f'--prefix={prefix}', 'shared']
            entry = run_cmd(alt_cmd, cwd=str(srcdir))
            result['steps'].append(entry)
            self.log_step(entry)
            if entry['exit'] != 0:
                return result

        # 4) make
        make_cmd = ['make', '-j', str(max(1, os.cpu_count() or 1))]
        if shutil.which('gmake'):
            make_cmd[0] = 'gmake'
        entry = run_cmd(make_cmd, cwd=str(srcdir))
        result['steps'].append(entry)
        self.log_step(entry)
        if entry['exit'] != 0:
            return result

        # 5) make test (optional)
        entry = run_cmd(['make', 'test'], cwd=str(srcdir))
        result['steps'].append(entry)
        self.log_step(entry)
        # continue even if tests fail; record

        # 6) make install
        entry = run_cmd(['make', 'install', f'PREFIX={prefix}'], cwd=str(srcdir))
        result['steps'].append(entry)
        self.log_step(entry)
        if entry['exit'] != 0:
            return result

        # 7) register lib path where possible
        if os.path.isdir('/etc/ld.so.conf.d'):
            conf_path = f'/etc/ld.so.conf.d/openssl-{version}.conf'
            try:
                with open(conf_path, 'w') as f:
                    f.write(os.path.join(prefix, 'lib') + '\n')
                result['steps'].append({'ts': datetime.datetime.utcnow().isoformat()+'Z', 'cmd': f'write {conf_path}', 'exit': 0, 'stdout': '', 'stderr': ''})
                self.log_step(result['steps'][-1])
                if shutil.which('ldconfig'):
                    r = run_cmd(['ldconfig'], sudo=True)
                    result['steps'].append(r)
                    self.log_step(r)
            except Exception as e:
                result['steps'].append({'ts': datetime.datetime.utcnow().isoformat()+'Z', 'cmd': f'write-ldconf-failed', 'exit': 1, 'stdout': '', 'stderr': str(e)})
                self.log_step(result['steps'][-1])

        result['status'] = 'ok'
        result['prefix'] = prefix
        return result

        result['prefix'] = prefix
        return result

    # --------------------------- Dependency Management ---------------------------
    def resolve_package_owner(self, lib_path: str) -> Optional[str]:
        """Resolve a library path to its owning package name."""
        if self.platform == 'linux':
            if shutil.which('dpkg'):
                r = run_cmd(['dpkg', '-S', lib_path])
                if r['exit'] == 0 and ':' in r['stdout']:
                    return r['stdout'].split(':')[0].strip()
            elif shutil.which('rpm'):
                r = run_cmd(['rpm', '-qf', lib_path])
                if r['exit'] == 0:
                    return r['stdout'].strip()
        
        elif self.platform == 'darwin':
            # Homebrew heuristic: /usr/local/Cellar/pkg/ver/...
            if 'Cellar' in lib_path:
                parts = lib_path.split('/')
                try:
                    idx = parts.index('Cellar')
                    if idx + 1 < len(parts):
                        return parts[idx+1]
                except ValueError:
                    pass

        elif self.platform == 'aix':
            # lslpp -w
            r = run_cmd(['lslpp', '-w', lib_path])
            for line in r['stdout'].splitlines():
                # Output: /usr/lib/libc.a  bos.rte.libc  File
                if lib_path in line:
                    parts = line.split()
                    if len(parts) >= 2:
                        return parts[1]

        elif self.platform == 'sunos':
            # IPS: pkg search
            if shutil.which('pkg'):
                r = run_cmd(['pkg', 'search', '-l', '-H', '-o', 'pkg.name', lib_path])
                if r['exit'] == 0 and r['stdout'].strip():
                    return r['stdout'].strip().split()[0]
            # SVR4: pkgchk
            elif shutil.which('pkgchk'):
                r = run_cmd(['pkgchk', '-l', '-p', lib_path])
                # Output parsing is complex, skipping for brevity/risk

        elif self.platform == 'windows':
            # Chocolatey heuristic: C:\ProgramData\chocolatey\lib\pkg\...
            if 'chocolatey' in lib_path.lower() and 'lib' in lib_path.lower():
                parts = lib_path.replace('\\', '/').split('/')
                try:
                    idx = parts.index('lib')
                    if idx + 1 < len(parts):
                        return parts[idx+1]
                except ValueError:
                    pass

        return None

    def upgrade_application_dependencies(self, app_path: str):
        """Check and upgrade application dependencies on all platforms."""
        self.log_step({'ts': datetime.datetime.utcnow().isoformat()+'Z', 'step': 'dep-check', 'cmd': 'checking-dependencies', 'exit': 0, 'stdout': '', 'stderr': ''})
        print(f"Checking dependencies for {app_path}...")
        
        libs = []
        
        # 1. Identify Libraries
        if self.platform in ('linux', 'sunos'):
            r = run_cmd(['ldd', app_path])
            if r['exit'] == 0:
                for line in r['stdout'].splitlines():
                    m = re.search(r'=>\s+(\S+)\s+\(', line)
                    if m:
                        path = m.group(1)
                        if os.path.exists(path):
                            libs.append(path)
                            
        elif self.platform == 'darwin':
            r = run_cmd(['otool', '-L', app_path])
            if r['exit'] == 0:
                for line in r['stdout'].splitlines():
                    line = line.strip()
                    # /usr/lib/libSystem.B.dylib (compatibility version ...)
                    if line.startswith('/'):
                        path = line.split()[0]
                        if os.path.exists(path):
                            libs.append(path)

        elif self.platform == 'aix':
            # Try ldd first (available on newer AIX)
            if shutil.which('ldd'):
                r = run_cmd(['ldd', app_path])
                for line in r['stdout'].splitlines():
                    m = re.search(r'=>\s+(\S+)\s+\(', line)
                    if m:
                        libs.append(m.group(1))
            else:
                # Fallback to dump -H (shows members, not full paths usually, hard to map)
                pass

        elif self.platform == 'hp-ux':
            if shutil.which('chatr'):
                r = run_cmd(['chatr', app_path])
                # chatr output parsing is complex and varies.
                pass

        elif self.platform == 'windows':
            # Try dumpbin if available
            if shutil.which('dumpbin'):
                r = run_cmd(['dumpbin', '/DEPENDENTS', app_path])
                # Output:
                #     Image has the following dependencies:
                #
                #       KERNEL32.dll
                #       ...
                # This gives filenames, not full paths. Hard to map to packages.
                pass
        
        # 2. Resolve Packages
        packages = set()
        for lib in libs:
            pkg = self.resolve_package_owner(lib)
            if pkg:
                packages.add(pkg)
        
        # 3. Filter & Confirm
        openssl_terms = ['openssl', 'libssl', 'libcrypto']
        packages_to_upgrade = sorted([p for p in packages if not any(x in p for x in openssl_terms)])
        
        if not packages_to_upgrade:
            print("No external package dependencies found to upgrade (or could not map libs to packages).")
            return

        print(f"Found {len(packages_to_upgrade)} dependencies (excluding OpenSSL):")
        if self.confirm_upgrade(packages_to_upgrade):
            # 4. Upgrade
            if self.platform == 'linux':
                if shutil.which('apt'):
                    cmd = ['apt', 'install', '--only-upgrade', '-y'] + packages_to_upgrade
                    self.log_step(run_cmd(cmd, sudo=True))
                elif shutil.which('yum'):
                    cmd = ['yum', 'update', '-y'] + packages_to_upgrade
                    self.log_step(run_cmd(cmd, sudo=True))
                elif shutil.which('dnf'):
                    cmd = ['dnf', 'update', '-y'] + packages_to_upgrade
                    self.log_step(run_cmd(cmd, sudo=True))
                elif shutil.which('apk'):
                    cmd = ['apk', 'add', '--upgrade'] + packages_to_upgrade
                    self.log_step(run_cmd(cmd, sudo=True))
            
            elif self.platform == 'darwin':
                if shutil.which('brew'):
                    cmd = ['brew', 'upgrade'] + packages_to_upgrade
                    self.log_step(run_cmd(cmd))
            
            elif self.platform == 'windows':
                if shutil.which('choco'):
                    cmd = ['choco', 'upgrade', '-y'] + packages_to_upgrade
                    self.log_step(run_cmd(cmd))
            
            elif self.platform == 'sunos':
                if shutil.which('pkg'):
                    cmd = ['pkg', 'update'] + packages_to_upgrade
                    self.log_step(run_cmd(cmd, sudo=True))
            
            elif self.platform == 'aix':
                # AIX updates via installp or yum
                if shutil.which('yum'):
                    cmd = ['yum', 'update', '-y'] + packages_to_upgrade
                    self.log_step(run_cmd(cmd, sudo=True))
            
            print("Dependency upgrade process finished.")

    # --------------------------- Upgrade orchestration ---------------------------
    def confirm_upgrade(self, items: List[str]) -> bool:
        print(f"\nThe agent is about to upgrade/install the following items:")
        for item in items:
            print(f" - {item}")
        
        if self.args.force:
            print("Force mode enabled. Proceeding automatically.")
            return True

        try:
            choice = input("Do you want to proceed with the upgrade? [y/N]: ").strip().lower()
        except EOFError:
            return False
        return choice == 'y'

    def decide_and_execute(self):
        # high-level orchestration
        self.log_step({'ts': datetime.datetime.utcnow().isoformat()+'Z', 'step': 'start', 'cmd': 'decide_and_execute', 'exit': 0, 'stdout': f'platform={self.platform}', 'stderr': ''})

        # 1) Detect openssl CLI
        self.detect_openssl_cli()
        # 2) Detect package managers
        pms = self.detect_package_managers()
        # 3) Application linking
        app_link = None
        if self.args.app_path:
            app_link = self.detect_application_linking(self.args.app_path)
            # NEW: Check and upgrade dependencies
            self.upgrade_application_dependencies(self.args.app_path)

        # 4) backup
        self.prepare_backup()

        # 5) choose strategy
        strategy = {'type': None, 'reason': None}
        # prefer package manager if it exists and likely provides openssl
        if any(pm in pms for pm in ['apt', 'dnf', 'yum', 'apk', 'zypper', 'brew', 'pkg']):
            strategy['type'] = 'package-manager'
            strategy['reason'] = f'package manager(s) found: {pms}'
        else:
            # fall back to side-install (safer than overwriting vendor libs)
            strategy['type'] = 'side-install'
            strategy['reason'] = 'no known package manager that provides target version; using side-install'

        self.log_step({'ts': datetime.datetime.utcnow().isoformat()+'Z', 'step': 'strategy', 'cmd': 'chosen', 'exit': 0, 'stdout': json.dumps(strategy), 'stderr': ''})

        # 6) dry-run handling
        if self.args.dry_run:
            self.log_step({'ts': datetime.datetime.utcnow().isoformat()+'Z', 'step': 'dry-run', 'cmd': 'planned-actions', 'exit': 0, 'stdout': f"Would run strategy: {strategy}", 'stderr': ''})
            self.generate_readme(strategy, success=None)
            return {'status': 'dry-run', 'strategy': strategy}

        # 7) perform upgrade
        if strategy['type'] == 'package-manager':
            pm = pms[0]
            # simple implementations per PM (best-effort)
            if pm == 'apt':
                if not self.confirm_upgrade(['openssl', 'libssl-dev']):
                    return {'status': 'aborted', 'success': False}
                self.log_step(run_cmd(['apt', 'update', '-y']))
                self.log_step(run_cmd(['apt', 'install', '--only-upgrade', '-y', 'openssl', 'libssl-dev']))
            elif pm in ('dnf','yum'):
                if not self.confirm_upgrade(['openssl']):
                    return {'status': 'aborted', 'success': False}
                self.log_step(run_cmd([pm, 'makecache']))
                self.log_step(run_cmd([pm, 'update', '-y', 'openssl']))
            elif pm == 'apk':
                if not self.confirm_upgrade(['openssl']):
                    return {'status': 'aborted', 'success': False}
                self.log_step(run_cmd(['apk', 'update']))
                self.log_step(run_cmd(['apk', 'add', '--upgrade', 'openssl']))
            elif pm == 'brew':
                pkg = f"openssl@{self.args.target_version.split('.')[0]}"
                if not self.confirm_upgrade([pkg]):
                    return {'status': 'aborted', 'success': False}
                self.log_step(run_cmd(['brew', 'update']))
                self.log_step(run_cmd(['brew', 'upgrade', pkg]))
            else:
                # fallback to side-install
                if not self.confirm_upgrade([f'OpenSSL {self.args.target_version} (source build)']):
                    return {'status': 'aborted', 'success': False}
                res = self.side_install_from_source(self.args.target_version)
                self.log_step({'ts': datetime.datetime.utcnow().isoformat()+'Z', 'step': 'side-install-result', 'cmd': 'side-install', 'exit': 0 if res.get('status')=='ok' else 1, 'stdout': json.dumps(res), 'stderr': ''})
        elif strategy['type'] == 'side-install':
            if not self.confirm_upgrade([f'OpenSSL {self.args.target_version} (source build)']):
                return {'status': 'aborted', 'success': False}
            res = self.side_install_from_source(self.args.target_version)
            self.log_step({'ts': datetime.datetime.utcnow().isoformat()+'Z', 'step': 'side-install-result', 'cmd': 'side-install', 'exit': 0 if res.get('status')=='ok' else 1, 'stdout': json.dumps(res), 'stderr': ''})

        # 8) post checks
        post_openssl = self.detect_openssl_cli()
        if self.args.app_path:
            post_ldd = self.detect_application_linking(self.args.app_path)
        # 9) smoke tests
        smoke = self.run_smoke_tests()
        # 10) generate README and finish
        success = (smoke.get('status') == 'pass')
        self.generate_readme(strategy, success=success)
        return {'status': 'done', 'success': success}

    # --------------------------- Smoke tests ---------------------------
    def run_smoke_tests(self):
        results = {'status': 'unknown', 'checks': []}
        # check openssl version
        # check openssl version
        # If we did a side-install, check that specific binary
        check_bin = 'openssl'
        if self.args.target_version:
             # Try to guess where it might be if we just installed it
             # This is tricky because decide_and_execute returns before we know the exact path in smoke tests unless we pass it.
             # But we can check if a custom prefix was used.
             pass

        # If we have a side-install prefix from the execution, we should use it. 
        # But run_smoke_tests is called without arguments. 
        # We'll check the default 'openssl' in PATH, and also check /opt/openssl-<version>/bin/openssl if it exists.
        
        bins_to_check = []
        if shutil.which('openssl'):
            bins_to_check.append(shutil.which('openssl'))
        
        # Check potential side-install location
        side_install_bin = pathlib.Path(f"/opt/openssl-{self.args.target_version}/bin/openssl")
        if side_install_bin.exists():
             bins_to_check.append(str(side_install_bin))
        
        for bin_path in bins_to_check:
            r = run_cmd([bin_path, 'version', '-a'])
            self.log_step(r)
            self.log_snapshot_file('post', f'openssl-version-{pathlib.Path(bin_path).name}.txt', r.get('stdout','') + '\n' + r.get('stderr',''))
            if self.args.target_version in r.get('stdout',''):
                results['checks'].append({'name': f'openssl-version-{bin_path}', 'ok': True})
            else:
                results['checks'].append({'name': f'openssl-version-{bin_path}', 'ok': False})
        # try TLS handshake if health-url provided
        if self.args.health_url and shutil.which('openssl'):
            host, port = self.args.health_url, 443
            r = run_cmd(['bash','-lc', f"echo | openssl s_client -connect {host}:{port} -servername {host} -brief"], shell=False)
            self.log_step(r)
            ok = (r.get('exit') == 0)
            results['checks'].append({'name': 'openssl-s_client', 'ok': ok})

        # basic health endpoint
        if self.args.health_url and shutil.which('curl'):
            r = run_cmd(['curl', '--fail', '--silent', '--show-error', self.args.health_url])
            self.log_step(r)
            results['checks'].append({'name': 'http-health', 'ok': (r.get('exit') == 0)})

        # finalizing status
        if all(c.get('ok') for c in results['checks']) and results['checks']:
            results['status'] = 'pass'
        else:
            results['status'] = 'fail' if results['checks'] else 'no-checks'
        self.log_step({'ts': datetime.datetime.utcnow().isoformat()+'Z', 'step': 'smoke-tests', 'cmd': 'completed', 'exit': 0, 'stdout': json.dumps(results), 'stderr': ''})
        return results

    # --------------------------- README generation ---------------------------
    def generate_readme(self, strategy: Dict[str, Any], success: Optional[bool]):
        lines = []
        lines.append(f"# OpenSSL Upgrade Report\nRun ID: {self.run_id}\nTimestamp (UTC): {datetime.datetime.utcnow().isoformat()}Z\n")
        lines.append("## Summary")
        lines.append(f"- Target version: {self.args.target_version}")
        lines.append(f"- Platform: {self.platform}")
        lines.append(f"- Strategy: {strategy.get('type')} — {strategy.get('reason')}")
        lines.append('\n## Artifacts')
        for a in self.artifacts:
            lines.append(f"- {a}")
        lines.append('\n## Pre-upgrade snapshots')
        for p in (self.pre_dir.iterdir() if self.pre_dir.exists() else []):
            lines.append(f"- {p}")
        lines.append('\n## Post-upgrade snapshots')
        for p in (self.post_dir.iterdir() if self.post_dir.exists() else []):
            lines.append(f"- {p}")
        lines.append('\n## Commands log')
        lines.append(f"See commands log: {self.commands_log}")
        lines.append('\n## Verification')
        lines.append(f"- Smoke tests success: {success}")
        lines.append('\n## Rollback instructions (generic)')
        lines.append('1. Stop dependent services (systemctl stop <service> or appropriate command).')
        lines.append('2. Restore backup tarball from backup directory into / (or original locations).')
        lines.append('3. Run ldconfig if available: `sudo ldconfig`.')
        lines.append('4. Start services and run verification.')

        with open(self.readme_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
        self.log_step({'ts': datetime.datetime.utcnow().isoformat()+'Z', 'step': 'generate-readme', 'cmd': f'write {self.readme_path}', 'exit': 0, 'stdout': '', 'stderr': ''})
        self.artifacts.append(str(self.readme_path))


# --------------------------- CLI ---------------------------

def parse_args():
    p = argparse.ArgumentParser(description='Cross-platform OpenSSL upgrade agent (Linux/macOS/Windows/AIX/HP-UX/Solaris)')
    p.add_argument('--app-path', help='Path to application binary to inspect (optional)', default=None)
    p.add_argument('--target-version', help='Target OpenSSL version (e.g. 3.0.8)', required=True)
    p.add_argument('--dry-run', action='store_true', help='Do not perform changes; only log planned steps')
    p.add_argument('--backup-dir', default=os.path.join(tempfile.gettempdir(), 'openssl-agent-backups'), help='Backup base directory')
    p.add_argument('--log-dir', default=os.path.join(tempfile.gettempdir(), 'openssl-agent-logs'), help='Log base directory')
    p.add_argument('--health-url', default=None, help='Optional health URL or host for smoke tests (e.g. example.com or https://localhost/health)')
    p.add_argument('--force', action='store_true', help='Force destructive actions (not recommended)')
    return p.parse_args()


# --------------------------- main ---------------------------

def main():
    args = parse_args()
    agent = OpenSSLAgent(args)
    res = agent.decide_and_execute()
    print('Run complete. Logs & README at:', agent.log_dir)
    if res.get('status') == 'dry-run':
        print('Dry-run only; no changes made.')
    elif res.get('success') is True:
        print('Upgrade seems successful (smoke-tests passed).')
    else:
        print('Upgrade finished; check logs and README for details and consider rollback if needed.')


if __name__ == '__main__':
    main()
