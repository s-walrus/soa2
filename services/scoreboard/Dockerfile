FROM python:3.11

WORKDIR /app

COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt
RUN pip3 install 'strawberry-graphql[debug-server]'

COPY . .

CMD ["python3", "-m", "strawberry", "server", "-p", "5000", "src.graphql"]
