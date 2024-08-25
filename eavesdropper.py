import os, socket, sys, time
from datetime import datetime


def eav_config_file_check():
    try:
        path_ls = str(sys.argv[1]).split('/')
        filename = ''
        if path_ls[0] == '~' or path_ls[0] == '.':
            home = os.path.expanduser('~')
            path_ls[0] = home
            filename += '/'.join(path_ls)
        else:
            filename += str(sys.argv[1])
        f = open(filename, 'r')
        server_port = 0
        client_port = 0
        spy_path = ''
        while True:
            line = f.readline()
            if line == '':
                break
            line_split = line.split('=')
            if len(line_split) != 2:
                sys.exit(2)
            if line_split[0] == 'server_port':
                if int(line_split[1]) <= 1024:
                    sys.exit(2)
                server_port = int(line_split[1])
            elif line_split[0] == 'client_port':
                if int(line_split[1]) <= 1024:
                    sys.exit(2)
                if server_port == client_port:
                    sys.exit(2)
                client_port = int(line_split[1])
            elif line_split[0] == 'spy_path':
                if not isinstance(line_split[1], str):
                    sys.exit(3)
                s = ''
                i = 0
                while i < len(line_split[1]):
                    if line_split[1][i] == '\n':
                        break
                    s += line_split[1][i]
                    i += 1
                line_split[1] = s
                spy_path_ls = line_split[1].split('/')
                if spy_path_ls[0] == '~' or path_ls[0] == '.':
                    home = os.path.expanduser('~')
                    spy_path_ls[0] = home
                    spy_path += '/'.join(spy_path_ls)
                else:
                    spy_path += str(line_split[1])
        if server_port == 0 or client_port == 0 or spy_path == '':
            sys.exit(2)
    except IndexError: 
        sys.exit(1)
    f.close()
    return [server_port, client_port, spy_path]


def spy_path_check(spy_path) -> bool:
    if os.path.exists(spy_path) and os.access(spy_path, os.W_OK):
        return True
    else:
        sys.exit(2)
        
        
# eavesdropper binds to the client and pretends to be the server
def ec_socket_setup():
    client_port = int(eav_config_file_check()[1])
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.settimeout(20)
    try:
        host = 'localhost'
        s.bind((host, client_port))
        s.listen()
        ec, addr = s.accept()
    except TimeoutError:
        sys.exit(3)
    except socket.error:
        sys.exit(2)
    return ec


# eavesdropper connects to the server and pretends to be the client
def es_socket_setup():
    server_port = int(eav_config_file_check()[0])
    try:
        es = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    except socket.error:
        print('AS: Cannot establish connection\r\n', end='', flush=True)
        sys.exit(3)
    es.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    es.settimeout(20)
    try:
        host = 'localhost'
        es.connect((host, server_port))
    except TimeoutError:
        sys.exit(3)
    except ConnectionRefusedError:
        print('AS: Cannot establish connection\r\n', end='', flush=True)
        sys.exit(3)
    return es


def eav_ehlo(es, ec):
    ser_response = es.recv(1024)
    ser_response = ser_response.decode('ascii')
    if ser_response == '':
        print('AS: Connection lost\r\n', end='', flush=True)
        sys.exit(3)
    print(f'S: {ser_response}', end='', flush=True)
    msg = ser_response
    ec.send(msg.encode('ascii'))
    print(f'AC: {msg}', end='', flush=True)
    cli_response = ec.recv(1024)
    cli_response = cli_response.decode('ascii')
    if cli_response == '':
        print('AC: Connection lost\r\n', end='', flush=True)
    print(f'C: {cli_response}', end='', flush=True)
    es.sendall(cli_response.encode('ascii'))
    print(f'AS: {cli_response}', end='', flush=True)
    ser_response = es.recv(1024)
    ser_response = ser_response.decode('ascii')
    if ser_response == '':
        print('AS: Connection lost\r\n', end='', flush=True)
        sys.exit(3)
    ser_response_ls = ser_response.split('\r\n')
    print(f'S: {ser_response_ls[0]}\r\n', end='', flush=True)
    print(f'S: {ser_response_ls[1]}\r\n', end='', flush=True)
    ec.send(ser_response.encode('ascii'))
    print(f'AC: {ser_response_ls[0]}\r\n', end='', flush=True)
    print(f'AC: {ser_response_ls[1]}\r\n', end='', flush=True)
    
    
