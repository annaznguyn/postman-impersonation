import os, socket, sys, base64, hmac, re
from datetime import datetime

# Visit https://edstem.org/au/courses/8961/lessons/26522/slides/196175 to get
PERSONAL_ID = '21C748'
PERSONAL_SECRET = '75137b2940d8cfccf33772a1bafb2778'


def cli_config_file_check():
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
        send_path = ''
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
            elif line_split[0] == 'send_path':
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
                sendpath_ls = line_split[1].split('/')
                if sendpath_ls[0] == '~' or sendpath_ls[0] == '.':
                    home = os.path.expanduser('~')
                    sendpath_ls[0] = home
                    send_path += '/'.join(sendpath_ls)
                else:
                    send_path += str(line_split[1])
        if server_port == 0 or send_path == '':
            sys.exit(2)
    except IndexError: 
        sys.exit(1)
    f.close()
    return [server_port, send_path]


def client_socket_setup():
    port = int(cli_config_file_check()[0])
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    except socket.error:
        print('C: Cannot establish connection\r\n', end='', flush=True)
        sys.exit(3)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.settimeout(20)
    try:
        host = 'localhost'
        s.connect((host, port))
    except TimeoutError:
        sys.exit(3)
    except ConnectionRefusedError:
        print('C: Cannot establish connection\r\n', end='', flush=True)
        sys.exit(3)
    return s


def cli_spfile_check(file) -> bool:
    f = open(file, 'r')
    count = 0
    while True:
        line = f.readline()
        if line == '':
            break
        count += 1
        line_split = line.split(':')
        if count == 1:
            if line == '\n':
                print(f'C: {file}: Bad formation\r\n', end='', flush=True)
                return False
            elif line_split[0] != 'From':
                print(f'C: {file}: Bad formation\r\n', end='', flush=True)
                return False
            elif line_split[1] == ' ' or line_split[1].isspace():
                print(f'C: {file}: Bad formation\r\n', end='', flush=True)
                return False
            s = ''
            i = 0
            while i < len(line_split[1]):
                if line_split[1][i] == '\n':
                    break
                s += line_split[1][i]
                i += 1
            line_split[1] = s 
            if line_split[1][1] != '<' or line_split[1][-1] != '>':
                print(f'C: {file}: Bad formation\r\n', end='', flush=True)
                return False
        elif count == 2:
            if line == '\n':
                print(f'C: {file}: Bad formation\r\n', end='', flush=True)
                return False
            elif line_split[0] != 'To':
                print(f'C: {file}: Bad formation\r\n', end='', flush=True)
                return False
            email_ls = line_split[1].split(',')
            c = 0 
            for k in line_split[1]:
                if k == '@':
                    c += 1
            if c > 1 and len(email_ls) < 2:
                print(f'C: {file}: Bad formation\r\n', end='', flush=True)
                return False
            s = ''
            i = 0
            while i < len(email_ls[-1]):
                if email_ls[-1][i] == '\n':
                    break
                s += email_ls[-1][i]
                i += 1
            email_ls[-1] = s
            j = 0
            while j < len(email_ls):
                if j == 0:
                    if email_ls[j][1] != '<' or email_ls[j][-1] != '>':
                        print(f'C: {file}: Bad formation\r\n', end='', flush=True)
                        return False
                else:
                    if email_ls[j][0] != '<' or email_ls[j][-1] != '>':
                        print(f'C: {file}: Bad formation\r\n', end='', flush=True)
                        return False
                j += 1
        elif count == 3:
            if line == '\n':
                print(f'C: {file}: Bad formation\r\n', end='', flush=True)
                return False
            elif line_split[0] != 'Date':
                print(f'C: {file}: Bad formation\r\n', end='', flush=True)
                return False
            elif line_split[0] == 'Date':
                dt = ''
                for i in range(0, len(line)):
                    if i < 6:
                        continue
                    if line[i] == '\n':
                        break
                    dt += line[i]
                form = '%a, %d %b %Y %X %z'
                date_time = datetime.strptime(dt, form)
                dt_ls = str(date_time).split()
                date = dt_ls[0].split('-')
                t = dt_ls[1].split(':')
                try:
                    datetime(int(date[0]), int(date[1]), int(date[2]), int(t[0]), int(t[1]))
                except ValueError:
                    print(f'C: {file}: Bad formation\r\n', end='', flush=True)
                    return False
        elif count == 4:
            if line == '\n':
                print(f'C: {file}: Bad formation\r\n', end='', flush=True)
                return False
            elif line_split[0] != 'Subject':
                print(f'C: {file}: Bad formation\r\n', end='', flush=True)
                return False
    f.close()
    return True
        

