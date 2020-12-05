#!/bin/bash
datasette \
	-m regmem-deploy/metadata.yml \
	--template-dir=regmem-deploy/templates/ \
	regmem.db \
	-p 8002
