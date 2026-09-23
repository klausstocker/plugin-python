@echo off
setlocal EnableExtensions EnableDelayedExpansion
set "NO_PUSH="
set "TARGET="
:parse_args
if "%~1"=="" goto args_done
if /i "%~1"=="-NoPush" goto no_push_arg
if /i "%~1"=="--no-push" goto no_push_arg
if /i "%~1"=="--help" goto help
if /i "%~1"=="-Help" goto help
if /i "%~1"=="jobe" goto target_arg
if /i "%~1"=="plugin" goto target_arg
goto usage_error
:no_push_arg
set "NO_PUSH=1"
shift /1
goto parse_args
:target_arg
if defined TARGET goto usage_error
set "TARGET=%~1"
shift /1
goto parse_args
:args_done
set "SCRIPT_DIR=%~dp0"
set "PLUGIN_BUILD_HASH=unknown"
set "TAGS="
if not exist "%SCRIPT_DIR%.git" goto metadata_done
git -C "%SCRIPT_DIR%." rev-parse --verify HEAD >nul 2>&1
if errorlevel 1 goto failed
for /f "delims=" %%i in ('git -C "%SCRIPT_DIR%." rev-parse --short HEAD') do set "PLUGIN_BUILD_HASH=%%i"
rem CRLF output is required by FINDSTR /x. Validate before delayed expansion.
git -C "%SCRIPT_DIR%." tag --points-at HEAD --format="%%(refname:short)%%0d" | %SystemRoot%\System32\findstr.exe /r /v /x "[A-Za-z0-9_][A-Za-z0-9_.-]*" >nul
if not errorlevel 1 goto invalid_tag
for /f "delims=" %%i in ('git -C "%SCRIPT_DIR%." tag --points-at HEAD') do (
    set "IMAGE_TAG=%%i"
    if not "!IMAGE_TAG:~128!"=="" goto invalid_tag
    set "TAGS=!TAGS! %%i"
)
:metadata_done
if defined TAGS if not defined NO_PUSH (
    set "DIRTY="
    for /f "delims=" %%i in ('git -C "%SCRIPT_DIR%." status --porcelain --untracked-files^=normal') do set "DIRTY=1"
    if defined DIRTY (
        echo Publishing requires a clean checkout. Commit changes or use --no-push. >&2
        exit /b 1
    )
)
set "PLUGIN_IMAGE=klausstocker/letto-plugin-python"
set "JOBE_IMAGE=klausstocker/letto-plugin-python-jobe"
set "IMAGES=!PLUGIN_IMAGE! !JOBE_IMAGE!"
if /i "!TARGET!"=="plugin" set "IMAGES=!PLUGIN_IMAGE!"
if /i "!TARGET!"=="jobe" set "IMAGES=!JOBE_IMAGE!"
echo Building images with PLUGIN_BUILD_HASH=!PLUGIN_BUILD_HASH!
if /i "!TARGET!"=="jobe" goto build_jobe
docker build --build-arg "PLUGIN_BUILD_HASH=!PLUGIN_BUILD_HASH!" -t "!PLUGIN_IMAGE!:latest" -f "%SCRIPT_DIR%Dockerfile" "%SCRIPT_DIR%."
if errorlevel 1 goto failed
if /i "!TARGET!"=="plugin" goto tag_images
:build_jobe
docker build --build-arg "PLUGIN_BUILD_HASH=!PLUGIN_BUILD_HASH!" -t "!JOBE_IMAGE!:latest" -f "%SCRIPT_DIR%jobe\Dockerfile" "%SCRIPT_DIR%."
if errorlevel 1 goto failed
:tag_images
for %%t in (!TAGS!) do for %%i in (!IMAGES!) do (
    docker tag "%%i:latest" "%%i:%%t"
    if errorlevel 1 goto failed
)
if defined NO_PUSH goto local_only
for %%i in (!IMAGES!) do (
    docker push "%%i:latest"
    if errorlevel 1 goto failed
    for %%t in (!TAGS!) do if not "%%t"=="latest" (
        docker push "%%i:%%t"
        if errorlevel 1 goto failed
    )
)
exit /b 0
:local_only
echo Images built locally; publishing skipped.
exit /b 0
:failed
exit /b 1

:invalid_tag
echo A Git tag at HEAD is not a valid Docker tag. >&2
exit /b 1
:usage_error
call :help
exit /b 1
:help
echo Usage: build.bat [jobe^|plugin] [--no-push]
exit /b 0
