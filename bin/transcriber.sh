#!/bin/bash
###############################################################
### Transcriber one file
###############################################################
### takes the wav file as input
### passes it to the transcriber, 
### waits for the complete status
### the result is put into <input>.txt file
###############################################################
###############################################################
file=$1
###############################################################
source liepa_ausys.env
AUTH=$liepa_ausys_auth
url=$liepa_ausys_url
###############################################################
uploadURL="$url/transcriber/upload"
statusURL="$url/status.service/status"
resultURL="$url/result.service/result"
###############################################################
RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color
###############################################################

if [ -z "${liepa_ausys_auth}" ]; then
    echo "liepa_ausys_auth is not set in liepa_ausys.env"; exit 1;
fi

if [ -z "${liepa_ausys_url}" ]; then
    echo "liepa_ausys_url is not set in liepa_ausys.env" ; exit 1;
fi

###############################################################
echo "File: $file"
echo "Uploading..."
id=$(curl -X POST -k $uploadURL -H 'Accept: application/json' -H "Authorization: Basic $AUTH" -H 'content-type: multipart/form-data' -F file="@$file"  -F recognizer=ben 2>/dev/null | jq -r '.["id"]')
if [ $? -gt "0" ] ; then
   echo -e "${RED}FAILED $file\n\tCan't send file.${NC}"
   exit 1
fi
echo "ID: $id"
###############################################################
echo "Checking status..."
SECONDS=0
r=""
err=""
status=""
while [ "$err" == "" ] && [ "$status" != "COMPLETED" ]
do
   sleep 3
   r=$(curl -X GET -k $statusURL/$id -H "Authorization: Basic $AUTH" -H "accept: application/json" 2>/dev/null)
   err=$(echo "$r" | jq -r '.["error"]')
   status=$(echo $r | jq -r '.["status"]')
   echo -en "\e[1A\e[0K\rstatus: $status\tworking: $SECONDS\n"
done
if [ -n "$err" ] ; then
   echo -e "${RED}FAILED $file\n\t$err${NC}"
   exit 1
fi
###############################################################
echo "Getting result..."
#curl -X GET -k $resultURL/$id/result.txt -o "$file.txt" 2>/dev/null
curl -X GET -H "Authorization: Basic $AUTH" -k $resultURL/$id/lat.restored.txt -o "$file.txt" 2>/dev/null
if [ $? -gt "0" ] ; then
   echo -e "${RED}FAILED $file\n\tCan't get file.${NC}"
   exit 1
else
   echo -e "${GREEN}DONE $file${NC}"
fi
###############################################################

