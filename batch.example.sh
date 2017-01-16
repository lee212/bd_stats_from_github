#!/bin/bash
for i in `echo facedetection.yml  fingerprint.yml  geographic.yml  healthcare.yml  sentiment.yml  warehousing.yml`
do 
	python search.py examples/$i
done

