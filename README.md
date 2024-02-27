# django-data-fetcher

## Installation

```bash
pip install django-data-fetcher
```

After installing, you'll need to add our middleware:


```python
# settings.py 
# ...
MIDDLEWARE = [
    # ...
    "data_fetcher.middleware.GlobalRequestMiddleware",
    # ...
]
```

## Usage

Data-fetcher enables request-scoped caching and batching, allowing you to decouple fetching logic from consumption logic without any performance impact.


### Caching

If you'd just like to cache a function so you don't repeat it in different places, you can just use the `cache_within_request` decorator:

```python
from data_fetcher import cache_within_request

@cache_within_request
def get_most_recent_order(user_id):
    return Order.objects.filter(user_id=user_id).order_by('-created_at').first()
```

Now you can call `get_most_recent_order` as many times as you want within a request, e.g. in template helpers and in views, and it will only hit the database once (assuming you use the same user_id). This is a wrapper around `functools.cache`, so it will also cache across calls to the same function with the same arguments.

### Batching

This library also supports _batching_ fetching logic. You need to subclass our `DataFetcher` class and implement a `batch_load` (or `batch_load_dict`) method with the batching logic. Then you can use its factory method to get an instance of your fetcher class, and call its `get()`, `get_many()`, or `prefetch_keys()` methods. 

For example, it's usually pretty difficult to efficiently fetch permissions for a list of objects without coupling your view to your templates/helpers. With this library, we can offload the work to a data-fetcher instance and have a re-usable template-helper that checks permissions. When we notice performance problems, we simply add a `prefetch_keys` call to our view to pre-populate the cache. 

```python
# my_app/fetchers.py

from data_fetcher import DataFetcher

class ArticlePermissionFetcher(DataFetcher):
    def batch_load_dict(self, article_ids):
        permissions = ArticlePermission.objects.filter(article_id__in=article_ids)
        return {p.article_id: p for p in permissions}

# my_app/template_helpers.py

from my_app.fetchers import ArticlePermissionFetcher

@register.simple_tag(takes_context=True)
def can_read_article(context, article):
    """
        called in a loop in article_list.html, e.g. to condtionally render a link
    """
    fetcher = ArticlePermissionFetcher.get_instance()
    permission = fetcher.get(article.id)
    return permission.can_read

# my_app/views.py

from my_app.fetchers import ArticlePermissionFetcher

def article_list(request):
    articles = Article.objects.all()
    fetcher = ArticlePermissionFetcher.get_instance()
    fetcher.prefetch_keys([a.id for a in articles])
    return render(request, 'article_list.html', {'articles': articles})

```  

Behind the scenes, fetchers' `get_instance` will use the global-request middleware's request object to always return the same instance of the fetcher for the same request. This allows the fetcher to call your batch function once, when the view calls `prefetch_keys`, and then use the cached results for all subsequent calls to `get` or `get_many`. 

