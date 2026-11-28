# Иконки предметов Freeplay Extras: где править

Таблица и карта ниже сгенерированы скриптом `tools/icon_audit.py` по настоящему атласу (`python3 tools/icon_audit.py --out docs/icons.md --preview docs/icons_preview.png`; нужен Pillow). После правки иконок или координат запустите его заново. Картинка `docs/icons_preview.png` показывает, что сейчас нарисовано в каждой назначенной клетке.

## Где что лежит

| что править | файл | что искать |
|---|---|---|
| какая клетка атласа у предмета | `gamedata/configs/misc/*.ltx` аддона (имя файла в таблице ниже) | секция предмета: `inv_grid_x`, `inv_grid_y` (клетка), `inv_grid_width`, `inv_grid_height` (размер в клетках) |
| сами картинки | `gamedata/textures/ui/ui_icon_equipment.dds` (1024x2048, DXT3, клетка 50x50 px, x вправо, y вниз) | сейчас файл только в ядре SRP; чтобы рисовать, скопируйте его в `addons/freeplay_extras/gamedata/textures/ui/` под тем же именем (копировать в аддон можно, ядро не трогаем) и укажите его скрипту через `--atlas` |
| документы (doc_1 ... doc_15) | `quest_items.ltx`, секция `[document]` (родитель) и `[doc_N]:document` | у всех 15 документов одна клетка родителя; своя клетка у документа = добавить `inv_grid_x/y` в его секцию |
| книги навыков | `fp_skill_items.ltx`, секция `[skill_book]` и `[skill_book_<оружие>]` | то же правило: клетка родителя общая |
| артефакты OGSM | `fp_artefacts.ltx` | `af_mica`, `af_slug`, `af_ball`, `af_thorn` |
| части мутантов | `fp_monster_items.ltx` | `mutant_*` |
| костюмы | `fp_outfit.ltx` | `*_outfit` |
| названия, тексты | `configs/text/<язык>/fp_extras.xml` | `<string id="doc_15">` и т.п. |
| откуда брать готовые рисунки | `gamedata/new_items_icons.txt` | клетки в атласах OGSM и SGM для каждой секции |

Новый документ: скопируйте секцию `[doc_15]:document` в `quest_items.ltx` как `[doc_16]:document`, поправьте `inv_name`, `description` (и свою клетку), добавьте строки в `fp_extras.xml` всех языков, имя в `doc_list` и цену в `doc_price` в `ogsm_bring_items.script`.

## Что показала проверка (на этом атласе)

1. **Документы и книги навыков не имеют иконки.** Их клетка (2,25) размером 2x1 в атласе пустая (4%). Это 15 документов, 34 книги навыков и оба dev-предмета.
2. **Артефакты и части мутантов стоят в занятых клетках.** Ряд y=30 слева (x от 0 до 8) в атласе занят кусками иконок оружия, а не свободен: `af_mica`, `af_slug`, `af_ball`, `af_thorn` и пять частей мутантов показывают обрезки винтовок. Клетки (9,30) и (10,30) пусты (`mutant_controller_hand`, `mutant_pseudogigant_nail`) и тоже без иконки.
3. **Свободное место для новых иконок** есть справа и внизу атласа: см. карту в конце (`.` = свободно). Целиком свободна область x от 9 до 19, y от 30 до 38, и ещё нижние ряды 34-38.
4. Общая клетка (10,25) размером 2x2 используется 10 квестовыми предметами (ящик): это заглушка, а не ошибка.
5. Пять костюмов с общей клеткой (16,13), три с (18,17): заглушки до своих иконок.

Atlas: 1024x2048 px, cell 50 px. Sections with their own cell: {'EMPTY': 7, 'OK': 22, 'SHARED': 20}

