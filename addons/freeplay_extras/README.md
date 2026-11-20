# Freeplay Extras — аддон поверх SRP Freeplay

Контентно-функциональное расширение для режима Freeplay. Устанавливается **после** SRP и ветки `freeplay`: папку `gamedata` копируют поверх основной `gamedata` игры (файлы аддона заменяют одноимённые).

## Использованные базы и авторы

| База | Авторы | Что взято |
|---|---|---|
| SRP (community patch для S.T.A.L.K.E.R.: Clear Sky) и ветка Freeplay | Decane и участники SRP; Freeplay — Eon | Основа, файлы-копии с точечными правками |
| OGSM для Clear Sky (CSOGSM) | DEXXX, Alex Ros, kstn и другие авторы OGSM | Идея и данные спавна находок по миру (100 точек), 15 секретных документов, тексты документов и диалогов продажи, цены |
| SGM (Sigerous Mod) | GeJorge (Болотов Николай) | Планируется: записки об оружии и изучение (модуль 2) |

В шапках заимствованных скриптов сохранены оригинальные копирайты и добавлена строка `-- Адаптация под SRP Freeplay: Eon`.

## Модуль 1 — «Находки в Зоне»

При подготовке мира во Фриплее (`freeplay_mode.prepare_world`, один раз за игру) аддон раскладывает в 100 точек OGSM:

- **флешки `flesh_up_*`**, которые в оригинале выдаются только наградами за сюжетные задания: `bd_mp5`, `a_novice_outfit`, `abcd_svu`, `abcd_pkm` (список — `configs/misc/fp_loot.ltx`, `[flashes]`); флешки из кладов и с убитых NPC не дублируются; второй набор флешек OGSM не используется: апгрейды идут штатными заданиями `find_upgrade` механиков SRP;
- **15 секретных документов** (`doc_1…doc_15`): продаются лидерам баз (Сахаров, лидер Чистого Неба, Свобода, Долг, сталкеры, бандиты) по ценам OGSM, 3000–3300 за штуку.

Состояние хранится одним info `fp_loot_spawned`; ничего не выполняется в `update`.

### Файлы

| Файл | Тип |
|---|---|
| `scripts/fp_loot.script` | новый (адаптация `ogsm_bring_items.script`) |
| `scripts/freeplay_mode.script` | копия из Freeplay + вызов `fp_loot.startup_spawn()` в конце `prepare_world` |
| `configs/misc/fp_loot.ltx` | новый, список флешек |
| `configs/misc/quest_items.ltx` | копия из Freeplay + секции `doc_1…doc_15` |
| `configs/gameplay/dialogs_fp_extras.xml` | новый, 6 диалогов продажи |
| `configs/gameplay/character_desc_{marsh,escape,garbage,darkvalley,agroprom,yantar}.xml` | копии из Freeplay + строка `<actor_dialog>` у покупателя |
| `configs/gameplay/info_portions.xml` | копия из Freeplay + `fp_loot_spawned` |
| `configs/system.ltx` | копия из Freeplay + `dialogs_fp_extras` в `[dialogs]` |
| `configs/text/*/fp_extras.xml` | новый; русский и английский (английский во всех остальных языках) |

## Ограничения и допущения

- Предметы лежат на земле в точках OGSM, а не на трупах сталкеров (в оригинале OGSM использует отдельные секции спавна трупов).
- Если файл Freeplay меняется, копии в аддоне нужно обновить (берётся актуальная версия + точечная правка).
- Список «сюжетных» флешек составлен по конфигам SRP и IXRay (в SRP нет `treasure_*.ltx`, `upgrade_items.ltx`): допущение, проверяется при тесте.
- Тексты диалогов и документов на языках, кроме русского, — английские.

## Дальше

Модуль 2: записки об оружии и изучение на info portion (в духе SGM, без привязки к оружейным пакам).
