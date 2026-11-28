# Иконки предметов Freeplay Extras: где править

Таблица и карта ниже сгенерированы скриптом `tools/icon_audit.py` по атласу аддона (`python3 tools/icon_audit.py --atlas gamedata/textures/ui/ui_icon_equipment.dds --out docs/icons.md --preview docs/icons_preview.png`; нужен Pillow). После правки иконок или координат запустите его заново. Картинка `docs/icons_preview.png` показывает, что сейчас нарисовано в каждой назначенной клетке.

## Где что лежит

| что править | файл | что искать |
|---|---|---|
| какая клетка атласа у предмета | `gamedata/configs/misc/*.ltx` аддона (имя файла в таблице ниже) | секция предмета: `inv_grid_x`, `inv_grid_y` (клетка), `inv_grid_width`, `inv_grid_height` (размер в клетках) |
| сами картинки | `gamedata/textures/ui/ui_icon_equipment.dds` аддона (1024x2048, DXT3, клетка 50x50 px, x вправо, y вниз) | это копия атласа ядра SRP с добавленными иконками; рисовать можно прямо в нём, в свободных клетках (карта ниже) |
| документы (doc_1 ... doc_15) | `quest_items.ltx`, секция `[document]` (родитель) и `[doc_N]:document` | у всех 15 документов одна клетка родителя; своя клетка у документа = добавить `inv_grid_x/y` в его секцию |
| книги навыков | `fp_skill_items.ltx`, секция `[skill_book]` и `[skill_book_<оружие>]` | то же правило: клетка родителя общая |
| артефакты OGSM | `fp_artefacts.ltx` | `af_mica`, `af_slug`, `af_ball`, `af_thorn` |
| части мутантов | `fp_monster_items.ltx` | `mutant_*` |
| костюмы | `fp_outfit.ltx` | `*_outfit` |
| названия, тексты | `configs/text/<язык>/fp_extras.xml` | `<string id="doc_15">` и т.п. |
| откуда брать готовые рисунки | `gamedata/new_items_icons.txt` | клетки в атласах OGSM и SGM для каждой секции |

Новый документ: скопируйте секцию `[doc_15]:document` в `quest_items.ltx` как `[doc_16]:document`, поправьте `inv_name`, `description` (и свою клетку), добавьте строки в `fp_extras.xml` всех языков, имя в `doc_list` и цену в `doc_price` в `ogsm_bring_items.script`.

## Что сделано (b28)

Иконки перенесены из атласа OGSM в копию атласа SRP (`gamedata/textures/ui/ui_icon_equipment.dds` аддона), а координаты секций исправлены под новые клетки. Это делает `tools/icon_port.py` по списку `tools/icon_port.json` (откуда клетка, куда, какие секции):

- 4 артефакта OGSM (`af_mica`, `af_slug`, `af_ball`, `af_thorn`) и 7 частей мутантов теперь в ряду y=38 и в (3,37), (4,37), а не поверх обрезков оружия;
- 14 костюмов OGSM имеют свои иконки в области x от 9 до 17, y от 30 до 38, размер 2x3 (у `bandit_heavy_outfit` был 2x2, стал 2x3, как в OGSM);
- документы, книги навыков и dev-предметы получили иконку документа OGSM, клетка (5,37) 2x1.

Как повторить или добавить иконку: допишите запись в `tools/icon_port.json` (`src`: `ogsm` или `sgm`, `from`: x,y,w,h клетки-источника, `to`: свободная клетка, `sections`: секции) и запустите

    python3 tools/icon_port.py --base <ядро SRP>/gamedata/textures/ui/ui_icon_equipment.dds --ogsm <csogsm>/gamedata/textures/ui/ui_icon_equipment.dds --sgm <sgm>/gamedata/textures/ui/ui_icon_equipment.dds --apply

Скрипт останавливается, если источник пуст, целевая клетка занята или иконки пересекаются. Без `--apply` он только перерисовывает атлас.

Важно: атлас аддона перекрывает атлас ядра. Если ядро SRP поменяет свой атлас, надо запустить скрипт заново на новом файле ядра (иначе новые иконки ядра не появятся).

Что осталось заглушкой: книги навыков (одна иконка документа на все 34, в SGM у книг свои, клетки искать в атласе SGM), медали, спальник и квестовые предметы (общий ящик в (10,25)), флешки лидеров, `device_flare` (клетка 12,7 пуста в атласе ядра, не наша).

Atlas: 1024x2048 px, cell 50 px. Sections with their own cell: {'EMPTY': 1, 'OK': 32, 'SHARED': 16}

