# register-of-members-interests

https://register-of-members-interests.datasettes.com/

Code for parsing the mySociety Registers of Members Interest XML, turning it into SQLite and publishing it with Datasette

Needs data from http://data.mysociety.org/datasets/members-interest/

See https://simonwillison.net/2018/Apr/25/register-members-interests/ for background

The most efficient way to get the original data is via rsync:

    rsync -az --progress --exclude '.svn' --exclude 'tmp/' \
        --relative data.theyworkforyou.com::parldata/scrapedxml/regmem .
