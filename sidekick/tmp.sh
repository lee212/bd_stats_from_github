#!/bin/bash
IFS=$'\n'
fn=$1
#fn='star_over_10k'
fname=$fn'.table.csv'
for i in `cat $fname`
do
	name=`echo $i|cut -f1 -d'&'|tr -d '[:space:]'`
	cnt=`grep "\"$name\"" $fn.stats.pack*|cut -d":" -f2|tr -d ','`
	echo $i|sed  -e "s/$name/$name \& $cnt/"
done
unset IFS
