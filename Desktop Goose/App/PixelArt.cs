using System.Windows.Media;
using System.Windows.Media.Imaging;
using DesktopGoose.Core;

namespace DesktopGoose.App;

internal enum Pose
{
    Stand, Walk, Turn, Run, Observe, Startle, Rest, Sleep, Fall, Sneeze, Dance,
    Drag, Dizzy, Lay, Sit, Bye, Spin, Flip, Slide, FancyDance, PlayDead, Backwards
}

internal sealed class SpriteFrame
{
    public BitmapSource Bitmap { get; }
    private readonly (int X, int Y)[] edge;

    public SpriteFrame(uint[] pixels)
    {
        Bitmap = BitmapSource.Create(64, 64, 96, 96, PixelFormats.Bgra32, null, pixels, 256);
        Bitmap.Freeze();
        edge = (from i in Enumerable.Range(0, pixels.Length)
                let x = i % 64
                let y = i / 64
                where pixels[i] != 0 &&
                    (x == 0 || x == 63 || y == 0 || y == 63 ||
                     pixels[i - 1] == 0 || pixels[i + 1] == 0 || pixels[i - 64] == 0 || pixels[i + 64] == 0)
                select (x, y)).ToArray();
    }

    public double Distance(double x, double y)
    {
        int px = (int)Math.Floor(x);
        int py = (int)Math.Floor(y);
        if (px is >= 0 and < 64 && py is >= 0 and < 64)
        {
            var pixel = new byte[4];
            Bitmap.CopyPixels(new System.Windows.Int32Rect(px, py, 1, 1), pixel, 4, 0);
            if (pixel[3] != 0)
                return 0;
        }
        double best = double.PositiveInfinity;
        foreach (var (ex, ey) in edge)
        {
            double dx = Math.Max(0, Math.Max(ex - x, x - ex - 1));
            double dy = Math.Max(0, Math.Max(ey - y, y - ey - 1));
            best = Math.Min(best, dx * dx + dy * dy);
        }
        return Math.Sqrt(best);
    }
}

// Original 64×64 sprite shapes, keyed poses and palette variants.
internal static class PixelArt
{
    private const uint Ink = 0xff242839;
    private const uint Bill = 0xffff9d44;
    private const uint BillShade = 0xffcc592f;
    private static readonly uint[] Palette = [
        0xfffff5d8, 0xff45465a, 0xffa8adc6, 0xffa76947, 0xfff291b6, 0xff83acf2,
        0xff83d6b3, 0xffffd980, 0xfff5bc4c, 0xffc3cee0, 0xc494ddff
    ];
    private static readonly Dictionary<(Plumage, Pose, int, bool), SpriteFrame> Frames = [];
    private static readonly Dictionary<(int, int), SpriteFrame> Props = [];

