import attr as _attr

__all__ = ('attrs', 'attr', 'PromotedAttribute', 'AmbiguousAttribute',
           'INIT', 'EMBED_CLS_METADATA', 'EMBED_EXTRA_METADATA')

EMBED_CLS_METADATA = '__embed_cls'
EMBED_EXTRA_METADATA = '__embed_extra'

INIT = object()


def attrs(maybe_cls=None, these=None, repr_ns=None, repr=True, cmp=True,
          hash=True, init=True, slots=False, frozen=False, str=False):
    def wrap(cls):
        cls_with_attrs = _attr.s(cls, these, repr_ns, repr, cmp, hash, init, slots, frozen, str)

        embedded_attrs = _get_embedded_attrs(cls_with_attrs)
        extra_names = _get_extra_promoted_names(embedded_attrs)
        for embedded_attr in embedded_attrs:
            embedded_cls = embedded_attr.metadata.get(EMBED_CLS_METADATA)
            for promoted_name in _attrs_to_promote(embedded_cls, extra_names):
                _try_to_promote(cls_with_attrs, promoted_name, embedded_attr)

        return cls_with_attrs

    if maybe_cls is None:
        return wrap
    else:
        return wrap(maybe_cls)


def _get_embedded_attrs(cls_with_attrs):
    return tuple(attrib for attrib in _attr.fields(cls_with_attrs)
                 if attrib.metadata.get(EMBED_CLS_METADATA) is not None)


def _get_extra_promoted_names(embedded_attrs):
    result = set()
    for attrib in embedded_attrs:
        extra_names = attrib.metadata.get(EMBED_EXTRA_METADATA, [])
        result = result.union(set(extra_names))
    return result


def _attrs_to_promote(embedded_cls, extra_names):
    for name in dir(embedded_cls):
        if not name.startswith('_') or name in extra_names:
            yield name


def _try_to_promote(cls, name, embedded_attr):
    try:
        local_attr = getattr(cls, name)
    except AttributeError:
        setattr(cls, name, PromotedAttribute(name, embedded_attr))
    else:
        if isinstance(local_attr, PromotedAttribute):
            setattr(cls, name, AmbiguousAttribute(name))


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
