# proton-runner

A command and control program for running tasks on multiple servers via SSH using YAML playbooks.

## Requirements

- Python 3.11+
- SSH agent or key-based authentication configured on target hosts

## Installation

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

For development (includes pytest):

```bash
pip install -e ".[dev]"
```

## Usage

```bash
proton-runner playbook.yml
```

Or run as a module:

```bash
python -m proton_runner playbook.yml
```

### CLI Options

| Flag | Default | Description |
|------|---------|-------------|
| `playbook` (positional) | — | Path to the YAML playbook file |
| `-i`, `--inventory` | `/etc/playbook/hosts` | Path to the inventory hosts file |
| `-u`, `--user` | Current user | SSH username |
| `--private-key` | SSH agent | Path to SSH private key file |
| `-c`, `--concurrency` | `10` | Max concurrent host connections |
| `--timeout` | `10` | SSH connection timeout (seconds) |
| `--command-timeout` | `300` | Per-command execution timeout (seconds) |
| `--no-host-key-check` | Off | Disable host key verification (insecure) |

### Example

```bash
proton-runner example/playbook.yml -i example/hosts -u deploy --concurrency 20
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

- **Authentication**: Uses SSH agent by default. Password authentication is not supported — production systems should use key-based auth.
- **Execution model**: Hosts within a play run concurrently (bounded by `--concurrency`). Tasks run sequentially per host over a single reused SSH session.
- **Error handling**: Connection/authentication failures mark a host as "unreachable". Non-zero exit codes mark a task as "failed". Both conditions are reported in the play recap.
- **Exit codes**: `0` = all tasks succeeded, `1` = one or more tasks failed, `2` = one or more hosts unreachable.

## Testing

```bash
pytest tests/ -v
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
