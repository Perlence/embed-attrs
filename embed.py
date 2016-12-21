import attr as _attr
import pytest

__all__ = ('attrs', 'attr', 'PromotedAttribute', 'AmbiguousAttribute',
           'INIT', 'EMBED_CLS_METADATA', 'EMBED_EXTRA_METADATA')

EMBED_CLS_METADATA = '__embed_cls'
EMBED_EXTRA_METADATA = '__embed_extra'

INIT = object()


def attrs(maybe_cls=None, these=None, repr_ns=None, repr=True, cmp=True,
          hash=True, init=True, slots=False, frozen=False, str=False):
    def wrap(cls):
        cls_with_attrs = _attr.s(cls, these, repr_ns, repr, cmp, hash, init, slots, frozen, str)

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


def attr(cls, extra=None, default=_attr.NOTHING, validator=None, repr=True,
         cmp=True, hash=True, init=True, convert=None, metadata=None):
    if metadata is None:
        metadata = {}
    metadata[EMBED_CLS_METADATA] = cls
    if extra is not None:
        metadata[EMBED_EXTRA_METADATA] = extra.replace(',', ' ').split()
    if default is INIT:
        default = _attr.Factory(cls)
    return _attr.ib(default, validator, repr, cmp, hash, init, convert, metadata)


def get_embedded_attrs(cls_with_attrs):
    return tuple(attrib for attrib in _attr.fields(cls_with_attrs)
                 if attrib.metadata.get(EMBED_CLS_METADATA) is not None)


def get_extra_promoted_names(embedded_attrs):
    result = set()
    for attrib in embedded_attrs:
        extra_names = attrib.metadata.get(EMBED_EXTRA_METADATA, [])
        result = result.union(set(extra_names))
    return result


@_attr.s
class PromotedAttribute:
    name = _attr.ib()
    embedded_attr = _attr.ib()

    def __get__(self, obj, cls=None):
        if obj is None:
            return self
        embedded_obj = getattr(obj, self.embedded_attr.name)
        return getattr(embedded_obj, self.name)

    def __set__(self, obj, value):
        embedded_obj = getattr(obj, self.embedded_attr.name)
        setattr(embedded_obj, self.name, value)


@_attr.s
class AmbiguousAttribute:
    name = _attr.ib()

    def __get__(self, obj, cls=None):
        if obj is None:
            return self
        raise AttributeError("ambiguous selector '{}'".format(self.name))

    def __set__(self, obj, value):
        raise AttributeError("ambiguous selector '{}'".format(self.name))


def test_person():
    @_attr.s
    class Person:
        name = _attr.ib(default='')

        def talk(self):
            return 'Hi, my name is {}'.format(self.name)

        def _sunder(self):
            return 'sunder'

        def __dunder__(self):
            return 'dunder'

    @attrs
    class Android:
        person = attr(Person, default=INIT, extra='_sunder __dunder__')
        model = _attr.ib(default='')

    a = Android(Person('Marvin'))
    assert a.talk() == 'Hi, my name is Marvin'
    assert a._sunder() == 'sunder'
    assert a.__dunder__() == 'dunder'

    p = Person('WALL-E')
    a.person = p
    assert a.talk() == 'Hi, my name is WALL-E'

    with pytest.raises(AttributeError) as excinfo:
        a.nonexistent
    assert str(excinfo.value) == "'Android' object has no attribute 'nonexistent'"

    a.name = 'Bender'
    assert a.person.name == 'Bender'
    a.person.name = 'Daniel'
    assert a.name == 'Daniel'

    a.nonexistent = 'not anymore'
    assert getattr(a, 'nonexistent') is 'not anymore'

    @attrs(frozen=True)
    class FrozenPerson:
        person = attr(Person)

    fp = FrozenPerson(Person('Marvin'))
    with pytest.raises(_attr.exceptions.FrozenInstanceError):
        fp.person = Person('Marvin')
    with pytest.raises(_attr.exceptions.FrozenInstanceError):
        fp.name = 'Bender'


def test_dont_replace():
    @_attr.s
    class A:
        x = _attr.ib(default='embedded')

        def fn(self):
            return self.x

    @attrs
    class B:
        a = attr(A, default=INIT)
        x = _attr.ib(default='parent')

    b = B()
    assert b.x == 'parent'
    assert b.fn() == 'embedded'
    b.x = 'new'
    assert b.x == 'new'
    assert b.a.x == 'embedded'


def test_ambiguous():
    @_attr.s
    class A:
        x = _attr.ib(default=0)

    @_attr.s
    class B:
        x = _attr.ib(default=0)

    @attrs
    class Ambiguous:
        a = attr(A, default=INIT)
        b = attr(B, default=INIT)

    amb = Ambiguous()
    with pytest.raises(AttributeError) as excinfo:
        amb.x = 1
    assert 'ambiguous selector' in str(excinfo.value)


def test_nesting():
    @_attr.s
    class C:
        d = _attr.ib(default=0)

    @attrs
    class B:
        c = attr(C, default=INIT)

    @attrs
    class A:
        b = attr(B, default=INIT)

    a = A()
    assert a.b.c.d == 0
    a.d = 1
    assert a.b.c.d == 1
    assert a.c is a.b.c
