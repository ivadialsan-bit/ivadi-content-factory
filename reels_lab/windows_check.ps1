$ErrorActionPreference = "Stop"
Write-Host "Reels Lab: Windows diagnostics (read-only)"
python --version
ffmpeg -version | Select-Object -First 1
ffprobe -version | Select-Object -First 1
try {
  nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader
} catch {
  Write-Host "No NVIDIA GPU detected; use Edge baseline or externally prepared voice WAVs."
}
Write-Host "No API tokens or server settings are required."
