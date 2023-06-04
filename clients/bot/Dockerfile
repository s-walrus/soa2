FROM alpine:latest

WORKDIR /app

RUN apk add --no-cache python3 python3 py3-pip g++ python3-dev gcc linux-headers protoc

COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt

COPY . .

# Generate GRPC schemas
RUN python3 -m grpc_tools.protoc --experimental_allow_proto3_optional -I static --python_out=src --grpc_python_out=src static/*.proto

CMD ["python3", "-u", "bot.py"]
