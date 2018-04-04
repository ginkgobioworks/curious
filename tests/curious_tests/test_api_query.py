import json
from django.test import TestCase
from curious import model_registry, CountObject
from curious.api import ModelView
from curious_tests.models import Blog, Entry, Person
import curious_tests.models


class TestQueryAPI(TestCase):
  N = 3

  def setUp(self):
    blog = Blog(name='Databases')
    blog.save()
    self.blog = blog

    headlines = ['MySQL is a relational DB'] * TestQueryAPI.N
    self.entries = [Entry(headline=headline, blog=blog) for i, headline in enumerate(headlines)]
    for entry in self.entries:
      entry.save()

    self.person = Person(gender='parrot', alive=False)
    self.person.save()

    # register model
    model_registry.register(curious_tests.models)

  def tearDown(self):
    model_registry.clear()

  def test_query(self):
    r = self.client.get('/curious/q/', dict(q='Blog(%s) Blog.entry_set' % self.blog.pk))
    self.assertEquals(r.status_code, 200)
    j = json.loads(r.content)
    self.assertEquals(j.keys(), ['result'])
    self.assertEquals(j['result']['last_model'], 'Entry')
    self.assertEquals(len(j['result']['results']), 1)
    self.assertItemsEqual(
      j['result']['results'][0].keys(),
      ['model', 'join_index', 'objects', 'tree'],
    )
    self.assertEquals(j['result']['results'][0]['model'], 'Entry')
    self.assertEquals(j['result']['results'][0]['join_index'], -1)
    objects = [[obj.id, None] for obj in self.entries]
    self.assertItemsEqual(j['result']['results'][0]['objects'], objects)

  def test_join_query(self):
    r = self.client.get('/curious/q/', dict(q='Blog(%s), Blog.entry_set' % self.blog.pk))
    self.assertEquals(r.status_code, 200)
    j = json.loads(r.content)
    self.assertEquals(j.keys(), ['result'])
    self.assertEquals(j['result']['last_model'], 'Entry')
    self.assertEquals(len(j['result']['results']), 2)

    self.assertItemsEqual(
      j['result']['results'][0].keys(),
      ['model', 'join_index', 'objects', 'tree'],
    )
    self.assertEquals(j['result']['results'][0]['model'], 'Blog')
    self.assertEquals(j['result']['results'][0]['join_index'], -1)
    self.assertItemsEqual(j['result']['results'][0]['objects'], [[self.blog.pk, None]])

    self.assertItemsEqual(
      j['result']['results'][1].keys(),
      ['model', 'join_index', 'objects', 'tree'],
    )
    self.assertEquals(j['result']['results'][1]['model'], 'Entry')
    self.assertEquals(j['result']['results'][1]['join_index'], 0)
    objects = [[obj.id, self.blog.pk] for obj in self.entries]
    self.assertItemsEqual(j['result']['results'][1]['objects'], objects)

  def test_count_query(self):
    self.maxDiff = None
    r = self.client.get(
      '/curious/q/',
      dict(d=1, q='Blog(%s), Blog.entry_set__count' % self.blog.pk),
    )
    self.assertEquals(r.status_code, 200)
    j = json.loads(r.content)
    self.assertEquals(j.keys(), ['result'])

    self.assertEquals(j['result']['last_model'], 'CountObject')
    self.assertEquals(len(j['result']['results']), 2)

    self.assertItemsEqual(
      j['result']['results'][0].keys(),
      ['model', 'join_index', 'objects', 'tree'],
    )
    self.assertEquals(j['result']['results'][0]['model'], 'Blog')
    self.assertEquals(j['result']['results'][0]['join_index'], -1)
    self.assertItemsEqual(j['result']['results'][0]['objects'], [[self.blog.pk, None]])

    self.assertItemsEqual(
      j['result']['results'][1].keys(),
      ['model', 'join_index', 'objects', 'tree'],
    )
    self.assertEquals(j['result']['results'][1]['model'], 'CountObject')
    self.assertEquals(j['result']['results'][1]['join_index'], 0)
    objects = [[self.N, self.blog.pk]]
    self.assertItemsEqual(j['result']['results'][1]['objects'], objects)

    self.assertItemsEqual(j['result'].keys(), ['last_model', 'results', 'computed_on', 'data'])
    self.assertEquals(j['result']['data'][0], ModelView.objects_to_dict([self.blog]))
    self.assertEquals(
      j['result']['data'][1],
      json.loads(json.dumps(ModelView.objects_to_dict([CountObject(3)]))),
    )

  def test_getting_data_with_query(self):
    r = self.client.get('/curious/q/', dict(d=1, q='Blog(%s), Blog.entry_set' % self.blog.pk))
    self.assertEquals(r.status_code, 200)
    j = json.loads(r.content)
    self.assertEquals(j.keys(), ['result'])

    self.assertEquals(j['result']['last_model'], 'Entry')
    self.assertEquals(len(j['result']['results']), 2)

    self.assertItemsEqual(
      j['result']['results'][0].keys(),
      ['model', 'join_index', 'objects', 'tree'],
    )
    self.assertEquals(j['result']['results'][0]['model'], 'Blog')
    self.assertEquals(j['result']['results'][0]['join_index'], -1)
    self.assertItemsEqual(j['result']['results'][0]['objects'], [[self.blog.pk, None]])

    self.assertItemsEqual(
      j['result']['results'][1].keys(),
      ['model', 'join_index', 'objects', 'tree'],
    )
    self.assertEquals(j['result']['results'][1]['model'], 'Entry')
    self.assertEquals(j['result']['results'][1]['join_index'], 0)
    objects = [[obj.id, self.blog.pk] for obj in self.entries]
    self.assertItemsEqual(j['result']['results'][1]['objects'], objects)

    self.assertItemsEqual(j['result'].keys(), ['last_model', 'results', 'computed_on', 'data'])
    self.assertEquals(j['result']['data'][0], ModelView.objects_to_dict([self.blog]))
    self.assertEquals(
      j['result']['data'][1],
      json.loads(json.dumps(ModelView.objects_to_dict(self.entries))),
    )

  def test_property_fields(self):
    person_manager = model_registry.get_manager('Person')
    person_manager.property_fields = [
      'example_property_field',
    ]

    r = self.client.post(
      '/curious/q/',
      data=json.dumps({'q': 'Person({0.pk})'.format(self.person), 'd': 1}),
      content_type='application/json',
    )
    self.assertEquals(r.status_code, 200)
    result = json.loads(r.content)['result']
    print result
    data = json.loads(r.content)['result']['data'][0]
    self.assertItemsEqual(data['fields'], ['id', 'alive', 'example_property_field', 'gender'])
    self.assertItemsEqual(data['objects'][0], [
      self.person.pk,
      self.person.alive,
      self.person.example_property_field,
      self.person.gender,
    ])
