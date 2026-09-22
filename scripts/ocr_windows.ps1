param([string]$JobsFile)
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Runtime.WindowsRuntime
$null = [Windows.Storage.StorageFile, Windows.Storage, ContentType=WindowsRuntime]
$null = [Windows.Graphics.Imaging.BitmapDecoder, Windows.Foundation, ContentType=WindowsRuntime]
$null = [Windows.Media.Ocr.OcrEngine, Windows.Foundation, ContentType=WindowsRuntime]
$null = [Windows.Globalization.Language, Windows.Globalization, ContentType=WindowsRuntime]
$asTask = ([System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object { $_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1' })[0]
function Await-Result($Operation, $ResultType) {
    $task = $asTask.MakeGenericMethod($ResultType).Invoke($null, @($Operation))
    $task.Wait()
    return $task.Result
}
$language = New-Object Windows.Globalization.Language('zh-Hans-CN')
$engine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromLanguage($language)
if ($null -eq $engine) { throw 'Chinese Windows OCR language pack is unavailable' }
$jobs = Get-Content -LiteralPath $JobsFile -Raw -Encoding UTF8 | ConvertFrom-Json
$count = 0
$timer = [System.Diagnostics.Stopwatch]::StartNew()
foreach ($job in $jobs) {
    if (Test-Path -LiteralPath $job.output) {
        $prior = Get-Content -LiteralPath $job.output -Raw -Encoding UTF8 | ConvertFrom-Json
        if ($prior.source_sha256 -eq $job.sha256) { continue }
    }
    $waiting = [System.Diagnostics.Stopwatch]::StartNew()
    while (-not (Test-Path -LiteralPath ($job.image + '.ready'))) {
        if ($waiting.Elapsed.TotalMinutes -gt 30) { throw "Timed out waiting for rendered page" }
        Start-Sleep -Seconds 1
    }
    $file = Await-Result ([Windows.Storage.StorageFile]::GetFileFromPathAsync($job.image)) ([Windows.Storage.StorageFile])
    $stream = Await-Result ($file.OpenAsync([Windows.Storage.FileAccessMode]::Read)) ([Windows.Storage.Streams.IRandomAccessStream])
    try {
        $decoder = Await-Result ([Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync($stream)) ([Windows.Graphics.Imaging.BitmapDecoder])
        $bitmap = Await-Result ($decoder.GetSoftwareBitmapAsync()) ([Windows.Graphics.Imaging.SoftwareBitmap])
        try {
            $result = Await-Result ($engine.RecognizeAsync($bitmap)) ([Windows.Media.Ocr.OcrResult])
            $lines = @($result.Lines | ForEach-Object { $_.Text })
            $record = @{source_sha256=$job.sha256;pdf_page=$job.page;text=($lines -join "`n");mean_confidence=$null;engine='Windows.Media.Ocr zh-Hans-CN';dpi=140;human_verified=$false}
            $parent = Split-Path -Parent $job.output
            $null = New-Item -ItemType Directory -Path $parent -Force
            $json = $record | ConvertTo-Json -Depth 5
            [System.IO.File]::WriteAllText($job.output, $json, (New-Object System.Text.UTF8Encoding($false)))
        } finally { $bitmap.Dispose() }
    } finally { $stream.Dispose() }
    $count += 1
    if ($count -eq 1 -or $count % 25 -eq 0) { Write-Output "$count pages in $($timer.Elapsed.TotalSeconds) seconds" }
}
Write-Output "Completed: $count pages in $($timer.Elapsed.TotalSeconds) seconds"
