import socket, threading, json, random

host = "127.0.0.1"
port = 8550


def num_validity(move: (int, int)):
    if (move[0] > 3) | (move[0] < 0) | (move[1] > 3) | (move[1] < 0):
        return False
    return True


class tic_tac_toe:
    table = []
    is_single = True
    turn = 0
    chat = []

    def __init__(self, single: bool):
        self.table = [[-1, -1, -1], [-1, -1, -1], [-1, -1, -1]]
        self.turn = 1
        self.is_single = single
        self.chat = []

    def check_finished(self, turn_id: int, move: (int, int)):
        if (self.table[0][move[1]] == turn_id) & (self.table[1][move[1]] == turn_id) & (self.table[2][move[1]] == turn_id):
            return True
        if (self.table[move[0]][0] == turn_id) & (self.table[move[0]][1] == turn_id) & (self.table[move[0]][2] == turn_id):
            return True
        if (self.table[0][0] == turn_id) & (self.table[1][1] == turn_id) & (self.table[2][2] == turn_id):
            return True
        if (self.table[0][2] == turn_id) & (self.table[1][1] == turn_id) & (self.table[2][0] == turn_id):
            return True
        return False

    def move_validity(self, move: (int, int)):
        return self.table[move[0]][move[1]] == -1

    def play_round(self, turn_id: int, move: (int, int)):
        self.table[move[0]][move[1]] = turn_id
        return 'Successful'

    def get_empty_cells(self):
        empty_cells = []
        iteration = 0
        for r in self.table:
            for c in r:
                if c == -1:
                    empty_cells.append(iteration)
                iteration += 1
        return empty_cells

    def is_draw(self):
        return len(self.get_empty_cells()) == 0

    def play_random(self, turn_id: int):
        rand_choice = random.choice(self.get_empty_cells())
        raw = int(rand_choice / 3)
        column = rand_choice % 3
        self.play_round(turn_id, (raw, column))
        return raw, column


tic_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
tic_server.connect((host, port))

current_game = tic_tac_toe(True)


def get_message():
    global current_game
    message = '{"type":"create_server"}'
    tic_server.send(message.encode('ascii'))
    while True:
        try:
            if json.loads(tic_server.recv(1024).decode("ascii"))["type"] == "accept":
                break
        except socket.error:
            print("server not accepted.")
            tic_server.close()
            break

    while True:
        try:
            message = json.loads(tic_server.recv(1024).decode("ascii"))
            print(f'received message:{message}')
            ty = message["type"]
            if ty == 'INIT':
                current_game = tic_tac_toe(message["single"])
            elif ty == 'forfeit':
                feedback = '{"type":"finish", "message":"player ' + str(3-message["sender"]) + ' won the game.", "table":' + str(
                    current_game.table) + ', "rec":[1,2]}'
                tic_server.send(feedback.encode('ascii'))
            elif ty == 'move':
                if message["sender"] != current_game.turn:
                    feedback = '{"type":"error", "message":"this is not your turn. please wait...", "table":' + str(
                        current_game.table) + ', "rec":[' + str(message["sender"]) + ']}'
                    tic_server.send(feedback.encode('ascii'))
                    continue
                r, c = int(message["raw"]) - 1, int(message["column"]) - 1
                this_turn = current_game.turn
                if not num_validity((r, c)):
                    feedback = '{"type":"error", "message":"choice range is invalid.", "table":' + str(
                        current_game.table) + ', "rec":[' + str(this_turn) + ']}'
                    tic_server.send(feedback.encode('ascii'))
                elif not current_game.move_validity((r, c)):
                    feedback = '{"type":"error", "message":"choice range is not empty.", "table":' + str(
                        current_game.table) + ', "rec":[' + str(this_turn) + ']}'
                    tic_server.send(feedback.encode('ascii'))
                else:
                    current_game.play_round(this_turn, (r, c))
                    win = current_game.check_finished(this_turn, (r, c))
                    if win:
                        feedback = '{"type":"finish", "message":"player ' + str(this_turn) + ' won the game.", "table":'\
                                   + str(current_game.table) + ', "rec":[1,2]}'
                        tic_server.send(feedback.encode('ascii'))
                    elif current_game.is_draw():
                        feedback = '{"type":"finish", "message":"The game ended in a draw.", "table":' + \
                                   str(current_game.table) + ', "rec":[1,2]}'
                        tic_server.send(feedback.encode('ascii'))
                    elif current_game.is_single:
                        r, c = current_game.play_random(2)
                        lost = current_game.check_finished(2, (r, c))
                        if lost:
                            feedback = '{"type":"finish", "message":"player 2 won the game.", "table":' + \
                                       str(current_game.table) + ', "rec":[1]}'
                            tic_server.send(feedback.encode('ascii'))
                        else:
                            feedback = '{"type":"feedback", "message":"the cell was successfully selected.", ' \
                                       '"table":' + str(current_game.table) + ', "rec":[1]}'
                            tic_server.send(feedback.encode('ascii'))
                    else:
                        current_game.turn = 3 - current_game.turn
                        feedback = '{"type":"feedback", "message":"the cell was successfully selected by player ' + \
                                   str(this_turn) + '.", "table":' + str(current_game.table) + ', "rec":[1,2]}'
                        tic_server.send(feedback.encode('ascii'))
                        pass
            elif ty == 'send':
                current_game.chat.append("player" + str(message["sender"]) + ": " + message["message"])
            elif ty == 'get':
                feedback = '{"type":"chat", "chat":' + json.dumps(current_game.chat) + ', "rec":[' + str(message["sender"]) + ']}'
                tic_server.send(feedback.encode('ascii'))
        except socket.error:
            print("server closed.")
            tic_server.close()
            break


# def send_message():
#     while True:
#         message = input()
#         tic_server.send(message.encode('ascii'))


get_thread = threading.Thread(target=get_message)
get_thread.start()
# send_thread = threading.Thread(target=send_message)
# send_thread.start()
