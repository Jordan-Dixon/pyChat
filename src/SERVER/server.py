import socket
import json
import threading
import sys
import argparse
import os
from datetime import datetime
from message import Message
from streaming import createMsg, streamData,initializeAES
import pyDHE
import time

serverDH = pyDHE.new()


class Server:
    def __init__(self, ip, port, buffer_size):
        self.IP = ip
        self.PORT = port
        self.BUFFER_SIZE = buffer_size

        self.USERNAME = "*server*"

        self.temp_f = False

        self.connections = []
        self.database = {
            "host" : "username"
        }

        self.command_list = {
            "[export_chat]" : "export current chat",
            "[help]" : "display possibile commands"
        }
        self.keyList = {
            "client" : "key"
        }

        self.users_log = "./logs/users.txt"
        self.chat_log = "./logs/chatlog.txt"
        self.cons_log = "./logs/cons.txt"
        self.current_chat = "./logs/currentchat.txt"

        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    def startServer(self):
        try:
            self.server.bind((self.IP, self.PORT))
        except socket.error as e:
            print(str(e))

        self.server.listen(10)

        print(f"[*] Starting server ({self.IP}) on port {self.PORT}")

    def acceptConnections(self):
        while True:
            client_socket, address = self.server.accept()
            print(f"[*] Connection from {address} has been established!")
            self.logConnections(address[0])

            cThread = threading.Thread(target = self.handler, args = (client_socket, address))
            cThread.daemon = True
            cThread.start()

            self.connections.append(client_socket)
            self.shareVector(client_socket, address[0])
            self.sharePublicInfo(client_socket, address[0])
            time.sleep(0.1) # to avoid buffer congestion
           
    def stopServer(self):
        for conn in self.connections:
            conn.close()

        self.server.close()

    def shareVector(self, client_socket, address):
        with open('./vector', 'rb') as vector:
            content = vector.read().decode("utf-8")
            packet = Message(self.IP, address, self.USERNAME, str(datetime.now()), content, 'iv_exc')
            client_socket.send(packet.pack())

        print("*** Vector sent ***")


    def sharePublicInfo(self, client_socket, address):
        packet  = Message(self.IP, address, self.USERNAME, str(datetime.now()), str(serverDH.getPublicKey()), 'key_exc')
        client_socket.send(packet.pack())
        
        print("*** Server's Public Key Sent ***")
        

    def logConnections(self, address):
        contime = datetime.now()
        with open(self.cons_log, "a") as cons:
            cons.write(address + ">" + str(contime) + '\n')

    def logUsers(self, data):
        with open(self.users_log, "a", encoding = "utf-8") as users:
            users.write(data + '\n')

    def logChat(self, data):
        timestamp = datetime.now()
        with open(self.chat_log, "a", encoding = "utf-8") as chatlog:
            chatlog.write(data + " " + str(timestamp) + '\n')

    def current(self, data):
        """ wasn't sure about using with here """
        self.currentchat = open(self.current_chat, "a+", encoding = "utf-8")
        self.currentchat.write(data + '\n')

    def checkUsername(self, client_socket, address, data):
        flag = False
        # decrypted_data = self.cipher.decrypt(data).decode("utf-8")

        for user in self.database:
            if self.database[user] == data.cont:
                flag = True
                self.temp_f = True

                content = "[*] Username already in use!"
                # encrypted_content = self.cipher.encrypt(content)

                warning = Message(self.IP, address[0], self.USERNAME, str(datetime.now()), content, 'username_taken')

                client_socket.send(warning.pack())
                break

        if flag == False:
            self.database.update( {address : data.cont} )
            # self.logUsers(decoded_content)

            content = "[*] You have joined the chat!"
            # encrypted_content = self.cipher.encrypt(content)

            joined = Message(self.IP, address[0], self.USERNAME, str(datetime.now()), content, 'approved_conn')
            client_socket.send(joined.pack())

    def exportChat(self, client_socket, address):
        with open(self.current_chat, "rb") as chat:
            content = chat.read().decode("utf-8")

            packet = Message(self.IP, address[0], self.USERNAME, str(datetime.now()), content, 'export')

            for connection in self.connections:
                if connection == client_socket:
                    connection.send(packet.pack())
                    print("[*] Sent!")


    def commandList(self, client_socket, address):
        packet = Message(self.IP, address[0], self.USERNAME, str(datetime.now()), self.command_list, 'help', True)

        for connection in self.connections:
            if connection == client_socket:
                connection.send(packet.pack())
                print("[*] Sent!")

    def closeConnection(self, client_socket, address):
        disconnected_msg = f"[{address[0]}] has left the chat"
        left_msg_obj = Message(self.IP, "allhosts", self.USERNAME, str(datetime.now()), disconnected_msg, 'default')
        left_msg = left_msg_obj.pack()

        self.connections.remove(client_socket)

        for connection in self.connections:
            connection.send(left_msg)

        if not self.connections:
            try:
                os.remove(self.current_chat)
            except FileNotFoundError:
                print("*** Nothing to clear in the logs")

        try:
            del self.database[address]
        except KeyError:
            pass
        client_socket.close()

    def handler(self, client_socket, address):
        while True:
            try:
                data = streamData(client_socket).decode("utf-8")
                # print("\nRECV AFTER AES ", data)
                data = Message.from_json(data)
                # print("\nRECV AFTER JSON ", data)

            except ConnectionResetError:
                print(f"*** [{address[0]}] unexpectedly closed the connetion, received only an RST packet.")
                self.closeConnection(client_socket, address)
                break
            except AttributeError:
                print(f"*** [{address[0]}] disconnected")
                self.closeConnection(client_socket, address)
                break
            except UnicodeDecodeError:
                print(f"*** [{address[0]}] disconnected due to an encoding error")
                self.closeConnection(client_socket, address)
                break

            if data.typ == 'setuser':
                self.checkUsername(client_socket, address, data)

                if self.temp_f == True:
                    continue
            elif data.typ == 'key_exc':
                finalKey = serverDH.update(int(data.cont))
                self.keyList.update( { address[0] : finalKey })
                print("\nFINAL KEY", finalKey)
                initializeAES(str(finalKey).encode("utf-8"))
                print("** encryption key set")
            else:
                if data.cont != '':
                    if data.typ == 'default':
                        self.logChat(data.cont)
                        self.current(data.cont)
                    else:
                        self.logChat(data.cont)

                    if data.typ == 'export':
                        print("*** Sending chat...")
                        self.exportChat(client_socket, address)
                    elif data.typ == 'help':
                        print("*** Sending command list...")
                        self.commandList(client_socket, address)
                    else:
                        data = data.pack()
                        for connection in self.connections:
                            if connection != client_socket:
                                # print("\nBROADCASTING ", data)
                                connection.send(data)



def getArgs():
    parser = argparse.ArgumentParser()
    parser.add_argument("-p", "--port", dest = "port", help = "Start server on port X")

    options = parser.parse_args()

    if not options.port:
        raise Exception
    else:
        return options

def main():
    try:
        options = getArgs()
        PORT = int(options.port)
    except Exception: # if the user doesn't parse values from the command line
        PORT = int(input("*** Start server on port > "))

    HOSTNAME = socket.gethostname()
    IP =  socket.gethostbyname(HOSTNAME)
    BUFFER_SIZE = 1024

    server = Server(IP, PORT, BUFFER_SIZE)

    try:
        server.startServer()
        server.acceptConnections()

    except KeyboardInterrupt:
        print("*** Closing all the connections ***")
        server.stopServer()
        print("*** Server stopped ***")

    # except Exception as e:
        # print("General error", str(e))


if __name__ == "__main__":
    main()
