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

import socket
import sys
import time

END = '---END---'
DEFAULT_PORT = 25576
BLOCKS = '_.:-=+*#%@'


def spark(values, width=16):
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
        raw = recv_all(sock)
        parts = raw.split('|')
        if len(parts) < 7:
            return None
        return {'online': parts[0] == 'ONLINE', 'ram': parts[1], 'cpu': parts[2],
                'nplayers': parts[3], 'names': parts[4], 'world': parts[5],
                'uptime': parts[6]}
    except:
        return None


def show_status(st, hist_ram, hist_players):
    print('=' * 44)
    if not st:
        print('Estado: SIN CONEXION')
        print('=' * 44)
        return
    print('Estado: {}'.format('ONLINE' if st['online'] else 'OFFLINE'))
    cpu = st['cpu']
    cpu_txt = '?' if cpu == '-1' else '{}%'.format(cpu)
    print('RAM: {}MB {} | CPU: {}'.format(st['ram'], spark(hist_ram), cpu_txt))
    print('Jugadores ({}): {}'.format(st['nplayers'],
                                      st['names'] if st['names'] else '-'))
    print('Grafica jugadores: {}'.format(spark(hist_players)))
    print('Mundo: {} | Uptime: {}'.format(fmt_size(st['world']), fmt_time(st['uptime'])))
    print('=' * 44)


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


def login_flow(sock):
    print('[1] Entrar')
    print('[2] Solicitar registro')
    try:
        op = input('Opcion: ').strip()
    except (KeyboardInterrupt, EOFError):
        return None
    if op == '2':
        try:
            nu = input('Nombre de usuario: ').strip()
            pw = input('Clave: ').strip()
        except (KeyboardInterrupt, EOFError):
            return None
        if not nu or not pw:
            print('Datos invalidos.')
            return None
        try:
            sock.sendall('register {} {}\n'.format(nu, pw).encode())
            print(recv_all(sock))
        except Exception as e:
            print('Error: {}'.format(e))
        return None
    try:
        user = input('Usuario: ').strip()
    except (KeyboardInterrupt, EOFError):
        return None
    if not user:
        return None
    try:
        sock.sendall((user + '\n').encode())
    except:
        print('Conexion perdida.')
        return None
    resp = recv_line(sock).strip()
    if 'Password:' not in resp:
        print(resp)
        return None
    try:
        pw = input('Password: ').strip()
    except (KeyboardInterrupt, EOFError):
        return None
    try:
        sock.sendall((pw + '\n').encode())
    except:
        print('Conexion perdida.')
        return None
    resp = recv_all(sock).strip()
    print(resp)
    if 'Bienvenido' in resp:
        return user
    return None


def main_menu(sock, user):
    hist_ram, hist_players = [], []
    while True:
        st = poll_stats(sock)
        if st is None:
            print('Se perdio la conexion.')
            return
        try:
            hist_ram.append(int(st['ram']))
            hist_players.append(int(st['nplayers']))
        except:
            pass
        hist_ram, hist_players = hist_ram[-20:], hist_players[-20:]
        print('\n--- {} ---'.format(user))
        show_status(st, hist_ram, hist_players)
        print('[1] Comando  [2] Logs  [3] Watch  [4] Actualizar  [5] Salir')
        try:
            op = input('> ').strip().lower()
        except (KeyboardInterrupt, EOFError):
            print()
            op = '5'
        if op == '1':
            try:
                cmd = input('Comando: ').strip()
            except (KeyboardInterrupt, EOFError):
                continue
            if not cmd:
                continue
            try:
                sock.sendall((cmd + '\n').encode())
                print(recv_all(sock))
            except:
                print('Se perdio la conexion.')
                return
            try:
                input('(Enter para continuar)')
            except (KeyboardInterrupt, EOFError):
                pass
        elif op == '2':
            try:
                n = input('Lineas [30]: ').strip() or '30'
            except (KeyboardInterrupt, EOFError):
                continue
            try:
                sock.sendall(('logs {}\n'.format(n)).encode())
                print(recv_all(sock))
            except:
                print('Se perdio la conexion.')
                return
            try:
                input('(Enter para continuar)')
            except (KeyboardInterrupt, EOFError):
                pass
        elif op == '3':
            if not watch_mode(sock):
                return
        elif op == '4':
            continue
        elif op in ('5', 'quit', 'exit', 'salir', 'q'):
            try:
                sock.sendall(b'quit\n')
                print(recv_all(sock))
            except:
                pass
            return
        else:
            print('Opcion invalida.')


def main():
    host = sys.argv[1] if len(sys.argv) > 1 else input('IP del servidor: ').strip()
    if not host:
        print('IP invalida')
        return
    try:
        port = int(sys.argv[2]) if len(sys.argv) > 2 else int((input('Puerto [25576]: ').strip() or '25576'))
    except:
        print('Puerto invalido')
        return
    print('Conectando a {}:{}...'.format(host, port))
    try:
        s = socket.create_connection((host, port), timeout=10)
    except Exception as e:
        print('No se pudo conectar: {}'.format(e))
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
    user = login_flow(s)
    if not user:
        try:
            s.close()
        except:
            pass
        print('Adios.')
        return
    main_menu(s, user)
    try:
        s.close()
    except:
        pass
    print('Desconectado.')


if __name__ == '__main__':
    main()
