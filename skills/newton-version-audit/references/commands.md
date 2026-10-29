# Commands and evidence transfer

`AUDIT` means the absolute path to `scripts/newton_version_audit.py` in this skill. Quote paths with spaces. Collection output must be outside the audited Newton source directory. Python 3.10+ is supported; the MCP distribution itself uses Python 3.12.

## Local source tree

```console
python AUDIT collect --source /path/to/newton-checkout --out /path/to/evidence/target.json
python AUDIT compare --knowledge-root /path/to/newton-knowledge --target /path/to/evidence/target.json --out /path/to/reports/audit.json
```

The source path can be a repository containing `newton/` or the installed `newton` package directory. Repository scans include visible source files except caches, environments and generated build directories. Package-directory scans cover `newton/**` only; missing repository docs/pyproject are outside scope, not deletions.

## Another computer / installed environment

Copy only `newton_version_audit.py` to that computer and use the Python interpreter that actually runs Newton:

```console
/path/to/target-env/bin/python newton_version_audit.py collect --installed --out target-newton.json
```

Windows example:

```powershell
& 'C:\sim env\.venv\Scripts\python.exe' 'C:\audit\newton_version_audit.py' collect --installed --out 'C:\audit\target-newton.json'
```

Return the JSON to the knowledge-base computer and run `compare`. The script resolves the top-level package without importing it, and records distribution metadata separately from source-declared version. It removes its own script directory from import lookup and includes the current directory, matching normal `python -c` precedence. Launch from the application's working directory. Custom application startup changes to module lookup still need inspection.

Installed versions collected: Newton, Warp, MuJoCo, MuJoCo-Warp, NumPy and SciPy. An absent optional dependency is a fact, not a universal failure. GPU/driver capability and effective runtime defaults are untested.

## Version string only

```console
python AUDIT compare --knowledge-root /path/to/newton-knowledge --target-version 1.4.0 --out /path/to/reports/version-only.json
```

This produces `evidence_incomplete`, never a compatibility approval. Collect actual evidence or retrieve the exact official source ref next.

## Outputs and invariants

- Collection produces checksum-protected JSON without absolute machine paths or full source-file contents. Compare produces detailed JSON and adjacent Markdown. Neither is an automatic migration patch.
- Exit 0 means a report was produced, **not** that compatibility passed. Read `status` and `runtime_compatibility`. Invalid inputs, baseline integrity failures and existing output paths exit 2.
- Parse failures, including unsupported newer Python grammar, are evidence gaps rather than API removals. Use a suitable target interpreter.
- Baseline verification covers pointer, snapshot files/programs, source-lock digest and locked source bytes; portable releases also verify `package-manifest.json`. Historical absolute paths are not used.
- Existing `knowledge-base/scripts/maintain.py inventory/compare` can supplement the audit with registry-based public-symbol resolution when a full checkout is available. Use fresh output paths; avoid mutating maintenance commands during an audit. Static defaults from either script are not backend-effective defaults.
