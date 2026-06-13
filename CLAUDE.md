<!-- GSD:project-start source:PROJECT.md -->
## Project

**DataAgent**

Agent analyste data autonome. Tu poses une question business en langage naturel (« Quel est le CA par mois ? », « Les retards de livraison plombent-ils les avis ? »), l'agent planifie, query la data, croise les sources, et sort un rapport markdown sourcé avec visualisations. Projet portfolio (Labs SolidScale) à but d'apprentissage : agentic AI + data engineering moderne.

**Core Value:** Une question business en langage naturel produit un rapport correct, sourcé et visualisé — sans intervention humaine dans la boucle d'analyse.

### Constraints

- **Tech stack**: LangGraph v1.0, `StateGraph` manuel — la doc recommande le StateGraph manuel dès qu'on a parallel nodes/supervisor/retry custom/branching ; la critic loop coche tout.
- **Tech stack**: DuckDB + Polars pour query/transform, plotly + kaleido pour viz, FastAPI + uvicorn pour l'API.
- **LLM**: Gemini via `langchain-google-genai` — Flash (planner/router/critic, cheap+rapide), Pro (synthesizer, qualité rapport). Clé `GEMINI_API_KEY` via `.env`. Décision révisée 2026-06-13 (pas de clé Anthropic ; Claude figé au plan initial).
- **Coût**: `max_iterations` hard stop dans le state dès J2 — empêche boucle critic infinie.
- **Tests**: vraie I/O DuckDB sur fixtures synthétiques, jamais de mock I/O ; pytest + dataset 10 Q/R pour l'eval.
<!-- GSD:project-end -->

<!-- GSD:stack-start source:STACK.md -->
## Technology Stack

Technology stack not yet documented. Will populate after codebase mapping or first phase.
<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->
## Conventions

Conventions not yet established. Will populate as patterns emerge during development.
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->
## Architecture

Architecture not yet mapped. Follow existing patterns found in the codebase.
<!-- GSD:architecture-end -->

<!-- GSD:skills-start source:skills/ -->
## Project Skills

No project skills found. Add skills to any of: `.claude/skills/`, `.agents/skills/`, `.cursor/skills/`, or `.github/skills/` with a `SKILL.md` index file.
<!-- GSD:skills-end -->

<!-- GSD:workflow-start source:GSD defaults -->
## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:
- `/gsd-quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd-debug` for investigation and bug fixing
- `/gsd-execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->



<!-- GSD:profile-start -->
## Developer Profile

> Profile not yet configured. Run `/gsd-profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
