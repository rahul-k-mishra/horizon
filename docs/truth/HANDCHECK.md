# Hand check of the truth tables

For the author. Drawn by scripts/draw_handcheck.py with seed 20261025 (logs/draw_handcheck.log) from the 30 deterministic games of docs/truth/gvgai.json, written by scripts/truth_vgdl.py (logs/truth_vgdl.log). The predicates are those of docs/PREREG.md draft v0, Section 5.

**How to use this sheet.** For each game, open its description (and level files) at the paths given, read each clause at its line, and decide whether the predicate's verdict is right for that game and level by the registered wording. Mark one box per row and add a note where you disagree. A clause line refers to the description unless the file named is a level file. No answer is filled in.

**The rule after the check** (docs/PREREG.md, Section 5): every disagreement is resolved from the GVGAI source, fixes the generator, and is listed in the registration; the generator is then rerun on all games and 5 fresh games are checked, which must agree on every predicate.

## clusters

Description: `third_party/gvgai/examples/gridphysics/clusters.txt`. Levels checked: 0 (`third_party/gvgai/examples/gridphysics/clusters_lvl0.txt`) and 3 (`third_party/gvgai/examples/gridphysics/clusters_lvl3.txt`).

| predicate | level | generator's verdict | the clauses it rests on (file:line, text, what was read) | agree | disagree | note |
|---|---|---|---|---|---|---|
| A1, input coupling | 0 | **holds** | clusters.txt:18 `avatar > MovingAvatar img=oryx/knight1` (avatar type avatar is MovingAvatar) | [ ] | [ ] |  |
| A1, input coupling | 3 | **holds** | clusters.txt:18 `avatar > MovingAvatar img=oryx/knight1` (avatar type avatar is MovingAvatar) | [ ] | [ ] |  |
| A2, one controlled object | 0 | **fails** | clusters.txt:40 `box avatar > bounceForward` (bounceForward moves box when the avatar moves into it) | [ ] | [ ] |  |
| A2, one controlled object | 3 | **fails** | clusters.txt:40 `box avatar > bounceForward` (bounceForward moves box when the avatar moves into it) | [ ] | [ ] |  |
| A3, lattice motion | 0 | **holds** | clusters.txt:18 `avatar > MovingAvatar img=oryx/knight1` (avatar is MovingAvatar at speed 1)<br>clusters.txt:36 `InteractionSet` (no interaction moves the avatar) | [ ] | [ ] |  |
| A3, lattice motion | 3 | **holds** | clusters.txt:18 `avatar > MovingAvatar img=oryx/knight1` (avatar is MovingAvatar at speed 1)<br>clusters.txt:36 `InteractionSet` (no interaction moves the avatar) | [ ] | [ ] |  |
| A4, a fixed set of blockers | 0 | **holds** | clusters.txt:49 `avatar block > stepBack` (blueblock blocks the avatar)<br>clusters.txt:49 `avatar block > stepBack` (greenblock blocks the avatar)<br>clusters.txt:49 `avatar block > stepBack` (redblock blocks the avatar)<br>clusters.txt:37 `avatar wall > stepBack` (wall blocks the avatar)<br>clusters.txt:8 `blueblock > img=newset/blockB` (blocker blueblock is Immovable)<br>clusters.txt:10 `greenblock > img=newset/blockG` (blocker greenblock is Immovable)<br>clusters.txt:9 `redblock > img=newset/blockR` (blocker redblock is Immovable)<br>clusters.txt:19 `wall > Immovable img=oryx/wall3 autotiling=True` (blocker wall is Immovable) | [ ] | [ ] |  |
| A4, a fixed set of blockers | 3 | **holds** | clusters.txt:49 `avatar block > stepBack` (blueblock blocks the avatar)<br>clusters.txt:49 `avatar block > stepBack` (greenblock blocks the avatar)<br>clusters.txt:49 `avatar block > stepBack` (redblock blocks the avatar)<br>clusters.txt:37 `avatar wall > stepBack` (wall blocks the avatar)<br>clusters.txt:8 `blueblock > img=newset/blockB` (blocker blueblock is Immovable)<br>clusters.txt:10 `greenblock > img=newset/blockG` (blocker greenblock is Immovable)<br>clusters.txt:9 `redblock > img=newset/blockR` (blocker redblock is Immovable)<br>clusters.txt:19 `wall > Immovable img=oryx/wall3 autotiling=True` (blocker wall is Immovable) | [ ] | [ ] |  |
| A5, a place goal | 0 | **fails** | clusters.txt:61 `SpriteCounter stype=box limit=0 win=True` (a winning termination)<br>clusters_lvl0.txt:3 `w..11...2.2.w` (the level places 8 sprite(s) of box) | [ ] | [ ] |  |
| A5, a place goal | 3 | **fails** | clusters.txt:61 `SpriteCounter stype=box limit=0 win=True` (a winning termination)<br>clusters_lvl3.txt:3 `w...1.2..c..w` (the level places 9 sprite(s) of box) | [ ] | [ ] |  |

## colourescape

