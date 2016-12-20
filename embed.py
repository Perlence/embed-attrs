from functools import reduce

import attr

EMBED_CLS_METADATA = '__embed_cls'
EMBED_PROMOTE_METADATA = '__embed_promote'


def embedding(maybe_cls=None, these=None, repr_ns=None, repr=True, cmp=True, hash=True, init=True, slots=False, frozen=False, str=False):
    def wrap(cls):
        try:
            orig_getattr = cls.__getattr__
        except AttributeError:
            __getattr__ = embedded_getattr
        else:
            def __getattr__(self, name):
                try:
                    return orig_getattr(self, name)
                except AttributeError:
                    return embedded_getattr(self, name)

        cls.__getattr__ = __getattr__
        return attr.s(cls, these, repr_ns, repr, cmp, hash, init, slots, frozen, str)

    if maybe_cls is None:
        return wrap
    else:
        return wrap(maybe_cls)


def embed(cls, promote=None, default=attr.NOTHING, validator=None,
          repr=True, cmp=True, hash=True, init=True, convert=None, metadata=None):
    if metadata is None:
        metadata = {}
    metadata[EMBED_CLS_METADATA] = cls
    if promote is not None:
        metadata[EMBED_PROMOTE_METADATA] = promote.replace(',', ' ').split()
    return attr.ib(default, validator, repr, cmp, hash, init, convert, metadata)


def embedded_getattr(self, name):
    embedded_attrs = [attrib for attrib in self.__attrs_attrs__
                      if attrib.metadata.get(EMBED_CLS_METADATA) is not None]

    promoted_attrs = reduce(lambda a, b: a.union(b),
                            [set(attrib.metadata.get(EMBED_PROMOTE_METADATA, []))
                             for attrib in embedded_attrs],
                            set())
    err = AttributeError("'{}' object has no attribute '{}'"
                         .format(type(self).__name__, name))
    if name.startswith('_') and name not in promoted_attrs:
        raise err

    for attrib in embedded_attrs:
        embedded_obj = getattr(self, attrib.name)
        try:
            return getattr(embedded_obj, name)
        except AttributeError:
            continue
    else:
        raise err


@attr.s
class Car:
    wheel_count = attr.ib(default=0)

    def number_of_wheels(self):
        return self.wheel_count

    def _sunder(self):
        return 'sunder'

    def __dunder__(self):
        return 'dunder'


@embedding
class Ferrari:
    car = embed(Car, promote='_sunder __dunder__')


def test_ferrari():
    f = Ferrari(Car(4))
    assert f.number_of_wheels() == 4
    assert f._sunder() == 'sunder'
    assert f.__dunder__() == 'dunder'

    c = Car(6)
    f.car = c
    assert f.number_of_wheels() == 6

    try:
        f.nonexistent
    except AttributeError as err:
        assert str(err) == "'Ferrari' object has no attribute 'nonexistent'"
