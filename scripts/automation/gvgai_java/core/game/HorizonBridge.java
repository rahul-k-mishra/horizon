package core.game;

import java.io.ByteArrayOutputStream;
import java.io.DataOutputStream;
import java.io.IOException;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Map;

import core.competition.CompetitionParameters;
import core.vgdl.SpriteGroup;
import core.vgdl.VGDLFactory;
import core.vgdl.VGDLParser;
import core.vgdl.VGDLRegistry;
import core.vgdl.VGDLSprite;
import ontology.Types;

/**
 * HORIZON's bridge to the GVGAI forward model (docs/DESIGN.md, Sections 5 and 6).  It adds no rule of its
 * own: every transition is StateObservation.advance of GVGAI at commit e58ff659, run on a copy.
 *
 * It sits in the package core.game only to read the sprite groups of the forward model, which GVGAI keeps
 * protected.  It changes no GVGAI field.
 *
 *   load        parses a description and builds a level, as GVGAI's ArcadeMachine does, and returns the
 *               level start as a StateObservation.
 *   key         the canonical serialization of a state (docs/PREREG.md, Section 6): for every sprite its
 *               type, position, orientation and resources, the avatar's health points, and the game tick
 *               only when withTick is set.  Sprites of one type are sorted, so the order in which GVGAI
 *               created them does not enter the key.
 *   status      0 running, 1 win, 2 loss by a termination, 3 loss by GVGAI's own limit of game ticks.
 *   Expander    the search's successor function: a frontier entry is the action sequence from the level
 *               start; consecutive entries share prefixes, so a stack of copies along the last sequence
 *               replays a new one only from the nearest shared ancestor.
 *   frame       the grid of visible sprite types per cell, for the frame contract.
 */
public class HorizonBridge {

    /** Sprite images are not needed by any rule; pointing GVGAI at an empty folder keeps it from reading
     *  PNG files whenever a sprite is created.  The images are used only for drawing. */
    public static void noImages(String emptyDir) {
        CompetitionParameters.IMG_PATH = emptyDir;
    }

    public static StateObservation load(String gameFile, String levelFile, int seed) {
        VGDLFactory.GetInstance().init();
        VGDLRegistry.GetInstance().init();
        Game game = new VGDLParser().parseGame(gameFile);
        game.buildLevel(levelFile, seed);
        return game.getObservation();
    }

    public static int status(StateObservation so) {
        if (!so.isGameOver()) return 0;
        Types.WINNER w = so.getGameWinner();
        if (w == Types.WINNER.PLAYER_WINS) return 1;
        ForwardModel m = so.model;
        if (m.gameTick >= CompetitionParameters.MAX_TIMESTEPS) {
            // checkTimeOut ended it; a termination met on the same tick still counts as a loss by termination
            boolean byTermination = false;
            for (core.termination.Termination t : m.terminations) {
                if (t.isDone(m)) { byTermination = true; break; }
            }
            return byTermination ? 2 : 3;
        }
        return 2;
    }

    public static Types.ACTIONS[] actions(StateObservation so) {
        ArrayList<Types.ACTIONS> a = so.getAvailableActions(false);
        return a.toArray(new Types.ACTIONS[0]);
    }

    public static String[] actionNames(StateObservation so) {
        Types.ACTIONS[] a = actions(so);
        String[] out = new String[a.length];
        for (int i = 0; i < a.length; i++) out[i] = a[i].toString();
        return out;
    }

    // ------------------------------------------------------------------ the state key
    /** Key forms.  REGISTERED is docs/PREREG.md, Section 6.  EXTENDED adds, per sprite, the counters GVGAI keeps
     *  that change over time and decide later transitions: the age of a Flicker (and of OrientedFlicker and
     *  Spreader, its subclasses), the counter and first tick of a SpawnPoint, the health points of every sprite,
     *  and the ticks since the last move of a sprite whose cooldown exceeds 1.  It is offered for the author's
     *  decision (docs/design/ENGINE.md, Section 3) and is not the registered key. */
    public static final int REGISTERED = 0, EXTENDED = 1;

