#!/usr/bin/env python3
"""
Cliente remoto standalone para MC Control Panel.
UN SOLO ARCHIVO, solo libreria estandar. Funciona en Termux, Linux, Windows y Mac.
No necesita la carpeta control/ ni instalar nada.

Uso:
    python termux_remote.py                 (pide IP y puerto)
    python termux_remote.py 192.168.1.8     (puerto 25576 por defecto)
    python termux_remote.py 192.168.1.8 25576
"""

import re
import shutil
import socket
import sys
import time
import os
import json

END = '---END---'
DEFAULT_PORT = 25576
BLOCKS = '_.:-=+*#%@'
CLIENT_VERSION = "1.2"
UPDATE_JSON = "https://raw.githubusercontent.com/Lol1122334455/MC-CONTROL/main/actualizacion.json"
CLIENT_URL = "https://raw.githubusercontent.com/Lol1122334455/MC-CONTROL/main/termux_remote.py"


def _is_newer(a, b):
    try:
        pa = [int(x) for x in str(a).split('.')]
        pb = [int(x) for x in str(b).split('.')]
        return pa > pb
    except:
        return str(a) != str(b)


def self_update():
    try:
        import urllib.request
        req = urllib.request.Request(UPDATE_JSON, headers={'User-Agent': 'MC-Control-Termux/1.0'})
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read().decode())
        latest = str(data.get('termux', '')).lstrip('v')
        if not latest or not _is_newer(latest, CLIENT_VERSION):
            return False
        box('ACTUALIZACION', ['Nueva version del cliente: ' + latest, '', 'Descargando...'])
        req2 = urllib.request.Request(CLIENT_URL, headers={'User-Agent': 'MC-Control-Termux/1.0'})
        with urllib.request.urlopen(req2, timeout=60) as r2:
            blob = r2.read()
        if not blob.startswith(b'#!/usr/bin/env python3'):
            return False
        me = os.path.abspath(sys.argv[0])
        tmp = me + '.new'
        with open(tmp, 'wb') as f:
            f.write(blob)
        os.replace(tmp, me)
        box('ACTUALIZACION', ['Listo. Reiniciando...'])
        time.sleep(1.5)
        os.execv(sys.executable, [sys.executable, me] + sys.argv[1:])
    except Exception:
        return False
    return True


def term_size():
    try:
        c = shutil.get_terminal_size()
        return max(40, c.columns), max(10, c.lines)
    except:
        return 80, 24


def clear():
    print('\033[2J\033[H', end='', flush=True)


def box(title, lines, subtitle=''):
    w, _h = term_size()
    bw = min(46, w - 2)
    inner = bw - 4
    out = []
    out.append('+' + '-' * (bw - 2) + '+')
    if title:
        out.append('| ' + title.center(inner) + ' |')
    if subtitle:
        out.append('| ' + subtitle.center(inner) + ' |')
    if title or subtitle:
        out.append('|' + '-' * (bw - 2) + '|')
    for ln in lines:
        out.append('| ' + ln.center(inner)[:inner] + ' |')
    out.append('+' + '-' * (bw - 2) + '+')
    for ln in out:
        print(ln.center(w).rstrip())


def masked_input(prompt):
    try:
        import getpass
        try:
            return getpass.getpass(prompt)
        except:
            pass
    except:
        pass
    return input(prompt)


def cline(text=''):
    w, _h = term_size()
    print(text.center(w).rstrip())


