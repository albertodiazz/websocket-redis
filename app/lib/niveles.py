import random
from array import array
from collections import Counter
import os


def handle_level_change_request(client_id, redis):
    # Verificar si hay algún otro cliente cambiando de nivel
    queue_key = "level_change_queue"
    if redis.exists(queue_key) == 0:
        # Agregar solicitud a la cola de mensajes en Redis
        redis.rpush(queue_key, client_id)
        print(f"Solicitud agregada a la cola por {client_id}")
        # Con esto solucionamos el doble click del cambio de niveles
        redis.expire('level_change_queue', int(os.getenv('Expire')))


def cambiarNivel(currentLevel: int,
                 redis,
                 clienteID=None):
    '''
        Cambiamos el nivel a siguiente
    '''
    valorObstaculo = int(redis.get('valorObstaculo'))

    if redis.exists('level_change_queue') == 0:
        handle_level_change_request(clienteID, redis)
        if currentLevel >= 0 and currentLevel <= 4 - 1:
            nextLevel = currentLevel
            if currentLevel == 4 - 1:
                levelRandom = random.sample(range(5, 10), 4)
                levelRandom = sorted(levelRandom, reverse=True)
                redis.lpush('random', 100)
                redis.lpush('random', *levelRandom)
                rand = redis.lrange('random', 0, -1)
                listInt = list(map(int, rand))
                toArray = array('i', listInt)
                nextLevel = toArray[0]
                print(f'random: {toArray}')
                print(f'toArray: {toArray[0]}')
                redis.set('valorObstaculo', nextLevel)
                redis.set('level', nextLevel)
            else:
                nextLevel += 1
                redis.delete('random')
                redis.set('level', nextLevel)
                redis.set('indexObstaculo', 0)
                redis.set('valorObstaculo', 0)
                redis.set('cronometro', 0)
            print('......')
            # print(f'nextLevel: {nextLevel}')

        elif currentLevel >= 6 - 1 and currentLevel <= 10 - 1: # noqa
            rand = redis.lrange('random', 0, -1)
            listInt = list(map(int, rand))
            toArray = array('i', listInt)

            print(f'random: {toArray}')
            redis.incr('indexObstaculo')
            nextLevel = toArray[int(redis.get('indexObstaculo'))]
            if int(redis.get('indexObstaculo')) < len(toArray)-1:
                valorObstaculo += 1
            elif int(redis.get('indexObstaculo')) >= len(toArray) - 1:
                nextLevel = 11
                # valorObstaculo += 0
            else:
                valorObstaculo += 0
            redis.set('valorObstaculo', nextLevel)
            redis.set('level', nextLevel)

            if nextLevel == 11:
                print('Estamos en el nivel 11')
                respuestasUsers = redis.lrange('estoRespondieron', 0, -1)
                resFinales = list(map(int, respuestasUsers))
                resultadoFinal = True if Counter(resFinales)[1] >= 3 else False
                redis.set('resultadoFinal', str(resultadoFinal))
                print(f'resultadoFinal: {resultadoFinal}')

        if currentLevel >= 12 - 1:
            print('Estamos en el nivel 12')
            # Esto lo solucione levantando una notificacion en redis
            # para que los clientes sepan que ya se activo el cronometro
            if int(redis.get('cronometro')) > 0:
                redis.set('level', 0)
            else:
                redis.set('level', 12)

    print(f"nextLevel: {redis.get('level')}")