    private static long[] spriteRecord(VGDLSprite sp, boolean isAvatar, int form) {
        Map<Integer, Integer> res = sp.resources;
        int extra = form == EXTENDED ? 6 : 0;
        int n = 6 + 2 * (res == null ? 0 : res.size()) + (isAvatar ? 1 : 0) + extra;
        long[] r = new long[n];
        int k = 0;
        r[k++] = sp.rect.x;
        r[k++] = sp.rect.y;
        r[k++] = Double.doubleToLongBits(sp.orientation.x() + 0.0);
        r[k++] = Double.doubleToLongBits(sp.orientation.y() + 0.0);
        r[k++] = isAvatar ? sp.healthPoints : 0;
        r[k++] = res == null ? 0 : res.size();
        if (res != null) for (Map.Entry<Integer, Integer> e : res.entrySet()) {   // TreeMap: key order
            r[k++] = e.getKey();
            r[k++] = e.getValue();
        }
        if (isAvatar) r[k++] = 1;
        if (form == EXTENDED) {
            r[k++] = sp.healthPoints;
            r[k++] = sp instanceof ontology.sprites.Flicker ? ((ontology.sprites.Flicker) sp).age : -1;
            r[k++] = sp instanceof ontology.sprites.producer.SpawnPoint ? spawnCounter(sp) : -1;
            r[k++] = sp instanceof ontology.sprites.producer.SpawnPoint ? spawnStart(sp) : -1;
            r[k++] = sp.cooldown > 1 ? sp.lastmove : -1;
            r[k++] = sp.cooldown;
        }
        return r;
    }

    private static long spawnCounter(VGDLSprite sp) {
        return ((ontology.sprites.producer.SpawnPoint) sp).counter;
    }

    private static final java.lang.reflect.Field SPAWN_START;
    static {
        try {
            SPAWN_START = ontology.sprites.producer.SpawnPoint.class.getDeclaredField("start");
            SPAWN_START.setAccessible(true);
        } catch (ReflectiveOperationException e) {
            throw new RuntimeException(e);
        }
    }

    /** SpawnPoint.start is private; it is read, never written. */
    private static long spawnStart(VGDLSprite sp) {
        try {
            return SPAWN_START.getInt(sp);
        } catch (IllegalAccessException e) {
            throw new RuntimeException(e);
        }
    }

    private static int cmp(long[] a, long[] b) {
        int n = Math.min(a.length, b.length);
        for (int i = 0; i < n; i++) if (a[i] != b[i]) return a[i] < b[i] ? -1 : 1;
        return Integer.compare(a.length, b.length);
    }

    public static byte[] key(StateObservation so, boolean withTick) {
        return key(so, withTick, REGISTERED);
    }

    public static byte[] key(StateObservation so, boolean withTick, int form) {
        ForwardModel m = so.model;
        ByteArrayOutputStream bos = new ByteArrayOutputStream(1024);
        DataOutputStream out = new DataOutputStream(bos);
        try {
            out.writeInt(withTick ? m.gameTick : -1);
            SpriteGroup[] groups = m.spriteGroups;
            for (int t = 0; t < groups.length; t++) {
                if (groups[t] == null) continue;
                ArrayList<VGDLSprite> list = groups[t].getSprites();
                if (list == null || list.isEmpty()) continue;
                long[][] recs = new long[list.size()][];
                for (int i = 0; i < recs.length; i++) {
                    VGDLSprite sp = list.get(i);
                    recs[i] = spriteRecord(sp, sp.is_avatar, form);
                }
                Arrays.sort(recs, HorizonBridge::cmp);
                out.writeInt(t);
                out.writeInt(recs.length);
                for (long[] r : recs) {
                    out.writeInt(r.length);
                    for (long v : r) out.writeLong(v);
                }
            }
        } catch (IOException e) {
            throw new RuntimeException(e);
        }
        return bos.toByteArray();
    }

    // ------------------------------------------------------------------ the successor function
    public static class Expander {
        private final Types.ACTIONS[] acts;
        private final boolean withTick;
        private final int form;
        private final ArrayList<StateObservation> stack = new ArrayList<>();   // stack.get(i): after i actions
        private byte[] seq = new byte[0];
        public long advances = 0, copies = 0;

        public Expander(StateObservation root, boolean withTick) {
            this(root, withTick, REGISTERED);
        }

        public Expander(StateObservation root, boolean withTick, int form) {
            this.acts = actions(root);
            this.withTick = withTick;
            this.form = form;
            stack.add(root);
        }

