from apps.wallposts.views import  Project
from django.conf.urls import patterns, url
from .views import ProjectWallPostList, ProjectWallPostDetail, ProjectMediaWallPostList, ProjectMediaWallPostDetail, ProjectTextWallPostList
urlpatterns = patterns('',
    # TODO: Move this to projects.
    url(r'^projectwallposts/$', ProjectWallPostList.as_view(), name='project-wallpost-list'),
    url(r'^projectwallposts/(?P<pk>[0-9]+)$', ProjectWallPostDetail.as_view(), name='project-wallpost-detail'),
    url(r'^projectmediawallposts/$', ProjectMediaWallPostList.as_view(), name='project-mediawallpost-list'),
    url(r'^projectmediawallposts/(?P<pk>[0-9]+)$', ProjectMediaWallPostDetail.as_view(), name='project-mediawallpost-detail'),
    url(r'^projecttextwallposts/$', ProjectTextWallPostList.as_view(), name='project-textwallpost-list'),
)