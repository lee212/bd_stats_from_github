#!/bin/bash
for i in `echo "geographic.yml healthcare.yml sentiment.yml warehousing.yml"`
do python search.py examples/$i
done