Description: `third_party/gvgai/examples/gridphysics/colourescape.txt`. Levels checked: 0 (`third_party/gvgai/examples/gridphysics/colourescape_lvl0.txt`) and 3 (`third_party/gvgai/examples/gridphysics/colourescape_lvl3.txt`).

| predicate | level | generator's verdict | the clauses it rests on (file:line, text, what was read) | agree | disagree | note |
|---|---|---|---|---|---|---|
| A1, input coupling | 0 | **holds** | colourescape.txt:20 `normalAvatar > img=newset/girl3` (avatar type normalAvatar is MovingAvatar) | [ ] | [ ] |  |
| A1, input coupling | 3 | **holds** | colourescape.txt:20 `normalAvatar > img=newset/girl3` (avatar type normalAvatar is MovingAvatar) | [ ] | [ ] |  |
| A2, one controlled object | 0 | **fails** | colourescape.txt:47 `greenbox greenAvatar > bounceForward` (bounceForward moves greenbox when the avatar moves into it)<br>colourescape.txt:50 `redbox redAvatar > bounceForward` (bounceForward moves redbox when the avatar moves into it)<br>colourescape.txt:53 `bluebox blueAvatar > bounceForward` (bounceForward moves bluebox when the avatar moves into it)<br>colourescape.txt:56 `box normalAvatar  > bounceForward` (bounceForward moves box when the avatar moves into it) | [ ] | [ ] |  |
| A2, one controlled object | 3 | **fails** | colourescape.txt:47 `greenbox greenAvatar > bounceForward` (bounceForward moves greenbox when the avatar moves into it)<br>colourescape.txt:50 `redbox redAvatar > bounceForward` (bounceForward moves redbox when the avatar moves into it)<br>colourescape.txt:53 `bluebox blueAvatar > bounceForward` (bounceForward moves bluebox when the avatar moves into it)<br>colourescape.txt:56 `box normalAvatar  > bounceForward` (bounceForward moves box when the avatar moves into it) | [ ] | [ ] |  |
| A3, lattice motion | 0 | **holds** | colourescape.txt:21 `blueAvatar > img=newset/girl2` (blueAvatar is MovingAvatar at speed 1)<br>colourescape.txt:23 `greenAvatar > img=newset/girl1` (greenAvatar is MovingAvatar at speed 1)<br>colourescape.txt:20 `normalAvatar > img=newset/girl3` (normalAvatar is MovingAvatar at speed 1)<br>colourescape.txt:22 `redAvatar > img=newset/girl5` (redAvatar is MovingAvatar at speed 1)<br>colourescape.txt:44 `InteractionSet` (no interaction moves the avatar) | [ ] | [ ] |  |
| A3, lattice motion | 3 | **holds** | colourescape.txt:21 `blueAvatar > img=newset/girl2` (blueAvatar is MovingAvatar at speed 1)<br>colourescape.txt:23 `greenAvatar > img=newset/girl1` (greenAvatar is MovingAvatar at speed 1)<br>colourescape.txt:20 `normalAvatar > img=newset/girl3` (normalAvatar is MovingAvatar at speed 1)<br>colourescape.txt:22 `redAvatar > img=newset/girl5` (redAvatar is MovingAvatar at speed 1)<br>colourescape.txt:44 `InteractionSet` (no interaction moves the avatar) | [ ] | [ ] |  |
| A4, a fixed set of blockers | 0 | **holds** | colourescape.txt:45 `avatar wall > stepBack` (wall blocks the avatar)<br>colourescape.txt:25 `wall > Immovable img=oryx/wall3 autotiling=True` (blocker wall is Immovable) | [ ] | [ ] |  |
| A4, a fixed set of blockers | 3 | **holds** | colourescape.txt:45 `avatar wall > stepBack` (wall blocks the avatar)<br>colourescape.txt:25 `wall > Immovable img=oryx/wall3 autotiling=True` (blocker wall is Immovable) | [ ] | [ ] |  |
| A5, a place goal | 0 | **holds** | colourescape.txt:71 `SpriteCounter stype=exit limit=0 win=True` (a winning termination)<br>colourescape_lvl0.txt:2 `w........w.x.....w` (the level places 1 sprite(s) of exit)<br>colourescape.txt:61 `exit avatar > killSprite scoreChange=1` (the avatar removes the goal) | [ ] | [ ] |  |
| A5, a place goal | 3 | **holds** | colourescape.txt:71 `SpriteCounter stype=exit limit=0 win=True` (a winning termination)<br>colourescape_lvl3.txt:2 `w..x..3..wc...4..w` (the level places 1 sprite(s) of exit)<br>colourescape.txt:61 `exit avatar > killSprite scoreChange=1` (the avatar removes the goal) | [ ] | [ ] |  |

## glow

Description: `third_party/gvgai/examples/gridphysics/glow.txt`. Levels checked: 0 (`third_party/gvgai/examples/gridphysics/glow_lvl0.txt`) and 4 (`third_party/gvgai/examples/gridphysics/glow_lvl4.txt`).

