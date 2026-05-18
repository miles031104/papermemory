function Resolve-NpmCommand {
    [CmdletBinding()]
    param()

    $npmCmd = Get-Command -Name "npm.cmd" -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($null -ne $npmCmd) {
        return $npmCmd.Source
    }

    $whereMatches = @()
    try {
        $whereMatches = @(where.exe npm 2>$null)
    }
    catch {
        $whereMatches = @()
    }

    foreach ($path in $whereMatches) {
        if ([System.IO.Path]::GetExtension($path).Equals(".cmd", [System.StringComparison]::OrdinalIgnoreCase)) {
            return $path
        }
    }

    $npmCommands = @(Get-Command -Name "npm" -CommandType Application -ErrorAction SilentlyContinue)
    foreach ($command in $npmCommands) {
        $extension = [System.IO.Path]::GetExtension($command.Source)
        if (
            $extension.Equals(".cmd", [System.StringComparison]::OrdinalIgnoreCase) -or
            $extension.Equals(".exe", [System.StringComparison]::OrdinalIgnoreCase)
        ) {
            return $command.Source
        }
    }

    $foundPaths = @($whereMatches) + @($npmCommands | ForEach-Object { $_.Source })
    if ($foundPaths.Count -gt 0) {
        $foundList = ($foundPaths | Select-Object -Unique) -join ", "
        throw "npm was found, but npm.cmd was not available on PATH. PowerShell can misparse the extensionless npm shim; install Node.js for Windows or put npm.cmd on PATH. Found: $foundList"
    }

    throw "npm was not found on PATH. Install Node.js 20+ and rerun setup."
}

function Format-NpmPowerShellCommand {
    [CmdletBinding()]
    param([string]$Arguments = "")

    $npmCommand = Resolve-NpmCommand
    $escapedCommand = $npmCommand.Replace("'", "''")
    if ([string]::IsNullOrWhiteSpace($Arguments)) {
        return "& '$escapedCommand'"
    }

    return "& '$escapedCommand' $Arguments"
}
