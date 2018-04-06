import types
from collections import defaultdict
from functools import update_wrapper

from .graph import traverse


class CountObject(object):
  """
  A virtual model representing the result of a `__count` expression
  """
  def __init__(self, pk):
    try:
      self.__value = int(pk)
    except (TypeError, ValueError):
      self.__value = None

  def __str__(self):
    return '%s' % self.__value

  @classmethod
  def fetch(cls, pks):
    """
    Mock up "fetching" a CountObject

    Necessary for the custom model API (see :mod:`test_custom_model` for an example)

    Parameters
    ----------
    pks : list of int
      Primary keys to "get" equal to the value of the count

    Returns
    -------
    list of CountObjects
      A list of new CountObject instances with the corresponding counts
    """
    return [cls(pk) for pk in pks]

  @property
  def value(self):
    """ The value the count represents """
    return self.__value

  @property
  def pk(self):
    """
    A mock of the primary key

    Necessary for the custom model API (see :mod:`test_custom_model` for an example). Equivalent
    to the value
    """
    return self.__value

  @property
  def id(self):
    """
    Aliased to :obj:`~self.pk`
    """
    return self.pk

  def fields(self):
    """
    List the fields the object returns

    Necessary for the custom model API (see :mod:`test_custom_model` for an example).

    Returns
    -------
    list of str
      A list of field names
    """
    return ['id', 'value']

  def get(self, field_name):
    """
    Get the value of an object field by name.

    Necessary for the custom model API (see :mod:`test_custom_model` for an example).

    Parameters
    ----------
    field_name : str
      The name of a field to get

    Returns
    -------
    object
      The object's value of `field_name`.
    """
    return getattr(self, field_name, None)

  @staticmethod
  def count_wrapper(relationship):
    """
    A decorator that turns a regular relationship into a count relationship

    This method is the workhorse of :class:`CountObject`. It takes a typical relationship (a
    function or Django model relationship) that gets you from a source model to target model, and
    turns it into a "count relationship" that, instead of returning objects of the target model
    type, returns :class:`CountObject` instances hold the _number of items_ of the target model in
    the relationship. The results, as in the relationship function, are paired in tupples
    with the primary key of the source object.

    Parameters
    ----------
    relationship : callable or Django relationship
      Either a Django relationship, or a function that takes a list of source objects, and returns a
      list of tuple pairs of related objects, of the form :samp:`({obj}, {id})`, where `obj` is a
      related object, and `id` is a primary key for the source object.

    Returns
    -------
    function
      A count relationship function that takes a list of source model objects and returns a list of
      tuple pairs of :samp:`({count}, {id})`, where `count` is a :class:`CountObject`, and `id` is
      the source object primary key.
    """

    def wrapper(objs, filters=None):
      rels = traverse(objs, relationship, filters=filters)

      # Uniquely count relations, grouped by source object
      counts = defaultdict(set)
      for target, src_pk in rels:
        counts[src_pk].add(target.pk)

      return [
        (CountObject(len(targets)), src_pk)
        for src_pk, targets in counts.iteritems()
      ]

    # Update the wrapper to look like the original relationship, if that relationship
    # is a function
    if isinstance(relationship, types.FunctionType) or hasattr(relationship, '__name__'):
      update_wrapper(wrapper, relationship)

    return wrapper
