from concurrent import futures
import logging
import time
import requests

import grpc
import core_pb2
import core_pb2_grpc

import pika
import atexit

import utils
import game_controller


class GameCore(core_pb2_grpc.GameCore):
    def __init__(self):
        # Init sessions
        self.sessions = dict()

        # Init connection to the chat
        self.chat_connection = None
        while self.chat_connection is None:
            try:
                connection = pika.BlockingConnection(
                    pika.ConnectionParameters(
                        "chat",
                        credentials=pika.credentials.PlainCredentials(
                            username="user", password="bitnami"
                        ),
                    ),
                )
                self.chat_connection = connection
                print("Connected to RabbitMQ!")
            except Exception as e:
                print(f"Failed to connect to RabbitMQ: {e}")
                time.sleep(5)
        atexit.register(self.chat_connection.close)
        self.chat_channel = self.chat_connection.channel()

    def MakeSession(self, request: core_pb2.MakeSessionRequest, context):
        session_id = request.session_id

        # Allocate new ID
        if not session_id:
            session_id = utils.make_session_id()

        # Validate session ID
        if session_id in self.sessions:
            context.abort(
                grpc.StatusCode.INVALID_ARGUMENT,
                f"Requested ID is already allocated: {session_id}",
            )

        # Create a message queue for the in-game chat
        self.chat_channel.queue_declare(queue=session_id)

        # Create a game controller
        self.sessions[session_id] = game_controller.GameController(
            lambda msg: self.chat_channel.basic_publish(
                exchange="", routing_key=session_id, body=msg
            ),
            lambda t, m: requests.post(
                "http://scoreboard:5000/graphql",
                data=f'{{"query": "mutation {{ updateGame(gameID:\\"{session_id}\\", towniesScore:{t}, mafiaScore:{m}) {{id}}}}"}}',
                headers={"Content-Type": "application/json"},
            ),
        )

        return core_pb2.SessionID(session_id=session_id)

    def JoinSession(self, request: core_pb2.JoinRequest, context):
        session_id = request.session_id
        player_name = request.player_name

        game = self._get_session(session_id)
        try:
            token = game.join(player_name)
            return core_pb2.PlayerInfo(player_token=token, session_id=session_id)
        except game_controller.InvalidAction as e:
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, str(e))

    def DoLeave(self, request: core_pb2.LeaveRequest, context):
        token = request.key.player_token
        session_id = request.key.session_id

        game = self._get_session(session_id)
        try:
            msg = game.do_leave(token)
            return core_pb2.CoreResponse(message=msg)
        except game_controller.InvalidAction as e:
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, str(e))

    def DoChat(self, request: core_pb2.ChatRequest, context):
        token = request.key.player_token
        session_id = request.key.session_id
        message = request.message

        game = self._get_session(session_id)
        try:
            msg = game.do_chat(token, message)
            return core_pb2.CoreResponse(message=msg)
        except game_controller.InvalidAction as e:
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, str(e))

    def DoVoteSacrifice(self, request: core_pb2.SacrificeRequest, context):
        token = request.key.player_token
        session_id = request.key.session_id
        target = request.target_name

        game = self._get_session(session_id)
        try:
            msg = game.do_vote_sacrifice(token, target)
            return core_pb2.CoreResponse(message=msg)
        except game_controller.InvalidAction as e:
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, str(e))

    def DoVoteMurder(self, request: core_pb2.MurderRequest, context):
        token = request.key.player_token
        session_id = request.key.session_id
        target = request.target_name

        game = self._get_session(session_id)
        try:
            msg = game.do_vote_murder(token, target)
            return core_pb2.CoreResponse(message=msg)
        except game_controller.InvalidAction as e:
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, str(e))

    def DoGetStatus(self, request: core_pb2.StatusRequest, context):
        token = request.key.player_token
        session_id = request.key.session_id

        game = self._get_session(session_id)
        try:
            msg = game.do_get_status(token)
            return core_pb2.CoreResponse(message=msg)
        except game_controller.InvalidAction as e:
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, str(e))

    def _get_session(self, session_id: str) -> game_controller.GameController:
        if session_id not in self.sessions:
            raise Exception(f"No session with such ID: {session_id}")
        return self.sessions[session_id]


def serve():
    port = "5000"
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=1))
    core_pb2_grpc.add_GameCoreServicer_to_server(GameCore(), server)
    server.add_insecure_port("[::]:" + port)
    server.start()
    print("Server started, listening on " + port)
    server.wait_for_termination()


if __name__ == "__main__":
    logging.basicConfig()
    serve()
