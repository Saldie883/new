import socket
import pickle

sock = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)      

udp_host = "127.0.0.1"	       
udp_port = 1234			              

sock.bind((udp_host,udp_port))

connections = []

def send_request(addr, requestType, requestMessage):
    data = {
        "requestType": requestType,
        "requestMessage": requestMessage
    }
    try:
        sock.sendto(pickle.dumps(data), addr)
    except Exception as ex:
        print(ex)
    return 

def make_addr(connection):
    return str(connection[0]) + ":" + str(connection[1])

def from_addr(addr):
    addr = addr.split(":")
    connection = ""
    try:
        connection = (addr[0], int(addr[1]))
    except Exception as ex:
        print(ex)
    return connection

def handle_request(data, addr):
    data = pickle.loads(data)
    print("Server: ", data)
    
    requestType = data["requestType"]
    requestMessage = data["requestMessage"]

    if requestType == 1: # Подключение нового клиента 
        connection = make_addr(addr)
        data["requestMessage"].append(connection)
        send_request(addr, 3, connection)
        for i in connections:
            send_request(from_addr(i), 1, requestMessage)
        connections.append(connection)
    elif requestType == 2: # Для локального клиента создать все остальные
        addr = requestMessage[8]
        send_request(from_addr(addr), 2, requestMessage)
    
    # 3 - получить локальный адрес

    elif requestType == 4: # Синхронизация передвижения
        addr = requestMessage[0]
        for i in connections:
            if i != addr:
                send_request(from_addr(i), 4, requestMessage)

    elif requestType == 5: # Смерть
        loser = requestMessage[0]
        winner = requestMessage[1]
        for i in connections:
            send_request(from_addr(i), 5, requestMessage)
        connections.remove(loser)

        

def main():
    while True:
        print ("Waiting for client...")
        try:
            data, addr = sock.recvfrom(1024)
            handle_request(data, addr)
        except Exception as ex:
            print(f"Server exception {ex}")

if __name__ == "__main__":
    main()