Curious
=======

Curious traverses relationships in a relational database. Curious queries allow
users to explore relationships among objects, traverse recursive relationships,
and jump between loosely connected databases. Curious also provides a JSON
interface to the objects. Users and programmers can use Curious queries in
analysis scripts and applications.

Curious favors a data centric model of application construction; Curious
queries expose normalized, relational data, reducing UI dependency on UI
specific API end-points serving denormalized data. Changing what data an UI
needs no longer requires changing the UI specific end-points.

Curious works well with deep data models with many relationships. A Curious
query can traverse 10s of foreign key like relationships efficiently. Curious
queries always operate on sets of objects, and can connect a small number of
objects via a relationship to a large number of objects, then via another
relationship from the large number of objects to a smaller set again. For
example, Book to Authors to Country of Residence. Unlike GraphQL, Curious
outputs relationships between objects, rather than an ever growing tree of JSON
representations of the objects.


Example
-------

```
Book.last(10) Book.author_set Author.country(continent__name="North America")
```


Query Language
--------------

avg, sum, max, count.
? modifier for left joins.
t modifier for dates.


Configuring Curious
-------------------

```
import myapp.models
from curious import model_registry

def register():
  model_registry.register(myapp.models)
```

Then include ```register``` when your Django app boots up.


Using Curious
-------------

Turn off CSRF. Deploy it as a Django app.


Writing Customized Relationships
--------------------------------

Use filter and deferred to real functions.


Development
-----------

Requires docker

Build js assets for the UI

```
./build
```

Run tests

```
./test
```
