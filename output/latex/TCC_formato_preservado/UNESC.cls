%==========================================================================
% Identificação
%==========================================================================
\NeedsTeXFormat{LaTeX2e}

%==========================================================================
% Declarações preliminares
%==========================================================================
\DeclareOption*{\PassOptionsToClass{\CurrentOption}{article}}
\ProcessOptions\relax
\LoadClass[12pt]{article}
\RequirePackage{times,fancyhdr}

% \renewcommand{\normalsize}{\@setfontsize\normalsize\@xiipt\@xivpt}


%==========================================================================
% Margens e tamanho da página
%==========================================================================
\usepackage[
top    = 3cm,
bottom = 2cm,
left   = 3cm,
right  = 2cm]{geometry}
\geometry{papersize={190mm,290mm},total={160mm,230mm}}
%\setlength{\oddsidemargin}{2.5cm}
\setlength{\headheight}{\baselineskip}
%\setlength{\topmargin}{3cm}
%\setlength{\headsep}{2cm}\addtolength{\headsep}{-\headheight}
\setlength{\footskip}{1cm}\addtolength{\footskip}{.5\baselineskip}
%\addtolength{\topmargin}{-1in}
%\addtolength{\oddsidemargin}{-1in}
%\setlength{\evensidemargin}{\oddsidemargin}

%==========================================================================
% Definições diversas
%==========================================================================
\setlength{\parindent}{2cm}
%\setlength{\parskip}{.21cm \@plus \p@}
\newcommand{\abstractinenglishname}{ABSTRACT}
\newcommand{\keywordsportugues}{Palavras-chave}
\newcommand{\keywordsenglishname}{Keywords}

%==========================================================================
% Cabeçalho e rodapé
%==========================================================================
% \ps@fancy{
% \fancyhead{} \fancyfoot{}
% \fancyfoot[R]{\thepage} %\cfoot{}
% \fancyfoot[L]{}
% }
% \renewcommand\footrulewidth{0.4pt}
% \renewcommand\headrulewidth{0pt}
% \pagestyle{fancy}

%==========================================================================
% Título
%==========================================================================
\renewcommand{\maketitle}{%
	\thispagestyle{empty}%
	\begin{center}
        \noindent{\textbf{\@title}\par}
        \vspace{0.8cm}
	{\let\and\\\@author}
        \vspace{0.8cm}
	\end{center}
}

%==========================================================================
% Resumo (abstract) e Abstract (englishabstract)
%==========================================================================
\renewenvironment{abstract}{%
        \begin{center}
	\begin{minipage}{14cm}
	{\textbf{\abstractname:}}
}{
        \end{minipage}
	\end{center}
}

\newenvironment{abstractinenglish}{
        \def\abstractname{\abstractinenglishname}
	\begin{abstract}
}{
        \end{abstract}
}

%==========================================================================
% Palavras-chave (keywords) e Keywords (keywordsenglish)
%==========================================================================
\newenvironment{keywords}{
        \def\abstractname{{\keywordsportugues}}
	\begin{abstract}
}{
        \end{abstract}
}

\newenvironment{keywordsenglish}{
        \def\abstractname{{\keywordsenglishname}}
	\begin{abstract}
}{
        \end{abstract}
}

%==========================================================================
% Formatação das seções
%==========================================================================
\renewcommand{\section}{%
	\@startsection{section}{1}{0pt}{.49cm}{.21cm}
		      {\reset@font\bfseries\MakeUppercase}%
}
\renewcommand{\subsection}{%
	\@startsection{subsection}{2}{0pt}{.42cm}{.07cm}{\reset@font\MakeUppercase}%
}
\renewcommand{\subsubsection}{%
	\@startsection{subsubsection}{3}{0pt}{.28cm}{.07cm}
		      {\reset@font\bfseries}%
}
\renewcommand{\paragraph}{%
	\@startsection{paragraph}{4}{0pt}{.28cm}{-1em}{\reset@font\itshape}%
}



%==========================================================================
% Formatação das legendas de figuras e tabelas
%==========================================================================

\long\def\@makecaption#1#2{%
  \vskip\abovecaptionskip
  \sbox\@tempboxa{\normalfont\bfseries #1\ - \normalfont #2}%
  \ifdim \wd\@tempboxa >\hsize
    \normalfont\bfseries #1\ - \normalfont #2\par
  \else
    \global \@minipagefalse
    \hb@xt@\hsize{\hfil\box\@tempboxa\hfil}%
  \fi
  \vskip\belowcaptionskip}

%==========================================================================
% Formatação das notas de rodapé
%==========================================================================
\renewcommand\@makefntext[1]{%
       \parbox[t]{\textwidth}{\mbox{\@makefnmark}#1}
}
