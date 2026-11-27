# Аудит сюжетной линии SGM (Sigerous Mod 3.10) для SRP Freeplay

Статус: аудит по чтению и grep файлов, в игре ничего не запускалось; «не проверено» помечено в тексте.
Состав: часть 1 — инфраструктура и хуки; часть 2 — Болота/Кордон/Свалка; часть 3 — Долина/Агропром/Янтарь/Военные.

## Итоги
- SGM работает одним покадровым опросом из `actor_binder:update`; в SRP-аддоне его заменяет один подписчик `on_update` с reschedule и таблицей триггеров (префикс `sgmq_`, включение `srp_freeplay`).
- Главный блокер: SRP-ядро не умеет задания SGM (`target_profile`, `no_sid_*`, `on_fail`, `hide_smart_name`, необязательный `target_story_ids`); `select_task("storyline")` во Freeplay возвращает nil. Нужен собственный слой заданий или копии файлов ядра.
- Логика NPC SGM использует схемы (`move` и др.) и эффекты/условия, которых нет в SRP; их придётся регистрировать в `xr_effects`/`xr_conditions`/`_G.schemes` во время работы (порядок загрузки не проверен).
- Сюжетные цепочки (Напр/пропуск на Свалке, оборона базы Долга, дверь базы Свободы в Долине, сопровождения) — SKIP для Freeplay.
- Лучшие кандидаты (малая/средняя работа): `esc_shilov_*`, захваты `mar_capture_pumping_station` и `mar_capture_church`, цепочка Барона, `agr_kill_wild_giant`, `mil_hog_*`, `yan_kill_tunnel_snorks`, `val_searched_impounded`/`val_find_ashot_dummy`.
- Около 18 секций предметов SGM нет ни в оригинале, ни в SRP, ни в аддоне (список — в части 3); skill-книги к оружию SGM не берём.

---

# Часть 1

# SGM (Sigerous Mod 3.10, CS) infrastructure audit, for porting into the SRP Freeplay addon

Read-only analysis. Everything below was verified by reading/grepping unless marked "unverified".
Paths: SGM = /home/claude/kvsuadn-art/sgm/gamedata, vanilla = /home/claude/kvsuadn-art/csogsm/original, SRP = /home/claude/srp/gamedata, addon = /home/claude/srp/addons/freeplay_extras/gamedata.

## 0. Key facts in one screen

* SGM = ~21 `sgm_*.script` (12 178 lines, of which 7 298 are sgm_phrases) + hooks in ~45 vanilla scripts + ~650 KB of new XML + 163 NPC logic ltx + ~225 spawn sections.
* SGM's runtime is one `actor_binder:update` hook (every frame, no throttling) -> `sgm_loader.sigerous_mod_init()` -> `sigerous_mod_loader()` -> 13 modules. All of it is "poll + flag via info portion", so it maps cleanly onto our `on_update` signal with `mgr:reschedule(ms)`.
* State: spawn/quest flags = engine info portions (744 new ids in sgm_portations.xml + extra_portation.xml); scalar variables (bank, blackday, satiety...) = actor `pstor` (saved by vanilla `xr_logic.pstor_save_all`, no extra save code in SGM); `sgm_flags.*` timers = module-level Lua vars, NOT saved (reset on load, harmless).
* SRP core has NONE of the SGM core extensions (task_objects `target_profile/no_sid_*/complete_info/on_fail/hide_smart_name`, sim_faction `faction_disable_info`, new schemes, xr_logic `shooter_switch`, xr_doctor/xr_gainer hooks). SRP's copies of the touched files differ from vanilla by 500-3000 diff lines each (e.g. task_objects 2926, xr_effects 2102, sim_board 1115), so SGM hunks cannot be re-applied as patches.
* Dialog callbacks (`<precondition>/<action>/<init_func>`) accept ANY script module (verified: `sgm_dialogs.*` used 819x, `sgm_phrases.*` via init_func), so dialogs do not need core edits. NPC logic ltx conditions/effects are the opposite: SRP `xr_logic` resolves them ONLY as `xr_conditions[func]` / `xr_effects[func]` (xr_logic.script lines 492-538), so SGM's 29 effects + 12 conditions used by NPC logic must be injected into those two tables (see E).
* Schemes: `_G.schemes` is a global table (`_g.script:5`, filled in modules.script). An addon can do `schemes["move"]="sgm_xr_move"` at runtime, no edit of modules.script needed (mechanism verified in code; timing relative to first NPC logic init unverified).
* 232 hard-coded `create(sect,x,y,z,lv,gv)` calls: 35 are in `all_secrets_spawn`/`all_npc_spawn` (no level_name context), 2 more (`gar_depo_defender1/2`, gv 329) sit in a cross-level block; of the 195 that sit inside a level_name block, 100% have a game_vertex_id inside that level's gvid range of the all.spawn in /home/claude/kvsuadn-art/cs_all.spawn (marsh 1-244, escape 472-742, garbage 245-471, darkvalley 743-960, agroprom 1057-1211, yantar 1212-1312, red_forest 961-1055, military 1313-1510, limansk 1524-1564). So positions/vertices are tied to the stock CS graph; SRP using the stock graph is unverified.

---------------------------------------------------------------------------------------------------

## A. Hooks into vanilla

### A1. Scripts SGM modified (diff vs vanilla, whitespace-insensitive; SRP column = how far SRP already diverged from vanilla)

Legend for "our mechanism": SIG = can be done from fp_binder signals (on_update/on_item_*/on_take_from_box/on_net_spawn/on_save/on_load); DLG = dialog callbacks (no core edit); INJ = inject into `xr_effects`/`xr_conditions`/`schemes` tables at runtime from addon script; CORE = needs a core change or a copy-override of the core file; DROP = not needed for quests.

| file | what SGM added | purpose | our mechanism |
|---|---|---|---|
| bind_stalker.script (SGM 195 / SRP 732 lines diff) | `sgm_callbacks.callback_for_take_item_from_box/info/trade/article/on_item_take/on_item_drop/task/location_added` (all except take_from_box are EMPTY bodies); `use_object` callback ON (`callback_on_use`, `_for_deserves`, `_for_skills`, `_for_sleep`); `update` -> `sgm_loader.sigerous_mod_init(); sgm_callbacks.callback_for_update()`; `on_hit` hook commented out | the whole per-frame engine + item-use features (sleeping bag, deserve boxes dv_*, skill books, repair kits, medals, food satiety) | SIG: on_update, on_item_use (fp_binder already registers callback.use_object), on_take_from_box. Nothing needs core. |
| xr_motivator.script (100/765) | per-NPC update: `sgm_modules.profile_update(obj)`, `enemy_found_tips_module`, `npc_range_module`, `xr_gainer.gainer_module`, `xr_picker.picker_module`, `xr_doctor.add_wounded`; npc hit -> `sgm_callbacks.callback_on_hit` | profile->id registry (used by tasks target_profile), random "enemy spotted" tips, night vision range, looting AI | Registry: CORE-free alternative = register ids at spawn (we create the NPCs ourselves) + `ogse` signal on_net_spawn of objects is not provided, so keep own `id` table filled in our `create()` wrapper (SGM already does this in `create_update` for create_update_one_list). Tips/range/looting = DROP (cosmetic/AI). |
| se_stalker.script (3/220) | `sgm_modules.on_death_module(self,killer)` in `se_stalker:on_death` | gives death infos `esc_explorer_ruins1_death`, spawns `dv_army_driver_case` on esc_driver, removes quest map spots | CORE hook (server object). Alternatives: poll `alife():object(id)` alive state of tracked ids in on_update (cheap, ~20 ids), or hook `xr_death`-like `on_death` section in NPC logic ltx (we own those ltx). |
| sim_board.script (1/1115) | `sgm_callbacks.callback_on_create_squad(...)` | EMPTY (debug) | DROP |
| bind_physic_object.script (36/287) | `sgm_modules.physic_update(obj)` in generic_physics_binder:update; `init2` | records id of `treasure_rukzak` physics objects, map spot | SIG-able by spawning wrapper (`create()` already adds spot). DROP mostly. |
| _g.script (504/1258) | ~50 new global functions (see D): `create, create_force, delete_force, release_force, universal_create*, give_*_to_actor/sid, use_*_mode, recover_info*, give_quick_news, show_hud_message, play_*snd*, add_task, add_eliminate_task, use_explorer_module, create_info_explorer(2), find_in_string, hero_in_stalker, variable_precond, activate_blackday, set_community_rel, present_night, actor_in_sleep_zone, show_progress_bar...`; ammo_section additions; `create()` calls `sgm_modules.create_update` | helper library for all sgm_* | Move into an addon script (e.g. `sgmq_lib.script`), call with module prefix. NB SRP `_g.script` has no `create` global (verified) so name clash is not an issue, but SRP _g is only 517 lines vs vanilla 1287, so check each helper's deps. |
| xr_effects.script (414/2102) | 55 new functions (respawn_* bodyguard/banker x15, sgm_bodyguard_* x6, create_esc_bodyguard_*, zone_tornado/infection_effect, install_less_relation, add_500_stalker_relation, sgm_activate_blackday, gar_create_propusk, agr tips, agr_dolg_n_wave1_update, yan_tunnel_snorks_w1-3_update, play_s2d/s3d_sound, remove_npc_spot, bad_on_sivoha_death, lim_send_sivoha_tip, ...) | referenced as `=name` from SGM NPC logic ltx and (a few) from tasks | INJ (`xr_effects.name = function...`) or rewrite ltx to avoid. 29 distinct effects used by NPC logic. |
| xr_conditions.script (220/1592) | 30 new functions: `actor_is_die/alive, actor_is_no_enemy (19 uses), is_enemy_actor, mar_rescue1-5_func, mar_plan_b1-5_func, mar_help_rescue_fail, agr_pre_wave3_end, agr_7_4_squad_ready, has_* item checks, its_hide_time (night deals, 12 uses), yan_open/close_door_before, is_no_level, actor_not_in_dolg, killed_by_actor` | logic ltx / task condlists | INJ. 12 used by NPC logic. |
| dialogs.script (31/585) | `relocate_*` unchanged names; `first_speaker:change_character_reputation(70)` + `change_community_goodwill(+100)` on every dialog finish (behaviour change!), new `actor_in_csky/actor_not_in_csky` preconditions | dialogs XML preconditions | The two preconditions -> copy into `sgm_dialogs`-style module (DLG). Reputation/goodwill side effect = CORE, DROP (changes base game balance). |
| task_objects.script (59/2926) | `hide_smart_name`, `on_fail` condlist, `complete_info/reverse_info/fail_info` polling in eliminate_smart, storyline task: `target_profile` -> `sgm_modules.get_profile_id`, `no_sid_x/y/z/lv/gv/shift` -> creates `<profile>_spot` marker object when NPC id unknown | storyline tasks with non-story-id NPC targets (47 of 77 SGM tasks use target_profile; 41 use no_sid_*) | CORE. Not reproducible from signals. Use own task layer (see E) with `CGameTask` (SRP task_objects.script:166 already uses the engine class) or add tasks via engine API. |
| task_manager.script (15/787) | `misc\task_manager.ltx` -> `misc\tasks\task_manager.ltx` (2 places) | SGM moved all tm_*.ltx to misc\tasks + sgm_tasks list | CORE. DROP: do not touch SRP task manager. |
| sim_faction.script (31/909) | `faction_disable_info` per expansion level; faction_stalker.ltx adds `faction_disable_info = stalker_off`, bandit/renegade `bandit_off` | story switch to stop faction respawn (info `bandit_off`/`stalker_off`, set by sgm_info/sgm_tasks on garbage) | CORE. DROP (story-specific). |
| smart_terrain.script (17/1176) | nil-job guards (`unregister_npc` instead of abort) | stability | DROP (SRP already has own fixes; unverified equivalent). |
| bind_smart_terrain / bind_restrictor (9/53, 5/107) | map spots for `show_smarts` debug + `check_smart_name_location` | debug/UI | DROP |
| death_manager.script (47/306) | `death_items_grants.ltx` `[grant_items]` list -> never dropped from corpse | keeps quest items off NPC drops | CORE; DROP or put quest items in our own spawn only. |
| release_body_manager.script (24/269) | corpse timer 6 s -> 160 s; `sgm_functions.ReadAllowRelease(section)` (system.ltx `allow_release` per section) so quest NPCs are not released | prevents cleaning quest corpses (val_impounded_corpse, agr_exo_bandit*) | CORE; alternative: set `allow_release`-like protection via existing SRP mechanism (unverified) or keep corpses by timer. |
| xr_meet (39/842), xr_remark (49/286), xr_walker (5/170), xr_kamp (2/899), xr_patrol (2/567), state_lib (50/1881), state_mgr_animation_list (7/-), sr_light, sr_no_weapon, sr_bloodsucker, mob_death (1/47), ph_minigun | meet: `auto_3_5` talk mode, voice-file sound_start/stop, blocks meet for gainer NPC and `actor_bodyguard_soldier*`; ph_minigun: gets id of esc_tunnel_scout; others small tweaks / new anim states for `move`/`theatre` | needed by SGM custom schemes + SGM NPC meet sections | CORE for meet `auto_3_5` and voice sounds; most SGM NPCs use plain `meet@x` sections that work with vanilla meet (verified: all 40 `meet@` sections use standard keys). |
| modules.script (18/202) | `load_scheme` x11: picker, shooter, corpse, theatre, move, gainer, doctor, defender, mob_move, ph_shot, ph_radio | register custom schemes | INJ via `_G.schemes` (see E). |
| xr_logic.script (22/1878) | `xr_doctor/xr_gainer` disable/set_scheme for every stalker; `shooter_switch` condition type | custom schemes generic init | doctor/gainer = DROP (not used by any SGM logic ltx, verified: no `[doctor]`/`[gainer]` sections). `shooter_switch` = used by 8 RPG-ambush NPC ltx -> CORE, or rewrite those NPCs without it. |
| news_manager.script (249/231) | `send_tip/send_silence_tip/bodyguard_tip/bankir_tip/send_deserve/send_repair/send_add_skill...` | HUD tip messages | Copy functions into an addon module (they use `news_manager.send_tip` w/ custom title; SRP news_manager already has its own — check), mostly independent (DLG/SIG). |
| guiders / treasure_manager / inventory_upgrades / dialogs_agroprom / stc_strelok_health_manager / bind_artefact / ui_main_menu / ui_mm_opt_main | treasure map-spot removal; skill_book_berg give; strelok health constants; main-menu cheat keys (`sgm_*` item lists); `ui_extra_*` options screens | unrelated to quests | DROP |
| NEW files: xr_move, mob_move, xr_theatre, xr_shooter, xr_corpse, xr_picker, xr_defender, xr_doctor, xr_gainer, ph_shot, ph_radio, deserves_manager, ui_extra_hud/modes/options | custom NPC schemes + options UI | see D | New files => can be shipped as-is in the addon (renamed to avoid clashes, e.g. `sgmq_move`). Scheme names `move, mob_move, shooter, corpse, theatre, picker, defender, doctor, gainer` do not exist in SRP modules.script (verified). |

### A2. Configs SGM changed that matter for quests (names only)

