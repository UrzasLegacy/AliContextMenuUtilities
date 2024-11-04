Set objShell = CreateObject("WScript.Shell")
objShell.Run "C:\AliProjects\Python\.venv\Scripts\pythonw.exe C:\AliProjects\AliContextMenuUtilities\CkptModelPageViewer\CkptModelPage.py """ & WScript.Arguments(0) & """", 0, False

