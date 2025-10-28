@echo off
chcp 65001 >nul
echo ============================================================
echo VSPreview 存储文件修复工具
echo ============================================================
echo.

REM 删除旧的存储文件
if exist ".vsjet\vspreview\*.yml" (
    echo 发现旧的存储文件，正在删除...
    
    REM 创建备份目录
    if not exist ".vsjet\vspreview\backup" mkdir ".vsjet\vspreview\backup"
    
    REM 备份文件
    copy ".vsjet\vspreview\*.yml" ".vsjet\vspreview\backup\" >nul 2>&1
    echo ✓ 已备份到 .vsjet\vspreview\backup\
    
    REM 删除文件
    del /q ".vsjet\vspreview\*.yml" >nul 2>&1
    echo ✓ 已删除旧的存储文件
) else (
    echo ✓ 未发现旧的存储文件
)

echo.
echo ============================================================
echo 关于 AvsCompat.dll 重复加载警告
echo ============================================================
echo.
echo 检测到 AvsCompat.dll 在两个位置:
echo   1. C:\Users\admin\AppData\Roaming\VapourSynth\plugins64\
echo   2. E:/MyProjects/vapoursynth/vs/VapourSynth/core/plugins/
echo.
echo 这只是警告，不影响功能。如需解决，可以删除其中一个副本。
echo.
echo 建议删除用户目录中的副本:
echo   del "C:\Users\admin\AppData\Roaming\VapourSynth\plugins64\AvsCompat.dll"
echo.

echo ============================================================
echo 修复完成！
echo ============================================================
echo.
echo 现在可以重新启动 VSPreview 了
echo.
pause

