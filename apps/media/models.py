import logging
logger = logging.getLogger(__name__)

import micawber

from django.db import models
from django.utils.translation import ugettext as _
from django.core.exceptions import ValidationError

from django_extensions.db.fields import (
    ModificationDateTimeField, CreationDateTimeField
)

from sorl.thumbnail import ImageField


class Album(models.Model):
    """ Album containing media objects. """

    title = models.CharField(_("title"), max_length=255)
    # This is populated from the project slug in legacy and should have
    # the same length
    slug = models.SlugField(_("slug"), unique=True, max_length=100)
    description = models.TextField(_("description"), blank=True)

    created = CreationDateTimeField(_("created"))
    updated = ModificationDateTimeField(_("updated"))

    class Meta:
        verbose_name = _("album")
        verbose_name_plural = _("albums")

    def __unicode__(self):
        return self.title or unicode(self.pk)

    @models.permalink
    def get_absolute_url(self):
        """ Get the URL for the current album. """

        return ('album_detail', (), {
            'slug': self.slug
        })


class MediaObjectBase(models.Model):
    """ Abstract base class for media objects contained in albums. """

    album = models.ForeignKey(Album, verbose_name=_("album"))

    title = models.CharField(_("title"), max_length=255, blank=True)
    description = models.TextField(_("description"), blank=True)

    created = CreationDateTimeField(_("created"))
    updated = ModificationDateTimeField(_("updated"))

    class Meta:
        abstract = True

    def __unicode__(self):
        return self.title or unicode(self.pk)


class OembedAbstractBase(models.Model):
    """ Abstract base class for classes populated through OEmbed. """

    # Title included in MediaObjectBase
    url = models.URLField(_("URL"))

    thumbnail_url = models.URLField(
        _("thumbnail URL"), blank=True
    )
    thumbnail_width = models.SmallIntegerField(
        _("thumbnail width"), blank=True, null=True
    )
    thumbnail_height = models.SmallIntegerField(
        _("thumbnail height"), blank=True, null=True
    )

    provider_name = models.CharField(
        _("providr name"), blank=True, max_length=255
    )
    provider_url = models.CharField(
        _("provider URL"), blank=True, max_length=255
    )

    author_name = models.CharField(
        _("author name"), blank=True, max_length=255
    )
    author_url = models.URLField(
        _("author URL"), blank=True
    )

    class Meta:
        abstract = True

    def clean(self):
        """ Get OEmbed metadata on save. """

        # load up rules for some default providers, such as youtube and flickr
        providers = micawber.bootstrap_basic()

        # Get the data
        try:
            oembed_data = providers.request(self.url)
        except micawber.ProviderException:
            msg = _('Could not find metadata for object.')

            logger.exception(msg)
            raise ValidationError(msg)

        logger.debug(
            u'Found OEmbed data on %s for %s',
            self.url, self
        )

        for (key, value) in oembed_data.iteritems():
            try:
                if not getattr(self, key):
                    logger.debug(
                        u'Setting field %s on %s to %s', key, self, value
                    )
                    setattr(self, key, value)
            except AttributeError:
                pass


class LocalPicture(MediaObjectBase):
    """ Picture stored locally. """

    picture = ImageField(_("picture"), upload_to='pictures/')

    class Meta:
        verbose_name = _("local picture")
        verbose_name_plural = _("local pictures")

    @models.permalink
    def get_absolute_url(self):
        """ Get the URL for the picture. """

        return ('localpicture_detail', (), {
            'album_slug': self.album.slug,
            'pk': str(self.pk)
        })


class EmbeddedVideo(MediaObjectBase, OembedAbstractBase):
    """ Embedded video, hosted remotely. """

    html = models.TextField(_("HTML"), blank=True)
    width = models.SmallIntegerField(_("width"), blank=True, null=True)
    height = models.SmallIntegerField(_("height"), blank=True, null=True)

    duration = models.SmallIntegerField(_("duration"), blank=True, null=True)

    class Meta:
        verbose_name = _("embedded video")
        verbose_name_plural = _("embedded videos")

    @models.permalink
    def get_absolute_url(self):
        """ Get the URL for the video. """

        return ('embeddedvideo_detail', (), {
            'album_slug': self.album.slug,
            'pk': str(self.pk)
        })


"""
Some more code I had lying around:

class Link(OembedAbstractBase):
    pass


class EmbeddedRich(OembedAbstractBase):
    html = models.TextField(blank=True)
    width = models.SmallIntegerField(blank=True, null=True)
    height = models.SmallIntegerField(blank=True, null=True)


class EmbeddedPhoto(OembedAbstractBase):
    width = models.SmallIntegerField(blank=True, null=True)
    height = models.SmallIntegerField(blank=True, null=True)
"""