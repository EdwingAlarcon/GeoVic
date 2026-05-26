# instalar_autoarranque.ps1
# Registra GeoVictoria como tarea automatica en el Programador de tareas de Windows.
# Se ejecuta al iniciar sesion, sin ventana de consola, con reintentos si falla.

param(
    [string]$ProjectDir = (Split-Path (Split-Path $MyInvocation.MyCommand.Path -Parent) -Parent)
)

$TaskName = "GeoVictoria Programador"
$Pythonw  = Join-Path $ProjectDir ".venv\Scripts\pythonw.exe"
$Script   = "src\programador.py"

Write-Host ""
Write-Host "Carpeta del proyecto: $ProjectDir"
Write-Host "Ejecutable Python:    $Pythonw"
Write-Host ""

if (-not (Test-Path $Pythonw)) {
    Write-Host "ERROR: No se encontro $Pythonw"
    Write-Host "       Ejecuta setup.bat primero para crear el entorno virtual."
    exit 1
}

# Eliminar tarea anterior si existe
Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue

# Accion: ejecutar pythonw.exe (sin consola) con el programador
$Action = New-ScheduledTaskAction `
    -Execute $Pythonw `
    -Argument $Script `
    -WorkingDirectory $ProjectDir

# Disparador: al iniciar sesion, con 30 segundos de espera
$Trigger       = New-ScheduledTaskTrigger -AtLogOn
$Trigger.Delay = "PT30S"

# Configuracion: sin limite de tiempo, reintentar hasta 3 veces si falla
$Settings = New-ScheduledTaskSettingsSet `
    -ExecutionTimeLimit ([TimeSpan]::Zero) `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 2) `
    -MultipleInstances IgnoreNew `
    -StartWhenAvailable

Register-ScheduledTask `
    -TaskName    $TaskName `
    -Action      $Action `
    -Trigger     $Trigger `
    -Settings    $Settings `
    -RunLevel    Limited `
    -Force | Out-Null

Write-Host "[OK] Tarea creada: $TaskName"
Write-Host "[OK] Iniciara automaticamente al iniciar sesion en Windows"
Write-Host "[OK] Espera 30 segundos antes de arrancar"
Write-Host "[OK] Reintentos automaticos si falla: hasta 3 veces (cada 2 min)"
Write-Host "[OK] Sin ventana de consola visible"
Write-Host ""
Write-Host "Para verificar: abre 'Programador de tareas' en el menu inicio"
Write-Host "Para eliminar:  scripts\desinstalar_autoarranque.bat"
Write-Host ""
