# Setup

The environment is already built. This file records how, and how to use it.

## Python

Python 3.13 is installed at:

```
C:\Users\isaia\AppData\Local\Programs\Python\Python313\python.exe
```

**It is not on your PATH.** Typing `python` hits the Windows Store stub instead, which
prints "Python was not found". Two ways to fix that permanently:

1. Settings → Apps → Advanced app settings → App execution aliases → turn off
   **python.exe** and **python3.exe**. Then reopen your terminal.
2. Or re-run the Python installer and tick "Add python.exe to PATH".

Until then, use the virtual environment below, which sidesteps the problem entirely.

## Virtual environment

Already created at `.venv` with `anthropic` 1.7.0 installed. Activate it:

```
.venv\Scripts\activate
```

Once active, plain `python` works. To rebuild it from scratch:

```
"%LOCALAPPDATA%\Programs\Python\Python313\python.exe" -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Claude API key

Needed only for `summarize`. `fetch`, `review`, and `build` work without it.

```
setx ANTHROPIC_API_KEY "sk-ant-..."
```

Reopen the terminal afterwards for `setx` to take effect.

## Running it

```
python -m app.cli fetch
python -m app.cli summarize --limit 3
python -m app.cli review
python -m app.cli build
```

Then open `outputs/site/index.html`.

`python -m app.cli status` shows where everything stands at any point.

## Tests

```
python -m unittest discover tests
```

13 tests, no network calls and no API calls. All passing as of 2026-09-20.

## Notes

- Start with `--limit 3` on your first `summarize` run. Read what comes back before
  spending money on a full batch.
- The database is `app/data/digest.db`. Back it up — it holds every approved summary.
- `outputs/site/` is regenerated on every `build`. Do not edit it by hand.