def center_input(label, mask=False, default=''):
    w, _h = term_size()
    pad = max(0, (w - len(label) - 24) // 2)
    prompt = ' ' * pad + label + ' '
    try:
        if mask:
            import getpass
            try:
                r = getpass.getpass(prompt)
                return r.strip() if r else default
            except:
                pass
        r = input(prompt)
        r = r.strip()
        return r if r else default
    except (KeyboardInterrupt, EOFError):
        return None


def connect_screen():
    clear()
    box('TERMUX REMOTE', ['by Control Fundencion', '', 'CONECTAR AL SERVIDOR'])
    print()
    host = center_input('IP:')
    if host is None:
        return None, None
    if not host:
        return None, None
    port_s = center_input('Puerto [25576]:', default='25576')
    if port_s is None:
        return None, None
    try:
        return host, int(port_s)
    except:
        cline('Puerto invalido.')
        time.sleep(1.5)
        return None, None


def spark(values, width=14):
    vals = (values or [])[-width:]
    if not vals or max(vals) <= 0:
        return '.' * width
    mx = max(vals)
    return ''.join(BLOCKS[min(int(v / mx * 9), 9)] for v in vals)


def fmt_size(b):
    try:
        b = int(b)
    except:
        return '?'
    for u in ['B', 'KB', 'MB', 'GB']:
        if b < 1024:
            return '{:.1f}{}'.format(b, u)
        b /= 1024.0
    return '{:.1f}TB'.format(b)


def fmt_time(s):
    try:
        s = int(s)
    except:
        return '?'
    d, s = divmod(s, 86400)
    h, s = divmod(s, 3600)
    m, s = divmod(s, 60)
    p = []
    if d:
        p.append('{}d'.format(d))
    if h:
        p.append('{}h'.format(h))
    if m:
        p.append('{}m'.format(m))
    if s and not d:
        p.append('{}s'.format(s))
    return ' '.join(p) or '0s'


def recv_line(sock, timeout=8):
    sock.settimeout(timeout)
    buf = b''
    try:
        while b'\n' not in buf:
            chunk = sock.recv(256)
            if not chunk:
                break
            buf += chunk
    except socket.timeout:
        pass
    return buf.decode('utf-8', errors='replace')


def recv_all(sock, timeout=10):
    sock.settimeout(timeout)
    buf = b''
    try:
        while True:
            chunk = sock.recv(4096)
            if not chunk:
                break
            buf += chunk
            if END.encode() in buf:
                break
    except socket.timeout:
        pass
    return buf.decode('utf-8', errors='replace').replace(END, '').strip()


def poll_stats(sock):
    try:
        sock.sendall(b'statsline\n')
        parts = recv_all(sock).split('|')
        if len(parts) < 7:
            return None
        d = {'online': parts[0] == 'ONLINE', 'ram': parts[1], 'cpu': parts[2],
             'nplayers': parts[3], 'names': parts[4], 'world': parts[5],
             'uptime': parts[6], 'role': parts[7] if len(parts) > 7 else '?',
             'cmds': parts[8] if len(parts) > 8 else '?'}
        return d
    except:
        return None


def login_screen(sock):
    while True:
        clear()
        box('TERMUX REMOTE', ['by Control Fundencion', '', 'INICIO DE SESION'])
        print()
        cline('[1] Entrar')
        cline('[2] Solicitud de registro')
        cline('[Q] Salir')
        op = center_input('Opcion:')
        if op is None or op.lower() in ('q', 'quit', 'exit'):
            return None
        if op == '2':
            if register_screen(sock):
                continue
            continue
        if op != '1':
            continue
        user = center_input('USUARIO:')
        if user is None:
            continue
        pw = center_input('CONTRASENA:', mask=True)
        if pw is None:
            continue
        if not user or not pw:
            cline('Completa ambos campos.')
            time.sleep(1.5)
            continue
        try:
            sock.sendall((user + '\n').encode())
        except:
            cline('Conexion perdida.')
            return None
        resp = recv_line(sock).strip()
        if 'Password:' not in resp:
            cline(resp)
            time.sleep(2)
            continue
        try:
            sock.sendall((pw + '\n').encode())
        except:
            cline('Conexion perdida.')
            return None
        resp = recv_all(sock).strip()
        m = re.search(r'\[(.*?)\]', resp)
        role = m.group(1) if m else '?'
        note = resp.split('].', 1)[1].strip() if '].' in resp else ''
        if 'Bienvenido' in resp:
            return {'user': user, 'role': role, 'note': note}
        cline(resp)
        time.sleep(2)


def register_screen(sock):
    while True:
        clear()
        box('SOLICITUD DE REGISTRO', ['LLENA LO NECESARIO'])
        print()
        nu = center_input('USUARIO:')
        if nu is None:
            return False
        if not nu:
            return False
        pw = center_input('CONTRASENA:', mask=True)
        if pw is None:
            return False
        pw2 = center_input('CONFIRMA CONTRASENA:', mask=True)
        if pw2 is None:
            return False
        if not nu or not pw or not pw2:
            cline('Completa todos los campos.')
            time.sleep(1.5)
            continue
        if pw != pw2:
            cline('Las claves no coinciden.')
            time.sleep(1.5)
            continue
        lv = center_input('Nivel [1]admin [2]usuario [3]invitado (2):', default='2')
        if lv is None:
            return False
        role = {'1': 'admin', '2': 'usuario', '3': 'invitado'}.get(lv.strip(), 'usuario')
        clear()
        box('SOLICITUD DE REGISTRO', ['Usuario: ' + nu, 'Nivel: ' + role, '', 'ENVIAR SOLICITUD'])
        print()
        cline('[E] Enviar  [Q] Cancelar')
        op = center_input('Opcion:')
        if op is None or op.lower() != 'e':
            return False
        try:
            sock.sendall('register {} {} {}\n'.format(nu, pw, role).encode())
            cline(recv_all(sock))
        except Exception as e:
            cline('Error: {}'.format(e))
        time.sleep(2)
        return True


def watch_mode(sock, n=20):
    print('(actualizando cada 2s - Ctrl+C para salir)')
    time.sleep(1)
    try:
        while True:
            try:
                sock.sendall('logs {}\n'.format(n).encode())
                logs = recv_all(sock)
            except:
                print('(conexion perdida)')
                return False
            print('\033[2J\033[H', end='')
            print(logs)
            print('--- actualizando... (Ctrl+C para salir) ---')
            time.sleep(2)
    except KeyboardInterrupt:
        print('\n(watch detenido)')
    return True


def read_key_line(prompt='> '):
    try:
        import termios
        import tty
    except:
        return None, None
    if not sys.stdin.isatty():
        return None, None
    try:
        fd = sys.stdin.fileno()
        old = termios.tcgetattr(fd)
    except:
        return None, None
    buf = ''
    try:
        tty.setraw(fd)
        sys.stdout.write(prompt)
        sys.stdout.flush()
        while True:
            ch = sys.stdin.read(1)
            if not ch:
                raise EOFError
            if ch in ('\r', '\n'):
                sys.stdout.write('\r\n')
                sys.stdout.flush()
                return buf, None
            o = ord(ch)
            if o == 3:
                raise KeyboardInterrupt
            if o in (127, 8):
                if buf:
                    buf = buf[:-1]
                    sys.stdout.write('\b \b')
                    sys.stdout.flush()
                continue
            if o < 32:
                if not buf:
                    return '', chr(o + 96)
                continue
            if ch.isprintable():
                buf += ch
                sys.stdout.write(ch)
                sys.stdout.flush()
    finally:
        try:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)
        except:
            pass


