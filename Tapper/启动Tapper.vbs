' SPDX-License-Identifier: Apache-2.0
Option Explicit
Dim shell, files, directory
Set shell = CreateObject("WScript.Shell")
Set files = CreateObject("Scripting.FileSystemObject")
directory = files.GetParentFolderName(WScript.ScriptFullName)
shell.CurrentDirectory = directory
shell.Run "pythonw.exe """ & files.BuildPath(directory, "Tapper.pyw") & """", 0, False
