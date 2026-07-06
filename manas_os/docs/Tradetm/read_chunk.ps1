param([int]$start, [int]$len = 8000)
$t = [System.IO.File]::ReadAllText('c:\Users\satta\Downloads\book\momentum-project\book\Tradetm\trading system.txt')
$end = [Math]::Min($start + $len, $t.Length)
Write-Output $t.Substring($start, $end - $start)
