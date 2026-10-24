# A guide to the hand check

For the author, before the hand check of the truth tables (docs/PREREG.md draft v0, Section 5). It explains how to read a GVGAI game file and what each of A1 to A5 asks, so that each verdict of scripts/truth_vgdl.py can be judged against the file itself. The tool scripts/handcheck_app.py shows the question of each predicate from this guide. Every count quoted below is read from docs/truth/gvgai.json (logs/truth_vgdl.log). Nothing here is a result.

## How a game is written

A game has two kinds of file under third_party/gvgai/examples/gridphysics: one **description** (for instance sokoban.txt) and five **level files** (sokoban_lvl0.txt to sokoban_lvl4.txt).

The description has four blocks, each started by a line with its name. Indentation shows what belongs to what.

- **SpriteSet**: the kinds of object in the game, called sprites. A line reads `name > Class options`. The class says how the sprite behaves: `Immovable` never moves, `Passive` moves only when pushed, `Missile` flies on by itself, `MovingAvatar` is the player's character. A line indented under another is a sub-kind and takes its parent's class and options unless it gives its own: in colourescape.txt, line 19 is `avatar > MovingAvatar` and line 20, `normalAvatar > img=newset/girl3`, is therefore a MovingAvatar too. Options such as `img=` only choose a picture; `speed=`, `stype=` and `rotateInPlace=` change behaviour.
- **LevelMapping**: which character in a level file stands for which sprites. `A > avatar floor` means that an A in a level puts an avatar on a floor tile.
- **InteractionSet**: what happens when two sprites meet. A line reads `first second > effect`: when a sprite of the first kind touches one of the second kind, the effect happens to the first. `avatar wall > stepBack` sends the avatar back to where it was, so walls block it. `box avatar > bounceForward` pushes the box one square on when the avatar walks into it. A line with more names, `first a b c > effect`, means the same effect with each of a, b and c. `EOS` stands for the edge of the screen. `undoAll` cancels every move of that step, the avatar's included.
- **TerminationSet**: how the game ends. `win=True` marks a way to win, `win=False` a way to lose. `SpriteCounter stype=box limit=0 win=True` means the player wins when no box is left. Where `limit` is not given, the generator reads it as 0.

A **level file** is a grid of characters, one per square, each read through the LevelMapping. Line 1 of the file is the top row of the screen.

The line numbers the generator quotes count every line of the file from 1, blank lines included.

## A1. Input coupling

**Question.** Does the player's character, as placed in the level at the start, answer to at least two different keys?

**The words that decide it.** The class of the avatar sprite that the level places (through the LevelMapping), read from its SpriteSet line or the parent it sits under. Every avatar class answers to at least two keys except `NullAvatar` and `MissileAvatar`, which do not respond to the keys.

**Example.** sokoban.txt, line 5: `avatar > MovingAvatar img=oryx/knight1`. A MovingAvatar steps up, down, left or right, one key for each, so A1 holds.

**Counter-example.** No grid-physics game fails A1 by its avatar's class at the start (logs/truth_vgdl.log). The class that would fail it appears in catapults.txt, line 12: `bullet > MissileAvatar img=oryx/bat1`. A MissileAvatar flies on by itself and the keys cannot steer it; if it were the avatar the level places, A1 would fail. In catapults the avatar at the start is line 11, `moving > MovingAvatar`, so A1 holds there.

## A2. One controlled object

**Question.** Is the avatar the only thing whose position the player's keys decide?

**The words that decide it.** It fails on any of three things: the level places more than one avatar, or none; an interaction pushes or pulls another sprite when the avatar walks into it (`bounceForward`, or `pullWithIt` with the avatar second); the avatar's use key creates a sprite (the classes `ShootAvatar`, `FlakAvatar`, `ShootOnlyAvatar`, `AimedAvatar`, `OngoingShootAvatar`; the `stype=` option names what is created).

**Example.** painter.txt, line 15: `avatar > MovingAvatar shrinkfactor=0.8 img=newset/painter21`, with no `bounceForward` or `pullWithIt` in the InteractionSet (line 25 on) and one A in the level. Only the avatar moves when a key is pressed, so A2 holds.

