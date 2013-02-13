from django.conf.urls import patterns, url
from surlex.dj import surl
from .views import (FundApi, OrderList, OrderDetail, OrderCurrent, OrderItemList, OrderDonationList,
                    OrderDonationDetail, OrderLatestDonationList, PaymentOrderProfileCurrent, OrderLatestItemList,
                    PaymentMethodCurrent)


urlpatterns = patterns('',
    url(r'^$', FundApi.as_view(), name='fund-order-list'),

    url(r'^orders/$', OrderList.as_view(), name='fund-order-list'),
    surl(r'^orders/<pk:#>$', OrderDetail.as_view(), name='fund-order-detail'),
    url(r'^orders/current$', OrderCurrent.as_view(), name='fund-order-current'),
    url(r'^orders/latest/items/$', OrderLatestItemList.as_view(), name='fund-order-latest-item-list'),
    url(r'^orders/current/items/$', OrderItemList.as_view(), name='fund-order-current-item-list'),
    url(r'^orders/current/donations/$', OrderDonationList.as_view(), name='fund-order-current-donation-list'),
    url(r'^orders/latest/donations/$', OrderLatestDonationList.as_view(), name='fund-order-latest-donation-list'),
    surl(r'^orders/current/donations/<pk:#>$', OrderDonationDetail.as_view(), name='fund-order-current-donation-detail'),

    url(r'^paymentorderprofiles/current$', PaymentOrderProfileCurrent.as_view(), name='fund-payment-order-profile-current'),
    url(r'^paymentmethods/current$', PaymentMethodCurrent.as_view(), name='fund-payment-order-profile-current'),


)
