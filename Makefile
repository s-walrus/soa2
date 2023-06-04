.PHONY: run

run:
	docker-compose build
	docker-compose up

gen-clients:
	python3 -m grpc_tools.protoc --experimental_allow_proto3_optional -I services/core/static --python_out=clients/bot --grpc_python_out=clients/bot services/core/static/*.proto

run-bot: gen-clients
	cd clients/bot && GAME_CORE_URL=localhost:8080 RABBITMQ_HOST=localhost python3 bot.py

run-scoreboard:
	sh clients/scoreboard.sh

clean:
	rm clients/bot/core_pb2*.py