* `system.ltx`: adds `#include mod_parameters\main_params.ltx`, `capture_list.ltx`, `misc\sgm_includes.ltx` (outfit/af upgrades), `misc\task_spots.ltx` (31 task map-spot sections `*_spot`), moves inventory_upgrades to `misc\engineer\`; `[info_portions] files += sgm_portations, extra_portation`; `[dialogs] files += sgm_dialogs`; `[profiles] files += sgm_profiles`; `specific_characters_files += character_desc_sgm`; `max_weight 50->70`, blood decal changes. `localization.ltx`: `+SGM_add_include` (text/rus/SGM_*.xml).
* `game_story_ids.ltx`: `1418 = freeplay_changer`(!, present only in SGM copy) and `20001 = sgm_lv_to_limansk`.
* `creatures/spawn_sections.ltx` (+`#include SGM_stalkers.ltx`, `SGM_monsters.ltx`), `creatures/stalkers.ltx` ([stalkers_common] corpse intervals 15h), `monsters.ltx` (corpse 36h->10h), `creatures/actor.ltx` (jump speed/mass), `creatures/game_relations.ltx` (actor_stalker row changed), `m_stalker*.ltx, m_giant, m_bloodsucker`.
* `misc/squad_descr.ltx` (+`#include squad_descr_sgm.ltx`), `squad_descr_agroprom.ltx`, `squad_descr_garbage.ltx`, NEW `squad_descr_sgm.ltx` (66 squads).
* `misc/tasks/` (NEW folder: task_manager.ltx + tm_*.ltx copies + `sgm_tasks.ltx` with 77 tasks).
* `misc/dialog_manager.ltx` (community lists extended: csky/renegade/ecolog), `misc/faction_{stalker,bandit,renegade,monster,duty,freedom}.ltx` (faction_disable_info), `misc/death_*` (+death_items_grants.ltx), `misc/trade/*` (+order_traders/*, trade_breeder.ltx; trader configs for new traders), `misc/sgm_quest_items.ltx, sgm_deserves.ltx, sgm_devices.ltx, sgm_modificates.ltx, sgm_medals.ltx, sgm_upgrades.ltx, deserve_items/*`.
* `gameplay/`: NEW `sgm_dialogs.xml` (74 dialogs), `sgm_profiles.xml` (character id -> class only), `character_desc_sgm.xml` (113 specific_characters), `sgm_portations.xml` + `extra_portation.xml` (744 infos); MODIFIED vanilla `character_desc_*.xml` (adds actor_dialog to existing characters, see C), `character_dialogs.xml` (adds `about_story_dialog` to generic), `info_portions.xml` (+`ui_talk_show`), dialogs*.xml (text/whitespace only; no new dialog ids in them).
* `ui/map_spots.xml` (custom spot types `quest_npc_location, bankir_npc_location, bodyguard_npc_location, squad_commander_location, hide_trader_location, breeder_location, upgrader_location, personal_location, mar_defend_tower_location, green_location, deserve, ...` used by `level.map_add_object_spot_ser`; unknown spot type => engine error, so the addon needs its own copy of these spot types), `environment/weather_effects/fx_blackday_clear|rain.ltx` (+`dynamic_weather_graphs.ltx` change). Addon already ships `fx_eclipse_*` weather fx.
* `scripts/SGM/**` = 163 NPC logic files; `configs/scripts/<level>/` vanilla logic files were NOT diffed in detail (unverified whether SGM changed vanilla NPC logic ltx).

---------------------------------------------------------------------------------------------------

## B. SGM runtime

### B1. Per-update call tree
`actor_binder:update` (every frame; no throttle) -> `sgm_loader.sigerous_mod_init()` (skipped if info `mod_deactivate`) -> `sigerous_mod_loader()`:

| module | what it polls | per-frame cost (static counts, comment lines excluded) |
|---|---|---|
| sgm_huds.hud_checker | HUD clock/weapon/armor statics, death radio messages by `get_time_minutes`, 8 `has_alife_info`, 7 `read_variable` | UI work every frame (DROP: cosmetic) |
| sgm_grant.item_works_update | gives `sleeping_bag` if missing; rank medals at rank>=100..1200 (`medal_rank_*` infos); removes `wpn_rpg7_for_blockpost` | 10 has_alife_info |
| sgm_modes | cheat modes by infos `activate_immortal/power/bleeding/repair`; calls `sgm_blackday.black_day_sys()` | 4 has_info + blackday (below) |
| sgm_effects | satiety counter (timer 13-21 s via sgm_flags), sleep wake-up logic, vertigo/shock pp effectors, auto energy drink | per frame |
| sgm_value_work.values_update | long if/elseif chain zeroing expired sgm_flags timers; bank percent at game hour 19/23 | cheap |
| sgm_world.update_spawn | ~94 `has_alife_info` per frame, spawns once per flag (see D) | per frame |
| sgm_info.info_work_update | derived infos, 1 distance check (limansk), `bandit_off` toggling | cheap |
| sgm_tasks.sgm_task_update | 8 distance checks (with `vector():set` alloc each), 80 has_alife_info, `is_smart_captured` -> `sim_board.smarts_by_names[...]` lookups; adds tasks via `add_task/add_eliminate_task`; spawns agroprom/yantar waves | per frame |
| sgm_reinforcement.update_reinforcement | 16 distance checks (squared dist to hardcoded points, radius 10-40) + 35 has_info | per frame (only for current level via `level.name()` branches) |
| sgm_squads.squads_update | `level.get_time_minutes()==15 or ==45` gates for explorer respawn: `get_explorers_deaths(...)` + `use_explorer_module`; condition is true for the whole game-minute (every frame, ~7.5 real seconds at time_factor 8), but each branch consumes its info flag at once so it fires once | 23 has_info + hero_in_faction scans of sim_board.players |
| sgm_news | 3 distance checks, bank percent tip at hour 20, tutorial triggers | cheap |
| sgm_creator.blackday_creator | builds 33 random artefact-name vars + 4 `math.random` every frame; spawns random artefacts only if `sgm_flags.enable_creator` | wasteful but cheap |
| sgm_sleep_places | **38 distance_to_sqr checks with `vector():set(...)` each frame** + `actor_in_sleep_zone` zone lookups; toggles `allow_sleep` pstor var and HUD static `hud_sleep_zone` | the most expensive single poller (allocation heavy) |
| sgm_callbacks.callback_for_update | reads weapon in slots 1/2 and outfit each frame (`system_ini():r_string` via sgm_functions Get* each frame for outfit) | per frame |

Per-NPC per-update (in `xr_motivator update`, every online stalker): `sgm_modules.profile_update` (loops 20-entry list), `enemy_found_tips_module` (builds 30 random tip strings + 7 `read_variable` per call, per NPC, per update), `npc_range_module`, gainer/picker modules. This is the real hot spot in large fights; do NOT port.

Per-frame blackday (sgm_blackday.black_day_sys): runs the body inside `for ... in pairs(on_level_allow)` (6 entries) so every check executes 6x per frame.

Other time-gated logic: `use_explorer_module` minute 15/45 gates (+ 10/30/59 for reset), blackday window hour `zatm_h_rnd`..., night-only sleep (hours 21-23, <6), bank interest at hour 19/20/23, `its_hide_time` night deals (xr_conditions).

### B2. State storage
| kind | where | saved? |
|---|---|---|
| quest/spawn flags (`*_spawner`, `*_spawn`, `*_allow`, `*_init`, `*_complete`...) | engine info portions via `db.actor:give_info_portion/has_alife_info` | yes (engine) |
| variables via `sgm_functions.write_variable/read_variable` (names from `функции.txt`: `actor_capital, actor_percent, actor_ptimer, actor_btimer, actor_deposit, fill_npc_time, fill_npc_enemy, zatm_h_rnd, zatm_m_rnd, zatm_timer, zatm_switch, allow_sleep, satiety_factor`) | `db.storage[actor_id].pstor[name]` (sgm_functions.pstor_store) | yes: `xr_logic.pstor_save_all` called from `actor_binder:save` (SGM did not add any save code); supports number/bool/string; verify key set in SRP version lines 955-1000 (number: s32/u32/float; string; bool handled) |
| `sgm_flags.*` (~60 timers: doctor_/picker_/defender_/move_/theatre_/launcher_/satiety_/sleep_value...), `victim_*`, `enable_creator`, `old_wpn1/2` | module-level Lua variables of `sgm_flags` | NO (reset on load; all timers are relative to `time_global()` so reset is harmless) |
| `sgm_modules.profiles_ids/profiles_names` (profile -> object id) | local tables | NO. Rebuilt from online NPC updates and from `create()` (create_update_one_list, 30 entries). After load an offline NPC is unknown to `target_profile` tasks. |
| map spots (`level.map_add_object_spot_ser`) | engine | yes (engine) |

Savegame risks (engine facts unverified at runtime, flagged):
* `zatm_timer` / `fill_npc_time` are absolute `time_global()+N` values stored in pstor. If `time_global()` restarts at 0 in a new game session (X-Ray behaviour, unverified here), a loaded save from an older session may keep the blackday "active" for a very long time or until timer passes. Port should store game-time (`game.get_game_time()`) instead.
* Adding ~744 info portions adds to the save (small) and, when the addon is removed from a save in progress, unknown ids are read by engine; (addon ecosystem already depends on this).
* Spawned quest NPCs are real alife objects (saved); their logic ltx path `custom_data = scripts\SGM\...ltx` is stored in the save-object custom data as a file reference? (unverified: if the file is missing on load, `xr_logic` aborts on missing ltx).
* No SGM data is added to the actor packet, so no save format change is needed (unlike our on_save/on_load); we can keep that property by using info portions + pstor only.

---------------------------------------------------------------------------------------------------

## C. Dialog system

### C1. How dialogs reach NPCs
1. `system.ltx [dialogs] files` loads `sgm_dialogs.xml` (74 `<dialog>` with classic phrase_list + `precondition/action/give_info/has_info/dont_has_info` nodes). Four of them (`gar/val/agr/yan_breeder` artefact-breeding) are built in Lua through `<init_func>sgm_phrases.<lvl>_breeder_dialog` (`dlg:AddPhrase`...; sgm_phrases.script 7 298 lines, 4 functions).
2. Callbacks: `sgm_dialogs.script` 394 functions, ~357 distinct ones referenced from XML/phrases: prefixes breeder_* (125), bankir_* (48), actor_* (44), val_/gar_/agr_/esc_/mar_/mil_/yan_/red_/lim_ quest checks. All are module-prefixed (`sgm_dialogs.xxx`) => no core edit. They use `dialogs.relocate_item_section(...)`, `dialogs.relocate_money(...)`, all present in SRP dialogs.script (verified; only `dialogs.actor_in_csky/actor_not_in_csky` are SGM-added).
3. Attachment is via `<specific_character>`: `character_desc_sgm.xml` (113 characters) has `<start_dialog>`/`<actor_dialog>` lists; `sgm_profiles.xml` is just `character id -> class` (no dialogs). The base dialogs `dm_hello_dialog` etc. are appended to every SGM NPC.
4. SGM also modified vanilla characters by adding actor_dialogs (character_desc_*.xml): `agr_duty_base_commander (+agr_dolg_leader_extra_job)`, `agr_stalker_base_leader (+agr_stalker_base_leader_start)`, `val_freedom_trader (+val_ashot_find_dummy_give/what, val_setup_binoculars_dialog)`, `esc_leader_stalkerbase (+esc_leader_heavy_jobs, esc_leader_vector_squads)`, `esc_trader_stalkerbase (+esc_about_eliminate_blockpost)`, `esc_tech_stalkerbase (+esc_shilov_find_rukzak_give/complete)`, `esc_wolf (+esc_wolf_about_reinforcements_dialog)`, `gar_digger_messenger_man (+gar_digger_messanger_accompany_give/complete)`, `gar_digger_quester (+gar_digger_leader_rescue_reward/info_reward)`, `mar_csky_commander (+mar_csky_leader_jobs, mar_csky_leader_bye)`, `mil_hog (+mil_hog_find_item_start/complete)`, `yan_stalker_sakharov (+yan_sample_dnk_task_start/choose, yan_scientist_af_work_dialog)`, and ~60 random stalkers got the generic 10-dialog pack (tm_random_task, guiders_dialog, about_story_dialog, ...) which is just stock CS behaviour.
5. The SRP Freeplay addon already does the same trick (copies of character_desc_agroprom/darkvalley/escape/garbage/marsh/yantar with extra `actor_dialog`s: rt_*, rare_items_dialog, *_items_dialog). **Both want the same files**: if SGM quest dialogs for vanilla NPCs (escape trader, esc_leader, mar_csky_commander...) are added through character_desc copies they must be merged into the addon's existing copies (only one file per name wins). New NPCs avoid this: add a new `character_desc_sgmq.xml` through the addon's `system.ltx` (already a copy; `specific_characters_files`).

### C2. SGM NPC roster (113 `specific_character`; scripted = created via `create()` in sgm_world/reinforcement/squads/tasks; "section only" = exists in SGM_stalkers.ltx but spawned as squad member by `create_force` or by another section)
Columns: character id | community | role (heuristic from id) | has dialogs | spawn path.
Note: character id (profile) differs from spawn section name for squads (e.g. `mar_csky_specnaz1..4` profiles are reused by sections `mar_explorer_*`).

* NEW non-combat NPCs that exist only in SGM (the "new NPCs"): per level a banker (`*_bankir`: deposit with interest, pstor `actor_deposit/percent/capital`), a trader/black-market (`*_trader`, `its_hide_time` night deals), a breeder (artefact breeding via artefact items `af_*_breeding_N`; `gar/val/agr_dolg/yan` + `gar_stalker_breeder`), hireable bodyguards (`*_bodyguard_*`: defender scheme + infos `<profile>_init/pursue/nofire/stop/death`; respawn via xr_effects), squad organisers (`*_squads_commander`, spawn via `create_force`), upgrader `mil_stalker_upgrader`, medic `val_freedom_medic`, quest persons.
* Exact list generated by script follows (section "Roster").

### C3. Spawn paths summary
* 211 distinct section names are passed to `create()/create_rukzak_item()`: 192 exist ONLY in SGM configs (132 in `creatures/SGM_stalkers.ltx`, 45 in `SGM_monsters.ltx`, rest items in sgm_modificates/cevlar_plastins/sgm_quest_items/sgm_devices/sgm_deserves/outfit/artefacts/w_*.ltx), 19 are vanilla (af_*, explosive_*, medkit, military_outfit, specops_outfit, wpn_*).
* Every NPC section = `[sect]:stalker` (or `:faction_boss`) with `character_profile`, `community`, `spec_rank`, `custom_data = scripts\SGM\<level>\<name>.ltx` (verified for the first 20 sections; all 160 follow the pattern, unverified individually).

---------------------------------------------------------------------------------------------------

## D. sgm_world / sgm_squads / sgm_reinforcement / sgm_modules / sgm_creator / sgm_blackday

### D1. Function inventory
* **sgm_world.script**: `all_secrets_spawn()` (25 `create` of items/artefacts/skill books/weapons at fixed lv/gv), `all_objects_spawn/all_animals_spawn` (empty), `all_npc_spawn()` (10 NPC: mar_csky_sleeper/patrol, mar_renegate_boss, esc_camp_stalker1-4, esc_stalker_bogdanov, esc_sidorovich_guard1-2), `all_functions_spawn()` (writes initial pstor vars: zatm_*, actor_*, allow_sleep, satiety_factor). All five are `<action>` entries of info portion `start_game_poratation` (sgm_portations.xml:6-12), which `sgm_info.info_work_update` gives on the very first frame of ANY save lacking it => a one-time bundle of 25 items + 10 NPC + var init, also on existing saves, `update_spawn()` (called each frame by loader; per level:
  * marsh: `personal_rukzak`(item), `mar_renegate_baron`, `mar_csky_specnaz_leader`/`mar_csky_bankir`, `mar_rescue_soldier1-5` + `explosive_dinamit`x3 + `mar_hindrance_renagad1-6` + `explosive_mobiltank`, `mar_csky_squads_commander`, `mar_bodyguard_csky`, `mar_outpost_renegate1-2`
  * escape: `esc_tunnel_scout`, `esc_stalker_bankir`, `esc_army_polkovnik`, `shilov_rukzak`, `esc_bodyguard_stalker/novice`
  * garbage: `gar_bodyguard_freedom`, `gar_stalker_bankir`, `gar_freedom_trader`, `gar_base_rpg_bandit1-2`, `gar_bodyguard_stalker`, `gar_stalker_trader`, `gar_stalker_squads_commander`, `valley_propusk`, `gar_barier_commander`, `explosive_barrel`, `svoboda_light_outfit_up`, `gar_stalker_breeder`, `gar_tunnel_novice`
  * darkvalley: `val_bodyguard_freedom, val_freedom_bankir, val_freedom_breeder, val_freedom_rpg_tower1-3, specops_outfit, personal_rukzak, val_freedom_squads_commander, val_freedom_medic, val_freedom_guard_leader, val_freedom_7_6_commander, val_impounded_corpse, val_bus_hostage/killer, val_freedom_rpg_trooper, val_4_0_trader`
  * agroprom: `agr_bodyguard_dolg/stalker, agr_dolg_squads_commander, agr_dolg_trader, agr_stalker_trader, agr_dolg_bankir, agr_stalker_bankir, agr_dolg_breeder, agr_dolg_agent, agr_7_4_commander, agr_bandit_victim1-2, agr_exo_bandit1-2, agr_wild_giant`
  * yantar: `yan_ecolog_trader, yan_ecolog_bankir`; red_forest: `red_dolg_bankir, red_dolg_trader, af_monolit(rukzak), skill_book_svd, red_freedom_bankir, red_csky_squads_commander`; military: `mil_army_boss, mil_zombied_boss, mil_killer_trader, mil_stalker_upgrader, mil_rpg_ambush`; limansk: `lim_construction_robbery_leader`.
  Each is guarded by an info flag (`*_spawner/_spawn`, via `give_info_portion` BEFORE `create`) => one-shot and save-safe; quest-driven ones also wait for a quest info (`*_allow`, `val_pursuit_comendant_complete`, `mar_story_capture_bandit_base_reward`, `esc_kill_blockpost_leader_allow`...).
* **sgm_reinforcement.script** `update_reinforcement()`: marsh: 4 explorer groups spawned by actor entering a radius (`mar_village/crossing/railway/khutor_explorers`, sections `mar_explorer_*`, 4-3-2-4 NPC), CS force (`mar_csky_force1-4 + leader`, requires `mar_capture_pump_station_complete + mar_capture_church_complete`), `mar_spec_reinforcement1-4`, `mar_recapture_renagad1-4`; darkvalley: info `val_rpg_support_actor` by position; agroprom: `agr_base_defender1-2`, `agr_tunnel_defender*`, `agr_coverture_defender*`, `agr_rush_soldier1-3`, and edits `sim_board.smarts_by_names["agr_smart_terrain_6_4"].player_name="none"`; red_forest `red_reinforcement_rpg/3_sniper`; military bridge trigger -> `mil_rpg_ambush_allow`; limansk `lim_team_breakout1-3`; garbage depot defenders by smart capture. 16 distance checks.
* **sgm_squads.script** `squads_update()`: respawn of dead explorer groups (every 15/45 game minutes) on marsh; `use_explorer_module`/`create_info_explorer2` on escape (squads `esc_*_once_squad`, `esc_ruins_explorers_s1/2` via smart `esc_smart_terrain_6_6`), `create_force(...)` for `esc_hero_reinforcements`, `gar_capture_reinf1-2`, `gar_acceptance_reinf`, `val_after_dogs_squad`, `agr_significant_hold_up`, `agr_smart_terrain_7_4_*_squad` (+`release_force`), `agr_tunnel_once_squad`, `mil_monolith_ambush1-2`, `mil_army_ambush1-2`, `gar_depo_attackers`. All 31 squad names exist in `misc/squad_descr_sgm.ltx` (66 squads; verified; `esc_ruins_explorers_s` is a prefix + random 1/2). Squads are `sim_squad_scripted` (exists in SRP).
* **sgm_modules.script**: text tables for "X vs Y" random tips (30 strings sets); `profiles_list/scheme_update_list/release_exclude_list/create_update_one|two|three_list` (profile->id registry, map spots at creation (`create_update` is called from `_g.create`), spot types are SGM-specific); modules: `enemy_found_tips_module, npc_range_module, on_death_module, profile_update, physic_update, scheme_update, create_update, release_exclude, get_profile_id/pre_profile_id`.
* **sgm_creator.script** `blackday_creator()`: after each "blackday" ends (`sgm_flags.enable_creator==true`) spawns 1-3 random artefacts at fixed points on escape/garbage/darkvalley/agroprom (artefact name lists per level; positions hard-coded, 33 `create(...)` calls). Needs artefacts `af_vyvert, af_medusa, af_cristall_flower, af_blood, af_dummy_glassbeads, af_soul, af_fuzz_kolobok, af_electra_flash, af_cristall` (vanilla ids; SRP/addon have `fp_artefacts` system, spawn would duplicate it).
* **sgm_blackday.script** `black_day_sys()`: random daytime window per day (`zatm_h_rnd` 10-19h, `zatm_m_rnd`), only on levels marsh/escape/garbage/darkvalley/agroprom/military and only if weather starts with `default_`; sets `level.set_weather_fx("fx_blackday_clear|rain")`, info `blackday_is_active`, duration 260 000 ms real time (`zatm_timer`), next day rescheduled at hours 21-23; reduces NPC `range` (`npc_range_module`). **Overlaps with addon `fp_surge`/`fp_eclipse` (addon has `fx_eclipse_*`, info `fp_eclipse`)**: decide before porting.
* **sgm_tasks / sgm_info / sgm_news / sgm_sleep_places**: see B; sgm_tasks also spawns agroprom defense waves (`agr_n_wave*`, `agr_e_wave*`, `agr_giant_hunter1-3`) and yantar tunnel waves (`yan_tunnel_snork1-15`, `yan_tunnel_rpg`, `yan_zombie_bloodsucker`).
* **sgm_grant/modes/effects/huds/callbacks/functions/dialogs/phrases**: items & player-mode features (medals by rank, sleeping bag, repair kits, deserve (treasure) boxes `dv_*` unpack with map spots, skill books, satiety, sleeping zones). `sgm_functions.GetDeserve*`/`GetSkill*` read system.ini keys (`create_deserve_x/y/z/lv/gv`, `increasing_skill_*`) => data-driven by item sections (needs the SGM item configs).

### D2. Sections vs vanilla/SRP
* Creature sections: 132 NPC + 45 monster sections only in `SGM_stalkers.ltx` / `SGM_monsters.ltx` (and need `m_stalker*` modifications? `[stalker]` base is vanilla; SGM modified `m_stalker.ltx/m_stalker_monolith/zombied/giant/bloodsucker`: effect on NPC base stats unverified).
* Items needed by quests only in SGM: `personal_rukzak, treasure_rukzak, shilov_rukzak, valley_propusk, svoboda_light_outfit_up, skill_book_*` (the addon `fp_skills` defines the same infos `skill_book_*`: **32 info-id collisions** between sgm_portations and addon info_portions.xml (skill_book_abakan ... wincheaster1300)), `mar_quest_*`, `device_pda_*`, `dv_*`/`*_unpack`.
* SGM_monsters / mob_move: 34 NPC logic files use `active = mob_move` (monsters walking to a vertex and releasing when they see the actor), 109 use `move`, 8 `shooter`, 3 `corpse`, 3 `theatre`, 1 `picker`; plus standard `[meet@]` (40), `[defender@]` (27), `[remark@]` (6). Custom data files per level: agroprom 24+2 bodyguards+19 monsters, darkvalley 12+1+3 scenes, escape 10+2+2, garbage 11+3, limansk 4, marsh 24+1+13, military 5, red_forest 7, yantar 4+15 monsters.
* `move` scheme (xr_move.script, new): path-less: `target_type = level_vertex`, `dest_number = <level vertex id>`, `state_in_center`, `look_vertex`, `miss_center`, `stand_time`... All NPC positions in logic are raw level vertex ids => map-dependent (stock CS levels).

---------------------------------------------------------------------------------------------------

## E. Proposed addon architecture

### E1. Layering
```
addon/gamedata/scripts/
  sgmq_core.script        -- attach(mgr): subscribes on_net_spawn/on_update(reschedule 500-1000 ms)/on_item_use/on_take_from_box;
                             owns throttling + `enabled()` gate (srp_freeplay info AND not story mode?)
  sgmq_lib.script         -- ported _g helpers: create(), create_force(), release_force(), add_task, is_smart_captured..., 
                             news helpers; id registry (profile->id) saved in pstor/or rebuilt
  sgmq_quests.script      -- data-driven trigger engine (reads configs/misc/sgmq_triggers.ltx)
  sgmq_inject.script      -- injects xr_effects/xr_conditions/schemes (INJ), guarded + logged
  sgmq_dialogs.script     -- copy of sgm_dialogs (+ actor_in_csky etc.), module-prefixed
  sgmq_phrases.script     -- copy of sgm_phrases (breeder dialogs)
  sgmq_scheme_move.script (xr_move), _mob_move, _shooter, _corpse, _theatre, _picker, _defender  -- renamed copies
addon/gamedata/configs/
  misc/sgmq_triggers.ltx  -- trigger table (below)
  creatures/sgmq_stalkers.ltx, sgmq_monsters.ltx (+ include via addon system.ltx copy)
  scripts/SGMQ/**         -- NPC logic files (163)
  gameplay/sgmq_dialogs.xml, character_desc_sgmq.xml, sgmq_profiles.xml, sgmq_portations.xml
  misc/squad_descr_sgmq.ltx (+ include from addon squad_descr.ltx copy)
  ui/map_spots.xml additions
```
Add `"sgmq_core"` to `ogse_signals_addons_list.addons`. No `bind_stalker` change is needed: fp_binder already provides every signal SGM's callbacks use (`on_item_use`, `on_take_from_box`, `on_update`), and no on_save/on_load packet is needed if all state stays in info portions + pstor.

### E2. What can be a data-driven "quest triggers" module
A single trigger row type covers most of sgm_world/reinforcement/squads/tasks/info/news:

```
[trg_mar_baron]
level      = marsh
when       = +mar_renegate_baron_allow -mar_baron_spawner      ; infos
near       = -58.469,1.206,286.588 r=15                         ; optional position gate, ONE vector reused (no per-frame alloc)
smart      = mar_smart_terrain_5_8 captured_by=csky             ; optional
time       = minute in {15,45}                                  ; optional
do         = +mar_baron_spawner spawn:mar_renegade_baron@144.582,2.099,493.792,222051,89
             squad:esc_hero_reinforcements@esc_smart_terrain_5_7  task:storyline:mar_entry_csky_force:csky  info:+x -y  spot:...
once       = true
```
Candidate rows (counts by static reading): sgm_world ~90 one-shot spawns, sgm_reinforcement ~25 (position triggers + info triggers), sgm_squads ~25, sgm_tasks ~35 spawn/info/task rows, sgm_info ~8, sgm_news ~5. Evaluate only the triggers of the current level (`level.name()` index), reschedule 500-1000 ms, per-frame cost then ~0.

Needs a verb set: `spawn(sect,x,y,z,lv,gv)`, `squad(sect,smart)`, `release_squad`, `give/remove info`, `task`, `news`, `map_spot`, `set_var`, with conditions: infos, dist<r, smart captured, time-of-day/minute, `squad_spawned`, `has_item`, `faction_player`.

### E3. What needs separate handling
1. **Hard-coded lv/gv spawns** (232 call sites): move into the trigger table but still keyed to stock CS all.spawn gvid/lvid. Add a startup validator (`level.vertex_position(lv)` ~ x,y,z within 1.5 m; gv in level range) and fall back to `alife():create(sect, pos, level.vertex_id(pos), gv_of_actor_level)`; unverified that SRP shares the graph with stock CS.
2. **Custom schemes**: register via `_G.schemes[name] = "sgmq_scheme_x"` before NPC logic init. Safer: do this at the top level of a script that is loaded early; if the first NPC logic init precedes `fp_binder` attach, load order must be checked at runtime (unverified). Rename schemes (`sgmq_move`) and rewrite 163 ltx via sed to avoid `move/mob_move/...` generic name clashes with future SRP updates.
3. **NPC logic effects/conditions** (29 + 12): inject into `xr_effects`/`xr_conditions` tables from `sgmq_inject.script` (or rewrite ltx to use only vanilla-available funcs: bodyguard flow can be done with plain `%+info%` effects + our on_update reacting to infos; `actor_is_no_enemy` has a vanilla equivalent `{!actor_enemy}`).
4. **Storyline tasks with `target_profile`/`no_sid_*`**: core task layer lacks them. Options (decision for the maintainer): (a) own mini task layer calling engine `CGameTask` directly (+ `game_tasks.xml` entries from `sgmq_tasks`) and our own id registry; (b) ship a copy of `task_objects.script` + `task_manager.script` (CORE-copy; high merge risk: SRP diff is 2926 lines).
5. **Per-NPC hooks** (profile registry, death module, release protection): replace by our own registry filled in `sgmq_lib.create()` + on_update liveness polling of the tracked ids; no per-NPC update hook needed.
6. **Dialogs**: ship as new files; risk: edits of vanilla characters (esc trader/leader, mar_csky_commander, ...) conflict with the addon's own character_desc copies -> merge into those files once, or attach vanilla-NPC dialogs through `<start_dialog>`-less approach: `character_desc_sgmq` can't modify an existing character, so merging into addon copies is unavoidable. Also dialog `finish` callback in dialogs.script (reputation +70, goodwill +100) is a CORE side effect: drop.
7. **Items**: quest items/skill books/medals/deserves/devices live in SGM item ltx; skill_book_* collides with the addon's `fp_skills` (same info ids). Port only quest items needed by kept quests; don't port satiety/modes/hud/cheat-menu/sleep systems (overlap with fp_satiety, UI).
8. **Blackday**: overlaps with addon `fp_surge`/eclipse; port only if desired and store game-time not `time_global`.
9. **Save/load**: keep to info portions + pstor (existing core save path, no format change). Do not store `time_global()` values.

### E4. Risks (checked unless noted)
* Info-id clashes: sgm_portations (744) vs SRP info files: 0 clashes; vs vanilla info files: 0; vs addon info_portions.xml: 32 (skill_book_*). SGM scripts also READ 16 vanilla story infos (`agr_actor_inside_2, agr_duty_open, agr_garbage_end, agr_smart_terrain_6_4_simulation_task, esc_trader_bandits_2, gar_quest_liberate_conc_camp_done, gar_story_find_diggers_started, gar_story_got_info_from_digger, mar_story_capture_bandit_base_reward, mil_actor_go_to_limansk, mil_actor_inside_wtower, red_bridge_scene_begin, val_deliver_ammo_done, val_kill_flesh, val_kill_flesh_done, val_pursuit_comendant_complete`), SGM dialogs read 6 more (`agr_take_reward_complete, gar_quest_liberate_conc_camp_done/told, mar_story_capture_bandit_base_reward, red_bridge_down_done, yan_proriv_k_ystanovke`) and tasks 8 (`gar_flea_market_stop_quest_line, mar_story_empower_csky_done, mar_story_go_to_escape_done, mil_hog_death, val_deliver_ammo_complete...`). In Freeplay these story infos never fire (story is off) => any SGM quest that waits for them is dead unless remapped (e.g. our own trigger "reach level X / kill Y"). SGM also WRITES infos with story-ish names (e.g. `val_deliver_ammo_done` given by sgm_info, `mil_stop_invasion_5_5_complete`, `gar_story_got_info_from_digger`) which could trigger vanilla story logic in Story mode => namespace them (`sgmq_` prefix) and never give vanilla-owned names. Unresolved infos referenced by SGM scripts: `agr_smart_terrain_4_2_simulation_task_complete`, `agr_smart_terrain_6_4_simulation_task_complete`, dialogs `red_dolg_bankir_about`, `yan_ecolog_bankir_about` (not defined in portations; engine tolerates?). unverified.
* Smart-terrain dependencies: quests use `mar_smart_terrain_*`, `gar_smart_terrain_3_5`, `agr_smart_terrain_6_4/2_3`, etc., `sim_board.smarts_by_names[...]` (nil -> Lua error in `is_smart_captured`) and even write `player_name="none"` on a smart. In Freeplay sim faction behaviour differs (unverified) => capture-based triggers may never fire or fire immediately.
* `create_force` requires `sim_board.squad_ltx` sections and `board.players[faction]`; SRP sim_board has `squad_ltx = ini_file("misc\\squad_descr.ltx")` (verified), so addon `squad_descr.ltx` copy must include the new file.
* Map spots: custom spot types need `ui/map_spots.xml` entries or `level.map_add_object_spot_ser` fails.
* `custom_data = scripts\SGM\...ltx` paths: need the files present under addon `configs/scripts`.
* Performance: do not port per-frame pollers (sleep_places 38 checks, tasks/reinforcement 24 checks, enemy_found_tips per NPC).
* NPC base-class diffs: SGM changed `m_stalker*.ltx`, `stalkers.ltx` (corpse 15 h), `monsters.ltx` (10 h), `spawn_sections*.ltx` (garbage), `game_relations.ltx` (actor_stalker goodwill) => skip; verify quest NPCs behave with SRP defaults.
* Mode isolation: the addon is global; gate every trigger/injection by info `srp_freeplay` (set by `freeplay_mode.script`) so Story mode stays untouched. Injected `xr_effects/xr_conditions` and `_G.schemes` additions are global but harmless in Story mode if names are prefixed (`sgmq_`).

### E5. Suggested port order (smallest risk first)
1. Trigger engine + lib + id registry + dialogs/phrases + 1 level (e.g. escape: `esc_stalker_bankir`, `esc_bodyguard_*`, `esc_tunnel_scout`) as vertical slice; includes `xr_effects/conditions` injection and `move`/`meet` NPC logic.
2. Remaining bankers/traders/breeders/bodyguards (pure dialog + spawn + defender/move scheme).
3. Reinforcement/explorer squads (sim_squad_scripted, squad_descr_sgmq).
4. Quest chains that depend on `target_profile` tasks (needs task layer decision).
5. Optional: blackday, creator, medals, sleeping zones.

---------------------------------------------------------------------------------------------------

## Roster (generated; level | id | community | role heuristic | has dialogs | spawn path)

**test** (1)
- `test_npc` | csky | misc | dlg | section only (squad/other)
**marsh** (20)
- `mar_outpost_renegate1` | renegade | misc | - | scripted:world
- `mar_outpost_renegate2` | renegade | misc | - | scripted:world
- `mar_renegate_boss` | renegade | boss | - | scripted:world
- `mar_bodyguard_csky` | csky | bodyguard (hireable) | dlg | scripted:world
- `mar_csky_squads_commander` | csky | squad organiser | dlg | scripted:world
- `mar_csky_bankir` | csky | banker | dlg | scripted:world
- `mar_csky_sleeper` | csky | ambient | - | scripted:world
- `mar_csky_patrol` | csky | patrol | dlg | scripted:world
- `mar_csky_specnaz_rescue` | csky | squad member | dlg | scripted:world
- `mar_csky_specnaz1` | csky | squad member | dlg | scripted:reinforcement/squads
- `mar_csky_specnaz2` | csky | squad member | dlg | scripted:reinforcement/squads/world
- `mar_csky_specnaz3` | csky | squad member | dlg | scripted:reinforcement/squads/world
- `mar_csky_specnaz4` | csky | squad member | dlg | scripted:reinforcement/squads/world
- `mar_csky_force_leader` | csky | leader | dlg | scripted:reinforcement
- `mar_renegate_baron` | renegade | boss | - | scripted:world
- `mar_recapture_renagad1` | renegade | misc | - | scripted:reinforcement/world
- `mar_recapture_renagad2` | renegade | misc | - | scripted:reinforcement
- `mar_recapture_renagad3` | renegade | misc | - | scripted:reinforcement
- `mar_recapture_renagad4` | renegade | misc | - | scripted:reinforcement/world
- `mar_csky_specnaz_leader` | csky | leader | dlg | scripted:world
**escape** (16)
- `esc_tunnel_scout` | stalker | scout | dlg | scripted:world
- `esc_stalker_bankir` | stalker | banker | dlg | scripted:world
- `esc_camp_stalker1` | stalker | camp stalker | dlg | scripted:world
- `esc_camp_stalker2` | stalker | camp stalker | dlg | scripted:world
- `esc_camp_stalker3` | stalker | camp stalker | dlg | scripted:world
- `esc_camp_stalker4` | stalker | camp stalker | dlg | scripted:world
- `esc_stalker_bogdanov` | stalker | misc | dlg | scripted:world
- `esc_army_polkovnik` | army | misc | dlg | scripted:world
- `esc_specnaz_stalker1` | stalker | squad member | dlg | section only (squad/other)
- `esc_specnaz_stalker2` | stalker | squad member | dlg | scripted:world
- `esc_specnaz_stalker3` | stalker | squad member | dlg | section only (squad/other)
- `esc_specnaz_stalker4` | stalker | squad member | dlg | scripted:world
- `esc_explorer_ruins1` | stalker | explorer squad member | dlg | section only (squad/other)
- `esc_explorer_ruins2` | stalker | explorer squad member | dlg | section only (squad/other)
- `esc_bodyguard_novice` | stalker | bodyguard (hireable) | dlg | scripted:world
- `esc_bodyguard_stalker` | stalker | bodyguard (hireable) | dlg | scripted:world
**garbage** (13)
- `gar_stalker_bankir` | stalker | banker | dlg | scripted:world
- `gar_bodyguard_stalker` | stalker | bodyguard (hireable) | dlg | scripted:world
- `gar_bodyguard_freedom` | freedom | bodyguard (hireable) | dlg | scripted:world
- `gar_stalker_trader` | stalker | trader | dlg | scripted:world
- `gar_stalker_freedom` | freedom | misc | dlg | no section
- `gar_barier_commander` | freedom | commander | dlg | scripted:world
- `gar_stalker_squads_commander` | stalker | squad organiser | dlg | scripted:world
- `gar_stalker_breeder` | stalker | artefact breeder | dlg | scripted:world
- `gar_tunnel_novice` | stalker | novice | dlg | scripted:world
- `gar_depo_defender1` | stalker | defender | dlg | scripted:reinforcement
- `gar_depo_defender2` | stalker | defender | dlg | scripted:reinforcement
- `gar_base_rpg_bandit1` | bandit | RPG/ambush | dlg | scripted:world
- `gar_base_rpg_bandit2` | bandit | RPG/ambush | dlg | scripted:world
**darkvalley** (17)
- `val_freedom_bankir` | freedom | banker | dlg | scripted:world
- `val_bodyguard_freedom` | freedom | bodyguard (hireable) | dlg | scripted:world
- `val_freedom_breeder` | freedom | artefact breeder | dlg | scripted:world
- `val_freedom_squads_commander` | freedom | squad organiser | dlg | scripted:world
- `val_freedom_specnaz1` | freedom | squad member | dlg | section only (squad/other)
- `val_freedom_specnaz2` | freedom | squad member | dlg | section only (squad/other)
- `val_freedom_specnaz3` | freedom | squad member | dlg | section only (squad/other)
- `val_freedom_specnaz4` | freedom | squad member | dlg | section only (squad/other)
- `val_freedom_medic` | freedom | medic | dlg | scripted:world
- `val_freedom_guard_leader` | freedom | leader | dlg | scripted:world
- `val_freedom_7_6_commander` | freedom | commander | dlg | scripted:world
- `val_freedom_rpg_trooper` | freedom | RPG/ambush | dlg | scripted:world
- `val_impounded_corpse` | freedom | quest corpse | dlg | scripted:world
- `val_bus_hostage` | freedom | quest hostage | dlg | scripted:world
- `val_freedom_suicide` | freedom | misc | dlg | section only (squad/other)
- `val_bus_killer` | bandit | bandit/killer | dlg | scripted:world
- `val_4_0_trader` | freedom | trader | dlg | scripted:world
**agroprom** (26)
- `agr_dolg_trader` | dolg | trader | dlg | scripted:world
- `agr_stalker_trader` | stalker | trader | dlg | scripted:world
- `agr_dolg_breeder` | dolg | artefact breeder | dlg | scripted:world
- `agr_dolg_squads_commander` | dolg | squad organiser | dlg | scripted:world
- `agr_dolg_bankir` | dolg | banker | dlg | scripted:world
- `agr_stalker_bankir` | stalker | banker | dlg | scripted:world
- `agr_bodyguard_dolg` | dolg | bodyguard (hireable) | dlg | scripted:world
- `agr_bodyguard_stalker` | stalker | bodyguard (hireable) | dlg | scripted:world
- `agr_dolg_specnaz1` | dolg | squad member | dlg | section only (squad/other)
- `agr_dolg_specnaz2` | dolg | squad member | dlg | section only (squad/other)
- `agr_dolg_specnaz3` | dolg | squad member | dlg | section only (squad/other)
- `agr_dolg_specnaz4` | dolg | squad member | dlg | section only (squad/other)
- `agr_base_defender1` | stalker | defender | dlg | scripted:reinforcement
- `agr_base_defender2` | stalker | defender | dlg | scripted:reinforcement
- `agr_giant_hunter1` | dolg | hunter | dlg | scripted:tasks
- `agr_giant_hunter2` | dolg | hunter | dlg | scripted:tasks
- `agr_giant_hunter3` | dolg | hunter | dlg | scripted:tasks
- `agr_7_4_commander` | stalker | commander | dlg | scripted:world
- `agr_rush_soldier1` | stalker | rescue soldier | dlg | scripted:reinforcement
- `agr_rush_soldier2` | stalker | rescue soldier | dlg | scripted:reinforcement
- `agr_rush_soldier3` | stalker | rescue soldier | dlg | scripted:reinforcement
- `agr_dolg_agent` | dolg | quest agent | dlg | scripted:world
- `agr_exo_bandit1` | bandit | bandit | - | scripted:world
- `agr_exo_bandit2` | bandit | bandit | - | scripted:world
- `agr_bandit_victim1` | dolg | quest victim | - | scripted:world
- `agr_bandit_victim2` | dolg | quest victim | - | scripted:world
**yantar** (4)
- `yan_ecolog_trader` | ecolog | trader | dlg | scripted:world
- `yan_ecolog_bankir` | ecolog | banker | dlg | scripted:world
- `yan_tunnel_rpg` | stalker | RPG/ambush | dlg | scripted:tasks
- `yan_zombie_bloodsucker` | zombied | misc | - | scripted:tasks
**red_forest** (7)
- `red_dolg_bankir` | dolg | banker | dlg | scripted:world
- `red_dolg_trader` | dolg | trader | dlg | scripted:world
- `red_freedom_bankir` | freedom | banker | dlg | scripted:world
- `red_reinforcement_rpg` | csky | RPG/ambush | dlg | scripted:reinforcement
- `red_reinforcement2_rpg` | csky | RPG/ambush | dlg | section only (squad/other)
- `red_reinforcement3_sniper` | csky | reinforcement | dlg | scripted:reinforcement
- `red_csky_squads_commander` | csky | squad organiser | dlg | scripted:world
**military** (5)
- `mil_army_boss` | army | boss | dlg | scripted:world
- `mil_zombied_boss` | zombied | boss | - | scripted:world
- `mil_killer_trader` | stalker | trader | dlg | scripted:world
- `mil_stalker_upgrader` | stalker | upgrader | dlg | scripted:world
- `mil_rpg_ambush` | army | RPG/ambush | dlg | scripted:world
**limansk** (4)
- `lim_team_breakout1` | stalker | misc | dlg | scripted:reinforcement
- `lim_team_breakout2` | stalker | misc | dlg | scripted:reinforcement
- `lim_team_breakout3` | stalker | misc | dlg | scripted:reinforcement
- `lim_construction_robbery_leader` | monolith | leader | dlg | scripted:world


---

# Часть 2

# SGM 3.10 -> аудит квестов, группа 1 (mar_ / esc_ / gar_)

Только чтение. Всё ниже проверено чтением/grep; что не проверено - помечено "unverified".
Пути: SGM = /home/claude/kvsuadn-art/sgm/gamedata, vanilla = .../csogsm/original, SRP = /home/claude/srp/gamedata.
В `sgm_tasks.ltx` из группы 37 секций (в `[list_tm_sgm]` 36 активны: `mar_capture_watch_tower` закомментирован).

---------------------------------------------------------------------------------------------------
## 0. Сквозные зависимости (верно для ВСЕХ квестов группы; в записях ниже на них ссылаюсь как G1..G9)

**G1. Движок задач SGM правил ядро `task_objects.script` (SRP-версия его не имеет).**
- SGM: `CStorylineTask` понимает `target_profile`, `no_sid_x/y/z/lv/gv/shift` (создаёт маркер `<profile>_spot` из `misc/task_spots.ltx`
  через `alife():create`), `target_story_ids` необязателен; плюс `hide_smart_name`, `complete_info/reverse_info/fail_info`.
  `target_profile` -> `sgm_modules.get_profile_id()` (локальная Lua-таблица `profiles_ids`, наполняется при `create(...)` из `create_update_one_list`
  и из `xr_motivator -> sgm_modules.profile_update` для НПС; для предметов (`shilov_rukzak`, `valley_propusk`, `explosive_*`, `svoboda_light_outfit_up`)
  только в момент `create` -> после загрузки сейва маркер теряется, если нет `no_sid_*` fallback; unverified в рантайме, но по коду так).
- SRP `task_objects.script:1355`: `target_story_ids = cfg_get_string(..., is_mandatory=true)` и `abort` если story-объекта нет.
  **Вывод (верифицировано чтением):** подключение `sgm_tasks.ltx` как есть в SRP `task_manager.ltx` [list] = `abort` при инициализации менеджера задач
  (каждая SGM storyline-секция с `target_profile` без `target_story_ids` валит `CStorylineTask:__init`). `hide_smart_name` в SRP не поддержан (безвредно, косметика).
- SGM читает `misc\tasks\task_manager.ltx` (путь изменён в `task_manager.script`); SRP - `misc\task_manager.ltx`. Нужно включить секции в SRP-файл (в аддоне - override).

**G2. Freeplay-блокировка storyline-задач в SRP.** `SRP task_manager.script:387`: `select_task("storyline",...)` в Freeplay возвращает nil;
`xr_effects.give_inited_task` в SRP это обрабатывает (return), а SGM-овский `_g.add_task` (SGM `_g.script:1580`, в SRP такой функции нет) делает
`task:give_task(...)` без nil-проверки -> **ошибка скрипта при любом `add_task("storyline",...)` в Freeplay** (его вызывают `sgm_tasks.script`, `sgm_dialogs.script`).
`eliminate_smart` не блокируется. Также `add_eliminate_task` не проверяет nil (если `target_cond` ложно - краш).

**G3. Схема логики НПС `move`** (`xr_move.script`, НОВЫЙ файл SGM; регистрируется в SGM `modules.script`: `load_scheme("xr_move","move")`, плюс
`xr_gainer, xr_picker, xr_theatre, xr_shooter, xr_corpse, xr_doctor, xr_defender`; `xr_logic.script` SGM принудительно вызывает `xr_doctor/xr_gainer.set_scheme`).
Все `configs/scripts/SGM/**/*.ltx` НПС этих квестов (`[move@...]`, `center_info`, `dest_number` = жёстко зашитые level vertex id) работают только с этой схемой;
`xr_move` общий таймер-флаги в `sgm_flags` (один на всех НПС) и `xr_gainer.currert_gainer2`. В SRP этих схем нет (проверено списком scripts).
Для порта: либо тащить xr_move+xr_gainer+sgm_flags+sgm_modules+правки modules/xr_logic, либо переписать логику на ванильные walker/camper/remark (SRP).

**G4. Спавн.** Статичные НПС/предметы создаются `sgm_world.script` -> `create(sect,x,y,z,lv,gv)` (`_g.script:1296`: `alife():create` + `sgm_modules.create_update`);
стартовые НПС (`mar_csky_patrol`, `esc_stalker_bogdanov`, ...) - один раз через `all_npc_spawn`, который вызывается ТОЛЬКО как `<action>` инфопорции
`start_game_poratation` (sgm_portations.xml:6-12, даётся в `sgm_info.script:12`, т.е. при первом апдейте `sgm_loader.sigerous_mod_init` из `bind_stalker.script` (каждый апдейт актёра)).
Респауна нет: убитый квестодатель - навсегда. Все координаты/lv/gv зашиты (проверено по ltx: смарты из `cs_all.spawn` существуют).
Сквады: `create_force()` (`_g.script:1302`) / ванильный `=create_squad(sect:smart)` (есть в SRP `xr_effects.script:1139`, та же сигнатура); секции сквадов - `misc/squad_descr_sgm.ltx`
(подключён include в SGM `squad_descr.ltx`; в SRP/аддоне `squad_descr.ltx` надо дописать include), НПС-секции сквадов (`esc_stalker_specnaz1..4`, `gar_stalker_specnaz1..4`, `gar_depo_attacker1/2`) - `creatures/SGM_stalkers.ltx`.

**G5. Правки SGM в ванильных файлах, на которые опираются квесты (в SRP их нет, версии файлов SRP отличаются):**
- `scripts/marsh/mar_intro_zone.ltx` (+`+mar_captures_allow` при смене экспансии ЧН; +`renegade_off` на expansion_3),
- `gameplay/dialogs_marsh.xml` (фразы 912-960 Лебедева: `mar_last_intensify_*`), `gameplay/character_desc_marsh.xml` (Лебедев `mar_csky_commander` получил `actor_dialog mar_csky_leader_jobs`),
- `gameplay/character_desc_escape.xml` (+actor_dialog у `esc_leader_stalkerbase`, `esc_trader_stalkerbase`, `esc_tech_stalkerbase`, `esc_wolf`),
- `gameplay/character_desc_garbage.xml` (+диалоги у `gar_digger_messenger_man`, `gar_digger_quester`), `gameplay/dialogs_garbadge.xml` (переписан hello Напра),
- `scripts/garbage/gar_quest_line.ltx` (все задачи сюжета Свалки выдаются фракции `stalker`, а не `csky`; шаг 5 переведён с `+gar_story_got_info_from_digger` на `+gar_step_5`),
  `scripts/garbage/gar_digger_messenger_man.ltx` (ввод `+gar_step_5`, ветка `accompany`), `scripts/garbage/gar_flea_market.ltx:148` (`=gar_create_propusk` при смерти Напра),
- `xr_conditions.script` (SGM-функции `has_shilov_rukzak`, `has_valley_propusk`, `has_master_outfit`, `mar_help_rescue_fail`, `mar_rescue*_func`, `mar_plan_b*_func`, `actor_in_stalker`...), `xr_effects.script` (`add_500_stalker_relation`, `install_less_relation`, `gar_create_propusk`, `gar_send_wild_napr_message`...). В SRP этих функций нет (grep по SRP/scripts - пусто).
- `bind_stalker.script` (хук `sgm_loader.sigerous_mod_init()` + `sgm_callbacks.callback_for_update()` каждый апдейт), `xr_motivator.script` (`sgm_modules.profile_update` и др.), `sim_board.script` (`sgm_callbacks.callback_on_create_squad`).
  Для самих квестов group1 критичны `sgm_loader/sgm_tasks/sgm_world/sgm_reinforcement/sgm_squads/sgm_info` + `profile_update`.

**G6. Предметы НЕ из vanilla CS и НЕ из SRP (проверено grep по секциям `[name]`):**
`skill_book_*` (fort, ak74, mp5, pm, bm16, toz34, abakan, ak74u, commander_pm, walther, wincheaster1300, shotgun, svu; база `[skill_book]`) - работают только через SGM-систему навыков
(`sgm_callbacks.callback_for_skills` даёт инфо `skill_book_*`, `callback_on_hit` бонус урона через `sgm_functions.GetSkillInfo/Point`; без неё книга - инертный предмет);
`wpn_silencer_5.45x39`, `wpn_autocolt` (модель - ванильный colt1911, SGM-звуки `sounds/weapons/for_autocolt`), `wpn_commander_pm`, `wpn_quest_svu`, `wpn_equipment_svu` (+ SGM-апгрейды `up_gr_*_equipment_svu` и UI-шаблон `upgrade_scheme_u7a_sgm` из SGM `ui/inventory_upgrade*.xml` - это не секция, а UI-шаблон; без него окно апгрейдов этого ствола не откроется),
`shilov_rukzak`, `valley_propusk` (sgm_quest_items.ltx), `svoboda_light_outfit_up` (outfit.ltx; апгрейды `up_*_svoboda_light_outfit` есть в vanilla), `repair_outfit_box`, `personal_rukzak`, `treasure_rukzak` (sgm_devices.ltx),
`dv_army_sviridov_case`, `dv_renegade_baron_case`, `dv_csky_kovalenko_case`, `dv_freedom_zvagincev_case` (sgm_deserves.ltx, "тайники" через `sgm_callbacks.callback_for_deserves`).
Есть в vanilla (SRP использует vanilla-fallback): `cs_heavy_outfit`, `stalker_outfit`, `flesh_up_ac_mp5` (upgrade_items.ltx), `medkit`, `medkit_army`, `medkit_scientic`, `af_dummy_battery`, `explosive_dinamit/mobiltank/barrel`, `ammo_7.62x54_7h14`.
Меши из vanilla (`dev_rukzak.ogf`, `wpn_colt1911`) есть; иконки (`inv_grid_x/y`) SGM-овских предметов лежат в SGM `textures/ui` - проверять отдельно (unverified).

**G7. Тексты.** Названия/описания задач - `configs/text/rus/SGM_tasks.xml` (все 36 id+_text найдены), диалоги - `SGM_xml_dialogs.xml` (все строки найдены; `dm_intro_9`, `dm_about_16` - ванильные, есть в SRP eng/ vanilla rus), имена НПС - `SGM_character_names.xml`.
Только rus; в SRP основной язык eng -> нужен перевод. Регистрация инфопорций/диалогов/профилей идёт через SGM `system.ltx` (`sgm_portations`, `sgm_dialogs`, `sgm_profiles`, `character_desc_sgm`): аддон `freeplay_extras` уже имеет свой `system.ltx`, `squad_descr.ltx` и `character_desc_{escape,garbage,marsh,...}.xml` - придётся мёржить.

**G8. Общий механизм выдачи и фейла.** Диалог даёт инфопорцию `*_start` -> `sgm_tasks.script::sgm_task_update` (каждый апдейт, защищён `*_init`) -> `add_task("storyline",id,faction)` / `add_eliminate_task(...)`.
Цепочки внутри ltx: `on_complete = %=give_inited_task(storyline:next:faction)%`. Награда `reward_money/reward_item` выдаётся ванильным менеджером; часть наград - в действии диалога (`sgm_dialogs.script`).

**G9. Фейл по сюжету.** Все Marsh-квесты имеют `{+mar_story_go_to_escape_done} fail` (ванильная инфа сюжета; в SRP ставится в `esc_quest_line.ltx:8`, в Freeplay не ставится по комментарию SRP - значит условие просто не срабатывает).

---------------------------------------------------------------------------------------------------
## MARSH (Болота)

### M1. mar_capture_pumping_station / mar_capture_church  (primary, eliminate_smart, фракция csky)
1. «Выбить ренегатов из насосной станции» / «Очистить старую церковь от ренегатов» - захват смартов `mar_smart_terrain_5_8` (насосная, (-3.8,3.1,6.3)) и `mar_smart_terrain_8_11` (церковь, (286,-0.7,-160)); оба есть в spawn.
2. Выдача: без НПС. `sgm_tasks.script`: церковь - при инфо `mar_captures_allow` (даётся ТОЛЬКО правкой SGM в `mar_intro_zone.ltx`, строки 87/89 -> в SRP не будет), насосная - после `mar_capture_church_complete` либо когда актёр подошёл к одной из 3 зашитых точек у станции (радиус 5 м). `add_eliminate_task`.
3. Награда: +100 goodwill ЧН (`community_relation_delta_complete`). Побочно на `on_complete/reversed/fail` ставят `+mar_capture_*_complete +mar_story_empower_csky_done`.
   Параллельно `sgm_tasks` САМ даёт `mar_capture_*_complete`, если смарт уже у csky.
4. Зависимости: `task_objects` SGM-ключи не нужны (eliminate_smart ванильный; `hide_smart_name` косметика); приоритеты 14/15 > sim-задач (prior 0 в SRP `tm_sim.ltx`), поэтому `select_task` выбирает именно эти секции. Отряды-захватчики `mar_explorer_*` (sgm_reinforcement/sgm_squads, жёсткие координаты) с квестом не связаны жёстко.
5. Сюжет: задаёт ванильную инфо `mar_story_empower_csky_done` (в vanilla/SRP её ставит/снимает логика `mar_intro_zone` при смене экспансии - SGM ставит напрямую, возможен конфликт: SRP-логика снимает `-mar_story_empower_csky_done`). Награда 3000 ванильной story-задачи `mar_story_empower_csky` может быть выдана досрочно. В Freeplay война ЧН/ренегатов идёт симуляцией (`start_sim`), eliminate_smart там работает; фракция-аргумент csky при актёре без фракции - unverified.
6. Дефекты: `mar_capture_watch_tower` не в списке, секция мёртвая. `elseif`-цепочка в `sgm_task_update` даёт только одну из pump/church-инфо за апдейт (нормально). Нет защиты от nil в `add_eliminate_task` (см. G2).
7. Вердикт: **ADAPT-S, для Freeplay** (убрать `+mar_story_empower_csky_done`, дать `mar_captures_allow` из своей логики/`sgm_tasks`, оставить сами секции). Ценность невысокая (дублирует sim).

### M2. mar_capture_boat_station / mar_capture_embankment / mar_capture_north_khutor / mar_last_intensify_reward  (additional)
1. «Захватить лодочную станцию» (`mar_smart_terrain_3_3`), «Захватить стоянку под насыпью» (`7_3`, (149,2.3,494)), «Захватить северный хутор» (`12_2`, (600,2.7,431)); «Получить екстра вознаграждение» (за полный контроль над болотом). Смарты есть в spawn.
2. Выдача: диалог Лебедева (`mar_csky_commander`, ванильный НПС) - фразы 912-917 в SGM-правленном `dialogs_marsh.xml` (+дубликат `mar_csky_leader_jobs` в sgm_dialogs.xml:426), условие `+mar_story_capture_bandit_base_reward` (ванильная награда сюжетного захвата базы 10_5) и `-mar_last_intensify_talk`; даёт `mar_last_intensify_talk` + `mar_last_intensify_start`. Далее `sgm_tasks`: по одному таску за апдейт (init4->5->6), затем reward-таск (`add_task("storyline",...)`).
3. Награда: +100/+100/+150 goodwill; финал: +400 goodwill, 4000 RU, `cs_heavy_outfit`, `flesh_up_ac_mp5`, `medkit_scientic`, `skill_book_mp5`.
4. Зависимости: G1/G2 (`mar_last_intensify_reward` - storyline без `target_story_ids`/`target_profile` -> abort в SRP); правка G5 dialogs_marsh/character_desc_marsh; `skill_book_mp5` (G6).
5. Сюжет: Story-only по гейту `mar_story_capture_bandit_base_reward` (в Freeplay задача `mar_story_capture_bandit_base` - capture_smart, раздаётся ли она в Freeplay - unverified). В Freeplay без смены гейта недостижимо.
6. Дефекты (верифицировано): (a) `mar_capture_north_khutor.target_cond = {-mar_capture_embankment_complete ...}` - копипаст, должен быть `north_khutor_complete`; сейчас сработает штатно только потому, что три таска выдаются подряд; если насыпь уже захвачена/complete -> `select_task` вернёт nil -> `add_eliminate_task` падает (G2). (b) `mar_last_intensify_reward.on_complete` и `reversed/fail` все ставят `mar_intensify_reward_complete` (нормально). (c) цепочка init4/5/6 одним `elseif` - по таску на апдейт, без проверки, захвачены ли смарты (если уже у csky - таск сразу `reversed`/complete без награды за захват, но финал всё равно выдастся).
7. Вердикт: **ADAPT-M, Freeplay+Story**: заменить гейт на свою инфо (напр. `mar_captures_init2`/по времени), reward-таск заменить диалоговой наградой (выдавать в диалоге Лебедева), исправить target_cond. Хорошая награда, но sim-захваты дублируют ванильную войну ЧН.

### M3. mar_entry_csky_force -> mar_meet_csky_force -> (mar_hold_renagade_base: МЁРТВЫЙ)
1. «Встретится с отрядом ЧН» («с карательным отрядом ЧН, для захвата фермы»), «Присоединиться к отряду» («поговорив с лидером»), «Удержать ферму до прибытия подкрепления».
2. Выдача: скрипт. `sgm_reinforcement`: при `mar_capture_pump_station_complete + mar_capture_church_complete` -> инфо `mar_csky_force_spawner`, спавн 4 бойцов `mar_csky_force1-4` и лидера `mar_csky_force_leader` у фермы ((464-472,0.4-1,134-142), gv 96, профиль `mar_csky_force_leader`); `sgm_tasks`: `add_task("storyline","mar_entry_csky_force","csky")`.
3. Шаги: подойти на 10 м (`mar_entry_csky_force_see`, ставится логикой лидера `on_actor_dist_le_nvis`) -> диалог `mar_csky_force_leader_start` (за 500 RU - `mar_csky_force_talk_a` + спавн 4 спецподкреплений `mar_spec_reinforcement1-4` в (392-396,0.7,100-107) gv 95; бесплатно - `talk_b`) -> `mar_csky_force_talk_end` -> `mar_meet_csky_force_complete` (создаёт `mar_csky_squads_commander` (42.6,3.06,-232) + 2 ренегатов-аутпоста) -> отряд штурмует базу (vertex 411937) -> `mar_entry_csky_force_free`.
   `mar_hold_renagade_base`: выдача закомментирована (`sgm_tasks.script:31`), `mar_hold_renagade_base_complete` не ставится нигде; но `mar_hold_renagade_base_init` по-прежнему спавнит 4 ренегатов-перехватчиков `mar_recapture_renagad1-4` ((458-470,1.3-1.5,355-360) gv 128/129; их смерть ставит `mar_renagade_base_capture`, не используется нигде).
   Награда: нет (только фейл/completion-инфо; +500 RU вычитается у игрока).
4. Зависимости: G1,G3 (логика `move@`), G4, `target_profile=mar_csky_force_leader` + `no_sid` (463.9,0.37,133.7), `task_spots.ltx`, профили `mar_csky_force_leader`, `mar_csky_specnaz1-4`, `mar_recapture_renagad1-4`; `target_story_ids = 310` (смарт 10_5, есть в spawn) у мёртвого hold.
5. Сюжет: Story-only: все логики НПС содержат `{+mar_story_capture_bandit_base_reward} nil`, задачи `complete` при этой инфо, штурм = ванильный сюжетный захват базы 10_5 (`mar_story_capture_bandit_base`). Freeplay: бессмысленно (ЧН воюют симуляцией).
6. Дефекты: hold-задача мертва; `mar_entry_csky_force_free` игнорирует, дошёл ли отряд (на `in_center` любого бойца); 500 RU списываются до проверки результата; лидер при `talk_a/talk_b` уходит в `no_meet`, повторный диалог невозможен.
7. Вердикт: **SKIP для Freeplay; Story: ADAPT-L** (низкая ценность - сцена ради ванильного захвата 10_5, плюс подтягивает схему `move`).

### M4. mar_csky_find_baron -> mar_csky_kill_baron -> mar_csky_reward_baron  (additional)
1. «Найти лидера ренегатов "Барона"» («Отправиться к ЖД») -> «Нейтрализировать "Барона"» -> «Вернуться на базу ЧН, и поговорить с "Патрульным"».
2. Выдача: НПС «Патрульный» `mar_csky_patrol` (csky, ранг 210, (-186,0.5,-301), gv 135; спавн `all_npc_spawn`), `actor_dialog mar_csky_patrol_extra_jobs` (sgm_dialogs.xml:352): фразы -> `mar_renegate_baron_allow` + `mar_csky_patrol_info` + действие `sgm_dialogs.mar_csky_kill_baron` = `add_task("storyline","mar_csky_find_baron","csky")`. Без сюжетного гейта.
3. Шаги: `sgm_world`: при `mar_renegate_baron_allow` спавн `mar_renegate_baron` (renegade, ранг 300, (144.6,2.1,493.8), gv 89 - рядом со смартом 7_3, `sit_ass`); find завершается инфо `mar_renegate_baron_see` (<=70 м, логика Барона) ИЛИ `..._death`; kill - `mar_renegate_baron_death` (on_death); report - диалог `mar_csky_patrol_start_dialog` фразы 300/301: `mar_renegate_baron_complete` + действие `treasure_manager.give_treasure("mar_treasure_18")` (ванильный тайник Болот: antirad, 2 medkit, 5 bandage, wpn_pb). Награда таска: 2000 RU + `skill_book_pm`, `skill_book_bm16`. Дроп с Барона: `dv_renegade_baron_case`.
4. Зависимости: G1-G4, профили `mar_csky_patrol`, `mar_renegate_baron` (в `profiles_list`), `no_sid` маркеры `mar_csky_patrol_spot`/`mar_renegate_baron_spot`, логика `scripts/SGM/march/mar_renegate_baron.ltx` (схема `move`), `mar_csky_patrol.ltx` (3 ветки `move@going` и `switch_start`), строки sgm_dialogs, `dv_*`, skill books.
5. Сюжет: НЕ требует сюжетных инфо (кроме `fail` на `mar_story_go_to_escape_done`). Подходит в Freeplay по смыслу (Болота, ЧН база).
6. Дефекты: (a) `treasure_manager.give_treasure` в SRP делает `abort`, если ящик занят другим активным тайником (SRP `treasure_manager.script:241-250`); (b) Патрульный и Барон не респавнятся - убит -> цепочка навсегда недоступна; (c) в Freeplay `add_task("storyline")` = ошибка (G2); (d) `find`-таск закрывается и по `death` (убили издали) - ок; (e) `mar_treasure_18` берётся из vanilla `treasure_marsh.ltx` (в SRP-копии нет, работает fallback - проверить, что include `treasure_marsh.ltx` не потерян в аддоне).
7. Вердикт: **ADAPT-M, Freeplay+Story** - лучший кандидат на Marsh: самодостаточен. Нужно: Freeplay-выдача (без storyline/или своя) , замена `target_profile` на что-то поддержанное SRP, логика Барона на ванильных схемах, перевод строк, замена skill_book'ов на предметы SRP/Freeplay.

### M5. mar_accompany_rescue_meet / _talk / _island / _home  (additional, цепочка из 4)
1. «Встретится c остатками отряда ЧН» («Отправиться на север... может быть в опасности») -> «Поговорить с лидером отряда» -> «Довести отряд к острову с валунами» -> «Сопроводить отряд к рыбацкому хутору» (потери недопустимы).
2. Выдача: НПС `mar_csky_specnaz_leader` («Орлов», ранг 1200, (-175,0.42,-289), gv 135) спавнится ТОЛЬКО при `mar_story_capture_bandit_base_reward` (sgm_world:~80), `actor_dialog mar_specnaz_leader_jobs` (sgm_dialogs.xml:516): `mar_rescue_specnaz_allow` + `mar_rescue_specnaz_start`; `sgm_tasks` -> `add_task("storyline","mar_accompany_rescue_meet","csky")`.
3. Шаги: спавн 5 бойцов `mar_rescue_soldier1-5` (~(99-108,1-1.5,339-345), gv 84), 3 динамита `explosive_dinamit` (физобъекты), 6 ренегатов `mar_hindrance_renagad1-6` (в (-67..-59,0.6,-90..-84), gv 27/64; `smart_terrain = mar_smart_terrain_3_7`); подойти (<10 м, `mar_rescue_specnaz_see`) -> диалог `mar_rescue_leader_start` (план A/B: `plan_a`/`plan_b`) -> бойцы по зашитым level vertex идут к камням, ставят динамит (состояние `dynamite`, есть в SRP `state_lib.script`), `mar_rescue_specnaz_step_0_end` -> второй этап: цель `explosive_mobiltank` (спавн (31,3.08,-249.3), gv 2 - у базы ЧН) -> `mar_rescue_specnaz_rescue`.
   Награда: +200 goodwill, 5000 RU, `af_dummy_battery`, `wpn_silencer_5.45x39`, `skill_book_toz34`.
4. Зависимости: G1,G3 (5 логик `mar_rescue_soldier*.ltx` на `xr_move`, `center_info`-синхронизация), `xr_conditions` (`mar_help_rescue_fail`, `mar_rescue1..5_func`, `mar_plan_b1..5_func` - в SRP отсутствуют), профили `mar_csky_specnaz_rescue`, `mar_csky_specnaz1-4`, `mar_recapture_renagad1/4`, dinamit/mobiltank, SGM-звук `characters_voice\scenario\yantar\yan_levsha_hello_actor`.
5. Сюжет: Story-only по гейту giver'а; в Freeplay недостижим без полной замены гейта.
6. Дефекты (верифицировано в ltx): (a) «сопровождение» не принуждается: бойцы идут по таймерам (`on_timer 150000 | move@go_home`), `mar_rescue_specnaz_rescue` ставится как только ПЕРВЫЙ боец дошёл до `go_home` (center_info), актёр может не идти; (b) фейл при гибели любого бойца (`mar_help_rescue_fail`); (c) в логике бойцов лишняя зависимость `{+esc_actor_inside_traders_dung} nil` (ванильная инфо Кордона); (d) `play_dir = csky_idle` - неизвестный ключ (в SRP state_lib нет `csky_idle`, unverified); (e) цели task'ов `island`/`home` = физобъекты `explosive_dinamit`/`explosive_mobiltank`, зарегистрированные только при `create` (после загрузки сейва маркера нет, `no_sid` не задан); (f) спавн ренегатов-помех идёт в смарт `3_7` (его владелец в Freeplay - unverified).
7. Вердикт: **SKIP для Freeplay; Story: ADAPT-L** (самая тяжёлая цепочка; скриптованный отряд на vertex-id).

---------------------------------------------------------------------------------------------------
## ESCAPE (Кордон)

### E1. esc_kill_blockpost_leader -> esc_kill_blockpost_talk  (primary)
1. «Нейтрализировать Свиридова винтовкой СВУ» («для получения признания и прохода на базу к сталкерам») -> «Поговорить с Богдановым» (доложить об устранении полковника).
2. Выдача: НПС `esc_stalker_bogdanov` (stalker, ранг 800, (21.3,0.32,276.5), gv 520; `all_npc_spawn`), `start_dialog esc_stalker_bogdanov_start_dialog` (sgm_dialogs.xml:1494) - фразы 100-108: `esc_kill_blockpost_leader_allow` + `..._start` и действие `esc_bogdanov_in_svu` (выдаёт `wpn_quest_svu` + `ammo_7.62x54_7h14`). `sgm_tasks` -> `add_task("storyline","esc_kill_blockpost_leader","stalker")`.
3. Шаги: `esc_army_polkovnik` (army, ранг 1200, спавн при `..._allow`: (-150.5,-30.4,-350.5), gv 564 - рядом с кострами смарта 3_16 (-133,-29.7,-382)) убить -> on_death `esc_kill_blockpost_leader_killed` -> task complete + `esc_kill_blockpost_leader_complete` -> следующий таск; диалог Богданова (фразы 300-304) -> `esc_kill_blockpost_leader_reward`, СВУ забирается (`esc_bogdanov_out_svu`). Награда: `skill_book_fort`, +500 goodwill сталкерам; дроп `dv_army_sviridov_case`.
4. Зависимости: G1,G3,G4; профили `esc_army_polkovnik`, `esc_stalker_bogdanov`; `wpn_quest_svu`; `add_500_stalker_relation` (xr_effects SGM); `install_less_relation` (штраф при убийстве Богданова актёром); `skill_book_fort`.
5. Сюжет: не требует сюжетных инфо Кордона, НО смысл («проход на базу») - SGM-специфичная ограда базы: `sgm_tasks.script:63-71` - если нет `esc_kill_blockpost_leader_reward` и актёр входит в радиус ~4.5 м двух точек у входа в базу сталкеров - **безусловный штраф -2500 goodwill сталкеров** (один раз, независимо от того, брал ли квест). В Freeplay/сюжете SRP база открыта -> штраф надо выкинуть.
6. Дефекты: требование «винтовкой СВУ» не проверяется (complete по смерти от кого угодно, даже от НПС); штраф -2500 безусловный (верифицировано); Свиридов - одиночка на посту с `guard`-патрулём между 2 вертексами (схема `move`), не взаимодействует с ванильными военными смарта 3_16 (в SRP есть `esc_smart_terrain_3_16_military_2_squad_0..4`).
7. Вердикт: **ADAPT-M, Freeplay+Story** (переписать выдачу под Freeplay; убрать штраф; НПС на ванильных схемах). Ценность средняя.

### E2. esc_take_equipments -> esc_capture_army_blockpost  (additional)
1. «Взять снаряжение у торговца» -> «Захватить военный блокпост» (выбить военных из главного блокпоста на юге Кордона, смарт `esc_smart_terrain_3_16`).
2. Выдача: диалог `esc_leader_heavy_jobs` (у ванильного `esc_leader_stalkerbase`, precondition `dialogs.actor_in_stalker`) -> `esc_eliminate_blockpost_start` -> `add_task("storyline","esc_take_equipments","stalker")` (target_story_ids=438: ванильный `esc_trader_stalkerbase`, есть); диалог торговца `esc_about_eliminate_blockpost`: выдача `wpn_equipment_svu`, `ammo_7.62x54_7h14`, 2x`medkit_army` + `esc_eliminate_blockpost_talk` -> `esc_eliminate_blockpost_needs` -> `add_eliminate_task("eliminate_smart","esc_capture_army_blockpost","stalker","esc_smart_terrain_3_16")`.
3. Подкрепление: `sgm_squads`: при `esc_eliminate_blockpost_talk` сквад `esc_hero_reinforcements` (7 `esc_stalker_specnaz*`, цель 3_16) создаётся в смарте `esc_smart_terrain_5_7`; Волк (`esc_wolf`) диалогом `esc_wolf_about_reinforcements_dialog` - ещё 2 сквада `esc_wolf_novices1/2` в `esc_smart_terrain_2_12`. По завершению/реверсу/фейлу: `+esc_eliminate_blockpost_complete =create_squad(esc_army_blockpost_explorers:esc_smart_terrain_2_12)`.
   Награда: 3000 RU, `stalker_outfit`, `wpn_autocolt`, `skill_book_abakan`, `skill_book_ak74u`, +300 goodwill.
4. Зависимости: G1(для первой storyline - `target_story_ids` у неё есть => в SRP не падает), G2, squad_descr_sgm, `SGM_stalkers.ltx` (`esc_stalker_specnaz1-4`), `wpn_equipment_svu`(SGM upgrades), `wpn_autocolt`, skill books, `dialogs.actor_in_stalker` (есть в SRP `dialogs.script:162`), правки character_desc_escape (G5).
5. Сюжет: гейт - членство в сталкерах (`actor_in_stalker`). Выход в Freeplay: может ли игрок вступить к сталкерам в Freeplay - unverified (SRP `faction_stalker.ltx:24` с `+srp_freeplay` намекает, что да). Смарт 3_16 с армией есть в SRP.
6. Дефекты: `condlist_0 = {=actor_on_level(garbage)} fail` -> уход на Свалку фейлит задачу, но `on_fail` всё равно ставит `esc_eliminate_blockpost_complete` и спавнит `esc_army_blockpost_explorers` (т.е. «захват» засчитывается без захвата); `esc_hero_reinforcements` спавнятся один раз (`esc_smart_3_16_once_squad`), если вырезаны - повтора нет; `squad_descr` секции без `auto_id` - повторный `create_squad` с тем же id невозможен.
7. Вердикт: **ADAPT-M, Freeplay+Story**; eliminate-часть и награда ценны (простая «зачистка блокпоста»).

### E3. esc_shilov_find_rukzak -> esc_shilov_talk_rukzak  (additional)
1. «Найти рюкзак Шилова» («забрать в лагере одиночек рюкзак заказчика») -> «Вернуть рюкзак Шилову».
2. Выдача: диалог `esc_shilov_find_rukzak_give` у `esc_tech_stalkerbase` (механик, story 437; precondition `actor_in_stalker`) -> `esc_shilov_find_rukzak_allow` (ставится ДО согласия) и `..._start` (после); `sgm_tasks`: `add_task("storyline","esc_shilov_find_rukzak","stalker")`.
3. Шаги: `sgm_world`: при `_allow` спавн `shilov_rukzak` (device_pda, `quest_item`) в (-200.7,-16.6,-160.8), gv 569 (рядом со смартом 2_12 (-196,-20,-147)); подобрать (`has_shilov_rukzak` в xr_conditions) -> диалог `esc_shilov_find_rukzak_complete` (`give_shilov_rukzak` + `..._reward`). Награда: 2000 RU, `medkit`, `skill_book_commander_pm`.
4. Зависимости: G1/G2, предмет `shilov_rukzak` (sgm_quest_items.ltx + иконка + строки `st_shilov_rukzak*`), `has_shilov_rukzak` в xr_conditions; `target_profile = shilov_rukzak` без `no_sid` (маркер теряется после загрузки: профиль-ID хранится только в памяти, G1).
5. Сюжет: независим; нужен только `actor_in_stalker` (можно снять).
6. Дефекты: `allow` ставится на фразе до выбора -> при отказе рюкзак уже заспавнен (безвредно); второй таск без `no_sid` и без маркера для `target_story_ids=437` - ок (437 есть).
7. Вердикт: **ADAPT-S, Freeplay+Story** - простейший fetch-квест; заменить storyline-выдачу и книгу; рекомендую брать.

---------------------------------------------------------------------------------------------------
## GARBAGE (Свалка)

> Цепочка G1-G3 ниже заменяет ванильный финал Свалки (`gar_story_got_info_from_digger` -> `gar_story_go_to_freedom`) и требует ванильных инфо Напра.
> Все задачи в SGM выдаются фракции `stalker` (и в `gar_quest_line.ltx` ВСЕ ванильные сюжетные таски Свалки переведены на `stalker`).

### GA1. gar_wild_napr_talk -> gar_wild_napr_assistance -> gar_wild_napr_get_info -> gar_get_propusk_having_talk -> gar_find_valley_propusk (+ запасные gar_fail_valley_propusk, gar_searched_commander_body)
1. «Поговорить с лидером диггеров» (Дикий Напр на барахолке) -> «Содействовать лидеру диггеров» (освободить ребят из концлагеря) -> «Получить нужную информацию от Напра» -> «Поговорить с командиром местного барьера» -> «Подобрать пропуск» (в постовой кабинке на кладбище техники). Запасные: «Забрать пропуск у погибшего Напра», «Обыскать тело лейтенанта Звягинцева».
2. Выдача: `gar_quest_line.ltx` (SGM-правка): `on_info {+gar_step_5}` -> `=gar_send_wild_napr_message =give_inited_task(storyline:gar_wild_napr_talk:stalker) +gar_digger_allow_dialogs`; `+gar_step_5` ставит логика ванильного НПС `gar_digger_messenger_man` (SGM-правка `gar_digger_messenger_man.ltx`, вместо `+gar_story_got_info_from_digger`).
3. Шаги: talk - `gar_wild_napr_talk_complete` (SGM-правка hello Напра в `dialogs_garbadge.xml:1199`, требует `gar_digger_allow_dialogs`); assistance - complete по ванильным `gar_quest_liberate_conc_camp_done`+`..._told` (сюжет Напра), on_complete спавнит сквад `gar_stalker_reinforcements` (смарт `gar_smart_terrain_5_8`); get_info - диалог `gar_digger_leader_info_reward` (`gar_barier_commander_allow` -> спавн `gar_barier_commander` (248.4,0.5,140.8, gv 286, freedom, носит `valley_propusk` и `skill_book_svu` и `dv_freedom_zvagincev_case`); награда: `wpn_silencer_5.45x39`+2 `medkit_army`) + сквад `gar_rush_reinforcements` (смарт 3_5); диалог командира `gar_barier_commander_start_dialog`: `gar_propusk_allow` -> спавн `valley_propusk` (-43.1,0.54,-205.4, gv 258) + `gar_get_propusk_having_talks`; подобрать пропуск (`has_valley_propusk`) -> выдаётся ванильная `gar_story_go_to_freedom` (фракция csky!) + `+gar_actor_has_valley_propusk`; `sgm_info.script`: на `darkvalley` -> `gar_story_got_info_from_digger` (разблокирует ванильную логику Долины). Запасные ветки: Напр умер (`gar_flea_market_stop_quest_line`, `=gar_create_propusk` в `gar_flea_market.ltx:148`) -> `gar_fail_valley_propusk`; командир убит (`gar_barier_commander_fail`) -> `gar_searched_commander_body`.
4. Зависимости: всё из G1-G6 + все G5-правки Свалки; маркеры `no_sid` у commander (248.4,0.535,140.75).
5. Сюжет: Story-only (жёстко вшит в финал Свалки, требует ванильные `gar_quest_liberate_conc_camp_*`); в Freeplay инфо Напра не ставятся (в SRP trade-конфиги Свалки отдельно проверяют `+srp_freeplay`, значит в Freeplay `gar_quest_liberate_conc_camp_done` не выставляется - верифицировано grep'ом SRP).
6. Дефекты: (a) `gar_fail_valley_propusk.target_profile = "logic@work5, gar_smart_terrain_6_3"` - это gulag-job, а не профиль: SGM-ветка `target_profile` его не разбирает -> target=nil (нет маркера); (b) `gar_create_propusk` без guard - дубль `valley_propusk` (на кладбище и/или у командира); (c) `gar_get_propusk_having_talk` и `gar_searched_commander_body` - тот же комплект `no_sid`; (d) выдача фракции `stalker` при актёре-csky (SRP story): `give_task("stalker")` для не-сталкера - unverified.
7. Вердикт: **SKIP** (Freeplay невозможно, Story - конфликтует с ванильным финалом Свалки; ADAPT-L только если сознательно переделывать сюжет).

### GA2. gar_digger_messanger_accompany -> gar_digger_messanger_reward
1. «Сопроводить Васяна на "блокпост-приемник"» -> «Поговорить с Васяном».
2. Выдача: диалог `gar_digger_messanger_accompany_give` у ванильного сюжетного НПС `gar_digger_messenger_man` (Васян), precondition `smart_terrain_5_8_is_captured` (смарт `gar_smart_terrain_5_8` захвачен stalker); инфо `..._allow` -> спавн `explosive_barrel` (физобъект-цель) (37.7,0.48,-304.4) gv 261; `..._start` -> `add_task("storyline","gar_digger_messanger_accompany","stalker")`.
3. Шаги: Васян сам бежит (`move@accompany`, state sprint) к вертексу 198307 и ставит `gar_digger_messanger_accompany_moved` (center_info) -> диалог `..._complete`: 1600 RU + `repair_outfit_box` + `skill_book_walther`. Фейл - если Васян стал врагом (`+gar_digger_messanger_accompany_fail`).
4. Зависимости: G1-G5; правка ванильной логики НПС (`gar_digger_messenger_man.ltx`: убран `wounded`, добавлена ветка `accompany`, сменены инфо) и его диалогов; `repair_outfit_box` (SGM-устройство), `skill_book_walther`.
5. Сюжет: Story-only: НПС - часть сюжета Свалки (его убийство/враждебность - сюжетная инфо `gar_story_digger_killed_or_hostile`); в Freeplay состояние НПС - unverified.
6. Дефекты: «сопровождение» не принуждается (идёт сам); `explosive_barrel` как маркер без `no_sid`; конфликт с ванильным `wounded` логики.
7. Вердикт: **SKIP** (правит сюжетного НПС; ценность низкая).

### GA3. gar_find_master_outfit -> gar_reward_master_outfit
1. «Найти предмет: Мастерский «Ветер свободы»» -> «Вернуть предмет: Мастерский «Ветер свободы»» (вернуть заказчику обещанное).
2. Выдача: НПС `gar_stalker_squads_commander` (stalker, (39.8,0.41,-312.9), gv 261; спавн при `gar_quest_liberate_conc_camp_done` + смарт `gar_smart_terrain_6_3` у stalker - sgm_world, т.е. гейт сюжета Напра) диалог `gar_stalker_squads_commander_start_dialog` фразы 510-513, 520: `gar_find_svoboda_up_outfit_allow/start` + `sgm_dialogs.gar_find_master_outfit` (`add_task("storyline",...,"stalker")`).
3. Шаги: спавн `svoboda_light_outfit_up` (outfit, quest_item) в (24.0,4.59,212.7), gv 341 (лагерь Свободы) -> `has_master_outfit` (xr_conditions) -> `gar_find_svoboda_up_outfit_find` и следующий таск -> диалог (520/521): `gar_master_outfit_give` + награда 2000 RU + `skill_book_wincheaster1300`.
4. Зависимости: G1-G4; секция `svoboda_light_outfit_up` (outfit.ltx SGM: наследует vanilla `svoboda_light_outfit`; апгрейды `up_ac/bd/g_svoboda_light_outfit` есть в vanilla; строки `svoboda_light_outfit_up_name/description` - проверить, unverified), `target_profile = svoboda_light_outfit_up` + `no_sid` (23.97,4.59,212.7) (маркер есть), `has_master_outfit`.
5. Сюжет: гейт giver'а (`gar_quest_liberate_conc_camp_done`) + `actor_in_stalker` (стр. диалога 100/200 - есть ветка и для не-сталкера, но квест-ветка 510 доступна обеим); в Freeplay giver не появится.
6. Дефекты: диалог 520 `give_info gar_find_svoboda_up_outfit_complete` даётся ДО/вместе с отдачей предмета (порядок в одном phrase: precondition `gar_master_outfit_has` защищает); нет защиты, если игрок продал/потерял предмет (`can_trade=false`, `quest_item=true` - ок).
7. Вердикт: **ADAPT-M, Freeplay+Story** (независимо спавнить НПС; предмет + 2 секции). Ценность средняя.

### GA4. gar_rescue_tunnel_novice -> gar_return_tunnel_novice -> gar_reward_tunnel_novice
1. «Разискать пропавшего диггера» («на место сигнала, который получил Напр») -> «Вернуться с диггером на базу» -> «Поговорить с Диким Напром о диггере».
2. Выдача: Напр (`gar_digger_quester`, story-logic `logic@work5` в смарте `gar_smart_terrain_6_3`) - фразы 9/90/91 в переписанном SGM hello (`dialogs_garbadge.xml`): после `gar_wild_napr_get_info_end` (т.е. после GA1!) `gar_rescue_tunnel_novice_allow/start` + `sgm_dialogs.gar_rescue_tunel_novice` -> `add_task("storyline","gar_rescue_tunnel_novice","stalker")`.
3. Шаги: спавн `gar_tunnel_novice` (stalker, ранг 44, (-275.5,0.375,28.4), gv 295, `sleep_noweap`, `combat_ignore_cond`) -> диалог `gar_tunel_novice_start` (`gar_rescue_tunnel_novice_find`) -> он сам бежит на базу (vertex 253167; на месте ставит `..._return`) -> диалог `gar_digger_leader_rescue_reward`: 3000 RU, 2x`medkit_army`, `skill_book_shotgun`. Фейл - смерть новичка (`..._fail`).
4. Зависимости: G1-G4; `gar_tunnel_novice` (профиль + `no_sid` (-275.5,0.375,28.4) маркер + логика `move`), диалоги, `target_story_ids = logic@work5, gar_smart_terrain_6_3` (gulag-job формат поддержан и в SRP `CStorylineTask`, при условии что на смарте есть job `logic@work5`: в vanilla `gar_flea_market.ltx` он есть - верифицировано).
5. Сюжет: Story-only по гейту (диалог Напра после GA1). Фейлится на `gar_flea_market_stop_quest_line` (смерть Напра/квестлайн). В Freeplay Напр существует (локация жива, торговые конфиги учитывают Freeplay), но диалог придётся выдавать по-новому.
6. Дефекты: «вернуться с диггером» не принуждается (новичок бежит сам); `no_sid_x/y/z` у НПС = точка спавна (маркер на месте даже после ухода НПС, если создан как `_spot`); nil-краш Freeplay (G2).
7. Вердикт: **ADAPT-M, Freeplay+Story** (независимый квест «спаси новичка»; убрать гейт GA1, добавить собственный диалог у Напра).

---------------------------------------------------------------------------------------------------
## ИТОГОВАЯ ТАБЛИЦА (приоритет для порта)

| Квест | Вердикт | Усилие | Режим | Главные блокеры |
|---|---|---|---|---|
| esc_shilov_find/talk_rukzak | ADAPT | S | оба | storyline->Freeplay (G2), предмет `shilov_rukzak`, `actor_in_stalker` |
| mar_csky_find/kill/reward_baron | ADAPT | M | оба | G1-G3, G2; НПС `mar_csky_patrol`/`mar_renegate_baron`; `treasure_manager` abort |
| esc_take_equipments + esc_capture_army_blockpost | ADAPT | M | оба | `actor_in_stalker`, G2 (1-я), squads, `wpn_autocolt`/`wpn_equipment_svu` |
| gar_rescue/return/reward_tunnel_novice | ADAPT | M | оба | гейт Напра, G2, `move`-логика новичка |
| gar_find/reward_master_outfit | ADAPT | M | оба | giver по гейту сюжета, G2, outfit |
| esc_kill_blockpost_leader/talk | ADAPT | M | оба | штраф -2500, `esc_army_polkovnik`, G2, SVU |
| mar_capture_pumping_station / church | ADAPT | S | Freeplay | `mar_captures_allow` из SGM-правки, `mar_story_empower_csky_done` |
| mar_capture_boat/embankment/north_khutor + last_intensify_reward | ADAPT | M | оба | гейт `mar_story_capture_bandit_base_reward`, bug target_cond, storyline-награда |
| mar_accompany_rescue_* (4) | SKIP (Freeplay) / ADAPT-L (Story) | L | Story | гейт, `move` 5 НПС, vertex-ids |
| mar_entry/meet_csky_force, mar_hold_renagade_base | SKIP / ADAPT-L (Story) | L | Story | сюжет 10_5, hold мёртв |
| gar_wild_napr_* ... propusk, searched_commander_body | SKIP | L | Story | замена ванильного финала Свалки |
| gar_digger_messanger_* | SKIP | M | Story | правка сюжетного НПС |

Общий вывод: прямой port «как есть» невозможен (G1: `abort` на загрузке менеджера задач; G2: краш `add_task` в Freeplay; G3: нет схемы `move`). Минимальный набор для порта лучших квестов: (1) своя выдача вместо `add_task("storyline")` + маркер без `target_profile` (напр. `target_story_ids` у заспавненных НПС/предметов или `level.map_add_object_spot`), (2) переписать НПС-логику на ванильные схемы, (3) заменить skill_book-награды, (4) добавить недостающие `xr_conditions`/`xr_effects` функции в аддон, (5) перевод строк, (6) мёрж `character_desc_*`, `squad_descr.ltx`, `system.ltx`, `task_manager.ltx` в аддоне.


---

# Часть 3

# SGM audit, group 2 (val_, agr_, yan_, mil_) for SRP Freeplay addon

Read-only audit. Everything below was read or grepped in the files unless marked "unverified".
Paths: SGM = /home/claude/kvsuadn-art/sgm/gamedata ; vanilla = /home/claude/kvsuadn-art/csogsm/original ; SRP = /home/claude/srp/gamedata ; addon = /home/claude/srp/addons/freeplay_extras/gamedata.
Task definitions: SGM configs/misc/tasks/sgm_tasks.ltx.
Effort: S = hours, M = 1-2 days, L = several days. "story" = needs the vanilla story line, "Freeplay" = could run in srp_freeplay, "both" = either.

## 0. Shared mechanics and dependencies (apply to every quest below)

### 0.1 How SGM runs quests
- bind_stalker.script (actor_binder:update, ~line 359) calls sgm_loader.sigerous_mod_init() and sgm_callbacks.callback_for_update() on every actor update. These run sgm_world.update_spawn, sgm_info.info_work_init, sgm_tasks.sgm_task_init, sgm_reinforcement, sgm_squads.squads_init and others.
- All quest triggers are per-frame polls guarded by info portions (sgm_tasks.script, sgm_world.script, sgm_squads.script, sgm_info.script). Addon policy says no actor_binder:update; the polls must be rewritten as ogse_signals (with reschedule) or callbacks.
- Quest start functions in sgm_dialogs.script are one-liners: add_task("storyline", id, faction) (add_task is a new function in SGM _g.script).

### 0.2 Core-file edits SGM made (vs vanilla) that these quests rely on
- modules.script: load_scheme for xr_picker, shooter, corpse, theatre, move, gainer, doctor, defender, mob_move, ph_shot, ph_radio.
- xr_logic.script: doctor/gainer schemes, shooter_switch condition.
- xr_motivator.script: calls sgm_modules.profile_update, enemy_found_tips_module, npc_range_module, xr_gainer, xr_picker.
- se_stalker.script: calls sgm_modules.on_death_module.
- _g.script: create(), create_force(), add_task(), add_eliminate_task(), delete_force(), release_force().
- xr_effects.script: agr_chief_commander_tip..tip4, agr_dolg_n_wave1_update, agr_outpost_search_bodyes, yan_tunnel_snorks_w1/w2/w3_update, val_send_guard_commander_message, val_send_comendant_message, respawn_val_guard_leader, respawn_val_7_6_commander, sgm_activate_blackday.
- xr_conditions.script: has_af_sizer, has_af_dummy, has_quest_rpg, has_bus_hostage_pda, has_exo_victim1_pda, has_exo_victim2_pda, agr_pre_wave3_end, actor_is_no_enemy.
- task_objects.script: target_profile and no_sid_x/y/z/lv/gv/shift, hide_smart_name, on_fail, complete_info/reverse_info/fail_info for eliminate_smart; CStorylineTask no longer aborts when there is no target.
- task_manager.script = vanilla except the ini path (misc\tasks\task_manager.ltx).
- SGM moved task ltx into configs/misc/tasks/ and added task_spots.ltx (system.ltx line 23 includes misc\task_spots.ltx).
- SRP task_objects.script is a rewrite: CStorylineTask requires target_story_ids and has no target_profile, no_sid, complete_info or hide_smart_name. SRP does have on_fail and reward parsing, target_smart_name (xr_conditions.script:471), actor_on_level, squad_exist. Porting storyline tasks that target profile-less NPCs means reimplementing SGM task_objects + sgm_modules (profiles_ids registry).
- Profile-less targets: task_spots.ltx defines `<profile>_spot` objects (class O_INVBOX). If the profile id is not in sgm_modules.profiles_ids (a non-saved table filled lazily when an NPC goes online), task_objects creates a new alife `_spot` at the no_sid coordinates on every get_inited_task call (duplicate spawn risk, behavior beyond the code read is unverified).

### 0.3 Custom NPC schemes needed (SGM scripts + modules.script)
- theatre (hostage/killer scenes), corpse (spawns items then kills NPC with hit power 1000), move, shooter, mob_move (per-frame send_to_nearest_accessible_vertex, reads only target_point). Use global sgm_flags timers (theatre_timer etc.) reset by sgm_value_work.

### 0.4 Missing in vanilla, SRP and the freeplay_extras addon (checked with sec.sh)
- Item sections: wpn_rpg7_for_blockpost, af_quest_sizer, device_pda_bus_hostage, device_pda_exo_victim1, device_pda_exo_victim2, mil_quest_wpn_rpg7, valley_propusk (all in SGM sgm_quest_items.ltx), wpn_knife_up, wpn_knife_up2, wpn_ak78, af_night_star_breeding_2, personal_rukzak, bio_bandage, ammo_5.56x45_gd, ammo_5.45x39_hr, skill_book_ak78, skill_book_viper, skill_book_spp200.
- Existing in addon fp_skill_items.ltx: skill_book_pb, sig550, spas12, groza, g36, l85, vintorez, fn2000, val.
- Exist in vanilla: af_dummy_dummy, af_eye, medkit_army, ammo_5.56x45_ap, ammo_7.62x54_7h14, grenade_rgd5, wpn_lr300_up2.
- Info portions: all SGM infos are in configs/gameplay/sgm_portations.xml and absent from vanilla/SRP. Vanilla ones reused: val_deliver_ammo_complete, agr_garbage_end, agr_actor_inside_N, agr_take_reward_complete, mil_hog_death, forester_talked_2 etc.
- Texts: task strings in SGM text files (not re-checked against SRP/CS string tables; whether agr_at_blokpost_name exists in SRP texts is unverified).
- Squads: squad_descr_sgm.ltx (SRP squad_descr.ltx does not #include it): agr_monsters_n_wave1 (7 dog_normal, on_death +agr_defend_dolg_north_h1_end), agr_monsters_n_wave2 (5 snork_normal, h2_end), mil_army_ambush1/2, val_pseudo_giant_6_4.

### 0.5 Files where SRP differs from vanilla (merge, not overwrite, if SGM variants are ported)
val_quests_line.ltx, val_door_komendant.ltx (SRP: srp_freeplay, smart_captured_by_faction val_smart_terrain_7_5, val_find_pda_done), agr_quest_line.ltx (SRP: agr_blokpost_1:csky, no agr_duty_open), yan_quest_line.ltx, mil_quest_line.ltx (heavily rewritten; SRP lacks +mil_stop_invasion_start and mil_5_6_5_ambush), trade_trader_val_freedom.ltx (SRP srp_freeplay rank-based supplies; SGM adds discount on +val_bring_ashot_dummy_discount), squad_descr.ltx.

### 0.6 Rewards
Non-immediate rewards are queued into tm.rewards[faction] by task_objects and paid via the faction rewarder dialog (SRP task_dialogs.script handles paying). immediate_reward = true pays on the spot.

---

## 1. DARK VALLEY (val_)

Common: all are type=storyline; giver is Freedom (faction "freedom") except where noted. Level vertex ids of spawns are unverified; game vertex ids lie inside the Dark Valley range 743-960.

### 1.1 Main-line replacement chain (story-gating)
This chain replaces vanilla val_go_to_trader / val_deliver_ammo in val_quests_line.ltx (SGM version) and is partly a progress gate for the Freedom base.

**val_go_to_outpost** (Dark Valley) - go to the blockpost (task strings in sgm_tasks.ltx ~343-483, Russian text: "Идти на блокпост").
- Giver: val_freedom_comendant (story id 1103) hello dialog (dialogs_darkvalley.xml, phrase 5111 gives val_come_back_comendant_to_revard + val_go_to_outpost_start).
- Steps/reward: walk to outpost (val_space_restrictor_blockpos_2_mapspot, story id 1105); no item reward.
- Deps: val_quests_line.ltx SGM edits, val_space_restrictor_actor_deadblockpost.ltx (val_go_to_outpost_start -> +val_go_to_outpost_distance), dialogs_darkvalley.xml SGM rewrite, sgm_portations infos.
- Story state: needs vanilla Valley story flow; SRP val_quests_line.ltx differs, so a merge is required. Freeplay: not viable as-is (Freeplay already has its own branches in door logic).
- Defects: none verified beyond the dependency on the merged quest line.
- Verdict: SKIP for Freeplay; ADAPT only if the whole Valley story rewrite is wanted. L, story.

**val_talk_to_outpost_leader** - talk to blockpost leader.
- Giver/start: blockpost leader dialog (dialogs 111 gives val_talk_to_outpost_leader_talk + val_speak_about_start).
- Deps: character_desc_darkvalley.xml edits, dialogs_darkvalley.xml. Reward: none.
- Verdict: SKIP (dialog-only step of the replaced story chain). S on its own, but only meaningful with 1.1 as a whole. story.

**val_speak_about** - talk to the second contact (dialog 73 gives val_speak_about_talk + val_talk_to_medic_start).
- Same deps as above. Verdict: SKIP, story.

**val_talk_to_medic** - find the Freedom medic.
- Giver: val_freedom_medic (spawned by sgm_world.update_spawn at (25.256,5.116,27.183) lv190243 gv795 on val_talk_to_medic_allow); dialog val_freedom_medic_start_dialog (sgm_dialogs.xml 4055); logic SGM/darkvalley/val_freedom_medic.ltx (move@doktor, meet, quest_npc=true).
- Deps: move scheme (modules.script + xr_move), doctor scheme.
- Defect: condlist_1 contains `{+gar_talk_to_medic_end}` (leftover Garbage name; harmless because the dialog gives both infos).
- Verdict: SKIP (story chain). M with the chain. story.

**val_deliver_outpost_equipments** - bring equipment from Krechetov to the blockpost.
- Start/reward: val_krechetov_equipments gives 4 medkit_army + 4 ammo_5.56x45_ap + 4 grenade_rgd5 (all existing items).
- Completion: walking into val_space_restrictor_killerblockpost_sound zone, after val_deadblockpost_sos a 30 s timer gives +val_deliver_ammo_complete. Items from Krechetov are never checked (verified in logic files).
- Verdict: SKIP; the task completes without delivering anything, so the step is cosmetic. story.

### 1.2 Base-door gating (soft-lock risk)

**val_talk_to_chief_guard**, **val_7_6_deliver_weapons**, **val_reward_chief_guard**
- Givers: val_freedom_guard_leader (spawn (-44.385,9.191,-25.075) lv121064 gv794, on val_talk_to_guard_leader_allow, dialog 4104) and val_freedom_7_6_commander (spawn (1.364,0.046,-164.671) lv167432 gv801, on val_7_6_deliver_weapon_allow, dialog 4207). tm_darkvalley.ltx val_come_to_freedom_base on_complete gives +val_talk_to_guard_leader_allow.
- Steps: talk to guard leader; take 2 wpn_rpg7_for_blockpost (missing section, 0.4) to the 7_6 commander (val_7_6_deliver_unpack removes them); return for val_reward_chief_guard = skill_book_pb (exists in addon).
- Deps: xr_effects respawn_val_guard_leader / respawn_val_7_6_commander (on_death respawns), SGM val_door_komendant.ltx.
- Defect: SGM val_door_komendant.ltx requires +val_reward_chief_guard_complete to open the base. If the 7_6 commander is killed or fails to spawn, the base door stays locked (respawn effects mitigate; behavior unverified in play).
- Freeplay: SRP version of val_door_komendant uses srp_freeplay; SGM version would overwrite it. 
- Verdict: SKIP (changes a core gate, conflicts with SRP Freeplay door logic). story.

### 1.3 Standalone side quests

**val_return_propusk** - return the pass ("Вернуть пропуск").
- Start: dialog 31111 gives val_return_propusk_start; val_quests_line.ltx gives it via `=give_inited_task(val_return_propusk)` after val_deliver_pda_done. valley_propusk item (missing section) is relocated "in" by val_return_propusk dialog function.
- Reward: skill_book_sig550 (in addon).
- Deps: val_allies_logic_north/south.ltx (walker@propusk_wait added, meet = no_meet removed), val_return_propusk_dialog on two blockpost leaders (character_desc_darkvalley.xml).
- Defect/behavior: sgm_tasks.script fails it (val_return_propusk_fail) if val_return_propusk_start without val_return_propusk_talk and actor goes to garbage/escape.
- Verdict: SKIP; tied to the SGM-invented item and checkpoint edits. story. M.

**val_searched_impounded** - search impounded goods ("Найти конфискат"), **val_reward_impounded** - report to the breeder.
- Giver: val_freedom_breeder (spawned unconditionally at (-20.942,0.090,-2.966) lv146468 gv855), scripted dialog val_breeder_dialog in sgm_phrases.script (~1450-1500); start function val_searched_impounded/freedom.
- Target: val_impounded_corpse (spawn (-6.543,7.011,-158.918) lv178873 gv849 on val_searched_impounded_allow), logic val_impounded_corpse.ltx: corpse@impounded with corpse_items = af_quest_sizer (missing section).
- Reward: val_reward_impounded task gives skill_book_viper (missing section); dialog reward type1 = discount only, type2 = 3000 + af_night_star_breeding_2 (missing).
- Deps: corpse scheme, trade_breeder.ltx, has_af_sizer condition, sgm_phrases.script.
- Freeplay: standalone, no story state dependency found. Viable.
- Verdict: ADAPT (replace missing items with existing artifacts/skill_book, reimplement corpse spawn via simple object spawn, rewrite start via addon dialog). M, both.

**val_find_ashot_dummy**, **val_bring_ashot_dummy** - find an artifact for the trader Ashot.
- Giver: Freedom trader (dialogs val_ashot_find_dummy_give/what, sgm_dialogs.xml 4290-4420, added to the trader in character_desc_darkvalley.xml). Start: val_find_ashot_dummy/freedom.
- Reward: val_af_dummy_reward 6000 money, val_bring_ashot_dummy gives skill_book_g36 (in addon) and sets +val_bring_ashot_dummy_discount (trader discount, needs trade_trader_val_freedom.ltx merge with SRP's srp_freeplay supplies).
- Item: af_dummy_dummy exists in vanilla and SRP trade files. It spawns only on military/red_forest/yantar per spawn (verified), so it is far from Dark Valley.
- Defect: val_find_ashot_dummy has no target_story_ids and no target_profile, so target = nil. CStorylineTask:save does package:w_u32(self.target) (task_objects.script ~1408), likely a save error with nil (engine behavior unverified). SRP CStorylineTask requires target_story_ids, so it would reject it.
- Verdict: ADAPT (task without target/marker, trader merge). S-M, both.

**val_sos_check_bus**, **val_sos_rescue_bus**, **val_sos_searched_bus**, **val_sos_reward_bus** - SOS from a bus (hostages).
- Giver: val_freedom_squads_commander (spawned at (19.066,0.133,-2.351) lv184135 gv811, only after val_pursuit_comendant_complete; dialog 3883).
- Targets: val_bus_hostage and val_bus_killer at (59.798,0.201,-187.310) lv222893 gv959 (on val_check_bus_allow); theatre scenes val_bus_hostage.ltx/val_bus_killer.ltx; hostage_reward 500. val_bus_ambush_danger kills the hostage via =kill_npc if the actor gets within 10 m (or sees the killer within 25 m) before the killer dies.
- Items: device_pda_bus_hostage (missing), has_bus_hostage_pda condition; rewards val_check_bus_reward1 1000 (PDA), reward2 5000 + wpn_ak78 (missing); val_sos_reward_bus gives skill_book_l85 (in addon).
- Defect: xr_theatre.script get_target references an undefined variable `st` (~line 59), a crash risk (not run, unverified in game).
- Verdict: ADAPT (the most self-contained side story, but requires theatre scheme, spawn of 2 NPCs, new items). L, both (the pursuit_comendant gate is a story state; replace it with a Freeplay trigger).

---

## 2. AGROPROM (agr_)

Common: spawns are coded in sgm_world.script / sgm_tasks.script with hardcoded coordinates. Game vertex ids are inside the Agroprom range 1057-1211; level vertex ids unverified. Story id 1001 = Duty commander agr_duty_base_commander.

### 2.1 Defend-Dolg chain (story rewrite, gates the Duty base door)

**agr_talk_to_stalker_leader**, **agr_fake_talk_to_leader**, **agr_occupy_north_position**, **agr_hold_north_position**, **agr_destroy_snork_hole**, **agr_occupy_east_position**, **agr_hold_east_position**
- Giver/start: agr_quest_line.ltx (SGM): agr_actor_inside_3 gives task agr_talk_to_stalker_leader:stalker; agr_stalker_leader_talk_end gives agr_fake_talk_to_leader:dolg + agr_duty_open. Dialog agr_stalker_base_leader_start (sgm_dialogs.xml 6206), character_desc_agroprom.xml.
- Steps: duty base entry zone (-139.221,-0.202,-188.336) gives agr_defend_dolg_tip; north position (-191.140,-0.101,-125.825) gives agr_defend_dolg_north; wave1 dogs, wave2 snorks (create_force into agr_smart_terrain_1_3), wave2 giant at (-178.278,-0.074,-35.885) lv28878 gv1135; then east position (-99.459,0.010,-182.903) with 3 giant_hunters with RPG shooters at (-106.9,7.3,-204.3), (-104.3,4.4,-154.1), (-68.9,7.3,-139.1) and E-waves 0-3 (dogs, pseudodogs, boars, flesh, giants).
- Rewards: agr_destroy_snork_hole skill_book_spas12 (in addon); agr_hold_east_position 8000 money + skill_book_groza:skill_book_ak78 (ak78 missing).
- Deps: sgm_tasks.script polling, squads, mob_move scheme on all wave NPCs (agr_n_wave*_*.ltx), shooter scheme, xr_effects agr_chief_commander_tip..4, agr_dolg_n_wave1_update, agr_pre_wave3_end, agr_duty_base_door.ltx (opens only on agr_defend_dolg_open_door, vanilla used agr_actor_inside_3), agr_bloodsucker_attack_duty disabled, agr_bandits_attack(_2) delayed, agr_7_4_commander.ltx, sgm_squads replacing Duty squads at road post 7_4 with stalker squads.
- Defects: agr_hold_east_position copy-pastes name/text from agr_hold_north_position. create_force silently returns if the smart owner is another faction; the hole_init branch then auto-gives h1_end/h2_end (the hole step is skipped). agr_n_wave2_giant.ltx has stray `target_smart = val_smart_terrain_6_4` (ignored by mob_move).
- Story state: relies on vanilla agr_actor_inside_N; SRP agr_quest_line differs (agr_blokpost_1:csky, no agr_duty_open). Conflicts with SRP flow; Duty base closed until the defense ends.
- Verdict: ADAPT as a standalone Freeplay "defend position" event (reuse wave spawn lists, drop door gating); SKIP as a story rewrite. L, Freeplay (event) / story (as is).

### 2.2 Outpost side chain

**agr_go_to_outpost**, **agr_eliminate_outpost**, **agr_search_lieutenant_body**, **agr_search_ordinary_body**, **agr_return_outpost_pda**
- Giver: agr_dolg_agent (spawn (-146.599,4.999,-201.909) lv45827 gv1168), dialog agr_dolg_agent_start (6244); start agr_go_to_outpost/dolg.
- Steps: go to south outpost, kill exo bandits agr_exo_bandit1/2 ((-37.787,-4.133,-290.333), (-35.325,-4.390,-299.174), gv1058; bandit1 gives +agr_find_squad_distance at <= 45 m), search bodies agr_bandit_victim1/2 ((-36.312,-4.307,-291.163), (-37.609,-4.385,-301.328)) via corpse scheme holding device_pda_exo_victim1/2 (missing), return PDAs (agr_outpost_pda_unpack removes them).
- Reward: agr_return_outpost_pda: 6000 money, community_relation_delta_complete = +200, items personal_rukzak, 2x bio_bandage, wpn_lr300_up2, 2x ammo_5.56x45_gd, skill_book_spp200 (rukzak, bandage, gd ammo, spp200 missing).
- Deps: corpse scheme, has_exo_victim1/2_pda conditions, agr_outpost_search_bodyes, task_spots, no_sid targets.
- Freeplay: no story state needed beyond the dolg agent spawn. Viable.
- Verdict: ADAPT (replace missing items; reimplement targets). M, both.

### 2.3 Wild giant

**agr_kill_wild_giant**
- Giver: Duty leader via dialog agr_dolg_leader_extra_job (6421, requires agr_take_reward_complete). Start agr_kill_wild_giant/dolg.
- Target: agr_wild_giant (spawn (-41.336,7.072,-93.258) lv118246 gv1159); target uses task_spots no_sid.
- Reward: 1000 money + af_eye (exists) + skill_book_vintorez (in addon).
- Verdict: ADAPT (S-M): give via Freeplay trigger instead of agr_take_reward_complete; all rewards available. both.

---

## 3. YANTAR (yan_)

Spawns inside Yantar gv range 1212-1312. Story id 808 is a space_restrictor (yan_otnesti_doc_saharavy), not an NPC.

**yan_kill_tunnel_snorks**, **yan_reward_tunnel_snorks**
- Giver: Sakharov hello dialog phrase 99 (dialogs_yantar.xml) starts the task, gives yan_questions_scientists (hides the vanilla zombie dialog); start yan_kill_tunnel_snorks/stalker.
- Steps: sgm_tasks.script creates yan_tunnel_rpg (RPG shooter) at (106.527,-8.865,-212.760) lv110614 gv1231 and 3 waves of 5 snorks at (127.993,-8.778,-165.259) lv124057 gv1266 (xr_effects yan_tunnel_snorks_w1/w2/w3_update); yan_tunnel_rpg.ltx uses shooter scheme with yan_kill_tunnel_snorks_fire.
- Reward: yan_reward_tunnel_snorks immediate 2000 money.
- Deps: yan_quest_line.ltx SGM: after yan_ready_actor_cut2 waits sgm_line_0 (needs yan_kill_tunnel_snorks_start) -> sgm_line_1 (waits yan_kill_tunnel_snorks_fire or 70000 ms timer) -> yan_quest_doc. The Yantar story is gated on this quest being started. dialog yan_scientist_about_strelok now requires yan_kill_tunnel_snorks_complete.
- Verdict: ADAPT as a Freeplay combat quest (S-M if shooter scheme dropped; M with it); SKIP the story gating changes. both.

**yan_bring_sample_dnk**, **yan_take_sample_dnk**, **yan_reward_sample_dnk**
- Giver: Sakharov, dialogs yan_sample_dnk_task_start/choose (sgm_dialogs.xml 7066, gated by has_info yan_proriv_k_ystanovke; added in character_desc_yantar.xml). Start yan_bring_sample_dnk/stalker.
- Steps: sgm_tasks.script creates yan_zombie_bloodsucker at (62.813,0.604,40.940) lv90537 gv1272 on yan_bring_sample_dnk_start; yan_zombie_bloodsucker.ltx has `[known_info] yan_bring_sample_dnk_has_dnk` (the known_info mechanism via xr_info.loadInfo not verified); take sample, bring back.
- Reward: yan_reward_sample_dnk immediate 4000 + skill_book_fn2000 (in addon).
- Verdict: ADAPT (needs a Freeplay replacement for the yan_proriv_k_ystanovke gate). M, both.

---

## 4. MILITARY (mil_)

Game vertex ids in the Military range 1313-1510. Story id 1207 = restrictor mil_hires_task (fixed marker at (-324.4,-22.3,213.2)), not the hog NPC.

**mil_hog_find_item**, **mil_hog_reward_item**
- Giver: Military "hog" NPC, dialogs mil_hog_find_item_start/complete (sgm_dialogs.xml 8009-8050; added as actor_dialogs in character_desc_military.xml). Start mil_hog_find_item/killer.
- Target: mil_quest_wpn_rpg7 (missing section) spawned by mil_quest_rpg_spawn via create("mil_quest_wpn_rpg7",3.503,5.977,-61.462,292865,1449); target spot via task_spots.
- Reward: mil_hog_reward_item immediate 4500 + ammo_7.62x54_7h14 (exists).
- Deps: has_quest_rpg condition, mil_hog_death vanilla info.
- Defect: the reward-target restrictor 1207 is a static map marker, not the NPC (task marker points to the fixed position).
- Verdict: ADAPT (S-M): new item section needed (copy of an RPG-7 or any loot item). both.

**mil_stop_invasion_5_5**, **mil_stop_invasion_5_6** (type = eliminate_smart)
- Start: sgm_tasks.script: `mil_stop_invasion_start` + is_smart_captured2(5_6 / 5_5, "army") calls add_eliminate_task("eliminate_smart","mil_stop_invasion_5_x","csky",smart) once. sgm_squads.script: after mil_actor_go_to_limansk and no mil_5_6_5_ambush, create_force(mil_army_ambush1 -> mil_smart_terrain_5_6, mil_army_ambush2 -> mil_smart_terrain_5_5), gives mil_5_6_5_ambush. mil_quest_line.ltx SGM final section adds +mil_stop_invasion_start; SRP lacks it.
- Squads: mil_army_ambush1/2 (5x sim_default_military_3/4, on_death mil_stop_invasion_5_6/5_5_complete) in squad_descr_sgm.ltx.
- Uses complete_info / hide_smart_name / on_fail (SGM task_objects only; absent in SRP). Task fails when the actor leaves to red_forest/garbage (sgm_info.script gives *_complete infos on red_forest with mil_5_6_5_ambush, so leaving also completes it, a defect).
- Verdict: SKIP as story (end-of-story clean-up, needs mil_actor_go_to_limansk). ADAPT possible as a Freeplay "retake base" event; needs the SGM eliminate_smart extensions in SRP task_objects. M-L, story / Freeplay.

---

## 5. Verdict table

| Quest | Verdict | Effort | Scope |
|---|---|---|---|
| val_go_to_outpost, val_talk_to_outpost_leader, val_speak_about, val_talk_to_medic, val_deliver_outpost_equipments | SKIP | L as a set | story |
| val_talk_to_chief_guard, val_7_6_deliver_weapons, val_reward_chief_guard | SKIP (door gate, soft-lock) | M | story |
| val_return_propusk | SKIP | M | story |
| val_searched_impounded, val_reward_impounded | ADAPT | M | both |
| val_find_ashot_dummy, val_bring_ashot_dummy | ADAPT | S-M | both |
| val_sos_check/rescue/searched/reward_bus | ADAPT | L | both |
| agr_talk_to_stalker_leader, agr_fake_talk_to_leader, agr_occupy/hold north/east, agr_destroy_snork_hole | SKIP as story; ADAPT as Freeplay event | L | story / Freeplay |
| agr_go_to_outpost .. agr_return_outpost_pda | ADAPT | M | both |
| agr_kill_wild_giant | ADAPT | S-M | both |
| yan_kill_tunnel_snorks, yan_reward_tunnel_snorks | ADAPT | M | both |
| yan_bring/take/reward_sample_dnk | ADAPT | M | both |
| mil_hog_find_item, mil_hog_reward_item | ADAPT | S-M | both |
| mil_stop_invasion_5_5, 5_6 | SKIP (or ADAPT as event) | M-L | story |

## 6. Defects list
1. agr_hold_east_position copy-pastes name/text of agr_hold_north_position.
2. val_find_ashot_dummy has nil target (CStorylineTask:save w_u32(nil); likely save error, unverified in engine).
3. val_deliver_outpost_equipments completes by zone/timer; delivered items never checked.
4. val_talk_to_medic condlist references +gar_talk_to_medic_end (harmless leftover).
5. xr_theatre.script get_target uses undefined `st` (~line 59).
6. agr_n_wave2_giant.ltx stray target_smart = val_smart_terrain_6_4.
7. create_force silently skips when the smart is owned by another faction, so the snork-hole step is auto-completed.
8. mil_stop_invasion tasks complete as soon as the actor leaves to red_forest with mil_5_6_5_ambush.
9. Base door lock via +val_reward_chief_guard_complete (soft-lock risk if the 7_6 commander dies/does not spawn).
10. Every trigger is a per-frame poll; Freeplay addon policy forbids actor_binder:update.
11. Profile-less targets may spawn duplicate `_spot` objects (profiles_ids not saved).

## 7. Unverified
- Level vertex ids of all create() spawns; engine behavior with nil target in save; SRP string-table coverage for the task texts (e.g. agr_at_blokpost_name); xr_info.loadInfo known_info mechanism; real in-game behavior of any quest (nothing was run).
