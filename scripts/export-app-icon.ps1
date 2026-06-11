# Rasterize assets/icons/app-icon.svg to app-icon-1024.png (no pip / npm deps).
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Svg = Join-Path $Root "assets\icons\app-icon.svg"
$Out = Join-Path $Root "assets\icons\app-icon-1024.png"

if (-not (Test-Path $Svg)) {
    Write-Error "Missing $Svg"
}

# Prefer ImageMagick when available (faithful SVG render).
$magick = Get-Command magick -ErrorAction SilentlyContinue
if ($magick) {
    & magick -background none -density 384 $Svg -resize 1024x1024 $Out
    Write-Host "Exported (ImageMagick) $Out"
    exit 0
}

Add-Type -AssemblyName System.Drawing

$size = 1024
$s = $size / 256.0
function S([double]$v) { [int][Math]::Round($v * $s) }
function New-Color([int]$r, [int]$g, [int]$b, [int]$a = 255) {
    [System.Drawing.Color]::FromArgb($a, $r, $g, $b)
}

$bmp = New-Object System.Drawing.Bitmap $size, $size
$g = [System.Drawing.Graphics]::FromImage($bmp)
$g.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias
$g.Clear((New-Color 10 15 31))

# Background gradient (matches SVG #5a78f0 -> #32c8ee)
$bg = New-Object System.Drawing.Drawing2D.LinearGradientBrush (
    [System.Drawing.Point]::new((S 32), (S 24)),
    [System.Drawing.Point]::new((S 224), (S 232)),
    (New-Color 90 120 240),
    (New-Color 50 200 238)
)
$round = New-Object System.Drawing.Drawing2D.GraphicsPath
$r = S 56
$round.AddArc(0, 0, $r * 2, $r * 2, 180, 90)
$round.AddArc($size - $r * 2, 0, $r * 2, $r * 2, 270, 90)
$round.AddArc($size - $r * 2, $size - $r * 2, $r * 2, $r * 2, 0, 90)
$round.AddArc(0, $size - $r * 2, $r * 2, $r * 2, 90, 90)
$round.CloseFigure()
$g.FillPath($bg, $round)

# Halo
$g.FillEllipse((New-Object System.Drawing.SolidBrush (New-Color 255 255 255 36)), (S 40), (S 36), (S 176), (S 176))

# Face
$face = New-Object System.Drawing.Drawing2D.LinearGradientBrush (
    [System.Drawing.Point]::new((S 88), (S 72)),
    [System.Drawing.Point]::new((S 168), (S 188)),
    (New-Color 245 230 220),
    (New-Color 196 160 144)
)
$fx = S 44
$fy = S 30
$fw = S 168
$fh = S 184
$g.FillEllipse($face, $fx, $fy, $fw, $fh)
$stroke = S 2
$g.DrawEllipse((New-Object System.Drawing.Pen (New-Color 255 255 255 56), $stroke), $fx, $fy, $fw, $fh)

# Eye whites
$g.FillEllipse([System.Drawing.Brushes]::White, (S 76), (S 98), (S 36), (S 20))
$g.FillEllipse([System.Drawing.Brushes]::White, (S 144), (S 98), (S 36), (S 20))

# Irises
$iris = New-Object System.Drawing.SolidBrush (New-Color 74 114 184)
$g.FillEllipse($iris, (S 84), (S 101), (S 18), (S 18))
$g.FillEllipse($iris, (S 154), (S 101), (S 18), (S 18))

# Highlights
$hi = New-Object System.Drawing.SolidBrush ([System.Drawing.Color]::White)
$g.FillEllipse($hi, (S 86), (S 103), (S 6), (S 6))
$g.FillEllipse($hi, (S 156), (S 103), (S 6), (S 6))

# Mouth
$penMouth = New-Object System.Drawing.Pen (New-Color 168 90 106), (S 4)
$penMouth.StartCap = [System.Drawing.Drawing2D.LineCap]::Round
$penMouth.EndCap = [System.Drawing.Drawing2D.LineCap]::Round
$g.DrawBezier($penMouth, (S 100), (S 150), (S 114), (S 158), (S 142), (S 158), (S 156), (S 142))

# Lip shine
$g.FillEllipse((New-Object System.Drawing.SolidBrush (New-Color 255 255 255 56)), (S 110), (S 148), (S 36), (S 8))

$bmp.Save($Out, [System.Drawing.Imaging.ImageFormat]::Png)
$g.Dispose(); $bmp.Dispose(); $bg.Dispose(); $round.Dispose()

Write-Host "Exported $Out"
