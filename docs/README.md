# BrightLoop documentation

BrightLoop (code name *Company Brain*) is a hackathon prototype: a Telegram bot that watches a
team's work, keeps a memory that team leads curate, and checks new work against the decisions
the team approved. The [project README](../README.md) is the short introduction; these pages
cover how the application is built and how to work on it.

| Page | Read it to learn |
|---|---|
| [Architecture](architecture.md) | The three programs, how they talk, where state lives, the design principles. |
| [Backend](backend.md) | The Brain module by module: access rules, answers, brief, watcher, actions, model and voice. |
| [API reference](api.md) | Every endpoint, its headers, request and response shapes, and its errors. |
| [Data model and seed](data.md) | People, sources, memory items, actions, the demo script and the fictional company. |
| [Telegram bot](bot.md) | How the bot ties chats to people, delivers messages and handles buttons. |
| [Control room](control-room.md) | The web page shown next to Telegram during the demo. |
| [Development](development.md) | Setup, configuration, running, tests, mock mode, recording the demo video. |

## Elsewhere in the repository

| Path | What it is |
|---|---|
| [`demo-video/demo.md`](../demo-video/demo.md) | The 9-step demo script, used as the acceptance test. |
| [`demo-video/pitch.md`](../demo-video/pitch.md) | The 3-minute pitch, demo included. |
| [`docs/plans/`](plans/README.md) | The development plans written during the hackathon: the original specification, the handover, the task lists and the work logs of the agents that built each piece. |
