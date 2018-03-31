import inspect
import types
import django.db.models
from .graph import _valid_django_rel
from .graph import traverse


def deferred_to_real(objs):
  deferred_model = [type(obj) for obj in objs if obj.get_deferred_fields()]
  if len(deferred_model) == 0:
    return []
  model = deferred_model[0]
  return model.objects.filter(pk__in=[obj.pk for obj in objs])


class CountObject(object):

  def __init__(self, id):
    try:
      self.__value = int(id)
    except:
      self.__value = None

  def __str__(self):
    return '%s' % self.__value

  @classmethod
  def fetch(cls, ids):
    return cls.query(ids)

  @classmethod
  def query(cls, ids):
    objs = [cls(id) for id in ids]
    return objs

  @property
  def value(self):
    return self.__value

  @property
  def id(self):
    return self.__value

  @property
  def pk(self):
    return self.id

  def fields(self):
    return ['id', 'value']

  def get(self, f):
    if f == 'id':
      return self.id
    elif f == 'value':
      return self.value
    return None

  @staticmethod
  def count_wrapper(f):
    def wrapped(objs, filters):
      rels = traverse(objs, f, filters=filters)
      counts = {}
      for target,src_id in rels:
        if src_id not in counts:
          counts[src_id] = {}
        counts[src_id][target.pk] = 1
      return [(CountObject(len(targets.keys())),src_id) for src_id,targets in counts.iteritems()]
    return wrapped


class ModelManager(object):

  @staticmethod
  def model_name(model_class):
    if hasattr(model_class, '_meta'):
      return '%s__%s' % (model_class._meta.app_label, model_class.__name__)
    return model_class.__name__

  def __init__(self, model_class, short_name=None):
    self.model_class = model_class

    self.model_name = ModelManager.model_name(model_class)
    self.short_name = model_class.__name__ if short_name is None else short_name

    # Relationships/foreign keys have explicit white/blacklists
    self.allowed_relationships = []
    self.disallowed_relationships = []

    # All model fields are included by default, except these
    self.field_excludes = []

    # Fields returned by Curious represented by @properties of the model
    self.property_fields = []

    self.url_function = None

  def is_rel_allowed(self, f):
    try:
      rel = getattr(self.model_class, f)
    except:
      rel = None
    if (
      rel
      and _valid_django_rel(getattr(self.model_class, f))
      and f not in self.disallowed_relationships
    ):
      return True
    return f in self.allowed_relationships

  def url_of(self, obj):
    if self.url_function is not None:
      return self.url_function(obj)
    return None

  def getattr(self, method):
    if method.endswith("__count"):
      method = method[:-7]
      f = self.getattr(method)
      return CountObject.count_wrapper(f)

    if not hasattr(self.model_class, method):
      raise Exception('Unknown attribute "%s" in "%s"' % (method, self.model_name))
    if not self.is_rel_allowed(method):
      raise Exception('Not allowed to call "%s" in "%s"' % (method, self.model_name))
    return getattr(self.model_class, method)


class ModelRegistry(object):
  def __init__(self):
    self.clear()

  def clear(self):
    self.__managers = {}
    self.__short_names = {}

  def __add_model_by_class(self, cls, short_name=None):
    manager = ModelManager(cls, short_name)
    if manager.model_name not in self.__managers:
      self.__managers[manager.model_name] = manager
      if manager.short_name not in self.__short_names:
        self.__short_names[manager.short_name] = []
      self.__short_names[manager.short_name].append(manager)

  def register(self, model, short_name=None):
    if isinstance(model, types.ModuleType):
      for name in dir(model):
        cls = getattr(model, name)
        if (
          inspect.isclass(cls)
          and issubclass(cls, django.db.models.Model)
          and not cls._meta.abstract
        ):
          self.__add_model_by_class(cls)
    else:
      if not hasattr(model, '_meta') or not model._meta.abstract:
        self.__add_model_by_class(model, short_name)

  def unregister(self, model_name):

    # will error out if model_name is ambiguious
    full_model_name = self.__translate_name(model_name)

    del self.__managers[full_model_name]

    # if we get here, we can be sure there's exactly one entry in short_names
    del self.__short_names[model_name]

  def __translate_name(self, name):
    if name in self.__managers:
      model_name = name
    else:
      if name in self.__short_names:
        if len(self.__short_names[name]) != 1:
          raise Exception('Ambiguous model name "%s": can match to %s' %
                          (name, ', '.join(i.model_name for i in self.__short_names[name])))
        else:
          model_name = self.__short_names[name][0].model_name
      else:
        raise Exception("Don't know about model %s" % name)
    return model_name

  def get_manager(self, name):
    model_name = self.__translate_name(name)
    if model_name in self.__managers:
      return self.__managers[model_name]
    raise Exception("Unknown model '%s'" % model_name)

  @property
  def model_names(self):
    return [m.model_name for m in self.__managers.values()]

  def get_name(self, cls):
    managers = [m for m in self.__managers.values() if m.model_class == cls]
    if len(managers) == 0:
      return ModelManager.model_name(cls)
    manager = managers[0]
    if (
      manager.short_name in self.__short_names
      and len(self.__short_names[manager.short_name]) == 1
    ):
      return manager.short_name
    return manager.model_name


model_registry = ModelRegistry()
model_registry.register(CountObject)
