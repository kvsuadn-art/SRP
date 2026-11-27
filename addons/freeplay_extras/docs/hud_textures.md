# HUD в SGM и OGSM: что прописано и на какие текстуры ссылается

Статики HUD задаются в `configs/ui/ui_custom_msgs.xml` (в SRP этого файла нет, он берётся из базовой игры; копия оригинала лежит в `csogsm/original/configs/ui/`). Текст на них пишут скрипты через `SetTextST`.

## SGM (Sigerous Mod 3.10)
Все элементы SGM берут спрайты из **одного атласа `ui\ui_hud.dds`**. У SGM он 2048x2048 (DXT5), у SRP 1024x1024 (32 бит), поэтому координаты SGM (x до 1700, y до 1290) в атласе SRP попадают в пустоту: напрямую взять нельзя, спрайты нужно вырезать.

| Статик | Что показывает | Область в `ui_hud.dds` SGM (x, y, w, h) | Берём |
|---|---|---|---|
| `hud_wpn_params_1/2/3` + `_1_1/_2_2/_3_3` | панель параметров оружия (урон, дальность; у гранаты радиус взрыва и разлёт осколков) | 1542, 941, 152x134 | ДА (`fp_hud_wpn`) |
| `hud_sleep_zone` | значок спального мешка в месте для сна | 1592, 1230, 68x60 | ДА (`fp_hud_sleep`) |
| `hud_wpn_dont`, `hud_icon_wpn_p/r`, `hud_wpn_conduction_1/2`, `hud_wpn_capt_1/2` | вспомогательные значки оружия SGM (запрет, тип, проводимость) | 1542,941,165x134; 1475,981,28x16; 1473,1027,45x20; 1610,1038,94x39 | нет |
| `hud_global_time` | часы (текст на фоне) | 1037, 0, 110x50 | нет |
| `hud_last_bg` + `hud_last_event` | «последнее событие» (радио-событие, кто погиб) | 1315, 629, 340x36 | нет |
| `hud_hunger1/2/3` | значок голода | 1304, 1103, 52x39 | нет |
| `hud_actor_rank_icon` + `_text` | счётчик ранга | 1432, 1091, 133x35 | нет |
| `hud_immortal_static` | значок бессмертия (отладка) | 1612, 1123, 68x74 | нет |
| `hud_hero_rank` | полоса «здоровье» (`ui_sega_healph`) | другой файл, в SGM его нет | нет |
| `hud_timer`, `crow_timer`, `shooting_timer` | таймеры мини-игр (`ui_hud_timer_games`) | файла нет ни в SGM, ни в OGSM, ни в SRP | нет |
| `sleep_001`, `controller_fx`, `monster_claws` | эффекты сна и контролёра (`car\trabantnoise`, `act\act_controller_hit*`, `controller\controller_blood_01`) | отдельные текстуры оригинала | нет |

## OGSM Extended 2.0
| Статик | Что показывает | Текстура | Где она |
|---|---|---|---|
| `indik2_rad`, `indik2_psy`, `indik2_wpn`, `indik2_slp`, `indik2_hun` | значки состояния: радиация, пси, износ оружия, сон, голод | `ui_hud_icon_radiation`, `_psycho`, `_weapon`, `_sleep`, `_eat` (по 64x64) | **уже в SRP**: `ui_hud.xml` SRP описывает их в `ui_hud.dds` SRP, свои текстуры не нужны |
| `hud_time_tex` + `hud_timer_text2` | электронные часы | `ui_watch_back` | **уже в SRP** (`ui_ingame2_common`) |
| `hud_psy_back`, `hud_psy_level` | шкала пси-здоровья | `ui\ui_hud_psy_back.dds`, `ui\ui_hud_psy_progress.dds` | только в OGSM; шкала завязана на пси-механику OGSM |
| `hudFreezeLow/Average/High` | экранные эффекты холода | `hud\freezeLow`, `freezeAverage`, `freezeHigh` | файлов нет даже в OGSM (мёртвый код) |
| `cs_debug` | отладочный текст | без текстуры | — |
| таймеры мини-игр, `cs_heli_health`, `cs_strelok_health` | как в SGM | `ui_hud_timer_games`, `ui_sega_healph`, `ui_hud_points_count` | файлов нет ни в одном моде |

Вывод по OGSM: все значки состояния и часы уже существуют в SRP, поэтому если они понадобятся, переносить нужно только статики и скрипты, без текстур. Шкала пси и холод не берутся.

## Решение владельца и что сделано
Берём из SGM только индикатор параметров оружия и значок спального мешка. Реализация: модуль `fp_hud`, текстура `ui\fp_hud.dds` (256x256, два спрайта, вырезаны из атласа SGM), статики `fp_hud_wpn`, `fp_hud_wpn2`, `fp_hud_sleep` в копии `ui_custom_msgs.xml` аддона (оригинал + три статика).
