from .fixtures import basic, nested
from morepath import setup
from morepath.config import Config
from morepath.request import Response
from werkzeug.test import Client

def test_basic():
    setup()
    
    config = Config()
    config.scan(basic)
    config.commit()
    
    c = Client(basic.app, Response)
    
    response = c.get('/foo')

    assert response.data == 'The resource for model: foo'

    response = c.get('/foo/link')
    assert response.data == 'foo'

def test_nested():
    setup()
    
    config = Config()
    config.scan(nested)
    config.commit()
    
    c = Client(nested.outer_app, Response)

    response = c.get('/inner/foo')

    assert response.data == 'The resource for model: foo'

    response = c.get('/inner/foo/link')
    assert response.data == 'inner/foo'
