import imp
import os
import pprint
import json
import responses
from mock import patch, MagicMock
from pymacaron_core.swagger.client import _format_flask_url
from pymacaron_core.exceptions import PyMacaronCoreException, ValidationError


utils = imp.load_source('common', os.path.join(os.path.dirname(__file__), 'utils.py'))


class Test(utils.PymTest):


    def setUp(self):
        super(Test, self).setUp()


    @responses.activate
    def test_client_with_query_param(self):
        handler, _ = self.generate_client_and_spec(self.yaml_query_param)

        responses.add(
            responses.GET, "http://some.server.com:80/v1/some/path",
            body=json.dumps({"foo": "a", "bar": "b"}),
            status=200,
            content_type="application/json"
        )

        res = handler(arg1='this', arg2='that')

        print("response: " + pprint.pformat(res))
        self.assertEqual(type(res).__name__, 'Result')
        self.assertEqual(res.foo, 'a')
        self.assertEqual(res.bar, 'b')


    @patch('pymacaron_core.swagger.client.requests')
    def test_requests_parameters_with_query_param(self, requests):
        requests.get = MagicMock()
        handler, _ = self.generate_client_and_spec(self.yaml_query_param)

        with self.assertRaises(PyMacaronCoreException) as e:
            handler(arg1='this', arg2='that')
        # self.assertEqual("Expected 1 caller, got 0", str(e.exception))

        requests.get.assert_called_once_with(
            'http://some.server.com:80/v1/some/path',
            data=None,
            headers={'Content-Type': 'application/json'},
            params={'arg1': 'this', 'arg2': 'that'},
            timeout=(10, 10),
            verify=True
        )


    @responses.activate
    def test_client_with_body_param(self):
        handler, spec = self.generate_client_and_spec(self.yaml_body_param)

        responses.add(
            responses.POST,
            "http://some.server.com:80/v1/some/path",
            body=json.dumps({"foo": "a", "bar": "b"}),
            status=200,
            content_type="application/json"
        )

        # Only 1 parameter expected
        with self.assertRaises(ValidationError) as e:
            res = handler()
        with self.assertRaises(ValidationError) as e:
            res = handler(1, 2)

        # Send a valid parameter object
        model_class = spec.definitions['Param']
        param = model_class(arg1='a', arg2='b')

        res = handler(param)
        self.assertEqual(type(res).__name__, 'Result')
        self.assertEqual(res.foo, 'a')
        self.assertEqual(res.bar, 'b')


    @patch('pymacaron_core.swagger.client.requests')
    def test_requests_parameters_with_body_param(self, requests):
        handler, spec = self.generate_client_and_spec(self.yaml_body_param)
        model_class = spec.definitions['Param']
        param = model_class(arg1='a', arg2='b')

        with self.assertRaises(PyMacaronCoreException) as e:
            handler(param)

        requests.post.assert_called_once_with(
            'http://some.server.com:80/v1/some/path',
            data=json.dumps({"arg1": "a", "arg2": "b"}),
            headers={'Content-Type': 'application/json'},
            params=None,
            timeout=(10, 10),
            verify=True
        )