def cli_get_sender_addr(file) -> str:
    f = open(file, 'r')
    first_line = f.readline()
    line_split = first_line.split(':')
    email_addr = str(line_split[1])
    s = ''
    i = 0
    while i < len(email_addr):
        if email_addr[i] == '\n':
            break
        elif email_addr[i].isspace():
            i += 1
            continue
        s += email_addr[i]
        i += 1
    email_addr = s
    f.close()
    return email_addr


def cli_rp_addr(file) -> list:
    f = open(file, 'r')
    f.readline()
    line = f.readline()
    line_split = line.split(':')
    addr_ls = line_split[1].split(',')
    store = ''
    i = 0
    while i < len(addr_ls[0]):
        if addr_ls[0][i].isspace():
            i += 1
            continue
        store += addr_ls[0][i]
        i += 1
    addr_ls[0] = store 
    s = ''
    i = 0
    while i < len(addr_ls[-1]):
        if addr_ls[-1][i] == '\n':
            break
        s += addr_ls[-1][i]
        i += 1
    addr_ls[-1] = s
    f.close()
    return addr_ls
        

def cli_get_data(file) -> list:
    f = open(file, 'r')
    f.readline()
    f.readline()
    ls = []
    while True:
        line = f.readline()
        if line == '':
            break
        s = ''
        for i in line:
            if i == '\n':
                break
            s += i
        line = s
        ls.append(line)
    f.close()
    return ls


def cli_ehlo(s):
    wel_msg = s.recv(1024)
    wel_msg = wel_msg.decode('ascii')
    if wel_msg == '':
        msg = 'Connection lost\r\n'
        print(f'S: {msg}', end='', flush=True)
        sys.exit(3)
    print(f'S: {wel_msg}', end='', flush=True)
    msg = 'EHLO 127.0.0.1\r\n'
    s.sendall(msg.encode('ascii'))
    print(f'C: {msg}', end='', flush=True)
    response = s.recv(1024) 
    response = response.decode('ascii')
    if response == '':
        msg = 'Connection lost\r\n'
        print(f'S: {msg}', end='', flush=True)
        sys.exit(3)
    print(f'S: {response}', end='', flush=True)


def cli_send_mail(s, file):
    msg = f'MAIL FROM:{cli_get_sender_addr(file)}\r\n'
    s.sendall(msg.encode('ascii'))
    print(f'C: {msg}', end='', flush=True)
    response = s.recv(1024)
    response = response.decode('ascii')
    if response == '':
        msg = 'Connection lost\r\n'
        print(f'S: {msg}', end='', flush=True)
        sys.exit(3)
    print(f'S: {response}', end='', flush=True)
    
    for j in cli_rp_addr(file): 
        msg = f'RCPT TO:{j}\r\n'
        s.sendall(msg.encode('ascii'))
        print(f'C: {msg}', end='', flush=True)
        response = s.recv(1024)
        response = response.decode('ascii')
        if response == '':
            msg = 'Connection lost\r\n'
            print(f'S: {msg}', end='', flush=True)
            sys.exit(3)
        print(f'S: {response}', end='', flush=True)
        
    msg = 'DATA\r\n'
    s.sendall(msg.encode('ascii'))
    print(f'C: {msg}', end='', flush=True)
    response = s.recv(1024)
    response = response.decode('ascii')
    if response == '':
        msg = 'Connection lost\r\n'
        print(f'S: {msg}', end='', flush=True)
        sys.exit(3)
    print(f'S: {response}', end='', flush=True) 
    for j in cli_get_data(file):
        msg = f'{j}\r\n'
        s.sendall(msg.encode('ascii'))
        print(f'C: {msg}', end='', flush=True)
        response = s.recv(1024)
        response = response.decode('ascii')
        if response == '':
            msg = 'Connection lost\r\n'
            print(f'S: {msg}', end='', flush=True)
            sys.exit(3)
        print(f'S: {response}', end='', flush=True)
    s.sendall('.\r\n'.encode('ascii'))
    print(f'C: .\r\n', end='', flush=True)
    response = s.recv(1024)
    response = response.decode('ascii')
    if response == '':
        msg = 'Connection lost\r\n'
        print(f'S: {msg}', end='', flush=True)
        sys.exit(3)
    print(f'S: {response}', end='', flush=True)
    
    msg = 'QUIT\r\n'
    s.sendall(msg.encode('ascii'))
    print(f'C: {msg}', end='', flush=True)
    response = s.recv(1024)
    response = response.decode('ascii')
    if response == '':
        msg = 'Connection lost\r\n'
        print(f'S: {msg}', end='', flush=True)
        sys.exit(3)
    print(f'S: {response}', end='', flush=True)
    r = response.split() 
    if r[0] == '221':
        s.close()
        
    
