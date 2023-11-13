import json
import socket
from base import *
from req import *
from resp import *
from config import config
from ui import UI
import subprocess
import logging
from threading import Thread
from itertools import cycle
from time import sleep
from logger import logger
from resp_anaylise import Info

import sys
import termios
import tty
import numpy as np

from decision import GetAction

# record the context of global data
gContext = {
    "playerID": -1,
    "gameOverFlag": False,
    "prompt": (
        "Take actions!\n"
        "'w': move up\n"
        "'s': move down\n"
        "'a': move left\n"
        "'d': move right\n"
        "'blank': place bomb\n"
    ),
    "steps": ["⢿", "⣻", "⣽", "⣾", "⣷", "⣯", "⣟", "⡿"],
    "gameBeginFlag": False,
}


class Client(object):
    """Client obj that send/recv packet.
    """
    def __init__(self) -> None:
        self.config = config
        self.host = self.config.get("host")
        self.port = self.config.get("port")
        assert self.host and self.port, "host and port must be provided"
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._connected = False

    def connect(self):
        if self.socket.connect_ex((self.host, self.port)) == 0:
            logger.info(f"connect to {self.host}:{self.port}")
            self._connected = True
        else:
            logger.error(f"can not connect to {self.host}:{self.port}")
            exit(-1)
        return

    def send(self, req: PacketReq):
        msg = json.dumps(req, cls=JsonEncoder).encode("utf-8")
        length = len(msg)
        self.socket.sendall(length.to_bytes(8, sys.byteorder) + msg)
        # uncomment this will show req packet
        # logger.info(f"send PacketReq, content: {msg}")
        return

    def recv(self, info : Info):
        length = int.from_bytes(self.socket.recv(8), sys.byteorder)
        result = b""
        while resp := self.socket.recv(length):
            result += resp
            length -= len(resp)
            if length <= 0:
                break

        # uncomment this will show resp packet
        # logger.info(f"recv PacketResp, content: {result}")
        packet = PacketResp().from_json(result)

        #数据解析
        resp_info = json.loads(result) # {player_id : int, map : [], round : int}
        if resp_info['type'] == 3 :
            resp_info = resp_info['data']
            info.update(resp_info=resp_info)

        return packet

    def __enter__(self):
        return self
    
    def close(self):
        logger.info("closing socket")
        self.socket.close()
        logger.info("socket closed successfully")
        self._connected = False
    
    @property
    def connected(self):
        return self._connected

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()
        if traceback:
            print(traceback)
            return False
        return True


def cliGetInitReq():
    """Get init request from user input."""
    # input("enter to start!")
    return InitReq(config.get("player_name"))


def recvAndRefresh(ui: UI, info : Info, client: Client):
    """Recv packet and refresh ui."""
    global gContext
    resp = client.recv(info)

    if resp.type == PacketType.ActionResp:
        gContext["gameBeginFlag"] = True
        gContext["playerID"] = resp.data.player_id
        ui.player_id = gContext["playerID"]


    while resp.type != PacketType.GameOver:
        subprocess.run(["clear"])
        ui.refresh(resp.data)
        ui.display(info)
        resp = client.recv(info)

    print(f"Game Over!")

    print(f"Final scores \33[1m{resp.data.scores}\33[0m")

    if gContext["playerID"] in resp.data.winner_ids:
        print("\33[1mCongratulations! You win! \33[0m")
    else:
        print(
            "\33[1mThe goddess of victory is not on your side this time, but there is still a chance next time!\33[0m"
        )

    gContext["gameOverFlag"] = True
    print("press any key to quit")



key2ActionReq = {
    'w': ActionType.MOVE_UP,
    's': ActionType.MOVE_DOWN,
    'a': ActionType.MOVE_LEFT,
    'd': ActionType.MOVE_RIGHT,
    ' ': ActionType.PLACED,
}

def termPlayAPI():
    ui = UI()
    info = Info()
    
    with Client() as client:
        client.connect()
        
        initPacket = PacketReq(PacketType.InitReq, cliGetInitReq())
        client.send(initPacket)
        
        # IO thread to display UI
        t = Thread(target=recvAndRefresh, args=(ui, info, client))
        t.start()
        
        print(gContext["prompt"])
        for c in cycle(gContext["steps"]):
            if gContext["gameBeginFlag"]:
                break
            print(
                f"\r\033[0;32m{c}\033[0m \33[1mWaiting for the other player to connect...\033[0m",
                flush=True,
                end="",
            )
            sleep(0.1)

        while not gContext["gameOverFlag"]:
            # key = scr.getch()
            # old_settings = termios.tcgetattr(sys.stdin)
            # tty.setcbreak(sys.stdin.fileno())
            # termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
            

            #等待接受一帧数据
            while(info.is_new_frame() == False) :
                if gContext["gameOverFlag"]:
                      break
                continue

            decision = GetAction(info)
            action = ActionReq(gContext["playerID"], decision[0])


            
            actionPacket = PacketReq(PacketType.ActionReq, action)
            client.send(actionPacket)

            sleep(0.04)

            #第二次发送
            action = ActionReq(gContext["playerID"], decision[1])
            actionPacket = PacketReq(PacketType.ActionReq, action)
            client.send(actionPacket)


            sleep(0.1)


if __name__ == "__main__":
    termPlayAPI()