# def test_client_with_auth_required():
#     pass


    def test__format_flask_url(self):
        ref = {
            'item_id': '1234',
            'path': 'abcd',
        }

        data = ref.copy()
        u = _format_flask_url(
            "/v1/seller/<item_id>/<path>/foo",
            data
        )
        self.assertEqual(u, "/v1/seller/1234/abcd/foo", u)
        self.assertEqual(len(list(data.keys())), 0)

        data = ref.copy()
        u = _format_flask_url(
            "/v1/seller/<item_id>/<path>/foo/<item_id>",
            data,
        )
        self.assertEqual(u, "/v1/seller/1234/abcd/foo/1234", u)
        self.assertEqual(len(list(data.keys())), 0)

        data = ref.copy()
        u = _format_flask_url(
            "/v1/seller/<item_id>/foo",
            data,
        )
        self.assertEqual(u, "/v1/seller/1234/foo", u)
        self.assertEqual(len(list(data.keys())), 1)
        self.assertEqual(data['path'], 'abcd')



    @responses.activate
    def test_client_with_path_param(self):
        handler, spec = self.generate_client_and_spec(self.yaml_path_param)

        responses.add(
            responses.GET,
            "http://some.server.com:80/v1/some/123/path/456",
            body=json.dumps({"foo": "a", "bar": "b"}),
            status=200,
            content_type="application/json"
        )

        # Make a valid call
        res = handler(foo=123, bar=456)
        self.assertEqual(type(res).__name__, 'Result')
        self.assertEqual(res.foo, 'a')
        self.assertEqual(res.bar, 'b')


    @patch('pymacaron_core.swagger.client.requests')
    def test_requests_parameters_with_path_params(self, requests):
        handler, spec = self.generate_client_and_spec(self.yaml_path_param)

        with self.assertRaises(PyMacaronCoreException) as e:
            handler(foo=123, bar=456)

        requests.get.assert_called_once_with(
            'http://some.server.com:80/v1/some/123/path/456',
            data=None,
            headers={'Content-Type': 'application/json'},
            params=None,
            timeout=(10, 10),
            verify=True)


    @patch('pymacaron_core.swagger.client.requests')
    def test_handler_extra_parameters(self, requests):
        handler, spec = self.generate_client_and_spec(self.yaml_path_param)

        with self.assertRaises(PyMacaronCoreException) as e:
            handler(
                foo=123,
                bar=456,
                max_attempts=2,
                read_timeout=6,
                connect_timeout=8
            )

        requests.get.assert_called_once_with(
            'http://some.server.com:80/v1/some/123/path/456',
            data=None,
            headers={'Content-Type': 'application/json'},
            params=None,
            timeout=(8, 6),
            verify=True
        )


    @responses.activate
    def test_client_with_path_query_param(self):
        handler, spec = self.generate_client_and_spec(self.yaml_path_query_param)

        responses.add(
            responses.GET,
            "http://some.server.com:80/v1/some/123/path",
            body=json.dumps({"foo": "a", "bar": "b"}),
            status=200,
            content_type="application/json"
        )

        # Make a valid call
        res = handler(foo=123, bar=456)
        self.assertEqual(type(res).__name__, 'Result')
        self.assertEqual(res.foo, 'a')
        self.assertEqual(res.bar, 'b')


    @patch('pymacaron_core.swagger.client.requests')
    def test_requests_parameters_with_path_query_params(self, requests):
        handler, spec = self.generate_client_and_spec(self.yaml_path_query_param)

        with self.assertRaises(PyMacaronCoreException) as e:
            handler(foo=123, bar=456)

        requests.get.assert_called_once_with(
            'http://some.server.com:80/v1/some/123/path',
            data=None,
            headers={'Content-Type': 'application/json'},
            params={'bar': 456},
            timeout=(10, 10),
            verify=True)



    @responses.activate
    def test_client_with_path_body_param(self):
        handler, spec = self.generate_client_and_spec(self.yaml_path_body_param)

        responses.add(
            responses.GET,
            "http://some.server.com:80/v1/some/123/path",
            body=json.dumps({"foo": "a", "bar": "b"}),
            status=200,
            content_type="application/json"
        )

        # Send a valid parameter object
        model_class = spec.definitions['Param']
        param = model_class(arg1='a', arg2='b')

        res = handler(param, foo=123)
        self.assertEqual(type(res).__name__, 'Result')
        self.assertEqual(res.foo, 'a')
        self.assertEqual(res.bar, 'b')

        # Only 1 parameter expected
        with self.assertRaises(ValidationError) as e:
            res = handler(foo=123)
        self.assertTrue('expects exactly' in str(e.exception))

        with self.assertRaises(ValidationError) as e:
            res = handler(1, 2, foo=123)
        self.assertTrue('expects exactly' in str(e.exception))

        with self.assertRaises(ValidationError) as e:
            res = handler(param)
        self.assertTrue('Missing some arguments' in str(e.exception))


    @patch('pymacaron_core.swagger.client.requests')
    def test_requests_parameters_with_path_body_params(self, requests):
        handler, spec = self.generate_client_and_spec(self.yaml_path_body_param)

        model_class = spec.definitions['Param']
        param = model_class(arg1='a', arg2='b')

        with self.assertRaises(PyMacaronCoreException) as e:
            handler(param, foo=123)

        requests.get.assert_called_once_with(
            'http://some.server.com:80/v1/some/123/path',
            data=json.dumps({"arg1": "a", "arg2": "b"}),
            headers={'Content-Type': 'application/json'},
            params=None,
            timeout=(10, 10),
            verify=True
        )


    @responses.activate
    def test_client_unknown_method(self):
        y = self.yaml_query_param
        y = y.replace('get:', 'foobar:')

        with self.assertRaises(PyMacaronCoreException) as e:
            handler, spec = self.generate_client_and_spec(y)
        self.assertTrue('BUG: method FOOBAR for /v1/some/path is not supported' in str(e.exception))


    @patch('pymacaron_core.swagger.client.requests')
    def test_requests_client_override_read_timeout(self, requests):
        handler, spec = self.generate_client_and_spec(self.yaml_path_query_param)

        with self.assertRaises(PyMacaronCoreException) as e:
            handler(read_timeout=50, foo='123', bar='456')

        requests.get.assert_called_once_with(
            'http://some.server.com:80/v1/some/123/path',
            data=None,
            headers={'Content-Type': 'application/json'},
            params={'bar': '456'},
            timeout=(10, 50),
            verify=True)


    @patch('pymacaron_core.swagger.client.requests')
    def test_requests_client_override_connect_timeout(self, requests):
        handler, spec = self.generate_client_and_spec(self.yaml_path_query_param)

        with self.assertRaises(PyMacaronCoreException) as e:
            handler(connect_timeout=50, foo='123', bar='456')

        requests.get.assert_called_once_with(
            'http://some.server.com:80/v1/some/123/path',
            data=None,
            headers={'Content-Type': 'application/json'},
            params={'bar': '456'},
            timeout=(50, 10),
            verify=True)


    @responses.activate
    def test_client_error_callback_return_dict(self):

        def callback(e):
            return {'error': str(e)}

        handler, spec = self.generate_client_and_spec(
            self.yaml_path_body_param,
            callback=callback,
        )

        responses.add(
            responses.GET,
            "http://some.server.com:80/v1/some/123/path",
            body=json.dumps({"foo": "a", "bar": "b"}),
            status=200,
            content_type="application/json"
        )

        # Send a valid parameter object
        model_class = spec.definitions['Param']
        param = model_class(arg1='a', arg2='b')

        res = handler(param)
        print("got: %s" % res)
        self.assertDictEqual(
            res,
            {
                'error': 'Missing some arguments to format url: http://some.server.com:80/v1/some/<foo>/path'
            }
        )


# TODO: test max_attempts?
