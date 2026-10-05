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

END = '---END---'
DEFAULT_PORT = 25576
BLOCKS = '_.:-=+*#%@'


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
        box('TERMUX REMOTE', ['by Control Fundencion', '', 'INICIO DE SESION'],
            subtitle='')
        print()
        print('  [1] Entrar')
        print('  [2] Solicitud de registro')
        print('  [Q] Salir')
        try:
            op = input('  Opcion: ').strip().lower()
        except (KeyboardInterrupt, EOFError):
            return None
        if op in ('q', 'quit', 'exit'):
            return None
        if op == '2':
            if register_screen(sock):
                continue
            continue
        if op != '1':
            continue
        try:
            user = input('  USUARIO: ').strip()
            pw = masked_input('  CONTRASENA: ').strip()
        except (KeyboardInterrupt, EOFError):
            continue
        if not user or not pw:
            print('  Completa ambos campos.')
            time.sleep(1.5)
            continue
        try:
            sock.sendall((user + '\n').encode())
        except:
            print('  Conexion perdida.')
            return None
        resp = recv_line(sock).strip()
        if 'Password:' not in resp:
            print('  ' + resp)
            time.sleep(2)
            continue
        try:
            sock.sendall((pw + '\n').encode())
        except:
            print('  Conexion perdida.')
            return None
        resp = recv_all(sock).strip()
        m = re.search(r'\[(.*?)\]', resp)
        role = m.group(1) if m else '?'
        note = resp.split('].', 1)[1].strip() if '].' in resp else ''
        if 'Bienvenido' in resp:
            return {'user': user, 'role': role, 'note': note}
        print('  ' + resp)
        time.sleep(2)


def register_screen(sock):
    while True:
        clear()
        box('SOLICITUD DE REGISTRO', ['LLENA LO NECESARIO'])
        print()
        try:
            nu = input('  USUARIO: ').strip()
            if not nu:
                return False
            pw = masked_input('  CONTRASENA: ').strip()
            pw2 = masked_input('  CONFIRMA CONTRASENA: ').strip()
        except (KeyboardInterrupt, EOFError):
            return False
        if not nu or not pw or not pw2:
            print('  Completa todos los campos.')
            time.sleep(1.5)
            continue
        if pw != pw2:
            print('  Las claves no coinciden.')
            time.sleep(1.5)
            continue
        clear()
        box('SOLICITUD DE REGISTRO', ['Usuario: ' + nu, '', 'ENVIAR SOLICITUD'])
        print()
        print('  [E] Enviar  [Q] Cancelar')
        try:
            op = input('  Opcion: ').strip().lower()
        except (KeyboardInterrupt, EOFError):
            return False
        if op != 'e':
            return False
        try:
            sock.sendall('register {} {}\n'.format(nu, pw).encode())
            print('  ' + recv_all(sock))
        except Exception as e:
            print('  Error: {}'.format(e))
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


def options_menu(sock, info):
    role = info['role']
    while True:
        clear()
        box('OPCIONES', ['Usuario: {} [{}]'.format(info['user'], role)])
        print()
        opts = []
        if role != 'invitado':
            opts.append('[1] Enviar comando')
        else:
            opts.append('[1] Enviar comando (no permitido)')
        opts += ['[2] Ver logs', '[3] Watch en vivo', '[4] Volver']
        for o in opts:
            print('  ' + o)
        try:
            op = input('  Opcion: ').strip()
        except (KeyboardInterrupt, EOFError):
            return True
        if op == '1' and role != 'invitado':
            try:
                cmd = input('  Comando: ').strip()
            except (KeyboardInterrupt, EOFError):
                continue
            if not cmd:
                continue
            try:
                sock.sendall((cmd + '\n').encode())
                print(recv_all(sock))
            except:
                print('  Se perdio la conexion.')
                return False
            try:
                input('  (Enter para continuar)')
            except (KeyboardInterrupt, EOFError):
                pass
        elif op == '2':
            try:
                n = input('  Lineas [30]: ').strip() or '30'
            except (KeyboardInterrupt, EOFError):
                continue
            try:
                sock.sendall(('logs {}\n'.format(n)).encode())
                print(recv_all(sock))
            except:
                print('  Se perdio la conexion.')
                return False
            try:
                input('  (Enter para continuar)')
            except (KeyboardInterrupt, EOFError):
                pass
        elif op == '3':
            if not watch_mode(sock):
                return False
        elif op == '4':
            return True
        else:
            print('  Opcion invalida o no permitida.')


def main_screen(sock, info):
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
        clear()
        role = st.get('role') or info['role']
        cmds = st.get('cmds', '?')
        cpu = st['cpu']
        cpu_txt = '?' if cpu == '-1' else '{}%'.format(cpu)
        lines = [
            'Usuario: {} [{}]  Clave: ******'.format(info['user'], role),
            '',
            'Estado: {}'.format('ONLINE' if st['online'] else 'OFFLINE'),
            'RAM: {}MB {}  CPU: {}'.format(st['ram'], spark(hist_ram), cpu_txt),
            'Jugadores ({}): {}'.format(st['nplayers'], st['names'] or '-'),
            '{}'.format(spark(hist_players)),
            'Mundo: {}  Up: {}'.format(fmt_size(st['world']), fmt_time(st['uptime'])),
        ]
        if info.get('note'):
            lines.append(info['note'])
        if role == 'usuario' and cmds != '?':
            lines.append('Comandos restantes hoy: {}'.format(cmds))
        if role == 'invitado':
            lines.append('Invitado: solo lectura (sin comandos)')
        box('TERMUX REMOTE', lines)
        print()
        print('  [Ctrl+C] Opciones   [5] Salir')
        try:
            op = input('  > ').strip().lower()
        except KeyboardInterrupt:
            if not options_menu(sock, dict(info, role=role)):
                return
            continue
        except EOFError:
            op = '5'
        if op in ('5', 'quit', 'exit', 'salir', 'q'):
            try:
                sock.sendall(b'quit\n')
                print(recv_all(sock))
            except:
                pass
            return
        elif op in ('1', '2', '3', '4'):
            if not options_menu(sock, dict(info, role=role)):
                return
        else:
            print('  Escribe el numero o pulsa Ctrl+C para opciones.')


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
    info = login_screen(s)
    if not info:
        try:
            s.close()
        except:
            pass
        print('Adios.')
        return
    main_screen(s, info)
    try:
        s.close()
    except:
        pass
    print('Desconectado.')


if __name__ == '__main__':
    main()
