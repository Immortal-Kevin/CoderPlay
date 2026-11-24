using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;
using DesktopGoose.Core;

namespace DesktopGoose.App;

internal static class PixelUi
{
    private static Brush Color(string hex) => (Brush)new BrushConverter().ConvertFromString(hex)!;
    public static readonly Brush Ink = Color("#22283D");
    public static readonly Brush Paper = Color("#FFF4D9");
    public static readonly Brush Accent = Color("#FFCC66");
    public static readonly Brush Muted = Color("#514D69");
    public static readonly Brush White = Color("#FFFCED");

    public static Window Window(string title, UIElement content, double width = 580, double height = 650) => new()
    {
        Title = $"Desktop Goose · {title}", Width = width, Height = height, MinWidth = 360, MinHeight = 300,
        WindowStartupLocation = WindowStartupLocation.CenterScreen, Background = Paper, Foreground = Ink,
        FontFamily = new FontFamily("Consolas, Microsoft YaHei UI"), FontSize = 14, Content = content
    };

    public static StackPanel Page(string title, out ScrollViewer scroll)
    {
        var panel = new StackPanel { Margin = new Thickness(22) };
        panel.Children.Add(new Border
        {
            Background = Ink, Padding = new Thickness(13, 8, 13, 8), Margin = new Thickness(0, 0, 0, 12),
            Child = new TextBlock { Text = title, FontSize = 24, FontWeight = FontWeights.Bold, Foreground = White }
        });
        scroll = new ScrollViewer { VerticalScrollBarVisibility = ScrollBarVisibility.Auto, Content = panel };
        return panel;
    }

    public static TextBlock Text(string value) => new()
    {
        Text = value, TextWrapping = TextWrapping.Wrap, Margin = new Thickness(0, 4, 0, 6), Foreground = Ink
    };

    public static Button Button(string title, Action action)
    {
        var button = new Button
        {
            Content = title, Background = Accent, Foreground = Ink, BorderBrush = Ink, BorderThickness = new Thickness(2),
            FontWeight = FontWeights.SemiBold, Padding = new Thickness(10, 5, 10, 5),
            Margin = new Thickness(0, 4, 6, 4), HorizontalAlignment = HorizontalAlignment.Left
        };
        button.Click += (_, _) => action();
        return button;
    }

    public static ComboBox Pick<T>(IEnumerable<T> values, int index)
    {
        var list = new ComboBox { ItemsSource = values.ToArray(), SelectedIndex = index, MinWidth = 145,
            Margin = new Thickness(0, 3, 6, 5), HorizontalAlignment = HorizontalAlignment.Left };
        return list;
    }

    public static TextBox Field(string value = "") => new()
    {
        Text = value, MinWidth = 160, Padding = new Thickness(5), Margin = new Thickness(0, 3, 5, 6)
    };

    public static CheckBox Check(string caption, bool on) => new()
    {
        Content = caption, IsChecked = on, Margin = new Thickness(0, 5, 5, 6), Foreground = Ink
    };

    public static Image Image(SpriteFrame sprite, double size)
    {
        var image = new Image { Source = sprite.Bitmap, Width = size, Height = size, HorizontalAlignment = HorizontalAlignment.Left };
        RenderOptions.SetBitmapScalingMode(image, BitmapScalingMode.NearestNeighbor);
        return image;
    }

    public static string RarityName(Rarity rarity) => new[] { "常见", "稀有", "罕见", "史诗", "特殊", "传说" }[(int)rarity];
    public static string TemperamentName(Temperament value) => new[] { "活泼", "胆小", "懒惰", "暴躁" }[(int)value];
    public static string AbilityName(Ability value) => new[] { "转圈", "后空翻", "滑行", "特殊舞蹈", "装死", "倒退走" }[(int)value];
    public static string ColorName(Plumage p)
    {
        string[] labels = ["白色", "黑色", "灰色", "棕色", "粉色", "蓝色", "薄荷绿", "奶油黄", "金色", "银色", "蓝白钻石"];
        return p.Rarity == Rarity.Legendary ? "金头 · 蓝白钻石" : p.Accent < 0
            ? labels[p.Color] : $"{labels[p.Color]} · {labels[p.Accent]}花纹";
    }

    public static string StageName(HatchStage stage) => stage switch
    {
        HatchStage.STORED => "未孵化", HatchStage.INCUBATING => "孵化中", HatchStage.PAUSED => "已暂停",
        HatchStage.READY => "可破壳", HatchStage.COMPLETED => "已孵化", _ => "破壳流程中"
    };
}
