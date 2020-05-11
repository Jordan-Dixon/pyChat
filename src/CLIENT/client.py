import socket
import json
import threading
import argparse
import sys
import time
from datetime import datetime
from message import Message
from streaming import createMsg, streamData, initializeAES
import pyDHE
import eel

# this is temporary, just for debuggining when you want to open two clients on one computer
# Note that there is a small chance the random port numbers will be the same and crash anyway. 
import random

client = None # so we can use it in exposed functions
eel.init('./GUI/web') # initializing eel

clientDH = pyDHE.new() # diffiehellman object

class Client:
    def __init__(self, server_ip, port, buffer_size, client_ip):
        self.SERVER_IP = server_ip
        self.PORT = port
        self.BUFFER_SIZE = buffer_size
        self.CLIENT_IP = client_ip
        self.finalDecryptionKey = None

        print(f"[*] Host: {self.CLIENT_IP} | Port: {self.PORT}")

        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)


    def connectToServer(self):
        try:
            self.client.connect((self.SERVER_IP, self.PORT))
        except socket.error as e:
            print(str(e))
            sys.exit()

        iv = self.recvVector() # we receive the vector
        finalDecryptionKey = self.recvServerKey()

        self.sharePublicInfo()
        initializeAES(str(finalDecryptionKey).encode("utf-8"), iv.cont) # we even parse the vector message content
        self.setUsername()

    def recvServerKey(self):
        #receives the servers public key and uses it to generate the final decryption key
        serverKey = Message.from_json(streamData(self.client).decode("utf-8"))
        return clientDH.update(int(serverKey.cont))

    def sharePublicInfo(self):
        packet  = Message(self.CLIENT_IP, self.SERVER_IP, "temp", str(datetime.now()), str(clientDH.getPublicKey()), 'key_exc')
        self.client.send(packet.pack())

    def recvVector(self):
        iv = streamData(self.client).decode("utf-8")
        return Message.from_json(iv)

    def setUsername(self):
        while True:
            self.USERNAME = input("Enter username> ")
            if self.USERNAME:
                if self.USERNAME != "*server*":
                    # encrypted_username = self.cipher.encrypt(self.USERNAME.encode("utf-8"))
                    packet = Message(self.CLIENT_IP, self.SERVER_IP, "temp", str(datetime.now()), self.USERNAME, 'setuser')

                    self.client.send(packet.pack())

                    check = streamData(self.client).decode("utf-8")
                    check = Message.from_json(check)
                    print(check.cont)

                    if check.cont != "[*] Username already in use!":
                        break

                else:
                    print("Can't set username as *server*!")

            else:
                print("Username can't be empty!")


    def sendMsg(self, to_send_msg):
        if to_send_msg == "[export_chat]":
            packet = Message(self.CLIENT_IP, self.SERVER_IP, self.USERNAME, str(datetime.now()), to_send_msg, 'export')
        elif to_send_msg == "[help]":
            packet = Message(self.CLIENT_IP, self.SERVER_IP, self.USERNAME, str(datetime.now()), to_send_msg, 'help')
        else:
            packet = Message(self.CLIENT_IP, self.SERVER_IP, self.USERNAME, str(datetime.now()), to_send_msg, 'default')

        self.client.send(packet.pack())

    def receiveData(self):
        while True:
            try:
                data = streamData(self.client)
                data = data.decode("utf-8")
                data = Message.from_json(data) # it's a dataclass object
            except AttributeError:
                print("\r[*] Connection closed by the server")
                break

            if data.typ == "export":
                timestamp = str(datetime.now())
                timestamp = timestamp.replace(":", ".") # windowz is stoopid

                chat_file = f"./exported/chat{timestamp}.txt"

                try:
                    with open(chat_file, "wb+") as chat:
                        chat.write(data.cont.encode("utf-8"))
                        print("\r[*] Writing to file...")

                    print(f"[*] Finished! You can find the file at {chat_file}")
                    print('\n' + "You> ", end = "")
                except:
                    print('\r' + "[*] Something went wrong" + '\n' + "You> ", end = "")
            else:
                if data.typ == "help":
                    for command in data.cont:
                        print('\r' + command + " : " + data.cont[command])

                    print('\r' + "You> ", end = "")
                else:
                    #print('\r' + data.username + "> " + data.cont + '\n' + "You> ", end = "")
                    eel.writeMsg(data.cont, data.username)

        self.client.close()

# [Eel functions]
@eel.expose
def exposeSendMsg(to_send_msg):
    client.sendMsg(to_send_msg)
    
@eel.expose
def getUsername():
    return client.USERNAME
 
def getArgs():
    parser = argparse.ArgumentParser()
    parser.add_argument("-s", "--server", dest = "server_ip", help = "Enter server IP")
    parser.add_argument("-p", "--port", dest = "server_port", help = "Enter server PORT")

    options = parser.parse_args()

    if not options.server_ip and not options.server_port:
        raise Exception # raising exception in case the user doesn't provide values from the terminal

    if not options.server_ip:
        parser.error("*** Please specify a server IP ***")
    elif not options.server_port:
        parser.error("*** Please specify a port number ***")
    else:
        return options

def startEel():
    eel.start('main.html', port=random.choice(range(8000, 8080)))

def main():
    try:
        options = getArgs()

        SERVER_IP = options.server_ip
        PORT = int(options.server_port)
    except Exception: # in case the user doesn't provide values we ask him to enter them
        SERVER_IP = input("*** Enter server IP address > ")
        PORT = int(input("*** Enter server PORT number > "))

    BUFFER_SIZE = 1024

    CLIENT_IP = socket.gethostbyname(socket.gethostname())

    global client
    client = Client(SERVER_IP, PORT, BUFFER_SIZE, CLIENT_IP)
    client.connectToServer()

    # threding eel in the background
    eThread = threading.Thread(target = startEel)
    eThread.daemon = True
    eThread.start()

    client.receiveData()


if __name__ == "__main__":
    main()
