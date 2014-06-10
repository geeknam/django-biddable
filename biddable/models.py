from django.db import models
from django.db.models.fields import Field
from django.conf import settings
from django.contrib.contenttypes import generic
from django.contrib.contenttypes.models import ContentType



class Bid(models.Model):

    auction = models.ForeignKey(settings.BIDDABLE_AUCTION_MODEL, related_name='bids')
    bidder = models.ForeignKey(settings.BIDDABLE_BIDDER_MODEL, related_name='bids')

    # Generic relations
    content_type = models.ForeignKey('contenttypes.ContentType')
    object_id = models.PositiveIntegerField(db_index=True)
    content_object = generic.GenericForeignKey('content_type', 'object_id')

    price = models.DecimalField()
    timestamp = models.DateTimeField(auto_now=True) 

    def __unicode__(self):
        return '[%s] on %s by %s with %s' % (
            self.content_object,
            self.auction,
            self.bidder,
            self.price
        )


class _BiddableManager(models.Manager):

    @property
    def content_type(self):
        return ContentType.objects.get_for_model(self.instance.__class__)

    def get_query_set(self):
        return super(BiddleManager, self).get_query_set().filter(
            content_type=self.content_type, object_id=self.instance.id
        )

    def create(self, auction, bidder, price):
        return Bid.objects.create(
            auction=auction, bidder=bidder,
            content_type=self.content_type, object_id=self.instance.id,
            price=price
        )

    def for_auction(self, auction):
        return self.get_query_set().filter(auction=auction)

    def highest(self, auction=None):
        qset = self.for_auction(auction) if auction else self.get_query_set()
        qset = qset.order_by('price')
        return qset[0]

    def lowest(self, auction=None):
        qset = self.for_auction(auction) if auction else self.get_query_set()
        qset = qset.order_by('-price')
        return qset[0]


class BiddleManager(Field):

    def __init__(self, verbose_name="Bids", help_text="Bids",
            blank=False, related_name=None, to=None, manager=_BiddableManager):
        Field.__init__(self, verbose_name=verbose_name, help_text=help_text, blank=blank, null=True, serialize=False)
        self.manager = manager

    def __get__(self, instance, model):
        if instance is not None and instance.pk is None:
            raise ValueError("%s objects need to have a primary key value "
                "before you can access their bids." % model.__name__)
        manager = self.manager(
            model=model,
            instance=instance,
            prefetch_cache_name = self.name
        )
        return manager