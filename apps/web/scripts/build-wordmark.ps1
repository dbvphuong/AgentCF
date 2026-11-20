# Rebuild the outlined wordmark on Windows; the Web app needs no installed font.
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Drawing
$culture = [Globalization.CultureInfo]::InvariantCulture
$outline = [Drawing.Drawing2D.GraphicsPath]::new()
$format = [Drawing.StringFormat]::GenericTypographic.Clone()
$cursor = 0.0
try {
    foreach ($part in @(
        @{ Text = 'Agent'; Family = 'Bahnschrift'; Gap = 11.0 },
        @{ Text = 'CF'; Family = 'Bahnschrift SemiBold'; Gap = 0.0 }
    )) {
        $family = [Drawing.FontFamily]::new($part.Family)
        try {
            foreach ($letter in $part.Text.ToCharArray()) {
                $glyph = [Drawing.Drawing2D.GraphicsPath]::new()
                try {
                    $glyph.AddString([string]$letter, $family, 0, 48, [Drawing.PointF]::new($cursor, 0), $format)
                    $bounds = $glyph.GetBounds()
                    $outline.AddPath($glyph, $false)
                    $cursor = $bounds.Right + 1.2
                } finally { $glyph.Dispose() }
            }
            $cursor += $part.Gap
        } finally { $family.Dispose() }
    }
    $bounds = $outline.GetBounds()
    $matrix = [Drawing.Drawing2D.Matrix]::new()
    try {
        $matrix.Translate(-$bounds.X + 1, -$bounds.Y + 3)
        $outline.Transform($matrix)
    } finally { $matrix.Dispose() }
    $points = $outline.PathPoints
    $types = $outline.PathTypes
    $commands = [Collections.Generic.List[string]]::new()
    function Point-Text($p) { $p.X.ToString('0.###', $culture) + ' ' + $p.Y.ToString('0.###', $culture) }
    for ($i = 0; $i -lt $points.Length; $i++) {
        $kind = $types[$i] -band 7
        if ($kind -eq 0) { $commands.Add('M' + (Point-Text $points[$i])) }
        elseif ($kind -eq 1) { $commands.Add('L' + (Point-Text $points[$i])) }
        elseif ($kind -eq 3) {
            $commands.Add('C' + (Point-Text $points[$i]) + ' ' + (Point-Text $points[$i + 1]) + ' ' + (Point-Text $points[$i + 2]))
            $i += 2
        }
        if (($types[$i] -band 128) -ne 0) { $commands.Add('Z') }
    }
    $width = ($bounds.Width + 2).ToString('0.###', $culture)
    $height = ($bounds.Height + 6).ToString('0.###', $culture)
    $svg = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ' + $width + ' ' + $height + '"><title>Agent CF</title><path fill="#292631" fill-rule="nonzero" d="' + ($commands -join ' ') + '"/></svg>'
    $destination = Join-Path $PSScriptRoot '../public/logos/agent-cf-wordmark.svg'
    [IO.File]::WriteAllText($destination, $svg + "`n", [Text.UTF8Encoding]::new($false))
} finally {
    $format.Dispose()
    $outline.Dispose()
}
