# Define the remote machine and user credentials
$remoteComputerName = "RemoteHostName"
$credential = Get-Credential

# The path to the New Relic installer on the remote machine
$newRelicInstallerPath = "\\path\to\newrelic-agent-x64.msi"

# The path to the New Relic configuration file
$newRelicConfigPath = "C:\ProgramData\New Relic\.NET Agent\newrelic.config"

# The New Relic license key and other configuration settings
$licenseKey = "YOUR_NEW_RELIC_LICENSE_KEY"
$appName = "YourAppName"

# The PowerShell script to run on the remote machine
$scriptBlock = {
    param (
        $installerPath,
        $configPath,
        $licenseKey,
        $appName
    )
    
    # Stop the IIS service to update the New Relic agent
    Stop-Service -Name 'w3svc' -Force

    # Install the New Relic agent
    Start-Process msiexec.exe -ArgumentList "/i $installerPath /quiet" -Wait

    # Update the New Relic configuration file
    [xml]$config = Get-Content -Path $configPath
    $config.configuration.service.licenseKey = $licenseKey
    $config.configuration.application.name = $appName
    $config.Save($configPath)

    # Start the IIS service
    Start-Service -Name 'w3svc'
}

# Execute the script on the remote machine
Invoke-Command -ComputerName $remoteComputerName -Credential $credential -ScriptBlock $scriptBlock -ArgumentList $newRelicInstallerPath, $newRelicConfigPath, $licenseKey, $appName