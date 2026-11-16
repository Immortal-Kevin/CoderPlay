# Third-party components

| Component | Version | Copyright / license | Official source / retained text |
|---|---|---|---|
| Microsoft.NETCore.App.Runtime.win-x64 | 10.0.14 | .NET Foundation and Contributors; MIT plus upstream incorporated notices | https://www.nuget.org/packages/Microsoft.NETCore.App.Runtime.win-x64/10.0.14 ; licenses/dotnet-runtime-MIT.txt ; licenses/dotnet-runtime-THIRD-PARTY-NOTICES.txt |
| Microsoft.WindowsDesktop.App.Runtime.win-x64 (WPF and bundled desktop runtime files) | 10.0.14 | .NET Foundation and Contributors; MIT plus WPF incorporated notices | https://www.nuget.org/packages/Microsoft.WindowsDesktop.App.Runtime.win-x64/10.0.14 ; licenses/dotnet-windowsdesktop-MIT.txt ; https://github.com/dotnet/wpf/blob/v10.0.14/THIRD-PARTY-NOTICES.TXT ; licenses/wpf-THIRD-PARTY-NOTICES.txt |
| .NET apphost / single-file bundler | 10.0.14 / SDK 10.0.403 | .NET Foundation and Contributors; MIT, included runtime notices | Official Microsoft .NET SDK; https://github.com/dotnet/runtime ; licenses/dotnet-runtime-MIT.txt |
| Windows winsqlite3.dll | Installed OS version (queried at runtime) | Microsoft Windows system component, not redistributed; upstream SQLite is public domain | https://www.sqlite.org/copyright.html ; installed Windows system component |
| Microsoft YaHei UI / fallback fonts | Installed OS fonts | Windows font rights; no font files redistributed | Installed Windows only |
| Application, test harness, installer, chart drawing, DOCX parser, 12 articles | 1.0.0 | Original project work; Apache-2.0 | src/, tests/, ui-tests/, installer/, LICENSE |

No explicit NuGet PackageReference, DOC parser, chart library, model, image or icon dependency. Framework runtime packs are implicit transitive distribution dependencies and are scanned separately. SDK and build tools are not bundled in either user package.

The two upstream notice files are authoritative for incorporated component copyright, exact notice text, URLs, and versions where upstream states them. SBOM.json also inventories every notice heading. Unstated subcomponent versions are tracked as incorporated in the exact runtime version and repository revision rather than invented.

Additional notice families reviewed: BSD-2/3, MIT, Apache-2.0, Unicode data, zlib, public domain/CC0, W3C, NCSA/LLVM, RFC grants, SGML/ISO entity-table notice, and BSD-4 advertising notice. Original runtime binaries are retained without modification. The ISO notice applies to the runtime's entity-table use; all upstream notices are retained. BSD-4 acknowledgement is reproduced in NOTICE and README. No third-party component is relicensed as Apache-2.0. Retaining an aggregate notice does not imply that every platform-specific component in that notice is present in the Windows pack.
