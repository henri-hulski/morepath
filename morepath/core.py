from .config import Config
from .mount import Mount
import morepath.directive
from morepath import generic
from .app import App
from .view import View
from .request import Request, Response, LinkMaker, NothingMountedLinkMaker
from .converter import Converter, IDENTITY_CONVERTER
from webob import Response as BaseResponse
from webob.exc import (
    HTTPException, HTTPNotFound, HTTPForbidden, HTTPMethodNotAllowed)
import morepath
from reg import mapply, KeyIndex, ClassIndex
from datetime import datetime, date
from time import mktime, strptime


assert morepath.directive  # we need to make the function directive work


def setup():
    """Set up core Morepath framework configuration.

    Returns a :class:`Config` object; you can then :meth:`Config.scan`
    the configuration of other packages you want to load and then
    :meth:`Config.commit` it.

    See also :func:`autoconfig` and :func:`autosetup`.

    :returns: :class:`Config` object.
    """
    config = Config()
    config.scan(morepath, ignore=['.tests'])
    return config


@App.function(generic.consume, object)
def traject_consume(request, model, lookup):
    traject = generic.traject(model, lookup=lookup)
    if traject is None:
        return None
    value, stack, traject_variables = traject.consume(request.unconsumed)
    if value is None:
        return None
    get_model, get_parameters = value
    variables = get_parameters(request.GET)
    context = generic.context(model, lookup=lookup)
    if context is None:
        return None
    variables.update(context)
    variables['parent'] = model
    variables['request'] = request
    variables.update(traject_variables)
    next_model = mapply(get_model, **variables)
    if next_model is None:
        return None
    request.unconsumed = stack
    return next_model


@App.function(generic.link, object)
def link(request, model, mounted):
    result = []
    parameters = {}
    while mounted is not None:
        path, params = generic.path(model, lookup=mounted.lookup)
        result.append(path)
        parameters.update(params)
        model = mounted
        mounted = mounted.parent
    result.append(request.script_name)
    result.reverse()
    return '/'.join(result).strip('/'), parameters


@App.function(generic.linkmaker, object)
def linkmaker(request, mounted):
    return LinkMaker(request, mounted)


@App.function(generic.linkmaker, type(None))
def none_linkmaker(request, mounted):
    return NothingMountedLinkMaker(request)


@App.function(generic.traject, App)
def app_traject(app):
    return app.traject


@App.function(generic.traject, Mount)
def mount_traject(model):
    return model.app.registry.traject


@App.function(generic.context, Mount)
def mount_context(mount):
    return mount.create_context()


@App.function(generic.response, object)
def get_response(request, obj):
    view = generic.view.component(request, obj, lookup=request.lookup)
    # XXX hardcoded shortcut to deal with view functions... ugh
    # instead look into defining view separately from view content
    # generation?
    if not isinstance(view, View):
        return view(request, obj)
    if view is None or view.internal:
        return None
    if (view.permission is not None and
        not generic.permits(request.identity, obj, view.permission,
                            lookup=request.lookup)):
        raise HTTPForbidden()
    content = view(request, obj)
    if isinstance(content, BaseResponse):
        # the view took full control over the response
        return content
    # XXX consider always setting a default render so that view.render
    # can never be None
    if view.render is not None:
        response = view.render(content, request)
    else:
        response = Response(content, content_type='text/plain')
    request.run_after(response)
    return response


@App.function(generic.permits, object, object, object)
def has_permission(identity, model, permission):
    return False


@App.predicate(generic.view, name='model', default=None, index=ClassIndex)
def obj_predicate(obj):
    return obj.__class__


@App.predicate_fallback(generic.view, obj_predicate)
def obj_not_found(self, request):
    # this triggers a NotFound error later in the system
    return None


@App.predicate(generic.view, name='name', default='', index=KeyIndex,
               after=obj_predicate)
def name_predicate(request):
    return request.view_name


@App.predicate_fallback(generic.view, name_predicate)
def name_not_found(self, request):
    # this triggers a NotFound error later in the system
    return None


@App.predicate(generic.view, name='request_method', default='GET',
               index=KeyIndex, after=name_predicate)
def request_method_predicate(request):
    return request.method


@App.predicate_fallback(generic.view, request_method_predicate)
def method_not_allowed(self, request):
    raise HTTPMethodNotAllowed()


@App.converter(type=int)
def int_converter():
    return Converter(int)


@App.converter(type=type(u""))
def unicode_converter():
    return IDENTITY_CONVERTER


# Python 2
if type(u"") != type(""): # flake8: noqa
    @App.converter(type=type(""))
    def str_converter():
        # XXX do we want to decode/encode unicode?
        return IDENTITY_CONVERTER


def date_decode(s):
    return date.fromtimestamp(mktime(strptime(s, '%Y%m%d')))


def date_encode(d):
    return d.strftime('%Y%m%d')


@App.converter(type=date)
def date_converter():
    return Converter(date_decode, date_encode)


def datetime_decode(s):
    return datetime.fromtimestamp(mktime(strptime(s, '%Y%m%dT%H%M%S')))


def datetime_encode(d):
    return d.strftime('%Y%m%dT%H%M%S')


@App.converter(type=datetime)
def datetime_converter():
    return Converter(datetime_decode, datetime_encode)


@App.tween_factory()
def excview_tween_factory(app, handler):
    def excview_tween(request):
        try:
            response = handler(request)
        except Exception as exc:
            # XXX is there a nicer way to override predicates than
            # poking in the request?
            # default name and GET is correct for exception views.
            request.view_name = ''
            request.method = 'GET'
            response = generic.response(request, exc, lookup=app.lookup)
            if response is None:
                raise
            return response
        return response
    return excview_tween


@App.view(model=HTTPException)
def standard_exception_view(self, model):
    # webob HTTPException is a response already
    return self
