"""
Traversing a graph of Django models, using FK and M2M relationships as edges. A
model can also explicitly define a relationship via a static method that takes
in model instances and returns a QuerySet for fetching the related objects for
these instances.
"""

import types
from django.db import connections, router
from django.db.models.query import QuerySet
from django.db.models import Count, Avg, Max, Min, Sum
from django.db.models.fields.related_descriptors import (
  ForwardOneToOneDescriptor,
  ForwardManyToOneDescriptor,
  ManyToManyDescriptor,
  ReverseManyToOneDescriptor,
  ReverseOneToOneDescriptor,
)


def mk_filter_function(filters):
  def apply_filters(q):
    order_by = 'id'  # default ordering, if asked with first or last

    if filters is not None:
      #if type(q) != QuerySet:
        #raise Exception('Can only apply filters to queryset objects')

      for _filter in filters:
        if 'method' not in _filter or\
           _filter['method'] not in ['exclude', 'filter',
                                     'count', 'max', 'min', 'sum', 'avg',
                                     'order', 'start', 'limit', 'first', 'last']:
          raise Exception('Missing or unknown method in filter')

        if _filter['method'] in ['exclude', 'filter']:
          if 'kwargs' not in _filter:
            raise Exception('Missing kwargs for filter')
          kwargs = _filter['kwargs']
          q = getattr(q, _filter['method'])(**kwargs)

        elif _filter['method'] in ['count', 'max', 'min', 'sum', 'avg']:
          if 'field' not in _filter:
            raise Exception('Missing field for aggregation function')
          field = _filter['field']
          if _filter['method'] == 'count':
            f = Count(field)
          elif _filter['method'] == 'avg':
            f = Avg(field)
          elif _filter['method'] == 'sum':
            f = Sum(field)
          elif _filter['method'] == 'max':
            f = Max(field)
          elif _filter['method'] == 'min':
            f = Min(field)
          q = q.annotate(f)

        elif _filter['method'] in ['order', 'start', 'limit', 'first', 'last']:
          if 'field' not in _filter:
            raise Exception('Missing field or range for paging')
          f = _filter['field']
          if _filter['method'] == 'order':
            q = q.distinct().order_by(f)
            order_by = f
          elif _filter['method'] == 'start':
            q = q[int(f):]
          elif _filter['method'] == 'limit':
            q = q[:int(f)]
          elif _filter['method'] == 'first':
            q = q.distinct().order_by(order_by)[0:int(f)]
          elif _filter['method'] == 'last':
            q = q.distinct().order_by('-%s' % order_by)[0:int(f)]

        else:
          raise Exception('Unknown method')

    q = q.only('pk')
    return q
  return apply_filters


# The following django model attributes are relationships we can traverse
def _valid_django_rel(rel_obj_descriptor):
  return type(rel_obj_descriptor) in (ForwardManyToOneDescriptor,
                                      ReverseManyToOneDescriptor,
                                      ManyToManyDescriptor,
                                      ForwardOneToOneDescriptor,
                                      ReverseOneToOneDescriptor)


# Use this attr of a query output object to determine the input object
# producing the output object using the query.
INPUT_ATTR_PREFIX = '_origin_'

