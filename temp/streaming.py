import json
import message

BUFFERSIZE = 10


#generates a message with a fixed header which specifies the length of the message 
#returns the message encoded in bytes
def createMsg(data):
    finalMsg = data
    finalMsg = f'{len(finalMsg):<10}' + finalMsg
    return finalMsg.encode("utf-8")


#streams data in with a set BUFFERSIZE and returns the message object (or any object)
def streamData(target):
    data = target.recv(BUFFERSIZE)
    if len(data) != 0:
        msglen = int(data[:BUFFERSIZE].strip())
        full_data = ''

        # stream the data in with a set buffer size
        while len(full_data) < msglen:
            full_data += target.recv(BUFFERSIZE).decode("utf-8")
        
        return Message.to_json(full_data)