def get_filename(dt, spy_path):
    form = '%a, %d %b %Y %X %z'
    date_time = datetime.strptime(dt, form)
    dt_ls = str(date_time).split()
    i = len(dt_ls[1]) - 1
    ls = dt_ls[1].split('+')
    dt_ls[1] = ' +'.join(ls)
    s = ''
    for i in range(0, len(dt_ls[1])):
        if i == len(dt_ls[1]) - 3:
            continue
        s += dt_ls[1][i]
    dt_ls[1] = s
    date = dt_ls[0].split('-')
    t = dt_ls[1].split(':')
    t_ls = t[-1].split()
    t.remove(t[-1])
    for i in t_ls:
        t.append(i)
    d = datetime(int(date[0]), int(date[1]), int(date[2]), int(t[0]), int(t[1]), int(t[2]))
    unix_ts = time.mktime(d.timetuple())
    store = ''
    for i in range(0, len(str(unix_ts))):
        if str(unix_ts)[i] == '.':
            break
        store += str(unix_ts)[i]
    store += '.txt'
    filename = ''
    filename += spy_path + '/' + store
    return filename
    
    
def eav_mail(es, ec, spy_path):
    mail_content_ls = []
    count = 0
    quit = False
    while True:
        cli_response = ec.recv(1024)
        cli_response = cli_response.decode('ascii')
        count += 1
        cli_res_ls = cli_response.split()
        if cli_res_ls[0] == 'AUTH':
            while True:
                print(f'C: {cli_response}', end='', flush=True)
                es.sendall(cli_response.encode('ascii'))
                print(f'AS: {cli_response}', end='', flush=True)
                ser_response = es.recv(1024)
                ser_response = ser_response.decode('ascii')
                if ser_response == '':
                    print('AS: Connection lost\r\n', end='', flush=True)
                    sys.exit(3)
                print(f'S: {ser_response}', end='', flush=True)
                ec.send(ser_response.encode('ascii'))
                print(f'AC: {ser_response}', end='', flush=True)
                ser_response_ls = ser_response.split()
                if ser_response_ls[0] == '235':
                    break
        cli_response_ls = cli_response.split(':')
        if cli_response == 'QUIT\r\n':
            quit = True
        elif cli_response == '.\r\n':
            f = open(filename, 'w')
            for i in range(0, len(mail_content_ls)):
                f.write(mail_content_ls[i] + '\n')
            f.close()
        elif count == 1 and cli_response_ls[0] == 'MAIL FROM':
            temp = ''
            for i in range(0, len(cli_response_ls[1])):
                if cli_response_ls[1][i] == '\r':
                    break
                temp += cli_response_ls[1][i]
            mail = 'From: ' + temp
            mail_content_ls.append(mail)
        elif count == 2 and cli_response_ls[0] == 'RCPT TO':
            temp = ''
            for i in range(0, len(cli_response_ls[1])):
                if cli_response_ls[1][i] == '\r':
                    break
                temp += cli_response_ls[1][i]
            rcpt = 'To: ' + temp
            mail_content_ls.append(rcpt)
        elif count == 4 and cli_response_ls[0] == 'Date':
            cli_response_ls.remove(cli_response_ls[0])
            store = ':'.join(cli_response_ls)
            s = ''
            c = 0
            for i in range(0, len(store)):
                if store[i].isspace():
                    c += 1
                    if c == 1:
                        continue
                elif store[i] == '\r':
                    break
                s += store[i]
            dt = ''
            for i in range(0, len(s)):
                if s[i] == '\r':
                    break
                dt += s[i]
            filename = get_filename(dt, spy_path)
            temp = ''
            for i in range(0, len(store)):
                if store[i] == '\r':
                    break
                temp += store[i]
            date = ''
            date += 'Date:' + temp
            mail_content_ls.append(date)
        elif count != 3:
            temp = ''
            for i in range(0, len(cli_response)):
                if cli_response[i] == '\r':
                    break
                temp += cli_response[i]
            mail_content_ls.append(temp)
        print(f'C: {cli_response}', end='', flush=True)
        es.sendall(cli_response.encode('ascii'))
        print(f'AS: {cli_response}', end='', flush=True)
        ser_response = es.recv(1024)
        ser_response = ser_response.decode('ascii')
        print(f'S: {ser_response}', end='', flush=True)
        ec.send(ser_response.encode('ascii'))
        print(f'AC: {ser_response}', end='', flush=True)
        if quit:
            sys.exit(0)


def main():
    eav_config_file_check()
    spy_path = str(eav_config_file_check()[2])
    spy_path_check(spy_path)
    
    es = es_socket_setup()
    ec = ec_socket_setup()
    
    eav_ehlo(es, ec)
    eav_mail(es, ec, spy_path)


if __name__ == '__main__':
    main()