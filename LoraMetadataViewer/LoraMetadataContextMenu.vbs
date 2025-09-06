Set objShell = CreateObject("WScript.Shell")
objShell.Run "C:\AliContextMenuUtilities\.venv\Scripts\pythonw.exe C:\AliContextMenuUtilities\LoraMetadataViewer\LoraMetadataContextMenu.py """ & WScript.Arguments(0) & """", 0, False
