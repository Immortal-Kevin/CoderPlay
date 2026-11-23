using System.Runtime.InteropServices;

namespace DesktopCleaner;

[ComImport, Guid("85CB6900-4D95-11CF-960C-0080C7F4EE85"), InterfaceType(ComInterfaceType.InterfaceIsDual)]
internal interface IShellWindows
{
    void SlotCount();
    void SlotItem();
    void SlotNewEnum();
    void SlotRegister();
    void SlotRegisterPending();
    void SlotRevoke();
    void SlotOnNavigate();
    void SlotOnActivated();
    [PreserveSig] int FindWindowSW([In, MarshalAs(UnmanagedType.Struct)] ref object location,
        [In, MarshalAs(UnmanagedType.Struct)] ref object? root, int windowClass, out int hwnd,
        int options, [MarshalAs(UnmanagedType.IDispatch)] out object dispatch);
}

[ComImport, Guid("6D5140C1-7436-11CE-8034-00AA006009FA"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
internal interface IShellServiceProvider
{
    [PreserveSig] int QueryService(in Guid service, in Guid iid, [MarshalAs(UnmanagedType.Interface)] out object result);
}

[ComImport, Guid("000214E2-0000-0000-C000-000000000046"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
internal interface IShellBrowser
{
    void SlotGetWindow();
    void SlotContextSensitiveHelp();
    void SlotInsertMenus();
    void SlotSetMenu();
    void SlotRemoveMenus();
    void SlotSetStatusText();
    void SlotEnableModeless();
    void SlotTranslateAccelerator();
    void SlotBrowseObject();
    void SlotGetViewStateStream();
    void SlotGetControlWindow();
    void SlotSendControlMsg();
    [PreserveSig] int QueryActiveShellView([MarshalAs(UnmanagedType.Interface)] out IShellView view);
}

[ComImport, Guid("000214E3-0000-0000-C000-000000000046"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
internal interface IShellView
{
    [PreserveSig] int GetWindow(out nint hwnd);
}

[ComImport, Guid("CDE725B0-CCC9-4519-917E-325D72FAB4CE"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
internal interface IFolderView
{
    void SlotGetCurrentViewMode();
    void SlotSetCurrentViewMode();
    void SlotGetFolder();
    [PreserveSig] int Item(int index, out nint child);
    [PreserveSig] int ItemCount(uint flags, out int count);
    void SlotItems();
    void SlotGetSelectionMarkedItem();
    void SlotGetFocusedItem();
    [PreserveSig] int GetItemPosition(nint child, out Pixel position);
    [PreserveSig] int GetSpacing(out Pixel spacing);
    void SlotGetDefaultSpacing();
    [PreserveSig] int GetAutoArrange();
    void SlotSelectItem();
    [PreserveSig] int SelectAndPositionItems(uint count,
        [In, MarshalAs(UnmanagedType.LPArray, SizeParamIndex = 0)] nint[] children,
        [In, MarshalAs(UnmanagedType.LPArray, SizeParamIndex = 0)] Pixel[] positions, uint flags);
}

