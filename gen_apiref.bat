@echo off
set doxy="c:\_PROG_\Doxygen\doxygen.exe"
set doxydir="pycross\doc\apiref"
%doxy% "%doxydir%\doxyfile"
"%doxydir%\html\index.html"