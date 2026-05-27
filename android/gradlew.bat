@rem Windows Gradle wrapper launcher. Downloads gradle-wrapper.jar on first run.
@echo off
setlocal

set DIR=%~dp0
set WRAPPER_DIR=%DIR%gradle\wrapper
set WRAPPER_JAR=%WRAPPER_DIR%\gradle-wrapper.jar

if not exist "%WRAPPER_JAR%" (
    echo Downloading gradle-wrapper.jar...
    if not exist "%WRAPPER_DIR%" mkdir "%WRAPPER_DIR%"
    powershell -NoProfile -Command "Invoke-WebRequest -UseBasicParsing -Uri 'https://raw.githubusercontent.com/gradle/gradle/v8.7.0/gradle/wrapper/gradle-wrapper.jar' -OutFile '%WRAPPER_JAR%'"
    if errorlevel 1 (
        echo failed to fetch gradle-wrapper.jar
        exit /b 1
    )
)

set JAVA_EXE=java.exe
if defined JAVA_HOME set JAVA_EXE=%JAVA_HOME%\bin\java.exe

"%JAVA_EXE%" -classpath "%WRAPPER_JAR%" org.gradle.wrapper.GradleWrapperMain %*
exit /b %ERRORLEVEL%
