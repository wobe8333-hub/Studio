@echo off
chcp 65001 >nul
set PYTHONUTF8=1
cd /d "%~dp0\..\.."
set KNOWLEDGE_STEP4_BULK=1
set KNOWLEDGE_STEP4_MAX_VIDEOS=300
set KNOWLEDGE_STEP4_GLOBAL_MIN_CANDIDATES=2000
set KNOWLEDGE_STEP4_CAT_MIN=50
set KNOWLEDGE_STEP4_CAT_MAX=200
python -m backend.cli.run knowledge keyword-discovery --categories science,history,common_sense,economy,geography,papers --mode run --max-keywords 50
python -m backend.cli.run knowledge discovery-cycle --categories science,history,common_sense,economy,geography,papers --mode run --max-keywords 50
python -m backend.scripts.verify_step4_approval
python -m backend.scripts.verify_step2
python -m backend.scripts.verify_step3
exit /b %ERRORLEVEL%

