#!/bin/bash

# echo "username: $1"
# echo "password: $2"
# echo "filename:  $3"
# echo "tag:          $4"

u="$1"
p="$2"
f="$3"
t="$4"

#echo $f"1"

instapy -u $u -p $p -f $f"1.jpg" -t "$t"
instapy -u $u -p $p -f $f"2.jpg" -t "$t"
instapy -u $u -p $p -f $f"3.jpg" -t "$t"
