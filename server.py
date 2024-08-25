import os, socket, sys, time, hmac, base64, binascii, secrets
from datetime import datetime


# Visit https://edstem.org/au/courses/8961/lessons/26522/slides/196175 to get
PERSONAL_ID = '21C748'
PERSONAL_SECRET = '75137b2940d8cfccf33772a1bafb2778'


def config_file_check():
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
        inbox_path = ''
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
            elif line_split[0] == 'inbox_path':
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
                ip_ls = line_split[1].split('/')
                if ip_ls[0] == '~' or ip_ls[0] == '.':
                    home = os.path.expanduser('~')
                    ip_ls[0] = home
                    inbox_path += '/'.join(ip_ls)
                else:
                    inbox_path += str(line_split[1])
        if server_port == 0 or inbox_path == '':
            sys.exit(2)
    except IndexError:
        sys.exit(1)
    f.close()
    return [server_port, inbox_path]


def inbox_path_check(inbox_path) -> bool:
    if os.path.exists(inbox_path) and os.access(inbox_path, os.W_OK):
        return True
    else:
        sys.exit(2)


def socket_setup():
    port = int(config_file_check()[0])
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.settimeout(20)
    try:
        host = 'localhost'
        s.bind((host, port))
        s.listen()
        c, addr = s.accept()
    except TimeoutError:
        sys.exit(3)
    except socket.error:
        sys.exit(2)
    return c


def ehlo_resp_check(response) -> bool:
    resp_ls = str(response).split()
    if len(resp_ls) != 2:
        return False
    if resp_ls[0] != 'EHLO':
        return False
    c = 0
    for i in range(0, len(resp_ls[1])):
        if resp_ls[1][i] == '.':
            c += 1
    if c != 3:
        return False
    ls = resp_ls[1].split('.')
    if len(ls) != 4:
        return False
    for i in range(0, len(ls)):
        if ls[i] == '':
            return False
        elif not ls[i].isnumeric():
            return False
    return True


def arg_err(c):
    err_msg = '501 Syntax error in parameters or arguments\r\n'
    c.send(err_msg.encode('ascii'))
    print(f'S: {err_msg}', end='', flush=True)
    
    
def bad_seq_err(c):
    err_msg = '503 Bad sequence of commands\r\n'
    c.send(err_msg.encode('ascii'))
    print(f'S: {err_msg}', end='', flush=True)


def reset_file_content(file_content_ls):
    while len(file_content_ls) > 0:
        file_content_ls.remove(file_content_ls[0])

def ehlo(c):
    msg = f'250 127.0.0.1\r\n'
    msg2 = f'250 AUTH CRAM-MD5\r\n'
    msg3 = ''
    msg3 += msg + msg2
    c.send(msg3.encode('ascii'))
    print(f'S: {msg}', end='', flush=True)
    print(f'S: {msg2}', end='', flush=True)


def mail_check(response) -> bool:
    resp_ls = response.split(':')
    if resp_ls[0] != 'MAIL FROM':
        return False
    if resp_ls[1] == '\r\n':
        return False
    if len(resp_ls) != 2:
        return False
    s = ''
    has_addr_symbol = 0
    for i in range(0, len(resp_ls[1])):
        if resp_ls[1][i] == '\r':
            break
        if resp_ls[1][i] == '@':
            has_addr_symbol += 1
        if i == len(resp_ls[1]) - 1:
            if has_addr_symbol != 1:
                return False
        s += resp_ls[1][i]   
    resp_ls[1] = s
    if resp_ls[1][0] != '<' or resp_ls[1][-1] != '>':
        return False
    addr_split = resp_ls[1].split('@')  
    dot_string_split = addr_split[0].split('.')
    if not dot_string_split[0][1].isalpha() and not dot_string_split[0][1].isdigit():
        return False
    for i in range(1, len(dot_string_split[0])): 
        if not dot_string_split[0][i].isalpha() and not dot_string_split[0][i].isdigit() and dot_string_split[0][i] != '-':
            return False
    for i in range(1, len(dot_string_split)):
        if not dot_string_split[i][0].isalpha():
            return False
        for j in range(1, len(dot_string_split[i])):
            if not dot_string_split[i][j].isalpha() and not dot_string_split[i][j].isdigit() and dot_string_split[i][j] != '-':
                return False
    domain_ls = addr_split[1].split('.')  
    if len(domain_ls) == 4: 
        if domain_ls[0][0] != '[' or domain_ls[-1][-1] != ']':  
            return False
        s = domain_ls[0].removeprefix('[') 
        domain_ls[0] = s
        s = domain_ls[-1].removesuffix(']') 
        domain_ls[-1] = s
        for digit in domain_ls:  
            if not digit.isdigit():
                return False
    elif len(domain_ls) > 1:
        domain_ls[-1] = domain_ls[-1].removesuffix('>')
        for i in range(0, len(domain_ls)): 
            if not domain_ls[i][-1].isalpha() and not domain_ls[i][-1].isdigit():
                return False
            if not domain_ls[i][0].isalpha() and not domain_ls[i][0].isdigit():
                return False
            for j in range(0, len(domain_ls[i])-1):  
                if not domain_ls[i][j].isalpha() and not domain_ls[i][j].isdigit() and domain_ls[i][j] != '-':
                    return False
    else:
        return False
    return True