**Counter-example.** sokoban.txt, line 16: `box avatar  > bounceForward`. When the avatar walks into a box the box moves as well, so the keys move a second sprite and A2 fails.

## A3. Lattice motion

**Question.** Does each arrow key, when the avatar is not blocked, always move it exactly one square in the same direction, wherever it is and whichever way it faces?

**The words that decide it.** The avatar's class and options: `MovingAvatar`, `HorizontalAvatar`, `VerticalAvatar` and `FlakAvatar` are fine at speed 1; `OrientedAvatar` and `ShootAvatar` are fine only with `rotateInPlace=False`, because by default they first turn on the spot when a new direction is pressed. A `speed=` other than 1 fails it. So does any interaction with the avatar first that carries it: `teleportToExit`, `wrapAround`, `pullWithIt`, `bounceForward`, `windGust`, `slipForward`, `conveySprite`, `attractGaze`.

**Example.** sokoban.txt, line 5: `avatar > MovingAvatar img=oryx/knight1`. No speed is given, so it is 1, and the InteractionSet (line 14 on) has no line that carries the avatar. A3 holds.

**Counter-example.** wrapsokoban.txt, line 21: `avatar EOS > wrapAround`. When the avatar steps off the edge it appears on the other side of the screen, so that step does not move it by one square. A3 fails.

## A4. A fixed set of blockers

**Question.** Is every step that the avatar cannot take stopped by a sprite that never moves on its own and that only the player's own actions can create, remove or move?

**The words that decide it.** The lines that stop the avatar: `stepBack` or `undoAll` with the avatar first, for instance `avatar wall > stepBack`. The class of each sprite named there must be one that never moves on its own: `Immovable`, `Passive`, `Door`, `Resource`, `ResourcePack`, `SpawnPoint`, `SpawnPointMultiSprite`, `Portal`, `SpriteProducer`. Then every line that creates, removes, moves or changes such a sprite (`transformTo`, `killSprite`, `spawn` and the like) must name only sprites driven by the avatar: the avatar itself, what its use key creates, and things only those push. A sprite that kills on contact does not block.

**Example.** sokoban.txt, line 15: `avatar wall > stepBack`, and line 7: `wall > Immovable img=oryx/wall3 autotiling=True`. Walls stop the avatar, never move, and no line changes them. A4 holds.

**Counter-example.** rivers.txt, line 39: `dryHouse water > transformTo stype=waterHouse scoreChange=1`. Houses stop the avatar (line 32), and here water, which is not the avatar, turns a dry house into a wet one. A blocker is changed without the player's own step, so A4 fails.

## A5. A place goal

**Question.** Is the only way to win to reach one single goal object that only the avatar can remove?

**The words that decide it.** The `win=True` lines of the TerminationSet: there must be exactly one, and it must be a `SpriteCounter` with limit 0 on one kind of sprite. The level must place exactly one sprite of that kind (count its character in the level file through the LevelMapping). Every interaction that removes it must have the avatar second, as in `exit avatar > killSprite`.

**Example.** labyrinthdual.txt, line 38: `SpriteCounter stype=exit limit=0 win=True`, the only winning line; level 0 places one exit (the x in labyrinthdual_lvl0.txt, line 2); line 33, `exit avatar > killSprite scoreChange=1`, is the only line that removes it. A5 holds.

**Counter-example.** sokoban.txt, line 20: `SpriteCounter stype=box    limit=0 win=True`. The player wins when every box is gone, and level 0 places 4 boxes, so there is no single goal object. A5 fails.

## Marking a row

Each row of the tool is one predicate on one level of one game. Agree if the verdict follows from the file by the question above; disagree if it does not; unsure if the files alone do not settle it. A note helps most where a row is marked disagree or unsure. Rows are not resolved by the tool: every disagreement is settled afterwards from the GVGAI source, as Section 5 of docs/PREREG.md draft v0 says.
