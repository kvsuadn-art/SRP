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
- `scripts/ogse_signals_addons_list.script` — список подключаемых модулей (`addons`: сейчас `fp_surge`).
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

## Модуль 2 — «Выброс по часам и затмение»

Работает целиком на слое сигналов (`scripts/fp_surge.script`, подписчик `on_update` с `reschedule` раз в 2 с), штатный `xr_surge_hide` SRP не меняется: фазы, задание «укрыться», урон и поведение NPC те же.

- **Выброс по часам** (как в ЗП): раз в игровые сутки, в час из диапазона 8–20, зависящий от даты, на уровне из `xr_surge_hide.levels_surge_table` с выполненным `condlist`. Признак «сегодня уже был» берётся из `xr_surge_hide.initialization_time` (SRP сам сохраняет его в блоке `SurgeHide`), поэтому модуль **ничего не пишет в сейв** и не заводит своих переменных. Следствие: в первые игровые сутки новой игры часового выброса нет.
- **Затмение** — вариант выброса с другим эффектом. Запуск как в оригинале SRP: бросок при входе на уровень (15 % и +10 % за промах). Если выброс начался сразу после входа на уровень и не по часам, модуль заменяет погодный эффект на эффект затмения из SGM (`fx_blackday_clear` при ясной/облачной погоде, иначе `fx_blackday_rain`).
- **Включение**: info `srp_freeplay` включает оба; `fp_surge_clock` и `fp_eclipse` включают по отдельности (для сюжетного режима).

| Файл | Тип |
|---|---|
| `scripts/fp_surge.script` | новый |
| `scripts/ogse_signals_addons_list.script` | изменён (`fp_surge` в списке) |
| `configs/environment/weather_effects/fx_blackday_clear.ltx`, `fx_blackday_rain.ltx` | из SGM 3.10 (GeJorge), без изменений |
| `configs/gameplay/info_portions.xml` | добавлены `fp_surge_clock`, `fp_eclipse` |

Не взято: код `sgm_blackday` (таймер на `time_global`, собственное хранилище, нет укрытия и урона) и звук `blackday_pre.ogg`.