| predicate | level | generator's verdict | the clauses it rests on (file:line, text, what was read) | agree | disagree | note |
|---|---|---|---|---|---|---|
| A1, input coupling | 0 | **holds** | glow.txt:5 `avatar > ShootAvatar img=newset/man3 frameRate=8 stype=spark` (avatar type avatar is ShootAvatar) | [ ] | [ ] |  |
| A1, input coupling | 4 | **holds** | glow.txt:5 `avatar > ShootAvatar img=newset/man3 frameRate=8 stype=spark` (avatar type avatar is ShootAvatar) | [ ] | [ ] |  |
| A2, one controlled object | 0 | **fails** | glow.txt:5 `avatar > ShootAvatar img=newset/man3 frameRate=8 stype=spark` (avatar type avatar is ShootAvatar: its use action creates a sprite) | [ ] | [ ] |  |
| A2, one controlled object | 4 | **fails** | glow.txt:5 `avatar > ShootAvatar img=newset/man3 frameRate=8 stype=spark` (avatar type avatar is ShootAvatar: its use action creates a sprite) | [ ] | [ ] |  |
| A3, lattice motion | 0 | **fails** | glow.txt:5 `avatar > ShootAvatar img=newset/man3 frameRate=8 stype=spark` (avatar is ShootAvatar, which turns in place when pressed in a new direction) | [ ] | [ ] |  |
| A3, lattice motion | 4 | **fails** | glow.txt:5 `avatar > ShootAvatar img=newset/man3 frameRate=8 stype=spark` (avatar is ShootAvatar, which turns in place when pressed in a new direction) | [ ] | [ ] |  |
| A4, a fixed set of blockers | 0 | **holds** | glow.txt:29 `avatar wall EOS > stepBack` (wall blocks the avatar)<br>glow.txt:18 `wall > Immovable color=BLACK img=oryx/wall3 autotiling=True` (blocker wall is Immovable) | [ ] | [ ] |  |
| A4, a fixed set of blockers | 4 | **holds** | glow.txt:29 `avatar wall EOS > stepBack` (wall blocks the avatar)<br>glow.txt:18 `wall > Immovable color=BLACK img=oryx/wall3 autotiling=True` (blocker wall is Immovable) | [ ] | [ ] |  |
| A5, a place goal | 0 | **fails** | glow.txt:39 `SpriteCounter stype=exit win=True` (a winning termination)<br>glow.txt:40 `Timeout limit=1500 win=True` (a winning termination) | [ ] | [ ] |  |
| A5, a place goal | 4 | **fails** | glow.txt:39 `SpriteCounter stype=exit win=True` (a winning termination)<br>glow.txt:40 `Timeout limit=1500 win=True` (a winning termination) | [ ] | [ ] |  |

## labyrinthdual

Description: `third_party/gvgai/examples/gridphysics/labyrinthdual.txt`. Levels checked: 0 (`third_party/gvgai/examples/gridphysics/labyrinthdual_lvl0.txt`) and 1 (`third_party/gvgai/examples/gridphysics/labyrinthdual_lvl1.txt`).

