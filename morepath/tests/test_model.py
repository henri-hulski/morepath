import dectate
try:
    from urllib.parse import urlencode
except ImportError:
    # Python 2
    from urllib import urlencode
from morepath.path import get_arguments
from morepath.converter import Converter, IDENTITY_CONVERTER, ConverterRegistry
import morepath
from morepath import generic
from morepath.publish import consume as traject_consume
import webob


def setup_module(module):
    morepath.disable_implicit()


def consume(mount, path, parameters=None):
    if parameters:
        path += '?' + urlencode(parameters, True)
    request = mount.request(webob.Request.blank(path).environ)
    return traject_consume(mount, request), request


class Root(object):
    pass


class Model(object):
    pass


def test_register_path():
    class App(morepath.App):
        pass

    root = Root()

    def get_model(id):
        model = Model()
        model.id = id
        return model

    dectate.commit(App)

    path_registry = App.config.path_registry

    path_registry.register_path(
        Root, '', lambda m: {},
        None, None, None, False,
        lambda: root)
    path_registry.register_path(
        Model, '{id}', lambda model: {'id': model.id},
        None, None, None, False, get_model)

    app = App()

    obj, request = consume(app, 'a')
    assert obj.id == 'a'
    model = Model()
    model.id = 'b'
    assert generic.path(model, lookup=app.lookup) == ('b', {})


def test_register_path_with_parameters():
    class App(morepath.App):
        pass

    root = Root()

    def get_model(id, param='default'):
        model = Model()
        model.id = id
        model.param = param
        return model

    dectate.commit(App)

    path_registry = App.config.path_registry

    path_registry.register_path(
        Root, '', lambda m: {}, None, None, None, False,
        lambda: root)
    path_registry.register_path(
        Model, '{id}',
        lambda model: {'id': model.id, 'param': model.param},
        None, None, None, False, get_model)

    mount = App()

    obj, request = consume(mount, 'a')
    assert obj.id == 'a'
    assert obj.param == 'default'

    obj, request = consume(mount, 'a', {'param': 'value'})
    assert obj.id == 'a'
    assert obj.param == 'value'

    model = Model()
    model.id = 'b'
    model.param = 'other'
    assert generic.path(model, lookup=mount.lookup) == (
        'b', {'param': ['other']})


def test_traject_path_with_leading_slash():
    class App(morepath.App):
        pass

    root = Root()

    def get_model(id):
        model = Model()
        model.id = id
        return model

    dectate.commit(App)

    path_registry = App.config.path_registry

    path_registry.register_path(
        Root, '', lambda m: {}, None, None, None, False,
        lambda: root)
    path_registry.register_path(
        Model, '/foo/{id}', lambda model: {'id': model.id},
        None, None, None, False, get_model)

    mount = App()
    obj, request = consume(mount, 'foo/a')
    assert obj.id == 'a'
    obj, request = consume(mount, '/foo/a')
    assert obj.id == 'a'


def test_get_arguments():
    def foo(a, b):
        pass
    assert get_arguments(foo, []) == {'a': None, 'b': None}


def test_get_arguments_defaults():
    def foo(a, b=1):
        pass
    assert get_arguments(foo, []) == {'a': None, 'b': 1}


def test_get_arguments_exclude():
    def foo(a, b, request):
        pass
    assert get_arguments(foo, ['request']) == {'a': None, 'b': None}


def test_argument_and_explicit_converters_none_defaults():
    class MyConverterRegistry(ConverterRegistry):
        def converter_for_type(self, t):
            return IDENTITY_CONVERTER

        def converter_for_value(self, v):
            return IDENTITY_CONVERTER

    reg = MyConverterRegistry()

    assert reg.argument_and_explicit_converters({'a': None}, {}) == {
        'a': IDENTITY_CONVERTER}


def test_argument_and_explicit_converters_explicit():
    class MyConverterRegistry(ConverterRegistry):
        def converter_for_type(self, t):
            return IDENTITY_CONVERTER

        def converter_for_value(self, v):
            return IDENTITY_CONVERTER

    reg = MyConverterRegistry()

    assert reg.argument_and_explicit_converters(
        {'a': None}, {'a': Converter(int)}) == {'a': Converter(int)}


def test_argument_and_explicit_converters_from_type():
    class MyConverterRegistry(ConverterRegistry):
        def converter_for_type(self, t):
            return Converter(int)

        def converter_for_value(self, v):
            return IDENTITY_CONVERTER

    reg = MyConverterRegistry()

    assert reg.argument_and_explicit_converters({'a': None}, {'a': int}) == {
        'a': Converter(int)}
