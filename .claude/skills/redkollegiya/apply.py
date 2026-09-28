#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""apply.py — детерминированный single-apply Редколлегии (Шаг 3 конвейера).

Detect-этапы (Аграновский, Слопотрон) текст не переписывают, а отдают находки с дословной
цитатой `quote` и заменой `edit`. Если вносить их руками оркестратора-LLM, это самое
хрупкое место конвейера: модель может «чуть подправить» соседнее слово, пропустить перекрытие
или дописать абзац. Здесь то же самое делает код, поэтому соответствие текста находкам
выполняется по построению (идея span-patch из gasyoun/RuWritingStyles, Apache-2.0; код свой).

Что делает (порядок важен):
  1. Раскладывает находки по `action`: `applied` — уже внесено переписчиком (транзит);
     `suggest` — автору; `flag` — замены нет, автору (blocker зон facts/meaning — активный);
     `apply`/`redirect` с `edit` — применимые; неизвестный `action` — автору, не вносится.
  2. Дедуп: одна `quote` + один `edit` от двух этапов → одна правка; одна `quote` + разные
     `edit` → конфликт, обе автору.
  3. Якорение: `quote` ищется в тексте дословно (с допуском на разницу пробелов). Не найдена
     или встречается больше одного раза → автору (скрипт не угадывает, какое вхождение).
  4. Перекрытие span — геометрически, по позициям в исходном тексте: пересекающиеся правки
     отдаются автору обе.
  5. Бюджет роста: суммарный прирост знаков от применённых правок ≤ ratio × длина текста
     (по умолчанию 0.2). Сверх бюджета вытесняются правки с наибольшим приростом, начиная
     с самой «раздувающей». Исправление blocker зон facts/meaning не вытесняется никогда —
     это исправление ошибки, а не стиль. Кластер Слопотрона вытесняется наравне с fix.
  6. Применение с конца текста к началу (позиции не сдвигаются).

Severity при эскалации: blocker зон facts/meaning, не попавший в текст, остаётся активным;
остальное уходит автору как author_choice (исходная severity — в поле orig_severity).

Использование:
    apply.py --text v1.md --findings findings.json --out v3.md [--report r.json]
             [--max-growth 0.2]
    apply.py --length-check prev.md next.md [--max-loss 0.10] [--max-growth 0.2]
    apply.py --selftest

findings.json — список находок или {"findings": [...]}; находка:
    {stage, zone, severity: blocker|fix|author_choice, quote,
     action: applied|apply|suggest|redirect|flag, edit, source?}
    edit — дословный текст, которым заменить quote ("" = удалить; null = замены нет).

Вывод в stdout — краткая сводка (счётчики). Полный отчёт — в --report (JSON).
Exit: 0 — ок; 1 — ошибка входа; 2 — (--length-check) объём вне коридора.

