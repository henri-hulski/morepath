# -*- coding: utf-8 -*-

from comparch import Lookup, ClassRegistry
from morepath.interfaces import IConsumer, IResource, ResolveError, ModelError
from morepath.pathstack import parse_path, DEFAULT
from morepath.request import Request
from morepath.resolve import resolve_model, resolve_resource, Traverser
from werkzeug.test import EnvironBuilder
import pytest

def get_request(*args, **kw):
    return Request(EnvironBuilder(*args, **kw).get_environ())

def get_registry():
    return ClassRegistry()

def get_lookup(registry):
    return Lookup(registry)

class Container(dict):
    pass

class Model(object):
    def __repr__(self):
        return "<Model>"

def get_structure():
    """A structure of containers and models.

    The structure is:

    /a
    /sub
    /sub/b

    all starting at root.
    """

    root = Container()

    a = Model()
    root['a'] = a
    
    sub = Container()
    root['sub'] = sub
    
    b = Model()
    sub['b'] = b
    sub.attr = b
    
    return root

def test_resolve_no_consumers():
    lookup = get_lookup(get_registry())
    base = object()

    stack = parse_path(u'/a')
    obj, unconsumed, lookup = resolve_model(base, stack, lookup)

    assert obj is base
    assert unconsumed == [(DEFAULT, u'a')]
    assert lookup is lookup
    
def test_resolve_traverse():
    reg = get_registry()
    
    lookup = get_lookup(reg)

    reg.register(IConsumer, (Container,), Traverser(traverse_container))

    base = get_structure()

    assert resolve_model(base, parse_path(u'/a'), lookup) == (
        base['a'], [], lookup)
    assert resolve_model(base, parse_path(u'/sub'), lookup) == (
        base['sub'], [], lookup) 
    assert resolve_model(base, parse_path(u'/sub/b'), lookup) == (
        base['sub']['b'], [], lookup)

    # there is no /c
    assert resolve_model(base, parse_path(u'/c'), lookup) == (
        base, [(DEFAULT, u'c')], lookup)

    # there is a sub, but no c in sub
    assert resolve_model(base, parse_path(u'/sub/c'), lookup) == (
        base['sub'], [(DEFAULT, u'c')], lookup)
    
def test_resolve_resource():
    reg = get_registry()

    model = Model()

    def resource(request, model):
        return 'resource'
    
    reg.register(IResource, (Request, Model), resource)
    
    lookup = get_lookup(reg)

    req = get_request()
    assert resolve_resource(req, model, parse_path(u''), lookup) == 'resource'
    assert req.resolver_info()['name'] == u''
    req = get_request()
    # this will work for any name given the resource we registered
    assert resolve_resource(
        req, model, parse_path(u'something'), lookup) == 'resource'
    assert req.resolver_info()['name'] == u'something'
    
def test_resolve_errors():
    reg = get_registry()
    model = Model()

    lookup = get_lookup(reg)
    
    request = get_request()

    with pytest.raises(ModelError) as e:
        resolve_resource(request, model, parse_path(u'a/b'), lookup)
    assert str(e.value) == (
        "<Model> has unresolved path /a/b")
    
    with pytest.raises(ResolveError) as e:
        resolve_resource(request, model, [], lookup)
    assert str(e.value) == "<Model> has no default resource"
        
    with pytest.raises(ResolveError) as e:
        resolve_resource(request, model, parse_path(u'test'), lookup)
    assert str(e.value) == "<Model> has neither resource nor sub-model: /test"
    
def traverse_container(container, ns, name):
    if ns != DEFAULT:
        return None
    return container.get(name)

def traverse_attributes(container, ns, name):
    if ns != DEFAULT:
        return None
    return getattr(container, name, None)
