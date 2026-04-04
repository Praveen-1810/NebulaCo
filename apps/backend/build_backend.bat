@echo off
echo Building Nebula Backend EXE...

pyinstaller ^
  --onefile ^
  --noconsole ^
  --name nebula_backend ^
  nebula/main.py

echo Build complete.
pause
