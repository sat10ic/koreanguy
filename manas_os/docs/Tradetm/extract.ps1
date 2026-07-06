[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$start = [int]$args[0]
$len = [int]$args[1]
$content = Get-Content -Path 'c:\Users\satta\Downloads\book\momentum-project\book\Tradetm\trading system.txt' -Encoding UTF8 -Raw
$end = [Math]::Min($start + $len, $content.Length)
$chunk = $content.Substring($start, $end - $start)
[System.IO.File]::WriteAllText('c:\Users\satta\Downloads\book\momentum-project\book\Tradetm\chunk_out.txt', $chunk, [System.Text.Encoding]::UTF8)
Write-Output "Done. Wrote $($end - $start) chars."
