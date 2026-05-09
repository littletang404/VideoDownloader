@echo off
chcp 65001 >nul
echo ========================================
echo   VideoDownloader 打包脚本
echo ========================================
echo.

REM 保存原始目录
set PROJECT_ROOT=%CD%

REM 创建输出目录
if not exist "release" mkdir release

REM 安装 PyInstaller（如果未安装）
pip show pyinstaller >nul 2>&1
if %errorlevel% neq 0 (
    echo 正在安装 PyInstaller...
    pip install pyinstaller
)

echo.
echo 正在打包，请稍候...
echo.

REM 打包为单个exe文件，输出到 release 目录
pyinstaller --onefile --noconfirm ^
    --distpath release ^
    --workpath release\build ^
    --specpath release ^
    --name VideoDownloader ^
    main.py

echo.
if exist "release\VideoDownloader.exe" (
    echo ========================================
    echo   打包成功！
    echo   输出文件: release\VideoDownloader.exe
    echo ========================================
    echo.
    echo 正在复制必要文件...
    xcopy /e /y "tools" "release\tools\" >nul 2>&1
    xcopy /e /y "cookies" "release\cookies\" >nul 2>&1
    xcopy /e /y "config" "release\config\" >nul 2>&1
    echo 复制完成！请将 release 目录下的所有文件一起分发。
) else (
    echo 打包失败，请检查错误信息
)

pause