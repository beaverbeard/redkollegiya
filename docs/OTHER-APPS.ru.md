# Редколлегия: подключение в других приложениях

Эта инструкция устанавливает выбранный скилл. Способ подключения зависит от приложения. Исходная папка в репозитории: `.claude/skills/redkollegiya/`. Сохраняйте инструкции, скрипты и ресурсы вместе. При переносе нужно проверить пути и названия инструментов.

```text
Установи скилл «Редколлегия»:
https://github.com/beaverbeard/redkollegiya

Используй его, когда мы пишем или редактируем тексты.
```

## Claude Code

Отправьте команду выше в чат агента. Скилл можно разместить в `.claude/skills/redkollegiya/` проекта или в `~/.claude/skills/redkollegiya/` для личной установки. Проверьте наличие SKILL.md и всех ресурсов рядом с ним.

## Codex

В Codex CLI, расширении IDE или локальном проекте ChatGPT Desktop отправьте команду выше. Проектная папка — `.agents/skills/redkollegiya/`, личная — `~/.agents/skills/redkollegiya/`. Не дублируйте скилл в нескольких местах. Если он не появился в списке, перезапустите сессию.

## Cursor

Откройте проект в Cursor и отправьте команду в чат Agent. Полную папку скилла можно разместить в `.cursor/skills/redkollegiya/` или `.agents/skills/redkollegiya/`. Выберите одно место, начните новую сессию и попросите использовать скилл по имени. Простая ссылка на репозиторий не является готовым плагином marketplace.

## Copilot

В GitHub Copilot в VS Code выберите режим Agent. Проектная папка скилла — `.github/skills/redkollegiya/`, личная — `~/.copilot/skills/redkollegiya/`. После подключения начните новый чат и проверьте, что агент читает нужные инструкции и ресурсы. Это инструкция для GitHub Copilot, не для обычного чата Microsoft Copilot.

## Gemini CLI

Отправьте команду выше. Папки скиллов — `.gemini/skills/redkollegiya/` или `.agents/skills/redkollegiya/` проекта; для личной установки — `~/.gemini/skills/redkollegiya/`. CLI также поддерживает `gemini skills install` с `--path` для папки внутри репозитория. Проверьте `gemini skills list` и обновите сессию.

## ChatGPT

Для локальных скиллов в ChatGPT Desktop используйте раздел Codex. В браузере создайте проект, распакуйте [пакет скилла](downloads/redkollegiya.zip) и добавьте инструкции и текстовые ресурсы. В инструкции проекта попросите использовать скилл «Редколлегия» и проверять доступность инструментов перед работой. Для скриптовых этапов передайте исходные .py в доступную среду выполнения и попросите показать команду и результат. Файлы проекта сами по себе не устанавливают локальный скилл и не подтверждают запуск скриптов.

## Claude

В Settings → Capabilities включите Code execution and file creation / Create and edit files. Скачайте [пакет скилла](downloads/redkollegiya.zip) и загрузите ZIP целиком в Customize → Skills → Create skill → Upload a skill. Включите скилл. Если метаданные не принимаются, адаптируйте копию пакета к требованиям приложения, сохранив оригинал. В командном аккаунте создание скиллов может быть ограничено администратором.

## Gemini

В браузере или приложении на Mac откройте Customize → Skills → Create → Upload и загрузите [ZIP скилла](downloads/redkollegiya.zip). Проверьте импорт и включите скилл. SKILL.md и ресурсы должны находиться в папке с именем скилла. Доступность раздела зависит от аккаунта: личные аккаунты переходят от Gems к Skills в ноябре 2026, рабочие и учебные — позднее. Скрипты Gemini Apps не могут выполнять внешние запросы; поиск источников нужно проверять через инструменты самого приложения.

## Readiness

Попросите агента показать, откуда прочитан скилл, доступны ли ресурсы и как запускаются нужные этапы. Для фактчекинга нужен доступ к источникам; для автоматических замен и типографики — реальный запуск Python. Имена инструментов и пути исходной среды требуют проверки в выбранном приложении. Подключение не требует покупки API-ключа; используйте доступные инструменты и подписку.

Для полного цикла Редколлегии нужны остальные инструменты семьи. Отсутствующий этап нельзя считать выполненным; команду установки всего комплекта найдёте в конце этой инструкции.

## Вся Редколлегия

Для полного процесса установите [Редколлегию](https://github.com/beaverbeard/redkollegiya) и все восемь скиллов:

```text
Установи Редколлегию и весь комплект из восьми редакционных скиллов:
https://github.com/beaverbeard/redkollegiya

Используй их, когда мы пишем или редактируем тексты.
```

[Полный комплект исходников](downloads/editorial-skill-sources.zip)

## Источники и дата проверки

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

[Назад](../README.md)
