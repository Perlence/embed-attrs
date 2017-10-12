import attr as _attr

__all__ = ('attrs', 'attr', 'INIT', 'EMBED_CLS_METADATA', 'EMBED_EXTRA_METADATA')

EMBED_CLS_METADATA = '__embed_cls'
EMBED_EXTRA_METADATA = '__embed_extra'

INIT = object()


def attr(cls, extra=None, default=_attr.NOTHING, validator=None, repr=True,
         cmp=True, hash=None, init=True, convert=None, metadata=None):
    if metadata is None:
        metadata = {}
    metadata[EMBED_CLS_METADATA] = cls
    if extra is not None:
        metadata[EMBED_EXTRA_METADATA] = extra.replace(',', ' ').split()
    if default is INIT:
        default = _attr.Factory(cls)
    if validator is None:
        validator = _attr.validators.instance_of(cls)
    return _attr.ib(default, validator, repr, cmp, hash, init, convert, metadata)


def attributes(maybe_cls=None, these=None, repr_ns=None, repr=True, cmp=True,
               hash=None, init=True, slots=False, frozen=False, str=False):
    def wrap(cls):
        cls_with_attrs = _attr.s(cls, these, repr_ns, repr, cmp, hash, init, slots, frozen, str)

        embedded_attrs = _get_embedded_attrs(cls_with_attrs)
        for embedded_attr in embedded_attrs:
            for promoted_name in _attrs_to_promote(embedded_attr):
                _try_to_promote(cls_with_attrs, promoted_name, embedded_attr)

        return cls_with_attrs

    if maybe_cls is None:
        return wrap
    else:
        return wrap(maybe_cls)


attrs = attributes


def _get_embedded_attrs(cls_with_attrs):
    return tuple(attrib for attrib in _attr.fields(cls_with_attrs)
                 if attrib.metadata.get(EMBED_CLS_METADATA) is not None)


def _attrs_to_promote(embedded_attr):
    embedded_cls = embedded_attr.metadata.get(EMBED_CLS_METADATA)
    extra_names = embedded_attr.metadata.get(EMBED_EXTRA_METADATA, [])
    for name in dir(embedded_cls):
        if not name.startswith('_') or name in extra_names:
            yield name


def _try_to_promote(cls, name, embedded_attr):
    try:
        local_attr = getattr(cls, name)
    except AttributeError:
        setattr(cls, name, _make_property(_property_tpl, name, promoted_name=embedded_attr.name))
    else:
        if isinstance(local_attr, promoted_property):
            setattr(cls, name, _make_property(_ambiguous_property_tpl, name))


def _make_property(template, name, **format_args):
    src = template.format(name=name, **format_args)
    namespace = {'promoted_property': promoted_property}
    exec(src, namespace)
    prop = namespace[name]
    return prop


class promoted_property(property):
    pass


_property_tpl = '''\
@promoted_property
def {name}(self):
    return self.{promoted_name}.{name}

@{name}.setter
def {name}(self, value):
    self.{promoted_name}.{name} = value
'''

_ambiguous_property_tpl = '''\
@property
def {name}(self):
    raise AttributeError("ambiguous selector '{name}'")

@{name}.setter
def {name}(self, other):
    raise AttributeError("ambiguous selector '{name}'")
'''
