# proton-runner

A command and control program for running tasks on multiple servers via SSH using YAML playbooks.

Inspired by [Ansible](https://github.com/ansible/ansible) — proton-runner reimplements a minimal subset of its core concepts (playbooks, inventory, plays, tasks) focused exclusively on SSH + bash execution.

## Requirements

- Python 3.11+
- SSH agent, key-based, or password authentication configured on target hosts

## Installation

```bash
uv tool install .
```

This makes the `proton-runner` command available globally.

### Development

```bash
uv sync --dev
uv run proton-runner playbook.yml
```

## Usage

```bash
proton-runner playbook.yml
```

### CLI Options

| Flag | Default | Description |
|------|---------|-------------|
| `playbook` (positional) | — | Path to the YAML playbook file |
| `-i`, `--inventory` | `/etc/playbook/hosts` | Path to the inventory hosts file |
| `-u`, `--user` | Current user | SSH username |
| `--private-key` | SSH agent | Path to SSH private key file |
| `-k`, `--ask-pass` | Off | Prompt for SSH password |
| `-c`, `--concurrency` | `10` | Max concurrent host connections |
| `--timeout` | `10` | SSH connection timeout (seconds) |
| `--command-timeout` | `300` | Per-command execution timeout (seconds) |
| `--no-host-key-check` | Off | Disable host key verification (insecure) |

### Examples

```bash
proton-runner example/playbook.yml -i example/hosts -u deploy --concurrency 20
```

Using password authentication with the [Rebex test server](https://test.rebex.net/):

```bash
proton-runner example/rebex-playbook.yml -i example/rebex-hosts -u demo -k --no-host-key-check
```

Expected output:

```
SSH password:

************************************************************
PLAY [rebex]
************************************************************

TASK [List home directory]
------------------------------------------------------------
ok | test.rebex.net
    drwx------ 2 demo users          0 Mar 31  2023 .
    drwx------ 2 demo users          0 Mar 31  2023 ..
    drwx------ 2 demo users          0 Mar 31  2023 pub
    -rw------- 1 demo users        379 Sep 19  2023 readme.txt

PLAY RECAP
============================================================
  ok=1    failed=0    unreachable=0
```

## Playbook Format

Playbooks are YAML files containing a list of plays. Each play targets a host group and defines tasks to run:

```yaml
---
- hosts: dbservers
  tasks:
    - name: Server uptime
      bash: uptime

    - name: Server disk usage
      bash: du -h --max-depth=1 /
```

The only supported task type is `bash`.

## Inventory Format

The inventory file uses an INI-style format to define host groups:

```ini
# Web tier
[webservers]
foo.example.com
bar.example.com

# Database tier
[dbservers]
one.example.com
two.example.com
three.example.com
```

- Lines starting with `#` are comments
- Blank lines are ignored
- Duplicate hosts within a group are deduplicated

## Design Assumptions

- **Authentication**: Uses SSH agent by default. Password authentication is supported via `--ask-pass` (`-k`). Production systems should prefer key-based auth.
- **Execution model**: Hosts within a play run concurrently (bounded by `--concurrency`). Tasks run sequentially per host over a single reused SSH session.
- **Error handling**: Connection/authentication failures mark a host as "unreachable". Non-zero exit codes mark a task as "failed". Both conditions are reported in the play recap.
- **Exit codes**: `0` = all tasks succeeded, `1` = one or more tasks failed, `2` = one or more hosts unreachable.

## Testing

```bash
uv run pytest tests/ -v
```

## Project Structure

```
src/proton_runner/
├── __main__.py     # Entry point and orchestration
├── cli.py          # Argument parsing
├── models.py       # Data models (Task, Play, TaskResult, HostResult)
├── inventory.py    # INI-style inventory parser
├── playbook.py     # YAML playbook parser and validator
├── executor.py     # Async SSH execution engine
└── output.py       # Color-coded terminal output
```
