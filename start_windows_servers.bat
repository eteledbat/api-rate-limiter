@echo off
:: filepath: /start_windows_servers.bat
echo 🪟 启动Windows优化的分布式Rate Limiter...

echo 启动第一个节点 (端口 8003)...
start "Rate Limiter Node 1" cmd /c "uvicorn app.main:app --host 0.0.0.0 --port 8003 --workers 2 --no-access-log"

timeout /t 3

echo 启动第二个节点 (端口 8004)...
start "Rate Limiter Node 2" cmd /c "uvicorn app.main:app --host 0.0.0.0 --port 8004 --workers 2 --no-access-log"

timeout /t 3

echo 启动第三个节点 (端口 8005)...
start "Rate Limiter Node 3" cmd /c "uvicorn app.main:app --host 0.0.0.0 --port 8005 --workers 2 --no-access-log"

echo.
echo ✅ 所有节点启动完成！
echo.
echo 测试URL:
echo   - http://127.0.0.1:8003/health
echo   - http://127.0.0.1:8004/health  
echo   - http://127.0.0.1:8005/health
echo.
echo 按任意键继续...
pause