from functools import reduce, partialmethod

import attr
import pytest

EMBED_CLS_METADATA = '__embed_cls'
EMBED_PROMOTE_METADATA = '__embed_promote'


def embedding(maybe_cls=None, these=None, repr_ns=None, repr=True, cmp=True, hash=True, init=True, slots=False, frozen=False, str=False):
    def wrap(cls):
        cls_with_attrs = attr.s(cls, these, repr_ns, repr, cmp, hash, init, slots, frozen, str)

        try:
            orig_getattr = cls_with_attrs.__getattr__
        except AttributeError:
            __getattr__ = embedded_getattr
        else:
            def __getattr__(self, name):
                try:
                    return orig_getattr(self, name)
                except AttributeError:
                    return embedded_getattr(self, name)
        cls_with_attrs.__getattr__ = __getattr__

        if not frozen:
            orig_setattr = cls_with_attrs.__setattr__
            __setattr__ = partialmethod(embedded_setattr, orig_setattr=orig_setattr)
            cls_with_attrs.__setattr__ = __setattr__

        return cls_with_attrs

    if maybe_cls is None:
        return wrap
    else:
        return wrap(maybe_cls)


def embed(cls, promote=None, default=attr.NOTHING, validator=None,
          repr=True, cmp=True, hash=True, init=True, convert=None, metadata=None):
    if not attr.has(cls):
        raise TypeError("embedded class '{}' must have attrs attributes".format(cls.__name__))
    if metadata is None:
        metadata = {}
    metadata[EMBED_CLS_METADATA] = cls
    if promote is not None:
        metadata[EMBED_PROMOTE_METADATA] = promote.replace(',', ' ').split()
    return attr.ib(default, validator, repr, cmp, hash, init, convert, metadata)


def embedded_getattr(self, name):
    embedded_attrs = filter_embedded_attrs(attr.fields(type(self)))

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


def embedded_setattr(self, name, value, orig_setattr, top=True):
    fields = attr.fields(type(self))
    names = (attrib.name for attrib in fields)
    if name in names:
        orig_setattr(self, name, value)
        return

    embedded_attrs = filter_embedded_attrs(fields)
    for attrib in embedded_attrs:
        embedded_obj = getattr(self, attrib.name)
        try:
            embedded_setattr(embedded_obj, name, value, orig_setattr, top=False)
            return
        except AttributeError:
            continue

    if top:
        orig_setattr(self, name, value)
    else:
        raise AttributeError("'{}' object has no attribute '{}'"
                             .format(type(self).__name__, name))


def filter_embedded_attrs(attrs):
    return tuple(attrib for attrib in attrs
                 if attrib.metadata.get(EMBED_CLS_METADATA) is not None)


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

    with pytest.raises(AttributeError) as excinfo:
        f.nonexistent
    assert str(excinfo.value) == "'Ferrari' object has no attribute 'nonexistent'"

    class NonAttr:
        pass
    with pytest.raises(TypeError) as excinfo:
        embed(NonAttr)
    assert 'must have attrs' in str(excinfo.value)

    f.wheel_count = 8
    assert f.car.wheel_count == 8
    with pytest.raises(AttributeError):
        object.__getattribute__(f, 'wheel_count')

    f.nonexistent = 'not anymore'
    assert object.__getattribute__(f, 'nonexistent') is 'not anymore'

    @embedding(frozen=True)
    class FrozenCar:
        car = embed(Car)

    fc = FrozenCar(Car(4))
    with pytest.raises(attr.exceptions.FrozenInstanceError):
        fc.car = Car(3)
    with pytest.raises(attr.exceptions.FrozenInstanceError):
        fc.number_of_wheels = 5