def info_lines(st, info, role, hist_ram, hist_players):
    if role == 'usuario':
        return ['Comandos restantes hoy:', '{}'.format(st.get('cmds', '?'))]
    cpu = st['cpu']
    cpu_txt = '?' if cpu == '-1' else '{}%'.format(cpu)
    lines = [
        '{} [{}]'.format(info['user'], role),
        'Clave: ******',
        'Estado: {}'.format('ONLINE' if st['online'] else 'OFFLINE'),
        'RAM: {}MB {}'.format(st['ram'], spark(hist_ram)),
        'CPU: {}'.format(cpu_txt),
        'Jug: {} {}'.format(st['nplayers'], (st['names'] or '-')),
        '{}'.format(spark(hist_players)),
        'Mundo: {} Up: {}'.format(fmt_size(st['world']), fmt_time(st['uptime'])),
    ]
    if info.get('note'):
        lines.append(info['note'])
    if role == 'invitado':
        lines.append('Solo lectura')
    return lines


def draw_split(st, info, role, hist_ram, hist_players, logs, last_out):
    w, _h = term_size()
    clear()
    info_l = info_lines(st, info, role, hist_ram, hist_players)
    bar = '[Ctrl+L] Logs  [Ctrl+W] Watch  [Ctrl+P] Jugadores  [Ctrl+Q] Salir'
    if w >= 100:
        lw = w - 36
        left = []
        for ln in logs[-12:]:
            left.append(ln[:lw])
        if last_out:
            left.append('-' * min(lw, 30))
            for ln in last_out[-6:]:
                left.append(ln[:lw])
        n = max(len(left), len(info_l))
        print('CONSOLA'.ljust(lw) + ' | ' + 'DATOS')
        for i in range(n):
            l = left[i] if i < len(left) else ''
            r = info_l[i] if i < len(info_l) else ''
            print(l.ljust(lw)[:lw] + ' | ' + r)
    else:
        box('DATOS', info_l)
        print('-' * w)
        for ln in logs[-8:]:
            print(ln[:w])
        if last_out:
            print('-' * 20)
            for ln in last_out[-5:]:
                print(ln[:w])
    print('-' * w)
    cline(bar)


