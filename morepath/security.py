"""This module defines the authentication system of Morepath.

Authentication is done by establishing an identity for a request using
an identity policy registered by the :meth:`morepath.App.identity_policy`
directive.

:data:`morepath.NO_IDENTITY`, :class:`morepath.Identity`,
:class:`morepath.IdentityPolicy` are part of the public API.
"""

from reg import mapply

from .app import RegRegistry
from .settings import SettingRegistry


class NoIdentity(object):
    """The user is not yet logged in.

    The request is anonymous.
    """
    userid = None


NO_IDENTITY = NoIdentity()
"""The identity if the request is anonymous.

The user has not yet logged in.
"""


class IdentityPolicyRegistry(object):
    """Register the current identity policy.

    Used by the :class:`morepath.App.identity_policy` directive.

    :param reg_registry: a :class:`reg.Registry` instance.
    :param setting_registry: a :class:`morepath.settings.SettingRegistry`
      instance.
    """
    factory_arguments = {
        'reg_registry': RegRegistry,
        'setting_registry': SettingRegistry,
    }

    def __init__(self, reg_registry, setting_registry):
        self.reg_registry = reg_registry
        self.setting_registry = setting_registry
        self.identity_policy = None

    def register_identity_policy_function(self, factory, dispatch, name):
        """Register a method from the identity policy as a function.

        The identity policy is registered as a class, but their methods
        are really registered with dispatch functions that are then
        exposed to the public API and are used in the framework.

        :param factory: factory to create identity policy instance,
          typically the identity policy class object.
        :param dispatch: the dispatch function we want to register
          a method on.
        :param name: the name of the method to register.
        """
        # make sure we only have a single identity policy
        identity_policy = self.identity_policy
        if identity_policy is None:
            self.identity_policy = identity_policy = mapply(
                factory,
                settings=self.setting_registry)
        self.reg_registry.register_function(
            dispatch,
            getattr(identity_policy, name))


class Identity(object):
    """Claimed identity of a user.

    Note that this identity is just a claim; to authenticate the user
    and authorize them you need to implement Morepath permission directives.
    """
    def __init__(self, userid, **kw):
        """
        :param userid: The userid of this identity
        :param kw: Extra information to store in identity.
        """
        self.userid = userid
        self._names = kw.keys()
        for key, value in kw.items():
            setattr(self, key, value)
        self.verified = None  # starts out as never verified

    def as_dict(self):
        """Export identity as dictionary.

        This includes the userid and the extra keyword parameters used
        when the identity was created.

        :return: dict with identity info.
        """
        result = {'userid': self.userid}
        for name in self._names:
            result[name] = getattr(self, name)
        return result


class IdentityPolicy(object):
    """Identity policy API.

    Implement this API if you want to have a custom way to establish
    identities for users in your application.
    """

    def identify(self, request):
        """Establish what identity this user claims to have from request.

        :param request: Request to extract identity information from.
        :type request: :class:`morepath.Request`.
        :return: :class:`morepath.security.Identity` instance or
          :attr:`morepath.security.NO_IDENTITY` if identity cannot
          be established.
        """
        raise NotImplementedError()  # pragma: nocoverage

    def remember(self, response, request, identity):
        """Remember identity on response.

        Implements ``morepath.remember_identity``, which is called
        from user login code.

        Given an identity object, store it on the response, for
        instance as a cookie. Some policies may not do any storing but
        instead retransmit authentication information each time in the
        request.

        :param response: response object on which to store identity.
        :type response: :class:`morepath.Response`
        :param request: request object.
        :type request: :class:`morepath.Request`
        :param identity: identity to remember.
        :type identity: :class:`morepath.security.Identity`

        """
        raise NotImplementedError()  # pragma: nocoverage

    def forget(self, response, request):
        """Forget identity on response.

        Implements ``morepath.forget_identity``, which is called from
        user logout code.

        Remove identifying information from the response. This could
        delete a cookie or issue a basic auth re-authentication.

        :param response: response object on which to forget identity.
        :type response: :class:`morepath.Response`
        :param request: request object.
        :type request: :class:`morepath.Request`

        """
        raise NotImplementedError()  # pragma: nocoverage
