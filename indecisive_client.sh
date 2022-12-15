#!/bin/bash

if [ "$#" -ne 2 ]; then
	echo "Usage: ./many_client.sh [ server address ] [ server port ]"
	exit 0
fi

channels=("Pokécenter" "lofi" "city pop")
all_switches=""
for i in {1..50}
do
	all_switches+="join $((i % 3))\n"
done

echo all_switches | python3 Client.py $1 $2
sleep 15
kill

