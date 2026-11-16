// SPDX-License-Identifier: Apache-2.0
using System.ComponentModel;
using System.Diagnostics;
using System.IO;
using System.Text;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Documents;
using System.Windows.Input;
using System.Windows.Media;
using System.Windows.Threading;
using Microsoft.Win32;
namespace TypingTrainer;
public static class Entry
{
    [STAThread] public static int Main(string[] args)
    {
        using var mutex=new Mutex(true,"Local\\TypingTrainer-v1",out bool first);
        if(!first){ UiDialog.Show(null,"Typing Trainer 已运行 / Already running","Typing Trainer");return 1; }
        Encoding.RegisterProvider(CodePagesEncodingProvider.Instance);
        var application=new Application();
        // Text-only UI: deterministic rendering without a GPU driver dependency.
        RenderOptions.ProcessRenderMode=System.Windows.Interop.RenderMode.SoftwareOnly;
        application.DispatcherUnhandledException+=(_,e)=>{UiDialog.Show(Application.Current.MainWindow,e.Exception.Message,"Typing Trainer");e.Handled=true;};
        try { return application.Run(new MainWindow()); } catch(Exception e) {UiDialog.Show(null,e.Message,"Typing Trainer");return 2;}
    }
}
public sealed class MainWindow : Window
{
    readonly Store store;
    readonly Grid shell=new();
    readonly ScrollViewer scroller;
    readonly StackPanel page=new(){Margin=new Thickness(36),MaxWidth=1500};
    readonly DispatcherTimer timer=new(){Interval=TimeSpan.FromMilliseconds(250)};
    TrainingSession? session; Article? article;
    TextBox? input; RichTextBox? target; TextBlock? clock; TextBlock? live; Button? pause;
    bool composing, processing, pendingSubmission; int compositionStart; string screen="home";
    Brush foreground=Brushes.Black, surface=Brushes.White, accent=Brushes.RoyalBlue;
    bool English=>store.Settings.Language=="en";
    string T(string zh,string en)=>English?en:zh;
    public MainWindow(Store? dataStore=null)
    {
        store=dataStore??new Store();
        // Apply the requested dark UI once; later explicit light-theme preferences remain intact.
        var themeMarker=Path.Combine(store.Root,"config","ui-v2.applied");
        if(!File.Exists(themeMarker)){store.Settings.Dark=true;store.SaveSettings();File.WriteAllText(themeMarker,"2");}
        Title="Typing Trainer";Width=1280;Height=800;MinWidth=900;MinHeight=600;WindowStyle=WindowStyle.SingleBorderWindow;ResizeMode=ResizeMode.CanResize;UseLayoutRounding=true;SnapsToDevicePixels=true;WindowStartupLocation=WindowStartupLocation.CenterScreen;
        FontFamily=new FontFamily("Microsoft YaHei UI");FontSize=16;Content=shell;
        var centered=new Grid{HorizontalAlignment=HorizontalAlignment.Stretch};
        centered.RowDefinitions.Add(new RowDefinition{Height=new GridLength(1,GridUnitType.Star)});
        centered.RowDefinitions.Add(new RowDefinition{Height=GridLength.Auto});
        centered.RowDefinitions.Add(new RowDefinition{Height=new GridLength(1,GridUnitType.Star)});
        Grid.SetRow(page,1);centered.Children.Add(page);
        scroller=new ScrollViewer{Content=centered,VerticalScrollBarVisibility=ScrollBarVisibility.Auto,HorizontalScrollBarVisibility=ScrollBarVisibility.Disabled,HorizontalContentAlignment=HorizontalAlignment.Stretch};
        centered.SetBinding(FrameworkElement.MinHeightProperty,new System.Windows.Data.Binding("ViewportHeight"){Source=scroller});shell.Children.Add(scroller);
        SourceInitialized+=(_,_)=>{WindowAppearance.FitInitialWindow(this);WindowAppearance.NativeTitleBar(this,store.Settings.Dark);};
        SizeChanged+=(_,_)=>page.Margin=new Thickness(ActualWidth<1050?24:36,24,ActualWidth<1050?24:36,24);
        timer.Tick+=(_,_)=>RefreshLive();timer.Start();
        PreviewKeyDown+=Keys;Closing+=OnClosing;Theme();Home();
    }
    void Theme()
    {
        bool dark=store.Settings.Dark;
        Brush ColorBrush(string value)=>new SolidColorBrush((Color)ColorConverter.ConvertFromString(value));
        byte b=(byte)(255*Math.Clamp(store.Settings.Brightness,85,100)/100);
        Background=dark?ColorBrush("#10141D"):new SolidColorBrush(Color.FromRgb(b,b,b));
        foreground=ColorBrush(dark?"#F8FAFC":"#192741");surface=ColorBrush(dark?"#1A2230":"#FFFFFF");
        try{accent=ColorBrush(store.Settings.Accent);}catch{accent=ColorBrush("#2563EB");}
        var palette=new Dictionary<string,Brush>{["BackgroundBrush"]=Background,["SurfaceBrush"]=surface,["ForegroundBrush"]=foreground,["SecondaryBrush"]=ColorBrush(dark?"#94A3B8":"#526176"),["BorderBrush"]=ColorBrush(dark?"#334155":"#CBD5E1"),["AccentBrush"]=accent,["HoverBrush"]=ColorBrush("#3B82F6"),["PressedBrush"]=ColorBrush("#1D4ED8"),["ChartAccuracyBrush"]=ColorBrush(dark?"#4ADE80":"#15803D")};
        if(Resources.MergedDictionaries.Count==0)Resources.MergedDictionaries.Add(new ResourceDictionary{Source=new Uri("/TypingTrainer;component/UiTheme.xaml",UriKind.Relative)});
        if(Application.Current!=null&&Application.Current.Resources.MergedDictionaries.Count==0)Application.Current.Resources.MergedDictionaries.Add(new ResourceDictionary{Source=new Uri("/TypingTrainer;component/UiTheme.xaml",UriKind.Relative)});
        foreach(var item in palette){Resources[item.Key]=item.Value;if(Application.Current!=null)Application.Current.Resources[item.Key]=item.Value;}
        foreach(var key in new[]{SystemColors.WindowBrushKey,SystemColors.ControlBrushKey,SystemColors.ControlLightBrushKey}){Resources[key]=surface;if(Application.Current!=null)Application.Current.Resources[key]=surface;}
        foreach(var key in new[]{SystemColors.WindowTextBrushKey,SystemColors.ControlTextBrushKey}){Resources[key]=foreground;if(Application.Current!=null)Application.Current.Resources[key]=foreground;}
        Foreground=foreground;shell.Background=Background;
        Language=System.Windows.Markup.XmlLanguage.GetLanguage(English?"en-US":"zh-CN");
        WindowAppearance.NativeTitleBar(this,dark);
    }
    void Begin(string name,string title)
    {screen=name;scroller.VerticalContentAlignment=VerticalAlignment.Top;page.Children.Clear();page.Children.Add(new TextBlock{Text=title,FontSize=32,FontWeight=FontWeights.SemiBold,Margin=new Thickness(0,0,0,20)});}
    TextBlock Label(string text,double size=16) {var label=new TextBlock{Text=text,FontSize=size,TextWrapping=TextWrapping.Wrap,Margin=new Thickness(0,6,0,10)};if(size<16)label.SetResourceReference(TextBlock.ForegroundProperty,"SecondaryBrush");page.Children.Add(label);return label;}
    Button Button(string label,Action action,Panel? parent=null) {var button=new Button{Content=label,HorizontalAlignment=HorizontalAlignment.Left,MinWidth=130};button.Click+=(_,_)=>Safe(action);(parent??page).Children.Add(button);return button;}
    void Safe(Action action){try{action();}catch(Exception e){UiDialog.Show(this,e.Message,T("操作失败","Operation failed"));}}
    WrapPanel Row(){var row=new WrapPanel{Orientation=Orientation.Horizontal};page.Children.Add(row);return row;}
    bool Confirm(string zh,string en)=>UiDialog.Show(this,T(zh,en),"Typing Trainer",true);
    void Back()=>Button(T("返回主页","Home"),Home);
    void Home()
    {
        session=null;Begin("home","Typing Trainer");scroller.VerticalContentAlignment=VerticalAlignment.Center;
        foreach(var entry in new (string,string,Action)[]{("开始训练","Start training",SelectArticle),("设置","Settings",Settings),("文本库·导入","Library / Import",Library),("退出","Exit",Close)})
        {var button=Button(T(entry.Item1,entry.Item2),entry.Item3);button.Width=320;button.MaxWidth=340;button.Height=60;button.HorizontalAlignment=HorizontalAlignment.Center;button.Margin=new Thickness(0,0,0,18);}
        ((TextBlock)page.Children[0]).HorizontalAlignment=HorizontalAlignment.Center;((TextBlock)page.Children[0]).Margin=new Thickness(0,0,0,32);
    }
    void SelectArticle()
    {
        Begin("select",T("选择练习文章","Choose an article"));
        var combo=new ComboBox{ItemsSource=store.Articles(),SelectedIndex=0,MinWidth=400};page.Children.Add(combo);
        var details=Label(""); var preview=new TextBox{IsReadOnly=true,TextWrapping=TextWrapping.Wrap,Height=300,VerticalScrollBarVisibility=ScrollBarVisibility.Auto};page.Children.Add(preview);
        void Update(){if(combo.SelectedItem is Article a){details.Text=$"{a.Language} · {a.Count} "+T("字符 · 预计 ","characters · about ")+Math.Max(1,(int)Math.Ceiling(a.Count/120.0))+T(" 分钟"," min");preview.Text=a.Text;}}
        combo.SelectionChanged+=(_,_)=>Update();Update();Button(T("确认开始","Start"),()=>Start((Article)combo.SelectedItem));Back();
    }
    void Start(Article selected)
    {
        article=selected;session=new(selected.Text);composing=false;pendingSubmission=false;Begin("training",selected.Title);
        var row=Row();clock=new TextBlock{Text="00:00",FontSize=26,MinWidth=110,VerticalAlignment=VerticalAlignment.Center};row.Children.Add(clock);
        pause=Button(T("暂停","Pause"),TogglePause,row);Button(T("终止训练","End training"),()=>Finish(false),row);
        Label(T("Esc 暂停 / 继续 · Ctrl+Enter 结束 · Ctrl+R 重新开始（确认）","Esc pause / resume · Ctrl+Enter end · Ctrl+R restart (confirm)"),13);
        live=Label("");
        target=new RichTextBox{IsReadOnly=true,IsDocumentEnabled=false,Height=220,FontSize=22,Background=surface,Foreground=foreground,VerticalScrollBarVisibility=ScrollBarVisibility.Auto,BorderBrush=accent,Padding=new Thickness(12)};page.Children.Add(target);
        Label(T("输入区（禁止粘贴；中文候选词确认后计入）","Type here (paste disabled; IME text counts after commit)"));
        input=new TrainingTextBox{AcceptsReturn=true,AcceptsTab=true,TextWrapping=TextWrapping.Wrap,VerticalScrollBarVisibility=ScrollBarVisibility.Auto,Height=220,FontSize=22,AllowDrop=false,MaxLength=16000,IsUndoEnabled=false};page.Children.Add(input);
        input.SetResourceReference(StyleProperty,typeof(TextBox));
        DataObject.AddPastingHandler(input,(_,e)=>e.CancelCommand());
        input.CommandBindings.Add(new CommandBinding(ApplicationCommands.Paste,(_,e)=>e.Handled=true,(_,e)=>{e.CanExecute=false;e.Handled=true;}));
        input.PreviewDrop+=(_,e)=>e.Handled=true;
        TextCompositionManager.AddPreviewTextInputStartHandler(input,(_,_)=>{compositionStart=input.SelectionStart;composing=true;});
        TextCompositionManager.AddPreviewTextInputUpdateHandler(input,(_,_)=>composing=true);
        TextCompositionManager.AddPreviewTextInputHandler(input,(_,e)=>{
            int position=composing?compositionStart:input.SelectionStart;composing=false;
            if(session!=null&&!session.Paused&&!string.IsNullOrEmpty(e.Text)){
                int scalar=TrainingSession.Characters(TrainingSession.Normalize(input.Text[..Math.Min(position,input.Text.Length)])).Length;
                session.RecordSubmission(e.Text,scalar);pendingSubmission=true;
            }
            Dispatcher.BeginInvoke(DispatcherPriority.Background,new Action(Commit));
        });
        input.TextChanged+=(_,_)=>{if(!composing)Commit();};
        input.AddHandler(ScrollViewer.ScrollChangedEvent,new ScrollChangedEventHandler((_,e)=>{if(target!=null&&e.ExtentHeight>e.ViewportHeight)target.ScrollToVerticalOffset(e.VerticalOffset/(e.ExtentHeight-e.ViewportHeight)*Math.Max(0,target.ExtentHeight-target.ViewportHeight));}));
        Paint();Dispatcher.BeginInvoke(DispatcherPriority.Input,new Action(()=>input?.Focus()));
    }
    void Commit()
    {
        if(processing||session==null||input==null||session.Paused||composing)return;
        processing=true;
        try {session.Update(input.Text,!pendingSubmission);pendingSubmission=false;Paint();RefreshLive();if(TrainingSession.Characters(session.Input).Length>=TrainingSession.Characters(session.Target).Length)Finish(true);}finally{processing=false;}
    }
    void Paint()
    {
        if(session==null||target==null)return;
        var goal=TrainingSession.Characters(session.Target);var actual=TrainingSession.Characters(session.Input);
        var paragraph=new Paragraph{Margin=new Thickness(0),LineHeight=34};
        for(int i=0;i<goal.Length;i++) {
            var run=new Run(goal[i]);if(i<actual.Length)run.Foreground=actual[i]==goal[i]?foreground:Brushes.IndianRed;
            if(i==Math.Min(actual.Length,goal.Length-1))run.Background=accent;
            paragraph.Inlines.Add(run);
        }
        target.Document=new FlowDocument(paragraph){PagePadding=new Thickness(0),FontFamily=FontFamily,FontSize=22,Foreground=foreground};
        if(actual.Length>0) {var pos=paragraph.ContentStart;int move=Math.Min(session.Input.Length,session.Target.Length);while(move-->0&&pos!=null)pos=pos.GetNextInsertionPosition(LogicalDirection.Forward);pos?.Parent?.ToString();if(pos!=null)target.ScrollToVerticalOffset(Math.Max(0,pos.GetCharacterRect(LogicalDirection.Forward).Y+target.VerticalOffset-100));}
    }
    void RefreshLive()
    {
        if(screen!="training"||session==null)return;
        // Cached edit-distance values are reused while only elapsed time changes.
        var metrics=session.Measure();if(clock!=null)clock.Text=$"{(int)metrics.Seconds/60:00}:{(int)metrics.Seconds%60:00}";
        if(live!=null)live.Text=$"{metrics.Progress:F1}% · {metrics.Completed}/{metrics.Total} · {metrics.Cpm:F1} CPM · {metrics.Wpm:F1} WPM · "+T("首次正确率 ","First accuracy ")+$"{metrics.FirstAccuracy:F1}%";
    }
    void TogglePause()
    {
        if(session==null||screen!="training")return;
        // Commit/cancel composition before disabling the editor; provisional text is excluded.
        session.TogglePause();if(input!=null)input.IsReadOnly=session.Paused;
        if(pause!=null)pause.Content=session.Paused?T("继续","Resume"):T("暂停","Pause");if(!session.Paused)input?.Focus();
    }
    void Finish(bool complete)
    {
        if(session==null||article==null)return;
        session.Stop();var metrics=session.Measure(complete:complete);var selected=article;
        Result? result=null;
        if(session.Submitted>0)result=store.Save(selected,complete,metrics);
        session=null;ShowResults(result,selected.Id);
    }
    void ShowResults(Result? current,string? articleId)
    {
        Begin("results",T("训练结算与历史","Results & history"));
        if(current!=null) {
            var m=current.Metrics;Label($"#{current.Number} · {current.Title} · "+(current.Complete?T("完成","Completed"):T("提前终止","Ended early")),23);
            Label($"{TimeSpan.FromSeconds(m.Seconds):mm\\:ss} · {m.Completed}/{m.Total} · {m.Progress:F1}%\n{m.Cpm:F1} CPM / {m.Wpm:F1} WPM · "+T("首次 / 最终正确率：","First / final accuracy: ")+$"{m.FirstAccuracy:F2}% / {m.FinalAccuracy:F2}%");
            var previous=store.Results().Where(x=>x.Number<current.Number).ToList();
            string Delta(double baseline)=>baseline>0?$"{(m.Cpm/baseline-1)*100:+0.0;-0.0;0.0}%":T("暂无基准","No baseline");
            Label(T("相比上次：","Versus previous: ")+Delta(previous.LastOrDefault()?.Metrics.Cpm??0)+T("；相比历史平均：","; versus historic mean: ")+Delta(previous.Count>0?previous.Average(x=>x.Metrics.Cpm):0));
        } else Label(T("未输入的训练不保存成绩。可在下方查看历史。","Zero-input sessions are not saved. History is shown below."));
        var filter=Row();var scope=new ComboBox{Width=230};scope.Items.Add(T("全部文章","All articles"));foreach(var a in store.Articles())scope.Items.Add(a);scope.SelectedIndex=0;
        if(articleId!=null)foreach(var a in scope.Items.OfType<Article>())if(a.Id==articleId){scope.SelectedItem=a;break;}filter.Children.Add(scope);
        var count=new ComboBox{ItemsSource=new[]{"10","30",T("全部","All")},SelectedIndex=0,Width=100};filter.Children.Add(count);
        var sort=new ComboBox{ItemsSource=new[]{T("训练时间","Date"),"CPM",T("最终正确率","Final accuracy")},SelectedIndex=0,Width=180};filter.Children.Add(sort);
        var full=new CheckBox{Content=T("仅完整成绩","Completed only"),IsChecked=true,VerticalAlignment=VerticalAlignment.Center};filter.Children.Add(full);
        var chart=new TrendChart{Height=250,Margin=new Thickness(0,12,0,12),ClipToBounds=true};page.Children.Add(chart);
        var trend=Label("");var list=new ListView{Height=240,Background=surface,Foreground=foreground};
        var view=new GridView();list.View=view;
        foreach(var col in new[]{("#","Number",55.0),(T("时间","Date"),"Date",170.0),(T("文章","Article"),"Title",200.0),("CPM","Cpm",95.0),("WPM","Wpm",90.0),(T("首次 %","First %"),"First",95.0),(T("最终 %","Final %"),"Final",95.0),(T("状态","Status"),"Status",130.0)})view.Columns.Add(new GridViewColumn{Header=col.Item1,DisplayMemberBinding=new System.Windows.Data.Binding(col.Item2),Width=col.Item3});page.Children.Add(list);
        void Update(){var records=store.Results().Where(x=>(scope.SelectedItem is not Article a||x.ArticleId==a.Id)&&(!full.IsChecked.GetValueOrDefault()||x.Complete)).ToList();
            int limit=count.SelectedIndex==0?10:count.SelectedIndex==1?30:int.MaxValue;var points=records.TakeLast(limit).ToList();DrawChart(chart,points);
            trend.Text=points.Count>1&&points[0].Metrics.Cpm>0?T("区间速度变化：","Speed change: ")+$"{(points[^1].Metrics.Cpm/points[0].Metrics.Cpm-1)*100:+0.0;-0.0;0.0}%":"";
            IEnumerable<Result> sorted=sort.SelectedIndex switch{1=>records.OrderByDescending(x=>x.Metrics.Cpm),2=>records.OrderByDescending(x=>x.Metrics.FinalAccuracy),_=>records.OrderByDescending(x=>x.Date)};
            list.ItemsSource=sorted.Select(x=>new{ x.Number,Date=x.Date.ToString("yyyy-MM-dd HH:mm"),x.Title,Cpm=x.Metrics.Cpm.ToString("F1"),Wpm=x.Metrics.Wpm.ToString("F1"),First=x.Metrics.FirstAccuracy.ToString("F1"),Final=x.Metrics.FinalAccuracy.ToString("F1"),Status=x.Complete?T("完成","Completed"):T("提前终止","Ended early")}).ToList();}
        scope.SelectionChanged+=(_,_)=>Update();count.SelectionChanged+=(_,_)=>Update();sort.SelectionChanged+=(_,_)=>Update();full.Checked+=(_,_)=>Update();full.Unchecked+=(_,_)=>Update();chart.SizeChanged+=(_,_)=>Update();Update();
        var row=Row();Button(T("重新训练","Train again"),()=>{if(article!=null)Start(article);else SelectArticle();},row);Button(T("返回主页","Home"),Home,row);
        Button(T("清空历史","Clear history"),()=>{if(Confirm("确定清空所有训练历史？将先创建备份。","Clear all history? A backup will be kept.")&&Confirm("再次确认：清空全部成绩？","Confirm again: delete all results?")){store.Clear();ShowResults(null,articleId);}},row);
    }
    void DrawChart(TrendChart chart,List<Result> data)
    {chart.Results=data;chart.English=English;chart.InvalidateVisual();}
    void Settings()
    {
        Begin("settings",T("设置","Settings"));Label(T("界面语言","Interface language"));
        var language=new ComboBox{ItemsSource=new[]{"简体中文","English"},SelectedIndex=English?1:0,Width=250,HorizontalAlignment=HorizontalAlignment.Left};page.Children.Add(language);
        language.SelectionChanged+=(_,_)=>Safe(()=>{store.Settings.Language=language.SelectedIndex==1?"en":"zh";store.SaveSettings();Theme();Settings();});
        var dark=new CheckBox{Content=T("深色主题","Dark theme"),IsChecked=store.Settings.Dark};page.Children.Add(dark);
        dark.Click+=(_,_)=>Safe(()=>{store.Settings.Dark=dark.IsChecked==true;store.SaveSettings();Theme();Settings();});
        Label(T("蓝色强调色","Blue accent"));var color=new ComboBox{ItemsSource=new[]{"#2563EB","#1D4ED8","#0369A1","#075985"},SelectedItem=store.Settings.Accent,Width=250,HorizontalAlignment=HorizontalAlignment.Left};page.Children.Add(color);
        color.SelectionChanged+=(_,_)=>Safe(()=>{store.Settings.Accent=(string)color.SelectedItem;store.SaveSettings();Theme();Settings();});
        Label(T("浅色背景明度（85–100）","Light background brightness (85–100)"));var brightness=new Slider{Minimum=85,Maximum=100,Value=store.Settings.Brightness,Width=350,HorizontalAlignment=HorizontalAlignment.Left,IsSnapToTickEnabled=true,TickFrequency=1};page.Children.Add(brightness);
        brightness.ValueChanged+=(_,_)=>Safe(()=>{store.Settings.Brightness=brightness.Value;store.SaveSettings();Theme();});
        Label(T("数据目录：","Data folder: ")+store.Root);
        var row=Row();Button(T("打开数据文件夹","Open data folder"),()=>Process.Start(new ProcessStartInfo(store.Root){UseShellExecute=true}),row);
        Button(T("安全迁移目录","Move data folder"),()=>{var dialog=new OpenFolderDialog{Title=T("选择空目录","Choose an empty folder")};if(dialog.ShowDialog(this)==true){store.SaveSettings();store.Migrate(dialog.FolderName);Settings();}},row);
        Button(T("历史成绩","Training history"),()=>ShowResults(null,null));Back();
    }
    void Library()
    {
        Begin("library",T("文本库 / 导入","Library / Import"));var search=new TextBox();page.Children.Add(search);Label(T("搜索标题或内容；内置文章只读","Search titles or text; built-in articles are read-only"),13);
        var list=new ListBox{Height=160,Background=surface,Foreground=foreground};page.Children.Add(list);
        var meta=Label("");var title=new TextBox();page.Children.Add(title);
        var preview=new TextBox{IsReadOnly=true,Height=200,TextWrapping=TextWrapping.Wrap,VerticalScrollBarVisibility=ScrollBarVisibility.Auto};page.Children.Add(preview);
        void Update(){list.ItemsSource=store.Articles().Where(x=>x.Title.Contains(search.Text,StringComparison.OrdinalIgnoreCase)||x.Text.Contains(search.Text,StringComparison.OrdinalIgnoreCase)).ToList();}
        search.TextChanged+=(_,_)=>Update();list.SelectionChanged+=(_,_)=>{if(list.SelectedItem is Article a){title.Text=a.Title;preview.Text=a.Text;meta.Text=(a.BuiltIn?T("内置","Built-in"):T("用户导入","Imported"))+$" · {a.Language} · {a.Count} · {a.Imported:yyyy-MM-dd}";}};Update();
        var row=Row();Button(T("重命名","Rename"),()=>{if(list.SelectedItem is Article a&&!a.BuiltIn){if(string.IsNullOrWhiteSpace(title.Text))throw new IOException(T("标题不能为空","Title is required"));store.Put(a with{Title=title.Text.Trim()});Update();}},row);
        Button(T("删除用户文章","Delete user article"),()=>{if(list.SelectedItem is Article a&&!a.BuiltIn&&Confirm("删除选中文章？历史成绩仍会保留。","Delete this article? History will be preserved.")){store.Delete(a);Update();}},row);
        Button(T("练习选中文章","Train selected"),()=>{if(list.SelectedItem is Article a)Start(a);},row);
        Label(T("TXT 编码（自动识别失败时手动指定）","TXT encoding (choose manually if detection fails)"));var encoding=new ComboBox{ItemsSource=new[]{"auto","UTF-8","UTF-16LE","UTF-16BE","GB18030"},SelectedIndex=0,Width=200,HorizontalAlignment=HorizontalAlignment.Left};page.Children.Add(encoding);
        Button(T("导入 TXT / DOCX / DOC","Import TXT / DOCX / DOC"),()=>{var dialog=new OpenFileDialog{Filter="Text / Word|*.txt;*.docx;*.doc"};if(dialog.ShowDialog(this)!=true)return;var text=Importer.Read(dialog.FileName,(string)encoding.SelectedItem);ImportPreview(System.IO.Path.GetFileNameWithoutExtension(dialog.FileName),text);});Back();
    }
    void ImportPreview(string name,string text)
    {
        Begin("import",T("导入预览","Import preview"));var title=new TextBox{Text=name};page.Children.Add(title);Label(TrainingSession.Characters(text).Length+T(" 字符"," characters"));var box=new TextBox{Text=text,IsReadOnly=true,Height=330,TextWrapping=TextWrapping.Wrap,VerticalScrollBarVisibility=ScrollBarVisibility.Auto};page.Children.Add(box);
        Button(T("确认导入","Confirm import"),()=>{if(string.IsNullOrWhiteSpace(title.Text))throw new IOException(T("标题不能为空","Title is required"));store.Put(new Article(Guid.NewGuid().ToString("N"),title.Text.Trim(),text.Any(c=>c>127)?"Mixed":"English",text,false,DateTime.Now));Library();});Button(T("取消","Cancel"),Library);
    }
    void Keys(object sender,KeyEventArgs e)
    {
        if(screen!="training"||session==null)return;
        if(e.Key==Key.Escape){e.Handled=true;TogglePause();}
        else if(Keyboard.Modifiers==ModifierKeys.Control&&e.Key==Key.Enter){e.Handled=true;Safe(()=>Finish(false));}
        else if(Keyboard.Modifiers==ModifierKeys.Control&&e.Key==Key.R){e.Handled=true;if(Confirm("放弃本次输入并重新开始？","Discard this session and restart?"))Start(article!);}
        else if((Keyboard.Modifiers==ModifierKeys.Control&&(e.Key==Key.V||e.Key==Key.Z||e.Key==Key.Y))||(Keyboard.Modifiers==ModifierKeys.Shift&&e.Key==Key.Insert))e.Handled=true;
    }
    void OnClosing(object? sender,CancelEventArgs e)
    {
        if(session!=null&&!Confirm("训练尚未结束，关闭将放弃本次成绩。确定关闭？","Training is active. Close and discard this session?"))e.Cancel=true;
    }
}


