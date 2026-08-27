Set WshShell = CreateObject("WScript.Shell")
strPath = Wscript.ScriptFullName
Set objFSO = CreateObject("Scripting.FileSystemObject")
Set objFile = objFSO.GetFile(strPath)
strFolder = objFSO.GetParentFolderName(objFile)
scriptPath = strFolder & "\asus_dh_service.py"

' Find correct python.exe by checking dependencies
pythonPath = "python.exe"

On Error Resume Next
Set objExec = WshShell.Exec("where python.exe")
If Err.Number = 0 Then
    Do While Not objExec.StdOut.AtEndOfStream
        line = Trim(objExec.StdOut.ReadLine())
        If line <> "" Then
            ' Check if this python can import dependencies
            testCmd = """" & line & """ -c ""import pystray, PIL, hid"""
            testRet = WshShell.Run(testCmd, 0, True)
            If testRet = 0 Then
                pythonPath = line
                Exit Do
            End If
        End If
    Loop
End If
Err.Clear

cmdLine = """" & pythonPath & """ """ & scriptPath & """"
' WindowStyle 0 = hidden; WaitOnReturn False = do not block Startup on the long-running service
WshShell.Run cmdLine, 0, False
