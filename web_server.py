import socket, threading, json

host = "127.0.0.1"
port = 8550

web_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
web_server.bind((host, port))
web_server.listen(1)

clients = []
waiting_users = []
ready_servers = []
games = []

lock = threading.Lock()


class game_play:
    user: socket.socket
    tic_server: socket.socket

    def __init__(self, user, server):
        self.user = user
        self.tic_server = server


class ready_server:
    tic_server: socket.socket
    status: str

    def __init__(self, server):
        self.tic_server = server
        self.status = 'WAIT'


def handle(cli: socket.socket):
    while True:
        try:
            message = json.loads(cli.recv(1024).decode("ascii"))
            print(message)
            ty = message["type"]
            if ty == 'create_server':
                lock.acquire()
                ready_servers.append(ready_server(cli))
                message = '{"type":"accept"}'
                cli.send(message.encode('ascii'))
                if waiting_users:
                    us = waiting_users.pop(0)
                    games.append(game_play(us, cli))
                    table = [[-1, -1, -1], [-1, -1, -1], [-1, -1, -1]]
                    message = '{"type":"accept", "table":' + str(table) + '}'
                    us.send(message.encode('ascii'))
                    for ser in ready_servers:
                        if ser.tic_server == cli:
                            ser.status = "BUSY"
                            break
                    message = '{"type":"INIT"}'
                    cli.send(message.encode('ascii'))
                lock.release()
            elif ty == 'start_game':
                found = False
                lock.acquire()
                for ser in ready_servers:
                    if ser.status == 'WAIT':
                        tic_server = ser.tic_server
                        message = '{"type":"INIT"}'
                        tic_server.send(message.encode('ascii'))
                        games.append(game_play(cli, tic_server))
                        ser.status = 'BUSY'
                        table = [[-1, -1, -1], [-1, -1, -1], [-1, -1, -1]]
                        message = '{"type":"accept", "table":' + str(table) + '}'
                        cli.send(message.encode('ascii'))
                        found = True
                        break
                lock.release()
                if not found:
                    message = '{"type":"decline", "message":"all servers are busy. please wait..."}'
                    cli.send(message.encode('ascii'))
                    waiting_users.append(cli)

            elif ty == 'move':
                tic_server: socket.socket
                for g in games:
                    if g.user == cli:
                        tic_server = g.tic_server
                        break
                tic_server.send(json.dumps(message).encode('ascii'))

            elif ty == 'exit':
                game: game_play
                found = False
                for g in games:
                    if g.user == cli:
                        game = g
                        found = True
                        break
                lock.acquire()
                if found:
                    games.remove(game)
                    tic_server = game.tic_server
                    if waiting_users:
                        us = waiting_users.pop(0)
                        games.append(game_play(us, tic_server))
                        table = [[-1, -1, -1], [-1, -1, -1], [-1, -1, -1]]
                        message = '{"type":"accept", "table":' + str(table) + '}'
                        us.send(message.encode('ascii'))
                        message = '{"type":"INIT"}'
                        tic_server.send(message.encode('ascii'))
                    else:
                        for ser in ready_servers:
                            if ser.tic_server == tic_server:
                                ser.status = "WAIT"
                                break
                else:
                    waiting_users.remove(cli)
                lock.release()

            elif ty in ['send', 'get']:
                if ty == 'send':
                    req = '{"type":"send", "sender":"1st player", "message":"' + message["message"] + '"}'
                else:
                    req = '{"type":"get"}'
                tic_server: socket.socket
                for g in games:
                    if g.user == cli:
                        tic_server = g.tic_server
                        break
                tic_server.send(req.encode('ascii'))

            else:
                game: game_play
                for g in games:
                    if g.tic_server == cli:
                        game = g
                        break
                user = game.user
                if ty == 'finish':
                    games.remove(game)
                    lock.acquire()
                    if waiting_users:
                        us = waiting_users.pop(0)
                        games.append(game_play(us, cli))
                        table = [[-1, -1, -1], [-1, -1, -1], [-1, -1, -1]]
                        mess = '{"type":"accept", "table":' + str(table) + '}'
                        us.send(mess.encode('ascii'))
                        mess = '{"type":"INIT"}'
                        cli.send(mess.encode('ascii'))
                    else:
                        for ser in ready_servers:
                            if ser.tic_server == cli:
                                ser.status = "WAIT"
                                break
                    lock.release()
                user.send(json.dumps(message).encode('ascii'))

        except socket.error:
            print("Error in handling")
            clients.remove(cli)
            cli.close()
            break


while True:
    client, address = web_server.accept()
    print(f'connecting with {address}')

    clients.append(client)
    thread = threading.Thread(target=handle, args=(client,))
    thread.start()
