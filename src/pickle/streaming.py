import pickle

BUFFERSIZE = 10

#generates a message with a fixed header which specifies the length of the message 
def createMsg(data):
    finalMsg = data
    finalMsg = f'{len(finalMsg):<10}'.encode("utf-8") + finalMsg
    return finalMsg


def streamData(target):
    data = target.recv(BUFFERSIZE)
    if len(data) != 0:
        msglen = int(data[:BUFFERSIZE].strip())
        full_data = b''

        # stream the data in with a set buffer size
        while len(full_data) < msglen:
            full_data += target.recv(BUFFERSIZE)
        
        obj = pickle.loads(full_data)
        return obj
    else:
        pass