        public int numActions() { return acts.length; }

        /** The state after the action sequence s (action indices into the action list), replayed from the
         *  nearest state on the stack. */
        public StateObservation reach(byte[] s) {
            int common = 0, lim = Math.min(s.length, seq.length);
            while (common < lim && s[common] == seq[common]) common++;
            while (stack.size() > common + 1) stack.remove(stack.size() - 1);
            for (int i = common; i < s.length; i++) {
                StateObservation c = stack.get(stack.size() - 1).copy();
                copies++;
                c.advance(acts[s[i]]);
                advances++;
                stack.add(c);
            }
            seq = s;
            return stack.get(stack.size() - 1);
        }

        /** Packs, for the state after s: its key, then for each action in order its successor's status and
         *  key.  Layout: int nActions; int len, bytes (parent key); then per action int status, int len, bytes. */
        public byte[] expand(byte[] s) {
            StateObservation p = reach(s);
            ByteArrayOutputStream bos = new ByteArrayOutputStream(4096);
            DataOutputStream out = new DataOutputStream(bos);
            try {
                byte[] pk = key(p, withTick, form);
                out.writeInt(acts.length);
                out.writeInt(pk.length);
                out.write(pk);
                for (int a = 0; a < acts.length; a++) {
                    StateObservation c = p.copy();
                    copies++;
                    c.advance(acts[a]);
                    advances++;
                    byte[] ck = key(c, withTick, form);
                    out.writeInt(status(c));
                    out.writeInt(ck.length);
                    out.write(ck);
                }
            } catch (IOException e) {
                throw new RuntimeException(e);
            }
            return bos.toByteArray();
        }
    }

    // ------------------------------------------------------------------ the frame contract
    /** For every cell, the sorted list of visible sprite types in it, as a flat int array:
     *  [width, height, then per cell (x fastest within a row): count, types...].  A sprite is visible
     *  unless its hidden or invisible flag is set; a sprite counts in the cell that holds its top-left
     *  corner. */
    public static int[] cellTypes(StateObservation so) {
        ForwardModel m = so.model;
        int bs = m.block_size;
        int w = m.screenSize.width / bs, h = m.screenSize.height / bs;
        ArrayList<Integer>[] cells = new ArrayList[w * h];
        SpriteGroup[] groups = m.spriteGroups;
        for (int t = 0; t < groups.length; t++) {
            if (groups[t] == null) continue;
            ArrayList<VGDLSprite> list = groups[t].getSprites();
            if (list == null) continue;
            for (VGDLSprite sp : list) {
                if (flag(sp.hidden) || flag(sp.invisible)) continue;
                int cx = Math.floorDiv(sp.rect.x, bs), cy = Math.floorDiv(sp.rect.y, bs);
                if (cx < 0 || cy < 0 || cx >= w || cy >= h) continue;
                int i = cy * w + cx;
                if (cells[i] == null) cells[i] = new ArrayList<>();
                if (!cells[i].contains(t)) cells[i].add(t);
            }
        }
        int total = 2;
        for (ArrayList<Integer> c : cells) total += 1 + (c == null ? 0 : c.size());
        int[] out = new int[total];
        out[0] = w; out[1] = h;
        int k = 2;
        for (ArrayList<Integer> c : cells) {
            if (c == null) { out[k++] = 0; continue; }
            java.util.Collections.sort(c);
            out[k++] = c.size();
            for (int t : c) out[k++] = t;
        }
        return out;
    }

    /** GVGAI keeps hidden and invisible as text, one value per player separated by commas; player 0's value
     *  is the first (VGDLSprite.draw for invisible; ForwardModel.java:155-163 reads hidden the same way for a
     *  single player). */
    static boolean flag(String v) {
        if (v == null) return false;
        return Boolean.parseBoolean(v.split(",")[0].trim());
    }

    /** Sprite type index to its name in the description. */
    public static String typeName(int itype) {
        return VGDLRegistry.GetInstance().getRegisteredSpriteKey(itype);
    }

    // ------------------------------------------------------------------ the game loop against the forward model
    /** A player for GVGAI's own game loop that plays a fixed action sequence and records, at every decision,
     *  the key of the state GVGAI hands it (Game.gameCycle updates that state before the avatar moves). */
    public static class Recorder extends core.player.AbstractPlayer {
        private final Types.ACTIONS[] seq;
        private final boolean withTick;
        private int i = 0;
        public final ArrayList<byte[]> keys = new ArrayList<>();
        public final ArrayList<Integer> ticks = new ArrayList<>();

