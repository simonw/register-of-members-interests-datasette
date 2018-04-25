#!/bin/bash
datasette \
	-m regmem-deploy/metadata.json \
	--template-dir=regmem-deploy/templates/ \
	regmem.db \
	-p 8002
