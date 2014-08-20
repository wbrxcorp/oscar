all: lib.tar

test:
	cd src && python -m test.hogetest

web:
	cd src && PYTHONPATH=. python -m web

compile:
	python2.7 -m compileall -q .

src/web/static/js/oscar.min.js: src/web/static/js/oscar.js
	PYTHONPATH=lib python -c 'import sys,jsmin;print jsmin.jsmin(open(sys.argv[1]).read())' $< > $@

lib.tar: compile src/web/static/js/oscar.min.js
	tar cvf $@ --exclude='*.py' --exclude='*~' --exclude='test' --exclude='web/static/js/test' --exclude='oscar.js' -C src .

install: all
	mkdir -p /opt/oscar/etc /opt/oscar/lib /opt/oscar/bin
	tar xvf lib.tar -C /opt/oscar/lib
	cp -a bin/oscar bin/oscar.wsgi /opt/oscar/bin
	chown -R oscar /opt/oscar

