from collections import defaultdict
from functools import wraps

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
  def count_wrapper(relationship_function):
    """
    A decorator that turns a regular relationship into a count relationship

    This method is the workhorse of :class:`CountObject`. It takes a typical "relationship function"
    that gets you from one model to another, and turns it into a "count relationship function" that,
    instead of returning objects of the next model type, returns virtual :class:`CountObject`
    instances which hold the number of items that the relationship function would have returned.

    Parameters
    ----------
    relationship_function : callable
      A function that takes a list of IDs

    Returns
    -------
    object
      The object's value of `field_name`.
    """

    @wraps(relationship_function)
    def wrapped(objs, filters=None):
      rels = traverse(objs, relationship_function, filters=filters)

      # Uniquely count relations, grouped by source object
      counts = defaultdict(set)
      for target, src_pk in rels:
        counts[src_pk].add(target.pk)

      return [
        (CountObject(len(targets)), src_pk)
        for src_pk, targets in counts.iteritems()
      ]

    return wrapped
