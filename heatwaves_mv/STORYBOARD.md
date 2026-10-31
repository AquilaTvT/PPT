# Heat Waves (Japanese Version) — fan MV storyboard

Song: Glass Animals「Heat Waves」, Japanese cover & lyrics by Lime (198.7 s, 81 BPM, 66 bars of 2.963 s; bar 0 = 2.16 s).
Every cut lands on a bar line; inside shots, light pulses, channel flips, crossing lamps and fireworks follow the beat grid
fitted on the separated drum stem.

## Concept 「陽炎の向こうの君」

初夏零時: a sleepless boy keeps the TV on so he won't think about *us*.
Every summer memory of 君 comes back to him the way a heat mirage does: bright,
wobbling, and gone the moment he gets close. Present day is a navy midnight
room lit by a CRT; the past is a sun-bleached country road under
cumulonimbus. Heat haze is the hinge between the two worlds: whenever the
picture starts to shimmer, we fall from one into the other. At the end the TV
is switched off, dawn comes, and the カーブミラー that once showed the two of
them shows only him, walking on.

## Look

Taken from the reference only at the level of craft: a limited set of inks,
flat shapes, and an AM halftone screen doing every gradient, glow and shadow,
so each frame reads like a riso / screen print at 1080p (the "pixel" feel);
the TV world is real low-res ordered dither on a 16-colour palette. Palette,
world, motifs and staging are new.

| world | inks |
|---|---|
| memory / noon | cobalt `#2A5FBF` → sky `#6FB6E8` → haze `#DDEFF4`, cloud lavender `#AEB5E6`, paddy greens, ribbon red `#E8383D`, cream paper |
| present / midnight | navy `#0B1030` `#141B3D`, CRT teal `#2BB3B1` `#7FE3DE`, moon cream |
| festival | navy + lantern coral `#FF6A55`, gold `#FFCB45`, pink `#FF5C9E` |
| goodbye / dusk | peach → rose → violet `#FFC489` `#E85A7A` `#5B3C8C` |
| climax / sunset road | coral → magenta → violet |
| ending / dawn | pale gold, peach, lilac |

Motifs: circles (sun → カーブミラー → TV standby dot → firework → moon), mirrors
(逃げ水 on the road, the convex traffic mirror, the TV glass, the river),
vertical heat ripples, the red `0:00` clock, the straw hat with the red ribbon.

Typography: Japanese lines set vertically (縦書き) in Shippori Mincho with a
halftone drop shadow, each character dropping into place as it is sung; a
small Chinese translation (my own wording) runs beside it in Noto Serif SC.
English lines in Cormorant italic; TV-world text in DotGothic16.

Characters: 君 was generated with Anima-Turbo in ComfyUI (CPU), cut out with
anime-seg, then re-inked by `tools/stylize.py` (flattened cels snapped to the
palette, line art in navy, shading turned into the same halftone screen as the
backgrounds, background inpainted for 2.5D parallax). The boy is only ever a
silhouette.

## Shot list

