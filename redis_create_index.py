from manage_database import *
from redis.commands.search.field import *
from redis.commands.search.indexDefinition import IndexDefinition, IndexType

server = {
    'ipv4': '',
    'username': 'root',
    'password': '',
    'available': 1,
    'free': 0,
    'uuid': ''
}

def create_index():
    
    redis_client = get_redis_client()

    schema = (
        TextField('$.ipv4', as_name='ipv4'),
        TextField('$.username', as_name='username'),
        TextField('$.password', as_name='password'),
        NumericField('$.available', as_name='available'),
        NumericField('$.free', as_name='free'),
        TextField('$.uuid', as_name='uuid')
    )

    redis_client.ft().create_index(
        schema,
        definition=IndexDefinition(
            prefix=['server-'],
            index_type=IndexType.JSON)
    )