| predicate | level | generator's verdict | the clauses it rests on (file:line, text, what was read) | agree | disagree | note |
|---|---|---|---|---|---|---|
| A1, input coupling | 0 | **holds** | labyrinthdual.txt:16 `avatarNormal > img=newset/girl1` (avatar type avatarNormal is MovingAvatar) | [ ] | [ ] |  |
| A1, input coupling | 1 | **holds** | labyrinthdual.txt:16 `avatarNormal > img=newset/girl1` (avatar type avatarNormal is MovingAvatar) | [ ] | [ ] |  |
| A2, one controlled object | 0 | **holds** | labyrinthdual.txt:16 `avatarNormal > img=newset/girl1` (the one avatar sprite at start is avatarNormal, MovingAvatar, which creates nothing)<br>labyrinthdual.txt:20 `InteractionSet` (no bounceForward or pullWithIt with the avatar as partner, and no interaction with the avatar that creates another sprite) | [ ] | [ ] |  |
| A2, one controlled object | 1 | **holds** | labyrinthdual.txt:16 `avatarNormal > img=newset/girl1` (the one avatar sprite at start is avatarNormal, MovingAvatar, which creates nothing)<br>labyrinthdual.txt:20 `InteractionSet` (no bounceForward or pullWithIt with the avatar as partner, and no interaction with the avatar that creates another sprite) | [ ] | [ ] |  |
| A3, lattice motion | 0 | **holds** | labyrinthdual.txt:18 `avatarBlue > img=oryx/queen1` (avatarBlue is MovingAvatar at speed 1)<br>labyrinthdual.txt:16 `avatarNormal > img=newset/girl1` (avatarNormal is MovingAvatar at speed 1)<br>labyrinthdual.txt:17 `avatarRed > img=oryx/princess1` (avatarRed is MovingAvatar at speed 1)<br>labyrinthdual.txt:20 `InteractionSet` (no interaction moves the avatar) | [ ] | [ ] |  |
| A3, lattice motion | 1 | **holds** | labyrinthdual.txt:18 `avatarBlue > img=oryx/queen1` (avatarBlue is MovingAvatar at speed 1)<br>labyrinthdual.txt:16 `avatarNormal > img=newset/girl1` (avatarNormal is MovingAvatar at speed 1)<br>labyrinthdual.txt:17 `avatarRed > img=oryx/princess1` (avatarRed is MovingAvatar at speed 1)<br>labyrinthdual.txt:20 `InteractionSet` (no interaction moves the avatar) | [ ] | [ ] |  |
| A4, a fixed set of blockers | 0 | **holds** | labyrinthdual.txt:23 `avatarNormal wall > stepBack` (blueWall blocks the avatar)<br>labyrinthdual.txt:22 `avatar normalWall > stepBack` (normalWall blocks the avatar)<br>labyrinthdual.txt:23 `avatarNormal wall > stepBack` (redWall blocks the avatar)<br>labyrinthdual.txt:10 `blueWall > img=oryx/wall3 autotiling=True` (blocker blueWall is Immovable)<br>labyrinthdual.txt:8 `normalWall > img=oryx/wall1` (blocker normalWall is Immovable)<br>labyrinthdual.txt:9 `redWall > img=oryx/dirtwall autotiling=True` (blocker redWall is Immovable) | [ ] | [ ] |  |
| A4, a fixed set of blockers | 1 | **holds** | labyrinthdual.txt:23 `avatarNormal wall > stepBack` (blueWall blocks the avatar)<br>labyrinthdual.txt:22 `avatar normalWall > stepBack` (normalWall blocks the avatar)<br>labyrinthdual.txt:23 `avatarNormal wall > stepBack` (redWall blocks the avatar)<br>labyrinthdual.txt:10 `blueWall > img=oryx/wall3 autotiling=True` (blocker blueWall is Immovable)<br>labyrinthdual.txt:8 `normalWall > img=oryx/wall1` (blocker normalWall is Immovable)<br>labyrinthdual.txt:9 `redWall > img=oryx/dirtwall autotiling=True` (blocker redWall is Immovable) | [ ] | [ ] |  |
| A5, a place goal | 0 | **holds** | labyrinthdual.txt:38 `SpriteCounter stype=exit limit=0 win=True` (a winning termination)<br>labyrinthdual_lvl0.txt:2 `ww.....rrr....xw` (the level places 1 sprite(s) of exit)<br>labyrinthdual.txt:33 `exit avatar > killSprite scoreChange=1` (the avatar removes the goal) | [ ] | [ ] |  |
| A5, a place goal | 1 | **holds** | labyrinthdual.txt:38 `SpriteCounter stype=exit limit=0 win=True` (a winning termination)<br>labyrinthdual_lvl1.txt:3 `wxttttw.....ww.w` (the level places 1 sprite(s) of exit)<br>labyrinthdual.txt:33 `exit avatar > killSprite scoreChange=1` (the avatar removes the goal) | [ ] | [ ] |  |

## lasers

Description: `third_party/gvgai/examples/gridphysics/lasers.txt`. Levels checked: 0 (`third_party/gvgai/examples/gridphysics/lasers_lvl0.txt`) and 1 (`third_party/gvgai/examples/gridphysics/lasers_lvl1.txt`).

