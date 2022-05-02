import socket, threading, json, re

host = "127.0.0.1"
port = 8550

states = ["READY", "WAIT", "ON_GAME"]
state = 0

valid_commands = {
    "READY": "/start_single , /start_double",
    "WAIT": "/exit",
    "ON_GAME": "/exit , /send [your_message] , /get , /select [123] [123]  # (1st number is row and 2nd is column.)",
}

board_sign = {
    -1: "N",
    1: "X",
    2: "O",
}

user = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
user.connect((host, port))


def echo():
    global state, states
    print("enter '/start_single' or '/start_double' to play.")
    while True:
        command = input()
        if command in ['/start_single', '/start_double']:
            if states[state] == 'READY':
                message = '{"type":"' + str(command[1:]) + '_game"}'
                user.send(message.encode('ascii'))
            elif states[state] == 'WAIT':
                print('please wait ...')
            else:
                print('invalid command!')
        elif command == '/exit':
            if states[state] == 'READY':
                print('you have not start the game yet!')
            else:
                message = '{"type":"exit"}'
                user.send(message.encode('ascii'))
                state = 0
        elif command.startswith('/select'):
            if states[state] != "ON_GAME":
                print("invalid command. You have not start a game.")
            else:
                reg = "/select ([123]) ([123])"
                find_rex = re.match(reg, command)
                if find_rex:
                    message = '{"type":"move", "raw":%d, "column":%d}' % (int(find_rex.group(1)), int(find_rex.group(2)))
                    user.send(message.encode('ascii'))
                else:
                    print("invalid command. please enter with pattern:/select [123] [123]  "
                          "# 1st number is row and 2nd is column.")
        elif command == '/get':
            if states[state] != "ON_GAME":
                print("invalid command. You have not start a game.")
            else:
                message = '{"type":"get"}'
                user.send(message.encode('ascii'))
        elif command.startswith("/send "):
            if states[state] != "ON_GAME":
                print("invalid command. You have not start a game.")
            else:
                message = '{"type":"send", "message":"' + command[6:] + '"}'
                user.send(message.encode('ascii'))
        else:
            print("please enter a valid command:" + str(valid_commands[states[state]]))


def read():
    global state
    while True:
        try:
            message = json.loads(user.recv(1024).decode("ascii"))
            if message["type"] == 'accept':
                print("game started. you are player %d" % message["player"])
                state = 2
                table = message["table"]
                print("*** N is empty. X is 1st player. O is 2nd player. ***")
                for row in table:
                    print(board_sign[row[0]] + "," + board_sign[row[1]] + "," + board_sign[row[2]])
            elif message["type"] == 'decline':
                state = 1
                print(message["message"])
            elif message["type"] == 'finish':
                state = 0
                table = message["table"]
                print("*** N is empty. X is 1st player. O is 2nd player. ***")
                for row in table:
                    print(board_sign[row[0]] + "," + board_sign[row[1]] + "," + board_sign[row[2]])
                print(message["message"])
            elif message["type"] in ['error', 'feedback']:
                print(message["message"])
                table = message["table"]
                print("*** N is empty. X is 1st player. O is 2nd player. ***")
                for row in table:
                    print(board_sign[row[0]] + "," + board_sign[row[1]] + "," + board_sign[row[2]])
            elif message["type"] == 'chat':
                print("chat list:")
                chat_list = message["chat"]
                for i in chat_list:
                    print(i)
            else:
                print(message["message"])
        except socket.error:
            print("error in receive data")
            user.close()
            break


echo_thread = threading.Thread(target=echo)
echo_thread.start()

read_thread = threading.Thread(target=read)
read_thread.start()
