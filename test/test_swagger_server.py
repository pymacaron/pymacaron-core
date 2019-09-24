import imp
import os
import pprint
import json
import logging

from flask import jsonify
from mock import patch

from pymacaron_core.models import get_model


utils = imp.load_source('common', os.path.join(os.path.dirname(__file__), 'utils.py'))


log = logging.getLogger(__name__)


class Test(utils.PymTest):


    def setUp(self):
        super(Test, self).setUp()


    def assertReplyOK(self, r, token):
        self.assertEqual(r.status_code, 200)
        j = json.loads(r.data.decode("utf-8"))
        print("json reply: " + pprint.pformat(j))
        self.assertEqual(j['token'], token)

    def assertError(self, r, status, content):
        self.assertEqual(str(r.status_code), str(status))
        self.assertTrue(content in r.status, "[%s] in [%s]" % (content, r.status))


    @patch('pymacaron_core.test.return_token')
    def test_swagger_server_no_param(self, func):
        func.__name__ = 'return_token'

        app, spec = self.generate_server_app(self.yaml_no_param)

        SessionToken = get_model('SessionToken')
        func.return_value = SessionToken(token='123')

        with app.test_client() as c:
            r = c.get('/v1/no/param')
            self.assertReplyOK(r, '123')
            func.assert_called_once_with()


    @patch('pymacaron_core.test.return_token')
    def test_swagger_server_no_result(self, func):
        func.__name__ = 'return_token'
        func.return_value = None

        app, spec = self.generate_server_app(self.yaml_no_param)

        with app.test_client() as c:
            r = c.get('/v1/no/param')
            self.assertError(r, 500, 'INTERNAL SERVER ERROR')


    @patch('pymacaron_core.test.return_token')
    def test_swagger_server_pass_through_responses(self, func):
        func.__name__ = 'return_token'

        app, spec = self.generate_server_app(self.yaml_no_param)

        with app.test_request_context('/'):
            r = jsonify({'foo': 'bar'})
            r.status_code = 534
            func.return_value = r

            with app.test_client() as c:
                r = c.get('/v1/no/param')
                print("sc: %s" % str(r.status_code))
                self.assertEqual(r.status_code, 534)
                j = json.loads(r.data.decode("utf-8"))
                print("json reply: " + pprint.pformat(j))
                self.assertEqual(j['foo'], 'bar')


    @patch('pymacaron_core.test.return_token')
    def test_swagger_invalid_server_return_value(self, func):
        func.__name__ = 'return_token'
        func.return_value = {'a': 1}

        app, spec = self.generate_server_app(self.yaml_no_param)

        with app.test_client() as c:
            r = c.get('/v1/no/param')
            self.assertError(r, 500, 'INTERNAL SERVER ERROR')


    @patch('pymacaron_core.test.return_token')
    def test_swagger_invalid_server_return_value_custom_callback(self, func):
        func.__name__ = 'return_token'
        func.return_value = {'a': 1}

        def callback(e):
            return get_model('SessionToken')(token=str(e))

        app, spec = self.generate_server_app(self.yaml_no_param, callback=callback)

        with app.test_client() as c:
            r = c.get('/v1/no/param')
            j = json.loads(r.data.decode('utf-8'))
            log.debug("Got reply: %s" % j)
            self.assertError(r, 500, 'INTERNAL SERVER ERROR')
            self.assertDictEqual(
                j,
                {'token': "Method pymacaron_core.test.return_token did not return a class instance but a <class 'dict'>"}
            )

