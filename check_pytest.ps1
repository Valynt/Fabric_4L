Get-Process -Name "pytest" -ErrorAction SilentlyContinue | Select-Object Id, ProcessName, CommandLine
