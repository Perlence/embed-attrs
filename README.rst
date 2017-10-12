embed-attrs
===========

Borrow attributes from other classes by *embedding* them. An experimental extension of `attrs
<https://github.com/hynek/attrs>`_.


Idea
----

When class ``B`` is embedded into class ``A``, all attributes (except attributes starting with underscore) of class
``B`` can be accessed and modified directly from class ``A``.


Examples
--------

An example from "An Introduction to Programming in Go", converted to Python with some extra stuff:

.. code-block:: python

    import attr
    import embed

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
        # Constant *INIT* here is a shortcut for `attr.Factory(Person)`
        # Keyword *extra* is used to select private attributes for promotion
        model = attr.ib(default='')

    a = Android()
    a.name = 'Marvin'
    assert a.talk() == 'Hi, my name is Marvin'
    assert a._sunder() == 'sunder'
    assert a.__dunder__() == 'dunder'