def mail(c, response, file_content_ls) -> bool:
    if mail_check(response):
        if len(file_content_ls) == 0:
            s = ''
            for i in range(0, len(response)):
                if response[i] == '\r':
                    break
                s += response[i]
            ls = s.split(':')
            store = ''
            store += 'From: ' + ls[1]
            file_content_ls.append(store)
            msg = '250 Requested mail action okay completed\r\n'
            c.send(msg.encode('ascii'))
            print(f'S: {msg}', end='', flush=True)
        else:
            bad_seq_err(c)
            return False
    else:
        arg_err(c)
        return False
    return True


def rcpt_check(response) -> bool:
    resp_ls = response.split(':') 
    if resp_ls[0] != 'RCPT TO':
        return False
    if resp_ls[1] == '\r\n': 
        return False
    if len(resp_ls) < 2:
        return False
    s = ''
    for i in range(0, len(resp_ls[1])):
        if resp_ls[1][i] == '\r':
            break
        s += resp_ls[1][i]          
    resp_ls[1] = s
    addr_ls = resp_ls[1].split(',')
    for i in range(0, len(addr_ls)):
        if addr_ls[i][0] != '<' or addr_ls[i][-1] != '>':
            return False
        addr_split = addr_ls[i].split('@')
        if len(addr_split) != 2:
            return False
        dot_string_split = addr_split[0].split('.')
        if not dot_string_split[0][1].isalpha() and not dot_string_split[0][1].isdigit():
            return False
        for i in range(1, len(dot_string_split[0])):
            if not dot_string_split[0][i].isalpha() and not dot_string_split[0][i].isdigit() and dot_string_split[0][i] != '-':
                return False
        for i in range(1, len(dot_string_split)):
            if not dot_string_split[i][0].isalpha():
                return False
            for j in range(1, len(dot_string_split[i])):
                if not dot_string_split[i][j].isalpha() and not dot_string_split[i][j].isdigit() and dot_string_split[i][j] != '-':
                    return False
        domain_ls = addr_split[1].split('.') 
        if len(domain_ls) == 4:
            if domain_ls[0][0] != '[' or domain_ls[-1][-1] != ']':
                return False
            s = domain_ls[0].removeprefix('[')
            domain_ls[0] = s
            s = domain_ls[-1].removesuffix(']')
            domain_ls[-1] = s
            for digit in domain_ls: 
                if not digit.isdigit():
                    return False
        elif len(domain_ls) > 1:
            domain_ls[-1] = domain_ls[-1].removesuffix('>')
            for i in range(0, len(domain_ls)):
                if not domain_ls[i][-1].isalpha() and not domain_ls[i][-1].isdigit():
                    return False
                if not domain_ls[i][0].isalpha() and not domain_ls[i][0].isdigit():
                    return False
                for j in range(0, len(domain_ls[i])-1):
                    if not domain_ls[i][j].isalpha() and not domain_ls[i][j].isdigit() and domain_ls[i][j] != '-':
                        return False
        else:
            return False
    return True


def rcpt(c, response, file_content_ls) -> bool:
    if file_content_ls == []:
        bad_seq_err(c)
        return False
    else:
        if rcpt_check(response):
            msg = '250 Requested mail action okay completed\r\n'
            c.send(msg.encode('ascii'))
            print(f'S: {msg}', end='', flush=True)
            s = ''
            for i in range(0, len(response)):
                if response[i] == '\r':
                    break
                s += response[i]
            ls = s.split(':')
            store = ''
            store += 'To: ' + ls[1]
            file_content_ls.append(store)
        else:
            arg_err(c)
            return False
    return True


