# Technical Appendix 

notebook requirements, notes on use of development branches, etc. 

## building this book 

https://jupyterbook.org/en/stable/advanced/pdf.html


```
$ pyenv virtualenv 3.10.11 yt_NASA_SMD
$ pyenv activate yt_NASA_SMD
```

from top level
```
$ pip install -r requirements.txt
$ jupyter-book build yt_xr_2024/ --builder pdflatex
$ cp yt_xr_2024/_build/pdf/book.pdf ./yt_xr_2024.pdf
```