| file | section | cell x,y | size | drawn | status | inv_name |
|---|---|---|---|---|---|---|
| devices.ltx | device_flare | 12,7 | 2x1 | 0% | EMPTY | device_flare |
| devices.ltx | detector_simple | 9,14 | 1x1 | 46% | OK | st_detector1 |
| devices.ltx | detector_advanced | 15,7 | 1x1 | 53% | OK | st_detector2 |
| devices.ltx | detector_elite | 5,14 | 1x1 | 50% | OK | st_detector3 |
| fp_artefacts.ltx | af_mica | 0,38 | 1x1 | 65% | OK | st_af_mica_name |
| fp_artefacts.ltx | af_slug | 1,38 | 1x1 | 64% | OK | st_af_slug_name |
| fp_artefacts.ltx | af_ball | 2,38 | 1x1 | 57% | OK | st_af_ball_name |
| fp_artefacts.ltx | af_thorn | 3,38 | 1x1 | 26% | OK | st_af_thorn_name |
| fp_deserves.ltx | fp_deserve_case | 11,23 | 1x1 | 38% | OK |  |
| fp_deserves.ltx | dv_dolg_holeman_case | - | - | - | INHERITS fp_deserve_case | dolg_holeman_case_title |
| fp_deserves.ltx | dv_freedom_boss_case | - | - | - | INHERITS fp_deserve_case | freedom_boss_case_title |
| fp_deserves.ltx | dv_army_driver_case | - | - | - | INHERITS fp_deserve_case | army_driver_case_title |
| fp_deserves.ltx | dv_stalker_messenger_case | - | - | - | INHERITS fp_deserve_case | stalker_messenger_case_title |
| fp_deserves.ltx | dv_bandit_boss_case | - | - | - | INHERITS fp_deserve_case | bandit_boss_case_title |
| fp_deserves.ltx | dv_stalker_avoska_case | - | - | - | INHERITS fp_deserve_case | stalker_avoska_case_title |
| fp_deserves.ltx | dv_stalker_wild_napr_case | - | - | - | INHERITS fp_deserve_case | stalker_wild_napr_case_title |
| fp_deserves.ltx | dv_renegade_baron_case | - | - | - | INHERITS fp_deserve_case | renegade_baron_case_title |
| fp_deserves.ltx | dv_army_sviridov_case | - | - | - | INHERITS fp_deserve_case | army_sviridov_case_title |
| fp_dev.ltx | fp_dev_console | 5,37 | 2x1 | 49% | SHARED(4) | st_fp_dev_console_name |
| fp_dev.ltx | fp_dev_tools | 5,37 | 2x1 | 49% | SHARED(4) | st_fp_dev_tools_name |
| fp_medals_items.ltx | medal_sect | 10,25 | 2x2 | 50% | SHARED(10) |  |
| fp_medals_items.ltx | medal_rank_100 | - | - | - | INHERITS medal_sect | st_medal_100_title |
| fp_medals_items.ltx | medal_rank_200 | - | - | - | INHERITS medal_sect | st_medal_200_title |
| fp_medals_items.ltx | medal_rank_400 | - | - | - | INHERITS medal_sect | st_medal_400_title |
| fp_medals_items.ltx | medal_rank_600 | - | - | - | INHERITS medal_sect | st_medal_600_title |
| fp_medals_items.ltx | medal_rank_800 | - | - | - | INHERITS medal_sect | st_medal_800_title |
| fp_medals_items.ltx | medal_rank_1000 | - | - | - | INHERITS medal_sect | st_medal_1000_title |
| fp_medals_items.ltx | medal_rank_1100 | - | - | - | INHERITS medal_sect | st_medal_1100_title |
| fp_medals_items.ltx | medal_rank_1200 | - | - | - | INHERITS medal_sect | st_medal_1200_title |
| fp_monster_items.ltx | mutant_tushkano_head | 4,38 | 1x1 | 50% | OK | mutant_tushkano_head |
| fp_monster_items.ltx | mutant_izlom_hand | 5,38 | 1x1 | 48% | OK | mutant_izlom_hand |
| fp_monster_items.ltx | mutant_cat_tail | 6,38 | 1x1 | 45% | OK | mutant_cat_tail |
| fp_monster_items.ltx | mutant_poltergeist_hand | 7,38 | 1x1 | 60% | OK | mutant_poltergeist_hand |
| fp_monster_items.ltx | mutant_chimera_nail | 8,38 | 1x1 | 43% | OK | mutant_chimera_nail |
| fp_monster_items.ltx | mutant_controller_hand | 3,37 | 1x1 | 48% | OK | mutant_controller_hand |
| fp_monster_items.ltx | mutant_pseudogigant_nail | 4,37 | 1x1 | 59% | OK | mutant_pseudogigant_nail |
| fp_outfit.ltx | killer_outfit | 9,30 | 2x3 | 66% | OK | killer_outfit_name |
| fp_outfit.ltx | monolith_scientific_outfit | 11,30 | 2x3 | 65% | OK | monolit_scientific_outfit_name |
| fp_outfit.ltx | red_ecolog_outfit | 13,30 | 2x3 | 64% | OK | red_ecolog_outfit_name |
| fp_outfit.ltx | green_ecolog_outfit | 15,30 | 2x3 | 64% | OK | green_ecolog_outfit_name |
| fp_outfit.ltx | cs_standart_outfit | 17,30 | 2x3 | 66% | OK | csky_standart_outfit_name |
| fp_outfit.ltx | bandit_heavy_outfit | 9,33 | 2x3 | 66% | OK | bandit_heavy_outfit_name |
| fp_outfit.ltx | dolg_scientific_outfit | 11,33 | 2x3 | 65% | OK | dolg_scientific_outfit_name |
| fp_outfit.ltx | dolg_heavy_extra_outfit | 13,33 | 2x3 | 60% | OK | dolg_skat_light_outfit_name |
| fp_outfit.ltx | dolg_exo_outfit | 15,33 | 2x3 | 50% | OK | dolg_black_exoskeleton_name |
| fp_outfit.ltx | svoboda_light2_outfit | 17,33 | 2x3 | 68% | OK | svoboda_light2_outfit_name |
| fp_outfit.ltx | svoboda_scientific_outfit | 9,36 | 2x3 | 65% | OK | svoboda_scientific_outfit_name |
| fp_outfit.ltx | soldier_outfit_grey | 11,36 | 2x3 | 51% | OK | outfit_soldier_name |
| fp_outfit.ltx | soldier_outfit_brown | 13,36 | 2x3 | 63% | OK | outfit2_soldier_name |
| fp_outfit.ltx | military_extra_outfit | 15,36 | 2x3 | 59% | OK | military_skat_name |
| fp_skill_items.ltx | skill_book | 5,37 | 2x1 | 49% | SHARED(4) |  |
| fp_skill_items.ltx | skill_book_ak74 | - | - | - | INHERITS skill_book | st_skill_book_ak74_title |
| fp_skill_items.ltx | skill_book_ak74u | - | - | - | INHERITS skill_book | st_skill_book_ak74u_title |
| fp_skill_items.ltx | skill_book_pkm | - | - | - | INHERITS skill_book | st_skill_book_pkm_title |
| fp_skill_items.ltx | skill_book_abakan | - | - | - | INHERITS skill_book | st_skill_book_abakan_title |
| fp_skill_items.ltx | skill_book_beretta | - | - | - | INHERITS skill_book | st_skill_book_beretta_title |
| fp_skill_items.ltx | skill_book_bm16 | - | - | - | INHERITS skill_book | st_skill_book_bm16_title |
| fp_skill_items.ltx | skill_book_colt1911 | - | - | - | INHERITS skill_book | st_skill_book_colt1911_title |
| fp_skill_items.ltx | skill_book_desert_eagle | - | - | - | INHERITS skill_book | st_skill_book_desert_eagle_title |
| fp_skill_items.ltx | skill_book_fn2000 | - | - | - | INHERITS skill_book | st_skill_book_fn2000_title |
| fp_skill_items.ltx | skill_book_fort | - | - | - | INHERITS skill_book | st_skill_book_fort_title |
| fp_skill_items.ltx | skill_book_g36 | - | - | - | INHERITS skill_book | st_skill_book_g36_title |
| fp_skill_items.ltx | skill_book_gauss | - | - | - | INHERITS skill_book | st_skill_book_gauss_title |
| fp_skill_items.ltx | skill_book_groza | - | - | - | INHERITS skill_book | st_skill_book_groza_title |
| fp_skill_items.ltx | skill_book_hpsa | - | - | - | INHERITS skill_book | st_skill_book_hpsa_title |
| fp_skill_items.ltx | skill_book_l85 | - | - | - | INHERITS skill_book | st_skill_book_l85_title |
| fp_skill_items.ltx | skill_book_lr300 | - | - | - | INHERITS skill_book | st_skill_book_lr300_title |
| fp_skill_items.ltx | skill_book_mp5 | - | - | - | INHERITS skill_book | st_skill_book_mp5_title |
| fp_skill_items.ltx | skill_book_pb | - | - | - | INHERITS skill_book | st_skill_book_pb_title |
| fp_skill_items.ltx | skill_book_pm | - | - | - | INHERITS skill_book | st_skill_book_pm_title |
| fp_skill_items.ltx | skill_book_rg-6 | - | - | - | INHERITS skill_book | st_skill_book_rg-6_title |
| fp_skill_items.ltx | skill_book_rpg7 | - | - | - | INHERITS skill_book | st_skill_book_rpg7_title |
| fp_skill_items.ltx | skill_book_sig220 | - | - | - | INHERITS skill_book | st_skill_book_sig220_title |
| fp_skill_items.ltx | skill_book_sig550 | - | - | - | INHERITS skill_book | st_skill_book_sig550_title |
| fp_skill_items.ltx | skill_book_spas12 | - | - | - | INHERITS skill_book | st_skill_book_spas12_title |
| fp_skill_items.ltx | skill_book_svd | - | - | - | INHERITS skill_book | st_skill_book_svd_title |
| fp_skill_items.ltx | skill_book_svu | - | - | - | INHERITS skill_book | st_skill_book_svu_title |
| fp_skill_items.ltx | skill_book_toz34 | - | - | - | INHERITS skill_book | st_skill_book_toz34_title |
| fp_skill_items.ltx | skill_book_usp | - | - | - | INHERITS skill_book | st_skill_book_usp_title |
| fp_skill_items.ltx | skill_book_val | - | - | - | INHERITS skill_book | st_skill_book_val_title |
| fp_skill_items.ltx | skill_book_vintorez | - | - | - | INHERITS skill_book | st_skill_book_vintorez_title |
| fp_skill_items.ltx | skill_book_walther | - | - | - | INHERITS skill_book | st_skill_book_walther_title |
| fp_skill_items.ltx | skill_book_wincheaster1300 | - | - | - | INHERITS skill_book | st_skill_book_wincheaster1300_title |
| fp_sleep_items.ltx | sleeping_bag | 10,25 | 2x2 | 50% | SHARED(10) | sleeping_bag_title |
| quest_items.ltx | esc_trader_habar | 10,25 | 2x2 | 50% | SHARED(10) | st_esc_trader_habar_name |
| quest_items.ltx | esc_quest_magic_vodka | 5,2 | 1x2 | 45% | SHARED(2) | st_esc_quest_magic_vodka |
| quest_items.ltx | esc_quest_spec_medkit | 16,20 | 2x1 | 60% | OK | st_esc_quest_spec_medkit |
| quest_items.ltx | gar_quest_vodka_2 | 5,2 | 1x2 | 45% | SHARED(2) | st_gar_quest_vodka_2 |
| quest_items.ltx | agr_quest_duty_case | 10,25 | 2x2 | 50% | SHARED(10) | st_agr_quest_duty_case |
| quest_items.ltx | yan_quest_granade | 10,9 | 1x1 | 20% | OK | st_yan_quest_granade |
| quest_items.ltx | red_quest_prototipe_device | 11,3 | 1x1 | 52% | OK | st_red_quest_prototipe_device |
| quest_items.ltx | document | 5,37 | 2x1 | 49% | SHARED(4) | Document |
| quest_items.ltx | doc_1 | - | - | - | INHERITS document | doc_1 |
| quest_items.ltx | doc_2 | - | - | - | INHERITS document | doc_2 |
| quest_items.ltx | doc_3 | - | - | - | INHERITS document | doc_3 |
| quest_items.ltx | doc_4 | - | - | - | INHERITS document | doc_4 |
| quest_items.ltx | doc_5 | - | - | - | INHERITS document | doc_5 |
| quest_items.ltx | doc_6 | - | - | - | INHERITS document | doc_6 |
| quest_items.ltx | doc_7 | - | - | - | INHERITS document | doc_7 |
| quest_items.ltx | doc_8 | - | - | - | INHERITS document | doc_8 |
| quest_items.ltx | doc_9 | - | - | - | INHERITS document | doc_9 |
| quest_items.ltx | doc_10 | - | - | - | INHERITS document | doc_10 |
| quest_items.ltx | doc_11 | - | - | - | INHERITS document | doc_11 |
| quest_items.ltx | doc_12 | - | - | - | INHERITS document | doc_12 |
| quest_items.ltx | doc_13 | - | - | - | INHERITS document | doc_13 |
| quest_items.ltx | doc_14 | - | - | - | INHERITS document | doc_14 |
| quest_items.ltx | doc_15 | - | - | - | INHERITS document | doc_15 |
| quest_items.ltx | ammo_package | 10,25 | 2x2 | 50% | SHARED(10) | st_ammo_package_name |
| quest_items.ltx | products_package | - | - | - | INHERITS ammo_package | st_products_package_name |
| quest_items.ltx | shilov_rukzak | 10,25 | 2x2 | 50% | SHARED(10) | st_shilov_rukzak |
| quest_items.ltx | fp_impounded_goods | 10,25 | 2x2 | 50% | SHARED(10) | st_fp_impounded_goods |
| quest_items.ltx | fp_outpost_pda | 10,25 | 2x2 | 50% | SHARED(10) | st_fp_outpost_pda |
| quest_items.ltx | pda_for_quests | 10,25 | 2x2 | 50% | SHARED(10) | st_pda_for_quests_name |
| quest_items.ltx | fp_dnk_sample | 10,25 | 2x2 | 50% | SHARED(10) | st_fp_dnk_sample |

