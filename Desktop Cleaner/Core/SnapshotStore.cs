using System.Security.Cryptography;
using System.Text.Json;

namespace DesktopCleaner;

public sealed record LayoutSnapshot(int Version, DateTimeOffset SavedAt, int Count,
    DesktopFrame Frame, DesktopIcon[] Icons);

public sealed class SnapshotStore(string directory)
{
    private const int Version = 1;
    private const int MaxSnapshotBytes = 16 * 1024 * 1024;
    private readonly string path = Path.Combine(directory, "original-layout.json");
    private sealed record Envelope(string Sha256, JsonElement Layout);

    public static SnapshotStore ForCurrentUser() =>
        new(Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "DesktopCleaner"));

    public IDisposable Acquire()
    {
        Directory.CreateDirectory(directory);
        try
        {
            return new FileStream(Path.Combine(directory, "session.lock"), FileMode.OpenOrCreate,
                FileAccess.ReadWrite, FileShare.None);
        }
        catch (IOException error)
        {
            throw new IOException("无法锁定恢复目录。请关闭其他 Desktop Cleaner 或紧急恢复进程后重试。", error);
        }
    }

    public bool Pending
    {
        get
        {
            try { _ = File.GetAttributes(path); return true; }
            catch (FileNotFoundException) { return false; }
            catch (DirectoryNotFoundException) { return false; }
        }
    }

    public LayoutSnapshot Save(DesktopState state)
    {
        var layout = new LayoutSnapshot(Version, DateTimeOffset.UtcNow, state.Icons.Length, state.Frame, state.Icons);
        byte[] payload = JsonSerializer.SerializeToUtf8Bytes(layout);
        string temp = Path.Combine(directory, $"original-layout-{Guid.NewGuid():N}.tmp");
        try
        {
            using (var file = new FileStream(temp, FileMode.CreateNew, FileAccess.Write, FileShare.None,
                4096, FileOptions.WriteThrough))
            {
                using (var writer = new Utf8JsonWriter(file))
                {
                    writer.WriteStartObject();
                    writer.WriteString(nameof(Envelope.Sha256), Convert.ToHexString(SHA256.HashData(payload)));
                    writer.WritePropertyName(nameof(Envelope.Layout));
                    writer.WriteRawValue(payload);
                    writer.WriteEndObject();
                }
                file.Flush(flushToDisk: true);
            }
            _ = Read(temp);
            // Publish atomically within the same directory. A pending original can never be overwritten.
            File.Move(temp, path);
            return Load();
        }
        finally { File.Delete(temp); }
    }

    public LayoutSnapshot Load() => Read(path);
    internal void ClearAfterVerification() => File.Delete(path);

    private static LayoutSnapshot Read(string source)
    {
        try
        {
            using var file = new FileStream(source, FileMode.Open, FileAccess.Read, FileShare.Read);
            if (file.Length > MaxSnapshotBytes)
                throw new InvalidDataException("桌面布局快照超过允许的大小。");
            var envelope = JsonSerializer.Deserialize<Envelope>(file)
                ?? throw new InvalidDataException("桌面布局快照为空。");
            byte[] payload = System.Text.Encoding.UTF8.GetBytes(envelope.Layout.GetRawText());
            if (!CryptographicOperations.FixedTimeEquals(SHA256.HashData(payload), Convert.FromHexString(envelope.Sha256)))
                throw new InvalidDataException("桌面布局快照的 SHA-256 校验失败。");
            var snapshot = JsonSerializer.Deserialize<LayoutSnapshot>(payload);
            if (snapshot is null || snapshot.Version != Version || snapshot.SavedAt == default ||
                snapshot.Icons is null || snapshot.Count != snapshot.Icons.Length ||
                snapshot.Icons.Any(i => i is null || string.IsNullOrEmpty(i.Id) || i.Name is null) ||
                snapshot.Icons.Select(i => i.Id).Distinct(StringComparer.Ordinal).Count() != snapshot.Count ||
                snapshot.Frame is null || snapshot.Frame.Dpi == 0 ||
                snapshot.Frame.Spacing.X <= 0 || snapshot.Frame.Spacing.Y <= 0 ||
                snapshot.Frame.Screens is not { Length: > 0 } ||
                snapshot.Frame.Screens.Any(s => s is null || string.IsNullOrEmpty(s.Device) || s.DpiX == 0 ||
                    s.DpiY == 0 || !s.Bounds.Contains(s.WorkArea)))
                throw new InvalidDataException("桌面布局快照的版本或内容无效。");
            return snapshot;
        }
        catch (Exception error) when (error is JsonException or FormatException or ArgumentException or InvalidOperationException)
        {
            throw new InvalidDataException("无法解析桌面布局快照。", error);
        }
    }
}
