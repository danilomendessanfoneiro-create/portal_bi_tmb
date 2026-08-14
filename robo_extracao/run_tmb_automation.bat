@echo off
REM run_tmb_automation.bat
REM Executa o robo TMB. Pensado para ser chamado pelo Agendador de Tarefas
REM do Windows na inicializacao do computador.

cd /d "%~dp0"

REM Se estiver usando um ambiente virtual, ajuste o caminho abaixo:
REM call venv\Scripts\activate.bat

python tmb_automation.py

REM Mantem o codigo de saida do script Python para o Agendador de Tarefas
exit /b %ERRORLEVEL%
