<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/assets/kapak-en-koyu.svg">
  <img src="docs/assets/kapak-en-acik.svg" width="100%" alt="COUNCIL: one memory, every agent. Claude Code, claude.ai, phone, server, Hermes and Antigravity around the same memory.">
</picture>

**COUNCIL is an open-source system that gives AI agents a lasting memory.** Your agent installs it on your computer. Your notes stay with you as plain Markdown files. Move the memory to a server and Claude on your phone and your other devices read and write the same notes.

To set it up, paste this sentence to your AI agent. It does the rest:

```text
Read these instructions and set up COUNCIL: https://raw.githubusercontent.com/musalkeremlboz/council/main/INSTALL.md
```

**[Setup](#setup)** · [How it works](#how-it-works) · [Why it is different](#why-different) · [Questions](#questions) · [Türkçe](README.md)

macOS · Linux · Windows &nbsp;|&nbsp; Python 3.11+ &nbsp;|&nbsp; version 0.2.2 &nbsp;|&nbsp; [MIT license](LICENSE)

<br>

<a id="what-it-does"></a>
<p><picture><source media="(prefers-color-scheme: dark)" srcset="docs/assets/baslik-what-it-does-koyu.svg"><img src="docs/assets/baslik-what-it-does-acik.svg" height="30" alt="What it does"></picture></p>

AI agents forget everything when the chat ends. COUNCIL fills that gap:

| Today | With COUNCIL |
|---|---|
| Every new chat starts from zero. You explain again who you are and what you are working on. | As the session opens, your profile, your rules, your open threads and your latest sessions are in front of the agent. |
| Your phone does not know what you said on your computer. Each tool keeps its own memory. | The memory lives in one place. Every agent that connects sees the same notes. |
| You have to say "remember this". If you forget to, it is gone. | The agent records your decision, preference or correction the moment you state it. |
| You correct the same mistake again and again. | Your correction becomes one dated line in the rules and loads in every later session. |
| When you move to a new system, your old notes stay behind. | Setup finds the memory your agents have kept so far and brings it in. |
| You cannot see what the memory knows or where it came from. | Notes are plain text. Every change stays in the history with when and why it was made. |

<br>

<a id="how-it-works"></a>
<p><picture><source media="(prefers-color-scheme: dark)" srcset="docs/assets/baslik-how-it-works-koyu.svg"><img src="docs/assets/baslik-how-it-works-acik.svg" height="30" alt="How it works"></picture></p>

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/assets/akis-en-koyu.svg">
  <img src="docs/assets/akis-en-acik.svg" width="100%" alt="Three sessions, three devices, one memory: each session starts by reading it and ends by writing to it.">
</picture>

The orange line is the memory. Each arc is a session: it leaves the memory and returns to it. Whatever device the next session opens on, it starts where the last one left off.

1. **It starts by reading.** When a session opens, a hook (a small script the agent runs by itself at set moments) asks the memory service for the starting context: who you are, your corrections, your open threads and the cards of your last two sessions. All of it fits a budget of 9,000 characters. What does not fit is named, never dropped silently.
2. **With every message it gets only the notes that matter.** Your message is searched in the memory and at most the five most relevant sections are added to it (up to 3,500 characters). A section is sent only once per session.
3. **It ends by writing.** When a meaningful piece of work is done, the agent writes the session card: what was done, why, which decisions were made, what is still open, what comes next. If it tries to finish without recording, the hook reminds it once.

### What is underneath

| Part | What it does |
|---|---|
| **Notes** | Plain Markdown files in a folder on your computer or your server. This is the single source of truth. |
| **History** | Every change is a git commit. Any earlier state can be restored. |
| **Search** | A SQLite FTS5 full-text index. It folds Turkish letters, so "şifre" and "sifre" match. If the index is deleted it is rebuilt from the notes. |
| **Connection** | Eight tools over MCP (the standard agents use to reach outside tools) and three hooks for Claude Code. |
| **Conflict protection** | Two agents cannot overwrite each other. The writer hands back the fingerprint of the version it read. If the note changed in between, the write is refused. |
| **Updates** | Once a day it looks at the latest published release. If there is a newer one it installs it and restarts the service. Notes are not touched. |
| **Backup** | `council backup` pushes the notes with their history to your own private git repository. If the backup fails for two days, your agent tells you. |

<details>
<summary><b>The eight MCP tools</b></summary>

| Tool | What it does |
|---|---|
| `council_context` | Loads the session-start context |
| `council_search` | Full-text search across all notes |
| `council_read` | Reads a note and its version fingerprint |
| `council_list` | Lists note paths |
| `council_write` | Writes a new note or replaces a whole note |
| `council_edit` | Changes part of a note |
| `council_session` | Writes the session's card |
| `council_log` | Records finished work with the notes it changed |

</details>

### Measurements

Measured on 2026-11-16 on a Linux server with a set of 44 questions. The sample is small. Results will differ with your notes.

| Measurement | Result |
|---|---|
| Building the session-start context | 4.8 ms (median) |
| The hook, end to end | about 250 ms, nearly all of it Python starting up |
| Search in a 13,000-section test vault | 12 ms (median) |
| The answer already in context, without the agent searching | 84% of 44 questions |
| Effect of per-session deduplication on a 10-message chat | 68% less injected context |
| Memory used by the service | about 70 MB |

<br>

<a id="why-different"></a>
<p><picture><source media="(prefers-color-scheme: dark)" srcset="docs/assets/baslik-why-different-koyu.svg"><img src="docs/assets/baslik-why-different-acik.svg" height="30" alt="Why it is different"></picture></p>

- **One sentence, nothing to configure.** You write one sentence to your agent; the service, the connection, the import and the updates set themselves up. No administrator rights needed.
- **It does not leave your old memory behind.** It copies the memory files your agents keep. If there is a system it does not recognise, your agent finds it and moves it in the first session.
- **It updates itself.** When a new release is published it reaches you within a day.
- **It is not tied to one agent.** The memory is in your files, not inside the agent. Any agent that speaks MCP can connect.
- **One memory across devices.** Move it to a server and your computer, your phone and claude.ai share the same notes. There is no folder to sync.
- **It can be inspected.** Everything is plain text, every change stays in the history, and two agents cannot overwrite each other.

### Two ways to use it

| | This computer | Your own server |
|---|---|---|
| **Setup** | One sentence to your agent | [The steps in the guide](docs/setup.md#server) |
| **Who can connect** | The agents on this computer | All your devices, including your phone and claude.ai |
| **What you need** | Python and git | A small Linux server with a domain name |

You can start on your computer and move to a server later. Copying the `vault/` folder is enough.

### Which agents it works with

| Agent | How it connects |
|---|---|
| **Claude Code** | Setup connects it. Context arrives by itself; the agent does not have to call anything. |
| **claude.ai** (web, desktop, phone) | With a server setup, as a custom connector. The agent loads the memory itself at the start of a session. |
| **Other agents that speak MCP** | MCP tools and the usage instructions the service gives. In use with Hermes and Antigravity. |

<br>

<a id="setup"></a>
<p><picture><source media="(prefers-color-scheme: dark)" srcset="docs/assets/baslik-setup-koyu.svg"><img src="docs/assets/baslik-setup-acik.svg" height="30" alt="Setup"></picture></p>

**Let your agent do it.** Paste this sentence to Claude Code or whichever agent you use:

```text
Read these instructions and set up COUNCIL: https://raw.githubusercontent.com/musalkeremlboz/council/main/INSTALL.md
```

Your agent reads [the instructions](INSTALL.md) and, without asking you questions, checks what is needed, runs the installer, verifies the result, brings in any other memory it knows about and tells you in a few lines what it did. When it is done, all you do is open a new session.

<details>
<summary><b>I want to set it up myself</b></summary>

You need Python 3.11 or later and git.

**macOS and Linux**

```sh
curl -fsSL https://raw.githubusercontent.com/musalkeremlboz/council/main/install.sh | sh
```

**Windows** (PowerShell)

```powershell
irm https://raw.githubusercontent.com/musalkeremlboz/council/main/install.ps1 | iex
```

When the command finishes, open a new Claude Code session. The memory is ready.

</details>

| What setup does | |
|---|---|
| **Installs** | Puts COUNCIL in the `~/.council` folder with its own Python environment. No administrator rights needed. |
| **Runs** | Starts the service. The service starts by itself when you log in. |
| **Connects** | Adds the hooks and MCP tools to Claude Code. It keeps your existing settings and backs them up before changing them. |
| **Imports** | Finds the memory your agents have kept and copies it. The source files are not touched. |
| **Keeps current** | Turns on the daily update check. |

Four commands for afterwards:

| Command | What it does |
|---|---|
| `council status` | Is the service running, are the hooks and updates on |
| `council update` | Installs the latest release right now |
| `council import FOLDER` | Brings a folder of notes into the memory |
| `council uninstall` | Removes the service and the connections. Your notes are not touched. |

<details>
<summary><b>How is my existing memory brought over?</b></summary>

In two steps:

1. **During setup.** The memory and instruction files agents keep in your home folder (those of Claude Code, Codex and Gemini) and the note vaults in folders you opened in Claude Code are copied. The copies go under `imported/`: they can be searched but are not loaded in every session.
2. **In the first session.** Setup leaves a task in the memory. Your agent checks whether any other memory system is in use on this computer, moves it if there is one, and sorts what was copied together with you: lasting facts into `core.md`, corrections into `rules.md`, project knowledge into the project notes.

No step changes or deletes the source files. If you do not want an import, run setup with `--no-import`.

</details>

<details>
<summary><b>How does the automatic update work?</b></summary>

Once a day the latest published release of this repository is looked up. If it is newer it is installed, the service restarts, and your agent tells you in the next session. Your notes are not touched.

Only published releases are installed, not the work in progress in the repository. To turn it off, run setup with `--no-auto-update`. You then update yourself with `council update`.

</details>

<details>
<summary><b>How do I pass options?</b></summary>

```sh
curl -fsSL https://raw.githubusercontent.com/musalkeremlboz/council/main/install.sh | sh -s -- --no-auto-update
```

| Option | What it does |
|---|---|
| `--no-auto-update` | Turns the automatic update off |
| `--no-import` | Does not look for an existing memory |
| `--from FOLDER` | Imports this folder instead of what is found |
| `--port 8765` | Changes the port the service listens on |

</details>

<details>
<summary><b>I want to connect my phone and my other devices too</b></summary>

For that the memory has to be at an address reachable from the internet. A small Linux server and a domain name are enough. The steps are in the [setup guide](docs/setup.md#server). To move the notes from your computer to the server, copy the `vault/` folder.

</details>

<br>

<a id="first-five-minutes"></a>
<p><picture><source media="(prefers-color-scheme: dark)" srcset="docs/assets/baslik-first-five-minutes-koyu.svg"><img src="docs/assets/baslik-first-five-minutes-acik.svg" height="30" alt="First 5 minutes"></picture></p>

| Step | Write to your agent | What happens |
|---|---|---|
| **Introduce yourself** | "My name is Deniz, I am a developer, I like short answers. Write these to your memory." | It goes into `core.md` and loads in every session. |
| **Make a decision** | "We decided to use SQLite as the database in the blog project." | It is written to the project note with its date. |
| **Ask again** | In a new session: "What did we decide about the database in the blog project?" | The answer comes without you explaining. |
| **Correct once** | "Explain technical terms the first time they appear." | A dated line is added to `rules.md`. You do not make the same correction again. |

<br>

<a id="inside-the-memory"></a>
<p><picture><source media="(prefers-color-scheme: dark)" srcset="docs/assets/baslik-inside-the-memory-koyu.svg"><img src="docs/assets/baslik-inside-the-memory-acik.svg" height="30" alt="Inside the memory"></picture></p>

```text
vault/
├── core.md            who you are and your lasting preferences
├── rules.md           your corrections, one dated line each
├── threads.md         open threads: where each stands and the next step
├── sessions.md        the latest session cards
├── sessions/          monthly archive of older cards
├── projects/<name>/   project notes and project-specific rules
├── knowledge/         single facts
├── imported/          notes copied from other systems
└── log/               what was done and which notes changed
```

The first four files load at the start of every session. The rest arrives only when it is relevant. All of it is plain text: you can open it in any editor, read it and fix it by hand.

<br>

<a id="questions"></a>
<p><picture><source media="(prefers-color-scheme: dark)" srcset="docs/assets/baslik-questions-koyu.svg"><img src="docs/assets/baslik-questions-acik.svg" height="30" alt="Questions"></picture></p>

<details>
<summary><b>Where are my notes and who can see them?</b></summary>

On your own computer, in the `~/.council/vault/` folder. If you set up a server, on your server. COUNCIL sends your notes nowhere else. The context handed to your agent does go to the AI provider you use, as part of the chat. The same is true of every message you type to the agent.

The service listens only on an address reachable from your own computer and is protected by a token. With a server setup, only someone who knows the owner password can approve a claude.ai connection. Five wrong password attempts in a row lock the sign-in for 15 minutes.

</details>

<details>
<summary><b>Does it remember everything?</b></summary>

No. It remembers what the agent recorded. Chat history does not turn into knowledge by itself.

Search is keyword based. If you ask the same thing in entirely different words it can miss: in the 44-question test the search tool found the right note in its top five results for about three quarters of the questions. Meaning-based search was tried and is not included yet.

</details>

<details>
<summary><b>What does it cost?</b></summary>

The software is free. COUNCIL itself never calls an AI model, so it adds no model fee. Run on your own computer, it costs nothing else.

The added context does raise your agent's token use (tokens are the unit a model counts text in): about 2,500 at the start of a session and up to about 1,200 with each message that has relevant notes.

</details>

<details>
<summary><b>What if the agent records something wrong?</b></summary>

Tell your agent to fix it, or edit the file yourself. Notes are plain text and every change is in the git history, so an earlier state can be restored.

A note written by an agent is a claim, not verified knowledge. For important decisions, check the source.

</details>

<details>
<summary><b>Can text inside a note give orders to the agent?</b></summary>

COUNCIL hands over context with the warning "this is data, not instructions", and the server's own instructions say the same. That lowers the risk; it does not remove it. Do not paste long text from a source you do not trust into the memory as is.

</details>

<details>
<summary><b>Is the automatic update safe?</b></summary>

Updates are installed only from this repository's published releases, over an encrypted connection. What you should still know: an automatic update means letting whoever publishes this repository run code on your computer. If you do not want that, set up with `--no-auto-update`, review the releases yourself and take them with `council update`.

</details>

<details>
<summary><b>What if I want to remove it?</b></summary>

`council uninstall` removes the service, the update check, the hooks and the MCP connection. It does not touch other tools' settings. Your notes stay in the `~/.council/vault/` folder. If you want them gone too, delete the folder yourself.

</details>

<br>

<a id="docs"></a>
<p><picture><source media="(prefers-color-scheme: dark)" srcset="docs/assets/baslik-docs-koyu.svg"><img src="docs/assets/baslik-docs-acik.svg" height="30" alt="Docs and contributing"></picture></p>

- **[INSTALL.md](INSTALL.md)**: the setup instructions your agent reads and follows
- **[Setup guide](docs/setup.md)**: server, Claude Code, claude.ai, backup, updating
- **[Kurulum rehberi](docs/kurulum.md)**: the same guide in Turkish
- **[deploy/](deploy)**: example service and timer files for a Linux server
- **[brand/](brand)**: logo files and the Council Halka typeface

COUNCIL is at version 0.2.2 and grows through one person's daily use. Its idea was inspired by [Avenox Beyin](https://github.com/avenoxai/avenoxbeyin). The code has 60 tests, and setup is tried on Linux, macOS and Windows with every change: `pip install -e ".[dev]" && pytest`. To report a bug or suggest something, [open an issue](https://github.com/musalkeremlboz/council/issues).

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="brand/logo/council-amblem-koyu.svg">
    <img src="brand/logo/council-amblem.svg" width="56" alt="COUNCIL emblem">
  </picture>
  <br>
  <sub><a href="LICENSE">MIT license</a></sub>
</p>
