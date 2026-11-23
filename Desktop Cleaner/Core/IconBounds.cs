using System.Runtime.InteropServices;

namespace DesktopCleaner;

internal static class IconBounds
{
    private const uint ClientObject = unchecked((uint)-4);
    private const int ListItemRole = 0x2c;
    private const int InvisibleState = 0x8000;

    internal static PixelRect[] Read(nint surface, int shellCount)
    {
        if (shellCount == 0)
            return [];
        Guid iid = typeof(IAccessible).GUID;
        Marshal.ThrowExceptionForHR(AccessibleObjectFromWindow(surface, ClientObject, iid, out var list));
        try
        {
            int actualCount = list.ChildCount;
            var children = new object[actualCount];
            Marshal.ThrowExceptionForHR(AccessibleChildren(list, 0, actualCount, children, out int fetched));
            var rectangles = new List<PixelRect>(shellCount);
            for (int index = 0; index < fetched; index++)
            {
                var item = children[index] as IAccessible ?? list;
                int child = children[index] is int id ? id : 0;
                if (!Equals(item.Role(child), ListItemRole) || item.State(child) is not int state || (state & InvisibleState) != 0)
                    continue;
                item.Location(out int x, out int y, out int width, out int height, child);
                if (width <= 0 || height <= 0)
                    throw new InvalidOperationException("Explorer 返回了无效的图标边界。");
                rectangles.Add(new(x, y, x + width, y + height));
            }
            if (rectangles.Count != shellCount)
                throw new InvalidOperationException($"Shell 返回 {shellCount} 个图标，可访问性接口返回 {rectangles.Count} 个可见图标。");
            return rectangles.ToArray();
        }
        finally { Marshal.ReleaseComObject(list); }
    }

    [DllImport("oleacc")]
    private static extern int AccessibleObjectFromWindow(nint window, uint objectId, in Guid iid,
        [MarshalAs(UnmanagedType.Interface)] out IAccessible accessible);

    [DllImport("oleacc")]
    private static extern int AccessibleChildren([MarshalAs(UnmanagedType.Interface)] IAccessible list, int start,
        int count, [Out, MarshalAs(UnmanagedType.LPArray, ArraySubType = UnmanagedType.Struct, SizeParamIndex = 2)] object[] children,
        out int fetched);

    [ComImport, Guid("618736E0-3C3D-11CF-810C-00AA00389B71"), InterfaceType(ComInterfaceType.InterfaceIsDual)]
    private interface IAccessible
    {
        void SlotParent();
        int ChildCount { get; }
        void SlotChild();
        void SlotName();
        void SlotValue();
        void SlotDescription();
        [return: MarshalAs(UnmanagedType.Struct)] object Role([MarshalAs(UnmanagedType.Struct)] object child);
        [return: MarshalAs(UnmanagedType.Struct)] object State([MarshalAs(UnmanagedType.Struct)] object child);
        void SlotHelp();
        void SlotHelpTopic();
        void SlotShortcut();
        void SlotFocus();
        void SlotSelection();
        void SlotDefaultAction();
        void SlotSelect();
        void Location(out int left, out int top, out int width, out int height,
            [MarshalAs(UnmanagedType.Struct)] object child);
    }
}
