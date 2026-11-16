// SPDX-License-Identifier: Apache-2.0
using System.Diagnostics;
using System.Text;
namespace TypingTrainer;
public record Metrics(double Seconds, int Completed, int Total, double Cpm, double Wpm, double FirstAccuracy, double FinalAccuracy, double Progress);
public sealed class TrainingSession(string target)
{
    public string Target { get; } = Normalize(target);
    public string Input { get; private set; } = "";
    public long Submitted { get; private set; }
    public long Correct { get; private set; }
    public bool Paused { get; private set; }
    readonly Stopwatch watch = new();
    (string Input, bool Complete, int Distance, int Matched, int Denominator, int Length)? cached;
    public static string Normalize(string value) => value.Replace("\r\n", "\n").Replace('\r', '\n');
    public static string[] Characters(string s) => s.EnumerateRunes().Select(r => r.ToString()).ToArray();
    public void RecordSubmission(string text, int scalarPosition)
    {
        if(Paused)return;
        var goal=Characters(Target);var submitted=Characters(Normalize(text));
        for(int j=0;j<submitted.Length;j++){Submitted++;if(scalarPosition+j<goal.Length&&scalarPosition+j>=0&&goal[scalarPosition+j]==submitted[j])Correct++;}
        if(Submitted>0&&!watch.IsRunning)watch.Start();
    }
    public void Update(string value, bool countEvents = true)
    {
        if (Paused) return;
        value = Normalize(value);
        var old = Characters(Input); var next = Characters(value); var goal = Characters(Target);
        int prefix = 0; while (prefix < old.Length && prefix < next.Length && old[prefix] == next[prefix]) prefix++;
        int suffix = 0; while (suffix < old.Length - prefix && suffix < next.Length - prefix && old[^(suffix + 1)] == next[^(suffix + 1)]) suffix++;
        if(countEvents)for (int i = prefix; i < next.Length - suffix; i++) { Submitted++; if (i < goal.Length && next[i] == goal[i]) Correct++; }
        if (Submitted > 0 && !watch.IsRunning) watch.Start();
        Input = value;
    }
    public void TogglePause() { Paused = !Paused; if (Paused) watch.Stop(); else if (Submitted > 0) watch.Start(); }
    public void Stop() => watch.Stop();
    public Metrics Measure(double? seconds = null, bool complete = false)
    {
        var goal = Characters(Target); var actual = Characters(Input);
        // On early termination, align only against the typed-length target prefix; missing suffix is progress, not error.
        var reference = complete ? goal : goal.Take(Math.Min(actual.Length, goal.Length)).ToArray();
        if (cached is not { } c || c.Input != Input || c.Complete != complete)
        {
            int d = Distance(reference, actual);
            cached = (Input, complete, d, Math.Max(0, reference.Length - d), Math.Max(reference.Length, actual.Length), actual.Length);
        }
        int distance = cached.Value.Distance; int denominator = cached.Value.Denominator;
        int matched = cached.Value.Matched;
        double duration = Math.Max(0, seconds ?? watch.Elapsed.TotalSeconds);
        double cpm = duration > 0 ? matched * 60.0 / duration : 0;
        return new(duration, matched, goal.Length, cpm, cpm / 5, Submitted > 0 ? 100.0 * Correct / Submitted : 0,
            denominator > 0 ? Math.Clamp(100.0 * (1.0 - (double)distance / denominator), 0, 100) : 0,
            goal.Length > 0 ? Math.Clamp(100.0 * Math.Min(actual.Length, goal.Length) / goal.Length, 0, 100) : 0);
    }
    // Exact Levenshtein distance, O(n*m) time / O(min(n,m)) memory; imports capped at 4000 Unicode scalars.
    public static int Distance(string[] a, string[] b)
    {
        if (a.Length > b.Length) (a, b) = (b, a);
        int[] row = Enumerable.Range(0, a.Length + 1).ToArray();
        for (int j = 1; j <= b.Length; j++) { int previous = row[0]; row[0] = j;
            for (int i = 1; i <= a.Length; i++) { int saved = row[i]; row[i] = Math.Min(Math.Min(row[i] + 1, row[i - 1] + 1), previous + (a[i - 1] == b[j - 1] ? 0 : 1)); previous = saved; } }
        return row[a.Length];
    }
}
public record Article(string Id, string Title, string Language, string Text, bool BuiltIn, DateTime Imported)
{ public override string ToString() => Title; public int Count => Text.EnumerateRunes().Count(); }
public record Result(long Number, DateTime Date, string ArticleId, string Title, bool Complete, Metrics Metrics);
public sealed class Preferences
{
    public string Language { get; set; } = "zh";
    public bool Dark { get; set; }
    public string Accent { get; set; } = "#2563EB";
    public double Brightness { get; set; } = 98;
}
public static class BuiltIns
{
    public static List<Article> All() => new (string, string, string)[] {
      ("晨光", "中文", "清晨，阳光落在窗前。我打开笔记本，写下今天的计划。慢慢练习，认真输入，每一次进步都值得记录。"),
      ("湖边散步", "中文", "湖面映着蓝天，微风轻轻吹过。沿着小路向前走，脚步可以慢一些，心中的方向却越来越清晰。"),
      ("书桌上的一天", "中文", "桌上放着一本书、一支笔和一杯温水。先完成眼前的小事，再安排下一项任务。保持专注，也记得适时休息。"),
      ("Simple steps", "English", "Start with a small step. Keep your hands relaxed and your eyes on the next word. A little practice each day can build a steady rhythm."),
      ("The quiet garden", "English", "In the quiet garden, a silver leaf turns in the wind. We listen, wait, and notice how even a short pause can bring a new idea."),
      ("Numbers", "数字 / Numbers", "0123456789 9876543210\n2026-11-05 08:30:45\n12 + 34 = 46; 100 - 25 = 75; 3.14 * 2 = 6.28"),
      ("Punctuation", "English", "\"Ready?\" asked Mia. \"Yes!\" replied Sam. (Take a breath.) Use commas, periods, colons: and semicolons; check [brackets] and {braces}."),
      ("中英协作", "混合 / Mixed", "今天学习 C#，明天练习 English。目标是每分钟 120 个字符，正确率达到 98%。Practice makes progress!"),
      ("换行与空格", "混合 / Mixed", "第一行：保持节奏。\n第二行：注意空格  和标点。\nLine three: one, two, three.\n    Indented line: 42."),
      ("Precision", "English", "Accuracy comes before speed. Compare A with a, zero (0) with the letter O, and one (1) with lowercase l. Save file_v2.txt at 09:05; then verify 99.8%."),
      ("城市夜色", "中文", "夜幕降临后，街角的灯亮了起来。公交车停靠站台，行人穿过斑马线。远处传来钟声：今天的练习结束了，明天还会有新的挑战。"),
      ("Mixed challenge", "混合 / Mixed", "版本 v1.0 已准备好！\nPath: C:\\Work\\Notes\nEmail example: learner@example.invalid\n预算：￥128.50；完成：100%。\nStay curious — keep practicing.")
    }.Select((x,i) => new Article("builtin-"+i, x.Item1,x.Item2,x.Item3,true, new DateTime(2026,11,5))).ToList();
}
