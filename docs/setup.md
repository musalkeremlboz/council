# COUNCIL setup guide

[Türkçe](kurulum.md) · [Home](../README.en.md)

There are two ways to use it. The first is enough for most people.

| | Who can connect | What you need |
|---|---|---|
| **[This computer](#computer)** | The agents on this computer | Python 3.11+, git |
| **[Your own server](#server)** | All your devices, including claude.ai and your phone | A Linux server with a domain name |

<a id="computer"></a>
## 1. Install on this computer

**The easiest way is to let your agent do the setup.** Paste this sentence to your AI agent:

```text
Read these instructions and set up COUNCIL:
https://raw.githubusercontent.com/musalkeremlboz/council/main/INSTALL.md
```

Your agent reads [INSTALL.md](../INSTALL.md) and follows the steps below for you. If you would rather do it yourself:

**macOS and Linux**

```sh
curl -fsSL https://raw.githubusercontent.com/musalkeremlboz/council/main/install.sh | sh
```

**Windows** (PowerShell)

```powershell
irm https://raw.githubusercontent.com/musalkeremlboz/council/main/install.ps1 | iex
```

Setup needs no administrator rights and does four things:

1. **Memory.** Puts COUNCIL in the `~/.council` folder with its own Python environment. Your notes are in `~/.council/vault/`. It brings in the agent memory already on your computer ([details](#import)).
2. **Service.** Starts the memory service on `127.0.0.1:8765`. The service starts by itself when you log in and can be reached only from this computer.
3. **Claude Code.** Connects the hooks (small scripts Claude Code runs by itself at set moments) and the MCP tools. It keeps your other settings in `~/.claude/settings.json` and `~/.claude.json`, and saves a copy of each with the extension `.before-council` before changing it.
4. **Updates.** Turns on the daily update check ([details](#updates)).

When it is done, open a new Claude Code session.

### Options

Options go at the end of the command after `sh -s --`:

```sh
curl -fsSL https://raw.githubusercontent.com/musalkeremlboz/council/main/install.sh | sh -s -- --no-auto-update
```

| Option | What it does |
|---|---|
| `--no-auto-update` | Turns the automatic update off |
| `--no-import` | Does not look for an existing memory |
| `--from FOLDER` | Imports this folder instead of what is found |
| `--port 8765` | Changes the port the service listens on |
| `--force` | If this computer is connected to another COUNCIL memory, switches it to the local one |

If this computer is already connected to another COUNCIL memory, setup stops without changing anything and says so.

### Check

```sh
~/.council/venv/bin/council status
```

On Windows the command is at `%USERPROFILE%\.council\venv\Scripts\council.exe`.

```text
version      0.2.1
service      running on http://127.0.0.1:8765 (0.2.1)
hooks        installed
auto-update  on
notes        /Users/you/.council/vault
```

### Remove

```sh
~/.council/venv/bin/council uninstall
```

Removes the service, the update check, the hooks and the MCP connection. It does not touch other tools' settings. Your notes stay in `~/.council/vault/`.

<a id="import"></a>
## 2. Bringing your existing memory over

No list of memory systems can be complete, so the import has two layers.

**During setup, what can be recognised from files is copied:**

| Source | Read from | Goes to |
|---|---|---|
| Claude Code | `~/.claude/CLAUDE.md`, `~/.claude/projects/*/memory/*.md` | `imported/claude-code/` |
| Codex | `~/.codex/AGENTS.md`, `~/.codex/memories/` | `imported/codex/` |
| Gemini | `~/.gemini/GEMINI.md` | `imported/gemini/` |
| Note vaults with a known layout | Folders you opened in Claude Code | Straight into `core.md`, `rules.md`, `threads.md` and project notes |

Notes under `imported/` can be searched but are not loaded in every session. A note vault is placed directly only while the memory is still empty; it never overwrites a memory in use.

**In the first session, your agent finishes the job.** Setup leaves a task in the memory. Your agent:

1. Checks whether any other memory system is in use on this computer: notes folders, instruction files, memory MCP servers, hooks that add context. If there is one, it reads it and moves what is still true.
2. Sorts what is under `imported/`: lasting facts and preferences into `core.md`, corrections into `rules.md`, project knowledge into `projects/<name>/`.
3. Tells you what it moved and closes the task.

No step changes or deletes the source files. The same source is not imported twice.

To import a folder later:

```sh
council import ~/Documents/MyNotes    # a folder of notes
council import                         # everything found on this computer
```

<a id="updates"></a>
## 3. Automatic updates

Once a day the latest published release of this repository is looked up. If it is newer:

1. The new release is installed into COUNCIL's own Python environment.
2. The hook script is refreshed and the service restarted.
3. Your agent tells you in the next session that the version changed.

Your notes are not touched. Only published releases are installed, not the work in progress in the repository. If updates keep failing, your agent reports that too.

| | |
|---|---|
| Update now | `council update` |
| See the state | `council status` |
| Turn off | `council install --no-auto-update` |
| Turn back on | `council install` |

An automatic update means letting whoever publishes this repository run code on your computer. If you do not want that, turn it off and review the releases yourself.

<a id="server"></a>
## 4. Install on your own server

To connect your phone, claude.ai and several computers to the same memory, the memory has to be at an address reachable from the internet. The commands are for Debian or Ubuntu and need administrator rights.

```sh
sudo mkdir -p /opt/council /var/lib/council
sudo python3 -m venv /opt/council/.venv
sudo /opt/council/.venv/bin/pip install git+https://github.com/musalkeremlboz/council
sudo COUNCIL_DATA=/var/lib/council /opt/council/.venv/bin/council token
sudo COUNCIL_DATA=/var/lib/council /opt/council/.venv/bin/council set-password --generate
```

The fourth command shows the access token and the fifth shows the owner password, once. Write both somewhere safe.

**Service.** Copy [`deploy/council.service`](../deploy/council.service) into `/etc/systemd/system/`. Replace `memory.example.com` with your domain and `Europe/Istanbul` with your time zone. Then:

```sh
sudo systemctl daemon-reload
sudo systemctl enable --now council
```

**HTTPS.** Point your domain's A record at the server. Install [Caddy](https://caddyserver.com), put the contents of [`deploy/Caddyfile`](../deploy/Caddyfile) with your domain into `/etc/caddy/Caddyfile` and run `sudo systemctl reload caddy`. Caddy gets the certificate by itself.

The service listens only on `127.0.0.1`. Caddy is the only door to the outside. `curl https://your-domain/health` should print `{"ok":true,...}`.

**Move your notes.** If you have a memory on your computer, copy the `~/.council/vault/` folder to `/var/lib/council/vault/` on the server and run `council reindex`.

### Connect your computers to the server

On every computer where you use Claude Code:

**Settings file.** `~/.config/council/config.json`:

```json
{"url": "https://your-domain", "token": "YOUR_TOKEN", "timezone": "Europe/Istanbul"}
```

`timezone` is optional. It keeps the time written into notes right on a machine set to another time zone.

**Hook script.**

```sh
mkdir -p ~/.council
curl -fsSL https://raw.githubusercontent.com/musalkeremlboz/council/main/council/hook.py -o ~/.council/hook.py
chmod 600 ~/.config/council/config.json
```

**Registering the hooks.** Add these to the `hooks` section of `~/.claude/settings.json`. If the file has other hooks, do not remove them; add these next to them.

```json
{
  "hooks": {
    "SessionStart": [
      {"hooks": [{"type": "command", "command": "python3 ~/.council/hook.py", "timeout": 10}]}
    ],
    "UserPromptSubmit": [
      {"hooks": [{"type": "command", "command": "python3 ~/.council/hook.py", "timeout": 8}]}
    ],
    "Stop": [
      {"hooks": [{"type": "command", "command": "python3 ~/.council/hook.py", "timeout": 5}]}
    ]
  }
}
```

| Hook | When it runs | What it does |
|---|---|---|
| `SessionStart` | When a session opens | Loads the starting context |
| `UserPromptSubmit` | With each of your messages | Adds the notes relevant to the message |
| `Stop` | When the agent finishes its reply | Reminds once if there is unrecorded work |

**MCP tools.**

```sh
claude mcp add --scope user --transport http council https://your-domain/mcp \
  --header "Authorization: Bearer YOUR_TOKEN"
```

**Check.**

```sh
echo '{"hook_event_name":"SessionStart","session_id":"test"}' | python3 ~/.council/hook.py
```

The output should contain a context starting with `COUNCIL session=test`.

### Connect claude.ai and your phone

1. In claude.ai: Settings → Connectors → Add custom connector.
2. Enter `https://your-domain/mcp` as the address. Leave the advanced settings empty.
3. When you press Connect, COUNCIL's sign-in page opens. Enter the owner password and approve.

The connector also appears in the desktop and phone apps signed in to the same account. These agents have no hooks; they load the memory themselves with a tool call at the start of a session.

### Set up the backup

Your notes are already a git repository. The backup pushes that repository to a private remote of yours.

1. Create a **private** repository on GitHub or another git server. Your personal memory will be in it.
2. Give the server an SSH key that can write to that repository.
3. Add the remote under the name `backup` and try it:

```sh
git -C /var/lib/council/vault remote add backup git@github.com:YOUR_ACCOUNT/YOUR_REPO.git
sudo COUNCIL_DATA=/var/lib/council /opt/council/.venv/bin/council backup
```

It should print `backup ok`. For a regular backup, copy [`deploy/council-backup.service`](../deploy/council-backup.service) and [`deploy/council-backup.timer`](../deploy/council-backup.timer) into `/etc/systemd/system/`:

```sh
sudo systemctl enable --now council-backup.timer
```

The timer runs every 15 minutes. If the backup fails for two days, your agent tells you at the start of a session. The notes and the questions you saved for `council check` go into the backup (a copy of the questions is kept under `vault/.council/`; nothing there is a note or is searched). The access token, the owner password and the sign-in records are kept outside the `vault/` folder and do not go into the backup.

The same backup works for the memory on your own computer: add the remote inside `~/.council/vault` and run `council backup`.

## 5. Commands

| Command | What it does |
|---|---|
| `council install` | Sets up this computer: service, Claude Code, import, updates |
| `council status` | Is the service running, are the hooks and updates on |
| `council update` | Installs the latest published release if it is newer |
| `council uninstall` | Removes the service and the connections; notes are kept |
| `council import [FOLDER]` | Imports a folder of notes, or everything that is found |
| `council serve` | Runs the service by hand |
| `council token` | Prints the access token; `--rotate` creates a new one |
| `council set-password` | Sets the owner password; `--generate` creates a random one |
| `council context "question"` | Prints the context an agent would see |
| `council search "word"` | Searches the notes; also names the words no note contains |
| `council check` | Checks that saved questions still find their notes and lists broken links between notes; changes no note |
| `council check add "question" NOTE` | Saves a question and the note it should find (`remove "question"` drops it) |
| `council reindex` | Rebuilds the search index from the notes |
| `council usage --days 7` | Summarizes what the memory handed out lately |
| `council backup` | Pushes the notes to the remote named `backup` |

The data folder is `~/.council` by default. For another folder use `--data FOLDER` or `COUNCIL_DATA`.

## Troubleshooting

| Symptom | Cause and fix |
|---|---|
| Setup says "Python 3.11 or later is needed" | The Python on this computer is old. Install a newer one from [python.org](https://www.python.org/downloads/). |
| Setup says "already connected to a COUNCIL memory" | This computer is connected to another memory. To switch to the local one: `council install --force`. |
| `council status` says "not running" | Look at `~/.council/service.log`. To set it up again: `council install`. |
| The hook says `COUNCIL memory is unreachable` | The service is down or the address in `config.json` is wrong. Try `council status`. |
| On Linux: "systemd user services are not available" | User services do not run in this session. Run `council serve` by hand. |
| `401` or `unauthorized` | Wrong token. Compare the output of `council token` with the one in `config.json`. |
| The claude.ai sign-in page says "Too many wrong attempts" | Five wrong password attempts lock the sign-in for 15 minutes. Wait and try again. |
| Search returns nothing | `council reindex` rebuilds the index. |
| A command says `no memory at FOLDER` | There is no memory in that folder: `--data` or `COUNCIL_DATA` is wrong, or this computer is connected to a memory on a server and the notes are there. Run the command where the memory lives. |
