rsync -az --progress --exclude '.svn' --exclude 'tmp/' \
    --relative data.theyworkforyou.com::parldata/scrapedxml/regmem .
