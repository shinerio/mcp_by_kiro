@echo off
REM MCP Base64 Server Startup Script for Windows
REM This script provides a convenient way to start the server with different configurations

setlocal enabledelayedexpansion

REM Default values
set TRANSPORT=stdio
set ENABLE_HTTP_SERVER=false
set LOG_LEVEL=INFO
set CONFIG_FILE=config.yaml
set HTTP_PORT=
set MCP_PORT=

REM Parse command line arguments
:parse_args
if "%~1"=="" goto start_server
if "%~1"=="-t" (
    set TRANSPORT=%~2
    shift
    shift
    goto parse_args
)
if "%~1"=="--transport" (
    set TRANSPORT=%~2
    shift
    shift
    goto parse_args
)
if "%~1"=="-s" (
    set ENABLE_HTTP_SERVER=true
    shift
    goto parse_args
)
if "%~1"=="--enable-http-server" (
    set ENABLE_HTTP_SERVER=true
    shift
    goto parse_args
)
if "%~1"=="-l" (
    set LOG_LEVEL=%~2
    shift
    shift
    goto parse_args
)
if "%~1"=="--log-level" (
    set LOG_LEVEL=%~2
    shift
    shift
    goto parse_args
)
if "%~1"=="-c" (
    set CONFIG_FILE=%~2
    shift
    shift
    goto parse_args
)
if "%~1"=="--config" (
    set CONFIG_FILE=%~2
    shift
    shift
    goto parse_args
)
if "%~1"=="-p" (
    set HTTP_PORT=%~2
    shift
    shift
    goto parse_args
)
if "%~1"=="--http-port" (
    set HTTP_PORT=%~2
    shift
    shift
    goto parse_args
)
if "%~1"=="-m" (
    set MCP_PORT=%~2
    shift
    shift
    goto parse_args
)
if "%~1"=="--mcp-port" (
    set MCP_PORT=%~2
    shift
    shift
    goto parse_args
)
if "%~1"=="-h" goto show_help
if "%~1"=="--help" goto show_help

echo [ERROR] Unknown option: %~1
goto show_help

:show_help
echo Usage: %~nx0 [OPTIONS]
echo.
echo Options:
echo     -t, --transport TYPE        Transport type: stdio or http (default: stdio)
echo     -s, --enable-http-server    Enable standalone HTTP API server
echo     -l, --log-level LEVEL       Log level: DEBUG, INFO, WARNING, ERROR (default: INFO)
echo     -c, --config FILE           Configuration file path (default: config.yaml)
echo     -p, --http-port PORT        HTTP API server port (default: 8080)
echo     -m, --mcp-port PORT         MCP HTTP transport port (default: 3000)
echo     -h, --help                  Show this help message
echo.
echo Examples:
echo     %~nx0                          # Start with stdio transport
echo     %~nx0 -t http -s               # Start with HTTP transport and API server
echo     %~nx0 -t stdio -l DEBUG        # Start with stdio transport and debug logging
echo     %~nx0 -c custom-config.yaml    # Start with custom configuration file
echo.
exit /b 0

:start_server
REM Validate transport type
if not "%TRANSPORT%"=="stdio" if not "%TRANSPORT%"=="http" (
    echo [ERROR] Invalid transport type: %TRANSPORT%. Must be 'stdio' or 'http'
    exit /b 1
)

REM Check if configuration file exists
if not exist "%CONFIG_FILE%" (
    echo [ERROR] Configuration file not found: %CONFIG_FILE%
    exit /b 1
)

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH
    exit /b 1
)

REM Check if required Python packages are installed
echo [INFO] Checking Python dependencies...
python -c "import yaml, psutil, flask" >nul 2>&1
if errorlevel 1 (
    echo [WARNING] Some Python dependencies are missing. Installing...
    pip install -r requirements.txt
)

REM Create logs directory if it doesn't exist
if not exist logs mkdir logs

REM Build command line arguments
set ARGS=--transport %TRANSPORT% --log-level %LOG_LEVEL% --config %CONFIG_FILE%

if "%ENABLE_HTTP_SERVER%"=="true" (
    set ARGS=!ARGS! --enable-http-server
)

if not "%HTTP_PORT%"=="" (
    set ARGS=!ARGS! --http-server-port %HTTP_PORT%
)

if not "%MCP_PORT%"=="" (
    set ARGS=!ARGS! --http-port %MCP_PORT%
)

REM Print startup information
echo [INFO] Starting MCP Base64 Server...
echo [INFO] Transport: %TRANSPORT%
echo [INFO] HTTP Server: %ENABLE_HTTP_SERVER%
echo [INFO] Log Level: %LOG_LEVEL%
echo [INFO] Config File: %CONFIG_FILE%

REM Start the server
echo [INFO] Executing: python main.py %ARGS%
python main.py %ARGS%