@echo off
setlocal EnableExtensions
chcp 65001 >nul
cd /d "%~dp0"

echo ========================================
echo   万能视频下载器 - Windows 构建
echo ========================================

python -c "import PyInstaller" >nul 2>&1
if errorlevel 1 (
    echo 正在安装 PyInstaller...
    python -m pip install "pyinstaller>=6.0"
    if errorlevel 1 goto :failed
)

python -m PyInstaller --noconfirm --clean --distpath dist --workpath build\pyinstaller VideoDownloader.spec
if errorlevel 1 goto :failed

if not exist "dist\tools" mkdir "dist\tools"

set "FFMPEG_SOURCE="
if exist "tools\ffmpeg\bin\ffmpeg.exe" set "FFMPEG_SOURCE=tools\ffmpeg\bin"
for /d %%D in ("tools\ffmpeg_full\*") do (
    if exist "%%~fD\bin\ffmpeg.exe" set "FFMPEG_SOURCE=%%~fD\bin"
)

if defined FFMPEG_SOURCE (
    copy /y "%FFMPEG_SOURCE%\ffmpeg.exe" "dist\tools\ffmpeg.exe" >nul
    if exist "%FFMPEG_SOURCE%\ffprobe.exe" copy /y "%FFMPEG_SOURCE%\ffprobe.exe" "dist\tools\ffprobe.exe" >nul
    echo 已复制 ffmpeg / ffprobe
) else (
    echo [提示] 未找到可打包的 ffmpeg。用户可在设置中选择系统 ffmpeg。
)

if exist "%USERPROFILE%\.deno\bin\deno.exe" copy /y "%USERPROFILE%\.deno\bin\deno.exe" "dist\tools\deno.exe" >nul
if exist "tools\deno\deno.exe" copy /y "tools\deno\deno.exe" "dist\tools\deno.exe" >nul
if exist "tools\deno.exe" copy /y "tools\deno.exe" "dist\tools\deno.exe" >nul

echo.
echo 构建完成：dist\VideoDownloader.exe
echo 用户 Cookie 和历史记录不会复制进发布包。
goto :end

:failed
echo.
echo 构建失败，请查看上方错误信息。
exit /b 1

:end
endlocal
