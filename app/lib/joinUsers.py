import os


def join(websocket, redis):
    '''
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