    public static SpriteFrame Goose(Plumage look, Pose pose, int step, bool left)
    {
        step %= 8;
        if (pose is Pose.Stand or Pose.Rest or Pose.Sit or Pose.PlayDead)
            step = 0;
        if (pose == Pose.Spin && step >= 4)
            left = !left;
        var key = (look, pose, step, left);
        if (Frames.TryGetValue(key, out var frame))
            return frame;
        if (Frames.Count >= 512)
            Frames.Clear();

        var p = new Canvas();
        bool flat = pose is Pose.Rest or Pose.Sleep or Pose.Sit or Pose.PlayDead or Pose.Lay;
        bool moving = pose is Pose.Walk or Pose.Run or Pose.Backwards or Pose.Bye or Pose.Spin;
        int gait = (int)Math.Round(Math.Sin(step * Math.PI / 4) * (pose is Pose.Run or Pose.Bye ? 7 : 4));
        int bounce = pose switch
        {
            Pose.Startle => -9 + Math.Abs(step - 3) * 2,
            Pose.Flip => -10 + Math.Abs(step - 4),
            Pose.Dance or Pose.FancyDance or Pose.Drag => -Math.Abs(gait),
            Pose.Lay => step is 2 or 3 ? -3 : 0,
            _ => moving ? -Math.Abs(gait / 3) : 0
        };
        int by = (flat ? 43 : 37) + bounce;
        uint body = Palette[look.Color];
        uint light = Mix(body, 0xfffdf8e8, .34);
        uint shade = Mix(body, 0xff393652, .30);
        uint head = look.Rarity == Rarity.Legendary ? Palette[8] : body;
        uint headLight = Mix(head, 0xfffff5d8, .30);
        int hx = pose switch
        {
            Pose.Observe => 48 + step / 3,
            Pose.Run or Pose.Bye or Pose.Slide => 47,
            Pose.Drag => 38,
            Pose.Turn => 39,
            Pose.Fall or Pose.PlayDead => 45,
            _ => flat ? 43 : 41
        };
        int hy = pose switch
        {
            Pose.Observe => 14 - step / 2,
            Pose.Fall or Pose.PlayDead => 44,
            Pose.Run or Pose.Bye or Pose.Slide => 26,
            Pose.Sneeze => step < 4 ? 12 : 23,
            Pose.Drag => 11,
            Pose.FancyDance => 15 + gait / 2,
            _ => flat ? 35 : 16
        };
        hy += bounce;
        int swing = moving || pose is Pose.Drag or Pose.FancyDance ? gait : 0;
        if (!flat)
        {
            Foot(p, 24 - swing, by + 9, moving ? 55 - Math.Max(0, -swing / 2) : 54);
            Foot(p, 35 + swing, by + 10, moving ? 56 - Math.Max(0, swing / 2) : 55);
        }
        p.Poly(Ink, (4, by - 8), (18, by - 6), (17, by + 5), (8, by + 1));
        p.Poly(shade, (7, by - 6), (20, by - 4), (16, by + 2));
        p.Ellipse(27, by, 19, 12, Ink);
        p.Ellipse(27, by - 1, 17, 10, body);
        p.Ellipse(25, by + 3, 15, 5, shade);
        p.Poly(Ink, (29, by - 1), (hx - 7, hy + 3), (hx + 4, hy + 2), (43, by + 4), (34, by + 7));
        p.Poly(body, (31, by), (hx - 5, hy + 4), (hx + 2, hy + 4), (41, by + 3), (35, by + 5));
        p.Line(hx - 3, hy + 6, 33, by + 1, light);
        p.Ellipse(25, by - 3, 12, 5, light);
        p.Line(17, by + 2, 28, by + 3, shade);
        p.Line(19, by - 1, 25, by + 1, body);
        if (look.Accent >= 0 && look.Rarity != Rarity.Legendary)
        {
            uint accent = Palette[look.Accent];
            for (int stripe = 0; stripe <= (look.Rarity == Rarity.Special ? 4 : 2); stripe++)
            {
                int x = 15 + stripe * 4;
                int offset = (stripe + look.Pattern) % 3;
                p.Line(x + offset, by - 6 + offset, x + 4, by + 3 - offset, accent);
                p.Line(x + offset + 1, by - 6 + offset, x + 5, by + 3 - offset, accent);
            }
            if (look.Rarity == Rarity.Special && look.Pattern % 2 != 0)
                p.Line(17, by, 36, by - 4, accent);
        }
        if (look.Rarity == Rarity.Legendary)
        {
            p.Poly(0xcef4ffff, (16, by - 3), (23, by - 9), (28, by - 1), (22, by + 4));
            p.Poly(0xc37caaff, (24, by + 5), (29, by), (36, by + 3), (29, by + 8));
            p.Line(32, by - 6, 35, by - 3, 0xffeeffff);
            p.Line(18, by - 2, 23, by - 7, 0xffffffff);
        }

        int radius = pose == Pose.Turn ? 6 : 8;
        p.Ellipse(hx, hy, radius, 7, Ink);
        p.Ellipse(hx, hy - 1, radius - 2, 5, head);
        p.Line(hx - 4, hy - 3, hx + 1, hy - 4, headLight);
        p.Poly(Ink, (hx + radius - 2, hy), (hx + radius + 7, hy + 2),
            (hx + radius + 6, hy + 5), (hx + radius - 2, hy + 6));
        p.Poly(Bill, (hx + radius - 2, hy + 1), (hx + radius + 5, hy + 2), (hx + radius + 4, hy + 4), (hx + radius - 2, hy + 4));
        p.Line(hx + radius + 1, hy + 4, hx + radius + 5, hy + 4, BillShade);

        if (pose is Pose.Sleep or Pose.Rest or Pose.PlayDead)
            p.Line(hx + 2, hy, hx + 4, hy - 1, Ink);
        else
        {
            p.Box(hx + 2, hy - 3, 3, 4, Ink);
            p.Set(hx + 2, hy - 3, 0xffffffff);
        }
        if (pose is Pose.Dizzy or Pose.Fall)
            Spark(p, 18 + step, 12, 0xffffd55a);
        if (pose == Pose.Sleep)
        {
            int y = 19 - step;
            p.Line(46, y, 51, y, 0xff8761ba);
            p.Line(51, y, 46, y + 5, 0xff8761ba);
            p.Line(46, y + 5, 51, y + 5, 0xff8761ba);
        }
        if (pose == Pose.Sneeze && step >= 4)
            Spark(p, 58, 27, 0xff9ad5ff);
        if (pose == Pose.FancyDance)
            Spark(p, 9 + step * 3, 19, 0xfff5bc4c);
        if (pose == Pose.Flip)
            p.Rotate(step);

        frame = new SpriteFrame(p.Oriented(left));
        Frames[key] = frame;
        return frame;
    }

