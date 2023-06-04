.PHONY: gen clean

gen:
	python3 -m grpc_tools.protoc --experimental_allow_proto3_optional -I static --python_out=src --grpc_python_out=src static/*.proto

clean:
	rm src/core_pb2*.py
