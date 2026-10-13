# Writes the Main Gate pavilion sign face (green board, white bilingual lettering) as a PNG texture
# for generators/main_gate_pavilion.py. Uses WPF (DirectWrite), which shapes Bengali correctly;
# Pillow on this machine has no complex-text layout (raqm).
#
# Run from the project root (Windows PowerShell 5.1):
#   powershell -NoProfile -ExecutionPolicy Bypass -File assets/source/blender/tools/main_gate_sign_texture.ps1
#
# Text and layout follow Docs/map-reference/area1/mainGate.jpg: English line on top in serif capitals,
# Bengali line below, both in off-white on dark green, filling the board width.

param(
    [string]$Out = "assets/source/blender/textures/main_gate_sign.png",
    [int]$Width = 4096,
    [int]$Height = 727
)

Add-Type -AssemblyName PresentationCore, PresentationFramework, WindowsBase

$english = "ISLAMIC UNIVERSITY OF TECHNOLOGY"
$bengali = [string]::new([char[]](
    0x0987, 0x09B8, 0x09B2, 0x09BE, 0x09AE, 0x09BF, 0x0995, 0x0020,
    0x0987, 0x0989, 0x09A8, 0x09BF, 0x09AD, 0x09BE, 0x09B0, 0x09CD, 0x09B8, 0x09BF, 0x099F, 0x09BF, 0x0020,
    0x0985, 0x09AC, 0x0020,
    0x099F, 0x09C7, 0x0995, 0x09A8, 0x09CB, 0x09B2, 0x099C, 0x09C0))

$green = [System.Windows.Media.Color]::FromRgb(28, 78, 60)
$edge = [System.Windows.Media.Color]::FromRgb(18, 52, 40)
$ink = [System.Windows.Media.Color]::FromRgb(244, 241, 230)
$ltr = [System.Windows.FlowDirection]::LeftToRight

function New-Text([string]$text, [string]$family, $weight, [double]$size, [string]$lang) {
    $face = [System.Windows.Media.Typeface]::new(
        [System.Windows.Media.FontFamily]::new($family),
        [System.Windows.FontStyles]::Normal, $weight, [System.Windows.FontStretches]::Normal)
    $brush = [System.Windows.Media.SolidColorBrush]::new($ink)
    return [System.Windows.Media.FormattedText]::new($text, [System.Globalization.CultureInfo]::GetCultureInfo($lang),
        $ltr, $face, $size, $brush, 1.0)
}

function Fit-Text([string]$text, [string]$family, [string]$lang, [double]$width) {
    $bold = [System.Windows.FontWeights]::Bold
    $probe = New-Text $text $family $bold 100 $lang
    return New-Text $text $family $bold (100 * $width / $probe.Width) $lang
}

# Each line fills the board width (as in the photo); both shrink together if they overflow the height.
$gap = $Height * 0.04
$avail = $Height * 0.90
$targetW = $Width * 0.93
$en = Fit-Text $english "Times New Roman" "en-US" $targetW
$bn = Fit-Text $bengali "Nirmala UI" "bn-BD" $targetW
$total = $en.Height + $gap + $bn.Height
if ($total -gt $avail) {
    $k = $avail / $total
    $en = Fit-Text $english "Times New Roman" "en-US" ($targetW * $k)
    $bn = Fit-Text $bengali "Nirmala UI" "bn-BD" ($targetW * $k)
    $total = $en.Height + $gap + $bn.Height
}

$visual = [System.Windows.Media.DrawingVisual]::new()
$dc = $visual.RenderOpen()
$dc.DrawRectangle([System.Windows.Media.SolidColorBrush]::new($green), $null,
    [System.Windows.Rect]::new(0, 0, $Width, $Height))
$border = [System.Windows.Media.Pen]::new([System.Windows.Media.SolidColorBrush]::new($edge), $Height * 0.035)
$dc.DrawRectangle($null, $border, [System.Windows.Rect]::new(0, 0, $Width, $Height))
$top = ($Height - $total) / 2.0
$dc.DrawText($en, [System.Windows.Point]::new(($Width - $en.Width) / 2.0, $top))
$dc.DrawText($bn, [System.Windows.Point]::new(($Width - $bn.Width) / 2.0, $top + $en.Height + $gap))
$dc.Close()

$bmp = [System.Windows.Media.Imaging.RenderTargetBitmap]::new($Width, $Height, 96, 96,
    [System.Windows.Media.PixelFormats]::Pbgra32)
$bmp.Render($visual)
$enc = [System.Windows.Media.Imaging.PngBitmapEncoder]::new()
$enc.Frames.Add([System.Windows.Media.Imaging.BitmapFrame]::Create($bmp))
$path = [System.IO.Path]::GetFullPath((Join-Path (Get-Location) $Out))
[System.IO.Directory]::CreateDirectory([System.IO.Path]::GetDirectoryName($path)) | Out-Null
$fs = [System.IO.File]::Create($path)
$enc.Save($fs)
$fs.Close()
"[SIGN] wrote $path ($Width x $Height): English $([math]::Round($en.Width)) px wide, Bengali $([math]::Round($bn.Width)) px wide, lines $([math]::Round($en.Height))/$([math]::Round($bn.Height)) px"