    private static void Foot(Canvas p, int x, int from, int y)
    {
        p.Line(x, from, x, y, BillShade);
        p.Line(x + 1, from, x + 1, y, Bill);
        p.Poly(Ink, (x - 2, y), (x + 7, y), (x + 8, y + 3), (x - 2, y + 3));
        p.Box(x, y + 1, 6, 2, Bill);
    }

    public static SpriteFrame Nest(bool diamond, bool egg, bool ready, int sparkle, bool diamondEgg)
    {
        int mode = (diamond ? 1 : 0) | (egg ? 2 : 0) | (ready ? 4 : 0) | (diamondEgg ? 8 : 0);
        return Prop(100 + mode, sparkle, p =>
        {
            uint rim = diamond ? 0xff76b9ed : 0xffaf8849;
            uint shine = diamond ? 0xffddfcff : 0xffe5bc70;
            p.Ellipse(32, 47, 29, 13, Ink);
            p.Ellipse(32, 46, 27, 11, rim);
            p.Ellipse(32, 43, 23, 7, 0xff435066);
            for (int i = 0; i < 9; i++)
            {
                int x = 9 + i * 5;
                int y = 49 + (i * 7 % 4);
                p.Line(x, y, x + 5, y - 3, shine);
            }
            if (egg)
                EggShape(p, 39, 35, 7, 10, diamondEgg, 0);
            if (ready)
            {
                p.Box(52, 21, 3, 7, 0xffffd667);
                p.Box(52, 30, 3, 3, 0xffffd667);
            }
            if (diamond && sparkle > 0)
            {
                Spark(p, 9 + sparkle * 5, 38 - sparkle % 3 * 3, shine);
                Spark(p, 52 - sparkle * 2, 49, shine);
            }
        });
    }

    public static SpriteFrame Cracking(bool diamond, int step) =>
        Prop(diamond ? 3 : 2, step, p => EggShape(p, 32, 34, 19, 23, diamond, step));

    public static SpriteFrame Footprint(bool left, int fade) => Prop(left ? 4 : 5, fade, p =>
    {
        uint ink = (uint)((7 - fade) * 20 << 24) | 0x00a77555;
        int side = left ? -1 : 1;
        p.Line(32, 44, 32 + side * 6, 25, ink);
        p.Line(32, 44, 32 + side * 16, 31, ink);
        p.Line(32, 44, 32 - side * 4, 24, ink);
    });

    private static SpriteFrame Prop(int kind, int step, Action<Canvas> draw)
    {
        if (Props.TryGetValue((kind, step), out var frame))
            return frame;
        var canvas = new Canvas();
        draw(canvas);
        return Props[(kind, step)] = new SpriteFrame(canvas.Oriented(false));
    }

