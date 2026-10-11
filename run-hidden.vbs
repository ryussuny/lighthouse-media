' Run a batch file with no visible console window, waiting until it finishes.
' 2026-10-11: the 19:00 premium task opened a console for ~10 minutes; closing it killed the run
' (exit 0xC000013A, no log on 10/7 and 10/9). Scheduled tasks now launch through this wrapper.
' Usage: wscript.exe run-hidden.vbs "C:\path\to\task.bat"
If WScript.Arguments.Count < 1 Then WScript.Quit 2
Set sh = CreateObject("WScript.Shell")
rc = sh.Run("cmd /c """ & WScript.Arguments(0) & """", 0, True)
WScript.Quit rc
