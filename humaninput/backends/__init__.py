"""Event stream consumers. Each backend module exposes a `render`/`play`
entry point and only imports its optional third-party dependency lazily,
inside that function, so `import humaninput.backends` never fails.
"""
