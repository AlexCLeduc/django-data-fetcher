# django-data-fetcher

## Installation

```bash
pip install django-data-fetcher
```

After installing, you'll need to add our sub-dependency (which is automaticaly installed), `django-middleware-global-request`, to your middleware:


```python
# settings.py 
# ...
MIDDLEWARE = [
    # ...
    'django_middleware_global_request',
    # ...
]


```

## Usage

Data-fetcher enables caching and batching against a request, allowing you to decouple code that fetches data from code that uses it without any performance impact.

Caching is done by default, but batching is more complex. 

If you'd just like to cache a function so you don't repeat it in different places, you can just use the `cache_within_request` decorator:

```python
from data_fetcher import cache_within_request

@cache_within_request
def get_most_recent_order(user_id):
    return Order.objects.filter(user_id=user_id).order_by('-created_at').first()
```

Now you can call `get_most_recent_order` as many times as you want within a request, e.g. in template helpers and in views, and it will only hit the database once (assuming you use the same user_id). This is a wrapper around `functools.cache`, so it will also cache across calls to the same function with the same arguments.

In addition to caching, if you'd also like to _batch_ a function, it gets a little more complicated. You need to subclass our `InjectibleDataFetcher` class and implement a `batch_load` (or `batch_load_dict`) method with the batching logic. Then you can use its factory method to get an instance of your fetcher class, and call its `get()`, `get_many()`, or `prefetch_keys()` methods. 

For example, it's usually pretty difficult to efficiently fetch permissions for a list of objects without coupling your view and your template. With data-fetcher, we can offload the work to a data-fetcher and have a re-usable template-helper that checks permissions. When we notice performance problems, we simply add a `prefetch_keys` call to our view to pre-populate the cache. 

```python
# my_app/fetchers.py

from data_fetcher import InjectibleDataFetcher

class ArticlePermissionFetcher(InjectibleDataFetcher):
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

Behind the scenes, fetchers' `get_instance` will use the global-middleware request to always return the same instance of the fetcher for the same request. This allows the fetcher to call your batch function once, when the view calls `prefetch_keys`, and then use the cached results for all subsequent calls to `get` or `get_many`. 

Fetchers also cache values that were called with `get` or `get_many`. If you request a key that isn't cached, it will call your batch method again for that single key. It's recommended to monitor your queries while developing via your server-console or a tool like django-debug-toolbar. 

## Shortcuts 

It's extremely common to want to fetch a single object by id or by a parent's foreign key. We provide a few shortcuts for this:

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

ArticleByIdFetcher = PrimaryKeyFetcherFactory(Article)
ArticleByIdFetcher2 = PrimaryKeyFetcherFactory(Article)
assert ArticleByIdFetcher == ArticleByIdFetcher2

article_1 = ArticleByIdFetcher.get_instance().get(1)
```


## Testing data-fetchers

Batch logic is often complex and error-prone. We recommend writing tests for your fetchers. django-middleware-global-request provides a mock request object that you can use to test your fetchers. Here's an example in pytest:

```python
from django_middleware_global_request import GlobalRequest

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

Data-fetcher's main feature is not performance, but enabling decoupling. The view no longer has to be responsible for fetching data for downstream consumers (e.g. templates).

This paradigm shift can be a challenging adjustment. For instance, our ArticlePermissionFetcher above was naïve. Permission records should be fetched with respect to a user. How can we provide the user's ID to the fetcher? 

It's tempting to subclass DataFetcher and add a user argument to the constructor. Unfortunately, this isn't supported by our factory pattern. There are broadly 3 different ways to solve this problem:

1. Use the global request to get the user. This is the simplest solution, but it limits your data-fetcher to the current user. You couldn't, for example, build a view that shows a list of articles available to _other_ users. 
2. Create composite-keys: instead of loading permissions by article id, you load them by `(user_id, article_id)` pairs. This is a good solution, but is often complex to implement and you usually don't need this flexibility. 
3. Dynamically create a _class_ that has a reference to the user

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

With this solution, we're still able to create fetchers for multiple users. However it won't be as efficient as the composite-key solution (e.g. one query per user vs. one query for all users).

