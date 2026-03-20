# PowerShell script to convert ML prediction results to simple format

# Find the newest Resultados_YYYYMMDD.txt file
$inputFiles = Get-ChildItem -Path "." -Filter "Resultados_????????.txt" | Sort-Object LastWriteTime -Descending

if ($inputFiles.Count -eq 0) {
    Write-Host "Error: No files found with format 'Resultados_YYYYMMDD.txt'"
    exit
}

# Use the newest file
$inputFile = $inputFiles[0].Name
Write-Host "Using newest file: $inputFile"

# Generate output filename based on input file
$datePart = $inputFile -replace 'Resultados_(\d{8})\.txt', '$1'
$outputFile = "Resultados_Simple_$datePart.txt"

# 1. Read as a single raw string so the regex works across multiple lines
$rawContent = Get-Content $inputFile -Raw

# 2. Use your regex pattern
$pattern = '(?m)(.+?)\r?\nResultado: (\d+-\d+)'
$foundMatches = [regex]::Matches($rawContent, $pattern)

if ($foundMatches.Count -eq 0) {
    Write-Host "No matches found. Check the file format."
    exit
}

# 3. Get the 3rd line (Index 2) by splitting the raw text
$allLines = $rawContent -split "`r?`n"
$fecha = $allLines[2]

# 4. Process matches
$simpleResults = @()
$simpleResults += $fecha  # Add the date first

foreach ($match in $foundMatches) {
    $simpleResults += "Team: $($match.Groups[1].Value) = Score: $($match.Groups[2].Value)"
}

# 5. Add the last 3 predictions
$keywords = "Goles totales predichos", "Cantidad de penales cobrados", "Cantidad de expulsados"
$simpleResults += ""

# Filter the lines and add them to the simpleResults array
foreach ($word in $keywords) {
    $line = $allLines -match $word
    if ($line) {
        $simpleResults += $line
    }
}

$simpleResults

# Save to file
$simpleResults | Out-File -FilePath $outputFile -Encoding UTF8
Write-Host "`nResults saved to: $outputFile"