        public Recorder(Types.ACTIONS[] seq, boolean withTick) {
            this.seq = seq;
            this.withTick = withTick;
        }

        @Override
        public Types.ACTIONS act(StateObservation so, tools.ElapsedCpuTimer t) {
            keys.add(key(so, withTick));
            ticks.add(so.getGameTick());
            // after the last action has been played, the state is recorded and the game is ended (MovingAvatar
            // aborts the game on ACTION_ESCAPE); nothing after that point is compared
            return i < seq.length ? seq[i++] : Types.ACTIONS.ACTION_ESCAPE;
        }
    }

    /** Keys of the states at every decision of GVGAI's own game loop (Game.runGame) playing seq (indices into
     *  the action list): before each action, and after the last.  If the game ends inside seq, the last key is
     *  that of the final state, which runGame hands to the forward model when the loop stops. */
    public static Object[] gameLoopKeys(String gameFile, String levelFile, byte[] seq, boolean withTick) {
        StateObservation root = load(gameFile, levelFile, 0);
        Types.ACTIONS[] acts = actions(root);
        VGDLFactory.GetInstance().init();
        VGDLRegistry.GetInstance().init();
        Game game = new VGDLParser().parseGame(gameFile);
        game.buildLevel(levelFile, 0);
        Types.ACTIONS[] s = new Types.ACTIONS[seq.length];
        for (int i = 0; i < seq.length; i++) s[i] = acts[seq[i]];
        Recorder r = new Recorder(s, withTick);
        game.runGame(new core.player.Player[]{r}, 0);
        StateObservation end = game.getObservation();
        boolean endedInside = r.keys.size() <= seq.length;
        if (endedInside) {
            r.keys.add(key(end, withTick));
            r.ticks.add(end.getGameTick());
        }
        return new Object[]{r.keys.toArray(new byte[0][]), r.ticks.stream().mapToInt(Integer::intValue).toArray(),
                endedInside ? status(end) : 0};
    }

    /** The same through the forward model: keys before each action and after the last action played (the
     *  sequence stops where the game ends). */
    public static Object[] forwardKeys(String gameFile, String levelFile, byte[] seq, boolean withTick) {
        StateObservation so = load(gameFile, levelFile, 0);
        Types.ACTIONS[] acts = actions(so);
        ArrayList<byte[]> keys = new ArrayList<>();
        ArrayList<Integer> ticks = new ArrayList<>();
        StateObservation cur = so.copy();
        for (int i = 0; i < seq.length && !cur.isGameOver(); i++) {
            keys.add(key(cur, withTick));
            ticks.add(cur.getGameTick());
            cur.advance(acts[seq[i]]);
        }
        keys.add(key(cur, withTick));
        ticks.add(cur.getGameTick());
        return new Object[]{keys.toArray(new byte[0][]), ticks.stream().mapToInt(Integer::intValue).toArray(),
                status(cur)};
    }

    // ------------------------------------------------------------------ timing, for the engine question
    /** Breadth-first search in Java alone, with copies kept in memory, for at most maxSeen states: returns
     *  {seen, expanded, advances, nanos}.  Used only to measure the engine's speed without the bridge to
     *  Python. */
    public static long[] benchBfs(StateObservation root, boolean withTick, int maxSeen) {
        Types.ACTIONS[] acts = actions(root);
        java.util.HashSet<String> seen = new java.util.HashSet<>();
        java.util.ArrayDeque<StateObservation> q = new java.util.ArrayDeque<>();
        long t0 = System.nanoTime(), expanded = 0, adv = 0;
        seen.add(Arrays.toString(key(root, withTick)));
        q.add(root);
        while (!q.isEmpty() && seen.size() < maxSeen) {
            StateObservation p = q.poll();
            expanded++;
            for (Types.ACTIONS a : acts) {
                StateObservation c = p.copy();
                c.advance(a);
                adv++;
                if (seen.add(Arrays.toString(key(c, withTick))) && status(c) == 0) q.add(c);
            }
        }
        return new long[]{seen.size(), expanded, adv, System.nanoTime() - t0};
    }
}
