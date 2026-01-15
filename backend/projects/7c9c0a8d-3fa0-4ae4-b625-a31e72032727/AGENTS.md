## APPAM OpenCode Agent Instructions

You are operating inside a bioinformatics container with all tools installed.
Always work inside the current project directory unless explicitly told otherwise.

Core behavior:
- Prefer running real commands to confirm facts instead of guessing.
- Use relative paths within the project and create output directories when needed.
- Keep commands reproducible and explain results concisely.
- Avoid destructive actions unless the user explicitly asks.

Bioinformatics specifics:
- Verify input files exist and match expected formats before running tools.
- Use explicit parameters and record the final command you ran.
- For long-running jobs, note expected runtime and resource usage.

If the user asks for parameter settings, reason from file types and sizes found in the project.