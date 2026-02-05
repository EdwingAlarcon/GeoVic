# Script para configurar Tarea Programada de Windows para GeoVictoria
# Ejecutar como Administrador

Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host "  CONFIGURADOR DE TAREA PROGRAMADA - GEOVICTORIA" -ForegroundColor Cyan
Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host ""

# Obtener ruta absoluta del proyecto
$projectPath = Split-Path -Parent $PSScriptRoot
$batPath = Join-Path $projectPath "scripts\iniciar_programador.bat"

Write-Host "[1/5] Verificando archivos necesarios..." -ForegroundColor Yellow

if (-not (Test-Path $batPath)) {
    Write-Host "ERROR: No se encuentra iniciar_programador.bat" -ForegroundColor Red
    Write-Host "Ruta esperada: $batPath" -ForegroundColor Red
    pause
    exit 1
}

Write-Host "  OK: $batPath" -ForegroundColor Green
Write-Host ""

# Verificar si ya existe la tarea
Write-Host "[2/5] Verificando tareas existentes..." -ForegroundColor Yellow

$taskName = "GeoVictoria Programador"
$existingTask = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue

if ($existingTask) {
    Write-Host "  ADVERTENCIA: Ya existe una tarea con el nombre '$taskName'" -ForegroundColor Yellow
    Write-Host "  ¿Desea eliminarla y crear una nueva? (S/N): " -NoNewline -ForegroundColor Yellow
    $response = Read-Host
    
    if ($response -eq 'S' -or $response -eq 's') {
        Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
        Write-Host "  Tarea anterior eliminada" -ForegroundColor Green
    } else {
        Write-Host "  Operación cancelada" -ForegroundColor Red
        pause
        exit 0
    }
}

Write-Host "  Listo para crear nueva tarea" -ForegroundColor Green
Write-Host ""

# Crear la acción (ejecutar el .bat)
Write-Host "[3/5] Configurando acción..." -ForegroundColor Yellow

$action = New-ScheduledTaskAction `
    -Execute $batPath `
    -WorkingDirectory $projectPath

Write-Host "  Acción: Ejecutar $batPath" -ForegroundColor Green
Write-Host "  Directorio: $projectPath" -ForegroundColor Green
Write-Host ""

# Crear el disparador (al iniciar sesión)
Write-Host "[4/5] Configurando disparador..." -ForegroundColor Yellow

$trigger = New-ScheduledTaskTrigger -AtLogOn

Write-Host "  Disparador: Al iniciar sesión del usuario" -ForegroundColor Green
Write-Host ""

# Configurar opciones principales
Write-Host "[5/5] Configurando opciones de la tarea..." -ForegroundColor Yellow

$principal = New-ScheduledTaskPrincipal `
    -UserId "$env:USERDOMAIN\$env:USERNAME" `
    -LogonType Interactive `
    -RunLevel Limited

$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -DontStopOnIdleEnd `
    -ExecutionTimeLimit (New-TimeSpan -Hours 0) `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 1)

Write-Host "  Usuario: $env:USERDOMAIN\$env:USERNAME" -ForegroundColor Green
Write-Host "  Nivel: Usuario estándar" -ForegroundColor Green
Write-Host "  Permitir en batería: Sí" -ForegroundColor Green
Write-Host "  Límite de tiempo: Sin límite" -ForegroundColor Green
Write-Host ""

# Registrar la tarea
Write-Host "Registrando tarea programada..." -ForegroundColor Yellow

try {
    Register-ScheduledTask `
        -TaskName $taskName `
        -Action $action `
        -Trigger $trigger `
        -Principal $principal `
        -Settings $settings `
        -Description "Marcaje automático de asistencia GeoVictoria para Colombia" `
        -ErrorAction Stop | Out-Null
    
    Write-Host ""
    Write-Host "================================================================================" -ForegroundColor Green
    Write-Host "  TAREA CREADA EXITOSAMENTE" -ForegroundColor Green
    Write-Host "================================================================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "Configuración de la tarea:" -ForegroundColor Cyan
    Write-Host "  Nombre: $taskName" -ForegroundColor White
    Write-Host "  Se ejecutará: Al iniciar sesión" -ForegroundColor White
    Write-Host "  Usuario: $env:USERNAME" -ForegroundColor White
    Write-Host "  Programa: iniciar_programador.bat" -ForegroundColor White
    Write-Host ""
    
    # Preguntar si desea ejecutar ahora
    Write-Host "¿Desea iniciar la tarea ahora? (S/N): " -NoNewline -ForegroundColor Yellow
    $runNow = Read-Host
    
    if ($runNow -eq 'S' -or $runNow -eq 's') {
        Write-Host ""
        Write-Host "Iniciando tarea programada..." -ForegroundColor Yellow
        Start-ScheduledTask -TaskName $taskName
        Start-Sleep -Seconds 2
        
        # Verificar estado
        $task = Get-ScheduledTask -TaskName $taskName
        $taskInfo = Get-ScheduledTaskInfo -TaskName $taskName
        
        Write-Host "Estado: " -NoNewline -ForegroundColor Cyan
        if ($task.State -eq "Running") {
            Write-Host "EJECUTÁNDOSE" -ForegroundColor Green
        } else {
            Write-Host $task.State -ForegroundColor Yellow
        }
        
        Write-Host "Última ejecución: $($taskInfo.LastRunTime)" -ForegroundColor White
        Write-Host "Última resultado: $($taskInfo.LastTaskResult)" -ForegroundColor White
        Write-Host ""
        Write-Host "NOTA: Se abrirá una ventana con el programador." -ForegroundColor Cyan
        Write-Host "      Puedes MINIMIZARLA (NO cerrarla)" -ForegroundColor Cyan
    }
    
    Write-Host ""
    Write-Host "================================================================================" -ForegroundColor Green
    Write-Host "Para administrar la tarea en el futuro:" -ForegroundColor Cyan
    Write-Host "  - Abrir Programador de tareas: Win + R > taskschd.msc" -ForegroundColor White
    Write-Host "  - Ejecutar manualmente: scripts\ejecutar_tarea_programada.bat" -ForegroundColor White
    Write-Host "  - Detener tarea: scripts\detener_tarea_programada.bat" -ForegroundColor White
    Write-Host "  - Eliminar tarea: scripts\eliminar_tarea_programada.bat" -ForegroundColor White
    Write-Host "================================================================================" -ForegroundColor Green
    
} catch {
    Write-Host ""
    Write-Host "ERROR al crear la tarea: $_" -ForegroundColor Red
    Write-Host ""
    Write-Host "Posibles soluciones:" -ForegroundColor Yellow
    Write-Host "  1. Ejecutar PowerShell como Administrador" -ForegroundColor White
    Write-Host "  2. Verificar permisos del usuario" -ForegroundColor White
    Write-Host "  3. Revisar que Task Scheduler esté habilitado" -ForegroundColor White
    pause
    exit 1
}

Write-Host ""
pause
