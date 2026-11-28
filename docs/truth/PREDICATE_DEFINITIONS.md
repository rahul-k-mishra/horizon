# Definitions of A1 to A5, for the blind hand check

The registered wording of A1 to A5, copied from docs/PREREG.md, Section 5, and, for A4, the wording of Section 1 on A4's first clause, which Section 5 refers to and does not repeat. Sentences and parts of sentences that give a reason, an example's source, a count or a reference to another file are left out, and each place where something was left out is marked [...]; where a sentence names a game, the name is replaced by [a game]. Nothing else in the definitions is changed. Each question above a definition is written from that definition for the window of the hand check; it is not registered wording and adds nothing to it. During the blind pass this is the only definition text the author reads (docs/PREREG.md, Section 5).

## A1

Question: Is the avatar present at the start of this level of a class that responds to at least two actions?

A1 holds iff the avatar present at level start is of a class that responds to at least two actions: every class except NullAvatar and MissileAvatar. Fails if no avatar is present.

## A2

Question: Is the avatar's the only displacement that is a function of the action, with no other sprite moved because the avatar moved into it and no sprite other than an avatar created by an action?

A2 holds iff exactly one sprite's displacement is a function of the action, the avatar. It fails if the level does not place exactly one avatar sprite at start; if an interaction moves another sprite because the avatar moved into it (bounceForward, pullWithIt with the avatar as partner); and if the avatar's use action creates a sprite (ShootAvatar, FlakAvatar, ShootOnlyAvatar, AimedAvatar, OngoingShootAvatar) [...] A2 also fails wherever an action creates a sprite other than the avatar: an interaction that names an avatar type, in any position, and creates a sprite of a non-avatar type (a spawn effect, cloneSprite, or a transform into a non-avatar type); a transform of the avatar into another avatar type creates no other sprite. [...]

## A3

Question: Does each movement action, when not blocked, shift the avatar by one constant vector whatever its position, facing and history?

A3 holds iff each movement action, when not blocked, shifts the avatar by one constant vector whatever its position, facing and history: MovingAvatar, HorizontalAvatar, VerticalAvatar and FlakAvatar at speed 1; OrientedAvatar and ShootAvatar only with rotateInPlace=False. It fails for every other avatar class, for a speed other than 1, and where an interaction moves the avatar (teleportToExit, wrapAround, pullWithIt, bounceForward, windGust, slipForward, conveySprite, attractGaze).

## A4

Question: Is every move of the avatar without effect explained by a blocking sprite of a class that never moves on its own, and are the blocking sprites created, removed or moved only through the avatar's own actions?

A4 holds iff every move without effect is explained by a sprite that blocks the avatar (stepBack or undoAll with the avatar), every blocking type is of a class that never moves on its own (Immovable, Passive, Door, Resource, ResourcePack, SpawnPoint, SpawnPointMultiSprite, Portal, SpriteProducer), and blocking sprites are created, removed or moved only through the avatar's own actions: by interactions whose names include only agent-driven sprites, which are the avatar, the sprites its use action creates, and stationary-class sprites that only those push or pull. A sprite that kills on contact does not block. [...] "With the avatar" is applied with the avatar named first. A blocker transformed into another blocking type in place counts as created and removed [...] A blocking relation that depends on the avatar's subtype holds A4, because the set of obstacles does not change during play. [...] The generator counts a name as standing for agent-driven sprites when every type it can place is agent-driven [...] The first clause is checked through every undoAll line that cancels the avatar's move, and a chain push or an edge wrap of a pushed box counts as the avatar's own [...]

From Section 1: The generator checks A4's first clause, that every move the avatar makes without effect is explained by a sprite that blocks it. An undoAll line puts every sprite back whichever sprite is named first [...], so a line without the avatar first also cancels the avatar's move. Every sprite such a line names must be agent-driven or pass the same tests as a blocker; otherwise A4 fails. The agent-driven set is the largest set consistent with itself: a crate pushed along by another crate the avatar pushed counts ([a game]), and a move whose only partner is the edge of the level, as a pushed box wrapping round, does not count against a sprite ([a game]). [...] What remains a limit: only stepBack and undoAll are treated as ways of cancelling a move. [...]

## A5

Question: Is the only winning condition a SpriteCounter with limit 0 on one sprite type, of which the level holds exactly one sprite, removed only by interactions with the avatar or an avatar subtype as partner?

A5 holds iff the only winning condition is a SpriteCounter with limit 0 on one sprite type, the level holds exactly one sprite of that type, and every interaction that removes it has the avatar or an avatar subtype as partner; a precondition met elsewhere is recorded and keeps A5 holding.
