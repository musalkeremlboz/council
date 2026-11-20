# COUNCIL setup guide

[Türkçe](kurulum.md) · [Home](../README.en.md)

A person or an AI agent can follow this guide.

> **If you are an agent:** apply the steps in order and run the check at the end of each section. Do not print the access token or the owner password into the chat; write them to a file and tell the user where it is. Before changing an existing settings file, back it up and keep the other settings in it.

## 0. Requirements

- Python 3.11 or later
- git
- To connect from several devices: a Linux server that is always on, with a domain name

There are two kinds of setup. Whichever you choose, copying the `vault/` folder is enough to move to the other later.

| | Who can connect | What you need |
|---|---|---|
| **A. One computer** | Only the agents on that computer | Nothing |
| **B. Server** | All your devices, including claude.ai and your phone | A Linux server and a domain name |

## 1. Set up the server

### A. One computer

```sh
python3 -m venv ~/.council/venv
~/.council/venv/bin/pip install git+https://github.com/musalkeremlboz/council
~/.council/venv/bin/council token
```

The last command creates and prints the access token. The token is kept in `~/.council/token`; your notes are in `~/.council/vault/`. For another folder, set the `COUNCIL_DATA` environment variable.

Start the service:

```sh
nohup ~/.council/venv/bin/council serve > ~/.council/serve.log 2>&1 &
```

The service runs on `127.0.0.1:8765` and stops when the computer restarts; run the same command again then.

### B. Server

The commands are for Debian or Ubuntu and need administrator rights.

```sh
sudo mkdir -p /opt/council /var/lib/council
sudo python3 -m venv /opt/council/.venv
sudo /opt/council/.venv/bin/pip install git+https://github.com/musalkeremlboz/council
sudo COUNCIL_DATA=/var/lib/council /opt/council/.venv/bin/council token
sudo COUNCIL_DATA=/var/lib/council /opt/council/.venv/bin/council set-password --generate
```

The last command shows the owner password once. You are asked for it when connecting claude.ai; write it somewhere safe.

**Service.** Copy [`deploy/council.service`](../deploy/council.service) into `/etc/systemd/system/`. Replace `memory.example.com` with your domain and `Europe/Istanbul` with your time zone. Then:

```sh
sudo systemctl daemon-reload
sudo systemctl enable --now council
```

**HTTPS.** Point your domain's A record at the server. Install [Caddy](https://caddyserver.com), put the contents of [`deploy/Caddyfile`](../deploy/Caddyfile) with your domain into `/etc/caddy/Caddyfile` and run `sudo systemctl reload caddy`. Caddy gets the certificate by itself.

The service listens only on `127.0.0.1`. Caddy is the only door to the outside.

### Check

```sh
curl http://127.0.0.1:8765/health
```

It should print `{"ok":true,"version":"0.1.0"}`. On a server setup, `curl https://your-domain/health` should give the same answer.

<a id="claude-code"></a>
## 2. Connect Claude Code

Do this on every computer where you use Claude Code. `ADDRESS` is `http://127.0.0.1:8765` for a one-computer setup and `https://your-domain` for a server setup.

**Settings file.** `~/.config/council/config.json`:

```json
{"url": "ADDRESS", "token": "YOUR_TOKEN", "timezone": "Europe/Istanbul"}
```

```sh
chmod 600 ~/.config/council/config.json
```

`timezone` is optional. It keeps the time written into notes right on a machine set to another time zone.

**Hook script.** A hook is a small script Claude Code runs by itself at set moments. It uses only Python's standard library, so there is nothing else to install.

```sh
mkdir -p ~/.council
curl -fsSL https://raw.githubusercontent.com/musalkeremlboz/council/main/council/hook.py -o ~/.council/hook.py
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

**MCP tools.** So the agent can search the memory and write notes:

```sh
claude mcp add --scope user --transport http council ADDRESS/mcp \
  --header "Authorization: Bearer YOUR_TOKEN"
```

### Check

```sh
echo '{"hook_event_name":"SessionStart","session_id":"test"}' | python3 ~/.council/hook.py
```

The output should contain a context starting with `COUNCIL session=test`. If it says `COUNCIL memory is unreachable`, the address or the token is wrong or the service is not running.

Then open a new Claude Code session and ask "What is in your memory?".

## 3. Connect claude.ai and your phone

Only possible with a server setup.

1. In claude.ai: Settings → Connectors → Add custom connector.
2. Enter `https://your-domain/mcp` as the address. Leave the advanced settings empty.
3. When you press Connect, COUNCIL's sign-in page opens. Enter the owner password and approve.

The connector also appears in the desktop and phone apps signed in to the same account. These agents have no hooks; they load the memory themselves with a tool call at the start of a session.

## 4. Set up the backup

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

The timer runs every 15 minutes. If the backup fails for two days, your agent tells you at the start of a session.

Only the notes go into the backup. The access token, the owner password and the sign-in records are kept outside the `vault/` folder.

## 5. Commands

| Command | What it does |
|---|---|
| `council serve` | Runs the service |
| `council token` | Prints the access token; `--rotate` creates a new one |
| `council set-password` | Sets the owner password; `--generate` creates a random one |
| `council context "question"` | Prints the context an agent would see |
| `council search "word"` | Searches the notes |
| `council reindex` | Rebuilds the search index from the notes |
| `council usage --days 7` | Summarizes what the memory handed out lately |
| `council backup` | Pushes the notes to the remote named `backup` |
| `council import-avenox FOLDER` | Imports an Avenox Beyin V3 vault |

The data folder is `~/.council` by default. For another folder use `--data FOLDER` or `COUNCIL_DATA`.

## 6. Updating

```sh
sudo /opt/council/.venv/bin/pip install -U git+https://github.com/musalkeremlboz/council
sudo systemctl restart council
```

On a one-computer setup run the same command with `~/.council/venv/bin/pip`, then stop and start the service. If the hook script changed, repeat the `curl` command from section 2. Your notes are not touched.

## Troubleshooting

| Symptom | Cause and fix |
|---|---|
| `no token: run council token first` | The service could not find the token. Run `council token` with the same data folder as the service. |
| The hook says `COUNCIL memory is unreachable` | The service is down or the address in `config.json` is wrong. Try `curl ADDRESS/health`. |
| `401` or `unauthorized` | Wrong token. Compare the output of `council token` with the one in `config.json`. |
| The claude.ai sign-in page says "Too many wrong attempts" | Five wrong password attempts lock the sign-in for 15 minutes. Wait and try again. |
| Search returns nothing | `council reindex` rebuilds the index. |