## Atlas map

`#` = something is drawn in the cell, `.` = free (transparent), `*` = a cell used by one of our sections

```
     0  1  2  3  4  5  6  7  8  9  10 11 12 13 14 15 16 17 18 19 
  0  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  
  1  #  #  #  .  .  .  #  #  #  #  #  #  #  #  #  #  #  #  #  #  
  2  #  #  #  #  #  #* #  #  #  #  #  #  #  #  #  #  #  #  #  #  
  3  #  #  #  #  #  #* #  #  #  .  .  #* #  #  #  #  #  #  #  #  
  4  .  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  
  5  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  .  #  
  6  #  #  #  #  #  #  #  #  .  .  #  #  #  #  #  #  #  #  #  #  
  7  #  #  #  .  .  #  #  #  #  #  #  #  .* .* .  #* #  #  #  #  
  8  #  #  #  #  #  #  #  #  #  .  #  #  #  #  #  #  #  #  #  #  
  9  .  #  #  #  #  #  #  #  #  #  #* #  #  #  #  #  #  #  #  #  
 10  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  
 11  #  #  #  .  .  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  
 12  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  
 13  #  #  #  .  .  #  #  .  #  #  #  #  #  #  #  #  #  #  #  #  
 14  #  #  #  #  #  #* #  #  #  #* #  #  #  #  #  #  #  #  #  #  
 15  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  
 16  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  
 17  .  #  #  .  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  
 18  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  
 19  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  
 20  #  #  #  #  #  #  #  #  #  #  #  #  .  .  #  #  #* #* #  #  
 21  #  #  #  .  .  #  #  #  #  .  #  #  #  #  #  #  #  #  #  #  
 22  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  
 23  #  #  #  #  .  #  #  #  #  #  #  #* #  #  #  #  #  #  #  #  
 24  #  #  #  #  #  #  #  #  .  .  .  #  #  #  #  #  #  #  #  #  
 25  #  #  #  .  .  #  #  #  #  #  #* #* #  #  #  #  #  #  #  #  
 26  #  #  #  #  #  #  #  #  .  .  #* #* #  #  #  #  #  #  #  #  
 27  #  #  #  .  .  #  #  #  #  #  #  #  #  #  #  #  #  .  .  .  
 28  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  .  .  .  
 29  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  .  .  .  
 30  #  #  #  #  #  #  #  #  #  #* #* #* #* #* #* #* #* #* #* .  
 31  #  #  #  .  .  #  #  #  #  #* #* #* #* #* #* #* #* #* #* .  
 32  #  #  #  #  #  #  #  #  .  #* #* #* #* #* #* #* #* #* #* .  
 33  #  #  #  #  .  #  #  #  .  #* #* #* #* #* #* #* #* #* #* .  
 34  #  #  #  #  #  .  .  .  .  #* #* #* #* #* #* #* #* #* #* .  
 35  #  #  #  #  #  .  .  .  .  #* #* #* #* #* #* #* #* #* #* .  
 36  #  #  #  #  #  #  .  .  .  #* #* #* #* #* #* #* #* .  .  .  
 37  #  #  #  #* #* #* #* .  .  #* #* #* #* #* #* #* #* .  .  .  
 38  #* #* #* #* #* #* #* #* #* #* #* #* #* #* #* #* #* .  .  .  
 39  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  
```