Zero-dep, stdlib only.
"""

import argparse
import json
import re
import sys

DEFAULT_MAX_GROWTH = 0.2
DEFAULT_MAX_LOSS = 0.10

APPLICABLE_SEVERITIES = {"fix", "blocker"}
ACTIONS = {"applied", "apply", "suggest", "redirect", "flag"}
# Зоны, где blocker без внесённой правки запрещает публикацию: ложный факт и смысловой дефект
# (внутреннее противоречие, логическая дыра). Стилистика и норма без правки — выбор автора.
HARD_ZONES = {"facts", "meaning"}


# ---------------------------------------------------------------- якорение

def _ws_pattern(quote):
    """Регэксп для quote с допуском: любой пробельный промежуток ↔ любой пробельный промежуток."""
    parts = [re.escape(p) for p in re.split(r"\s+", quote.strip()) if p]
    return re.compile(r"\s+".join(parts)) if parts else None


def locate(text, quote):
    """Вернуть список (start, end) всех вхождений quote. Сначала дословно, потом с допуском пробелов."""
    if not quote:
        return []
    spans = []
    i = text.find(quote)
    while i != -1:
        spans.append((i, i + len(quote)))
        i = text.find(quote, i + 1)
    if spans:
        return spans
    pat = _ws_pattern(quote)
    if pat is None:
        return []
    return [(m.start(), m.end()) for m in pat.finditer(text)]


# ---------------------------------------------------------------- ядро

def _norm_findings(raw):
    if isinstance(raw, dict):
        raw = raw.get("findings", [])
    if not isinstance(raw, list):
        raise ValueError("findings: ожидается список или {\"findings\": [...]}")
    out = []
    for n, f in enumerate(raw):
        if not isinstance(f, dict):
            raise ValueError(f"находка #{n}: не объект")
        g = dict(f)
        g["_id"] = n
        g["severity"] = str(g.get("severity") or "").strip()
        g["action"] = str(g.get("action") or "").strip()
        out.append(g)
    return out


def _to_author(item, reason):
    rec = {k: v for k, v in item.items() if not k.startswith("_")}
    rec["reason"] = reason
    return rec


def _hard(f):
    """Blocker, который вне текста остаётся активным: зоны фактов (выдуманный факт, 👤) и смысла
    (противоречие, которое этап-переписчик не смог снять сам). Стилистический blocker (кластер
    Слопотрона) без правки — это выбор автора, не запрет публикации."""
    return f["severity"] == "blocker" and str(f.get("zone") or "") in HARD_ZONES


def apply_findings(text, findings, max_growth=DEFAULT_MAX_GROWTH):
    """Single-apply. Возвращает (new_text, report)."""
    findings = _norm_findings(findings)
    applied, to_author, active_blockers, passthrough = [], [], [], []

    def escalate(f, reason):
        rec = _to_author(f, reason)
        if _hard(f):
            active_blockers.append(rec)
        else:
            if rec["severity"] != "author_choice":
                rec["orig_severity"] = rec["severity"]
                rec["severity"] = "author_choice"
            to_author.append(rec)

    # 1. раскладка
    candidates = []
    for f in findings:
        sev, act, edit = f["severity"], f["action"], f.get("edit")
        if act not in ACTIONS:
            escalate(f, f"неизвестный action «{act}» — не вносится")
            continue
        if act == "applied":
            passthrough.append(_to_author(f, "уже внесено этапом-переписчиком"))
            continue
        if act == "flag":
            escalate(f, "замены нет — нужен автор или эксперт")
            continue
        if sev == "author_choice" or act == "suggest":
            to_author.append(_to_author(f, "author_choice"))
            continue
        if sev not in APPLICABLE_SEVERITIES:
            escalate(f, f"неизвестная severity «{sev}»")
            continue
        if edit is None:
            escalate(f, "edit: null — замены нет (ручная правка / эксперт)" if _hard(f)
                     else "этап не дал замены")
            continue
        if not isinstance(edit, str):
            escalate(f, "edit не строка")
            continue
        if not str(f.get("quote") or "").strip():
            escalate(f, "нет quote — нечего якорить")
            continue
        candidates.append(f)

    # 2. дедуп по quote
    by_quote = {}
    for f in candidates:
        by_quote.setdefault(f["quote"].strip(), []).append(f)
    unique = []
    for q, group in by_quote.items():
        edits = {g["edit"] for g in group}
        if len(edits) > 1:
            for g in group:
                escalate(g, "конфликт: одна цитата, разные замены у этапов")
            continue
        head = dict(group[0])
        head["_stages"] = sorted({str(g.get("stage", "?")) for g in group})
        head["_severity"] = "blocker" if any(g["severity"] == "blocker" for g in group) \
            else head["severity"]
        head["severity"] = head["_severity"]
        unique.append(head)

    # 3. якорение
    anchored = []
    for f in unique:
        spans = locate(text, f["quote"])
        if not spans:
            escalate(f, "цитата не найдена в тексте дословно")
        elif len(spans) > 1:
            escalate(f, f"цитата неоднозначна: {len(spans)} вхождения")
        else:
            f["_span"] = spans[0]
            f["_growth"] = len(f["edit"]) - (spans[0][1] - spans[0][0])
            anchored.append(f)

    # 4а. вложенная правка: точечная находка внутри абзаца-замены (кластер Слопотрона ⊃ факт
    # Аграновского). Если её quote ровно один раз есть в edit внешней правки — применить внутри.
    nested_applied = []
    for outer in sorted(anchored, key=lambda f: f["_span"][0] - f["_span"][1]):
        if outer.get("_nested_into"):
            continue
        for inner in anchored:
            if inner is outer or inner.get("_nested_into"):
                continue
            (os_, oe), (is_, ie) = outer["_span"], inner["_span"]
            if os_ <= is_ and ie <= oe and (os_, oe) != (is_, ie) \
                    and outer["edit"].count(inner["quote"].strip()) == 1:
                outer["edit"] = outer["edit"].replace(inner["quote"].strip(), inner["edit"])
                outer["_growth"] = len(outer["edit"]) - (oe - os_)
                outer["_stages"] = sorted(set(outer["_stages"]) | set(inner["_stages"]))
                if inner["severity"] == "blocker":
                    outer["_carries_hard"] = outer.get("_carries_hard") or _hard(inner)
                inner["_nested_into"] = outer
                nested_applied.append(inner)
    anchored = [f for f in anchored if not f.get("_nested_into")]

    # 4б. перекрытие span (геометрия по исходному тексту)
    anchored.sort(key=lambda f: f["_span"])
    overlapping = set()
    for a in range(len(anchored)):
        for b in range(a + 1, len(anchored)):
            if anchored[b]["_span"][0] >= anchored[a]["_span"][1]:
                break
            overlapping.add(a)
            overlapping.add(b)
    ok = []
    for i, f in enumerate(anchored):
        if i in overlapping:
            escalate(f, "перекрытие span с другой правкой")
        else:
            ok.append(f)

    # 5. бюджет роста: исправление факта проходит всегда, остальное — от меньшего прироста к большему
    immune = lambda f: _hard(f) or f.get("_carries_hard")
    budget = int(max_growth * len(text))
    growth = sum(max(0, f["_growth"]) for f in ok if immune(f))
    accepted = [f for f in ok if immune(f)]
    for f in sorted((f for f in ok if not immune(f)), key=lambda f: f["_growth"]):
        g = max(0, f["_growth"])
        if g > 0 and growth + g > budget:
            escalate(f, f"бюджет роста: +{g} знаков сверх лимита {budget} "
                        f"({max_growth:.0%} от {len(text)})")
            continue
        growth += g
        accepted.append(f)

    # 6. применение с конца
    new_text = text
    for f in sorted(accepted, key=lambda f: f["_span"][0], reverse=True):
        s, e = f["_span"]
        new_text = new_text[:s] + f["edit"] + new_text[e:]
        rec = _to_author(f, "applied")
        rec["stages"] = f["_stages"]
        rec["span"] = [s, e]
        rec["growth"] = f["_growth"]
        if f["severity"] == "blocker":
            rec["reason"] = "blocker снят правкой"
        applied.append(rec)
    accepted_ids = {id(f) for f in accepted}
    for inner in nested_applied:
        outer = inner["_nested_into"]
        if id(outer) in accepted_ids:
            rec = _to_author(inner, f"применено внутри правки абзаца ({', '.join(outer['_stages'])})")
            rec["stages"], rec["span"], rec["growth"] = inner["_stages"], list(inner["_span"]), None
            applied.append(rec)
        else:
            escalate(inner, "внешняя правка абзаца не применена: " + "бюджет роста/перекрытие")
    applied.sort(key=lambda r: r["span"][0])

    # одна и та же цитата от двух этапов в разделе автора — одна строка с атрибуцией обоих
    merged = {}
    for rec in to_author:
        key = (str(rec.get("quote") or "").strip(), rec["reason"])
        if key in merged:
            prev = merged[key]
            prev["stages"] = sorted(set(prev["stages"]) | {str(rec.get("stage", "?"))})
        else:
            rec["stages"] = [str(rec.get("stage", "?"))]
            merged[key] = rec
    to_author = list(merged.values())

    report = {
        "len_before": len(text),
        "len_after": len(new_text),
        "growth_budget": budget,
        "growth_used": growth,
        "applied": applied,
        "to_author": to_author,
        "active_blockers": active_blockers,
        "already_applied": passthrough,
    }
    return new_text, report


def length_check(prev, nxt, max_loss=DEFAULT_MAX_LOSS, max_growth=DEFAULT_MAX_GROWTH):
    """Коридор объёма для этапов-переписчиков: (status, ratio). status ∈ ok|loss|growth."""
    a, b = len(prev.strip()), len(nxt.strip())
    if a == 0:
        return ("ok" if b == 0 else "growth"), None
    ratio = (b - a) / a
    if ratio < -max_loss:
        return "loss", ratio
    if ratio > max_growth:
        return "growth", ratio
    return "ok", ratio


# ---------------------------------------------------------------- selftest

def selftest():
    fails, seen = [], []

    def check(name, cond):
        seen.append(name)
        if not cond:
            fails.append(name)

    F = lambda **kw: dict({"stage": "slopotron", "zone": "ai-markers", "action": "apply"}, **kw)

    # 1. простая правка + author_choice не вносится
    t = "В современном мире важно отметить, что рынок растёт."
    out, r = apply_findings(t, [
        F(severity="fix", quote="В современном мире важно отметить, что рынок",
          edit="Рынок"),
        F(severity="author_choice", action="suggest", quote="растёт", edit="рос"),
    ])
    check("simple-apply", out == "Рынок растёт.")
    check("author-choice-untouched", len(r["to_author"]) == 1 and "растёт" in out)

    # 2. удаление edit=""
    out, _ = apply_findings("Раз. Лишнее. Два.", [F(severity="fix", quote=" Лишнее.", edit="")])
    check("delete", out == "Раз. Два.")

    # 3. перекрытие: обе автору, blocker остаётся активным
    t = "Компания выросла на 40% за год благодаря синергии."
    out, r = apply_findings(t, [
        F(stage="agranovsky", zone="facts", severity="blocker",
          quote="выросла на 40% за год", edit="выросла на 12% за год"),
        F(severity="fix", quote="за год благодаря синергии", edit="за год"),
    ])
    check("overlap-untouched", out == t)
    check("overlap-blocker-active", len(r["active_blockers"]) == 1 and len(r["to_author"]) == 1)

    # 4. цитата не найдена / неоднозначна
    t = "Это важно. Это важно."
    out, r = apply_findings(t, [
        F(severity="fix", quote="Это важно.", edit="Важно."),
        F(severity="fix", quote="нет такой", edit="x"),
    ])
    check("ambiguous-and-missing", out == t and len(r["to_author"]) == 2)

    # 5. допуск пробелов (NBSP / перенос строки внутри цитаты)
    t = "Рынок диктует\nправила игры."
    out, _ = apply_findings(t, [F(severity="fix", quote="Рынок диктует правила", edit="Правила задаёт спрос:")])
    check("whitespace-tolerant", out == "Правила задаёт спрос: игры.")

    # 6. бюджет роста: вытесняется самая раздувающая, blocker — никогда
    t = "а" * 100 + " X " + "б" * 100 + " Y " + "в" * 100 + " Z " + "г" * 100
    budget_text_len = len(t)                      # 412 → бюджет 0.2 = 82
    out, r = apply_findings(t, [
        F(severity="fix", quote=" X ", edit=" " + "x" * 40 + " "),     # +40
        F(severity="fix", quote=" Y ", edit=" " + "y" * 60 + " "),     # +60 — вытесняется
        F(stage="agranovsky", zone="facts", severity="blocker",
          quote=" Z ", edit=" " + "z" * 30 + " "),                            # +30, blocker
    ], max_growth=0.2)
    check("budget-evicts-largest", "y" * 60 not in out and "x" * 40 in out)
    check("budget-keeps-blocker", "z" * 30 in out)
    check("budget-report", any("бюджет роста" in a["reason"] for a in r["to_author"])
          and r["growth_used"] <= int(0.2 * budget_text_len))

    # 7. дедуп: одна цитата и одна замена от двух этапов → одна правка, blocker побеждает
    t = "Эксперты считают, что рынок вырос."
    out, r = apply_findings(t, [
        F(severity="author_choice", action="suggest", quote="рынок", edit=None),
        F(severity="fix", quote="Эксперты считают, что рынок", edit="Рынок"),
        F(stage="agranovsky", zone="facts", severity="blocker",
          quote="Эксперты считают, что рынок", edit="Рынок"),
    ])
    check("dedup", out == "Рынок вырос." and len(r["applied"]) == 1
          and r["applied"][0]["stages"] == ["agranovsky", "slopotron"]
          and r["applied"][0]["reason"] == "blocker снят правкой")

    # 8. конфликт замен
    out, r = apply_findings("Цифра 40%.", [
        F(severity="fix", quote="40%", edit="12%"),
        F(stage="agranovsky", zone="facts", severity="blocker", quote="40%", edit="15%"),
    ])
    check("conflict", out == "Цифра 40%." and len(r["active_blockers"]) == 1 and len(r["to_author"]) == 1)

    # 9. edit null: blocker активен, fix → автору
    out, r = apply_findings("Закон № 999-ФЗ.", [
        F(stage="agranovsky", zone="facts", severity="blocker", quote="№ 999-ФЗ", edit=None),
        F(stage="agranovsky", zone="facts", severity="fix", quote="Закон", edit=None),
    ])
    check("edit-null", out == "Закон № 999-ФЗ." and len(r["active_blockers"]) == 1
          and r["to_author"][0]["reason"] == "этап не дал замены")

    # 10. несколько правок — позиции не съезжают
    t = "один два три четыре пять"
    out, _ = apply_findings(t, [
        F(severity="fix", quote="два", edit="ДВА-ДВА"),
        F(severity="fix", quote="четыре", edit="4"),
        F(severity="fix", quote="один", edit=""),
    ], max_growth=1.0)
    check("multi-positions", out == " ДВА-ДВА три 4 пять")

    # 11. applied от переписчика не трогаем
    out, r = apply_findings("текст", [dict(stage="chukovsky", severity="fix",
                                           action="applied", quote="текст", edit="ТЕКСТ")])
    check("passthrough", out == "текст" and len(r["already_applied"]) == 1)

    # 12. дубль в разделе автора склеивается
    _, r = apply_findings("Эксперты считают так.", [
        F(severity="author_choice", action="suggest", quote="Эксперты считают", edit=None),
        F(stage="agranovsky", severity="author_choice", action="suggest", quote="Эксперты считают", edit=None),
    ])
    check("author-dedup", len(r["to_author"]) == 1 and r["to_author"][0]["stages"] == ["agranovsky", "slopotron"])

    # 13. кластер Слопотрона без edit — автору, не активный blocker; severity в разделе автора = author_choice
    _, r = apply_findings("Абзац со слопом.", [F(severity="blocker", action="redirect",
                                                  quote="Абзац со слопом.", edit=None)])
    check("style-blocker-not-hard", not r["active_blockers"] and r["to_author"][0]["severity"] == "author_choice"
          and r["to_author"][0]["orig_severity"] == "blocker")

    # 14. стилистический blocker вытесняется бюджетом, факт — нет
    t = "а" * 100 + " P " + "б" * 100
    out, r = apply_findings(t, [
        F(severity="blocker", action="redirect", quote=" P ", edit=" " + "p" * 80 + " "),
    ], max_growth=0.2)
    check("style-blocker-budget", "p" * 80 not in out and not r["active_blockers"])

    # 15. факт внутри абзаца-замены применяется вложенно
    t = "Рынок вырос на 40% за год, это синергия и экосистема. Второй абзац."
    out, r = apply_findings(t, [
        F(severity="blocker", action="redirect",
          quote="Рынок вырос на 40% за год, это синергия и экосистема.", edit="Рынок вырос на 40% за год."),
        F(stage="agranovsky", zone="facts", severity="blocker", quote="40%", edit="12%"),
    ])
    check("nested-apply", out == "Рынок вырос на 12% за год. Второй абзац." and len(r["applied"]) == 2
          and not r["active_blockers"])
    # ...а если абзац-замена выкинул факт — конфликт, факт остаётся активным
    out, r = apply_findings(t, [
        F(severity="blocker", action="redirect",
          quote="Рынок вырос на 40% за год, это синергия и экосистема.", edit="Рынок вырос."),
        F(stage="agranovsky", zone="facts", severity="blocker", quote="40%", edit="12%"),
    ])
    check("nested-conflict", out == t and len(r["active_blockers"]) == 1)

    # 16а. контракт action: неизвестный не вносится; flag смысла — активный blocker
    t = "Продажи выросли на 40%. Выручка упала вдвое."
    out, r = apply_findings(t, [F(severity="fix", action="verify", quote="на 40%", edit="на 4%")])
    check("unknown-action-not-applied", out == t and len(r["to_author"]) == 1
          and "неизвестный action" in r["to_author"][0]["reason"])
    out, r = apply_findings(t, [F(stage="chukovsky", zone="meaning", severity="blocker",
                                  action="flag", quote="Выручка упала вдвое.", edit=None)])
    check("meaning-flag-active", out == t and len(r["active_blockers"]) == 1)
    out, r = apply_findings(t, [F(stage="chukovsky", zone="meaning", severity="author_choice",
                                  action="flag", quote="Выручка упала вдвое.", edit=None)])
    check("meaning-flag-choice-not-active", out == t and not r["active_blockers"])
    out, r = apply_findings(t, [F(zone="ai-markers", severity="blocker", action="flag",
                                  quote="Выручка упала вдвое.", edit=None)])
    check("style-flag-not-active", not r["active_blockers"] and len(r["to_author"]) == 1)

    # 16. коридор объёма
    check("len-ok", length_check("a" * 100, "a" * 95)[0] == "ok")
    check("len-loss", length_check("a" * 100, "a" * 85)[0] == "loss")
    check("len-growth", length_check("a" * 100, "a" * 125)[0] == "growth")

    total = len(seen)
    if fails:
        print(f"selftest: FAIL {total - len(fails)}/{total} — " + ", ".join(fails))
        return 1
    print(f"selftest: PASS {total}/{total}")
    return 0


# ---------------------------------------------------------------- CLI

def _read(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def main(argv=None):
    p = argparse.ArgumentParser(description="Детерминированный single-apply Редколлегии")
    p.add_argument("--text", help="text_v1 (после Чуковского)")
    p.add_argument("--findings", help="JSON находок Detect-этапов")
    p.add_argument("--out", help="куда записать text_v3")
    p.add_argument("--report", help="куда записать полный JSON-отчёт")
    p.add_argument("--max-growth", type=float, default=DEFAULT_MAX_GROWTH)
    p.add_argument("--max-loss", type=float, default=DEFAULT_MAX_LOSS)
    p.add_argument("--length-check", nargs=2, metavar=("PREV", "NEXT"))
    p.add_argument("--selftest", action="store_true")
    a = p.parse_args(argv)

    if a.selftest:
        return selftest()

    if a.length_check:
        status, ratio = length_check(_read(a.length_check[0]), _read(a.length_check[1]),
                                     a.max_loss, a.max_growth)
        shown = "n/a" if ratio is None else f"{ratio:+.1%}"
        print(f"length-check: {status} ({shown}; коридор −{a.max_loss:.0%}…+{a.max_growth:.0%})")
        return 0 if status == "ok" else 2

    if not (a.text and a.findings and a.out):
        p.error("нужны --text, --findings и --out (или --selftest / --length-check)")
    try:
        text = _read(a.text)
        findings = json.loads(_read(a.findings))
        new_text, report = apply_findings(text, findings, a.max_growth)
    except (OSError, ValueError) as e:
        print(f"ошибка: {e}", file=sys.stderr)
        return 1

    with open(a.out, "w", encoding="utf-8") as fh:
        fh.write(new_text)
    if a.report:
        with open(a.report, "w", encoding="utf-8") as fh:
            json.dump(report, fh, ensure_ascii=False, indent=2)

    print(f"applied: {len(report['applied'])} | to_author: {len(report['to_author'])} | "
          f"active_blockers: {len(report['active_blockers'])} | "
          f"growth: +{report['growth_used']}/{report['growth_budget']} | "
          f"len {report['len_before']}→{report['len_after']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
