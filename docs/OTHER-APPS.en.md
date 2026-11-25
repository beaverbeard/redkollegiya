# Redkollegiya: setup in other apps

This guide installs the selected skill. Setup depends on the app. The source location is `.claude/skills/redkollegiya/`. Keep instructions, scripts and resources together; verify paths and tool names when moving the skill.

```text
Install the Redkollegiya skill:
https://github.com/beaverbeard/redkollegiya

Use it whenever we write or edit texts.
```

## Claude Code

Send the instruction above in agent chat. Use the project’s `.claude/skills/redkollegiya/` or personal `~/.claude/skills/redkollegiya/`. Keep SKILL.md and its resources together.

## Codex

In Codex CLI, its IDE extension or a local ChatGPT Desktop project, send the instruction above. Use project `.agents/skills/redkollegiya/` or personal `~/.agents/skills/redkollegiya/`. Avoid duplicate copies. Restart the session if the skill is missing from the list.

## Cursor

Open the project and use Agent chat. Copy the complete skill folder to either `.cursor/skills/redkollegiya/` or `.agents/skills/redkollegiya/`, not both. Start a new session and ask for the skill by name. A repository link alone is not a ready marketplace plugin.

## Copilot

In GitHub Copilot in VS Code, choose Agent mode. Project skills use `.github/skills/redkollegiya/`; personal skills use `~/.copilot/skills/redkollegiya/`. Start a fresh chat and verify instructions and resources. This is GitHub Copilot, not Microsoft Copilot chat.

## Gemini CLI

Send the instruction above. Use project `.gemini/skills/redkollegiya/` or `.agents/skills/redkollegiya/`, or personal `~/.gemini/skills/redkollegiya/`. The CLI also provides `gemini skills install` with `--path`. Check `gemini skills list` and refresh the session.

## ChatGPT

For local ChatGPT Desktop skills, use the Codex section. In a browser, create a project and add the instructions and text resources from the extracted [skill package](downloads/redkollegiya.zip). Ask the project to use Redkollegiya and verify tools before working. For scripted stages, provide the original .py files to an available execution environment and ask to see commands and results. Uploaded context does not install a local skill or establish that scripts ran.

## Claude

Enable Code execution and file creation / Create and edit files in Settings → Capabilities. Upload the [skill ZIP](downloads/redkollegiya.zip) in Customize → Skills → Create skill → Upload a skill, then enable it. If metadata is rejected, adapt a copy to the current format while keeping the original. Organization settings may restrict custom skills.

## Gemini

On the web or Mac, use Customize → Skills → Create → Upload and select the [skill ZIP](downloads/redkollegiya.zip). Review and activate it. Keep SKILL.md and resources in a folder matching the skill name. Personal accounts are transitioning from Gems to Skills in November 2026; work and education follow later. Gemini Apps scripts cannot make external requests; source search depends on the app’s tools.

## Readiness

Ask the agent to show where it reads the skill and resources and how required stages run. Fact-checking needs source access; automatic replacements and typography need actual Python execution. Check paths and tool names against the current app. Setup does not require buying an API key; use your available tools and subscription.

The complete Redkollegiya workflow needs the other family tools. Do not claim a missing stage ran; the whole-toolkit installation prompt is at the end of this guide.

## The whole Redkollegiya toolkit

For the complete workflow, install [Redkollegiya](https://github.com/beaverbeard/redkollegiya) with all eight skills:

```text
Install Redkollegiya and the complete set of eight editorial skills:
https://github.com/beaverbeard/redkollegiya

Use them whenever we write or edit texts.
```

[Complete source kit](downloads/editorial-skill-sources.zip)

## Sources and check date

2026-11-24.

- [claude-code](https://code.claude.com/docs/en/skills)
- [codex](https://learn.chatgpt.com/docs/build-skills)
- [cursor](https://cursor.com/docs/skills)
- [copilot](https://code.visualstudio.com/docs/agent-customization/agent-skills)
- [gemini-cli](https://geminicli.com/docs/cli/skills/)
- [claude](https://support.claude.com/en/articles/12512180-use-skills-in-claude)
- [chatgpt](https://help.openai.com/en/articles/10169521-projects-in-chatgpt)
- [gemini](https://support.google.com/gemini/answer/17094296)
- [gemini-transition](https://support.google.com/gemini/answer/18560919)

[Back](../README.en.md)
