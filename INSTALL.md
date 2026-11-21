# Set up COUNCIL (instructions for an AI agent)

You are an AI agent, and your user asked you to set up COUNCIL: a memory system that lets you and their other agents remember across sessions and devices. **Do the whole setup yourself.** Your user should not have to type a command. Ask them only the one question in step 6.

Talk to your user in their own language. As you go, keep them posted in one short line per step.

## Rules

- Do not use `sudo` or administrator rights. Nothing here needs them.
- Never show the access token in the chat. It is stored in `~/.council/token` and in `~/.claude.json`; do not print either file.
- Never delete the user's existing memory, and do not change it except as step 6 describes.
- Never pass `--force`. If the installer stops because this computer is already connected to another COUNCIL memory, tell the user that and stop.
- If a step fails, show the user the exact error and stop. Do not work around a failure by editing settings files by hand.

The `council` command is not on the PATH. Call it by its full path, here written as `COUNCIL`:

- macOS and Linux: `~/.council/venv/bin/council`
- Windows: `& "$HOME\.council\venv\Scripts\council.exe"`

## 1. Check what is needed

COUNCIL needs Python 3.11 or later and git.

macOS and Linux:

```sh
python3 --version; git --version
```

Windows:

```powershell
py -3 --version; git --version
```

If one is missing and you can install it without administrator rights, do so (for example `brew install python git` where Homebrew exists). Otherwise tell the user exactly what to install (https://www.python.org/downloads/ or https://git-scm.com/downloads) and wait for them.

## 2. Run the installer

macOS and Linux:

```sh
curl -fsSL https://raw.githubusercontent.com/musalkeremlboz/council/main/install.sh | sh
```

Windows (PowerShell):

```powershell
irm https://raw.githubusercontent.com/musalkeremlboz/council/main/install.ps1 | iex
```

What it does, so you can say it in one line: it installs COUNCIL into `~/.council`, starts a small background service that only this computer can reach, connects Claude Code (hooks and MCP tools, keeping the user's other settings and saving a `.before-council` copy of each file it changes), copies the user's existing agent memory in, and turns on a daily update check.

It prints four numbered lines and then `Done.`

- `already connected to a COUNCIL memory`: this computer uses a memory somewhere else. Tell the user and stop.
- `port ... is used by another program`: run the installer again with the port it suggests. macOS and Linux: add `-s -- --port 8766` after `sh`. Windows: download `install.ps1` and run it with `--port 8766`.

## 3. Check

```sh
COUNCIL status
```

`service` must say `running`. When Claude Code is on this computer, `hooks` says `installed` and `mcp tools` says `connected to Claude Code`. The `imported` line says how many notes were brought in and from where.

## 4. Connect yourself, if you are not Claude Code

Skip this if you are Claude Code.

Any agent that speaks MCP can use COUNCIL. Add it to your own MCP configuration as an HTTP server:

- URL: `http://127.0.0.1:8765/mcp` (or the port you chose)
- Header: `Authorization: Bearer <token>`, where the token is the content of the file `~/.council/token`. Copy it from the file into your configuration without displaying it.

You know your own configuration format. Make a copy of the configuration file before you change it. Once connected, COUNCIL's own instructions tell you how to use it; the short version is to call `council_context` at the start of every session.

## 5. Bring the user's existing memory over

The installer has already copied these, if they exist: `~/.claude/CLAUDE.md`, Claude Code's own memory notes (`~/.claude/projects/*/memory/`), `~/.codex/AGENTS.md`, `~/.codex/memories/` and `~/.gemini/GEMINI.md`. You do not need to import them again.

Now use what you know about this computer. Do you, or other agents here, keep memory anywhere else? A notes folder or vault you were told to read and write, a memory tool or memory MCP server, another file that holds facts about the user. For each one you find:

- A folder of Markdown notes, or a single Markdown file:

  ```sh
  COUNCIL import "/path/to/folder-or-file"
  ```

- Memory that is not stored as Markdown files: write what it holds into Markdown files in a temporary folder (one topic per file; keep dates and sources), then import that folder the same way.

Importing only reads the source. Running it twice on the same source adds nothing the second time. Do not ask the user to do any of this. If you find nothing, that is fine.

Sorting the imported notes into their final places happens in the next session. A task for it is already in the memory, so you do not need to remember it.

## 6. Retire the old memory instructions

Look at the instruction files you load every session (for example `~/.claude/CLAUDE.md`, `AGENTS.md`). If one of them tells agents to keep memory somewhere else ("read this notes file first", "write decisions into that folder"), those lines will keep sending new memories to the old place, and the user's memory will split in two.

If you find such lines, this is the one thing to ask the user: show them the lines and ask whether you may remove them now that COUNCIL does that job. If they agree, save a copy of the file next to it (`<name>.before-council`), then remove only those lines. If they do not agree, or there are no such lines, change nothing.

## 7. Tell the user

In their language, in a few short lines:

- COUNCIL is installed and running, and their notes are plain files in `~/.council/vault`.
- What was imported: how many notes, from where (`COUNCIL status` shows it).
- COUNCIL updates itself once a day. `COUNCIL install --no-auto-update` turns that off. Give them the full command path.
- `COUNCIL uninstall` removes it and keeps the notes.
- **Ask them to start a new session.** Memory works from the next session on, and in it you will finish sorting what was imported together with them.
