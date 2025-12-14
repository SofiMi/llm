
registered_users = set()

async def create_db_pool():
    global registered_users
    registered_users = set()
    return True

async def get_pool():
    return True