| file | section | cell x,y | size | drawn | status | inv_name |
|---|---|---|---|---|---|---|
| devices.ltx | device_flare | 12,7 | 2x1 | 0% | EMPTY | device_flare |
| devices.ltx | detector_simple | 9,14 | 1x1 | 44% | OK | st_detector1 |
| devices.ltx | detector_advanced | 15,7 | 1x1 | 51% | OK | st_detector2 |
| devices.ltx | detector_elite | 5,14 | 1x1 | 48% | OK | st_detector3 |
| fp_artefacts.ltx | af_mica | 0,30 | 1x1 | 8% | OK | st_af_mica_name |
| fp_artefacts.ltx | af_slug | 1,30 | 1x1 | 27% | OK | st_af_slug_name |
| fp_artefacts.ltx | af_ball | 2,30 | 1x1 | 38% | OK | st_af_ball_name |
| fp_artefacts.ltx | af_thorn | 3,30 | 1x1 | 27% | OK | st_af_thorn_name |
| fp_deserves.ltx | fp_deserve_case | 11,23 | 1x1 | 36% | OK |  |
| fp_deserves.ltx | dv_dolg_holeman_case | - | - | - | INHERITS fp_deserve_case | dolg_holeman_case_title |
| fp_deserves.ltx | dv_freedom_boss_case | - | - | - | INHERITS fp_deserve_case | freedom_boss_case_title |
| fp_deserves.ltx | dv_army_driver_case | - | - | - | INHERITS fp_deserve_case | army_driver_case_title |
| fp_deserves.ltx | dv_stalker_messenger_case | - | - | - | INHERITS fp_deserve_case | stalker_messenger_case_title |
| fp_deserves.ltx | dv_bandit_boss_case | - | - | - | INHERITS fp_deserve_case | bandit_boss_case_title |
| fp_deserves.ltx | dv_stalker_avoska_case | - | - | - | INHERITS fp_deserve_case | stalker_avoska_case_title |
| fp_deserves.ltx | dv_stalker_wild_napr_case | - | - | - | INHERITS fp_deserve_case | stalker_wild_napr_case_title |
| fp_deserves.ltx | dv_renegade_baron_case | - | - | - | INHERITS fp_deserve_case | renegade_baron_case_title |
| fp_deserves.ltx | dv_army_sviridov_case | - | - | - | INHERITS fp_deserve_case | army_sviridov_case_title |
| fp_dev.ltx | fp_dev_console | 2,25 | 2x1 | 4% | EMPTY | st_fp_dev_console_name |
| fp_dev.ltx | fp_dev_tools | 2,25 | 2x1 | 4% | EMPTY | st_fp_dev_tools_name |
| fp_medals_items.ltx | medal_sect | 10,25 | 2x2 | 49% | SHARED(10) |  |
| fp_medals_items.ltx | medal_rank_100 | - | - | - | INHERITS medal_sect | st_medal_100_title |
| fp_medals_items.ltx | medal_rank_200 | - | - | - | INHERITS medal_sect | st_medal_200_title |
| fp_medals_items.ltx | medal_rank_400 | - | - | - | INHERITS medal_sect | st_medal_400_title |
| fp_medals_items.ltx | medal_rank_600 | - | - | - | INHERITS medal_sect | st_medal_600_title |
| fp_medals_items.ltx | medal_rank_800 | - | - | - | INHERITS medal_sect | st_medal_800_title |
| fp_medals_items.ltx | medal_rank_1000 | - | - | - | INHERITS medal_sect | st_medal_1000_title |
| fp_medals_items.ltx | medal_rank_1100 | - | - | - | INHERITS medal_sect | st_medal_1100_title |
| fp_medals_items.ltx | medal_rank_1200 | - | - | - | INHERITS medal_sect | st_medal_1200_title |
| fp_monster_items.ltx | mutant_tushkano_head | 4,30 | 1x1 | 12% | OK | mutant_tushkano_head |
| fp_monster_items.ltx | mutant_izlom_hand | 5,30 | 1x1 | 28% | OK | mutant_izlom_hand |
| fp_monster_items.ltx | mutant_cat_tail | 6,30 | 1x1 | 37% | OK | mutant_cat_tail |
| fp_monster_items.ltx | mutant_poltergeist_hand | 7,30 | 1x1 | 24% | OK | mutant_poltergeist_hand |
| fp_monster_items.ltx | mutant_chimera_nail | 8,30 | 1x1 | 17% | OK | mutant_chimera_nail |
| fp_monster_items.ltx | mutant_controller_hand | 9,30 | 1x1 | 0% | EMPTY | mutant_controller_hand |
| fp_monster_items.ltx | mutant_pseudogigant_nail | 10,30 | 1x1 | 0% | EMPTY | mutant_pseudogigant_nail |
| fp_outfit.ltx | killer_outfit | 6,15 | 2x3 | 60% | OK | killer_outfit_name |
| fp_outfit.ltx | monolith_scientific_outfit | 16,13 | 2x3 | 70% | SHARED(5) | monolit_scientific_outfit_name |
| fp_outfit.ltx | red_ecolog_outfit | 16,13 | 2x3 | 70% | SHARED(5) | red_ecolog_outfit_name |
| fp_outfit.ltx | green_ecolog_outfit | 16,13 | 2x3 | 70% | SHARED(5) | green_ecolog_outfit_name |
| fp_outfit.ltx | cs_standart_outfit | 11,27 | 2x3 | 70% | OK | csky_standart_outfit_name |
| fp_outfit.ltx | bandit_heavy_outfit | 12,0 | 2x2 | 60% | OK | bandit_heavy_outfit_name |
| fp_outfit.ltx | dolg_scientific_outfit | 16,13 | 2x3 | 70% | SHARED(5) | dolg_scientific_outfit_name |
| fp_outfit.ltx | dolg_heavy_extra_outfit | 16,16 | 2x3 | 74% | OK | dolg_skat_light_outfit_name |
| fp_outfit.ltx | dolg_exo_outfit | 14,13 | 2x3 | 54% | OK | dolg_black_exoskeleton_name |
| fp_outfit.ltx | svoboda_light2_outfit | 12,13 | 2x3 | 62% | OK | svoboda_light2_outfit_name |
| fp_outfit.ltx | svoboda_scientific_outfit | 16,13 | 2x3 | 70% | SHARED(5) | svoboda_scientific_outfit_name |
| fp_outfit.ltx | soldier_outfit_grey | 18,17 | 2x3 | 76% | SHARED(3) | outfit_soldier_name |
| fp_outfit.ltx | soldier_outfit_brown | 18,17 | 2x3 | 76% | SHARED(3) | outfit2_soldier_name |
| fp_outfit.ltx | military_extra_outfit | 18,17 | 2x3 | 76% | SHARED(3) | military_skat_name |
| fp_skill_items.ltx | skill_book | 2,25 | 2x1 | 4% | EMPTY |  |
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
| fp_sleep_items.ltx | sleeping_bag | 10,25 | 2x2 | 49% | SHARED(10) | sleeping_bag_title |
| quest_items.ltx | esc_trader_habar | 10,25 | 2x2 | 49% | SHARED(10) | st_esc_trader_habar_name |
| quest_items.ltx | esc_quest_magic_vodka | 5,2 | 1x2 | 44% | SHARED(2) | st_esc_quest_magic_vodka |
| quest_items.ltx | esc_quest_spec_medkit | 16,20 | 2x1 | 59% | OK | st_esc_quest_spec_medkit |
| quest_items.ltx | gar_quest_vodka_2 | 5,2 | 1x2 | 44% | SHARED(2) | st_gar_quest_vodka_2 |
| quest_items.ltx | agr_quest_duty_case | 10,25 | 2x2 | 49% | SHARED(10) | st_agr_quest_duty_case |
| quest_items.ltx | yan_quest_granade | 10,9 | 1x1 | 18% | OK | st_yan_quest_granade |
| quest_items.ltx | red_quest_prototipe_device | 11,3 | 1x1 | 51% | OK | st_red_quest_prototipe_device |
| quest_items.ltx | document | 2,25 | 2x1 | 4% | EMPTY | Document |
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
| quest_items.ltx | ammo_package | 10,25 | 2x2 | 49% | SHARED(10) | st_ammo_package_name |
| quest_items.ltx | products_package | - | - | - | INHERITS ammo_package | st_products_package_name |
| quest_items.ltx | shilov_rukzak | 10,25 | 2x2 | 49% | SHARED(10) | st_shilov_rukzak |
| quest_items.ltx | fp_impounded_goods | 10,25 | 2x2 | 49% | SHARED(10) | st_fp_impounded_goods |
| quest_items.ltx | fp_outpost_pda | 10,25 | 2x2 | 49% | SHARED(10) | st_fp_outpost_pda |
| quest_items.ltx | pda_for_quests | 10,25 | 2x2 | 49% | SHARED(10) | st_pda_for_quests_name |
| quest_items.ltx | fp_dnk_sample | 10,25 | 2x2 | 49% | SHARED(10) | st_fp_dnk_sample |

