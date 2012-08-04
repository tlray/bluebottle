from django.conf.urls.defaults import patterns, url, include

from surlex.dj import surl

from .api import ProjectResource, ProjectSearchFormResource
from .views import (
        ProjectListView, ProjectDetailView, ProjectMapView,
        ProjectSearchView)

project_resource = ProjectResource()
projectsearchform_resource = ProjectSearchFormResource()


urlpatterns = patterns('apps.projects.views',
    surl(r'^list/$', ProjectListView.as_view(), name='project_list'),
    surl(r'^$', ProjectSearchView.as_view(), name='project_search'),
    surl(r'^<slug:s>/$', ProjectDetailView.as_view(), name='project_detail'),
    surl(r'^<slug:s>/map/$', ProjectMapView.as_view(), name='project_map'),
)

# API urls
urlpatterns += patterns('',
    url(r'^api/', include(project_resource.urls)),
    url(r'^api/', include(projectsearchform_resource.urls)),
)
