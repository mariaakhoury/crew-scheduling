# Merge the three slide files into slides/slides_groupM.pptx and slides/slides_groupM.pdf (task C, needs PowerPoint).
#   powershell -ExecutionPolicy Bypass -File slides\merge_deck.ps1
# Order (Master Plan §12): A 1-5, B 6-9, C 10-12, B 13, C 14. A's file is the base (its title slide has its own
# layout); B's and C's slides are inserted with their speaker notes. Re-run after anyone changes their .pptx.
$ErrorActionPreference = "Stop"
$dir = Split-Path -Parent $MyInvocation.MyCommand.Path
$A = Join-Path $dir "slides_A.pptx"; $B = Join-Path $dir "slides_B.pptx"; $C = Join-Path $dir "slides_C.pptx"
$outPptx = Join-Path $dir "slides_groupM.pptx"; $outPdf = Join-Path $dir "slides_groupM.pdf"

$app = New-Object -ComObject PowerPoint.Application
try {
    $deck = $app.Presentations.Open($A, $true, $true, $false)          # read-only, untitled copy, no window
    if ($deck.Slides.Count -ne 5) { throw "slides_A.pptx should have 5 slides, has $($deck.Slides.Count)" }
    # InsertFromFile(file, insert after index, first, last)
    $null = $deck.Slides.InsertFromFile($B, 5, 1, 4)                   # B slides 6-9
    $null = $deck.Slides.InsertFromFile($C, 9, 1, 3)                   # C slides 10-12
    $null = $deck.Slides.InsertFromFile($B, 12, 5, 5)                  # B slide 13
    $null = $deck.Slides.InsertFromFile($C, 13, 4, 4)                  # C slide 14
    if ($deck.Slides.Count -ne 14) { throw "merged deck has $($deck.Slides.Count) slides, expected 14" }
    $deck.SaveAs($outPptx, 24)                                          # ppSaveAsOpenXMLPresentation
    $deck.SaveAs($outPdf, 32)                                           # ppSaveAsPDF
    $deck.Close()
    Write-Output "wrote $outPptx and $outPdf (14 slides)"
} finally {
    $app.Quit()
}
