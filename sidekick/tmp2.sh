#!/bin/bash
IFS=$'\n'
fn=$1
#fn='star_over_10k'
for line in `cat *.table.csv|grep hline|sort -u`
do
	#echo $line
	name=`echo $line|cut -f1 -d" "`
	IFS=$' '
	add=''
	for i in `echo star_over_10k analytics data_processing nosql streams`
	do
		cnt=`grep "\"$name\"" $i.stats.packages_in*|cut -d":" -f2|tr -d '[:space:]'|tr -d ','`
		dcnt=`grep Dockerfile $i.*.json|wc -l`
		#echo $name, $i, $cnt, $dcnt, `python -c "print \"{0:.1f}\".format(${cnt}.0 / $dcnt)"`
		val=`python -c "print \"{0:.2f}\".format(${cnt}.0 / $dcnt)"`
		add=$add" \& "$val
	done
	echo $line|sed -e "s/$name/$name $add/"
	IFS=$'\n'
done

