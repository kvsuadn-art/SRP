# Freeplay Extras — аддон поверх SRP Freeplay

Контентно-функциональное расширение для режима Freeplay. Устанавливается **после** SRP и ветки `freeplay`: папку `gamedata` копируют поверх основной `gamedata` игры (файлы аддона заменяют одноимённые).

## Использованные базы и авторы

| База | Авторы | Что взято |
|---|---|---|
| SRP (community patch для S.T.A.L.K.E.R.: Clear Sky) и ветка Freeplay | Decane и участники SRP; Freeplay — Eon | Основа, файлы-копии с точечными правками |
| OGSM Extended 2.0 для Clear Sky (репозиторий CSOGSM) | DEXXX, Alex Ros, kstn и другие авторы OGSM | Идея и данные спавна находок по миру (100 точек), 15 секретных документов, тексты документов и диалогов продажи, цены |
| Sigerous Mod 3.10 (SGM, репозиторий -SGM) | GeJorge (Болотов Николай) | Планируется: записки об оружии и изучение (модуль 2) |
| OGS Evolution (OGSE) | Malandrinus, OGS Evolution Team | Система сигналов `ogse_signals` (оригинальные имя и копирайт сохранены) |

В шапках заимствованных скриптов сохранены оригинальные копирайты и добавлена строка `-- Адаптация под SRP Freeplay: Eon`.

## Базовый слой `fp_*` — наследование вместо правок оригиналов

Оригинальные `bind_stalker.script` и `actor.ltx` ядра не меняются. Аддон подменяет только строку `script_binding` в своей копии `configs/creatures/actor.ltx`, а биндер актора наследуется:

- `scripts/fp_binder.script` — класс `fp_actor_binder` (наследник `bind_stalker.actor_binder`). Вызывает базовый метод, затем отправляет сигнал: `on_net_spawn`, `on_net_destroy`, `on_update`, `on_item_take`, `on_item_drop`, `on_trade`, `on_task`, `on_take_from_box`, `on_save`, `on_load` (аргументы описаны в шапке файла). Новые коллбэки движка (`use_object`, info, hit и др.) не регистрируются, пока нет модуля, которому они нужны.
- `scripts/ogse_signals.script` — менеджер сигналов и слотов (Malandrinus, OGS Evolution Team) с минимальными правками: `ASSERT` и `log2` определены локально, `profile_timer` и `debug.getinfo` защищены проверкой наличия, `slot` сделан `local`. Модули подписываются в собственном `attach(mgr)`, редкие подписки задают период через `reschedule(мс)`.
- `scripts/ogse_signals_addons_list.script` — список подключаемых модулей (`addons`, пока пуст).
- `configs/creatures/actor.ltx` — копия из ядра, изменена одна строка `script_binding = fp_binder.actor_init`.

Ошибки подписчиков намеренно не перехватываются: пойманная ошибка оставила бы очередь `ogse_signals` в полуобработанном состоянии. Подписчик, пишущий в пакет сохранения (`on_save`), меняет формат сейва.

## Модуль 1 — «Находки в Зоне»

При подготовке мира во Фриплее (`freeplay_mode.prepare_world`, один раз за игру) аддон раскладывает в точках OGSM (100 мест):

- *(опционально)* дополнительные флешки `flesh_up_*` из списка `configs/misc/fp_loot.ltx` (`[flashes]`, по умолчанию пуст). Флешки, закрытые сюжетом, возвращаются в ядре тайниками (`configs/misc/treasure_freeplay.ltx`), а не этим модулем; второй набор флешек OGSM не используется;
- **15 секретных документов** (`doc_1…doc_15`): продаются лидерам баз (Сахаров, лидер Чистого Неба, Свобода, Долг, сталкеры, бандиты) по ценам OGSM, 3000–3300 за штуку.

Состояние хранится одним info `fp_loot_spawned`; ничего не выполняется в `update`.

### Файлы

| Файл | Тип |
|---|---|
| `scripts/fp_loot.script` | новый (адаптация `ogsm_bring_items.script`) |
| `scripts/freeplay_mode.script` | копия из Freeplay + вызов `fp_loot.startup_spawn()` в конце `prepare_world` |
| `configs/misc/fp_loot.ltx` | новый, список дополнительных флешек (пуст) |
| `configs/misc/quest_items.ltx` | копия из Freeplay + `[document]:device_pda` и секции `doc_1…doc_15` (родитель определён в этом же файле) |
| `configs/gameplay/dialogs_fp_extras.xml` | новый, 6 диалогов продажи |
| `configs/gameplay/character_desc_{marsh,escape,garbage,darkvalley,agroprom,yantar}.xml` | копии из Freeplay + строка `<actor_dialog>` у покупателя |
| `configs/gameplay/info_portions.xml` | копия из Freeplay + `fp_loot_spawned` |
| `configs/system.ltx` | копия из Freeplay + `dialogs_fp_extras` в `[dialogs]`; секция `[document]` убрана (определена в `quest_items.ltx`) |
| `configs/text/*/fp_extras.xml` | новый; русский и английский (английский во всех остальных языках) |

## Ограничения и допущения

- Документы лежат на земле в точках OGSM. Мелкие предметы на полу могут провалиться под текстуры или быть унесены аномалией; план — перенести их в тела или ящики (уборщик трупов SRP не удаляет тела с предметами из `[keep_items]` в `death_generic.ltx`).
- Если файл Freeplay меняется, копии в аддоне нужно обновить (берётся актуальная версия + точечная правка).
- Тексты диалогов и документов на языках, кроме русского, — английские.

## Дальше

Модуль 2: записки об оружии и изучение на info portion (в духе SGM, без привязки к оружейным пакам).
