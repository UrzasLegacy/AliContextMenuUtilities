Set objShell = CreateObject("WScript.Shell")
objShell.Run "C:\AliProjects\AliContextMenuUtilities\.venv\Scripts\pythonw.exe C:\AliProjects\AliContextMenuUtilities\LoraMetadataViewer\LoraMetadataContextMenu.py """ & WScript.Arguments(0) & """", 0, False
