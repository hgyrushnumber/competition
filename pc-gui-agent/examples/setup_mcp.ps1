# MCP 服务器快速配置脚本 (Windows PowerShell)
# 用于快速配置真实的 MCP 服务器

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "MCP 服务器快速配置" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 检查 Node.js 是否安装
$nodeInstalled = $false
try {
    $nodeVersion = node --version 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ 检测到 Node.js: $nodeVersion" -ForegroundColor Green
        $nodeInstalled = $true
    }
} catch {
    Write-Host "✗ 未检测到 Node.js" -ForegroundColor Yellow
}

# 检查 Python 是否安装
$pythonInstalled = $false
try {
    $pythonVersion = python --version 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ 检测到 Python: $pythonVersion" -ForegroundColor Green
        $pythonInstalled = $true
    }
} catch {
    Write-Host "✗ 未检测到 Python" -ForegroundColor Yellow
}

Write-Host ""

# 选择 MCP 服务器类型
Write-Host "请选择要配置的 MCP 服务器类型：" -ForegroundColor Yellow
Write-Host "1. Puppeteer MCP 服务器（推荐，支持浏览器控制）" -ForegroundColor White
Write-Host "2. Filesystem MCP 服务器（文件系统操作）" -ForegroundColor White
Write-Host "3. 自定义 MCP 服务器命令" -ForegroundColor White
Write-Host ""

$choice = Read-Host "请输入选项 (1-3)"

switch ($choice) {
    "1" {
        if (-not $nodeInstalled) {
            Write-Host "✗ 错误：Puppeteer MCP 服务器需要 Node.js" -ForegroundColor Red
            Write-Host "   请先安装 Node.js: https://nodejs.org/" -ForegroundColor Yellow
            exit 1
        }
        
        Write-Host ""
        Write-Host "配置 Puppeteer MCP 服务器..." -ForegroundColor Cyan
        
        # 设置环境变量
        $env:MCP_ENABLED = "true"
        $env:MCP_SERVER_COMMAND = "npx -y @modelcontextprotocol/server-puppeteer"
        
        Write-Host "✓ 已设置环境变量：" -ForegroundColor Green
        Write-Host "  MCP_ENABLED=$env:MCP_ENABLED" -ForegroundColor Gray
        Write-Host "  MCP_SERVER_COMMAND=$env:MCP_SERVER_COMMAND" -ForegroundColor Gray
        
        Write-Host ""
        Write-Host "提示：这些环境变量只在当前 PowerShell 会话中有效" -ForegroundColor Yellow
        Write-Host "如果要永久设置，请使用：" -ForegroundColor Yellow
        Write-Host "  [System.Environment]::SetEnvironmentVariable('MCP_ENABLED', 'true', 'User')" -ForegroundColor Gray
        Write-Host "  [System.Environment]::SetEnvironmentVariable('MCP_SERVER_COMMAND', 'npx -y @modelcontextprotocol/server-puppeteer', 'User')" -ForegroundColor Gray
    }
    
    "2" {
        if (-not $pythonInstalled) {
            Write-Host "✗ 错误：Filesystem MCP 服务器需要 Python" -ForegroundColor Red
            Write-Host "   请先安装 Python: https://www.python.org/" -ForegroundColor Yellow
            exit 1
        }
        
        Write-Host ""
        Write-Host "配置 Filesystem MCP 服务器..." -ForegroundColor Cyan
        
        # 检查是否安装了 mcp 包
        $mcpInstalled = $false
        try {
            python -m mcp.server.filesystem --help 2>$null | Out-Null
            if ($LASTEXITCODE -eq 0) {
                $mcpInstalled = $true
            }
        } catch {
            # 尝试导入检查
            $mcpCheck = python -c "import mcp; print('OK')" 2>$null
            if ($LASTEXITCODE -eq 0) {
                $mcpInstalled = $true
            }
        }
        
        if (-not $mcpInstalled) {
            Write-Host "⚠️  未检测到 mcp 包，正在尝试安装..." -ForegroundColor Yellow
            pip install mcp
            if ($LASTEXITCODE -ne 0) {
                Write-Host "✗ 安装失败，请手动运行: pip install mcp" -ForegroundColor Red
                exit 1
            }
            Write-Host "✓ mcp 包安装成功" -ForegroundColor Green
        }
        
        # 设置环境变量
        $env:MCP_ENABLED = "true"
        $env:MCP_SERVER_COMMAND = "python -m mcp.server.filesystem"
        
        Write-Host "✓ 已设置环境变量：" -ForegroundColor Green
        Write-Host "  MCP_ENABLED=$env:MCP_ENABLED" -ForegroundColor Gray
        Write-Host "  MCP_SERVER_COMMAND=$env:MCP_SERVER_COMMAND" -ForegroundColor Gray
        
        Write-Host ""
        Write-Host "提示：这些环境变量只在当前 PowerShell 会话中有效" -ForegroundColor Yellow
        Write-Host "如果要永久设置，请使用：" -ForegroundColor Yellow
        Write-Host "  [System.Environment]::SetEnvironmentVariable('MCP_ENABLED', 'true', 'User')" -ForegroundColor Gray
        Write-Host "  [System.Environment]::SetEnvironmentVariable('MCP_SERVER_COMMAND', 'python -m mcp.server.filesystem', 'User')" -ForegroundColor Gray
    }
    
    "3" {
        Write-Host ""
        Write-Host "请输入自定义 MCP 服务器命令：" -ForegroundColor Cyan
        $customCommand = Read-Host "命令"
        
        if ([string]::IsNullOrWhiteSpace($customCommand)) {
            Write-Host "✗ 错误：命令不能为空" -ForegroundColor Red
            exit 1
        }
        
        # 设置环境变量
        $env:MCP_ENABLED = "true"
        $env:MCP_SERVER_COMMAND = $customCommand
        
        Write-Host "✓ 已设置环境变量：" -ForegroundColor Green
        Write-Host "  MCP_ENABLED=$env:MCP_ENABLED" -ForegroundColor Gray
        Write-Host "  MCP_SERVER_COMMAND=$env:MCP_SERVER_COMMAND" -ForegroundColor Gray
    }
    
    default {
        Write-Host "✗ 无效的选项" -ForegroundColor Red
        exit 1
    }
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "配置完成！" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "现在可以运行测试脚本：" -ForegroundColor Yellow
Write-Host "  python examples/test_browser_apps.py" -ForegroundColor White
Write-Host ""

