import os


def joinTemporary(websocket, redis):
    '''
        Aqui se unen los jugadores de forma temporal

        RETURN:
            len() : De los jugadores unidos
    '''
    # redis.sadd  Specified members that are already a member of this set
    # are ignored. If key does not exist, a new set is created before adding
    # the specified members.
    if bool(int(os.getenv('Debug'))):
        redis.sadd('playersTemporary', websocket.id.int)
    else:
        redis.sadd('playersTemporary', websocket.remote_address[0])
    clientesID = redis.smembers('playersTemporary')
    print(f"playersTemporary: {clientesID}")
    return len(list(map(int, clientesID)))


def join(websocket, redis):
    '''
        Aqui se unen los jugadores de forma permanente

        RETURN:
            len() : De los jugadores unidos
    '''
    # redis.sadd  Specified members that are already a member of this set
    # are ignored. If key does not exist, a new set is created before adding
    # the specified members.
    if bool(int(os.getenv('Debug'))):
        redis.sadd('players', websocket.id.int)
    else:
        redis.sadd('players', websocket.remote_address[0])
    clientesID = redis.smembers('players')
    print(f"players: {clientesID}")
    return len(list(map(int, clientesID)))
