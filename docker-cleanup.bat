@echo off
setlocal EnableExtensions DisableDelayedExpansion
set "CONFIRMED="
if "%~1"=="--help" goto help
if "%~1"=="--yes" set "CONFIRMED=1"
if not "%~1"=="" if not defined CONFIRMED goto usage_error
if not "%~2"=="" goto usage_error
docker info >nul
if errorlevel 1 exit /b 1
echo WARNING: This affects ALL containers and images on the Docker engine targeted by your current Docker settings.
echo Containers and their writable data will be removed. Volumes and bind-mounted files are preserved.
echo All unused images and the selected builder cache will be deleted.
if defined CONFIRMED goto cleanup
set "ANSWER="
set /p "ANSWER=Type DELETE to continue: "
setlocal EnableDelayedExpansion
if "!ANSWER!"=="DELETE" goto cleanup
echo Cancelled.
exit /b 1

:cleanup
set "CONTAINER_LIST=%TEMP%\docker-cleanup-%RANDOM%-%RANDOM%.txt"
docker container ls --all --quiet --no-trunc >"%CONTAINER_LIST%"
if errorlevel 1 goto failed
for /f "usebackq delims=" %%i in ("%CONTAINER_LIST%") do (
    docker container stop "%%i"
    if errorlevel 1 goto failed
    docker container rm "%%i"
    if errorlevel 1 goto failed
)
del /q "%CONTAINER_LIST%"
set "CONTAINER_LIST="
docker image prune --all --force
if errorlevel 1 goto failed
docker builder prune --all --force
if errorlevel 1 goto failed
docker system df
if errorlevel 1 goto failed
echo Cleanup complete. Volumes and bind-mounted files were preserved.
exit /b 0

:failed
if defined CONTAINER_LIST del /q "%CONTAINER_LIST%" 2>nul
echo Cleanup failed. See the Docker error above. >&2
exit /b 1
:usage_error
call :help
exit /b 1
:help
echo Usage: docker-cleanup.bat [--yes]
exit /b 0
