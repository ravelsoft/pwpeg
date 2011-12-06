"Vim syntax file
" Language:	Vim 7.2 script
" Filenames:    *.ini, .hgrc, */.hg/hgrc
" Maintainer:	Peter Hosey
" Last Change:	Nov 11, 2008
" Version:	7.2-02

" Quit when a syntax file was already loaded
if exists("b:current_syntax")
  finish
endif

runtime! syntax/jinja.vim
unlet! b:current_syntax

runtime! syntax/html.vim

let b:current_syntax = ''
unlet b:current_syntax
syntax include @PYTHON syntax/python.vim

syn match operator    /{\|}\|<\|>\|&\|!\||\|\[\|\]\|+\|\*\|,/

syn match commentRule "#.*$" contains=@NoSpell

syn match repetition /<\s*[0-9]\+\s*\(,\s*[0-9]\+\)\?\s*>/ contains=number,operator
syn match number /[0-9]\+/ contained

syn match  escapedRule '\\.'
"syn match   bigTagRule  '^@/\?[[:alnum:]_-]\+\(\s*\.[[:alnum:]_-]\+\|\s*#[[:alnum:]_-]\+\|\s*[[:alnum:]_-]\+=\"\(.\|\\\"\)*\"\)*' contains=tagRule,classRule,keyRule,idRule,valueRule,@NoSpell

"syn match   tagRule     '[^\\]@[a-zA-Z0-9_-]\+'ms=s+1 
"syn match   tagRule     '^@[a-zA-Z0-9_-]\+' 
syn match startingCode +%%\(\\%%\|\_.\)*%%+ contains=@PYTHON
syn match braceCode    +[&!]?\s*{\(\\}\|[^}]\)*}+ contains=bracePython
syn match bracePython  +{\(\\}\|[^}]\)*}+ contains=operator,@PYTHON

syn match oneLineCode  /->.*/ contains=@PYTHON

syn match severalLineCode /->[ \t]*\n\([ \t]\+\).*\n\(\1.*\n\|[ \t]*\n\)*/ contains=@PYTHON


syn match   string      '"\(\\"\|[^"]\)*"'
syn match   string      "'\(\\'\|[^']\)*'"
syn match   string      /\\[^ \t]*/
syn match   string      "/\(\\/\|[^/]\)*/[a-z]*"

syn match   rule        '[a-zA-Z_][a-zA-Z0-9_]*\s*='
syn match   pwlabel       '[[:alnum:]]\+:' contains=@NoSpell

"syn region  valueRule  start=+="+ms=s+1 end=+"+ skip=+\\"+ contained contains=@NoSpell,escapedRule,bigTagRule,variableRule
"syn region  valueRule  start=+='+ end=+'+ skip=+\\"+ contained contains=@NoSpell,escapedRule,bigTagRule,variableRule

" Highlighting Settings
" ====================
hi def link number Number
hi def link rule Function
hi def link operator Special
hi def link string String
" We don't want to confuse labels with python syntax
hi def link pwlabel Special
hi def link commentRule Comment
hi def link arrow Function

let b:current_syntax = "pweg"

