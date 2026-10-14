# instalar_tarea_servidor.ps1
# Registra el programador GeoVictoria como Tarea Programada de Windows para SERVIDOR:
#   - Arranca con el SISTEMA (AtStartup), sin necesidad de iniciar sesion
#   - Corre aunque no haya nadie conectado (S4U, sin guardar contrasena)
#   - Reintenta si falla, sin limite de tiempo, una sola instancia
# Reemplaza la tarea "GeoVictoria Programador" anterior (AtLogOn), asi que
# ejecutar_tarea_programada.bat / detener_tarea_programada.bat / estado_tarea_programada.bat siguen funcionando.
# Requiere Administrador (instalar_tarea_servidor.bat lo eleva automaticamente).
#
# Parametros:
#   -UsarPassword   Pide la contrasena de Windows y la guarda en la tarea. Usar solo si el modo
#                   por defecto (S4U) no logra arrancar el navegador en tu servidor.

param(
    [string]$ProjectDir = (Split-Path (Split-Path $MyInvocation.MyCommand.Path -Parent) -Parent),
    [switch]$UsarPassword
)

$ErrorActionPreference = "Stop"
$TaskName = "GeoVictoria Programador"
$Launcher = Join-Path $ProjectDir "scripts\servicio_programador.bat"
$VenvPy   = Join-Path $ProjectDir ".venv\Scripts\python.exe"
$User     = "$env:USERDOMAIN\$env:USERNAME"

Write-Host ""
Write-Host "Carpeta del proyecto: $ProjectDir"
Write-Host "Lanzador:             $Launcher"
Write-Host "Usuario de la tarea:  $User"
Write-Host ""

$identity  = [Security.Principal.WindowsIdentity]::GetCurrent()
$isAdmin   = (New-Object Security.Principal.WindowsPrincipal $identity).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "ERROR: ejecuta como Administrador (usa instalar_tarea_servidor.bat)."
    exit 1
}

if (-not (Test-Path $Launcher)) {
    Write-Host "ERROR: no se encontro $Launcher"
    exit 1
}
if (-not (Test-Path $VenvPy)) {
    Write-Host "AVISO: no existe .venv; el lanzador usara 'python' del PATH del sistema."
    Write-Host "       Recomendado: ejecutar setup.bat primero."
}
if (-not ((Test-Path (Join-Path $ProjectDir ".env")) -or (Test-Path (Join-Path $ProjectDir "config\employees.json")))) {
    Write-Host "ERROR: faltan credenciales (.env o config\employees.json)."
    exit 1
}

# Reemplazar tarea anterior (si existe)
if (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    Write-Host "[OK] Tarea anterior eliminada"
}

$Action = New-ScheduledTaskAction -Execute $Launcher -WorkingDirectory $ProjectDir

# Al arrancar el sistema, con 1 minuto de espera para que la red este lista
$Trigger       = New-ScheduledTaskTrigger -AtStartup
$Trigger.Delay = "PT1M"

$Settings = New-ScheduledTaskSettingsSet `
    -ExecutionTimeLimit ([TimeSpan]::Zero) `
    -RestartCount 99 `
    -RestartInterval (New-TimeSpan -Minutes 1) `
    -MultipleInstances IgnoreNew `
    -StartWhenAvailable `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries

if ($UsarPassword) {
    $cred = Get-Credential -UserName $User -Message "Contrasena de Windows para ejecutar la tarea sin sesion iniciada"
    Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -Settings $Settings `
        -User $cred.UserName -Password $cred.GetNetworkCredential().Password -RunLevel Limited `
        -Description "Marcaje automatico GeoVictoria (arranque con el sistema)" | Out-Null
} else {
    $Principal = New-ScheduledTaskPrincipal -UserId $User -LogonType S4U -RunLevel Limited
    Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -Settings $Settings `
        -Principal $Principal `
        -Description "Marcaje automatico GeoVictoria (arranque con el sistema)" | Out-Null
}

$t = Get-ScheduledTask -TaskName $TaskName
Write-Host ""
Write-Host "[OK] Tarea creada: $TaskName (estado: $($t.State))"
Write-Host "[OK] Disparador: al arrancar el sistema, +1 min (no requiere iniciar sesion)"
Write-Host "[OK] Navegador en modo headless (GEOVICTORIA_HEADLESS=1 en el lanzador)"
Write-Host "[OK] Si el proceso muere con error, se relanza a los 60 s"
Write-Host ""
Write-Host "Si ya hay un programador corriendo (ej: de instalar_autoarranque), detenlo antes con"
Write-Host "scripts\detener_todas_instancias.bat y luego: scripts\ejecutar_tarea_programada.bat"
Write-Host "Logs del lanzador: src\logs\servicio.log | del programador: src\logs\programador_*.log"
Write-Host ""
