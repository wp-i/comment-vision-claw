# 抖音热评抓取工具 - 一键安装脚本
# 使用方法：在PowerShell中运行以下命令
# iex ((New-Object System.Net.WebClient).DownloadString('https://raw.githubusercontent.com/YOUR_USERNAME/comment-vision-claw/main/install.ps1'))

$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  🎯 抖音热评智能抓取工具 - 一键安装" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 检查Python
try {
    $pythonVersion = python --version 2>&1
    Write-Host "✅ Python: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ 未检测到Python，请先安装Python 3.8+" -ForegroundColor Red
    Write-Host "下载地址: https://www.python.org/downloads/" -ForegroundColor Yellow
    exit 1
}

# 检查Git
try {
    $gitVersion = git --version 2>&1
    Write-Host "✅ $gitVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ 未检测到Git，请先安装Git" -ForegroundColor Red
    Write-Host "下载地址: https://git-scm.com/downloads" -ForegroundColor Yellow
    exit 1
}

# 设置安装目录
$installDir = "$env:USERPROFILE\Desktop\comment-vision-claw"

Write-Host ""
Write-Host "[1/5] 克隆项目..." -ForegroundColor Yellow
if (Test-Path $installDir) {
    Write-Host "项目已存在，跳过克隆" -ForegroundColor Gray
} else {
    git clone https://github.com/YOUR_USERNAME/comment-vision-claw.git $installDir
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ 克隆失败，请检查网络连接" -ForegroundColor Red
        exit 1
    }
}

Set-Location $installDir

Write-Host "[2/5] 安装项目依赖..." -ForegroundColor Yellow
pip install -r requirements.txt -q

Write-Host "[3/5] 检查MediaCrawler..." -ForegroundColor Yellow
if (-not (Test-Path "D:\MediaCrawler\main.py")) {
    Write-Host "正在安装MediaCrawler..." -ForegroundColor Yellow
    git clone https://github.com/NanmiCoder/MediaCrawler.git D:\MediaCrawler
    Set-Location D:\MediaCrawler
    pip install -r requirements.txt -q
    Set-Location $installDir
}

Write-Host "[4/5] 安装Playwright浏览器..." -ForegroundColor Yellow
playwright install chromium 2>$null

Write-Host "[5/5] 启动Web界面..." -ForegroundColor Yellow
Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  ✅ 安装完成！正在启动..." -ForegroundColor Green
Write-Host "  📌 浏览器会自动打开" -ForegroundColor Green
Write-Host "  📌 首次使用需扫码登录抖音" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""

Start-Sleep -Seconds 2
Start-Process "http://localhost:8501"
python -m streamlit run app.py --server.headless=true