| # | time (s) | shot | lyric | transition out |
|---|---|---|---|---|
| 1 | 0.00–2.16 | `s01_power` black, red standby LED, the CRT switches on | — | cut |
| 2 | 2.16–8.09 | `s02_tvroad` inside the CRT: the noon road in 320×180 dither, typed subtitles | Last night… / Don't stop… | cut |
| 3 | 8.09–11.05 | `s03_pullback` pixel title card, pull back to reveal the midnight room | Don't want… | cut |
| 4 | 11.05–14.02 | `s04_details` wind chime against the moon, a gust; the fan | You know that I'm never gonna lose | dissolve |
| 5 | 14.02–16.98 | `s05_intotv` push into the TV, the room starts to ripple, white-out on the drop | — | cut |
| 6 | 16.98–19.94 | `s06_road` POV down the noon road, glare pulsing on the beat | 光りだすロード / 揺らいでくビジョン | heat |
| 7 | 19.94–22.90 | `s07_mirage` low on the asphalt: the mirage mirrors the sky; 君 stands inside it | 熱波ゆらり 泳いでくミラー | whip |
| 8 | 22.90–25.87 | `s08_side` side parallax along the paddies, poles whipping past | 光りだすロード / 揺らいでくビジョン | dots |
| 9 | 25.87–28.83 | `s09_curvemirror` カーブミラー at the junction: 君 swims in the convex reflection | 熱波ゆらり 泳いでくミラー | flash |
| 10 | 28.83–31.79 | `s10_portrait` 君 reveal: hat, ribbon, sunflowers, sea (2.5D) | 思い浮かぶの君ばかり | cut |
| 11 | 31.79–34.76 | `s11_clock` the LED clock flips 23:59 → 0:00 on the beat | 初夏零時過ぎたばかり | heat |
| 12 | 34.76–37.72 | `s12_type` HEAT WAVES marquees melting; the boy walks into the haze | ヒートウェイブに迷うのさ | dots |
| 13 | 37.72–40.68 | `s13_walkaway` 君 walks away down the road and dissolves into dots | 君に幸せあげられない | flash |
| 14 | 40.68–43.65 | `s14_sunflowers` low in the sunflower field, the straw hat sails across the sky | 思い浮かぶの君ばかり | crt |
| 15 | 43.65–46.61 | `s15_house` midnight: his house, the one window lit by the TV | 初夏零時過ぎたばかり | dissolve |
| 16 | 46.61–49.57 | `s16_train` the coastal railcar along the seawall | ヒートウェイブに迷うのさ | wipe |
| 17 | 49.57–52.54 | `s17_busstop` 君 at the wooden bus stop with a ramune (2.5D), dusk creeps in | 君に幸せあげられない | cut |
| 18 | 52.54–55.50 | `s18_tvon` the TV clicks on: colour bars | テレビつけて消さないように | cut |
| 19 | 55.50–58.46 | `s19_surf` channel surfing, one channel per beat | 僕らのこと考えないように | crt |
| 20 | 58.46–61.42 | `s20_hollywood` the late-night roadshow: palms, a convertible at sunset | 今日のハリウッド映画放映 | cut |
| 21 | 61.42–64.39 | `s21_projection` the movie couple dissolves into our memory on the screen | 僕らのことまるで投影 | flash |
| 22 | 64.39–67.35 | `s22_happy` 君 laughing in golden light, his reflection on the glass | 幸せに君なるはず | dots |
| 23 | 67.35–70.31 | `s23_crossing` level crossing: lamps blinking on the beat, a train strobes her away | 僕じゃなきゃ可能なはず | heat |
| 24 | 70.31–73.28 | `s24_nigemizu` 逃げ水 spreads; only her reflection is in the water | 路に広がる逃げ水 | dissolve |
| 25 | 73.28–76.24 | `s25_dark` night road, fireflies, iris to black | 闇の中ではもう見えず | cut |
| 26 | 76.24–79.20 | `s26_yukata` festival: 君 in yukata glancing back (2.5D) | 思い浮かぶの君ばかり | dots |
| 27 | 79.20–82.17 | `s27_goldfish` kingyo-sukui from above; the poi tears | 初夏零時過ぎたばかり | wipe |
| 28 | 82.17–85.13 | `s28_riverbank` the two of them on the riverbank, fireworks on the beat | ヒートウェイブに迷うのさ | flash |
| 29 | 85.13–88.10 | `s29_profile` fireworks light on her face | 君に幸せあげられない | white |
| 30 | 88.10–91.06 | `s30_underwater` drowning in the mirror: caustics, sinking | 闘えず息できず | heat |
| 31 | 91.06–94.02 | `s31_seawall` dusk seawall, the two of them | 愛とか言っていたって | dissolve |
| 32 | 94.02–96.99 | `s32_station` かげろう station (prev 逃げ水, next 蜃気楼), the train pulls in | 行くべきなのさ | cut |
| 33 | 96.99–99.95 | `s33_door` 君 in the train doorway | ほかの誰かふさわしいよ | cut |
| 34 | 99.95–102.91 | `s34_doors_close` the doors close on her silhouette | そりゃつらいけど | dissolve |
| 35 | 102.91–105.87 | `s35_eyes` tears | 君もわかるはず | dissolve |
| 36 | 105.87–108.84 | `s36_breaking` her picture peels off into its own halftone dots | 泣いてる君壊れそうだ | dots |
| 37 | 108.84–111.80 | `s37_depart` the train leaves; him alone on the platform; white bloom | さよならにも一度だけ | cut |
| 38 | 111.80–114.76 | `s38_wall` a wall of CRTs, every memory at once | 思い浮かぶの君ばかり | crt |
| 39 | 114.76–117.72 | `s39_melt` the 0:00 LED melts | 初夏零時過ぎたばかり | flash |
| 40 | 117.72–120.69 | `s40_chase` sunset road chase: however fast he runs, she stays 40 m ahead | ヒートウェイブに迷うのさ | heat |
| 41 | 120.69–123.65 | `s41_embers` 君 against the sun burns away into embers | 君に幸せあげられない | dots |
| 42 | 123.65–126.61 | `s42_finale` festival finale over the two of them | 思い浮かぶの君ばかり | whip |
| 43 | 126.61–129.58 | `s43_house_fw` the midnight house under memory-fireworks | 初夏零時過ぎたばかり | flash |
| 44 | 129.58–132.54 | `s44_kaleido` the sunset road folded into a kaleidoscope | ヒートウェイブに迷うのさ | heat |
| 45 | 132.54–135.50 | `s45_mirror` the カーブミラー now shows only him | 君に幸せあげられない | cut |
| 46 | 135.50–138.47 | `s46_sleep` she sleeps on the train, pole shadows sweeping | 君はどんな夢のなかに | dissolve |
| 47 | 138.47–141.43 | `s47_smile` closer: the contented smile | 満たされた笑み浮かべて | dissolve |
| 48 | 141.43–144.39 | `s48_hands` his empty hands in the TV light | 思い知る自分の無力 | dissolve |
| 49 | 144.39–147.36 | `s49_noshadow` light floods her face until nothing is in shadow | 陰りない君の表情に | white |
| 50 | 147.36–150.32 | `s50_walk` night walk past the street lamps | 思い浮かぶの君ばかり | dissolve |
| 51 | 150.32–153.28 | `s51_vending` the vending machine's glow | 初夏零時過ぎたばかり | dissolve |
| 52 | 153.28–156.25 | `s52_nightmirage` a mirage at night: her silhouette on the warm road | ヒートウェイブに迷うのさ | cut |
| 53 | 156.25–159.21 | `s53_stop` he stops; she fades | 君に幸せあげられない | dissolve |
| 54 | 159.21–162.17 | `s54_rise` tilt up into the pre-dawn sky, stars stretching, white-out | 君に幸せあげられない | cut |
| 55 | 162.17–165.14 | `s55_sunrise` sunrise over the sea | Sometimes, all I think about is you | cut |
| 56 | 165.14–168.10 | `s56_calendar` the June calendar loses a day on every beat | Late nights in the middle of June | flash |
| 57 | 168.10–171.06 | `s57_ghosts` dawn road full of her mirages, appearing on the beat | Heat waves been fakin' me out | heat |
| 58 | 171.06–174.03 | `s58_burn` the summer memory burns away like film | Can't make you happier now | white |
| 59 | 174.03–176.99 | `s59_wall` the CRT wall, more and more static | Sometimes, all I think about is you | crt |
| 60 | 176.99–179.95 | `s60_off` he switches the TV off; dawn in the window (4:52) | Late nights in the middle of June | dissolve |
| 61 | 179.95–182.92 | `s61_morningwalk` walking past the paddies in the morning | Heat waves been fakin' me out | dots |
| 62 | 182.92–185.88 | `s62_crane` crane up over him on the road | Can't make you happier now | dissolve |
| 63 | 185.88–191.81 | `s63_mirror` the カーブミラー shows the two of them, then only him | Road shimmer… / Heat, heat waves… | dots |
| 64 | 191.81–198.74 | `s64_title` title card under the cumulonimbus, fade out | Road shimmer… / Heat, heat waves… | — |
