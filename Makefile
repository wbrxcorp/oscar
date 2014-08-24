all: oscar.tgz

test:
	cd src && python -m test.hogetest

web:
	cd src && PYTHONPATH=. python -m web

compile:
	python2.7 -m compileall -q src

src/web/static/js/oscar.min.js: src/web/static/js/oscar.js
	python -c 'import sys,jsmin;print jsmin.jsmin(open(sys.argv[1]).read())' $< > $@

lib.tar: compile src/web/static/js/oscar.min.js
	tar cvf $@ --exclude='*.py' --exclude='*~' --exclude='test' --exclude='web/static/js/test' --exclude='oscar.js' -C src .

oscar.tgz: lib.tar bin/oscar bin/oscar.wsgi
	mkdir -p lib
	tar xvf lib.tar -C lib
	tar zcvf $@ --exclude='src' --exclude='*~' bin lib

install: all
	mkdir -p /opt/oscar/etc
	tar zxvf oscar.tgz -C /opt/oscar

