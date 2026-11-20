<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/assets/kapak-en-koyu.svg">
  <img src="docs/assets/kapak-en-acik.svg" width="100%" alt="COUNCIL: one memory, every agent. Claude Code, claude.ai, phone, server, Hermes and Antigravity around the same memory.">
</picture>

**COUNCIL is an open-source, self-hosted system that gives AI agents a lasting memory.** Your notes are plain Markdown files. Claude Code on your computer, Claude on your phone and the agents on your server all read and write the same notes. A decision you make on one device is there in the chat you open on another.

**[Go to setup](#setup)** · [How it works](#how-it-works) · [Why it is different](#why-different) · [Questions](#questions) · [Türkçe](README.md)

Python 3.11+ &nbsp;|&nbsp; MCP &nbsp;|&nbsp; version 0.1.0 &nbsp;|&nbsp; [MIT license](LICENSE)

<a id="what-it-does"></a>
<h2><picture><source media="(prefers-color-scheme: dark)" srcset="docs/assets/baslik-what-it-does-koyu.svg"><img src="docs/assets/baslik-what-it-does-acik.svg" height="30" alt="What it does"></picture></h2>

AI agents forget everything when the chat ends. COUNCIL fills that gap:

| Today | With COUNCIL |
|---|---|
| Every new chat starts from zero. You explain again who you are and what you are working on. | As the session opens, your profile, your rules, your open threads and your latest sessions are in front of the agent. |
| Your phone does not know what you said on your computer. Each tool keeps its own memory. | The memory lives in one place. Every agent that connects sees the same notes. |
| You have to say "remember this". If you forget to, it is gone. | The agent records your decision, preference or correction the moment you state it. |
| You correct the same mistake again and again. | Your correction becomes one dated line in the rules and loads in every later session. |
| You cannot see what the memory knows or where it came from. | Notes are plain text. Every change stays in the history with when and why it was made. |

<a id="how-it-works"></a>
<h2><picture><source media="(prefers-color-scheme: dark)" srcset="docs/assets/baslik-how-it-works-koyu.svg"><img src="docs/assets/baslik-how-it-works-acik.svg" height="30" alt="How it works"></picture></h2>

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/assets/akis-en-koyu.svg">
  <img src="docs/assets/akis-en-acik.svg" width="100%" alt="Three sessions, three devices, one memory: each session starts by reading it and ends by writing to it.">
</picture>

The orange line is the memory. Each arc is a session: it leaves the memory and returns to it. Whatever device the next session opens on, it starts where the last one left off.

1. **It starts by reading.** When a session opens, a hook (a small script the agent runs by itself at set moments) asks the server for the starting context: who you are, your corrections, your open threads and the cards of your last two sessions. All of it fits a budget of 9,000 characters. What does not fit is named, never dropped silently.
2. **With every message it gets only the notes that matter.** Your message is searched in the memory and at most the five most relevant sections are added to it (up to 3,500 characters). A section is sent only once per session.
3. **It ends by writing.** When a meaningful piece of work is done, the agent writes the session card: what was done, why, which decisions were made, what is still open, what comes next. If it tries to finish without recording, the hook reminds it once.

### What is underneath

| Part | What it does |
|---|---|
| **Notes** | Plain Markdown files in a folder on the server. This is the single source of truth. |
| **History** | Every change is a git commit. Any earlier state can be restored. |
| **Search** | A SQLite FTS5 full-text index. It folds Turkish letters, so "şifre" and "sifre" match. If the index is deleted it is rebuilt from the notes. |
| **Connection** | Eight tools over MCP (the standard agents use to reach outside tools) and three hooks for Claude Code. |
| **Conflict protection** | Two agents cannot overwrite each other. The writer hands back the fingerprint of the version it read. If the note changed in between, the write is refused. |
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

Measured on 2026-11-16 on our own server with a set of 44 questions. The sample is small. Results will differ with your notes.

| Measurement | Result |
|---|---|
| Building the session-start context on the server | 4.8 ms (median) |
| The hook, end to end | about 250 ms, nearly all of it Python starting up |
| Search in a 13,000-section test vault | 12 ms (median) |
| The answer already in context, without the agent searching | 84% of 44 questions |
| Effect of per-session deduplication on a 10-message chat | 68% less injected context |
| Memory used by the service | about 70 MB |

<a id="why-different"></a>
<h2><picture><source media="(prefers-color-scheme: dark)" srcset="docs/assets/baslik-why-different-koyu.svg"><img src="docs/assets/baslik-why-different-acik.svg" height="30" alt="Why it is different"></picture></h2>

Most memory systems live in a folder on one computer. COUNCIL puts the memory on a server. The differences follow from that:

| | Memory in a local folder | COUNCIL |
|---|---|---|
| **Where it lives** | On one computer | On your own server, in one place |
| **Phone and web** | Usually out of reach | claude.ai and the phone app connect with a password-protected sign-in |
| **Several devices** | You have to sync the folder | All connect to the same server; nothing to sync |
| **Two agents writing at once** | Files can conflict | Version check and a write lock protect them |
| **Server and internet** | Not needed | Needed |

The last row is the price of COUNCIL: it wants a small server that is always on. If you use one tool on one computer, a local system is simpler. [Avenox Beyin](https://github.com/avenoxai/avenoxbeyin) is a good example of one, and COUNCIL took its idea from it. If you are coming from there, `council import-avenox` moves your notes.

### Which agents it works with

| Agent | How it connects |
|---|---|
| **Claude Code** (macOS, Linux) | MCP and hooks. Context arrives by itself; the agent does not have to call anything. |
| **claude.ai** (web, desktop, phone) | Custom connector. The agent loads the memory itself at the start of a session. |
| **Other agents that speak MCP** | MCP tools and the usage instructions the server gives. In use with Hermes and Antigravity. |

Not tried on Windows. The server side needs Linux or macOS.

<a id="setup"></a>
<h2><picture><source media="(prefers-color-scheme: dark)" srcset="docs/assets/baslik-setup-koyu.svg"><img src="docs/assets/baslik-setup-acik.svg" height="30" alt="Setup"></picture></h2>

You need Python 3.11 or later and git. For several devices, a small Linux server with a domain name.

**The easiest way is to let your agent do the setup.** Paste this message into Claude Code:

```text
Read https://github.com/musalkeremlboz/council/blob/main/docs/setup.md and set up COUNCIL.
Use this computer as the server. When you are done, write a test note to the memory and
verify it by reading it back in a new session.
```

If you have a server, change the second line to "Server: this address I reach over ssh: ...".

<details>
<summary><b>I want to set it up myself</b></summary>

**1. Start the server**

```sh
pip install git+https://github.com/musalkeremlboz/council
council token     # creates and prints the access token
council serve     # runs on 127.0.0.1:8765
```

**2. Connect Claude Code**

```sh
claude mcp add --scope user --transport http council http://127.0.0.1:8765/mcp \
  --header "Authorization: Bearer YOUR_TOKEN"
```

For context to arrive by itself you need three hooks. The steps are in the [setup guide](docs/setup.md#claude-code).

**3. Connect your phone and claude.ai**

If your server is published over HTTPS with a domain name, add `https://your-domain/mcp` as a custom connector in the claude.ai settings. While connecting you are asked for the owner password you set with `council set-password`.

Every step, server setup and backup: **[docs/setup.md](docs/setup.md)**

</details>

<a id="first-five-minutes"></a>
<h2><picture><source media="(prefers-color-scheme: dark)" srcset="docs/assets/baslik-first-five-minutes-koyu.svg"><img src="docs/assets/baslik-first-five-minutes-acik.svg" height="30" alt="First 5 minutes"></picture></h2>

| Step | Write to your agent | What happens |
|---|---|---|
| **Introduce yourself** | "My name is Deniz, I am a developer, I like short answers. Write these to your memory." | It goes into `core.md` and loads in every session. |
| **Make a decision** | "We decided to use SQLite as the database in the blog project." | It is written to the project note with its date. |
| **Ask from elsewhere** | In a new session, on another device if you can: "What did we decide about the database in the blog project?" | The answer comes without you explaining. |
| **Correct once** | "Explain technical terms the first time they appear." | A dated line is added to `rules.md`. You do not make the same correction again. |

<a id="inside-the-memory"></a>
<h2><picture><source media="(prefers-color-scheme: dark)" srcset="docs/assets/baslik-inside-the-memory-koyu.svg"><img src="docs/assets/baslik-inside-the-memory-acik.svg" height="30" alt="Inside the memory"></picture></h2>

```text
vault/
├── core.md            who you are and your lasting preferences
├── rules.md           your corrections, one dated line each
├── threads.md         open threads: where each stands and the next step
├── sessions.md        the latest session cards
├── sessions/          monthly archive of older cards
├── projects/<name>/   project notes and project-specific rules
├── knowledge/         single facts
└── log/               what was done and which notes changed
```

The first four files load at the start of every session. The rest arrives only when it is relevant. All of it is plain text: you can open it in any editor, read it and fix it by hand.

<a id="questions"></a>
<h2><picture><source media="(prefers-color-scheme: dark)" srcset="docs/assets/baslik-questions-koyu.svg"><img src="docs/assets/baslik-questions-acik.svg" height="30" alt="Questions"></picture></h2>

<details>
<summary><b>Where are my notes and who can see them?</b></summary>

In the `vault/` folder on your own server. COUNCIL sends your notes nowhere else. The context handed to your agent does go to the AI provider you use, as part of the chat. The same is true of every message you type to the agent.

Access to the server is protected by a token. Only someone who knows the owner password can approve a claude.ai connection. Five wrong password attempts in a row lock the sign-in for 15 minutes.

</details>

<details>
<summary><b>Does it remember everything?</b></summary>

No. It remembers what the agent recorded. Chat history does not turn into knowledge by itself.

Search is keyword based. If you ask the same thing in entirely different words it can miss: in the 44-question test the search tool found the right note in its top five results for about three quarters of the questions. Meaning-based search was tried and is not included yet.

</details>

<details>
<summary><b>What does it cost?</b></summary>

The software is free. COUNCIL itself never calls an AI model, so it adds no model fee. Your cost is the server.

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
<summary><b>I have no server. Can I still use it?</b></summary>

Yes. Run `council serve` on your own computer. Then only the agents on that computer can connect. To move to a server later, copying the `vault/` folder is enough.

</details>

<details>
<summary><b>I use Avenox Beyin. Can I bring my notes?</b></summary>

```sh
council import-avenox /path/to/vault --dry-run   # shows what would be imported
council import-avenox /path/to/vault             # imports; the source folder is not touched
```

Tried with an Avenox Beyin V3 vault.

</details>

<a id="docs"></a>
<h2><picture><source media="(prefers-color-scheme: dark)" srcset="docs/assets/baslik-docs-koyu.svg"><img src="docs/assets/baslik-docs-acik.svg" height="30" alt="Docs and contributing"></picture></h2>

- **[Setup guide](docs/setup.md)**: server, Claude Code, claude.ai, backup, updating
- **[Kurulum rehberi](docs/kurulum.md)**: the same guide in Turkish
- **[deploy/](deploy)**: example service and timer files for a Linux server
- **[brand/](brand)**: logo files and the Council Halka typeface

COUNCIL is at version 0.1.0 and grows through one person's daily use. The code has 39 tests: `pip install -e ".[dev]" && pytest`. To report a bug or suggest something, [open an issue](https://github.com/musalkeremlboz/council/issues).

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="brand/logo/council-amblem-koyu.svg">
    <img src="brand/logo/council-amblem.svg" width="56" alt="COUNCIL emblem">
  </picture>
  <br>
  <sub><a href="LICENSE">MIT license</a></sub>
</p>