| predicate | level | generator's verdict | the clauses it rests on (file:line, text, what was read) | agree | disagree | note |
|---|---|---|---|---|---|---|
| A1, input coupling | 0 | **holds** | lasers.txt:5 `avatar > ShootAvatar stype=boulder rotateInPlace=true img=oryx/archer1` (avatar type avatar is ShootAvatar) | [ ] | [ ] |  |
| A1, input coupling | 1 | **holds** | lasers.txt:5 `avatar > ShootAvatar stype=boulder rotateInPlace=true img=oryx/archer1` (avatar type avatar is ShootAvatar) | [ ] | [ ] |  |
| A2, one controlled object | 0 | **fails** | lasers.txt:5 `avatar > ShootAvatar stype=boulder rotateInPlace=true img=oryx/archer1` (avatar type avatar is ShootAvatar: its use action creates a sprite)<br>lasers.txt:37 `box avatar  > bounceForward` (bounceForward moves box when the avatar moves into it) | [ ] | [ ] |  |
| A2, one controlled object | 1 | **fails** | lasers.txt:5 `avatar > ShootAvatar stype=boulder rotateInPlace=true img=oryx/archer1` (avatar type avatar is ShootAvatar: its use action creates a sprite)<br>lasers.txt:37 `box avatar  > bounceForward` (bounceForward moves box when the avatar moves into it) | [ ] | [ ] |  |
| A3, lattice motion | 0 | **fails** | lasers.txt:5 `avatar > ShootAvatar stype=boulder rotateInPlace=true img=oryx/archer1` (avatar is ShootAvatar, which turns in place when pressed in a new direction) | [ ] | [ ] |  |
| A3, lattice motion | 1 | **fails** | lasers.txt:5 `avatar > ShootAvatar stype=boulder rotateInPlace=true img=oryx/archer1` (avatar is ShootAvatar, which turns in place when pressed in a new direction) | [ ] | [ ] |  |
| A4, a fixed set of blockers | 0 | **holds** | lasers.txt:34 `avatar wall lasercannon > stepBack` (lcdown blocks the avatar)<br>lasers.txt:34 `avatar wall lasercannon > stepBack` (lcleft blocks the avatar)<br>lasers.txt:34 `avatar wall lasercannon > stepBack` (lcright blocks the avatar)<br>lasers.txt:34 `avatar wall lasercannon > stepBack` (lcswap blocks the avatar)<br>lasers.txt:34 `avatar wall lasercannon > stepBack` (lcup blocks the avatar)<br>lasers.txt:34 `avatar wall lasercannon > stepBack` (wall blocks the avatar)<br>lasers.txt:9 `lcdown > img=newset/lasercannon_2 stype=ldown` (blocker lcdown is SpawnPoint)<br>lasers.txt:11 `lcleft > img=newset/lasercannon_3 stype=lleft` (blocker lcleft is SpawnPoint)<br>lasers.txt:10 `lcright > img=newset/lasercannon_1 stype=lright` (blocker lcright is SpawnPoint)<br>lasers.txt:12 `lcswap > img=newset/lasercannon_4 stype=lleft` (blocker lcswap is SpawnPoint)<br>lasers.txt:8 `lcup > img=newset/lasercannon stype=lup` (blocker lcup is SpawnPoint)<br>lasers.txt:20 `wall > Immovable img=oryx/wall3 autotiling=True` (blocker wall is Immovable) | [ ] | [ ] |  |
| A4, a fixed set of blockers | 1 | **holds** | lasers.txt:34 `avatar wall lasercannon > stepBack` (lcdown blocks the avatar)<br>lasers.txt:34 `avatar wall lasercannon > stepBack` (lcleft blocks the avatar)<br>lasers.txt:34 `avatar wall lasercannon > stepBack` (lcright blocks the avatar)<br>lasers.txt:34 `avatar wall lasercannon > stepBack` (lcswap blocks the avatar)<br>lasers.txt:34 `avatar wall lasercannon > stepBack` (lcup blocks the avatar)<br>lasers.txt:34 `avatar wall lasercannon > stepBack` (wall blocks the avatar)<br>lasers.txt:9 `lcdown > img=newset/lasercannon_2 stype=ldown` (blocker lcdown is SpawnPoint)<br>lasers.txt:11 `lcleft > img=newset/lasercannon_3 stype=lleft` (blocker lcleft is SpawnPoint)<br>lasers.txt:10 `lcright > img=newset/lasercannon_1 stype=lright` (blocker lcright is SpawnPoint)<br>lasers.txt:12 `lcswap > img=newset/lasercannon_4 stype=lleft` (blocker lcswap is SpawnPoint)<br>lasers.txt:8 `lcup > img=newset/lasercannon stype=lup` (blocker lcup is SpawnPoint)<br>lasers.txt:20 `wall > Immovable img=oryx/wall3 autotiling=True` (blocker wall is Immovable) | [ ] | [ ] |  |
| A5, a place goal | 0 | **holds** | lasers.txt:58 `SpriteCounter stype=goal    limit=0 win=True` (a winning termination)<br>lasers_lvl0.txt:5 `w.b.......d..................gw` (the level places 1 sprite(s) of goal)<br>lasers.txt:47 `goal avatar > killSprite scoreChange=5` (the avatar removes the goal) | [ ] | [ ] |  |
| A5, a place goal | 1 | **holds** | lasers.txt:58 `SpriteCounter stype=goal    limit=0 win=True` (a winning termination)<br>lasers_lvl1.txt:10 `w.........ww..........w..g.w` (the level places 1 sprite(s) of goal)<br>lasers.txt:47 `goal avatar > killSprite scoreChange=5` (the avatar removes the goal) | [ ] | [ ] |  |

## painter

Description: `third_party/gvgai/examples/gridphysics/painter.txt`. Levels checked: 0 (`third_party/gvgai/examples/gridphysics/painter_lvl0.txt`) and 3 (`third_party/gvgai/examples/gridphysics/painter_lvl3.txt`).

