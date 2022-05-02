import socket, threading, json

host = "127.0.0.1"
port = 8550

web_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
web_server.bind((host, port))
web_server.listen(1)

clients = []
waiting_singles = []
waiting_doubles = []
ready_servers = []
games = []

lock = threading.Lock()


class game_play:
    user1: socket.socket
    user2: socket.socket
    tic_server: socket.socket

    def __init__(self, user1, user2, server):
        self.user1 = user1
        self.user2 = user2
        self.tic_server = server


class ready_server:
    tic_server: socket.socket
    status: str

    def __init__(self, server):
        self.tic_server = server
        self.status = 'WAIT'


def handle(cli: socket.socket):
    global waiting_doubles, waiting_singles
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
                if len(waiting_doubles) > 1:
                    us1 = waiting_doubles.pop(0)
                    us2 = waiting_doubles.pop(0)
                    games.append(game_play(us1, us2, cli))
                    table = [[-1, -1, -1], [-1, -1, -1], [-1, -1, -1]]
                    feed1 = '{"type":"accept", "player":1, "table":' + str(table) + '}'
                    feed2 = '{"type":"accept", "player":2, "table":' + str(table) + '}'
                    us1.send(feed1.encode('ascii'))
                    us2.send(feed2.encode('ascii'))
                    for ser in ready_servers:
                        if ser.tic_server == cli:
                            ser.status = "BUSY"
                            break
                    feed = '{"type":"INIT", "single":false}'
                    cli.send(feed.encode('ascii'))
                elif waiting_singles:
                    us = waiting_singles.pop(0)
                    games.append(game_play(us, None, cli))
                    table = [[-1, -1, -1], [-1, -1, -1], [-1, -1, -1]]
                    feed = '{"type":"accept", "player":1, "table":' + str(table) + '}'
                    us.send(feed.encode('ascii'))
                    for ser in ready_servers:
                        if ser.tic_server == cli:
                            ser.status = "BUSY"
                            break
                    feed1 = '{"type":"INIT", "single":true}'
                    cli.send(feed1.encode('ascii'))
                lock.release()
            elif ty == 'start_single_game':
                found = False
                lock.acquire()
                for ser in ready_servers:
                    if ser.status == 'WAIT':
                        tic_server = ser.tic_server
                        message = '{"type":"INIT", "single":true}'
                        tic_server.send(message.encode('ascii'))
                        games.append(game_play(cli, None, tic_server))
                        ser.status = 'BUSY'
                        table = [[-1, -1, -1], [-1, -1, -1], [-1, -1, -1]]
                        message = '{"type":"accept", "player":1, "table":' + str(table) + '}'
                        cli.send(message.encode('ascii'))
                        found = True
                        break
                if not found:
                    message = '{"type":"decline", "message":"all servers are busy. please wait..."}'
                    cli.send(message.encode('ascii'))
                    waiting_singles.append(cli)
                lock.release()
            elif ty == 'start_double_game':
                lock.acquire()
                if len(waiting_doubles) == 0:
                    feed = '{"type":"decline", "message":"no competitor is available. please wait..."}'
                    cli.send(feed.encode('ascii'))
                    waiting_doubles.append(cli)
                else:
                    found = False
                    waiting_doubles.append(cli)
                    for ser in ready_servers:
                        if ser.status == 'WAIT':
                            tic_server = ser.tic_server
                            feed = '{"type":"INIT", "single":false}'
                            tic_server.send(feed.encode('ascii'))
                            us1 = waiting_doubles.pop(0)
                            us2 = waiting_doubles.pop(0)
                            games.append(game_play(us1, us2, tic_server))
                            ser.status = 'BUSY'
                            table = [[-1, -1, -1], [-1, -1, -1], [-1, -1, -1]]
                            feed1 = '{"type":"accept", "player":1, "table":' + str(table) + '}'
                            feed2 = '{"type":"accept", "player":2, "table":' + str(table) + '}'
                            us1.send(feed1.encode('ascii'))
                            us2.send(feed2.encode('ascii'))
                            found = True
                            break
                    if (not found) | (len(waiting_doubles) > 0):
                        message = '{"type":"decline", "message":"all servers are busy. please wait..."}'
                        cli.send(message.encode('ascii'))
                lock.release()
            elif ty == 'move':
                tic_server: socket.socket
                player: int
                for g in games:
                    if g.user1 == cli:
                        tic_server = g.tic_server
                        player = 1
                        break
                    elif g.user2 == cli:
                        tic_server = g.tic_server
                        player = 2
                message["sender"] = player
                tic_server.send(json.dumps(message).encode('ascii'))

            elif ty == 'exit':
                game: game_play
                player: int
                found = False
                for g in games:
                    if g.user1 == cli:
                        game = g
                        player = 1
                        found = True
                        break
                    elif g.user2 == cli:
                        game = g
                        player = 2
                        found = True
                        break
                lock.acquire()
                if found:
                    feed = '{"type":"forfeit", "sender":%d }' % player
                    game.tic_server.send(feed.encode("ascii"))
                else:
                    if cli in waiting_singles:
                        waiting_singles.remove(cli)
                    elif cli in waiting_doubles:
                        waiting_doubles.remove(cli)
                lock.release()

            elif ty in ['send', 'get']:
                tic_server: socket.socket
                player: int
                for g in games:
                    if g.user1 == cli:
                        tic_server = g.tic_server
                        player = 1
                        break
                    elif g.user2 == cli:
                        tic_server = g.tic_server
                        player = 2
                        break
                message["sender"] = player
                tic_server.send(json.dumps(message).encode('ascii'))

            else:
                game: game_play
                for g in games:
                    if g.tic_server == cli:
                        game = g
                        break
                user1 = game.user1
                user2 = game.user2
                if ty == 'finish':
                    games.remove(game)
                    lock.acquire()
                    if len(waiting_doubles) > 1:
                        us1 = waiting_doubles.pop(0)
                        us2 = waiting_doubles.pop(0)
                        games.append(game_play(us1, us2, cli))
                        table = [[-1, -1, -1], [-1, -1, -1], [-1, -1, -1]]
                        feed1 = '{"type":"accept", "player":1, "table":' + str(table) + '}'
                        feed2 = '{"type":"accept", "player":2, "table":' + str(table) + '}'
                        us1.send(feed1.encode('ascii'))
                        us2.send(feed2.encode('ascii'))
                        feed = '{"type":"INIT", "single":false}'
                        cli.send(feed.encode('ascii'))
                    elif waiting_singles:
                        us = waiting_singles.pop(0)
                        games.append(game_play(us, None, cli))
                        table = [[-1, -1, -1], [-1, -1, -1], [-1, -1, -1]]
                        feed = '{"type":"accept", "player":1, "table":' + str(table) + '}'
                        us.send(feed.encode('ascii'))
                        feed = '{"type":"INIT", "single":true}'
                        cli.send(feed.encode('ascii'))
                    else:
                        for ser in ready_servers:
                            if ser.tic_server == cli:
                                ser.status = "WAIT"
                                break
                    lock.release()
                if 1 in message["rec"]:
                    user1.send(json.dumps(message).encode('ascii'))
                if (2 in message["rec"]) and user2:
                    user2.send(json.dumps(message).encode('ascii'))
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
