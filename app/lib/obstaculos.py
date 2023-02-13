from itertools import groupby


def all_equal(iterable):
    g = groupby(iterable)
    return next(g, True) and not next(g, False)


def logic(res: int, redis):
    respuestasCorrectas = {
        '5': 0,
        '6': 0,
        '7': 1,
        '8': 1,
        '9': 2,
        '10': 2,
    }
    users = redis.smembers('players')
    usersNum = len(list(map(int, users)))
    index = redis.get('valorObstaculo')

    if int(redis.llen('obstaculos')) != usersNum:
        print('Se agrego una respuesta')
        redis.lpush('obstaculos', res)
        if int(redis.llen('obstaculos')) == usersNum:
            print('Respondieron igual')# noqa
            redis.set('respuestas', 'iguales')
            resAll = list(map(int, redis.lrange('obstaculos', 0, -1)))
            areEqual = all_equal(resAll)
            if areEqual:
                print(f'Respondieron: {resAll[0]}')
                comparacion = respuestasCorrectas[index]
                if comparacion == resAll[0]:
                    print('Respuesta Correcta')
                    # redis.set('respuestas', '')
                    redis.set('respuestaAcertada', 1)
                    redis.delete('obstaculos')
                    redis.lpush('estoRespondieron', 1)
                else:
                    print('Respuesta Incorrecta')
                    redis.delete('obstaculos')
                    # redis.set('respuestas', '')
                    redis.set('respuestaAcertada', 0)
                    redis.lpush('estoRespondieron', 0)
            else:
                # Aqui es el pop up
                print('Alguien contesto diferente')
                redis.set('respuestas', 'diferentes')
                redis.delete('obstaculos')
