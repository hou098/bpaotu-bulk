import re
import logging
import ckan.plugins as p
from pylons import config
from ckan import model
from ckan.lib.base import abort, BaseController
from ckan.controllers.organization import OrganizationController
from ckan.common import request, response, c
from ckan.logic import NotFound, NotAuthorized

_ = p.toolkit._


log = logging.getLogger(__name__)


class WgetOrganizationController(OrganizationController):
    controller = 'ckanext.wget.controller:WgetOrganizationController'
    group_types = ['organization']

    def __init__(self, *args, **kwargs):
        super(WgetOrganizationController, self).__init__(*args, **kwargs)
        self.limit = p.toolkit.asint(config.get('ckanext.wget.limit', 100))

    def file_list(self, id):
        group_type = self._ensure_controller_matches_group_type(
            id.split('@')[0])

        context = {
            'model': model,
            'session': model.Session,
            'user': c.user,
            'schema': self._db_to_form_schema(group_type=group_type),
            'for_view': True
        }
        data_dict = {'id': id, 'type': group_type}

        # unicode format (decoded from utf8)
        c.q = request.params.get('q', '')

        try:
            # Do not query for the group datasets when dictizing, as they will
            # be ignored and get requested on the controller anyway
            data_dict['include_datasets'] = False
            c.group_dict = self._action('group_show')(context, data_dict)
            c.group = context['group']
        except (NotFound, NotAuthorized):
            raise
            abort(404, _('Group not found'))

        self._read(id, self.limit, group_type)

        urls = []
        for package in c.page.items:
            for resource in package['resources']:
                urls.append(resource['url'])
        response.headers['Content-Type'] = 'text/plain'
        response.charset = 'UTF-8'
        resp = u'\n'.join(urls) + u'\n'
        return resp


class WgetPackageController(BaseController):
    controller = 'ckanext.wget.controller:WgetPackageController'

    def __init__(self, *args, **kwargs):
        super(WgetPackageController, self).__init__(*args, **kwargs)
        self.limit = p.toolkit.asint(config.get('ckanext.wget.limit', 100))

    def file_list(self, id):
        package = {'resources': []}
        urls = []
        for resource in package['resources']:
            urls.append(resource['url'])
        response.headers['Content-Type'] = 'text/plain'
        response.charset = 'UTF-8'
        resp = u'\n'.join(urls) + u'\n'
        return resp
