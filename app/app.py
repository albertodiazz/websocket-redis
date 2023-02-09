import asyncio
import http
import websockets
import json
import redis
import datetime
import time
import threading
import socket
import struct
import os
from lib import niveles
from lib import joinUsers
from lib import obstaculos


r = redis.Redis(host='broker-redis', port=6379, db=0, decode_responses=True)

# Hay que comprobar que exista y si no lo creamos para evitar errores
r.set('valorObstaculo', 0) if r.exists('valorObstaculo') == 0 else None
r.set('level', 0) if r.exists('level') == 0 else None
r.set('respuestas', '') if r.exists('respuestas') == 0 else None
r.set('respuestaAcertada', 0) if r.exists('respuestaAcertada') == 0 else None
r.set('cronometro', 0) if r.exists('cronometro') == 0 else None


timer_lock = threading.Lock()
CLIENTS = set()


def cron_thread(CLIENTS, redis):
    print('start cronometro')
    time.sleep(5)
    if int(redis.get('cronometro')) > 0:
        redis.set('level', 0)
        redis.set('cronometro', 0)
        data = {
            'level': int(r.get('level')),
            'players': list(map(str, r.smembers('players'))),
            'respuestas': r.get('respuestas'),
            'respuestaAcertada': bool(int(r.get('respuestaAcertada'))),
            'indexObstaculo': int(r.get('indexObstaculo')),
            'resultadoFinal': bool(r.get('resultadoFinal')),
        }
        websockets.broadcast(CLIENTS, json.dumps(data))


