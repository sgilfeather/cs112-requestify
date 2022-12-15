#!/bin/bash

if [ "$#" -ne 2 ]; then
        echo "Usage: ./many_client.sh [ server address ] [ server port ]"
        exit 0
fi

for i in {1..25}
do
	python3 Client.py $1 $2 &
done
sleep 30
pkill -f Client.py
