#!/bin/sh

while true; do
printf "\033c"
curl -s 'http://localhost:8082/graphql' --data '{"query": "\n{\ngames {\nid\nscore {\ntownies\nmafia\n}\ncomments\n}\n}\n"}' -H 'Content-Type: application/json'n | jq
sleep 5
done