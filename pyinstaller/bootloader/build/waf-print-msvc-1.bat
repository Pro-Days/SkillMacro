@echo off
set INCLUDE=
set LIB=
call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvarsall.bat" x64
echo PATH=%PATH%
echo INCLUDE=%INCLUDE%
echo LIB=%LIB%;%LIBPATH%
