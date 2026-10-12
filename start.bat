@echo off
chcp 65001 > nul
echo ===== 策澜量化竞技场 =====
echo 管理员 admin/admin123  投资者 trader01~05/123456（模拟资金100万）
echo 启动后访问 http://127.0.0.1:8002
cd /d "%~dp0backend"
if not exist quant.db python seed.py
python -m uvicorn app.main:app --port 8002
