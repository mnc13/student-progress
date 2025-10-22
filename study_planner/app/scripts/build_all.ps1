# app/scripts/build_all.ps1
Param(
  [string]$PythonBin = "python",
  # Optional overrides (fall back to env vars, then to hard defaults)
  [string]$ChunkSize,
  [string]$ChunkOverlap,
  [string]$CrossPageOverlap,
  [string]$BatchMaxChunks,
  [string]$PreviewLen
)

$ROOT = Split-Path -Parent $MyInvocation.MyCommand.Path

# --- Resolve defaults (param > env > hard default) ---
if (-not $ChunkSize)        { $ChunkSize        = $env:CHUNK_SIZE        }
if (-not $ChunkOverlap)     { $ChunkOverlap     = $env:CHUNK_OVERLAP     }
if (-not $CrossPageOverlap) { $CrossPageOverlap = $env:CROSS_PAGE_OVERLAP}
if (-not $BatchMaxChunks)   { $BatchMaxChunks   = $env:BATCH_MAX_CHUNKS  }
if (-not $PreviewLen)       { $PreviewLen       = $env:PREVIEW_LEN       }

if (-not $ChunkSize)        { $ChunkSize        = "1600" }
if (-not $ChunkOverlap)     { $ChunkOverlap     = "15%" }  # can be "200" or "15%"
if (-not $CrossPageOverlap) { $CrossPageOverlap = "1"    } # 1=true, 0=false
if (-not $BatchMaxChunks)   { $BatchMaxChunks   = "800"  }
if (-not $PreviewLen)       { $PreviewLen       = "240"  }

# Export as env vars so the Python script picks them up
$env:CHUNK_SIZE         = $ChunkSize
$env:CHUNK_OVERLAP      = $ChunkOverlap
$env:CROSS_PAGE_OVERLAP = $CrossPageOverlap
$env:BATCH_MAX_CHUNKS   = $BatchMaxChunks
$env:PREVIEW_LEN        = $PreviewLen

function Build($name, $pdf) {
  $out = Join-Path $ROOT ("data\" + $name)
  New-Item -ItemType Directory -Force -Path $out | Out-Null
  Write-Host "[BUILD] $name -> $out"
  & $PythonBin (Join-Path $ROOT "build_vector_store.py") --pdf $pdf --out $out
  if ($LASTEXITCODE -ne 0) {
    throw "Build failed for $name"
  }
}

Build "anatomy"            (Join-Path $ROOT "anatomy.pdf")
Build "physiology"         (Join-Path $ROOT "physiology.pdf")
Build "biochemistry"       (Join-Path $ROOT "biochemistry.pdf")
Build "pharmacology"       (Join-Path $ROOT "pharmacology.pdf")
Build "forensic_medicine"  (Join-Path $ROOT "forensic_medicine.pdf")

Write-Host "[DONE] All stores built."



#powershell -ExecutionPolicy Bypass -File app\scripts\build_all.ps1 `   -ChunkOverlap "20%" -CrossPageOverlap "1" -ChunkSize "1600"