Fetchers also cache values that were called with `get` or `get_many`. If you request a key that isn't cached, it will call your batch method again for that single key. It's recommended to monitor your queries while developing with a tool like [django-debug-toolbar](https://github.com/jazzband/django-debug-toolbar/). 


#### Fetcher API


Public method:

- `get(key)` : fetch a single resource by key
- `get_many(keys)` : fetch multiple resources by key, returns a list
- `get_many_as_dict(keys)` : like get_many, but returns a dict indexed by your requested keys
- `prefetch_keys(keys)` : Like get-many but returns nothing. Pre-populates the cache with a list of keys. This is useful when you know you're going to need a lot of objects, and you want to avoid N+1 queries.
- `prime(key,value)` manually set a value in the cache. This isn't recommended, but it can be useful for performance in certain cases

Subclass-API:

You can implement `batch_load(keys)` OR `batch_load_dict(keys)`. 
- `batch_load(keys)` needs to return a list of resources in the same order (and length) as the keys. If a resource is missing, you need an explicit None in the returned list.
- `batch_load_dict(keys)` should return a dict of resources, indexed by the keys. If a value is missing, `None` will be returned when that key is requested (it tolerates missing keys).


## Shortcuts 

It's extremely common to want to fetch a single object by id, or by a parent's foreign key. We provide a few baseclasses for this:

```python
from data_fetcher import AbstractModelByIdFetcher, AbstractChildModelByAttrFetcher

class ArticleByIdFetcher(AbstractModelByIdFetcher):
    model = Article

class ArticleByAuthorIdFetcher(AbstractChildModelByAttrFetcher):
    model = Article
    parent_attr = 'author_id'

```

In fact, the ID fetcher was so common we have a factory for it. This factory returns the same class every time, so you can use it in multiple places without worrying about creating multiple classes with distinct caches. 

```python
from data_fetcher import PrimaryKeyFetcherFactory

ArticleByIdFetcher = PrimaryKeyFetcherFactory.get_model_by_id_fetcher(Article)
ArticleByIdFetcher2 = PrimaryKeyFetcherFactory.get_model_by_id_fetcher(Article)
assert ArticleByIdFetcher == ArticleByIdFetcher2

article_1 = ArticleByIdFetcher.get_instance().get(1)
```


## Testing data-fetchers

Batch logic is often complex and error-prone. We recommend writing tests for your fetchers.  provides a mock request object that you can use to test your fetchers. Without this context-manager, your fetchers won't be able to cache anything and might raise errors. Here's an example in pytest:

```python
from data_fetcher.util import GlobalRequest

def test_article_permission_fetcher(django_assert_num_queries):
    with GlobalRequest():
        with django_assert_num_queries(1):
            fetcher = ArticlePermissionFetcher.get_instance(request)
            fetcher.prefetch_keys([1, 2, 3])
            assert fetcher.get(1).can_read
            assert not fetcher.get(2).can_read
            assert not fetcher.get(3).can_read

```


## How to provide non-key data to fetchers

Data-fetcher's main feature is not performance, but enabling decoupling. The view layer no longer has to be responsible for passing data to downstream consumers (e.g. utils, template-helpers, service-objects, etc.).

This paradigm shift can be a challenging adjustment. For instance, our `ArticlePermissionFetcher` above was naïve. Permission records should be fetched with respect to a user. How can we provide the user's ID to the fetcher? 

It's tempting to subclass DataFetcher and add a user argument to its `get_instance()` method. Unfortunately, extending the factory pattern is rather complex. There are broadly 3 different ways to solve this problem:

1. Use the global request to get the user. This is the simplest solution, but it limits your data-fetcher to the current user. You couldn't, for example, build a view that shows a list of articles available to _other_ users. 
2. Create composite-keys: instead of loading permissions by article id, you load them by `(user_id, article_id)` pairs. This is a good solution, but is often complex to implement and you usually don't need this flexibility. 
3. Dynamically create a data-fetcher _class_ that has a reference to the user

The 3rd solution fulfills the OOP temptation of adding a user argument to the constructor, but it's a "higher-order" solution. Rather than attaching the user to the fetcher-class, we would dynamically create a class that has a reference to the user, and then use a factory to ensure we recycle the same class for the same user. 

There's a builtin shortcut for this pattern, too, called `ValueBoundDataFetcher`. ValueBoundDataFetcher classes have a `bound_value` attribute available inside their batch-load methods. 


```python
# my_app/fetchers.py
from data_fetcher import ValueBoundDataFetcher

class UserBoundArticlePermissionFetcher(ValueBoundDataFetcher):
    def batch_load_dict(self, article_ids):
        user_id = self.bound_value
        permissions = ArticlePermission.objects.filter(user_id=user_id, article_id__in=article_ids)
        return { p.article_id: p for p in permissions }

# my_app/views.py
from my_app.fetchers import UserBoundArticlePermissionFetcher

def article_list(request):
    # generate a class that has a reference to the user
    UserBoundArticlePermissionFetcher = ValueBoundDataFetcher.get_value_bound_class(
        UserBoundArticlePermissionFetcher, 
        request.user.id
    )
    fetcher = UserBoundArticlePermissionFetcher.get_instance()
    articles = Article.objects.all()
    fetcher.prefetch_keys([a.id for a in articles])
    return render(request, 'article_list.html', {'articles': articles})

```

With this solution, we're still able to create fetchers for multiple users. However, it won't be as efficient as the composite-key solution (e.g. one query per user vs. one query for all users). 

Note that `bound_value` can be anything, so you can use this pattern to provide more than a single piece of data to your fetcher, just make sure it's hashable so it can be used as a key (otherwise, you'll want to pass separate value and key kwargs to `get_value_bound_class`. 


## Recipe: Caching a single data-structure with complex data

Batching logic often has a high-cognitive load, it may not be worth it to batch everything. Fortunately, the `@cache_within_request` decorator can cache anything, there's no need to restrict ourselves to a single resource. For instance, let's say we have a complex home-feed page that needs to fetch a lot of data for a particular user. We can use the `cache_within_request` decorator to cache the entire data-structure. 


```python
@cache_within_request
def get_home_feed_data(user_id):
    user = User.objects.filter(id=user_id).prefetch_related(
        Prefetch('articles', queryset=Article.objects.filter(deleted=False), to_attr='article_list'),
        Prefetch('articles__comments', queryset=Comment.objects.filter(deleted=False), to_attr='comment_list'),
        Prefetch('articles__author', queryset=User.objects.all(), to_attr='author_list'),
        # ...
    )
    more_data = get_more_data(user)
    # assemble a rich data structure with convenient API
    return {
        'user': user,
        'articles': user.article_list,
        'comments': flatten([article.comment_list for article in user.article_list]),
        'articles_by_id': # ...
        'comments_by_article_id': # ...
        'comments_by_id': # ...
        # ...
    }

```

Now any function can request the entire structure and use its rich API. We can isolate the ugly fetching logic and don't need to pass data around (e.g. view -> template -> helpers) to remain efficient.

This is not a perfect approach, as it couples our consumers (e.g. views, helpers) to this data-structure. This makes it difficult to re-use those helpers, or parts of the data-structure. However, in a pinch, it may be preferable to setting up fetchers (e.g. article-by-id, comments-by-article-id) for every atomic piece of data. A neat compromise might be to split this up into multiple cache functions, or a class that that executes other cached functions lazily. 


## Async 

Like most ORM-consuming code, data-fetcher is synchronous. You'll need to use `sync_to_async` to use it inside async views. Behind the scenes, the global-request middleware uses context-vars, which are both thread-safe and async-safe. 
