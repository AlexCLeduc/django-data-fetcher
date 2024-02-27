from unittest.mock import MagicMock, patch

from django.test.client import Client
from django.urls import reverse

from sample_app import data_factories


def test_view_with_loader():
    u = data_factories.UserFactory()
    client1 = Client()
    client1.force_login(u)

    u2 = data_factories.UserFactory()
    client2 = Client()
    client2.force_login(u2)

    data_factories.AuthorFactory.create_batch(20)

    url = reverse("view1")

    spy1 = MagicMock()

    with patch("sample_app.views.spyable_func", spy1):
        response = client1.get(url)
        assert response.status_code == 200

    spy2 = MagicMock()
    with patch("sample_app.views.spyable_func", spy2):
        response = client2.get(url)
        assert response.status_code == 200

    assert spy1.call_count == 1
    assert spy2.call_count == 1


def test_async_view_with_loader():
    u = data_factories.UserFactory()
    client1 = Client()
    client1.force_login(u)

    u2 = data_factories.UserFactory()
    client2 = Client()
    client2.force_login(u2)

    data_factories.AuthorFactory.create_batch(20)

    url = reverse("async_view1")

    spy1 = MagicMock()

    with patch("sample_app.views.spyable_func", spy1):
        response = client1.get(url)
        assert response.status_code == 200

    spy2 = MagicMock()
    with patch("sample_app.views.spyable_func", spy2):
        response = client2.get(url)
        assert response.status_code == 200

    assert spy1.call_count == 1
    assert spy2.call_count == 1
