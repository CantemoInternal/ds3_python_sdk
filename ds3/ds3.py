import httplib
import hmac
import base64
import xml.dom.minidom
import xml.etree.ElementTree as xmldom

from hashlib import sha1
from urlparse import urlparse
from email.Utils import formatdate

def format_output(xml_string):
    print xml.dom.minidom.parseString(xml_string).toprettyxml()

def sign(key, contents):
    signer = hmac.new(key.encode('utf-8'), digestmod=sha1)
    signer.update(contents)
    digest = signer.digest()
    return base64.encodestring(digest).strip().decode('utf-8')

def aws_signature(key, verb='GET', md5='',
    content_type='', date='',
    canonicalized_amz_header='', canonicalized_resource=''):
    signature_string = verb + '\n'
    signature_string += md5 + '\n'
    signature_string += content_type+ '\n'
    signature_string += date + '\n'
    signature_string += canonicalized_amz_header
    signature_string += canonicalized_resource
    return sign(key, signature_string)

def get_date():
    return formatdate()

def join_paths(path1, path2):
    final_path = ''
    if not path1.startswith('/'):
        final_path += '/'
    final_path += path1

    if path1.endswith('/') and path2.startswith('/'):
        final_path += path2[1:]
    elif path1.endswith('/'):
        final_path += path2
    else:
        final_path += '/' + path2
    return final_path

def build_path(resource, query_params):
    if len(query_params) == 0:
        return resource
    new_path = resource + '?'

    new_path += '&'.join(map(lambda tupal: (tupal[0] + '=' + tupal[1]), query_params.iteritems()))
    return new_path

class Credentials(object):
    def __init__(self, client_id, key):
        self.client_id = client_id
        self.key = key

class ObjectData(object):
    def __init__(self, name, size):
        self.name = name
        self.size = size

class Ds3(object):
    def __init__(self, endpoint, credentials):
        self.endpoint = endpoint
        self.credentials = credentials
        url = urlparse(self.endpoint)
        self.hostname = url.hostname
        self.port = url.port

    def service_list(self):
        response = self.__get('/')
        return response.read()

    def bucket_list(self, bucket):
        response = self.__get(join_paths('/', bucket))
        return response.read()

    def create_bucket(self, bucket):
        response = self.__put(join_paths('/', bucket))
        return response.read()

    def get_object(self, bucket, object_name):
        response = self.__get(join_paths(bucket, object_name))
        return response.read()

    def put_object(self, bucket, object_name, object_data):
        response = self.__put(join_paths(bucket, object_name), object_data)
        return response.read()

    def bulk_put(self, bucket, object_list):
        objects = xmldom.Element('objects')
        for file_object in object_list:
            obj_elm = xmldom.Element('object')
            obj_elm.set('name', file_object.name)
            obj_elm.set('size', file_object.size)
            objects.append(obj_elm)
        response = self.__put(join_paths('/', bucket) + '/?start-bulk-put', xmldom.tostring(objects))
        return response.read()

    def bulk_get(self, bucket, object_list):
        objects = xmldom.Element('objects')
        for file_object in object_list:
            obj_elm = xmldom.Element('object')
            obj_elm.set('name', file_object.name)
            objects.append(obj_elm)
        response = self.__put(join_paths('/', bucket) + '/?start-bulk-get', xmldom.tostring(objects))
        return response.read()

    def delete_object(self, bucket, object_name):
        response = self.__delete(join_paths(bucket, object_name))
        return response.read()

    def __get(self, resource):
        return self.__http_opt('GET', resource)

    def __delete(self, resource):
        return self.__http_opt('DELETE', resource)

    def __http_opt(self, verb, resource):
        connection = httplib.HTTPConnection(self.endpoint)
        date = get_date()
        headers = {}
        headers['Host'] = self.hostname
        headers['Date'] = date
        headers['Authorization'] = self.__build_authorization(verb=verb, date=date, resource=resource)
        connection.request(verb, resource, headers=headers)

        return connection.getresponse()

    def __put(self, resource, body='', query_params={}):
        connection = httplib.HTTPConnection(self.endpoint)
        date = get_date()
        headers = {}
        headers['Host'] = self.hostname
        headers['Date'] = date
        headers['Content-Type'] = 'application/octet-stream'
        headers['Authorization'] = self.__build_authorization(verb='PUT', date=date, content_type='application/octet-stream', resource=resource)
        resource_path = build_path(resource, query_params)
        connection.request('PUT', resource_path, body=body, headers=headers)

        return connection.getresponse()

    def __build_authorization(self, verb='', date='', content_type='', resource=''):
        signature = aws_signature(self.credentials.key, verb=verb, content_type=content_type, date=date, canonicalized_resource=resource)
        return 'AWS ' + self.credentials.client_id + ':' + signature

