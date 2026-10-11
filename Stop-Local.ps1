[CmdletBinding(SupportsShouldProcess = $true)]
param()

$statePath = Join-Path $PSScriptRoot 'work\servers.json'
if (-not (Test-Path -LiteralPath $statePath)) {
    Write-Output 'Não existe registo de servidores iniciados nesta sessão.'
    return
}
$state = Get-Content -LiteralPath $statePath -Raw | ConvertFrom-Json
foreach ($server in $state.servers) {
    $process = Get-Process -Id $server.pid -ErrorAction SilentlyContinue
    if ($null -eq $process) { continue }
    # A identidade inclui o instante de arranque: nunca parar um PID reutilizado.
    if ($process.StartTime.ToUniversalTime().Ticks.ToString() -ne $server.startTimeTicks) {
        Write-Warning "O PID $($server.pid) foi reutilizado; não será parado."
        continue
    }
    if ($PSCmdlet.ShouldProcess("$($server.name), PID $($server.pid)", 'Parar servidor local DroneDirector')) {
        Stop-Process -Id $process.Id
    }
}