async def handler(websocket):
    # De esta forma puedo agarrar al cliente por id o ip
    # las ventajas por ip es que no deja conectar mas clientes por ip
    # eso es bueno a nivel de control de jugadores, pero no permite debuguear
    # en una misma maquina
    CLIENTS.add(websocket)
    # El ping no funciona para que cada conexion realizada nuestro servidor
    # enseguida mande un ping
    await websocket.ping()
    # Esto nos sirve para poner al cliente en cola
    # y no dejar que cambien el nivel de forma simultanea
    if bool(int(os.getenv('Debug'))):
        idClientes = websocket.id.int
    else:
        idClientes = websocket.remote_address[0]

    while True:
        try:
            message = await websocket.recv()
            event = json.loads(message)

            if 'cambiarnivel' in event['type']:
                level = int(r.get('level'))
                try:
                    if int(event['message']) == 0:
                        # Regresamos a standby
                        r.set('valorObstaculo', 0)
                        r.set('level', 0)
                        r.delete('random')
                        r.delete('players')
                        r.set('indexObstaculo', 0)
                        nextLevel = r.get('level')
                        r.set('respuestas', '')
                        print(f'nextLevel: {nextLevel}')
                except KeyError:
                    if int(r.get('level')) >= 12-1 and int(r.get('cronometro')) == 0:# noqa
                        r.incr('cronometro')
                        r.set('level', 12)
                        timer_thread = threading.Thread(target=cron_thread,
                                                        args=(CLIENTS,
                                                              r))
                        timer_thread.start()
                    else:
                        r.set('respuestas', '')
                        niveles.cambiarNivel(level, r, idClientes)

            elif 'waituntil' in event['type']:
                '''
                    Aqui siempre esperamos a los jugadores para despues
                    generar una accion
                '''
                level = int(r.get('level'))
                # users = joinUsers.join(websocket, r)
                # Unirse = te cambio a nivel en automatico y agrego los ID
                if level == 2:
                    users = joinUsers.join(websocket, r)
                    if users == 4:
                        # Se unieron todos cambiamos el nivel en automatico
                        niveles.cambiarNivel(level, r)
                # TODO: PENTIENTE
                elif level >= 5 or level <= 10:
                    users = r.smembers('players')
                    clienteEnSesion = len(list(map(int, users)))
                    waitPlayers = joinUsers.joinTemporary(websocket, r)

                    if str(r.get('respuestas')) == 'diferentes':
                        # Pop up
                        # Esperamos a los demas
                        # Seteamos diferete '' esperando confiramacion de todos
                        if clienteEnSesion >= waitPlayers:
                            r.set('respuestas', '')
                            r.delete('playersTemporary')

                    elif str(r.get('respuestas')) == 'iguales':
                        # Respuestas
                        # Esperamos a los demas
                        # Seteamos iguales '' esperando confiramacion de todos
                        if clienteEnSesion >= waitPlayers:
                            r.set('respuestas', '')
                            r.delete('playersTemporary')
                            r.set('respuestas', '')
                            niveles.cambiarNivel(level, r, idClientes)

            elif 'obstaculos' in event['type']:
                '''
                    Aqui es donde seteamos las respuestas
                '''
                try:
                    obstaculos.logic(event['message'], r)
                except KeyError:
                    pass

            elif 'exituser' in event['type']:
                if bool(int(os.getenv('Debug'))):
                    r.srem('players', websocket.id.int)
                    print(f'ExitUser: {websocket.id.int}')
                else:
                    ipS = socket.inet_aton(websocket.remote_address[0])
                    ip = struct.unpack('!L', ipS)[0]
                    r.srem('players', ip)
                    print(f'ExitUser: {ip}')
                    # r.srem('players', websocket.remote_address[0])
                    # print(f'ExitUser: {websocket.remote_address[0]}')
                # Si hay menos de dos jugadores nos regresamos a standby
                numUsers = r.smembers('players')
                if len(list(map(int, numUsers))) <= 1:
                    print('hay muy poco jugadores')
                    r.delete('players')
                    r.set('level', 0)

            else:
                print('estas mandado el type incorrecto')

            # await websocket.send('hey')
        except websockets.ConnectionClosedOK:
            # Borramos al player que se desconecte
            CLIENTS.remove(websocket)
            if bool(int(os.getenv('Debug'))):
                r.srem('players', websocket.id.int)
                print(f'WebsocketCloseOK: {websocket.id.int}')
            else:
                ipS = socket.inet_aton(websocket.remote_address[0])
                ip = struct.unpack('!L', ipS)[0]
                r.srem('players', ip)
                print(f'WebsocketCloseError: {ip}')
                # r.srem('players', websocket.remote_address[0])
                # print(f'WebsocketCloseOK: {websocket.remote_address[0]}')
            break
        except websockets.exceptions.ConnectionClosedError:
            # TouchDesigner no desconecta bien el socket entonces
            # cuando Touch se desconecta usualmente marca error
            # Borramos al player que se desconecte
            CLIENTS.remove(websocket)
            if bool(int(os.getenv('Debug'))):
                r.srem('players', websocket.id.int)
                print(f'WebsocketCloseError: {websocket.id.int}')
            else:
                ipS = socket.inet_aton(websocket.remote_address[0])
                ip = struct.unpack('!L', ipS)[0]
                r.srem('players', ip)
                print(f'WebsocketCloseError: {ip}')
                # r.srem('players', websocket.remote_address[0])
                # print(f'WebsocketCloseError: {websocket.remote_address[0]}')
            break
        # Aqui es donde hacemos nuestro json y el broadcast
        # a todos los clientes para mandar siempre los cambios a todos

        data = {
            'level': int(r.get('level')),
            'players': list(map(str, r.smembers('players'))),
            'respuestas': r.get('respuestas'),
            'respuestaAcertada': bool(int(r.get('respuestaAcertada'))),
            'indexObstaculo': int(r.get('indexObstaculo')),
            'resultadoFinal': bool(r.get('resultadoFinal')),
        }
        websockets.broadcast(CLIENTS, json.dumps(data,
                                                 indent=4))
        # print(f'Cliente: {idClientes}')
        # print(data)
        # print(clientesID)


async def health_check(path, request_headers):
    if path == "/healthz":
        return http.HTTPStatus.OK, [], b"OK\n"


async def main():
    async with websockets.serve(handler, "", 8001,
                                process_request=health_check,
                                ping_interval=int(os.getenv('Ping', 20)),
                                ):
        await asyncio.Future()  # run forever


if __name__ == "__main__":
    try:
        version = websockets.version.version
        print(f'Websocket Version:{version} | {datetime.datetime.now()}')
        asyncio.run(main())
    except KeyboardInterrupt:
        exit()