def cli_file_check(send_path) -> bool:
    if os.path.exists(send_path) and os.access(send_path, os.R_OK):
        file_ls = os.listdir(send_path)
        file_ls.sort() 
        for i in range(0, len(file_ls)):
            store = ''
            store += send_path + '/' + file_ls[i]
            file_ls[i] = store
        i = 0
        while i < len(file_ls):
            if os.path.isfile(file_ls[i]): 
                if os.access(file_ls[i], os.R_OK):
                    if not cli_spfile_check(file_ls[i]):
                        if i < len(file_ls) - 1: 
                            i += 1
                            continue
                        elif i == len(file_ls) - 1:
                            sys.exit(0)
                    else:
                        if i == len(file_ls) - 1:
                            return True
                else:
                    sys.exit(2)
            i += 1
    else:
        sys.exit(2)


def cli_manage_files(s, send_path):
    file_ls = os.listdir(send_path) 
    file_ls.sort() 
    for i in range(0, len(file_ls)):
        store = ''
        store += send_path + '/' + file_ls[i]
        file_ls[i] = store
    for i in range(0, len(file_ls)):
        cli_send_mail(s, file_ls[i])
        if i == len(file_ls) - 1:
            sys.exit(0)
        s = client_socket_setup()
        cli_ehlo(s)


def cli_has_auth(send_path) -> bool:
    file_ls = os.listdir(send_path)
    for i in range(0, len(file_ls)):
        store = ''
        store += send_path + '/' + file_ls[i]
        file_ls[i] = store
    for i in range(0, len(file_ls)):
        has_auth = re.search('.*auth.*', file_ls[i])
        if has_auth:
            return True
    return False


def cli_auth(s):
    msg = 'AUTH CRAM-MD5\r\n'
    s.sendall(msg.encode('ascii'))
    print(f'C: {msg}', end='', flush=True)
    
    r = s.recv(1024)
    r_check = r.decode('ascii')
    if r_check == '':
        msg = 'Connection lost\r\n'
        print(f'S: {msg}', end='', flush=True)
        sys.exit(3)
    r_dec = base64.b64decode(r).decode('ascii')
    r_enc = r_dec.encode('ascii')
    key = PERSONAL_SECRET.encode('ascii')
    client_hmac = hmac.new(key, r_enc, digestmod='md5').hexdigest()
    store = ''
    store += PERSONAL_ID + client_hmac
    client_enc = store.encode('ascii')
    client_msg = base64.b64encode(client_enc).decode('ascii')
    s.sendall(client_msg.encode('ascii'))
    print(f'C: {client_msg}', end='', flush=True)
    
    r = s.recv(1024)
    r = r.decode('ascii')
    print(f'S: {r}', end='', flush=True)


def main():
    cli_config_file_check()
    send_path = str(cli_config_file_check()[1])
    cli_file_check(send_path)
    
    s = client_socket_setup()
    
    cli_ehlo(s)
    
    if cli_has_auth(send_path):
        r = s.recv(1024)
        r = r.decode('ascii')
        if r == '':
            msg = 'Connection lost\r\n'
            print(f'S: {msg}', end='', flush=True)
            sys.exit(3)
        print(f'S: {r}', end='', flush=True)
        cli_auth(s)

    cli_manage_files(s, send_path)
    
        
if __name__ == '__main__':
    main()