    private static void EggShape(Canvas p, int x, int y, int rx, int ry, bool diamond, int crack)
    {
        p.Ellipse(x, y, rx, ry, Ink);
        p.Ellipse(x, y, rx - 1, ry - 1, diamond ? 0xffb8edff : 0xffffebba);
        p.Ellipse(x + rx / 4, y + ry / 3, rx / 2, ry / 3, diamond ? 0xff83bce3 : 0xffe6c790);
        p.Ellipse(x - rx / 3, y - ry / 3, rx / 4, ry / 4, 0xfffefbea);
        if (crack > 0)
        {
            p.Line(x + 3, y - ry, x - 4, y - 4, Ink);
            if (crack > 2)
                p.Line(x - 4, y - 4, x + 7, y + 3, Ink);
            if (crack > 4)
                p.Line(x + 7, y + 3, x - 4, y + ry, Ink);
        }
    }

    private static void Spark(Canvas p, int x, int y, uint color)
    {
        p.Box(x - 2, y, 5, 1, color);
        p.Box(x, y - 2, 1, 5, color);
    }

    private static uint Mix(uint from, uint to, double fraction)
    {
        uint result = from & 0xff000000;
        for (int shift = 0; shift < 24; shift += 8)
        {
            double channel = (from >> shift & 255) * (1 - fraction) + (to >> shift & 255) * fraction;
            result |= (uint)channel << shift;
        }
        return result;
    }

    private sealed class Canvas
    {
        private uint[] pixels = new uint[4096];

        public void Set(int x, int y, uint color)
        {
            if (x is >= 0 and < 64 && y is >= 0 and < 64)
                pixels[y * 64 + x] = color;
        }

        public void Box(int x, int y, int w, int h, uint color)
        {
            for (int yy = y; yy < y + h; yy++)
                for (int xx = x; xx < x + w; xx++)
                    Set(xx, yy, color);
        }

        public void Ellipse(int x, int y, int rx, int ry, uint color)
        {
            for (int yy = -ry; yy <= ry; yy++)
                for (int xx = -rx; xx <= rx; xx++)
                    if (xx * xx * ry * ry + yy * yy * rx * rx <= rx * rx * ry * ry)
                        Set(x + xx, y + yy, color);
        }

        public void Line(int x, int y, int endX, int endY, uint color)
        {
            int n = Math.Max(Math.Abs(endX - x), Math.Abs(endY - y));
            for (int i = 0; i <= n; i++)
                Set(x + (endX - x) * i / Math.Max(1, n), y + (endY - y) * i / Math.Max(1, n), color);
        }

        public void Poly(uint color, params (int X, int Y)[] corners)
        {
            for (int y = corners.Min(c => c.Y); y <= corners.Max(c => c.Y); y++)
            {
                var crosses = new List<int>();
                for (int i = 0; i < corners.Length; i++)
                {
                    var (x1, y1) = corners[i];
                    var (x2, y2) = corners[(i + 1) % corners.Length];
                    if ((y1 <= y && y < y2) || (y2 <= y && y < y1))
                        crosses.Add(x1 + (x2 - x1) * (y - y1) / (y2 - y1));
                }
                crosses.Sort();
                for (int i = 1; i < crosses.Count; i += 2)
                    Box(crosses[i - 1], y, crosses[i] - crosses[i - 1] + 1, 1, color);
            }
        }

        public void Rotate(int step)
        {
            double angle = step * 2 * Math.PI / 8;
            double sin = Math.Sin(angle);
            double cos = Math.Cos(angle);
            uint[] previous = pixels;
            pixels = new uint[4096];
            for (int y = 0; y < 64; y++)
                for (int x = 0; x < 64; x++)
                {
                    int sx = 32 + (int)Math.Round((x - 32) * cos + (y - 32) * sin);
                    int sy = 30 + (int)Math.Round((y - 30) * cos - (x - 32) * sin);
                    if (sx is >= 0 and < 64 && sy is >= 0 and < 64)
                        Set(x, y, previous[sy * 64 + sx]);
                }
        }

        public uint[] Oriented(bool left)
        {
            if (left)
                for (int i = 0; i < pixels.Length; i += 64)
                    Array.Reverse(pixels, i, 64);
            return pixels;
        }
    }
}