def main_screen(sock, info):
    hist_ram, hist_players = [], []
    role = info['role']
    last_out = []
    many_logs = False
    use_raw = sys.stdin.isatty()
    try:
        import termios
    except:
        use_raw = False
    while True:
        st = poll_stats(sock)
        if st is None:
            cline('Se perdio la conexion.')
            time.sleep(1.5)
            return
        role = st.get('role') or role
        try:
            hist_ram.append(int(st['ram']))
            hist_players.append(int(st['nplayers']))
        except:
            pass
        hist_ram, hist_players = hist_ram[-20:], hist_players[-20:]
        try:
            sock.sendall('logs {}\n'.format(25 if many_logs else 10).encode())
            logs = recv_all(sock).splitlines()
        except:
            cline('Se perdio la conexion.')
            time.sleep(1.5)
            return
        draw_split(st, info, role, hist_ram, hist_players, logs, last_out)
        if use_raw:
            try:
                text, ctrl = read_key_line('> ')
            except KeyboardInterrupt:
                continue
            except (OSError, EOFError):
                use_raw = False
                continue
            if ctrl:
                c = ctrl.lower()
                if c == 'q':
                    try:
                        sock.sendall(b'quit\n')
                        recv_all(sock)
                    except:
                        pass
                    return
                elif c == 'l':
                    many_logs = not many_logs
                    continue
                elif c == 'w':
                    if not watch_mode(sock):
                        return
                    continue
                elif c == 'p':
                    try:
                        sock.sendall(b'players\n')
                        last_out = recv_all(sock).splitlines() or ['(nadie)']
                    except:
                        cline('Se perdio la conexion.')
                        time.sleep(1.5)
                        return
                    continue
                else:
                    continue
            if not (text or '').strip():
                continue
            try:
                sock.sendall((text.strip() + '\n').encode())
                last_out = recv_all(sock).splitlines() or ['(sin respuesta)']
            except:
                cline('Se perdio la conexion.')
                time.sleep(1.5)
                return
        else:
            try:
                text = input('> ').strip()
            except (KeyboardInterrupt, EOFError):
                return
            if text.lower() in ('q', 'quit', 'exit', 'salir'):
                try:
                    sock.sendall(b'quit\n')
                except:
                    pass
                return
            if text.lower() == 'watch':
                if not watch_mode(sock):
                    return
                continue
            if not text:
                continue
            try:
                sock.sendall((text + '\n').encode())
                last_out = recv_all(sock).splitlines()
            except:
                cline('Se perdio la conexion.')
                time.sleep(1.5)
                return


def main():
    clear()
    self_update()
    clear()
    if len(sys.argv) > 1:
        host = sys.argv[1]
        try:
            port = int(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_PORT
        except:
            cline('Puerto invalido')
            return
    else:
        host, port = connect_screen()
        if not host or not port:
            return
    clear()
    box('TERMUX REMOTE', ['Conectando a {}:{}...'.format(host, port)])
    try:
        s = socket.create_connection((host, port), timeout=10)
    except Exception as e:
        cline('No se pudo conectar: {}'.format(e))
        time.sleep(2)
        return
    banner = recv_line(s).strip()
    print(banner)
    s.settimeout(4)
    try:
        peek = s.recv(512).decode('utf-8', errors='replace')
    except socket.timeout:
        peek = ''
    if 'Sin usuarios' in peek:
        rest = recv_all(s, timeout=3)
        print((peek + rest).replace(END, '').strip())
        try:
            s.close()
        except:
            pass
        return
    info = login_screen(s)
    if not info:
        try:
            s.close()
        except:
            pass
        cline('Adios.')
        return
    main_screen(s, info)
    try:
        s.close()
    except:
        pass
    cline('Desconectado.')


if __name__ == '__main__':
    main()
