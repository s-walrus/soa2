import random
import string
import time
import os

import grpc
import core_pb2_grpc
import core_pb2

import pika

DEBUG = False


def flush_messages(channel, queue):
    while True:
        msg = get_message(channel, queue)
        if msg is None:
            return
        print("> " + msg.decode("utf-8"))


def get_message(channel, queue):
    method_frame, header_frame, body = channel.basic_get(queue=queue)
    if not method_frame or method_frame.NAME == "Basic.GetEmpty":
        return None
    else:
        channel.basic_ack(delivery_tag=method_frame.delivery_tag)
        return body


def play_round(stub, chat, session_id, players):
    print("All players send a message to the chat")
    for p in players:
        stub.DoChat(core_pb2.ChatRequest(key=p, message="hi"))
    flush_messages(chat, session_id)

    time.sleep(1)

    print()
    print("Status of each player:")
    for i, p in enumerate(players):
        print(f"player{i}: " + stub.DoGetStatus(core_pb2.StatusRequest(key=p)).message)
    print()

    time.sleep(1)

    while True:
        for p in players:
            i = random.choice(range(5))
            if random.randint(0, 2) == 1:
                try:
                    stub.DoVoteMurder(
                        core_pb2.MurderRequest(key=p, target_name=f"player{i}")
                    )
                except Exception as e:
                    if DEBUG:
                        print(f"err: {e}")
            else:
                try:
                    stub.DoVoteSacrifice(
                        core_pb2.SacrificeRequest(key=p, target_name=f"player{i}")
                    )
                except Exception as e:
                    if DEBUG:
                        print(f"err: {e}")
            flush_messages(chat, session_id)
            time.sleep(0.1)


def run(channel):
    print("Starting a game")
    stub = core_pb2_grpc.GameCoreStub(channel)
    session_id = stub.MakeSession(core_pb2.MakeSessionRequest()).session_id

    print("Welcome!")
    print("This script will emulate 5 bots playing the game.")
    print("The chat log will be printed here.")
    print()
    print("Created a gaming session (rpc: MakeSession)")
    print()

    time.sleep(1)

    print("Connecting to the chat message queue")
    connection = pika.BlockingConnection(
        pika.ConnectionParameters(
            os.environ["RABBITMQ_HOST"],
            credentials=pika.credentials.PlainCredentials(
                username="user", password="bitnami"
            ),
        )
    )
    chat = connection.channel()
    print("Done!")
    print()
    time.sleep(1)
    print("Message from chat will look like this:")
    print("> message")
    print()

    time.sleep(1)

    players = [
        stub.JoinSession(
            core_pb2.JoinRequest(player_name=f"player{i}", session_id=session_id)
        )
        for i in range(5)
    ]
    flush_messages(chat, session_id)

    time.sleep(1)

    while True:
        play_round(stub, chat, session_id, players)


def main():
    with grpc.insecure_channel(os.environ["GAME_CORE_URL"]) as channel:
        run(channel)


if __name__ == "__main__":
    main()
