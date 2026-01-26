' EmberOS Windows Installer (VBScript)
' A self-contained installer that runs without any dependencies
' Double-click to install EmberOS

Option Explicit

Dim objShell, objFSO, objHTTP, objStream
Dim strScriptPath, strEmberDir, strTempDir, strModelDir
Dim intResponse

' Initialize
Set objShell = CreateObject("WScript.Shell")
Set objFSO = CreateObject("Scripting.FileSystemObject")

' Get paths
strScriptPath = objFSO.GetParentFolderName(WScript.ScriptFullName)
strEmberDir = objShell.ExpandEnvironmentStrings("%LOCALAPPDATA%") & "\EmberOS"
strTempDir = objShell.ExpandEnvironmentStrings("%TEMP%") & "\EmberOS_Setup"
strModelDir = strEmberDir & "\models"

' Welcome message
intResponse = MsgBox( _
    "Welcome to EmberOS Installer!" & vbCrLf & vbCrLf & _
    "This will install EmberOS on your PC." & vbCrLf & vbCrLf & _
    "Installation is fully self-contained and won't affect" & vbCrLf & _
    "any existing software on your system." & vbCrLf & vbCrLf & _
    "Click OK to continue or Cancel to exit.", _
    vbOKCancel + vbInformation, "EmberOS Installer")

If intResponse = vbCancel Then
    WScript.Quit
End If

' Check if batch installer exists
Dim strBatchInstaller
strBatchInstaller = strScriptPath & "\EmberOS-Install.bat"

If Not objFSO.FileExists(strBatchInstaller) Then
    MsgBox "EmberOS-Install.bat not found!" & vbCrLf & vbCrLf & _
           "Please make sure you're running this from the EmberOS directory.", _
           vbCritical, "EmberOS Installer"
    WScript.Quit
End If

' Run the batch installer in a visible window
MsgBox "The installer will now start." & vbCrLf & vbCrLf & _
       "Please follow the on-screen instructions.", _
       vbInformation, "EmberOS Installer"

objShell.Run """" & strBatchInstaller & """", 1, True

' Success message
MsgBox "Installation complete!" & vbCrLf & vbCrLf & _
       "To start EmberOS:" & vbCrLf & _
       "1. Open a new Command Prompt" & vbCrLf & _
       "2. Run: ember-llm" & vbCrLf & _
       "3. Run: emberd" & vbCrLf & _
       "4. Run: ember-ui" & vbCrLf & vbCrLf & _
       "Or use Start Menu -> EmberOS", _
       vbInformation, "EmberOS Installer"

' Cleanup
Set objShell = Nothing
Set objFSO = Nothing

