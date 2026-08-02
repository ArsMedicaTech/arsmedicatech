# unseal-vault.ps1
# Usage: .\unseal-vault.ps1 [-EnvFile .env] [-Nodes vault-0,vault-1,vault-2]

param(
    [string]$EnvFile = ".env",
    [string[]]$Nodes = @("vault-0", "vault-1", "vault-2"),
    [string]$Namespace = "vault",
    [string]$LeaderAddress = "http://vault-0.vault-internal:8200"
)

# ---------------------------------------------------------------------------
# Load unseal keys from .env
# ---------------------------------------------------------------------------

if (-not (Test-Path $EnvFile)) {
    Write-Error "Env file not found: $EnvFile"
    exit 1
}

$keys = @()
foreach ($line in Get-Content $EnvFile) {
    if ($line -match '^\s*VAULT_UNSEAL_KEY_\d+\s*=\s*(.+)$') {
        $keys += $Matches[1].Trim()
    }
}

if ($keys.Count -lt 3) {
    Write-Error "Need at least 3 unseal keys, found $($keys.Count). Check your .env file."
    exit 1
}

Write-Host "Loaded $($keys.Count) unseal keys." -ForegroundColor Cyan

# ---------------------------------------------------------------------------
# Helper: check if a node is initialized
# ---------------------------------------------------------------------------

function Get-VaultStatus($node) {
    $raw = kubectl exec -n $Namespace $node -- vault status 2>&1 | Out-String
    return @{
        Initialized = $raw -match "Initialized\s+true"
        Sealed      = $raw -notmatch "Sealed\s+false"
    }
}

# ---------------------------------------------------------------------------
# Process each node
# ---------------------------------------------------------------------------

foreach ($node in $Nodes) {
    Write-Host "`n--- $node ---" -ForegroundColor Yellow

    $status = Get-VaultStatus $node

    # Join if uninitialized (vault-1, vault-2 on first run)
    if (-not $status.Initialized) {
        Write-Host "$node is uninitialized - joining Raft cluster..."
        kubectl exec -n $Namespace $node -- vault operator raft join $LeaderAddress
    } else {
        Write-Host "$node is already initialized."
    }

    # Unseal if sealed
    $status = Get-VaultStatus $node
    if ($status.Sealed) {
        Write-Host "$node is sealed - unsealing..."
        $progress = 0
        foreach ($key in $keys[0..2]) {
            kubectl exec -n $Namespace $node -- vault operator unseal $key | Out-Null
            $progress++
            Write-Host "  Key $progress/3 applied."
            # Check if already unsealed (threshold may be met before all 3)
            $status = Get-VaultStatus $node
            if (-not $status.Sealed) { break }
        }
        $status = Get-VaultStatus $node
        if ($status.Sealed) {
            Write-Warning "$node is still sealed after applying keys. Check your keys."
        } else {
            Write-Host "$node unsealed successfully." -ForegroundColor Green
        }
    } else {
        Write-Host "$node is already unsealed." -ForegroundColor Green
    }
}

# ---------------------------------------------------------------------------
# Final: list Raft peers
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Load root token
# ---------------------------------------------------------------------------

$rootToken = $null
foreach ($line in Get-Content $EnvFile) {
    if ($line -match '^\s*VAULT_ROOT_TOKEN\s*=\s*(.+)$') {
        $rootToken = $Matches[1].Trim()
    }
}

# ---------------------------------------------------------------------------
# Final: list Raft peers
# ---------------------------------------------------------------------------

Write-Host "`n--- Raft peer list ---" -ForegroundColor Cyan
if ($rootToken) {
    kubectl exec -n $Namespace vault-0 -- env VAULT_TOKEN=$rootToken vault operator raft list-peers
} else {
    Write-Warning "VAULT_ROOT_TOKEN not set in $EnvFile - skipping raft peer list."
}
