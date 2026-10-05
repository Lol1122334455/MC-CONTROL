#!/usr/bin/env python3
"""
Cliente remoto standalone para MC Control Panel.
UN SOLO ARCHIVO, solo libreria estandar. Funciona en Termux, Linux, Windows y Mac.
No necesita la carpeta control/ ni instalar nada.

Uso:
    python termux_remote.py                 (pide IP y puerto)
    python termux_remote.py 192.168.1.8     (puerto 25576 por defecto)
    python termux_remote.py 192.168.1.8 25576

Comandos una vez conectado:
    <comando mc>   Enviar comando al servidor (say hola, stop, list...)
    status         Ver si el servidor esta online
    logs [n]       Ver ultimas n lineas del log (30 por defecto)
    players        Ver jugadores conectados
    watch [n]      Ver logs en vivo (se actualiza cada 2s, Ctrl+C para salir)
    help           Ayuda del servidor
    quit           Desconectar
"""

import socket
import sys
import time

END = '---END---'
DEFAULT_PORT = 25576


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
    print(recv_line(s).strip())
    probe = recv_line(s, timeout=2)
    if 'Password:' in probe:
        try:
            pw = input('Password: ')
        except (KeyboardInterrupt, EOFError):
            s.close()
            return
        s.sendall((pw + '\n').encode())
        result = recv_line(s).strip()
        print(result)
        if 'fallida' in result.lower():
            s.close()
            return
    print("Escribe 'help' para ver comandos, 'quit' para salir.")
    alive = True
    while alive:
        try:
            cmd = input('> ').strip()
        except (KeyboardInterrupt, EOFError):
            print()
            cmd = 'quit'
        if not cmd:
            continue
        low = cmd.lower()
        if low in ('quit', 'exit', 'salir'):
            try:
                s.sendall(b'quit\n')
                print(recv_all(s))
            except:
                pass
            alive = False
        elif low.startswith('watch'):
            parts = cmd.split()
            try:
                n = int(parts[1]) if len(parts) > 1 else 20
            except:
                n = 20
            if not watch_mode(s, n):
                alive = False
        else:
            try:
                s.sendall((cmd + '\n').encode())
                print(recv_all(s))
            except Exception as e:
                print('Error: {}'.format(e))
                alive = False
    try:
        s.close()
    except:
        pass
    print('Desconectado.')


if __name__ == '__main__':
    main()