def date(c, response, file_content_ls, mail_command_ls):
    resp_ls = response.split(':')
    if resp_ls[1] == '\r\n':
        file_content_ls.append('unknown.txt')
    else:
        date = ''
        for i in range (0, len(response)):
            if response[i] == '\r':
                break
            date += response[i]
        file_content_ls.append(date)
        msg = '354 Start mail input end <CRLF>.<CRLF>\r\n'
        c.send(msg.encode('ascii'))
        print(f'S: {msg}', end='', flush=True)
        mail_command_ls.append('Date')


def subject(c, response, file_content_ls, mail_command_ls):
    resp_ls = response.split(':')
    if resp_ls[1] == '\r\n':
        file_content_ls.append('Subject:')
    else:
        msg = '354 Start mail input end <CRLF>.<CRLF>\r\n'
        c.send(msg.encode('ascii'))
        print(f'S: {msg}', end='', flush=True)
        sub = ''
        for i in range(0, len(response)):
            if response[i] == '\r':
                break
            sub += response[i]
        file_content_ls.append(sub)
        mail_command_ls.append('Subject')
            
            
def write_file(inbox_path, file_content_ls):
    filename = ''
    dates = ''
    if file_content_ls[2] == 'unknown.txt':
        filename += inbox_path + '/' + file_content_ls[2]
        dates += 'Date:'
    else:
        dates += file_content_ls[2]
        dt = ''
        for i in range(0, len(file_content_ls[2])):
            if i < 6:
                continue
            dt += file_content_ls[2][i]
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
    filename = inbox_path + '/' + store
    file_content_ls[2] = dates
    f = open(filename, 'w')
    for i in range(0, len(file_content_ls)):
        s = ''
        for j in range(0, len(file_content_ls[i])):
            if file_content_ls[i][j] == '\r':
                break
            s += file_content_ls[i][j]
        f.write(s + '\n')
    f.close()                   

        
def data(c, response, file_content_ls, inbox_path, mail_command_ls):
    if response != 'DATA\r\n':
        arg_err(c)
    else:
        first_rep = 0
        date_count = 0
        sub = 0
        while True:
            first_rep += 1
            if first_rep == 1:
                msg = '354 Start mail input end <CRLF>.<CRLF>\r\n'
                c.send(msg.encode("ascii"))
                print(f'S: {msg}', end='', flush=True)
                continue
            elif first_rep > 1:
                r = c.recv(1024)
                r = r.decode()
                print(f'C: {r}', end='', flush=True)
                if r == '.\r\n':
                    msg = '250 Requested mail action okay completed\r\n'
                    c.send(msg.encode("ascii"))
                    print(f'S: {msg}', end='', flush=True)
                    write_file(inbox_path, file_content_ls)
                    break
                resp_ls = r.split(':') 
                if resp_ls[0] == 'Date':
                    date(c, r, file_content_ls, mail_command_ls)
                    date_count += 1
                elif resp_ls[0] == 'Subject':
                    subject(c, r, file_content_ls, mail_command_ls)
                    sub += 1
                else:
                    if date_count == 1 and sub == 1:
                        msg = '354 Start mail input end <CRLF>.<CRLF>\r\n'
                        c.send(msg.encode("ascii"))
                        print(f'S: {msg}', end='', flush=True)
                        s = ''
                        for i in range(0, len(r)):
                            if r[i] == '\r':
                                break
                            s += r[i]
                        file_content_ls.append(s)
                    elif date_count == 1 and sub == 0:
                        file_content_ls.append('Subject:')
                        s = ''
                        for i in range(0, len(r)):
                            if r[i] == '\r':
                                break
                            s += r[i]
                        file_content_ls.append(s)
        

def auth(c, response):
    if response == 'AUTH CRAM-MD5\r\n':
        challenge = secrets.token_hex(20)
        chal_encode = challenge.encode('ascii')
        chal_b64encode = base64.b64encode(chal_encode)
        chal_decode = chal_b64encode.decode('ascii')
        msg = f'334 {chal_decode}\r\n'
        c.send(msg.encode('ascii'))
        msg = f'334 {chal_decode}\r\n'
        print(f'S: {msg}', end='', flush=True)
        r = c.recv(1024)
        r_dec = r.decode('ascii')
        if r_dec == '*\r\n':
            arg_err(c)
        else:
            cli_resp = ''
            for i in range(0, len(r_dec)):
                if r_dec[i] == '\r':
                    break
                cli_resp += r_dec[i]
            cli_resp_encode = cli_resp.encode('ascii')
            can_decode = True
            try:
                c_keyed_digest = base64.b64decode(cli_resp_encode).decode('ascii')
            except binascii.Error:
                arg_err(c)
                can_decode = False
            if can_decode == True:
                key = PERSONAL_SECRET.encode('ascii')
                message = challenge.encode('ascii')
                ser_hmac = hmac.new(key, message, digestmod='md5').hexdigest()
                s_keyed_digest = ''
                s_keyed_digest += PERSONAL_ID + ' ' + str(ser_hmac)
                if c_keyed_digest == s_keyed_digest:
                    msg = '235 Authentication successful\r\n'
                    c.send(msg.encode('ascii'))
                    print(f'S: {msg}', end='', flush=True)
                else:
                    msg = '535 Authentication credentials invalid\r\n'
                    c.send(msg.encode('ascii'))
                    print(f'S: {msg}', end='', flush=True)
    else:
        err_msg = '504 Unrecognized authentication type\r\n'
        c.send(err_msg.encode('ascii'))
        print(f'S: {err_msg}', end='', flush=True)
        
        
