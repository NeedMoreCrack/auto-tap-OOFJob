@echo off
chcp 65001 >nul

echo 啟動 Google Chrome...

"C:\Program Files\Google\Chrome\Application\chrome.exe" ^
    --remote-debugging-port=9222 ^
    --user-data-dir="C:\Users\User\selenium-chrome-profile" ^
    --disable-features=BackForwardCache
