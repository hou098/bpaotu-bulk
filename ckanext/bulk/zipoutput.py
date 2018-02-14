import jinja2
import ckan.lib.helpers as h
import sys
import datetime
import csv
from collections import defaultdict
from StringIO import StringIO
from pylons import config
from urlparse import urlparse
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED
from ckan.common import response
from io import BytesIO
from .bash import SH_TEMPLATE
from .powershell import POWERSHELL_TEMPLATE
from ckanext.scheming.helpers import scheming_get_dataset_schema


BULK_EXPLANATORY_NOTE = '''\
CKAN Bulk Download
------------------

{title}

Bulk download package generated:
{timestamp}

This archive contains the following files:

urls.txt:
A list of all URLs matching the CKAN search you performed.

md5sum.txt:
MD5 checksums for all files.

download.ps1:
Windows PowerShell script, which when executed will download the files,
and then checksum them. There are no dependencies other than PowerShell.

download.sh:
UNIX shell script, which when executed will download the files,
and then checksum then. This is supported on any Linux or MacOS/BSD
system, so long as `wget` is installed.

'''


def get_timestamp():
    return datetime.datetime.now(
        h.get_display_timezone()).strftime('%Y-%m-%dT%H:%M:%S.%f%z')


def packages_by_type(packages):
    by_type = defaultdict(list)
    for package in packages:
        by_type[package['type']].append(package)
    return by_type


def resources_by_type(resources):
    by_type = defaultdict(list)
    for resource in resources:
        by_type[resource['resource_type']].append(resource)
    return by_type


def debug(s):
    sys.stderr.write(repr(s))
    sys.stderr.write('\n')
    sys.stderr.flush()


def schema_to_csv(typ, schema_key, objects):
    # Note: as we're in Python 2, we have to do a bit of a dance here with unicode --
    # we must make sure everything we put into the writer has been encoded
    schema = scheming_get_dataset_schema(typ)
    fd = StringIO()
    w = csv.writer(fd)
    header = []
    field_names = []
    for field in schema[schema_key]:
        field_names.append(field['field_name'])
        header.append(unicode(field['label'].encode('utf8')))
    w.writerow(header)
    for obj in sorted(objects, key=lambda p: p['name']):
        w.writerow([unicode(obj.get(field_name, '')).encode('utf8') for field_name in field_names])
    return fd.getvalue()


def bulk_download_zip(pfx, title, user, packages, resources):
    def ip(s):
        return pfx + '/' + s

    def write_script(filename, contents):
        info = ZipInfo(ip(filename))
        info.external_attr = 0755 << 16L
        user_page = None
        if user:
            site_url = config.get('ckan.site_url').rstrip('/')
            user_page = '%s/%s' % (site_url, h.url_for(controller='user', action='read', id=user.name))
        contents = jinja2.Environment().from_string(contents).render(user_page=user_page)
        zf.writestr(info, contents.encode('utf-8'))

    urls = []
    md5sums = []

    md5_attribute = config.get('ckanext.bulk.md5_attribute', 'md5')
    for resource in sorted(resources, key=lambda r: r['url']):
        url = resource['url']
        urls.append(resource['url'])
        if md5_attribute in resource:
            filename = urlparse(url).path.split('/')[-1]
            md5sums.append((resource[md5_attribute], filename))

    response.headers['Content-Type'] = 'application/zip'
    response.headers['Content-Disposition'] = str('attachment; filename="%s.zip"' % pfx)
    fd = BytesIO()
    zf = ZipFile(fd, mode='w', compression=ZIP_DEFLATED)
    zf.writestr(ip('README.txt'), BULK_EXPLANATORY_NOTE.format(
        timestamp=get_timestamp(),
        title=title))
    zf.writestr(ip('urls.txt'), u'\n'.join(urls) + u'\n')
    zf.writestr(ip('md5sum.txt'), u'\n'.join('%s  %s' % t for t in md5sums) + u'\n')

    for typ, typ_packages in packages_by_type(packages).items():
        zf.writestr(ip('datasets/{}.csv'.format(typ)), schema_to_csv(typ, 'dataset_fields', typ_packages))

    for typ, typ_resources in resources_by_type(resources).items():
        zf.writestr(ip('files/{}.csv'.format(typ)), schema_to_csv(typ, 'resource_fields', typ_resources))

    write_script('download.sh', SH_TEMPLATE)
    write_script('download.ps1', POWERSHELL_TEMPLATE)

    zf.close()
    return fd.getvalue()