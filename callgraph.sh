#!/bin/sh

pycallgraph -ng --include "bvc.*" graphviz --output-file=bvc.png -- ./bin/check-buildout-updates && eog bvc.png