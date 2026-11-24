using System.IO;
using System.Media;
using DesktopGoose.Core;

namespace DesktopGoose.App;

internal enum Honk { Normal, Startled, Lay, Protest }

internal sealed class Honks : IDisposable
{
    private SoundPlayer? player;
    private MemoryStream? clip;

    public void Play(Honk sound, Settings settings, DateTime local)
    {
        int minute = local.Hour * 60 + local.Minute;
        bool quiet = settings.QuietEnabled && (settings.QuietFrom < settings.QuietTo
            ? minute >= settings.QuietFrom && minute < settings.QuietTo
            : minute >= settings.QuietFrom || minute < settings.QuietTo);
        if (settings.Volume == 0 || quiet)
            return;
        Dispose();
        int[] notes = sound switch
        {
            Honk.Startled => [410, 285],
            Honk.Lay => [152, 172, 275, 236],
            Honk.Protest => [340, 245, 345],
            _ => [295, 226]
        };
        const int rate = 22050;
        int perNote = rate * (sound == Honk.Startled ? 105 : 145) / 1000;
        int bytes = 2 * perNote * notes.Length;
        clip = new MemoryStream();
        using var writer = new BinaryWriter(clip, System.Text.Encoding.ASCII, true);
        writer.Write("RIFF"u8);
        writer.Write(36 + bytes);
        writer.Write("WAVEfmt "u8);
        writer.Write(16);
        writer.Write((short)1);
        writer.Write((short)1);
        writer.Write(rate);
        writer.Write(rate * 2);
        writer.Write((short)2);
        writer.Write((short)16);
        writer.Write("data"u8);
        writer.Write(bytes);
        foreach (int note in notes)
        {
            double phase = 0;
            for (int i = 0; i < perNote; i++)
            {
                double t = (double)i / perNote;
                phase += 2 * Math.PI * (note * (1.13 - 0.33 * t) + 9 * Math.Sin(t * 20)) / rate;
                double edge = Math.Min(1, Math.Min(t * 24, (1 - t) * 7));
                double tone = .60 * Math.Sin(phase) + .27 * Math.Sin(phase * 2) + .13 * Math.Sin(phase * 5);
                writer.Write((short)(tone * edge * 13500 * settings.Volume / 100));
            }
        }
        clip.Position = 0;
        player = new SoundPlayer(clip);
        player.Load();
        player.Play();
    }

    public void Dispose()
    {
        player?.Stop();
        player?.Dispose();
        clip?.Dispose();
        player = null;
        clip = null;
    }
}
