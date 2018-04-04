from django.test import TestCase

from curious.count import CountObject

from .test_custom_model import MyModel


class TestCountObject(TestCase):

  def test_properties(self):
    self.assertEqual(CountObject(3).value, 3)
    self.assertEqual(CountObject(3).pk, 3)
    self.assertEqual(CountObject(3).id, 3)

  def test_wrong_type_sets_value_none(self):
    self.assertEqual(CountObject("three").value, None)

  def test_fetch(self):
    pks = [
      "owls",
      3,
      "3",
      "golden shovel",
      {},
      11.5,
      (),
      -42,
    ]
    self.assertEqual([count_obj.value for count_obj in CountObject.fetch(pks)], [
      None,
      3,
      3,
      None,
      None,
      11,
      None,
      -42,
    ])

  def test_fields(self):
    self.assertEqual(CountObject(3).fields(), ['id', 'value'])

  def test_get(self):
    count_obj = CountObject(3)
    for field in ['pk'] + count_obj.fields():
      self.assertEqual(count_obj.get(field), 3)

  def test_wrapper(self):

    def example_rel(nodes, filters=None):
      related = []
      for node in nodes:
        related.extend([
          (MyModel(node.pk + 'a'), node.pk),
          (MyModel(node.pk + 'b'), node.pk),
          (MyModel(node.pk + 'a'), node.pk),
        ])

      return related

    # Make sure our relationship function works as expected
    self.assertEqual(
      [(target.pk, src_pk) for target, src_pk in example_rel([MyModel(1)])],
      [('mymy1a', 'my1'), ('mymy1b', 'my1'), ('mymy1a', 'my1')],
    )

    # The count function should work the same way, just counting by unique IDs
    wrapped_rel = CountObject.count_wrapper(example_rel)
    self.assertEqual(
      [(target.value, src_pk) for target, src_pk in wrapped_rel([MyModel(1)])],
      [(2, 'my1')],
    )