def get_related_obj_accessor(rel_obj_descriptor, instance, allow_missing_rel=False):
  """
  From a related object descriptor (there are a few types of descriptors
  defined in django.db.models.fields.related), build a function that takes in
  multiple instances and return the related objects for all the instances.

  The instance variable is an example instance, required by Django to construct
  a related object manager; it does not affect the query produced by the
  returned function.
  """

  if not _valid_django_rel(rel_obj_descriptor) and\
     type(rel_obj_descriptor) not in (types.FunctionType, types.MethodType):
    if allow_missing_rel:
      return None
    else:
      raise Exception("Cannot handle related object descriptor %s." % rel_obj_descriptor)

  def get_related_objects(instances, filters=None):
    queryset = None

    # because we can recursively call traverse, after the first call filters
    # argument is already converted to the result of mk_filter_function
    if filters is not None and type(filters) == types.FunctionType:
      apply_filters = filters
    else:
      apply_filters = mk_filter_function(filters)

    # functioning defining a relationship
    if type(rel_obj_descriptor) in (types.FunctionType, types.MethodType):
      return rel_obj_descriptor(instances, apply_filters)

    # FK from instance to a related object
    elif type(rel_obj_descriptor) in (ForwardManyToOneDescriptor, ForwardOneToOneDescriptor):
      field = rel_obj_descriptor.field

      rel_obj_attr = field.get_foreign_related_value
      instance_attr = field.get_local_related_value
      query = {'%s__in' % field.related_query_name(): instances}
      rel_mgr = field.rel.to._default_manager
      # If the related manager indicates that it should be used for related
      # fields, respect that.
      if getattr(rel_mgr, 'use_for_related_fields', False):
        queryset = rel_mgr
      else:
        queryset = QuerySet(field.rel.to)
      queryset = queryset.filter(**query).only('pk')

      table = instances[0]._meta.db_table
      pk_field = instances[0]._meta.pk.column
      related_table = field.rel.model._meta.db_table
      if table == related_table:
        # XXX hack: assuming django uses T2 for joining two tables of same name
        table = 'T2'
      queryset = queryset.extra(select={INPUT_ATTR_PREFIX: '%s.%s' % (table, pk_field)})

    # reverse FK from instance to related objects with FK to the instance
    elif type(rel_obj_descriptor) in (ReverseManyToOneDescriptor, ReverseOneToOneDescriptor):
      rel_obj = rel_obj_descriptor.related if (type(rel_obj_descriptor) == ReverseOneToOneDescriptor) else \
        rel_obj_descriptor.rel

      rel_field = rel_obj.field
      rel_obj_attr = rel_field.get_local_related_value
      rel_column = rel_field.column

      rel_model = rel_obj.related_model
      rel_mgr = rel_model._default_manager.__class__()
      rel_mgr.model = rel_model

      query = {'%s__in' % rel_field.name: instances}
      queryset = rel_mgr.get_queryset().filter(**query).only('pk')
      queryset = queryset.extra(select={INPUT_ATTR_PREFIX: '%s' % rel_column})

    # M2M from instance to related objects
    elif type(rel_obj_descriptor) in (ReverseManyToOneDescriptor, ManyToManyDescriptor):
      db = router.db_for_read(instance.__class__, instance=instance)
      connection = connections[db]

      mgr = rel_obj_descriptor.__get__(instance)
      query = {'%s__in' % mgr.query_field_name: instances}
      queryset = super(mgr.__class__, mgr).get_queryset().filter(**query).only('pk')

      fk = mgr.through._meta.get_field(mgr.source_field_name)
      join_table = mgr.through._meta.db_table
      qn = connection.ops.quote_name
      queryset = queryset.extra(select=dict(
        ('%s%s' % (INPUT_ATTR_PREFIX, f.attname),
         '%s.%s' % (qn(join_table), qn(f.column))) for f in fk.local_related_fields))

    # if you just do 'if queryset', that triggers query execution because
    # python checks length of the enumerable. to prevent query execution, check
    # if queryset is not None.
    if queryset is not None:
      return apply_filters(queryset)

    return []

  return get_related_objects


def traverse(nodes, attr, filters=None):
  """
  Traverse one relationship on list of nodes. Returns output, input tuple
  array, where input is the pk of the node producing the output object.
  """

  nodes = list(nodes) if type(nodes) == QuerySet else nodes
  nodes = [nodes] if type(nodes) not in [type([]), type((0,))] else nodes

  if len(nodes) == 0:
    return []
  if attr is None:
    return nodes

  f = get_related_obj_accessor(attr, nodes[0])
  nodes = f(nodes, filters=filters)

  def _execute(nodes):
    return list(nodes)
  nodes = _execute(nodes)

  if len(nodes) == 0:
    return []

  # already in output, input tuple format
  elif type(nodes[0]) == tuple:
    return nodes

  else:
    nodes_with_src = []
    for node in nodes:
      src = None
      for a in dir(node):
        if a.startswith(INPUT_ATTR_PREFIX):
          src = getattr(node, a)
          break
      nodes_with_src.append((node, src))

    return nodes_with_src
