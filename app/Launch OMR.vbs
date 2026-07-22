Set sh = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

appDir = fso.GetParentFolderName(WScript.ScriptFullName)
omrExe = appDir & "\OMR\OMR.exe"

If Not fso.FileExists(omrExe) Then
  MsgBox "Run ""Extract OMR Demo.bat"" first.", vbExclamation, "OMR"
  WScript.Quit 1
End If

' Avoid launching twice if already running.
Set proc = GetObject("winmgmts:").ExecQuery("SELECT * FROM Win32_Process WHERE Name='OMR.exe'")
If proc.Count > 0 Then
  WScript.Quit 0
End If

sh.CurrentDirectory = appDir & "\OMR"
sh.Run """" & omrExe & """", 0, False
