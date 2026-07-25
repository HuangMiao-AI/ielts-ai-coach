param(
    [string]$BankPath = ""
)

$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
if (-not $BankPath) {
    $BankPath = Join-Path $projectRoot `
        "ielts_ai_coach\content\question_banks\listening_v1.json"
}
$bank = Get-Content -Raw -Encoding UTF8 -LiteralPath $BankPath |
    ConvertFrom-Json

$voiceProbe = New-Object -ComObject SAPI.SpVoice
$voiceTokens = @($voiceProbe.GetVoices())
if ($voiceTokens.Count -eq 0) {
    throw "No installed Windows speech voice is available."
}
$englishVoice = $voiceTokens |
    Where-Object { $_.GetDescription() -match "English" } |
    Select-Object -First 1
if ($null -eq $englishVoice) {
    $englishVoice = $voiceTokens[0]
}

foreach ($test in $bank.tests) {
    $outputPath = Join-Path $projectRoot $test.audio_path
    $outputDirectory = Split-Path -Parent $outputPath
    New-Item -ItemType Directory -Force -Path $outputDirectory | Out-Null

    $speechXml = [System.Text.StringBuilder]::new()
    [void]$speechXml.Append("<SAPI>")
    foreach ($section in $test.sections) {
        $sectionTitle = [System.Security.SecurityElement]::Escape(
            [string]$section.title
        )
        [void]$speechXml.Append(
            "<RATE SPEED='-1'>Beginning $sectionTitle.</RATE>" +
            "<SILENCE MSEC='800'/>"
        )
        foreach ($turn in $section.script) {
            $speaker = [System.Security.SecurityElement]::Escape(
                [string]$turn.speaker
            )
            $text = [System.Security.SecurityElement]::Escape(
                [string]$turn.text
            )
            $pause = [Math]::Max(0, [Math]::Min(5000, [int]$turn.pause_ms))
            $speed = if ($turn.speaker -eq "Speaker B") { 0 } else { -1 }
            [void]$speechXml.Append(
                "<RATE SPEED='$speed'>$speaker. $text</RATE>" +
                "<SILENCE MSEC='$pause'/>"
            )
        }
        [void]$speechXml.Append("<SILENCE MSEC='1400'/>")
    }
    [void]$speechXml.Append("</SAPI>")

    $synth = New-Object -ComObject SAPI.SpVoice
    $stream = New-Object -ComObject SAPI.SpFileStream
    try {
        $synth.Voice = $englishVoice
        $synth.Volume = 100
        $stream.Format.Type = 22
        $stream.Open($outputPath, 3, $false)
        $synth.AudioOutputStream = $stream
        [void]$synth.Speak($speechXml.ToString(), 8)
    }
    finally {
        $stream.Close()
    }
    Write-Output "$($test.test_id) -> $outputPath"
}