## Atlas map

`#` = something is drawn in the cell, `.` = free (transparent), `*` = a cell used by one of our sections

```
     0  1  2  3  4  5  6  7  8  9  10 11 12 13 14 15 16 17 18 19 
  0  #  #  #  #  #  #  #  #  #  #  #  #  #* #* #  #  #  #  #  #  
  1  #  #  #  .  .  .  #  #  #  #  #  #  #* #* #  #  #  #  #  #  
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
 13  #  #  #  .  .  #  #  .  #  #  #  #  #* #* #* #* #* #* #  #  
 14  #  #  #  #  #  #* #  #  #  #* #  #  #* #* #* #* #* #* #  #  
 15  #  #  #  #  #  #  #* #* #  #  #  #  #* #* #* #* #* #* #  #  
 16  #  #  #  #  #  #  #* #* #  #  #  #  #  #  #  #  #* #* #  #  
 17  .  #  #  .  #  #  #* #* #  #  #  #  #  #  #  #  #* #* #* #* 
 18  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #* #* #* #* 
 19  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #* #* 
 20  #  #  #  #  #  #  #  #  #  #  #  #  .  .  #  #  #* #* #  #  
 21  #  #  #  .  .  #  #  #  #  .  #  #  #  #  #  #  #  #  #  #  
 22  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  
 23  #  #  #  #  .  #  #  #  #  #  #  #* #  #  #  #  #  #  #  #  
 24  #  #  #  #  #  #  #  #  .  .  .  #  #  #  #  #  #  #  #  #  
 25  #  #  #* .* .  #  #  #  #  #  #* #* #  #  #  #  #  #  #  #  
 26  #  #  #  #  #  #  #  #  .  .  #* #* #  #  #  #  #  #  #  #  
 27  #  #  #  .  .  #  #  #  #  #  #  #* #* #  #  #  #  .  .  .  
 28  #  #  #  #  #  #  #  #  #  #  #  #* #* #  #  #  #  .  .  .  
 29  #  #  #  #  #  #  #  #  #  #  #  #* #* #  #  #  #  .  .  .  
 30  #* #* #* #* #* #* #* #* #* .* .* .  .  .  .  .  .  .  .  .  
 31  #  #  #  .  .  #  #  #  #  .  .  .  .  .  .  .  .  .  .  .  
 32  #  #  #  #  #  #  #  #  .  .  .  .  .  .  .  .  .  .  .  .  
 33  #  #  #  #  .  #  #  #  .  .  .  .  .  .  .  .  .  .  .  .  
 34  #  #  #  #  #  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  
 35  #  #  #  #  #  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  
 36  #  #  #  #  #  #  .  .  .  .  .  .  .  .  .  .  .  .  .  .  
 37  #  #  #  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  
 38  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  
 39  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  
```