| predicate | level | generator's verdict | the clauses it rests on (file:line, text, what was read) | agree | disagree | note |
|---|---|---|---|---|---|---|
| A1, input coupling | 0 | **holds** | painter.txt:15 `avatar > MovingAvatar shrinkfactor=0.8 img=newset/painter21` (avatar type avatar is MovingAvatar) | [ ] | [ ] |  |
| A1, input coupling | 3 | **holds** | painter.txt:15 `avatar > MovingAvatar shrinkfactor=0.8 img=newset/painter21` (avatar type avatar is MovingAvatar) | [ ] | [ ] |  |
| A2, one controlled object | 0 | **fails** | painter.txt:29 `ground avatar > spawn stype=prepaint` (spawn creates prepaint, a sprite other than the avatar, in an interaction with the avatar)<br>painter.txt:35 `paint avatar > spawn stype=preground` (spawn creates preground, a sprite other than the avatar, in an interaction with the avatar) | [ ] | [ ] |  |
| A2, one controlled object | 3 | **fails** | painter.txt:29 `ground avatar > spawn stype=prepaint` (spawn creates prepaint, a sprite other than the avatar, in an interaction with the avatar)<br>painter.txt:35 `paint avatar > spawn stype=preground` (spawn creates preground, a sprite other than the avatar, in an interaction with the avatar) | [ ] | [ ] |  |
| A3, lattice motion | 0 | **holds** | painter.txt:15 `avatar > MovingAvatar shrinkfactor=0.8 img=newset/painter21` (avatar is MovingAvatar at speed 1)<br>painter.txt:25 `InteractionSet` (no interaction moves the avatar) | [ ] | [ ] |  |
| A3, lattice motion | 3 | **holds** | painter.txt:15 `avatar > MovingAvatar shrinkfactor=0.8 img=newset/painter21` (avatar is MovingAvatar at speed 1)<br>painter.txt:25 `InteractionSet` (no interaction moves the avatar) | [ ] | [ ] |  |
| A4, a fixed set of blockers | 0 | **holds** | painter.txt:25 `InteractionSet` (no sprite blocks the avatar (no stepBack or undoAll with the avatar first, except at the edge)) | [ ] | [ ] |  |
| A4, a fixed set of blockers | 3 | **holds** | painter.txt:25 `InteractionSet` (no sprite blocks the avatar (no stepBack or undoAll with the avatar first, except at the edge)) | [ ] | [ ] |  |
| A5, a place goal | 0 | **fails** | painter.txt:41 `SpriteCounter stype=ground limit=0 win=True` (a winning termination)<br>painter_lvl0.txt:1 `A...` (the level places 10 sprite(s) of ground) | [ ] | [ ] |  |
| A5, a place goal | 3 | **fails** | painter.txt:41 `SpriteCounter stype=ground limit=0 win=True` (a winning termination)<br>painter_lvl3.txt:1 `A...w.` (the level places 17 sprite(s) of ground) | [ ] | [ ] |  |

## racebet

Description: `third_party/gvgai/examples/gridphysics/racebet.txt`. Levels checked: 0 (`third_party/gvgai/examples/gridphysics/racebet_lvl0.txt`) and 4 (`third_party/gvgai/examples/gridphysics/racebet_lvl4.txt`).

| predicate | level | generator's verdict | the clauses it rests on (file:line, text, what was read) | agree | disagree | note |
|---|---|---|---|---|---|---|
| A1, input coupling | 0 | **holds** | racebet.txt:26 `normal >` (avatar type normal is MovingAvatar) | [ ] | [ ] |  |
| A1, input coupling | 4 | **holds** | racebet.txt:26 `normal >` (avatar type normal is MovingAvatar) | [ ] | [ ] |  |
| A2, one controlled object | 0 | **holds** | racebet.txt:26 `normal >` (the one avatar sprite at start is normal, MovingAvatar, which creates nothing)<br>racebet.txt:35 `InteractionSet` (no bounceForward or pullWithIt with the avatar as partner, and no interaction with the avatar that creates another sprite) | [ ] | [ ] |  |
| A2, one controlled object | 4 | **holds** | racebet.txt:26 `normal >` (the one avatar sprite at start is normal, MovingAvatar, which creates nothing)<br>racebet.txt:35 `InteractionSet` (no bounceForward or pullWithIt with the avatar as partner, and no interaction with the avatar that creates another sprite) | [ ] | [ ] |  |
| A3, lattice motion | 0 | **holds** | racebet.txt:27 `betA >` (betA is MovingAvatar at speed 1)<br>racebet.txt:28 `betB >` (betB is MovingAvatar at speed 1)<br>racebet.txt:29 `betC >` (betC is MovingAvatar at speed 1)<br>racebet.txt:30 `betD >` (betD is MovingAvatar at speed 1)<br>racebet.txt:26 `normal >` (normal is MovingAvatar at speed 1)<br>racebet.txt:35 `InteractionSet` (no interaction moves the avatar) | [ ] | [ ] |  |
| A3, lattice motion | 4 | **holds** | racebet.txt:27 `betA >` (betA is MovingAvatar at speed 1)<br>racebet.txt:28 `betB >` (betB is MovingAvatar at speed 1)<br>racebet.txt:29 `betC >` (betC is MovingAvatar at speed 1)<br>racebet.txt:30 `betD >` (betD is MovingAvatar at speed 1)<br>racebet.txt:26 `normal >` (normal is MovingAvatar at speed 1)<br>racebet.txt:35 `InteractionSet` (no interaction moves the avatar) | [ ] | [ ] |  |
| A4, a fixed set of blockers | 0 | **holds** | racebet.txt:48 `avatar wall > stepBack` (wall blocks the avatar)<br>racebet.txt:33 `wall > Immovable img=oryx/space5` (blocker wall is Immovable) | [ ] | [ ] |  |
| A4, a fixed set of blockers | 4 | **holds** | racebet.txt:48 `avatar wall > stepBack` (wall blocks the avatar)<br>racebet.txt:33 `wall > Immovable img=oryx/space5` (blocker wall is Immovable) | [ ] | [ ] |  |
| A5, a place goal | 0 | **fails** | racebet.txt:68 `MultiSpriteCounter stype1=winA stype2=betA limit=2 win=True` (a winning termination)<br>racebet.txt:69 `MultiSpriteCounter stype1=winB stype2=betB limit=2 win=True` (a winning termination)<br>racebet.txt:70 `MultiSpriteCounter stype1=winC stype2=betC limit=2 win=True` (a winning termination)<br>racebet.txt:71 `MultiSpriteCounter stype1=winD stype2=betD limit=2 win=True` (a winning termination) | [ ] | [ ] |  |
| A5, a place goal | 4 | **fails** | racebet.txt:68 `MultiSpriteCounter stype1=winA stype2=betA limit=2 win=True` (a winning termination)<br>racebet.txt:69 `MultiSpriteCounter stype1=winB stype2=betB limit=2 win=True` (a winning termination)<br>racebet.txt:70 `MultiSpriteCounter stype1=winC stype2=betC limit=2 win=True` (a winning termination)<br>racebet.txt:71 `MultiSpriteCounter stype1=winD stype2=betD limit=2 win=True` (a winning termination) | [ ] | [ ] |  |