# TODO: enable this test when server-side validation is enabled
#
#    c = get_model('Credentials')
#    func.return_value = c(email='asdasd')
#
#     with app.test_client() as c:
#         r = c.get('/v1/no/param')
#         print("sc: %s" % str(r.status_code))
#         assert r.status_code == 500, r.status_code
#         j = json.loads(r.data.decode("utf-8"))
#         print("json reply: " + pprint.pformat(j))
#         assert j['error'] == 'SERVER_ERROR'
#         assert 'did not return a class' in j['error_description']



    @patch('pymacaron_core.test.return_token')
    def test_swagger_server_param_in_body(self, func):
        func.__name__ = 'return_token'

        app, spec = self.generate_server_app(self.yaml_in_body)

        SessionToken = get_model('SessionToken')
        Credentials = get_model('Credentials')
        func.return_value = SessionToken(token='456')

        with app.test_client() as c:
            r = c.get('/v1/in/body', data=json.dumps({
                'email': 'a@a.a',
                'int': '123123',
            }))
            self.assertReplyOK(r, '456')
            func.assert_called_once_with(Credentials(email='a@a.a', int='123123'))


    @patch('pymacaron_core.test.return_token')
    def test_swagger_server_param_in_query(self, func):
        func.__name__ = 'return_token'

        app, spec = self.generate_server_app(self.yaml_in_query)

        SessionToken = get_model('SessionToken')
        func.return_value = SessionToken(token='456')

        with app.test_client() as c:
            r = c.get('/v1/in/query?foo=aaaa&bar=bbbb')
            self.assertReplyOK(r, '456')
            func.assert_called_once_with(bar='bbbb', foo='aaaa')


    @patch('pymacaron_core.test.return_token')
    def test_swagger_server_param_in_query__missing_required_param(self, func):
        func.__name__ = 'return_token'
        app, spec = self.generate_server_app(self.yaml_in_query)

        SessionToken = get_model('SessionToken')
        func.return_value = SessionToken(token='456')

        with app.test_client() as c:
            r = c.get('/v1/in/query?bar=bbbb')
            self.assertError(r, 400, 'BAD REQUEST')
            func.assert_not_called()


    def test_swagger_server_auth(self):
        pass


    @patch('pymacaron_core.test.return_token')
    def test_unmarshal_request_error__missing_required_argument(self, func):
        func.__name__ = 'return_token'

        app, spec = self.generate_server_app(self.yaml_in_body)

        SessionToken = get_model('SessionToken')
        func.return_value = SessionToken(token='456')

        with app.test_client() as c:
            r = c.get('/v1/in/body', data=json.dumps({'bazzoom': 'thiswontwork'}))
            self.assertError(r, 400, 'BAD REQUEST')
            func.assert_not_called()


    @patch('pymacaron_core.test.return_token')
    def test_unmarshal_request_error__wrong_argument_format(self, func):
        func.__name__ = 'return_token'

        app, spec = self.generate_server_app(self.yaml_in_body)

        SessionToken = get_model('SessionToken')
        func.return_value = SessionToken(token='456')

        with app.test_client() as c:
            data = json.dumps({
                'email': 'a@2a.a',
                'int': [1, 2, 3],
            })

            r = c.get('/v1/in/body', data=data)

        # verify server reply
# TODO: uncomment when bravado-core start returning error on this
#         assert r.status_code == 400, r.status_code
#         j = json.loads(r.data.decode("utf-8"))
#         print("json reply: " + pprint.pformat(j))
#         assert j['error'] == 'INVALID_PARAMETER'
#         assert j['status'] == 400
#         assert "email' is a required property" in j['error_description']



    @patch('pymacaron_core.test.return_token')
    def test_swagger_server_param_in_path(self, func):
        func.__name__ = 'return_token'

        app, spec = self.generate_server_app(self.yaml_in_path)

        SessionToken = get_model('SessionToken')
        func.return_value = SessionToken(token='456')

        with app.test_client() as c:
            r = c.get('/v1/in/1234/foo/bob234')
            self.assertReplyOK(r, '456')
            func.assert_called_once_with(item='1234', path='bob234')


# @patch('pymacaron_core.test.return_token')
# def test_swagger_server_param_in_path__missing_required_param(self, func):
#     app, spec = self.generate_server_app(self.yaml_in_query)

#     func.__name__ = 'return_token'
#     SessionToken = get_model('SessionToken')
#     func.return_value = SessionToken(token='456')

#     with app.test_client() as c:
#         r = c.get('/v1/in/query?bar=bbbb')
#         self.assertError(r, 400, 'BAD REQUEST')
#         func.assert_not_called()