def noop(c, response):
    if response != 'NOOP\r\n':
        err_msg = '501 Syntax error in parameters or arguments\r\n'
        c.send(err_msg.encode('ascii'))
        print(f'S: {err_msg}', end='', flush=True)
    else:
        msg = '250 Requested mail action okay completed\r\n'
        c.send(msg.encode('ascii'))
        print(f'S: {msg}', end='', flush=True)
        
        
def rset(c, file_content_ls, response) -> bool:
    if response != 'RSET\r\n':
        arg_err(c)
        return False
    else:
        while len(file_content_ls) > 0:
            file_content_ls.remove(file_content_ls[0])
        msg = '250 Requested mail action okay completed\r\n'
        c.send(msg.encode('ascii'))
        print(f'S: {msg}', end='', flush=True)
        return True
    

def quit(c, response) -> bool:
    if response == 'QUIT\r\n':
        msg = '221 Service closing transmission channel\r\n'
        c.send(msg.encode('ascii'))
        print(f'S: {msg}', end='', flush=True)
        c.close()
        return True
    else:
        arg_err(c)
        return False
    
    
def sigint(c, response):
    if response == 'SIGINT\r\n':
        msg = 'SIGINT received, closing\r\n'
        c.send(msg.encode('ascii'))
        print(f'S: {msg}', end='', flush=True)
        c.close()
        sys.exit(0)
    else:
        arg_err(c)


def main():
    c = socket_setup()
    inbox_path = str(config_file_check()[1])
    inbox_path_check(inbox_path)
    file_content_ls = []
    mail_command_ls = []
    
    msg = '220 Service ready\r\n'
    c.send(msg.encode('ascii'))
    print(f'S: {msg}', end='', flush=True)

    has_ehlo = False
    ehlo_count = 0
    has_mail = False
    has_rcpt = False
    while True:
        response = c.recv(1024)
        response = response.decode('ascii')
        if response == '':
            msg = 'Connection lost\r\n'
            print(f'S: {msg}', end='', flush=True)
            break
        else:
            print(f'C: {response}', end='', flush=True)
            comm = ''
            for i in range(0, 4):
                comm += response[i]
            if comm == 'EHLO':
                if ehlo_resp_check(response):
                    has_ehlo = True
                    ehlo_count += 1
                    ehlo(c)
                    if ehlo_count > 1:
                        ehlo_count = 1
                        reset_file_content(file_content_ls)
                else:
                    arg_err(c)
            if comm == 'RSET':
                if rset(c, file_content_ls, response):
                    ehlo_count = 1
                    has_mail = False
                    has_rcpt = False
            if comm == 'QUIT':
                if quit(c, response):
                    break
            if comm == 'MAIL':
                if has_ehlo == True:
                    if mail(c, response, file_content_ls):
                        has_mail = True
                        mail_command_ls.append(comm)
                else:
                    bad_seq_err(c)
            if comm == 'RCPT':
                if has_mail == True:
                    if rcpt(c, response, file_content_ls):
                        has_rcpt = True
                        mail_command_ls.append(comm)
                    else:
                        continue
                else:
                    bad_seq_err(c)
            if comm == 'DATA':
                if has_rcpt == True:
                    mail_command_ls.append(comm)
                    data(c, response, file_content_ls, inbox_path, mail_command_ls)
                else:
                    bad_seq_err(c)
            if comm == 'AUTH':
                if len(mail_command_ls) >= 5 or len(mail_command_ls) == 0:
                        auth(c, response)
                else:
                    bad_seq_err(c)
            if comm == 'NOOP':
                noop(c, response)
            if comm == 'SIGINT':
                sigint(c, response)
                    

if __name__ == '__main__':
    main()