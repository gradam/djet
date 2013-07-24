import types
from django.core import mail
from django.core.handlers.wsgi import WSGIRequest
from django import test as django_test
from django.http import HttpResponse
from django.views import generic
import djet


class MockMiddleware(object):

    def process_request(self, request):
        request.middleware_was_here = True


class RequestFactoryTest(django_test.TestCase):

    def setUp(self):
        self.factory = djet.RequestFactory()

    def test_create_request_should_return_request(self):
        request = self.factory.get()

        self.assertIsInstance(request, WSGIRequest)

    def test_create_request_should_return_request_processes_by_middleware(self):
        request = self.factory.get(
            middleware_classes=[
                MockMiddleware,
            ]
        )

        self.assertTrue(request.middleware_was_here)

    def test_init_should_create_shortcuts(self):
        request = self.factory.get()

        self.assertEqual(request.method, 'GET')


class MockView(generic.View):

    def mock_method(self):
        self.mock_method_called = True


class KwargsMockView(generic.View):
    test = None

    def get(self, *args, **kwargs):
        return self.test


def mock_function_view(request):
    return HttpResponse(status=200)


class ViewTestCaseTest(djet.ViewTestCase):
    view_class = MockView
    middleware_classes = [MockMiddleware]

    def test_init_should_create_view_method_when_view_class_provided(self):
        self.assertIsInstance(self.view, types.FunctionType)

    def test_init_should_create_factory_instance_with_middleware_classes(self):
        self.assertIsInstance(self.factory, djet.RequestFactory)
        self.assertIn(MockMiddleware, self.factory.middleware_classes)

    def test_creating_view_object(self):
        view_object = self.view_class()

        view_object.mock_method()

        self.assertTrue(view_object.mock_method_called)


class KwargsViewTestCaseTest(djet.ViewTestCase):
    view_class = KwargsMockView
    view_kwargs = {'test': 'test'}

    def test_view_should_have_kwargs_when_view_kwargs_specified(self):
        request = self.factory.get()

        response = self.view(request)

        self.assertEqual(response, 'test')

    def test_view_object_should_have_kwargs_when_view_kwargs_specified(self):
        view_object = self.create_view_object()

        self.assertEqual(view_object.test, 'test')


class ViewTestCaseFunctionViewTest(djet.ViewTestCase):
    view_function = mock_function_view

    def test_assert_response_when_function_view_used(self):
        request = self.factory.get()

        response = self.view(request)

        self.assertEqual(response.status_code, 200)


class RedirectAssertionsMixinTest(djet.RedirectsAssertionsMixin, djet.ViewTestCase):
    view_class = MockView

    def test_assert_not_redirect_should_pass_when_view_not_redirect(self):
        request = self.factory.get()

        response = self.view(request)

        self.assert_not_redirect(response)

    def test_assert_redirect_should_pass_when_view_redirect(self):
        view = generic.RedirectView.as_view(url='/')
        request = self.factory.get()

        response = view(request)

        self.assert_redirect(response)


class EmailMockView(generic.View):

    def get(self, *args, **kwargs):
        for _ in range(int(self.request.GET.get('send'))):
            mail.send_mail('test', 'tasty test', 'glados@aperture.edu', ['you@testingchamber.com'])
        return HttpResponse()


class EmailAssertionsMixinTest(djet.EmailAssertionsMixin, djet.ViewTestCase):
    view_class = EmailMockView

    def test_assert_no_email_sent_when_not_sent(self):
        request = self.factory.get(data={'send': '0'})

        self.view(request)

        self.assert_emails_in_mailbox(0)

    def test_assert_email_sent_when_really_sent(self):
        request = self.factory.get(data={'send': '3'})

        self.view(request)

        self.assert_emails_in_mailbox(3)

    def test_assert_email_exists_raising_errors_when_should_raise(self):
        request = self.factory.get(data={'send': '1'})

        self.view(request)

        with self.assertRaises(AssertionError):
            self.assert_email_exists(subject='toast')

    def test_assert_email_exists_passing(self):
        request = self.factory.get(data={'send': '1'})

        self.view(request)

        self.assert_email_exists(subject='test')
