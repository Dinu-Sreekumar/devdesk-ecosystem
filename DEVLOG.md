# DevDesk Incident & Debugging Log (`DEVLOG.md`)

This journal documents real engineering hurdles, root causes, and architectural takeaways encountered during the development of the DevDesk ecosystem, adhering to the failure-driven development paradigm.

---

### [2026-09-30] - POSIX XDG Path Resolver Double-Dot Nesting
* **Symptoms:** Configuration directory was resolving to `~/.config/.devdesk` instead of the expected `~/.config/devdesk`.
* **Root Cause:** In `shared/config.py`, the fallback was hardcoded as `Path.home() / ".config" / ".devdesk"`. Because `.config` is already a hidden top-level directory in `$HOME`, adding another dot to `.devdesk` created redundant hidden nesting.
* **Resolution:** Normalized the path in `get_config_dir()` to `Path.home() / ".config" / "devdesk"`.
* **Key Takeaway:** Under the Linux XDG Base Directory specification, only top-level dotfiles in `$HOME` carry a leading dot. Directories placed inside `$XDG_CONFIG_HOME` (`~/.config`) and `$XDG_DATA_HOME` (`~/.local/share`) should be clean directory names without dot prefixes.

---

### [2026-10-01] - Python Single-Item Tuple Evaluation in SQLite Queries
* **Symptoms:** Executing `delete_snippet()` raised a `TypeError: parameters are of unsupported type`.
* **Root Cause:** In Python, parentheses around a single variable without a trailing comma evaluate as a grouped expression: `(snippet_id)` evaluates to a raw `int`, not a 1-element tuple. Python's `sqlite3.Cursor.execute()` requires a sequence (tuple or list) for parameterized `?` bindings.
* **Resolution:** Added a trailing comma: `cursor = conn.execute("DELETE FROM snippets WHERE id = ?", (snippet_id,))`.
* **Key Takeaway:** A 1-element tuple in Python must always be defined with a trailing comma: `(val,)`.

---

### [2026-10-09] - Python Module Resolution Failure when Invoked from Subdirectories
* **Symptoms:** Running `python3 -m snippetvault.src.main list` from inside `snippetvault/src/` failed with:
  ```text
  ModuleNotFoundError: No module named 'snippetvault'
  ```
* **Root Cause:** When running Python with `-m <module>`, Python prepends the current working directory to `sys.path`. When the working directory was `snippetvault/src/`, Python looked for a subdirectory named `snippetvault` inside `src/` which did not exist.
* **Resolution:** Re-centered the working directory to the project repository root (`/home/dinusreekumar/Projects/devdesk-ecosystem`) where the top-level packages (`shared`, `snippetvault`, `netwatch`, `workpulse`) are located.
* **Key Takeaway:** In Python monorepos without editable wheel installations (`pip install -e .`), module execution with `-m` must always be executed from the project root.

---

### [2026-10-09] - Interactive Bash History Expansion Trap (`!`)
* **Symptoms:** Executing CLI commands with double-quoted strings like:
  ```bash
  python3 -m snippetvault.src.main save "Hello" "print('Hello World!')"
  ```
  abruptly aborted before running Python with:
  ```text
  bash: !': event not found
  ```
* **Root Cause:** In interactive Bash shells, the exclamation mark `!` inside double quotes (`"..."`) triggers `csh`-style history expansion (it attempts to look up a past command in `.bash_history` starting with `!'`).
* **Resolution:** Wrapped strings in single quotes `'...'` where history expansion is disabled, or omitted/escaped the exclamation mark.
* **Key Takeaway:** Never use unescaped `!` inside double quotes in interactive shell pipelines. Prefer single quotes for arbitrary code payloads.

---

### [2026-10-11] - Rich Console Markup Leakage in `Text.append()`
* **Symptoms:** The live WorkPulse focus countdown displayed literal markup tags on the terminal screen:
  ```text
  [bold green]Dev Server Running on port(s): 8000[/bold green]
  ```
  instead of rendering colored text.
* **Root Cause:** In the Rich library, `rich.text.Text.append()` treats its first argument as raw literal text by design and purposefully ignores markup tags to prevent unintended style injections.
* **Resolution:** Extracted the styling out of the string content and passed it to the keyword argument:
  ```python
  content.append("Dev Server Running on port(s): 8000\n\n", style="bold green")
  ```
* **Key Takeaway:** When building Rich text programmatically, use `style="..."` in `.append()`, or explicitly parse strings via `Text.from_markup(...)`.

---

### [2026-10-11] - Shell Redirection Collision with Documentation Placeholders
* **Symptoms:** Attempting to run:
  ```bash
  echo "..." | python3 -m snippetvault.src.main save "Snippet" --session <SESSION_ID>
  ```
  caused Bash to report missing files or unexpected redirection behavior.
* **Root Cause:** `<` and `>` in Bash are input/output redirection operators. `<SESSION_ID>` instructed the shell to open a file named `SESSION_ID` as stdin, colliding with the piped stdin stream.
* **Resolution:** Substituted the active SQLite session identifier string (`20261011-d1aebe`) in place of the documentation placeholder.
* **Key Takeaway:** In CLI manuals, use `$SESSION_ID` or replace `<...>` placeholders with actual string values to prevent shell redirection errors.

---

### [2026-10-13] - Uvicorn Dynamic String Import Failure in Frozen PyInstaller Binaries
* **Symptoms:** Running `vault serve` or `netwatch serve` exited immediately with:
  ```text
  ERROR: Error loading ASGI app. Could not import module "snippetvault.src.server".
  ```
* **Root Cause:** When `uvicorn.run("snippetvault.src.server:app", ...)` is called with a string import path, Uvicorn dynamically invokes `importlib.import_module()`. Inside a frozen PyInstaller binary (and when not explicitly in `PYTHONPATH`), Python does not find a loose folder on disk corresponding to that string path.
* **Resolution:** Updated both CLI `serve` commands to import and pass the instantiated FastAPI ASGI app object directly (`from snippetvault.src.server import app as server_app; uvicorn.run(server_app, ...)`).
* **Key Takeaway:** In compiled or frozen Python environments, avoid passing string module paths to ASGI/WSGI servers; pass the instantiated application object directly.
