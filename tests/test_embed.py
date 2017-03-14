import attr
import pytest

import embed


def test_androids():
    @attr.s
    class Person:
        name = attr.ib(default='')

        def talk(self):
            return 'Hi, my name is {}'.format(self.name)

        def _sunder(self):
            return 'sunder'

        def __dunder__(self):
            return 'dunder'

    @embed.attrs
    class Android:
        person = embed.attr(Person, default=embed.INIT, extra='_sunder __dunder__')
        model = attr.ib(default='')

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

    @embed.attrs(frozen=True)
    class FrozenPerson:
        person = embed.attr(Person)

    fp = FrozenPerson(Person('Marvin'))
    with pytest.raises(attr.exceptions.FrozenInstanceError):
        fp.person = Person('Marvin')
    with pytest.raises(attr.exceptions.FrozenInstanceError):
        fp.name = 'Bender'


def test_dont_replace():
    @attr.s
    class A:
        x = attr.ib(default='embedded')

        def fn(self):
            return self.x

    @embed.attrs
    class B:
        a = embed.attr(A, default=embed.INIT)
        x = attr.ib(default='parent')

    b = B()
    assert b.x == 'parent'
    assert b.fn() == 'embedded'
    b.x = 'new'
    assert b.x == 'new'
    assert b.a.x == 'embedded'


def test_ambiguous():
    @attr.s
    class A:
        x = attr.ib(default=0)

    @attr.s
    class B:
        x = attr.ib(default=0)

    @embed.attrs
    class Ambiguous:
        a = embed.attr(A, default=embed.INIT)
        b = embed.attr(B, default=embed.INIT)

    amb = Ambiguous()
    with pytest.raises(AttributeError) as excinfo:
        amb.x = 1
    assert 'ambiguous selector' in str(excinfo.value)


def test_nesting():
    @attr.s
    class C:
        d = attr.ib(default=0)

    @embed.attrs
    class B:
        c = embed.attr(C, default=embed.INIT)

    @embed.attrs
    class A:
        b = embed.attr(B, default=embed.INIT)

    a = A()
    assert a.b.c.d == 0
    a.d = 1
    assert a.b.c.d == 1
    assert a.c is a.b.c


def test_validator():
    @attr.s
    class Person:
        name = attr.ib(default='')

    @embed.attrs
    class Android:
        person = embed.attr(Person, default=embed.INIT)
        model = attr.ib(default='')

    assert Android() == Android(Person(''), '')

    with pytest.raises(TypeError) as excinfo:
        Android(42)
    assert "'person' must be" in str(excinfo.value)