## rivers

Description: `third_party/gvgai/examples/gridphysics/rivers.txt`. Levels checked: 0 (`third_party/gvgai/examples/gridphysics/rivers_lvl0.txt`) and 4 (`third_party/gvgai/examples/gridphysics/rivers_lvl4.txt`).

| predicate | level | generator's verdict | the clauses it rests on (file:line, text, what was read) | agree | disagree | note |
|---|---|---|---|---|---|---|
| A1, input coupling | 0 | **holds** | rivers.txt:5 `avatar  > ShootAvatar stype=shovel img=newset/man1` (avatar type avatar is ShootAvatar) | [ ] | [ ] |  |
| A1, input coupling | 4 | **holds** | rivers.txt:5 `avatar  > ShootAvatar stype=shovel img=newset/man1` (avatar type avatar is ShootAvatar) | [ ] | [ ] |  |
| A2, one controlled object | 0 | **fails** | rivers.txt:5 `avatar  > ShootAvatar stype=shovel img=newset/man1` (avatar type avatar is ShootAvatar: its use action creates a sprite) | [ ] | [ ] |  |
| A2, one controlled object | 4 | **fails** | rivers.txt:5 `avatar  > ShootAvatar stype=shovel img=newset/man1` (avatar type avatar is ShootAvatar: its use action creates a sprite) | [ ] | [ ] |  |
| A3, lattice motion | 0 | **fails** | rivers.txt:5 `avatar  > ShootAvatar stype=shovel img=newset/man1` (avatar is ShootAvatar, which turns in place when pressed in a new direction) | [ ] | [ ] |  |
| A3, lattice motion | 4 | **fails** | rivers.txt:5 `avatar  > ShootAvatar stype=shovel img=newset/man1` (avatar is ShootAvatar, which turns in place when pressed in a new direction) | [ ] | [ ] |  |
| A4, a fixed set of blockers | 0 | **fails** | rivers.txt:39 `dryHouse water > transformTo stype=waterHouse scoreChange=1` (transformTo removes blocker dryHouse without the avatar)<br>rivers.txt:39 `dryHouse water > transformTo stype=waterHouse scoreChange=1` (transformTo creates blocker waterHouse without the avatar) | [ ] | [ ] |  |
| A4, a fixed set of blockers | 4 | **fails** | rivers.txt:39 `dryHouse water > transformTo stype=waterHouse scoreChange=1` (transformTo removes blocker dryHouse without the avatar)<br>rivers.txt:39 `dryHouse water > transformTo stype=waterHouse scoreChange=1` (transformTo creates blocker waterHouse without the avatar) | [ ] | [ ] |  |
| A5, a place goal | 0 | **fails** | rivers.txt:45 `SpriteCounter stype=dryHouse limit=0 win=True` (a winning termination)<br>rivers_lvl0.txt:3 `w.........r......h.w` (the level places 6 sprite(s) of dryHouse) | [ ] | [ ] |  |
| A5, a place goal | 4 | **fails** | rivers.txt:45 `SpriteCounter stype=dryHouse limit=0 win=True` (a winning termination)<br>rivers_lvl4.txt:3 `w............h.....w` (the level places 6 sprite(s) of dryHouse) | [ ] | [ ] |  |

## sokoban

Description: `third_party/gvgai/examples/gridphysics/sokoban.txt`. Levels checked: 0 (`third_party/gvgai/examples/gridphysics/sokoban_lvl0.txt`) and 1 (`third_party/gvgai/examples/gridphysics/sokoban_lvl1.txt`).

