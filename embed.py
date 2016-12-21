import attr
import pytest

EMBED_CLS_METADATA = '__embed_cls'
EMBED_EXTRA_METADATA = '__embed_extra'


def embedding(maybe_cls=None, these=None, repr_ns=None, repr=True, cmp=True,
              hash=True, init=True, slots=False, frozen=False, str=False):
    def wrap(cls):
        cls_with_attrs = attr.s(cls, these, repr_ns, repr, cmp, hash, init, slots, frozen, str)

        embedded_attrs = get_embedded_attrs(cls_with_attrs)
        extra_names = get_extra_promoted_names(embedded_attrs)
        for embedded_attr in embedded_attrs:
            embedded_cls = embedded_attr.metadata.get(EMBED_CLS_METADATA)
            for promoted_name in dir(embedded_cls):
                if promoted_name.startswith('_') and promoted_name not in extra_names:
                    continue
                local_attr = getattr(cls_with_attrs, promoted_name, None)
                if local_attr is None:
                    setattr(cls_with_attrs, promoted_name, PromotedAttribute(promoted_name, embedded_attr))
                elif isinstance(local_attr, PromotedAttribute):
                    setattr(cls_with_attrs, promoted_name, AmbiguousAttribute(promoted_name))

        return cls_with_attrs

    if maybe_cls is None:
        return wrap
    else:
        return wrap(maybe_cls)


def embed(cls, extra=None, default=attr.NOTHING, validator=None, repr=True,
          cmp=True, hash=True, init=True, convert=None, metadata=None):
    if metadata is None:
        metadata = {}
    metadata[EMBED_CLS_METADATA] = cls
    if extra is not None:
        metadata[EMBED_EXTRA_METADATA] = extra.replace(',', ' ').split()
    return attr.ib(default, validator, repr, cmp, hash, init, convert, metadata)


def get_embedded_attrs(cls_with_attrs):
    return tuple(attrib for attrib in attr.fields(cls_with_attrs)
                 if attrib.metadata.get(EMBED_CLS_METADATA) is not None)


def get_extra_promoted_names(embedded_attrs):
    result = set()
    for attrib in embedded_attrs:
        extra_names = attrib.metadata.get(EMBED_EXTRA_METADATA, [])
        result = result.union(set(extra_names))
    return result


@attr.s
class PromotedAttribute:
    name = attr.ib()
    embedded_attr = attr.ib()

    def __get__(self, obj, cls=None):
        if obj is None:
            return self
        embedded_obj = getattr(obj, self.embedded_attr.name)
        return getattr(embedded_obj, self.name)

    def __set__(self, obj, value):
        embedded_obj = getattr(obj, self.embedded_attr.name)
        setattr(embedded_obj, self.name, value)


@attr.s
class AmbiguousAttribute:
    name = attr.ib()

    def __get__(self, obj, cls=None):
        if obj is None:
            return self
        raise AmbiguousError("ambiguous selector '{}'".format(self.name))

    def __set__(self, obj, value):
        raise AmbiguousError("ambiguous selector '{}'".format(self.name))


class AmbiguousError(Exception):
    pass


def test_ferrari():
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
        car = embed(Car, extra='_sunder __dunder__')

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

    f.wheel_count = 8
    assert f.car.wheel_count == 8
    f.car.wheel_count = 6
    assert f.wheel_count == 6

    f.nonexistent = 'not anymore'
    assert getattr(f, 'nonexistent') is 'not anymore'

    @embedding(frozen=True)
    class FrozenCar:
        car = embed(Car)

    fc = FrozenCar(Car(4))
    with pytest.raises(attr.exceptions.FrozenInstanceError):
        fc.car = Car(3)
    with pytest.raises(attr.exceptions.FrozenInstanceError):
        fc.number_of_wheels = 5


def test_dont_replace():
    @attr.s
    class A:
        x = attr.ib(default='embedded')

    @embedding
    class B:
        a = embed(A, default=attr.Factory(A))
        x = attr.ib(default='parent')

    b = B()
    assert b.x == 'parent'


def test_ambiguous():
    @attr.s
    class A:
        x = attr.ib(default=0)

    @attr.s
    class B:
        x = attr.ib(default=0)

    @embedding
    class Ambiguous:
        a = embed(A, default=attr.Factory(A))
        b = embed(B, default=attr.Factory(A))

    amb = Ambiguous()
    with pytest.raises(AmbiguousError):
        amb.x = 1


def test_nesting():
    @attr.s
    class C:
        d = attr.ib(default=0)

    @embedding
    class B:
        c = embed(C, default=attr.Factory(C))

    @embedding
    class A:
        b = embed(B, default=attr.Factory(B))

    a = A()
    assert a.b.c.d == 0
    a.d = 1
    assert a.b.c.d == 1
    assert a.c is a.b.c
