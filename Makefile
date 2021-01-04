#
# Author: Markus Stenberg <fingon@iki.fi>
#
# Copyright (c) 2021 Markus Stenberg
#
# Created:       Mon Jan  4 09:07:59 2021 mstenber
# Last modified: Mon Jan  4 09:08:35 2021 mstenber
# Edit time:     1 min
#
#

.PHONY: pylint
.PHONY: test

all: pylint test

pylint:
	pylint $(wildcard *.py)

test:
	pytest