| predicate | level | generator's verdict | the clauses it rests on (file:line, text, what was read) | agree | disagree | note |
|---|---|---|---|---|---|---|
| A1, input coupling | 0 | **holds** | sokoban.txt:5 `avatar > MovingAvatar img=oryx/knight1` (avatar type avatar is MovingAvatar) | [ ] | [ ] |  |
| A1, input coupling | 1 | **holds** | sokoban.txt:5 `avatar > MovingAvatar img=oryx/knight1` (avatar type avatar is MovingAvatar) | [ ] | [ ] |  |
| A2, one controlled object | 0 | **fails** | sokoban.txt:16 `box avatar  > bounceForward` (bounceForward moves box when the avatar moves into it) | [ ] | [ ] |  |
| A2, one controlled object | 1 | **fails** | sokoban.txt:16 `box avatar  > bounceForward` (bounceForward moves box when the avatar moves into it) | [ ] | [ ] |  |
| A3, lattice motion | 0 | **holds** | sokoban.txt:5 `avatar > MovingAvatar img=oryx/knight1` (avatar is MovingAvatar at speed 1)<br>sokoban.txt:14 `InteractionSet` (no interaction moves the avatar) | [ ] | [ ] |  |
| A3, lattice motion | 1 | **holds** | sokoban.txt:5 `avatar > MovingAvatar img=oryx/knight1` (avatar is MovingAvatar at speed 1)<br>sokoban.txt:14 `InteractionSet` (no interaction moves the avatar) | [ ] | [ ] |  |
| A4, a fixed set of blockers | 0 | **holds** | sokoban.txt:15 `avatar wall > stepBack` (wall blocks the avatar)<br>sokoban.txt:7 `wall > Immovable img=oryx/wall3 autotiling=True` (blocker wall is Immovable) | [ ] | [ ] |  |
| A4, a fixed set of blockers | 1 | **holds** | sokoban.txt:15 `avatar wall > stepBack` (wall blocks the avatar)<br>sokoban.txt:7 `wall > Immovable img=oryx/wall3 autotiling=True` (blocker wall is Immovable) | [ ] | [ ] |  |
| A5, a place goal | 0 | **fails** | sokoban.txt:20 `SpriteCounter stype=box    limit=0 win=True` (a winning termination)<br>sokoban_lvl0.txt:3 `w...1.......w` (the level places 4 sprite(s) of box) | [ ] | [ ] |  |
| A5, a place goal | 1 | **fails** | sokoban.txt:20 `SpriteCounter stype=box    limit=0 win=True` (a winning termination)<br>sokoban_lvl1.txt:3 `wwww1......ww` (the level places 3 sprite(s) of box) | [ ] | [ ] |  |

## wrapsokoban

Description: `third_party/gvgai/examples/gridphysics/wrapsokoban.txt`. Levels checked: 0 (`third_party/gvgai/examples/gridphysics/wrapsokoban_lvl0.txt`) and 1 (`third_party/gvgai/examples/gridphysics/wrapsokoban_lvl1.txt`).

| predicate | level | generator's verdict | the clauses it rests on (file:line, text, what was read) | agree | disagree | note |
|---|---|---|---|---|---|---|
| A1, input coupling | 0 | **holds** | wrapsokoban.txt:7 `avatar > OrientedAvatar rotateInPlace=False img=oryx/knight1` (avatar type avatar is OrientedAvatar) | [ ] | [ ] |  |
| A1, input coupling | 1 | **holds** | wrapsokoban.txt:7 `avatar > OrientedAvatar rotateInPlace=False img=oryx/knight1` (avatar type avatar is OrientedAvatar) | [ ] | [ ] |  |
| A2, one controlled object | 0 | **fails** | wrapsokoban.txt:22 `bbox avatar  > bounceForward` (bounceForward moves bbox when the avatar moves into it) | [ ] | [ ] |  |
| A2, one controlled object | 1 | **fails** | wrapsokoban.txt:22 `bbox avatar  > bounceForward` (bounceForward moves bbox when the avatar moves into it) | [ ] | [ ] |  |
| A3, lattice motion | 0 | **fails** | wrapsokoban.txt:21 `avatar EOS > wrapAround` (wrapAround moves the avatar) | [ ] | [ ] |  |
| A3, lattice motion | 1 | **fails** | wrapsokoban.txt:21 `avatar EOS > wrapAround` (wrapAround moves the avatar) | [ ] | [ ] |  |
| A4, a fixed set of blockers | 0 | **holds** | wrapsokoban.txt:24 `avatar wall > stepBack` (wall blocks the avatar)<br>wrapsokoban.txt:11 `wall > Immovable img=oryx/wall3 autotiling=True` (blocker wall is Immovable) | [ ] | [ ] |  |
| A4, a fixed set of blockers | 1 | **holds** | wrapsokoban.txt:24 `avatar wall > stepBack` (wall blocks the avatar)<br>wrapsokoban.txt:11 `wall > Immovable img=oryx/wall3 autotiling=True` (blocker wall is Immovable) | [ ] | [ ] |  |
| A5, a place goal | 0 | **fails** | wrapsokoban.txt:30 `SpriteCounter stype=box    limit=0 win=True` (a winning termination)<br>wrapsokoban_lvl0.txt:3 `.w.o*.w.` (the level places 4 sprite(s) of box) | [ ] | [ ] |  |
| A5, a place goal | 1 | **fails** | wrapsokoban.txt:30 `SpriteCounter stype=box    limit=0 win=True` (a winning termination)<br>wrapsokoban_lvl1.txt:1 `.........*.` (the level places 3 sprite(s) of box) | [ ] | [ ] |  |
