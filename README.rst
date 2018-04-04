Curious
=======

.. image:: https://travis-ci.org/ginkgobioworks/curious.svg?branch=master
    :target: https://travis-ci.org/ginkgobioworks/curious

Curious traverses relationships in a relational database. Curious
queries allow users to explore relationships among objects, traverse
recursive relationships, and jump between loosely connected databases.
Curious also provides a JSON interface to the objects. Users and
programmers can use Curious queries in analysis scripts and
applications.

Curious favors a data centric model of application construction; Curious
queries expose normalized, relational data, reducing UI dependency on UI
specific API end-points serving denormalized data. Changing what data an
UI needs no longer requires changing the UI specific end-points.

Curious works well with deep data models with many relationships. A
Curious query can traverse 10s of foreign key like relationships
efficiently. Curious queries always operate on sets of objects, and can
connect a small number of objects via a relationship to a large number
of objects, then via another relationship from the large number of
objects to a smaller set again. For example, Book to Authors to Country
of Residence. Unlike GraphQL, Curious outputs relationships between
objects, rather than an ever growing tree of JSON representations of the
objects.

Example
-------

::

    Book.last(10) Book.author_set Author.country(continent__name="North America")

Query Language
--------------

The query language allows traversing models by identfying the relationships between them,
through foreign keys in Django models, or arbitrary id-mapping functions. A Curious query
is a space-separated set of terms, which connect models together by relationships.

Several kinds of "joins" are possible using these relationship primitives:

- A traditional `inner join` ``Book Book.author_set``
- A `left outer join`: ``Book.last(10) ?(Book.author_set)``
- A `recusrive join`: ``Parent.children_*``

Furthermore, at each stage in a join, `filtering` can happen:

- Filtering by `Django field lookups`_: ``Book Book.author_set(id__in=[2,3,4])``
- Filtering by `subquery`: ``Book +(Book.author_set(id__in=[2,3,4]))``
- Filtering by `exclusive subquery` ``Book -(Book.author_set(id__in=[2,3,4]))``

Finally, relationships can generate `counts`:

- Counting ``Book Book.author_set__count``

.. _Django field lookups: https://docs.djangoproject.com/en/1.11/ref/models/querysets/#field-lookups

Configuring Curious
-------------------

::

    import myapp.models
    from curious import model_registry

    def register():
      model_registry.register(myapp.models)

Then include ``register`` when your Django app boots up.

Using Curious
-------------

Turn off CSRF. Deploy it as a Django app.

Writing Customized Relationships
--------------------------------

Use filter and deferred to real functions.

Development
-----------

Requires Docker. Spin up your container using the provided ``docker-compose.yml`` file and Makefile
by running ``make image``. This creates an image with a correct git configuration for your user,
which makes it easy to release. All of the commands you should need to run are defined the
``Makefile`` as targets. All of the targets except for ``image``, are meant to be run inside the
Docker container, but can be run from the host machine by having ``-ext`` appended to them. For
example, to run tests, you could either call ``make test`` from inside the container, or ``make
test-ext`` from the host.

If you are modifying the static assets during development, they can be recompiled with the
``build_assets`` make task, or by calling ``python setup.py build_assets``.

::

    ./make test-ext


Deployment
----------

Deployment of tagged commits happens to PyPI automatically via Travis CI. To bump and deploy a new
version, run ``make bump/[foo]-ext``, where ``[foo]`` is ``major``, ``minor``, or ``patch``. Then
``git push origin --tags master``.

