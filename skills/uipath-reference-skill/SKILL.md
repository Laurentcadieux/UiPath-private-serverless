---
name: "uipath-reference-skill"
description: "Expose uploaded UiPath reference skills as a reusable OpenClaw skill"
---

# UiPath Reference Skill

This skill provides programmatic access to the UiPath reference documentation and templates uploaded in the workspace. It loads the markdown and JSON files from the `skills/uipath-*/` directories, indexes them, and offers commands to query or retrieve specific reference sections.

## Features
- **list-skills** – enumerates available UiPath skill modules
- **get-skill <name>** – returns the markdown/JSON for a specific skill
- **search-references <query>** – finds relevant sections across all uploaded references
- **export-sdd <template>** – outputs a selected SDD template as a ready‑to‑use BPMN file

The skill can be invoked by agents to enrich automations with up‑to‑date UiPath best‑practice guidance, validate process designs against reference patterns, or generate starter templates directly from the stored artifact set.
